"""Fontes e citações fictícias; nenhuma consulta a tribunal ou regra jurídica real."""
import copy
from datetime import date, timedelta
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
from caso_trabalhista import criar, gravar
from documentos import hash_arquivo, salvar_json
from fontes_jt import carregar_fonte, conferir_corpus, caminho_fonte, validar_metadados
from importar_fontes_jt import importar, confirmar
from merge_fontes_jt import consolidar
from verificar_referencias_jt import contexto, verificar
from normalizacao_fontes import normalizar_chave
import merge_fontes


def meta(tipo='precedente', orgao='TST', referencia='Referência inteiramente fictícia'):
    return {'origem': 'arquivo-oficial-local', 'tipo': tipo, 'orgao': orgao, 'referencia': referencia,
            'url_oficial': 'https://www.tst.jus.br/', 'data_consulta': date.today().isoformat(),
            'situacao': 'vigente', 'modalidade': 'tese-firmada' if tipo == 'precedente' else 'legislacao',
            'temas': ['jornada'], 'ambito': {'nivel': 'nacional', 'trt': None, 'categoria': None, 'territorio': None},
            'vigencia': {'inicio': '2025-01-01', 'fim': None}, 'contexto_temporal': 'SOMENTE TESTE, SEM VALOR JURIDICO.'}


def conferencia(fonte):
    return {'responsavel': 'Pessoa fictícia de teste', 'data': date.today().isoformat(),
            'valida_ate': (date.today()+timedelta(days=30)).isoformat(),
            'original_sha256': fonte['sha256'], 'texto_sha256': fonte['texto_sha256'],
            'metadados_sha256': fonte['metadados_sha256'], 'declaracao_origem_oficial': True}


def revisao():
    return {'estado': 'conferida', 'responsavel': 'Revisor fictício', 'data': date.today().isoformat(),
            'justificativa': 'Teste sintético de estrutura e vínculos; não é avaliação jurídica.'}


class FontesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.base.cleanup)
        pasta = Path(cls.base.name).resolve()
        workspace, rel, tri, regras, matriz = criar(pasta)
        cls.ids, vinculos = [], []
        for i, regra in enumerate(regras['regras']):
            entrada = pasta/f'fonte-{i}.txt'
            entrada.write_text(regra['texto'], encoding='utf-8')
            metadata = meta('legislacao', regra['orgao'], regra['referencia']+str(i))
            metadata['temas'] = [regra['tema']]
            ident = importar(workspace, entrada, metadata)['id']
            fonte = carregar_fonte(workspace, ident)
            confirmar(workspace, ident, conferencia(fonte))
            cls.ids.append(ident)
            regra.update(arquivo=fonte['texto'], sha256=fonte['texto_sha256'], url_oficial=metadata['url_oficial'])
            vinculos.append({'regra_id': regra['id'], 'fonte_id': ident, 'revisao_pertinencia': revisao()})
        gravar(workspace, rel, tri, regras, matriz)
        consolidar(workspace, cls.ids)
        cls.modelo = workspace
        cls.registro = {'schema_version': 1, **contexto(workspace), 'vinculos_regras': vinculos,
                        'referencias': [], 'revisao_cobertura': {'matriz': revisao(), 'minuta': None}}
        salvar_json(workspace/'referencias-minuta.json', cls.registro)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name).resolve()
        self.workspace = self.pasta/'caso'
        shutil.copytree(self.modelo, self.workspace)
        self.registro = copy.deepcopy(self.__class__.registro)

    def gravar_registro(self):
        self.registro.update(contexto(self.workspace))
        salvar_json(self.workspace/'referencias-minuta.json', self.registro)

    def adicionar_fonte(self, texto='TEXTO OFICIAL INTEIRAMENTE FICTICIO. Não é devido.', metadata=None, extensao='txt', confirmar_fonte=True):
        entrada = self.pasta / ('fonte.'+extensao)
        entrada.write_text(texto, encoding='utf-8')
        resultado = importar(self.workspace, entrada, metadata or meta())
        fonte = carregar_fonte(self.workspace, resultado['id'])
        if confirmar_fonte:
            confirmar(self.workspace, fonte['id'], conferencia(fonte))
        return carregar_fonte(self.workspace, fonte['id'])

    def minuta(self, texto):
        (self.workspace/'minuta.md').write_text(texto, encoding='utf-8')
        self.registro['revisao_cobertura']['minuta'] = revisao()

    def citar(self, fonte, trecho, origem=None, uso='direta', inicio=None):
        texto = (self.workspace/'minuta.md').read_text(encoding='utf-8')
        inicio = texto.index(trecho) if inicio is None else inicio
        citacao = {'id': f'CIT-{len(self.registro["referencias"])+1:03d}', 'alvo': 'minuta', 'ponteiro': '',
                   'inicio': inicio, 'fim': inicio+len(trecho), 'trecho': trecho, 'tipo_uso': uso,
                   'natureza': 'fonte', 'fonte_id': fonte['id'], 'documento_id': None, 'pagina': None,
                   'trecho_origem': origem or trecho, 'revisao_pertinencia': revisao()}
        self.registro['referencias'].append(citacao)
        return citacao

    def publicar(self, fonte):
        self.assertTrue(consolidar(self.workspace, self.ids+[fonte['id']])['publicado'])

    def test_corpus_conferido_e_regras_da_matriz(self):
        resultado = verificar(self.workspace)
        self.assertTrue(resultado['sem_pendencias'], resultado)
        self.assertFalse(resultado['apto_para_minuta'])

    def test_importacao_pendente_e_repeticao_idempotente(self):
        fonte = self.adicionar_fonte(confirmar_fonte=False)
        self.assertIsNone(fonte['conferencia'])
        antes = (self.workspace/caminho_fonte(fonte['id'])).stat().st_mtime_ns
        self.assertFalse(consolidar(self.workspace, [fonte['id']])['publicado'])
        resultado = importar(self.workspace, self.pasta/'fonte.txt', fonte['metadados'])
        self.assertTrue(resultado['reutilizada'])
        self.assertEqual(antes, (self.workspace/caminho_fonte(fonte['id'])).stat().st_mtime_ns)

    def test_conferencia_exige_tres_hashes_e_declaracao(self):
        fonte = self.adicionar_fonte(confirmar_fonte=False)
        for campo in ('original_sha256', 'texto_sha256', 'metadados_sha256'):
            dados = conferencia(fonte); dados[campo] = '0'*64
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                confirmar(self.workspace, fonte['id'], dados)
        dados = conferencia(fonte); dados['declaracao_origem_oficial'] = False
        with self.assertRaises(ValueError): confirmar(self.workspace, fonte['id'], dados)

    def test_origem_tst_trt_e_dominio_enganoso(self):
        metadata = meta(orgao='TRT12')
        metadata.update(url_oficial='https://portal.trt12.jus.br/documento')
        metadata['ambito'].update(nivel='regional', trt=12)
        fonte = self.adicionar_fonte(metadata=metadata)
        self.publicar(fonte)
        for url in ['https://tst.jus.br.exemplo.com/', 'http://www.tst.jus.br/', 'https://usuario@www.tst.jus.br/', 'https://www.trt2.jus.br/']:
            invalida = meta(); invalida['url_oficial'] = url
            with self.subTest(url=url), self.assertRaises(ValueError): validar_metadados(invalida)

    def test_trt_diferente_do_caso_bloqueia_publicacao(self):
        metadata = meta(orgao='TRT2'); metadata['url_oficial'] = 'https://www.trt2.jus.br/'
        metadata['ambito'].update(nivel='regional', trt=2)
        fonte = self.adicionar_fonte(metadata=metadata)
        self.assertFalse(consolidar(self.workspace, [fonte['id']])['publicado'])

    def test_tema_afetado_suspenso_e_status_incerto_nao_sao_tese_firmada(self):
        for campo, valor in [('modalidade', 'tema-afetado'), ('modalidade', 'tema-suspenso'),
                             ('situacao', 'incerta'), ('situacao', 'vencida'), ('situacao', 'revogada')]:
            metadata = meta(); metadata[campo] = valor
            fonte = self.adicionar_fonte(metadata=metadata)
            with self.subTest(campo=campo, valor=valor):
                self.assertFalse(consolidar(self.workspace, [fonte['id']])['publicado'])

    def test_conferencia_vencida_detectada_em_corpus_previamente_publicado(self):
        fonte = carregar_fonte(self.workspace, self.ids[0])
        futuro = date.today()+timedelta(days=31)
        with patch('fontes_jt.date') as calendario:
            calendario.today.return_value = futuro
            _, erros, pendencias = conferir_corpus(self.workspace)
        self.assertEqual(erros, [])
        self.assertTrue(any('vencida' in p for p in pendencias))

    def test_html_remove_scripts_preserva_texto_e_original(self):
        html = '<html><head><title>ignorar</title></head><body><p>Texto &amp; fonte.</p><script>ignorar()</script><p>Outra linha.</p></body></html>'
        fonte = self.adicionar_fonte(html, extensao='html')
        self.assertEqual((self.workspace/fonte['original']).read_text(), html)
        texto = (self.workspace/fonte['texto']).read_text()
        self.assertIn('Texto & fonte.', texto)
        self.assertIn('Outra linha.', texto)
        self.assertNotIn('ignorar', texto)
        self.assertIsNone(fonte['paginas_total'])

    def test_pdf_preserva_pagina_e_bloqueia_protegido(self):
        for nome in ('digital.pdf', 'protegido.pdf'):
            fonte = importar(self.workspace, RAIZ/'tests/fixtures/jt'/nome, meta())
            dados = carregar_fonte(self.workspace, fonte['id'])
            if nome == 'digital.pdf':
                self.assertEqual(dados['paginas_total'], 1)
                self.assertEqual(dados['paginas'][0]['numero'], 1)
                confirmar(self.workspace, dados['id'], conferencia(dados))
                self.assertTrue(consolidar(self.workspace, [dados['id']])['publicado'])
            else:
                self.assertEqual(dados['estado'], 'protegido')
                self.assertFalse(consolidar(self.workspace, [dados['id']])['publicado'])

    def test_arquivo_dos_autos_nao_pode_virar_jurisprudencia(self):
        doc = json.loads((self.workspace/'documentos.json').read_text())['documentos'][0]
        copia = self.pasta/'peticao-renomeada.pdf'
        shutil.copyfile(self.workspace/doc['original'], copia)
        with self.assertRaisesRegex(ValueError, 'autos'):
            importar(self.workspace, copia, meta())

    def test_merge_deduplica_ids_e_preserva_consolidado_em_falha(self):
        antes = (self.workspace/'fontes-juridicas.json').read_bytes()
        mtime = (self.workspace/'fontes-juridicas.json').stat().st_mtime_ns
        self.assertTrue(consolidar(self.workspace, self.ids*2)['publicado'])
        self.assertEqual(mtime, (self.workspace/'fontes-juridicas.json').stat().st_mtime_ns)
        fonte = self.adicionar_fonte(confirmar_fonte=False)
        self.assertFalse(consolidar(self.workspace, self.ids+[fonte['id']])['publicado'])
        self.assertEqual(antes, (self.workspace/'fontes-juridicas.json').read_bytes())
        with patch('merge_fontes_jt.salvar_json', side_effect=OSError('Falha simulada')):
            with self.assertRaises(OSError): consolidar(self.workspace, self.ids[:1])
        self.assertEqual(antes, (self.workspace/'fontes-juridicas.json').read_bytes())

    def test_versoes_com_metadados_diferentes_exigem_selecao(self):
        fonte = self.adicionar_fonte()
        metadata = copy.deepcopy(fonte['metadados']); metadata['contexto_temporal'] += ' Nova revisão.'
        outra = self.adicionar_fonte(metadata=metadata)
        self.assertNotEqual(fonte['id'], outra['id'])
        self.assertFalse(consolidar(self.workspace, [fonte['id'], outra['id']])['publicado'])

    def test_original_texto_metadados_e_corpus_adulterados(self):
        fonte = carregar_fonte(self.workspace, self.ids[0])
        for campo in ['original', 'texto']:
            caminho = self.workspace/fonte[campo]; antes = caminho.read_bytes()
            caminho.write_bytes(antes+b'alterado')
            self.assertTrue(conferir_corpus(self.workspace)[1])
            caminho.write_bytes(antes)
        fonte['metadados']['referencia'] = 'Outra referência'
        corpus = json.loads((self.workspace/'fontes-juridicas.json').read_text()); corpus['fontes'][0] = fonte
        salvar_json(self.workspace/'fontes-juridicas.json', corpus)
        self.assertTrue(conferir_corpus(self.workspace)[1])

    def test_renovacao_da_conferencia_invalida_corpus_antigo(self):
        fonte = carregar_fonte(self.workspace, self.ids[0]); nova = conferencia(fonte)
        nova['responsavel'] = 'Outro responsável fictício'
        confirmar(self.workspace, fonte['id'], nova)
        self.assertTrue(conferir_corpus(self.workspace)[1])

    def test_corpus_vazio_impede_aprovacao(self):
        salvar_json(self.workspace/'fontes-juridicas.json', {'schema_version': 1, 'numero_cnj': self.registro['numero_cnj'], 'fontes': []})
        self.gravar_registro()
        resultado = verificar(self.workspace)
        self.assertFalse(resultado['sem_pendencias'])
        self.assertTrue(any('vazio' in p for p in resultado['pendencias']))

    def test_citacao_direta_curta_com_aspas_e_sem_aspas(self):
        fonte = self.adicionar_fonte(); self.publicar(fonte)
        for texto in ['“Não é devido.”', 'Não é devido.', '> Não é devido.']:
            self.minuta(texto); self.registro['referencias'] = []
            self.citar(fonte, 'Não é devido.'); self.gravar_registro()
            r = verificar(self.workspace)
            self.assertTrue(r['sem_pendencias'], r)

    def test_citacao_direta_nao_ignora_negacao_acento_caixa(self):
        fonte = self.adicionar_fonte(); self.publicar(fonte)
        self.minuta('“É devido.”')
        self.citar(fonte, 'É devido.', origem='Não é devido.'); self.gravar_registro()
        self.assertTrue(verificar(self.workspace)['erros'])

    def test_citacao_sem_aspas_nao_registrada_detectada_por_conteudo(self):
        trecho = 'Esta passagem fictícia contém mais de oito palavras para detectar reprodução literal sem aspas.'
        fonte = self.adicionar_fonte(trecho); self.publicar(fonte)
        self.minuta(trecho); self.gravar_registro()
        r = verificar(self.workspace)
        self.assertTrue(any('sem registro' in p for p in r['pendencias']))

    def test_legislacao_mencionada_sem_registro(self):
        self.minuta('Aplica-se o art. 818 da CLT, segundo a tese referida.'); self.gravar_registro()
        self.assertTrue(any('sem registro' in p for p in verificar(self.workspace)['pendencias']))

    def test_parafrase_exige_revisao_de_pertinencia(self):
        fonte = self.adicionar_fonte(); self.publicar(fonte)
        self.minuta('A hipótese afasta a parcela.')
        c = self.citar(fonte, 'A hipótese afasta a parcela.', origem='Não é devido.', uso='parafrase')
        c['revisao_pertinencia'].update(estado='pendente', responsavel=None, data=None)
        self.gravar_registro()
        self.assertFalse(verificar(self.workspace)['sem_pendencias'])
        c['revisao_pertinencia'] = revisao(); self.gravar_registro()
        self.assertTrue(verificar(self.workspace)['sem_pendencias'])

    def test_ponteiro_posicao_e_pagina_inexistentes(self):
        fonte = self.adicionar_fonte(); self.publicar(fonte)
        self.minuta('Não é devido.'); c = self.citar(fonte, 'Não é devido.')
        for campo, valor in [('inicio', 1), ('ponteiro', '/inexistente'), ('pagina', 2), ('fonte_id', 'FON-'+'0'*64)]:
            original = c[campo]; c[campo] = valor; self.gravar_registro()
            with self.subTest(campo=campo): self.assertTrue(verificar(self.workspace)['erros'])
            c[campo] = original

    def test_regra_sem_vinculo_ou_com_fonte_errada(self):
        self.registro['vinculos_regras'].pop(); self.gravar_registro()
        self.assertTrue(verificar(self.workspace)['erros'])
        self.registro = copy.deepcopy(self.__class__.registro)
        self.registro['vinculos_regras'][0]['fonte_id'] = self.ids[1]; self.gravar_registro()
        self.assertTrue(verificar(self.workspace)['erros'])

    def test_citacao_na_matriz_com_ponteiro_json(self):
        fonte = self.adicionar_fonte(); self.publicar(fonte)
        matriz = json.loads((self.workspace/'matriz-pedidos.json').read_text())
        matriz['analises'][0]['conclusao']['fundamentacao'] = '“Não é devido.”'
        salvar_json(self.workspace/'matriz-pedidos.json', matriz)
        self.minuta('Não é devido.'); c = self.citar(fonte, 'Não é devido.')
        c.update(alvo='matriz', ponteiro='/analises/0/conclusao/fundamentacao', inicio=1, fim=14)
        (self.workspace/'minuta.md').unlink(); self.registro['revisao_cobertura']['minuta'] = None
        self.gravar_registro()
        self.assertTrue(verificar(self.workspace)['sem_pendencias'], verificar(self.workspace))

    def test_jurisprudencia_nos_autos_e_relato_de_alegacao(self):
        doc = json.loads((self.workspace/'documentos.json').read_text())['documentos'][0]
        self.minuta('A parte cita a Súmula fictícia do TST.')
        c = {'id': 'CIT-001', 'alvo': 'minuta', 'ponteiro': '', 'inicio': 0, 'fim': 36,
             'trecho': 'A parte cita a Súmula fictícia do TST.', 'tipo_uso': 'parafrase', 'natureza': 'prova',
             'fonte_id': None, 'documento_id': doc['id'], 'pagina': 1,
             'trecho_origem': 'CASO INTEIRAMENTE FICTICIO - SEM VALOR JURIDICO', 'revisao_pertinencia': revisao()}
        c['fim'] = len(c['trecho']); self.registro['referencias'] = [c]; self.gravar_registro()
        self.assertTrue(any('não substitui' in p for p in verificar(self.workspace)['pendencias']))
        c['tipo_uso'] = 'relato-alegacao'; self.gravar_registro()
        self.assertTrue(verificar(self.workspace)['sem_pendencias'])

    def test_dispensa_requer_revisao_e_nao_apaga_mencao_juridica(self):
        self.minuta('“expressão comum”')
        c = {'id': 'CIT-001', 'alvo': 'minuta', 'ponteiro': '', 'inicio': 1, 'fim': 16,
             'trecho': 'expressão comum', 'tipo_uso': 'nao-citacao', 'natureza': 'nenhuma',
             'fonte_id': None, 'documento_id': None, 'pagina': None, 'trecho_origem': None,
             'revisao_pertinencia': revisao()}
        self.registro['referencias'] = [c]; self.gravar_registro()
        self.assertTrue(verificar(self.workspace)['sem_pendencias'])
        self.minuta('CLT'); c.update(inicio=0, fim=3, trecho='CLT'); self.gravar_registro()
        self.assertFalse(verificar(self.workspace)['sem_pendencias'])

    def test_hash_da_minuta_e_cobertura_pendente(self):
        self.minuta('Texto fictício sem citações.'); self.gravar_registro()
        (self.workspace/'minuta.md').write_text('Texto alterado.')
        self.assertTrue(verificar(self.workspace)['erros'])
        self.gravar_registro(); self.registro['revisao_cobertura']['minuta'] = None; self.gravar_registro()
        self.assertFalse(verificar(self.workspace)['sem_pendencias'])

    def test_normalizacao_compartilhada_preserva_contrato_legado(self):
        for texto in ['AÇÃO   RESCISÓRIA', '  órgão\nJulgador ', 'Tema 1']:
            self.assertEqual(normalizar_chave(texto), merge_fontes._norm(texto))
        self.assertEqual(normalizar_chave('AÇÃO   RESCISÓRIA'), 'acao rescisoria')
        self.assertTrue(merge_fontes.validar_item({'origem_mcp': 'julia-trf5', 'tribunal': 'TRF5', 'tipo': 'acordao',
                                                 'referencia': 'teste', 'campo': 'ementa', 'trecho_verbatim': 'teste'})[0])

    def test_merge_legado_standalone_mantem_saida_e_deduplicacao(self):
        script = self.pasta/'merge_fontes.py'
        shutil.copyfile(RAIZ/'scaffold/scripts/merge_fontes.py', script)
        pasta = self.pasta/'legado'; pasta.mkdir()
        item = {'origem_mcp': 'julia-trf5', 'tribunal': 'TRF5', 'tipo': 'acordao',
                'referencia': 'Teste', 'campo': 'ementa', 'trecho_verbatim': 'AÇÃO fictícia'}
        salvar_json(pasta/'fontes-teste.json', [item, {**item, 'trecho_verbatim': 'acao  FICTICIA'}])
        r = subprocess.run([sys.executable, '-S', str(script), str(pasta), '--id', 'teste'], cwd=self.pasta, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        saida = json.loads((pasta/'teste-fontes.json').read_text())
        self.assertEqual(len(saida['fontes']), 1)
        self.assertEqual(saida['fontes'][0]['id'], 'JULIA-001')

    def test_stf_e_norma_coletiva_tipados(self):
        metadata = meta(orgao='STF'); metadata['url_oficial'] = 'https://portal.stf.jus.br/'
        fonte = self.adicionar_fonte(metadata=metadata)
        self.assertTrue(consolidar(self.workspace, [fonte['id']])['publicado'])
        metadata = meta(tipo='norma-coletiva', orgao='MTE')
        metadata.update(modalidade='instrumento-coletivo', url_oficial='https://www.gov.br/trabalho-e-emprego/')
        metadata['ambito'].update(nivel='coletivo', trt=12, categoria='comercio', territorio='Florianopolis')
        fonte = self.adicionar_fonte(metadata=metadata)
        self.assertTrue(consolidar(self.workspace, [fonte['id']])['publicado'])
        metadata['ambito']['categoria'] = None
        with self.assertRaises(ValueError): validar_metadados(metadata)

    def test_citacao_de_fonte_pdf_exige_pagina_fisica(self):
        ident = importar(self.workspace, RAIZ/'tests/fixtures/jt/digital.pdf', meta())['id']
        fonte = carregar_fonte(self.workspace, ident)
        confirmar(self.workspace, ident, conferencia(fonte)); self.publicar(fonte)
        trecho = 'CONTROLE DE JORNADA'
        self.minuta('“'+trecho+'”'); c = self.citar(fonte, trecho); c['pagina'] = 1
        self.gravar_registro()
        self.assertTrue(verificar(self.workspace)['sem_pendencias'])
        c['pagina'] = None; self.gravar_registro()
        self.assertTrue(verificar(self.workspace)['erros'])

    def test_citacoes_sobrepostas_e_revisao_de_cobertura_pendente(self):
        fonte = self.adicionar_fonte(); self.publicar(fonte)
        self.minuta('Não é devido.'); c = self.citar(fonte, 'Não é devido.')
        self.registro['referencias'].append({**c, 'id': 'CIT-002'})
        self.gravar_registro()
        self.assertTrue(verificar(self.workspace)['erros'])
        self.registro['referencias'].pop()
        self.registro['revisao_cobertura']['matriz'].update(estado='pendente', responsavel=None, data=None)
        self.gravar_registro()
        self.assertFalse(verificar(self.workspace)['sem_pendencias'])

    def test_cli_importacao_conferencia_e_merge_instalados(self):
        instalado = self.pasta/'instalado'
        subprocess.run([sys.executable, str(RAIZ/'scripts/instalar_perfil.py'), '--perfil', 'jt-1g-local',
                        '--destino', str(instalado)], check=True, capture_output=True)
        entrada = self.pasta/'oficial.txt'; entrada.write_text('FONTE INTEIRAMENTE FICTICIA.')
        metadata = self.pasta/'metadata.json'; salvar_json(metadata, meta())
        script = instalado/'scripts/importar_fontes_jt.py'
        r = subprocess.run([sys.executable, str(script), str(self.workspace), '--input', str(entrada),
                            '--metadados', str(metadata)], cwd=self.pasta, capture_output=True)
        self.assertEqual(r.returncode, 1, r.stderr)
        ident = json.loads(r.stdout)['id']; fonte = carregar_fonte(self.workspace, ident)
        confirmacao = self.pasta/'confirmacao.json'; salvar_json(confirmacao, conferencia(fonte))
        r = subprocess.run([sys.executable, str(script), str(self.workspace), '--fonte', ident,
                            '--conferencia', str(confirmacao)], cwd=self.pasta, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = subprocess.run([sys.executable, str(instalado/'scripts/merge_fontes_jt.py'), str(self.workspace),
                            '--fontes', ident], cwd=self.pasta, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_lock_links_e_falha_sem_publicacao_parcial(self):
        lock = self.workspace/'fontes/.fontes.lock'; lock.touch()
        with self.assertRaises(ValueError): consolidar(self.workspace, self.ids)
        lock.unlink()
        fonte = carregar_fonte(self.workspace, self.ids[0]); original = self.workspace/fonte['original']
        original.unlink(); original.symlink_to(self.workspace/fonte['texto'])
        with self.assertRaises(ValueError): conferir_corpus(self.workspace)

    def test_instalacao_cli_e_codigos(self):
        instalado = self.pasta/'instalado'
        r = subprocess.run([sys.executable, str(RAIZ/'scripts/instalar_perfil.py'), '--perfil', 'jt-1g-local', '--destino', str(instalado)], capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        cmd = [sys.executable, str(instalado/'scripts/verificar_referencias_jt.py'), str(self.workspace)]
        self.assertEqual(subprocess.run(cmd+['--gate'], cwd=self.pasta, capture_output=True).returncode, 0)
        self.minuta('CLT'); self.gravar_registro()
        self.assertEqual(subprocess.run(cmd, cwd=self.pasta, capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(cmd+['--gate'], cwd=self.pasta, capture_output=True).returncode, 1)
        (self.workspace/'referencias-minuta.json').write_text('{}')
        self.assertEqual(subprocess.run(cmd+['--gate'], cwd=self.pasta, capture_output=True).returncode, 2)


if __name__ == '__main__': unittest.main()
