"""Minuta e sessão com dados sintéticos: verifica software, não o mérito jurídico."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ/'scaffold/scripts'))
sys.path.insert(0, str(RAIZ/'tests/fixtures'))
from caso_com_fontes import criar_com_fontes, revisao
from documentos import hash_arquivo, salvar_json
from fontes_jt import ler_json
from verificar_referencias_jt import contexto as contexto_refs, verificar as verificar_refs, regras_usadas
from verificar_sentenca_jt import contexto, contexto_revisao, verificar, renderizar, ITENS
from merge_sentenca_jt import preparar, publicar
import merge_sentenca_jt
import estado_execucao as estado


class MinutaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.base.cleanup)
        cls.modelo, _, _ = criar_com_fontes(Path(cls.base.name).resolve())
        docs = ler_json(cls.modelo, 'documentos.json')['documentos']
        salvar_json(cls.modelo/'classificacao.json', {'schema_version': 1, 'segmentos': [
            {'documento_id': d['id'], 'pagina_inicio': 1, 'pagina_fim': d['paginas_total'],
             'tipo': 'desconhecido', 'justificativa': 'Peças sintéticas na mesma página.'} for d in docs]})
        shutil.copyfile(cls.modelo/'referencias-minuta.json', cls.modelo/'referencias-analise.json')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name).resolve(); self.w = self.pasta/'caso'
        shutil.copytree(self.modelo, self.w)
        self.token = estado.iniciar(self.w)['token']
        self.r = {'schema_version': 1, **contexto(self.w), 'relatorio': 'Relatório inteiramente fictício para teste.',
                  'fundamentos': [{'pedido_id': 'PED-001', 'texto': 'Fundamentação fictícia para teste de estrutura.'}],
                  'dispositivo': [{'pedido_id': 'PED-001', 'resultado': 'parcial', 'texto': 'Proposta fictícia de acolhimento parcial.'}],
                  'questoes_processuais': [{'tema': t, 'texto': 'Proposta fictícia sem efeito jurídico.'} for t in
                                          ['processo', 'honorarios', 'custas', 'gratuidade', 'atualizacao']],
                  'parametros': [], 'pendencias': []}
        self.r['dispositivo_processual'] = copy.deepcopy(self.r['questoes_processuais'])
        self.gravar()

    def gravar(self):
        salvar_json(self.w/'redacao.json', self.r)

    def candidata(self):
        r = preparar(self.w, self.token); self.assertTrue(r['preparada'], r)
        registro = ler_json(self.w, 'referencias-analise.json')
        registro.update(contexto_refs(self.w, 'candidata'))
        registro['revisao_cobertura']['minuta'] = revisao()
        salvar_json(self.w/'referencias-candidata.json', registro)
        return registro

    def revisar(self):
        self.candidata()
        regras = sorted(regras_usadas(ler_json(self.w, 'matriz-pedidos.json')))
        r = {'schema_version': 1, **contexto_revisao(self.w), 'resultado': 'sem-pendencias',
             'verificacoes': [{'item': i, 'estado': 'conferido', 'justificativa': 'Teste fictício de revisão técnica.',
                              'pedido_ids': ['PED-001'], 'regra_ids': regras} for i in sorted(ITENS)],
             'pendencias': [], 'aceite_humano': 'nao-registrado'}
        salvar_json(self.w/'revisao.json', r)
        return r

    def test_ordinario_publicacao_sem_aceite_humano(self):
        self.revisar()
        r = publicar(self.w, self.token); self.assertTrue(r['publicada'], r)
        self.assertEqual(r['aceite_humano'], 'nao-registrado')
        gate = verificar(self.w); self.assertTrue(gate['valido_tecnicamente'], gate)
        self.assertTrue(verificar_refs(self.w)['sem_pendencias'])
        self.assertIn('## Relatório', (self.w/'minuta.md').read_text())
        self.assertEqual((self.w/'minuta.md').read_bytes(), (self.w/'minuta-candidata.md').read_bytes())

    def test_sumarissimo_preserva_relatorio_interno(self):
        pasta = self.pasta/'sumarissimo'; pasta.mkdir()
        self.w, _, _ = criar_com_fontes(pasta, rito='sumarissimo')
        shutil.copyfile(self.modelo/'classificacao.json', self.w/'classificacao.json')
        shutil.copyfile(self.w/'referencias-minuta.json', self.w/'referencias-analise.json')
        self.token = estado.iniciar(self.w)['token']
        self.r.update(contexto(self.w)); self.r['relatorio'] = None; self.gravar()
        self.revisar()
        r = publicar(self.w, self.token); self.assertTrue(r['publicada'], r)
        self.assertNotIn('## Relatório', (self.w/'minuta.md').read_text())
        self.assertTrue((self.w/'pedidos.json').is_file())

    def test_redacao_incompleta_divergente_ou_pendente_bloqueia(self):
        original = copy.deepcopy(self.r)
        for campo, valor in [('fundamentos', []), ('dispositivo', []), ('questoes_processuais', []),
                             ('dispositivo_processual', []), ('relatorio', ' '), ('pendencias', ['Dado ausente']),
                             ('pedidos_sha256', '0'*64), ('numero_cnj', 'outro'),
                             ('parametros', [{'pedido_id': 'PED-001', 'nome': 'juros', 'valor': '1%', 'regra_ids': ['REG-001']}])]:
            with self.subTest(campo=campo):
                self.r = {**original, campo: valor}; self.gravar()
                self.assertFalse(preparar(self.w, self.token)['preparada'])
                self.assertFalse((self.w/'minuta.md').exists())
        self.r = original; self.r['dispositivo'][0]['resultado'] = 'deferimento'; self.gravar()
        self.assertFalse(verificar(self.w, 'redacao')['valido_tecnicamente'])

    def test_falta_revisao_ou_citacao_nao_publica(self):
        self.candidata()
        self.assertFalse(publicar(self.w, self.token)['publicada'])
        self.r['fundamentos'][0]['texto'] += ' Conforme art. 123 da CLT.'; self.gravar()
        self.revisar()
        r = publicar(self.w, self.token); self.assertFalse(r['publicada']); self.assertTrue(r['pendencias'])

    def test_revisao_pendente_e_na_invalido(self):
        original = self.revisar()
        for campo, valor in [('resultado', 'com-pendencias'), ('pendencias', ['Reexaminar pedido']),
                             ('minuta_sha256', '0'*64), ('aceite_humano', 'aprovado')]:
            with self.subTest(campo=campo):
                salvar_json(self.w/'revisao.json', {**original, campo: valor})
                self.assertFalse(publicar(self.w, self.token)['publicada'])
        r = copy.deepcopy(original)
        next(i for i in r['verificacoes'] if i['item'] == 'dispositivo')['estado'] = 'nao-aplicavel'
        salvar_json(self.w/'revisao.json', r)
        self.assertFalse(publicar(self.w, self.token)['publicada'])

    def test_na_motivado_e_regra_correta(self):
        r = self.revisar()
        item = next(i for i in r['verificacoes'] if i['item'] == 'custas')
        item['estado'] = 'nao-aplicavel'; salvar_json(self.w/'revisao.json', r)
        self.assertTrue(verificar(self.w, 'revisao')['valido_tecnicamente'])
        item['justificativa'] = ' '; salvar_json(self.w/'revisao.json', r)
        self.assertFalse(verificar(self.w, 'revisao')['valido_tecnicamente'])
        item['justificativa'] = 'Motivo fictício'; item['regra_ids'] = ['REG-001']; salvar_json(self.w/'revisao.json', r)
        self.assertFalse(verificar(self.w, 'revisao')['valido_tecnicamente'])

    def test_candidata_alterada_sem_redacao_bloqueia(self):
        self.revisar(); (self.w/'minuta-candidata.md').write_text('Outro texto')
        self.assertFalse(publicar(self.w, self.token)['publicada'])

    def test_fonte_alterada_invalida_publicacao(self):
        self.revisar(); self.assertTrue(publicar(self.w, self.token)['publicada'])
        fonte = ler_json(self.w, 'fontes-juridicas.json')['fontes'][0]
        (self.w/fonte['texto']).write_text('Conteúdo adulterado')
        self.assertFalse(verificar(self.w)['valido_tecnicamente'])

    def test_analise_independe_de_minuta_anterior(self):
        (self.w/'minuta.md').write_text('Minuta antiga não validada')
        self.assertTrue(verificar_refs(self.w, 'analise')['sem_pendencias'])
        self.assertFalse(verificar_refs(self.w)['sem_pendencias'])

    def test_falha_ultimo_rename_preserva_publicacao_anterior(self):
        self.revisar(); self.assertTrue(publicar(self.w, self.token)['publicada'])
        antes = {n: (self.w/n).read_bytes() for n in estado.SAIDAS['publicacao']}
        self.r['relatorio'] += ' Complemento.'; self.gravar(); self.revisar()
        real = merge_sentenca_jt.os.replace
        def falhar(origem, destino):
            if Path(destino) == self.w/'minuta.md': raise OSError('Falha sintética')
            return real(origem, destino)
        with patch('merge_sentenca_jt.os.replace', side_effect=falhar), self.assertRaises(OSError):
            publicar(self.w, self.token)
        for n, conteudo in antes.items(): self.assertEqual(conteudo, (self.w/n).read_bytes())
        self.assertFalse(verificar(self.w)['valido_tecnicamente'])
        self.assertFalse(list(self.w.glob('.minuta-*')))

    def test_artefato_symlink_recusado(self):
        self.revisar(); externo = self.pasta/'externo'; externo.write_text('preservar')
        (self.w/'minuta.md').symlink_to(externo)
        with self.assertRaises(ValueError): publicar(self.w, self.token)
        self.assertEqual(externo.read_text(), 'preservar')

    def test_sessao_exclusiva_outro_processo(self):
        r = subprocess.run([sys.executable, str(RAIZ/'scaffold/scripts/estado_execucao.py'), 'iniciar', str(self.w)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2); self.assertIn('residual', r.stderr)
        with self.assertRaises(ValueError): estado.encerrar(self.w, 'token-incorreto')
        self.assertEqual(estado.diagnostico(self.w)['token'], self.token)

    def test_recuperacao_explicita_registrada(self):
        estado.encerrar(self.w, self.token, 'Teste: execução anterior interrompida e diagnosticada.')
        self.assertEqual(len(list(self.pasta.glob('.caso.recuperacao-*.json'))), 1)
        self.assertNotEqual(estado.iniciar(self.w)['token'], self.token)
        self.assertTrue((self.w/'redacao.json').exists())

    def test_limite_duas_tentativas_persiste_entre_sessoes(self):
        # Ingestão inválida consome duas tentativas sem inventar dependências válidas.
        (self.w/'documentos.json').unlink()
        for _ in range(2):
            estado.transicao(self.w, self.token, 'ingestao')
            self.assertEqual(estado.transicao(self.w, self.token, 'ingestao', True)['estado'], 'invalida')
        estado.encerrar(self.w, self.token); self.token = estado.iniciar(self.w)['token']
        with self.assertRaises(ValueError): estado.transicao(self.w, self.token, 'ingestao')

    def test_etapa_interrompida_consumiu_tentativa(self):
        estado.transicao(self.w, self.token, 'ingestao')
        with self.assertRaises(ValueError): estado.transicao(self.w, self.token, 'ingestao')
        estado.encerrar(self.w, self.token, 'Interrupção sintética')
        self.token = estado.iniciar(self.w)['token']
        self.assertEqual(estado.transicao(self.w, self.token, 'ingestao')['tentativas'], 2)
        self.assertEqual(estado.transicao(self.w, self.token, 'ingestao', True)['estado'], 'valida')

    def test_inventario_reutiliza_e_invalida_descendentes(self):
        self.revisar(); self.assertTrue(publicar(self.w, self.token)['publicada'])
        for etapa in estado.ETAPAS:
            estado.transicao(self.w, self.token, etapa)
            r = estado.transicao(self.w, self.token, etapa, True)
            self.assertEqual(r['estado'], 'valida', (etapa, r))
        self.assertIsNone(estado.inventario(self.w, self.token)['proxima'])
        self.assertEqual(estado.transicao(self.w, self.token, 'redacao')['acao'], 'reutilizar')
        self.r['relatorio'] += ' Alteração.'; self.gravar()
        inventario = estado.inventario(self.w, self.token)
        self.assertEqual(inventario['proxima'], 'redacao')
        self.assertTrue(all(i['estado'] != 'valida' for i in inventario['etapas'][7:]))
        self.assertFalse(verificar(self.w)['valido_tecnicamente'])

    def test_assinaturas_insumos_pacote_fontes_e_pdf(self):
        antes = estado.calcular_assinatura_etapa(self.w, 'redacao')
        for nome in ['prompt.md', 'perfil.json', 'script.py', 'template.md']:
            p = self.pasta/nome; p.write_text('versão um')
            with patch('estado_execucao.pacote', return_value=(self.pasta, [nome])):
                assinatura = estado.calcular_assinatura_etapa(self.w, 'redacao')
                p.write_text('versão dois')
                self.assertNotEqual(assinatura, estado.calcular_assinatura_etapa(self.w, 'redacao'))
        pdf = next((self.w/'originais').glob('*.pdf')); pdf.write_bytes(pdf.read_bytes()+b'\n')
        self.assertNotEqual(antes, estado.calcular_assinatura_etapa(self.w, 'redacao'))

    def test_pdf_externo_muda_assinatura_de_ingestao(self):
        entrada = self.pasta/'entrada.pdf'; entrada.write_bytes(b'PDF sintetico')
        caso = self.pasta/'caso.json'; shutil.copyfile(self.w/'caso.json', caso)
        estado.registrar_entrada(self.w, self.token, entrada, caso)
        antes = estado.calcular_assinatura_etapa(self.w, 'ingestao')
        entrada.write_bytes(b'PDF alterado')
        self.assertNotEqual(antes, estado.calcular_assinatura_etapa(self.w, 'ingestao'))
        self.assertTrue(estado.validar_etapa(self.w, 'ingestao')['erros'])

    def test_insumos_alterados_durante_etapa_recusam_conclusao(self):
        estado.transicao(self.w, self.token, 'ingestao')
        # Contexto externo registrado passa a integrar a assinatura da etapa em andamento.
        entrada = self.pasta/'entrada.pdf'; entrada.write_bytes(b'PDF')
        estado.registrar_entrada(self.w, self.token, entrada, self.w/'caso.json')
        with self.assertRaises(ValueError): estado.transicao(self.w, self.token, 'ingestao', True)

    def test_instalacao_isolada_executa_montagem_e_gate(self):
        self.revisar()
        projeto = self.pasta/'instalado'
        r = subprocess.run([sys.executable, str(RAIZ/'scripts/instalar_perfil.py'), '--perfil', 'jt-1g-local',
                            '--destino', str(projeto)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        def executar(script, *args):
            r = subprocess.run([sys.executable, str(projeto/'scripts'/script), *map(str, args)],
                               cwd=projeto, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout+r.stderr)
            return json.loads(r.stdout)
        executar('merge_sentenca_jt.py', self.w, '--token', self.token, '--preparar')
        executar('merge_sentenca_jt.py', self.w, '--token', self.token)
        self.assertTrue(executar('verificar_sentenca_jt.py', self.w, '--gate')['valido_tecnicamente'])
        self.assertEqual([p.name for p in (projeto/'.claude/commands').iterdir()], ['pipeline-sentenca-trabalhista.md'])

    def test_mudanca_durante_publicacao_nao_substitui_minuta(self):
        self.revisar()
        with patch('merge_sentenca_jt.assinatura_publicacao', side_effect=['antes', 'depois']):
            with self.assertRaises(ValueError): publicar(self.w, self.token)
        self.assertFalse((self.w/'minuta.md').exists())

    def test_duas_operacoes_mesma_sessao_nao_correm_juntas(self):
        with estado.operacao(self.w, self.token):
            r = subprocess.run([sys.executable, str(RAIZ/'scaffold/scripts/estado_execucao.py'),
                                'inventario', str(self.w), '--token', self.token], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn('Outra operação', r.stderr)


    def test_classificacao_invalida_nao_bloqueia_reparo_da_propria_etapa(self):
        estado.transicao(self.w, self.token, 'ingestao')
        self.assertEqual(estado.transicao(self.w, self.token, 'ingestao', True)['estado'], 'valida')
        salvar_json(self.w/'classificacao.json', {'schema_version': 1, 'segmentos': []})
        self.assertEqual(estado.inventario(self.w, self.token)['proxima'], 'classificacao')
        self.assertEqual(estado.transicao(self.w, self.token, 'classificacao')['estado'], 'executando')
        self.assertEqual(estado.transicao(self.w, self.token, 'classificacao', True)['estado'], 'invalida')


    def test_publicacao_recebida_nao_e_aprovacao(self):
        self.revisar(); publicar(self.w, self.token)
        r = ler_json(self.w, 'publicacao.json'); r['aceite_humano'] = 'aprovado'; salvar_json(self.w/'publicacao.json', r)
        self.assertFalse(verificar(self.w)['valido_tecnicamente'])

if __name__ == '__main__': unittest.main()
