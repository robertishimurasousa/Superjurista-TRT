"""Contratos de ingestão e casos sintéticos; nenhum acesso a tribunais ou IA."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'scaffold/scripts'))
from cnj import validar_cnj
from documentos import hash_arquivo, salvar_json, validar_caso
from ingerir_documentos import conversor_jt, ingerir
from verificar_documentos import verificar

FIXTURES = RAIZ / 'tests/fixtures/jt'


class Ingestao(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name).resolve()
        self.entrada = self.pasta / 'entrada'
        self.entrada.mkdir()
        self.workspace = self.pasta / 'caso'
        self.metadata = self.pasta / 'caso.json'
        self.caso = json.loads((FIXTURES / 'caso.json').read_text())
        self.gravar_caso()

    def gravar_caso(self):
        salvar_json(self.metadata, self.caso)

    def copiar(self, nome='digital.pdf', destino=None):
        alvo = self.entrada / (destino or nome)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURES / nome, alvo)
        return alvo

    def ingerir(self, entrada=None):
        return ingerir(entrada or self.entrada, self.workspace, self.metadata)

    def indice(self):
        return json.loads((self.workspace / 'documentos.json').read_text())

    def test_cnj_valido_e_digitos_segmento_regiao_invalidos(self):
        numero = self.caso['numero_cnj']
        self.assertEqual(validar_cnj(numero, 12)['unidade_codigo'], '0001')
        for invalido in (numero[:8]+'00'+numero[10:],
                         numero.replace('.5.', '.4.'), numero.replace('.12.', '.25.'),
                         numero.replace('.0001', '.0000'), numero + '\n', 123):
            with self.subTest(numero=invalido), self.assertRaises(ValueError):
                validar_cnj(invalido)
        with self.assertRaises(ValueError):
            validar_cnj(numero, 1)

    def test_metadados_incoerentes_e_nao_confirmados(self):
        for campo, valor in [('trt', 1), ('unidade_codigo', '0002'), ('instancia', 2),
                             ('escopo_confirmado', False), ('rito', 'outro'),
                             ('data_referencia', '2026-02-30'), ('fase', 'execucao')]:
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                validar_caso({**self.caso, campo: valor})

    def test_digital_preserva_original_linhas_e_referencias(self):
        origem = self.copiar()
        resultado = self.ingerir(origem)
        self.assertTrue(resultado['apto_tecnicamente'])
        doc = self.indice()['documentos'][0]
        self.assertEqual(doc['id'], 'DOC-' + hash_arquivo(origem))
        self.assertEqual((self.workspace / doc['original']).read_bytes(), origem.read_bytes())
        self.assertEqual(doc['tipo'], 'jornada')
        p = doc['paginas'][0]
        for tipo in ['bruto', 'normalizado']:
            texto = (self.workspace / p['texto_' + tipo]).read_text()
            self.assertEqual(texto.count('08:00 12:00 13:00 17:00'), 8)
        self.assertEqual(p['numero'], 1)
        self.assertEqual(p['metodo'], 'digital')

    def test_repeticao_idempotente_e_duplicata_por_hash(self):
        self.copiar()
        self.copiar(destino='copia.pdf')
        self.assertTrue(self.ingerir()['apto_tecnicamente'])
        self.assertEqual(len(self.indice()['documentos']), 1)
        antes = {p.relative_to(self.workspace): (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.workspace.rglob('*') if p.is_file()}
        self.ingerir()
        depois = {p.relative_to(self.workspace): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.workspace.rglob('*') if p.is_file()}
        self.assertEqual(antes, depois)

    def test_documento_ausente_e_acrescimo_posterior(self):
        self.caso['documentos'].append({'arquivo': 'pasta/segundo.pdf', 'tipo': 'desconhecido', 'obrigatorio': True})
        self.gravar_caso()
        self.copiar()
        self.assertFalse(self.ingerir()['apto_tecnicamente'])
        # Outro PDF digital, com bytes distintos e sem OCR.
        from reportlab.pdfgen import canvas
        novo = self.entrada / 'pasta/segundo.pdf'
        novo.parent.mkdir()
        c = canvas.Canvas(str(novo)); c.drawString(50, 750, 'OUTRO DOCUMENTO FICTICIO'); c.save()
        self.assertTrue(self.ingerir()['apto_tecnicamente'])
        self.assertEqual(len(self.indice()['documentos']), 2)

    def test_substituicao_da_entrada_recusada_sem_alteracao(self):
        original = self.copiar()
        self.ingerir()
        antes = (self.workspace / 'documentos.json').read_bytes()
        original.write_bytes(b'%PDF-modificado')
        with self.assertRaisesRegex(ValueError, 'mudou de conteúdo'):
            self.ingerir()
        self.assertEqual(antes, (self.workspace / 'documentos.json').read_bytes())
        self.assertTrue(verificar(self.workspace)['apto_tecnicamente'])

    def test_entrada_vazia_nao_cria_workspace(self):
        with self.assertRaisesRegex(ValueError, 'Nenhum PDF'):
            self.ingerir()
        self.assertFalse(self.workspace.exists())

    def test_symlink_e_traversal_recusados(self):
        origem = self.copiar()
        (self.entrada / 'link.pdf').symlink_to(origem)
        with self.assertRaises(ValueError):
            self.ingerir()
        self.caso['documentos'][0]['arquivo'] = '../fora.pdf'
        with self.assertRaises(ValueError):
            validar_caso(self.caso)

    def test_pasta_de_saida_nao_pode_ser_entrada(self):
        self.copiar()
        with self.assertRaises(ValueError):
            ingerir(self.entrada, self.entrada / 'saida', self.metadata)

    def test_protegido_e_corrompido_preservados_com_pendencias(self):
        for nome in ('protegido.pdf', 'corrompido.pdf'):
            self.copiar(nome)
        resultado = self.ingerir()
        self.assertFalse(resultado['apto_tecnicamente'])
        self.assertEqual(resultado['erros'], [])
        self.assertEqual({d['estado'] for d in self.indice()['documentos']}, {'protegido', 'corrompido'})
        for doc in self.indice()['documentos']:
            self.assertTrue((self.workspace / doc['original']).exists())
            self.assertEqual(doc['paginas'], [])

    def test_ocr_falha_registra_pagina_sem_omitir(self):
        self.copiar('misto.pdf')
        conversor = conversor_jt()
        with patch.object(conversor, 'ocr_pagina_jt', side_effect=RuntimeError('OCR indisponível')):
            with patch('ingerir_documentos.conversor_jt', return_value=conversor):
                resultado = self.ingerir()
        doc = self.indice()['documentos'][0]
        self.assertEqual(doc['paginas_total'], 2)
        self.assertEqual([p['estado'] for p in doc['paginas']], ['extraida', 'falha'])
        self.assertFalse(resultado['apto_tecnicamente'])
        self.assertEqual(resultado['erros'], [])

    def test_pdf_sem_paginas_registra_bloqueio_e_permite_acrescimo(self):
        from pypdf import PdfWriter
        PdfWriter().write(self.entrada / 'sem-paginas.pdf')
        resultado = self.ingerir()
        self.assertFalse(resultado['apto_tecnicamente'])
        self.assertEqual(resultado['erros'], [])
        self.copiar()
        resultado = self.ingerir()
        self.assertEqual(resultado['erros'], [])
        self.assertEqual(len(self.indice()['documentos']), 2)

    def test_pagina_vazia_registrada(self):
        self.copiar('vazio.pdf')
        conversor = conversor_jt()
        with patch.object(conversor, 'ocr_pagina_jt', return_value=''):
            with patch('ingerir_documentos.conversor_jt', return_value=conversor):
                self.ingerir()
        doc = self.indice()['documentos'][0]
        self.assertEqual(doc['paginas_total'], 1)
        self.assertEqual(doc['paginas'][0]['estado'], 'vazia-ou-ilegivel')

    def test_imagem_pequena_com_texto_digital_tambem_exige_ocr(self):
        self.copiar('hibrido.pdf')
        conversor = conversor_jt()
        with patch.object(conversor, 'ocr_pagina_jt', return_value='CONTEUDO DA IMAGEM') as ocr:
            with patch('ingerir_documentos.conversor_jt', return_value=conversor):
                self.ingerir()
        ocr.assert_called_once()
        pagina = self.indice()['documentos'][0]['paginas'][0]
        self.assertEqual(pagina['metodo'], 'digital+ocr')
        texto = (self.workspace / pagina['texto_bruto']).read_text()
        self.assertIn('CABECALHO DIGITAL', texto)
        self.assertIn('CONTEUDO DA IMAGEM', texto)

    def test_duplicata_com_metadados_conflitantes_aborta_lote(self):
        self.copiar()
        self.copiar(destino='copia.pdf')
        self.caso['documentos'].append({'arquivo': 'copia.pdf', 'tipo': 'ata', 'obrigatorio': True})
        self.gravar_caso()
        with self.assertRaisesRegex(ValueError, 'conflitante'):
            self.ingerir()
        self.assertFalse(self.workspace.exists())

    def test_caminho_no_indice_nao_pode_escapar_da_pasta(self):
        self.copiar()
        self.ingerir()
        indice = self.indice()
        indice['documentos'][0]['original'] = '../externo.pdf'
        salvar_json(self.workspace / 'documentos.json', indice)
        with self.assertRaises(ValueError):
            verificar(self.workspace)

    def test_cli_modo_preservacao_e_codigos_de_pendencia(self):
        script = RAIZ / 'scaffold/skills/converter-pdf/scripts/pdf_para_txt.py'
        saida = self.pasta / 'convertido'
        cmd = [sys.executable, str(script), '--input', str(self.copiar()),
               '--output', str(saida), '--preservar-jt']
        r = subprocess.run(cmd, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        paginas = json.loads((saida / 'paginas.json').read_text())
        self.assertEqual(len(paginas['paginas']), 1)
        self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        self.caso['pendencias'] = ['Conferir a unidade com os autos.']
        self.gravar_caso()
        self.ingerir()
        cmd = [sys.executable, str(RAIZ / 'scaffold/scripts/verificar_documentos.py'), str(self.workspace)]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(cmd + ['--gate'], capture_output=True).returncode, 1)

    def test_adulteracao_texto_original_e_metadados_detectada(self):
        self.copiar()
        self.ingerir()
        doc = self.indice()['documentos'][0]
        for rel in (doc['original'], doc['paginas'][0]['texto_bruto'], 'caso.json'):
            caminho = self.workspace / rel
            dados = caminho.read_bytes()
            caminho.write_bytes(dados + b' ')
            self.assertTrue(verificar(self.workspace)['erros'])
            with self.assertRaises(ValueError):
                self.ingerir()
            caminho.write_bytes(dados)

    def test_referencia_pagina_omitida_e_id_inexistente(self):
        self.copiar()
        self.ingerir()
        indice = self.indice()
        indice['documentos'][0]['paginas'] = []
        indice['historico'][0]['entradas'][0]['documento_id'] = 'DOC-' + '0' * 64
        salvar_json(self.workspace / 'documentos.json', indice)
        erros = verificar(self.workspace)['erros']
        self.assertTrue(any('Cobertura' in e for e in erros))
        self.assertTrue(any('Histórico' in e for e in erros))

    def test_classificacao_cobre_paginas_e_rejeita_referencia_invalida(self):
        self.copiar()
        self.ingerir()
        ident = self.indice()['documentos'][0]['id']
        segmento = {'documento_id': ident, 'pagina_inicio': 1, 'pagina_fim': 1,
                    'tipo': 'jornada', 'justificativa': 'Título da página.'}
        caminho = self.workspace / 'classificacao.json'
        salvar_json(caminho, {'schema_version': 1, 'segmentos': [segmento]})
        self.assertTrue(verificar(self.workspace)['apto_tecnicamente'])
        for segmentos in ([], [segmento, segmento], [{**segmento, 'pagina_fim': 2}],
                          [{**segmento, 'documento_id': 'DOC-' + '0' * 64}]):
            salvar_json(caminho, {'schema_version': 1, 'segmentos': segmentos})
            self.assertTrue(verificar(self.workspace)['erros'])

    def test_lock_impede_execucao_concorrente(self):
        self.copiar()
        lock = self.pasta / '.caso.ingestao.lock'
        lock.touch()
        with self.assertRaisesRegex(ValueError, 'lock'):
            self.ingerir()
        self.assertTrue(lock.exists())
        self.assertFalse(self.workspace.exists())

    def test_falha_de_publicacao_preserva_indice_e_originais(self):
        self.copiar()
        self.ingerir()
        antes = (self.workspace / 'documentos.json').read_bytes()
        self.copiar('corrompido.pdf')
        with patch('ingerir_documentos.salvar_json', side_effect=OSError('Disco indisponível')):
            with self.assertRaises(OSError):
                self.ingerir()
        self.assertEqual(antes, (self.workspace / 'documentos.json').read_bytes())
        self.assertEqual(len(list((self.workspace / 'originais').iterdir())), 1)

    def test_instalacao_e_cli_fora_do_repositorio(self):
        destino = self.pasta / 'instalado'
        r = subprocess.run([sys.executable, str(RAIZ / 'scripts/instalar_perfil.py'),
                            '--perfil', 'jt-1g-local', '--destino', str(destino)], capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.copiar()
        cmd = [sys.executable, str(destino / 'scripts/ingerir_documentos.py'), '--input', str(self.entrada),
               '--workspace', str(self.workspace), '--caso', str(self.metadata)]
        r = subprocess.run(cmd, cwd=self.pasta, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        gate = [sys.executable, str(destino / 'scripts/verificar_documentos.py'), str(self.workspace), '--gate']
        self.assertEqual(subprocess.run(gate, capture_output=True).returncode, 0)
        (self.workspace / self.indice()['documentos'][0]['paginas'][0]['texto_bruto']).unlink()
        self.assertEqual(subprocess.run(gate, capture_output=True).returncode, 1)

    @unittest.skipUnless(os.environ.get('TESTAR_OCR') == '1', 'OCR real: execute com TESTAR_OCR=1')
    def test_ocr_real_escaneado_e_misto(self):
        self.caso['documentos'] = []
        self.gravar_caso()
        self.copiar('escaneado.pdf')
        self.copiar('misto.pdf')
        resultado = self.ingerir()
        self.assertTrue(resultado['apto_tecnicamente'], resultado)
        docs = self.indice()['documentos']
        self.assertEqual([len(d['paginas']) for d in docs], [1, 2])
        self.assertEqual([p['metodo'] for p in docs[1]['paginas']], ['digital', 'ocr'])
        for doc in docs:
            texto = (self.workspace / doc['paginas'][-1]['texto_bruto']).read_text().upper()
            self.assertIn('SALARIO', texto)


if __name__ == '__main__':
    unittest.main()
