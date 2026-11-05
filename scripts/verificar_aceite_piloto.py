#!/usr/bin/env python3
"""Confere evidências e declarações humanas; não preenche aceite nem autentica assinaturas."""
import argparse
from datetime import datetime, date
import json
import math
from pathlib import Path
import re
import sys

RAIZ=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RAIZ/'scaffold/scripts'));sys.path.insert(0,str(RAIZ/'tests/fixtures'))
from documentos import caminho_seguro, hash_arquivo, sem_links
from corpus_piloto import casos, MANIFESTO
from estado_execucao import ETAPAS, validar_etapa
from fontes_jt import ler_json
from validar_repositorio import hash_pacote
from preparar_avaliacao_jt import CRITERIOS

CRITICOS={'fato-inventado-decisivo','pedido-omitido','fonte-falsa','regra-federal-indevida','conclusao-fora-do-escopo'}
HASH=re.compile(r'^[0-9a-f]{64}$')


def preenchido(v):return isinstance(v,str) and bool(v.strip())


def verificar(arquivo):
    arquivo=sem_links(arquivo);raiz=arquivo.parent
    dados=json.loads(arquivo.read_text(encoding='utf-8'));erros=[];pendencias=[]
    cadastro={c['id']:c for c in casos()}
    if dados.get('schema_version')!=1 or dados.get('natureza')!='avaliacao-com-agentes':raise ValueError('Contrato de avaliação inválido.')
    if dados.get('manifesto_sha256')!=hash_arquivo(MANIFESTO):erros.append('Manifesto mudou desde a preparação.')
    if dados.get('pacote_sha256')!=hash_pacote():erros.append('Pacote mudou desde a preparação; reavaliar execuções afetadas.')
    pares=[(e['caso'],e['repeticao']) for e in dados['execucoes']]
    esperados={(c,n) for c in cadastro for n in range(1,4)}
    if len(pares)!=36 or len(set(pares))!=36 or set(pares)!=esperados:erros.append('Exigir exatamente 12 casos × 3 repetições distintas.')
    revisaveis={c:[] for c in cadastro};transcricoes=set();workspaces=set();avaliadas=0
    for e in dados['execucoes']:
        c=cadastro.get(e['caso']);local=f'{e["caso"]}/{e["repeticao"]}'
        if c is None:continue
        if e['estado']=='nao-executada':pendencias.append('Execução não realizada: '+local);continue
        inicio_erros=len(erros);inicio_pendencias=len(pendencias)
        if e['estado']!='executada':erros.append('Estado de execução desconhecido: '+local);continue
        for campo in ('modelo','claude_code_versao','observacoes'):
            if not preenchido(e.get(campo)):erros.append('Identificação/observação ausente: '+local+'/'+campo)
        try:
            inicio=datetime.fromisoformat(e['inicio']);fim=datetime.fromisoformat(e['fim'])
            duracao=(fim-inicio).total_seconds()
            valor=e['duracao_segundos']
            if type(valor) not in (int,float) or not math.isfinite(valor):raise ValueError()
            if not inicio.tzinfo or not fim.tzinfo or duracao<=0 or abs(duracao-valor)>1:
                raise ValueError()
            if fim>datetime.now(fim.tzinfo):raise ValueError()
        except (ValueError,TypeError):erros.append('Datas/duração inválidas: '+local)
        try:
            w=caminho_seguro(raiz,e['workspace']);transcricao=caminho_seguro(raiz,e['transcricao'])
            if w in workspaces:erros.append('Repetições precisam de workspaces independentes: '+local)
            workspaces.add(w)
            if transcricao in transcricoes:erros.append('Transcrição reutilizada entre repetições: '+local)
            transcricoes.add(transcricao)
            if not transcricao.is_file() or transcricao.stat().st_size==0 or hash_arquivo(transcricao)!=e['transcricao_sha256']:
                erros.append('Transcrição ausente/alterada: '+local)
            for campo,relativo in [('entrada_sha256','entrada/autos.pdf'),('caso_sha256','caso.json')]:
                if e[campo]!=hash_arquivo(caminho_seguro(raiz,'entradas/'+c['id']+'/'+relativo)):
                    erros.append('Entrada de avaliação alterada: '+local)
            if hash_arquivo(w/'caso.json')!=e['caso_sha256']:erros.append('Identidade/metadados do workspace divergem da entrada: '+local)
            if e['entrada_sha256'] not in {d['sha256'] for d in ler_json(w,'documentos.json')['documentos']}:
                erros.append('PDF de avaliação ausente do workspace: '+local)
            artifacts=e['artefatos_sha256']
            obrigatorios={'caso.json','documentos.json'}
            if c['esperado']['resultado']=='minuta-tecnica':obrigatorios|={'minuta.md','publicacao.json','revisao.json','referencias-minuta.json'}
            else:obrigatorios|={'resultado-gate.json'}
            if not obrigatorios<=set(artifacts):erros.append('Snapshot de artefatos incompleto: '+local)
            for nome,sha in artifacts.items():
                if not HASH.fullmatch(sha) or hash_arquivo(caminho_seguro(w,nome))!=sha:erros.append('Artefato alterado: '+local+'/'+nome)
            if e['resultado']!=c['esperado']['resultado'] or e['etapa']!=c['esperado']['etapa']:
                erros.append('Resultado diverge do esperado: '+local)
            # Verificar a cadeia até o bloqueio; uma falha estrutural não conta como bloqueio esperado.
            for etapa in ETAPAS[:ETAPAS.index(c['esperado']['etapa'])+1]:
                gate=validar_etapa(w,etapa)
                if gate['erros']:erros.append('Erro técnico em '+local+'/'+etapa);break
                if gate['pendencias']:
                    motivo=c['esperado']['pendencia_contem']
                    if etapa!=c['esperado']['etapa'] or not motivo or not any(motivo.casefold() in p.casefold() for p in gate['pendencias']):
                        erros.append('Bloqueio divergente: '+local+'/'+etapa)
                    if (w/'minuta.md').exists():erros.append('Minuta conclusiva presente em caso bloqueado: '+local)
                    break
            else:
                if c['esperado']['resultado']=='bloqueio':erros.append('Bloqueio esperado não ocorreu: '+local)
        except (ValueError,OSError,KeyError,TypeError):erros.append('Evidência ausente ou inválida: '+local)
        if len(erros)==inicio_erros and len(pendencias)==inicio_pendencias:
            revisaveis[c['id']].append(e['repeticao']);avaliadas+=1
    fichas=dados['fichas'];ids=[f['caso'] for f in fichas]
    if len(ids)!=12 or len(set(ids))!=12 or set(ids)!=set(cadastro):erros.append('Exigir uma ficha por caso.')
    for f in fichas:
        local=f['caso']
        if f['estado']!='aceito':pendencias.append('Revisão humana pendente/rejeitada: '+local);continue
        if not preenchido(f['responsavel']) or not preenchido(f['justificativa']) or f['recorte_confirmado'] is not True:
            erros.append('Aceite sem responsável, justificativa ou confirmação do recorte: '+local)
        try:
            if date.fromisoformat(f['data'])>date.today():raise ValueError()
        except (ValueError,TypeError):erros.append('Data de aceite inválida: '+local)
        if sorted(f['execucoes_revisadas'])!=[1,2,3] or sorted(revisaveis.get(local,[]))!=[1,2,3]:
            erros.append('Aceite exige três execuções válidas conferidas: '+local)
        if set(f['criterios'])!=set(CRITERIOS) or any(v['estado']!='conferido' or not preenchido(v['observacao']) for v in f['criterios'].values()):
            erros.append('Ficha sem conferência integral dos seis critérios: '+local)
        if not preenchido(f['variacao_entre_repeticoes']):erros.append('Variação entre repetições não avaliada: '+local)
        if any(d.get('estado')!='resolvido' for d in f['defeitos']):erros.append('Defeito aberto impede aceite: '+local)
        if any(d.get('tipo') in CRITICOS and (not preenchido(d.get('correcao')) or sorted(d.get('reexecucoes',[]))!=[1,2,3]) for d in f['defeitos']):
            erros.append('Defeito crítico exige correção e repetição: '+local)
    if dados.get('aceite_humano')!='registrado-pelo-responsavel':pendencias.append('Aceite humano global não registrado.')
    return {'erros':erros,'pendencias':pendencias,'execucoes_verificadas':avaliadas,
            'registro_completo':not erros and not pendencias,'assinatura_autenticada':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('arquivo',type=Path);a=p.parse_args()
    try:
        r=verificar(a.arquivo);print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['registro_completo'] else 1
    except (ValueError,OSError,KeyError,TypeError):print('Registro inválido; confira o roteiro e os campos.',file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
