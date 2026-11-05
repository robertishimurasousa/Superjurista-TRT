"""Aceite permanece pendente sem 36 evidências e declarações humanas completas."""
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys
import tempfile
import unittest
RAIZ=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RAIZ/'scripts'))
from preparar_avaliacao_jt import preparar
from verificar_aceite_piloto import verificar
from documentos import salvar_json, hash_arquivo
from corpus_piloto import criar_oraculo, redigir_oraculo, casos
from estado_execucao import iniciar, encerrar
from merge_sentenca_jt import publicar


class AceiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.registro=preparar(Path(cls.tmp.name).resolve()/'avaliacao')
        cls.modelo=json.loads(cls.registro.read_text())

    def setUp(self):
        self.dados=copy.deepcopy(self.modelo)
        self.tmpcaso=tempfile.TemporaryDirectory();self.addCleanup(self.tmpcaso.cleanup)
        self.arquivo=Path(self.tmpcaso.name).resolve()/'avaliacao.json'

    def conferir(self):salvar_json(self.arquivo,self.dados);return verificar(self.arquivo)

    def test_modelo_tem_36_execucoes_e_12_fichas_sem_aceite(self):
        self.assertEqual(len(self.dados['execucoes']),36);self.assertEqual(len(self.dados['fichas']),12)
        self.assertTrue(all(e['estado']=='nao-executada' and e['modelo'] is None for e in self.dados['execucoes']))
        r=self.conferir();self.assertEqual(r['erros'],[]);self.assertFalse(r['registro_completo']);self.assertEqual(r['execucoes_verificadas'],0)

    def test_repeticoes_duplicadas_ou_ausentes_recusadas(self):
        self.dados['execucoes'][-1]=copy.deepcopy(self.dados['execucoes'][0])
        self.assertTrue(self.conferir()['erros'])
        self.dados['execucoes'].pop();self.assertTrue(self.conferir()['erros'])

    def test_alteracao_pacote_ou_manifesto_exige_reavaliacao(self):
        for campo in ('pacote_sha256','manifesto_sha256'):
            self.dados=copy.deepcopy(self.modelo);self.dados[campo]='0'*64
            self.assertTrue(self.conferir()['erros'])

    def test_aceite_nominal_nao_supre_ausencia_de_execucoes(self):
        self.dados['aceite_humano']='registrado-pelo-responsavel'
        f=self.dados['fichas'][0];f.update(estado='aceito',responsavel='REVISOR FICTICIO DE TESTE',data='2026-01-01',recorte_confirmado=True,
            execucoes_revisadas=[1,2,3],variacao_entre_repeticoes='Sem avaliação real.',justificativa='Teste sem aceite real.')
        for item in f['criterios'].values():item.update(estado='conferido',observacao='Conferência fictícia.')
        r=self.conferir();self.assertFalse(r['registro_completo']);self.assertTrue(any('três execuções' in e for e in r['erros']))

    def test_defeito_critico_aberto_impede_aceite(self):
        f=self.dados['fichas'][0];f['estado']='aceito'
        f['defeitos']=[{'tipo':'pedido-omitido','estado':'aberto','correcao':None,'reexecucoes':[]}]
        r=self.conferir();self.assertTrue(any('Defeito' in e for e in r['erros']))

    def test_execucao_declarada_sem_evidencia_nao_conta(self):
        self.dados['execucoes'][0]['estado']='executada'
        r=self.conferir();self.assertTrue(r['erros']);self.assertEqual(r['execucoes_verificadas'],0)

    def test_snapshot_confere_integridade_sem_comprovar_execucao_de_modelo(self):
        # Registro fictício exercita o verificador de evidências, não Claude Code.
        raiz=Path(self.tmpcaso.name).resolve()
        self.arquivo=preparar(raiz/'avaliacao')
        self.dados=json.loads(self.arquivo.read_text())
        origem=self.arquivo.parent/'execucoes/primeira';origem.mkdir(parents=True)
        w=criar_oraculo(origem,casos()[0]);t=iniciar(w)['token']
        redigir_oraculo(w,t);publicar(w,t);encerrar(w,t)
        transcricao=self.arquivo.parent/'transcricao-ficticia.txt'
        transcricao.write_text('TESTE SINTETICO. Nenhum agente foi executado.')
        fim=datetime.now(timezone.utc)-timedelta(seconds=1);inicio=fim-timedelta(seconds=10)
        e=self.dados['execucoes'][0]
        e.update(estado='executada',modelo='MODELO FICTICIO',claude_code_versao='VERSAO FICTICIA',
            inicio=inicio.isoformat(),fim=fim.isoformat(),duracao_segundos=10,
            workspace=w.relative_to(self.arquivo.parent).as_posix(),transcricao=transcricao.name,
            transcricao_sha256=hash_arquivo(transcricao),resultado='minuta-tecnica',etapa='publicacao',
            artefatos_sha256={n:hash_arquivo(w/n) for n in ['caso.json','documentos.json','minuta.md','publicacao.json','revisao.json','referencias-minuta.json']},
            observacoes='Registro simulado para teste de integridade, sem autoria autenticada.')
        r=self.conferir();self.assertEqual(r['erros'],[]);self.assertEqual(r['execucoes_verificadas'],1)
        self.assertFalse(r['registro_completo']);self.assertFalse(r['assinatura_autenticada'])
        e['duracao_segundos']=float('nan');self.assertTrue(self.conferir()['erros'])
        e['duracao_segundos']=10;transcricao.write_text('Alterada')
        self.assertEqual(self.conferir()['execucoes_verificadas'],0)


if __name__=='__main__':unittest.main()
