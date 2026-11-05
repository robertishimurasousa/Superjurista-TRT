#!/usr/bin/env python3
"""Consolida somente fontes selecionadas, íntegras e conferidas; sem aprovação parcial."""
import argparse
import json
from pathlib import Path
import sys

from documentos import caminho_seguro, salvar_json, sem_links
from fontes_jt import carregar_fonte, caso_local, chave_duplicata, conferir_fonte, lock_fontes


def consolidar(workspace, ids):
    raiz = sem_links(workspace)
    caso = caso_local(raiz)
    erros, pendencias, fontes, chaves = [], [], [], set()
    if not ids:
        return {'erros': [], 'pendencias': ['Nenhuma fonte selecionada.'], 'publicado': False}
    with lock_fontes(raiz):
        for ident in sorted(set(ids)):
            fonte = carregar_fonte(raiz, ident)
            e, p = conferir_fonte(raiz, fonte, caso)
            erros.extend(e); pendencias.extend(p)
            chave = chave_duplicata(fonte)
            if chave in chaves:
                erros.append('Versões da mesma fonte: selecione explicitamente uma revisão.')
            chaves.add(chave)
            fontes.append(fonte)
        if erros or pendencias:
            return {'erros': erros, 'pendencias': pendencias, 'publicado': False}
        corpus = {'schema_version': 1, 'numero_cnj': caso['numero_cnj'], 'fontes': fontes}
        destino = caminho_seguro(raiz, 'fontes-juridicas.json')
        if not destino.exists() or json.loads(destino.read_text(encoding='utf-8')) != corpus:
            salvar_json(destino, corpus)
        return {'erros': [], 'pendencias': [], 'publicado': True, 'quantidade': len(fontes)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('--fontes', nargs='+', required=True, help='IDs FON das revisões selecionadas')
    args = parser.parse_args()
    try:
        resultado = consolidar(args.workspace, args.fontes)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0 if resultado['publicado'] else 1
    except (ValueError, OSError, ImportError):
        print('Consolidação recusada: confira contratos, caminhos e importações.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
