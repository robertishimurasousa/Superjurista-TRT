#!/usr/bin/env python3
"""Prepara 12 entradas, 36 registros vazios e fichas humanas, sem executar/aceitar o piloto."""
import argparse
import json
from pathlib import Path
import sys
RAIZ=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RAIZ/'tests/fixtures'))
sys.path.insert(0,str(RAIZ/'scaffold/scripts'))
from corpus_piloto import casos,gerar_entrada,MANIFESTO
from documentos import hash_arquivo,salvar_json
from validar_repositorio import hash_pacote

CRITERIOS=['fatos','pedidos','fontes','rito','encargos','dispositivo']


def preparar(destino):
    if destino.exists():raise ValueError('Destino já existe; preserve a avaliação anterior.')
    destino.mkdir(parents=True)
    registros=[];fichas=[]
    for c in casos():
        pasta=destino/'entradas'/c['id'];gerar_entrada(pasta,c)
        for repeticao in range(1,4):
            registros.append({'caso':c['id'],'repeticao':repeticao,'estado':'nao-executada',
                'entrada_sha256':hash_arquivo(pasta/'entrada/autos.pdf'),'caso_sha256':hash_arquivo(pasta/'caso.json'),
                'modelo':None,'claude_code_versao':None,'inicio':None,'fim':None,'duracao_segundos':None,
                'workspace':None,'transcricao':None,'transcricao_sha256':None,
                'resultado':None,'etapa':None,'artefatos_sha256':{},'observacoes':None})
        fichas.append({'caso':c['id'],'estado':'pendente','responsavel':None,'data':None,
            'recorte_confirmado':False,'execucoes_revisadas':[],
            'criterios':{k:{'estado':'pendente','observacao':None} for k in CRITERIOS},
            'defeitos':[],'variacao_entre_repeticoes':None,'justificativa':None})
    avaliacao={'schema_version':1,'natureza':'avaliacao-com-agentes','manifesto_sha256':hash_arquivo(MANIFESTO),
        'pacote_sha256':hash_pacote(),'execucoes':registros,'fichas':fichas,'aceite_humano':'nao-registrado'}
    salvar_json(destino/'avaliacao.json',avaliacao)
    return destino/'avaliacao.json'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--destino',required=True,type=Path);a=p.parse_args()
    try:print(preparar(a.destino));return 0
    except (ValueError,OSError) as exc:print(str(exc),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
