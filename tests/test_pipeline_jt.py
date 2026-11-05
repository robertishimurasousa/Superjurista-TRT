"""Corpus e integração instalada; resultados de software não são execuções de agentes."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RAIZ/'tests/fixtures'))
sys.path.insert(0,str(RAIZ/'scaffold/scripts'))
from corpus_piloto import casos, criar_oraculo, redigir_oraculo, gerar_entrada
from documentos import hash_arquivo, salvar_json
from fontes_jt import ler_json
from estado_execucao import ETAPAS, iniciar, encerrar, validar_etapa
from merge_sentenca_jt import publicar
from verificar_sentenca_jt import verificar


class CorpusTests(unittest.TestCase):
    def conferir_caso(self,c):
        if c['entrada']['ocr'] and os.environ.get('TESTAR_OCR') != '1':
            self.skipTest('Corpus misto exige TESTAR_OCR=1, Poppler e Tesseract por.')
        with tempfile.TemporaryDirectory() as tmp:
            w=criar_oraculo(Path(tmp).resolve(),c); token=iniciar(w)['token']
            try:
                docs=ler_json(w,'documentos.json')['documentos']
                self.assertEqual(sum(d['paginas_total'] for d in docs),c['entrada']['paginas'])
                rel=ler_json(w,'pedidos.json')
                self.assertEqual([p['id'] for p in rel['pedidos']],c['esperado']['pedidos'])
                self.assertEqual(len([p for p in rel['partes'] if p['polo']=='reclamado']),c['reclamadas'])
                etapa_bloqueada=None
                for e in ETAPAS:
                    if e=='redacao':redigir_oraculo(w,token)
                    if e=='publicacao':self.assertTrue(publicar(w,token)['publicada'])
                    r=validar_etapa(w,e)
                    self.assertEqual(r['erros'],[],(c['id'],e,r))
                    if r['pendencias']:
                        etapa_bloqueada=e
                        self.assertEqual(e,c['esperado']['etapa'])
                        self.assertTrue(any(c['esperado']['pendencia_contem'].casefold() in p.casefold() for p in r['pendencias']),r)
                        self.assertFalse((w/'minuta.md').exists())
                        self.assertFalse(verificar(w)['valido_tecnicamente'])
                        break
                if c['esperado']['resultado']=='minuta-tecnica':
                    self.assertIsNone(etapa_bloqueada)
                    self.assertTrue(verificar(w)['valido_tecnicamente'])
                    minuta=(w/'minuta.md').read_text()
                    for pedido in c['esperado']['pedidos']:self.assertEqual(minuta.count('### '+pedido),2)
                    self.assertEqual('## Relatório' in minuta,c['rito']=='ordinario')
                    self.assertNotIn('juiz federal',minuta.lower())
                else:self.assertIsNotNone(etapa_bloqueada)
                textos='\n'.join((w/p['texto_bruto']).read_text() for d in docs for p in d['paginas'])
                self.assertIn('INSTRUCAO ADVERSARIAL',textos)
                if c['id']=='jornada-tabela-repetida':self.assertEqual(textos.count('08:00 12:00 13:00 17:00'),8)
                if c['entrada']['ocr']:
                    self.assertTrue(any(p['metodo']=='ocr' for d in docs for p in d['paginas']))
            finally:encerrar(w,token)

    def test_entradas_para_agentes_nao_contem_oraculos_ou_conferencias(self):
        with tempfile.TemporaryDirectory() as tmp:
            for c in casos():
                pasta=Path(tmp)/c['id']; gerar_entrada(pasta,c)
                self.assertEqual({p.name for p in pasta.iterdir()},{'entrada','caso.json'})
                self.assertEqual({p.name for p in (pasta/'entrada').iterdir()},{'autos.pdf'})

for cenario in casos():
    def teste(self,c=cenario): self.conferir_caso(c)
    setattr(CorpusTests,'test_corpus_'+cenario['id'].replace('-','_'),teste)


class IntegracaoInstaladaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        base=Path(cls.tmp.name).resolve(); cls.modelo=base/'instalado'
        subprocess.run([sys.executable,str(RAIZ/'scripts/instalar_perfil.py'),'--perfil','jt-1g-local','--destino',str(cls.modelo)],check=True,capture_output=True)
        origem=base/'origem'; origem.mkdir()
        w=criar_oraculo(origem,casos()[0]); token=iniciar(w)['token']; redigir_oraculo(w,token); encerrar(w,token)
        cls.workspace=cls.modelo/'data/casos/piloto'; cls.workspace.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(w,cls.workspace)
        cls.token=cls.cli(cls.modelo,'estado_execucao.py','iniciar',cls.workspace)['token']
        for etapa in ETAPAS:
            cls.cli(cls.modelo,'estado_execucao.py','iniciar-etapa',cls.workspace,'--token',cls.token,'--etapa',etapa)
            if etapa=='publicacao': cls.cli(cls.modelo,'merge_sentenca_jt.py',cls.workspace,'--token',cls.token)
            cls.cli(cls.modelo,'estado_execucao.py','concluir-etapa',cls.workspace,'--token',cls.token,'--etapa',etapa)
        cls.cli(cls.modelo,'estado_execucao.py','encerrar',cls.workspace,'--token',cls.token)

    @staticmethod
    def cli(projeto,script,*args,esperado=0):
        r=subprocess.run([sys.executable,str(projeto/'scripts'/script),*map(str,args)],cwd=projeto,capture_output=True,text=True)
        if r.returncode!=esperado:raise AssertionError((r.returncode,r.stdout,r.stderr))
        return json.loads(r.stdout) if r.stdout.strip() else r.stderr

    def setUp(self):
        self.tmpcaso=tempfile.TemporaryDirectory(); self.addCleanup(self.tmpcaso.cleanup)
        self.projeto=Path(self.tmpcaso.name).resolve()/'instalado'; shutil.copytree(self.modelo,self.projeto)
        self.w=self.projeto/'data/casos/piloto'
        self.token=self.cli(self.projeto,'estado_execucao.py','iniciar',self.w)['token']
        self.addCleanup(lambda:self.cli(self.projeto,'estado_execucao.py','encerrar',self.w,'--token',self.token))

    def inventario(self):return self.cli(self.projeto,'estado_execucao.py','inventario',self.w,'--token',self.token)

    def test_retomada_sem_mudancas_preserva_bytes_e_reutiliza(self):
        antes={p.relative_to(self.w).as_posix():hash_arquivo(p) for p in self.w.rglob('*') if p.is_file() and p.name!='execucao.json'}
        self.assertIsNone(self.inventario()['proxima'])
        r=self.cli(self.projeto,'estado_execucao.py','iniciar-etapa',self.w,'--token',self.token,'--etapa','redacao')
        self.assertEqual(r['acao'],'reutilizar')
        self.assertEqual(antes,{p.relative_to(self.w).as_posix():hash_arquivo(p) for p in self.w.rglob('*') if p.is_file() and p.name!='execucao.json'})

    def test_pdf_alterado_invalida_todo_fluxo(self):
        p=next((self.w/'originais').glob('*.pdf')); p.write_bytes(p.read_bytes()+b'\n')
        r=self.inventario(); self.assertEqual(r['proxima'],'ingestao')
        self.assertTrue(all(e['estado']!='valida' for e in r['etapas']))
        self.cli(self.projeto,'verificar_sentenca_jt.py',self.w,'--gate',esperado=1)

    def test_prompt_e_perfil_alterados_invalidam_descendentes(self):
        for relativo in ['.claude/agents/trabalhista/fundamentador.md','.claude/perfis/jt-1g-local.json']:
            p=self.projeto/relativo; original=p.read_bytes(); p.write_bytes(original+b'\n')
            r=self.inventario(); self.assertEqual(r['proxima'],'ingestao')
            self.assertTrue(all(e['estado']!='valida' for e in r['etapas']))
            self.cli(self.projeto,'verificar_sentenca_jt.py',self.w,'--gate',esperado=1)
            p.write_bytes(original)

    def test_fonte_alterada_preserva_anteriores_invalida_dependentes(self):
        fonte=ler_json(self.w,'fontes-juridicas.json')['fontes'][0]
        p=self.w/fonte['texto']; p.write_bytes(p.read_bytes()+b'\nMUDANCA SINTETICA')
        r=self.inventario(); self.assertEqual(r['proxima'],'fontes')
        self.assertTrue(all(e['estado']=='valida' for e in r['etapas'][:4]))
        self.assertTrue(all(e['estado']!='valida' for e in r['etapas'][4:]))
        self.cli(self.projeto,'verificar_sentenca_jt.py',self.w,'--gate',esperado=1)

    def test_processos_e_casos_nao_compartilham_sessao(self):
        self.cli(self.projeto,'estado_execucao.py','iniciar',self.w,esperado=2)
        outra=self.projeto/'data/casos/outro'; shutil.copytree(self.w,outra)
        t=self.cli(self.projeto,'estado_execucao.py','iniciar',outra)['token']
        try:
            antes=hash_arquivo(outra/'execucao.json')
            self.cli(self.projeto,'estado_execucao.py','inventario',outra,'--token',self.token,esperado=2)
            self.assertEqual(antes,hash_arquivo(outra/'execucao.json'))
            self.assertNotEqual(t,self.token)
        finally:self.cli(self.projeto,'estado_execucao.py','encerrar',outra,'--token',t)

    def test_interrupcao_antes_ultimo_rename_recusa_publicacao_parcial(self):
        recibo=ler_json(self.w,'publicacao.json'); recibo['minuta_sha256']='0'*64
        salvar_json(self.w/'publicacao.json',recibo)
        antes=(self.w/'minuta.md').read_bytes()
        self.cli(self.projeto,'verificar_sentenca_jt.py',self.w,'--gate',esperado=1)
        r=self.inventario();self.assertEqual(r['proxima'],'publicacao')
        self.cli(self.projeto,'estado_execucao.py','iniciar-etapa',self.w,'--token',self.token,'--etapa','publicacao')
        self.cli(self.projeto,'merge_sentenca_jt.py',self.w,'--token',self.token)
        self.cli(self.projeto,'estado_execucao.py','concluir-etapa',self.w,'--token',self.token,'--etapa','publicacao')
        self.cli(self.projeto,'verificar_sentenca_jt.py',self.w,'--gate')
        self.assertEqual(antes,(self.w/'minuta.md').read_bytes())

if __name__=='__main__':unittest.main()
