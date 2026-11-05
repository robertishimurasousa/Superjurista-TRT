"""Aceite técnico da fase 3 com caso fictício e duas reclamadas."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'scaffold/scripts'))
sys.path.insert(0, str(RAIZ / 'tests/fixtures'))
from documentos import hash_arquivo, salvar_json, validar_schema
from verificar_pedidos import contexto, verificar
from caso_trabalhista import criar, gravar


class PedidosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.base.cleanup)
        cls.modelo = criar(Path(cls.base.name).resolve())

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name).resolve()
        self.workspace = self.pasta / 'workspace'
        shutil.copytree(self.modelo[0], self.workspace)
        self.rel, self.tri, self.regras, self.matriz = copy.deepcopy(self.modelo[1:])
        self.gravar()

    def gravar(self):
        gravar(self.workspace, self.rel, self.tri, self.regras, self.matriz)

    def conferir(self, etapa='analise'):
        self.gravar()
        return verificar(self.workspace, etapa)

    def assertBloqueado(self, resultado):
        self.assertFalse(resultado['sem_pendencias'], resultado)
        self.assertFalse(resultado['apto_para_minuta'])

    def test_caso_com_duas_empresas_e_analise_provisoria(self):
        resultado = verificar(self.workspace)
        self.assertTrue(resultado['sem_pendencias'], resultado)
        self.assertFalse(resultado['apto_para_minuta'])
        self.assertEqual(resultado['validacao_juridica'], 'nao-realizada')
        self.assertEqual(resultado['aceite_humano'], 'nao-registrado')
        self.assertIn('fontes-juridicas-fase-4', resultado['dependencias_posteriores'])
        self.assertTrue(resultado['lacunas'])  # Valor não informado não é inventado.

    def test_dado_informado_sem_referencia_e_ausencia_com_valor_rejeitados(self):
        for campo, valor in [('referencias', []), ('valor', None)]:
            rel = copy.deepcopy(self.rel)
            rel['partes'][0]['nome'][campo] = valor
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                validar_schema(rel, 'pedidos.schema.json')
        self.rel['pedidos'][0]['valor']['valor'] = '100.00'
        with self.assertRaises(ValueError):
            validar_schema(self.rel, 'pedidos.schema.json')

    def test_nao_completa_defesa_ausente(self):
        self.rel['pedidos'][0]['defesas'][1]['alegacao'] = copy.deepcopy(self.rel['pedidos'][0]['valor'])
        self.tri['estado'] = 'bloqueada'
        self.assertBloqueado(self.conferir('triagem'))

    def test_pedido_omitido_da_triagem_ou_matriz(self):
        self.tri['questoes'] = []
        self.assertTrue(self.conferir()['erros'])
        self.tri = copy.deepcopy(self.modelo[2])
        self.matriz['analises'] = []
        self.assertTrue(self.conferir()['erros'])

    def test_pedido_acessorio_exige_principal_e_cobertura(self):
        acessorio = copy.deepcopy(self.rel['pedidos'][0])
        acessorio.update(id='PED-002', natureza='acessorio', principal_id='PED-001')
        acessorio['descricao']['valor'] = 'Reflexos das horas extras.'
        self.rel['pedidos'].append(acessorio)
        self.rel['cobertura'][0]['pedidos_ids'].append('PED-002')
        self.assertTrue(self.conferir('relatorio')['sem_pendencias'])
        self.assertTrue(self.conferir('triagem')['erros'])
        acessorio['principal_id'] = 'PED-002'
        self.assertTrue(self.conferir('relatorio')['erros'])

    def test_ids_repetidos_e_duplicata_material(self):
        self.rel['pedidos'].append(copy.deepcopy(self.rel['pedidos'][0]))
        self.assertTrue(self.conferir('relatorio')['erros'])
        self.rel['pedidos'][-1]['id'] = 'PED-002'
        self.assertTrue(any('duplicado' in e for e in self.conferir('relatorio')['pendencias']))

    def test_parte_inexistente_polo_e_contrato_incompativeis(self):
        for campo, valor in [('reclamante_id', 'PAR-002'), ('reclamadas_ids', ['PAR-999']), ('contratos_ids', ['CON-999'])]:
            self.rel = copy.deepcopy(self.modelo[1])
            self.rel['pedidos'][0][campo] = valor
            with self.subTest(campo=campo):
                self.assertTrue(self.conferir('relatorio')['erros'])

    def test_omissao_de_defesa_da_segunda_empresa(self):
        self.matriz['analises'][0]['defesas'].pop()
        self.assertTrue(self.conferir()['erros'])
        self.rel['pedidos'][0]['defesas'].pop()
        self.assertTrue(self.conferir('relatorio')['erros'])

    def test_periodo_invertido_e_data_impossivel(self):
        self.rel['pedidos'][0]['periodo']['inicio']['valor'] = '2026-01-01'
        self.assertTrue(self.conferir('relatorio')['erros'])
        self.rel['pedidos'][0]['periodo']['inicio']['valor'] = '2025-02-30'
        with self.assertRaises(ValueError):
            self.conferir('relatorio')

    def test_campos_obrigatorios_por_materia(self):
        for tema, campo in [('jornada', 'funcao'), ('verbas-rescisorias', 'salario')]:
            self.rel = copy.deepcopy(self.modelo[1])
            self.rel['pedidos'][0]['tema'] = tema
            self.rel['contratos'][0][campo] = copy.deepcopy(self.rel['pedidos'][0]['valor'])
            with self.subTest(tema=tema):
                self.assertBloqueado(self.conferir('relatorio'))

    def test_documento_pagina_e_trecho_inexistentes(self):
        for campo, valor in [('documento_id', 'DOC-'+'0'*64), ('pagina', 2), ('trecho', 'FRASE QUE NAO EXISTE NOS AUTOS')]:
            self.rel = copy.deepcopy(self.modelo[1])
            self.rel['partes'][0]['nome']['referencias'][0][campo] = valor
            with self.subTest(campo=campo):
                self.assertTrue(self.conferir('relatorio')['erros'])

    def test_cobertura_incompleta_repetida_e_pedido_inexistente(self):
        for paginas in [[], self.rel['cobertura']*2, [{**self.rel['cobertura'][0], 'pedidos_ids': ['PED-999']}]]:
            self.rel['cobertura'] = copy.deepcopy(paginas)
            self.assertTrue(self.conferir('relatorio')['erros'])

    def test_inventario_exige_conferencia_humana(self):
        self.rel['conferencia_inventario'] = {'estado': 'pendente', 'responsavel': None, 'data': None}
        self.assertBloqueado(self.conferir('relatorio'))

    def test_escopo_incerto_bloqueia_triagem_e_analise(self):
        self.tri['escopo']['competencia']['estado'] = 'incerto'
        self.assertTrue(self.conferir()['erros'])
        self.tri['estado'] = 'bloqueada'
        self.matriz['analises'][0].update(estado='bloqueada', pendencias=['Conferir competência.'])
        self.matriz['analises'][0]['conclusao']['resultado'] = 'inconclusiva'
        resultado = self.conferir()
        self.assertEqual(resultado['erros'], [])
        self.assertBloqueado(resultado)

    def test_ente_publico_e_materia_fora_recorte(self):
        self.rel['partes'][1]['natureza']['valor'] = 'ente-publico'
        self.assertBloqueado(self.conferir('relatorio'))
        self.rel = copy.deepcopy(self.modelo[1])
        self.rel['pedidos'][0]['tema'] = 'outro'
        self.assertTrue(self.conferir('triagem')['erros'])

    def test_prova_decisiva_ausente_e_prova_sem_referencia(self):
        prova = self.tri['questoes'][0]['provas_necessarias'][0]
        prova['estado'] = 'ausente'
        prova['referencias'] = []
        self.assertTrue(self.conferir('triagem')['erros'])
        prova['estado'] = 'disponivel'
        self.assertTrue(self.conferir('triagem')['erros'])

    def test_instrumento_coletivo_ausente_gera_bloqueio(self):
        self.rel['pedidos'][0]['norma_coletiva']['necessaria'] = True
        resultado = self.conferir('relatorio')
        self.assertEqual(resultado['erros'], [])
        self.assertTrue(any('coletivo' in p for p in resultado['pendencias']))
        self.assertBloqueado(resultado)

    def test_norma_coletiva_por_categoria_territorio_e_periodo(self):
        norma = self.rel['pedidos'][0]['norma_coletiva']
        norma.update(necessaria=True, documento_id=self.rel['cobertura'][0]['documento_id'],
                     vigencia=copy.deepcopy(self.rel['contratos'][0]['periodo']),
                     categoria=copy.deepcopy(self.rel['contratos'][0]['categoria']),
                     territorio=copy.deepcopy(self.rel['contratos'][0]['territorio']))
        self.assertTrue(self.conferir('relatorio')['sem_pendencias'])
        norma['territorio']['valor'] = 'Outra cidade'
        norma['vigencia']['fim']['valor'] = '2025-06-30'
        self.assertBloqueado(self.conferir('relatorio'))

    def test_regra_nao_conferida_impede_hipotese_de_merito(self):
        self.regras['regras'][0]['conferencia'] = {'estado': 'pendente', 'responsavel': None, 'data': None}
        resultado = self.conferir()
        self.assertTrue(resultado['erros'])
        self.assertBloqueado(resultado)

    def test_regra_ausente_suspensa_e_fora_da_vigencia(self):
        self.regras['regras'].pop(0)
        self.assertTrue(self.conferir()['erros'])
        for campo, valor in [('situacao', 'suspensa'), ('vigencia', {'inicio': '2026-01-01', 'fim': None})]:
            self.regras = copy.deepcopy(self.modelo[3])
            self.regras['regras'][0][campo] = valor
            self.assertBloqueado(self.conferir())

    def test_conteudo_de_regra_alterado_e_url_enganosa(self):
        caminho = self.workspace / self.regras['regras'][0]['arquivo']
        original = caminho.read_bytes()
        caminho.write_bytes(original+b'ALTERACAO')
        self.assertTrue(verificar(self.workspace)['erros'])
        caminho.write_bytes(original)
        for url in ['https://www.tst.jus.br.exemplo.com/regra', 'http://www.tst.jus.br/regra', 'https://usuario@www.tst.jus.br/regra']:
            self.regras['regras'][0]['url_oficial'] = url
            self.assertTrue(self.conferir()['erros'])

    def test_arquivo_de_regra_fora_da_pasta_e_link_simbolico(self):
        self.regras['regras'][0]['arquivo'] = '../fora.txt'
        with self.assertRaises(ValueError):
            self.conferir()
        self.regras = copy.deepcopy(self.modelo[3])
        caminho = self.workspace / self.regras['regras'][0]['arquivo']
        caminho.unlink()
        caminho.symlink_to(self.workspace / self.regras['regras'][1]['arquivo'])
        with self.assertRaises(ValueError):
            self.conferir()

    def test_hashes_impedem_reuso_apos_alteracao(self):
        for arquivo in ['documentos.json', 'pedidos.json', 'triagem.json', 'regras-juridicas.json']:
            caminho = self.workspace / arquivo
            dados = caminho.read_bytes()
            caminho.write_bytes(dados+b'\n')
            with self.subTest(arquivo=arquivo):
                self.assertTrue(verificar(self.workspace)['erros'])
            caminho.write_bytes(dados)

    def test_onus_dinamico_sem_decisao_e_questao_processual_omitida(self):
        self.matriz['analises'][0]['onus']['atribuicao'] = 'distribuicao-dinamica'
        self.assertBloqueado(self.conferir())
        self.matriz['questoes_processuais'].pop()
        self.assertTrue(self.conferir()['erros'])

    def test_matriz_bloqueada_nao_pode_concluir_merito(self):
        self.matriz['analises'][0].update(estado='bloqueada', pendencias=['Lacuna de prova.'])
        self.assertTrue(self.conferir()['erros'])

    def test_periodo_sem_relacao_com_contrato(self):
        # Desvincula os objetos compartilhados da fixture antes de alterar o período do pedido.
        self.rel['pedidos'][0]['periodo'] = copy.deepcopy(self.rel['pedidos'][0]['periodo'])
        self.rel['pedidos'][0]['periodo']['inicio']['valor'] = '2024-01-01'
        self.rel['pedidos'][0]['periodo']['fim']['valor'] = '2024-12-31'
        self.assertBloqueado(self.conferir('relatorio'))

    def test_fato_ausente_nao_pode_ser_corroborado(self):
        self.matriz['analises'][0]['fatos'][0] = {
            'descricao': copy.deepcopy(self.rel['pedidos'][0]['valor']), 'situacao': 'corroborado'}
        self.assertTrue(self.conferir()['erros'])

    def test_regras_de_outro_tema_nao_suprem_onus_e_custas(self):
        self.matriz['analises'][0]['onus']['regra_ids'] = ['REG-001']
        self.matriz['questoes_processuais'][0]['regra_ids'] = ['REG-001']
        resultado = self.conferir()
        self.assertBloqueado(resultado)
        self.assertTrue(any('próprio tema' in p for p in resultado['pendencias']))

    def test_matriz_bloqueada_sem_registro_de_regras_preserva_lacunas(self):
        self.matriz['regras_sha256'] = None
        analise = self.matriz['analises'][0]
        analise.update(estado='bloqueada', pendencias=['Fontes oficiais ainda não conferidas.'], regra_ids=[])
        analise['onus'].update(atribuicao='nao-definido', regra_ids=[])
        analise['conclusao'].update(resultado='inconclusiva', regra_ids=[])
        for q in self.matriz['questoes_processuais']:
            q.update(estado='pendente', regra_ids=[])
        (self.workspace/'regras-juridicas.json').unlink()
        salvar_json(self.workspace/'matriz-pedidos.json', self.matriz)
        resultado = verificar(self.workspace)
        self.assertEqual(resultado['erros'], [], resultado)
        self.assertBloqueado(resultado)

    def test_contexto_cli_e_instalacao_independente(self):
        destino = self.pasta / 'instalado'
        r = subprocess.run([sys.executable, str(RAIZ/'scripts/instalar_perfil.py'), '--perfil', 'jt-1g-local', '--destino', str(destino)], capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        script = destino / 'scripts/verificar_pedidos.py'
        cmd = [sys.executable, str(script), str(self.workspace)]
        r = subprocess.run(cmd+['--contexto'], cwd=self.pasta, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['pedidos_sha256'], hash_arquivo(self.workspace/'pedidos.json'))
        r = subprocess.run(cmd+['--gate'], cwd=self.pasta, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.tri['estado'] = 'bloqueada'
        self.matriz['analises'][0].update(estado='bloqueada', pendencias=['Caso bloqueado.'])
        self.matriz['analises'][0]['conclusao']['resultado'] = 'inconclusiva'
        self.gravar()
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(cmd+['--gate'], capture_output=True).returncode, 1)
        (self.workspace/'pedidos.json').write_text('{}')
        self.assertEqual(subprocess.run(cmd+['--gate'], capture_output=True).returncode, 2)

    def test_artefatos_ausentes_e_schema_desconhecido(self):
        (self.workspace/'pedidos.json').unlink()
        self.assertTrue(verificar(self.workspace)['erros'])
        self.rel['schema_version'] = 2
        with self.assertRaises(ValueError):
            self.conferir()


if __name__ == '__main__':
    unittest.main()
