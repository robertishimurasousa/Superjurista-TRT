#!/usr/bin/env python3
"""Prepara a candidata e publica uma minuta revisada por substituição atômica."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from documentos import caminho_seguro, hash_arquivo, salvar_json
from estado_execucao import operacao
from fontes_jt import ler_json
from verificar_sentenca_jt import renderizar, verificar, assinatura_publicacao


def salvar_bytes(caminho, dados):
    with tempfile.NamedTemporaryFile(dir=caminho.parent, prefix='.minuta-', delete=False) as f:
        tmp = Path(f.name)
        try:
            f.write(dados); f.flush(); os.fsync(f.fileno())
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
    try:
        os.replace(tmp, caminho)
    finally:
        tmp.unlink(missing_ok=True)


def preparar(workspace, token):
    with operacao(workspace, token) as raiz:
        gate = verificar(raiz, 'redacao')
        if not gate['valido_tecnicamente']:
            return {'preparada': False, **gate}
        assinatura = assinatura_publicacao(raiz)
        texto = renderizar(ler_json(raiz, 'redacao.json')).encode('utf-8')
        if assinatura_publicacao(raiz) != assinatura:
            raise ValueError('Insumos alterados durante a preparação.')
        destino = caminho_seguro(raiz, 'minuta-candidata.md')
        if not destino.exists() or destino.read_bytes() != texto:
            salvar_bytes(destino, texto)
        return {'preparada': True, 'minuta_sha256': hash_arquivo(destino), 'aceite_humano': 'nao-registrado'}


def publicar(workspace, token):
    with operacao(workspace, token) as raiz:
        assinatura = assinatura_publicacao(raiz)
        gate = verificar(raiz, 'revisao')
        if not gate['valido_tecnicamente']:
            return {'publicada': False, **gate}
        candidata = caminho_seguro(raiz, 'minuta-candidata.md').read_bytes()
        refs = caminho_seguro(raiz, 'referencias-candidata.json').read_bytes()
        recibo = {'schema_version': 1, 'assinatura': assinatura,
                  'minuta_sha256': hash_arquivo(caminho_seguro(raiz, 'minuta-candidata.md')), 'aceite_humano': 'nao-registrado'}
        if assinatura_publicacao(raiz) != assinatura:
            raise ValueError('Insumos alterados durante a revisão; publicação recusada.')
        final = caminho_seguro(raiz, 'minuta.md')
        destinos = [caminho_seguro(raiz, 'referencias-minuta.json'), caminho_seguro(raiz, 'publicacao.json')]
        anteriores = {p: p.read_bytes() if p.exists() else None for p in destinos}
        # Metadados primeiro; minuta por último. Uma interrupção entre renomes é detectada pelo gate.
        try:
            salvar_bytes(destinos[0], refs)
            salvar_json(destinos[1], recibo)
            if assinatura_publicacao(raiz) != assinatura:
                raise ValueError('Insumos alterados antes da publicação.')
            salvar_bytes(final, candidata)
        except Exception:
            for caminho, conteudo in anteriores.items():
                if conteudo is None: caminho.unlink(missing_ok=True)
                else: salvar_bytes(caminho, conteudo)
            raise
        return {'publicada': True, 'minuta_sha256': recibo['minuta_sha256'],
                'validacao_juridica': 'nao-realizada', 'aceite_humano': 'nao-registrado'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('workspace', type=Path); p.add_argument('--token', required=True)
    p.add_argument('--preparar', action='store_true')
    a = p.parse_args()
    try:
        r = preparar(a.workspace, a.token) if a.preparar else publicar(a.workspace, a.token)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r.get('preparada') or r.get('publicada') else 1
    except (ValueError, OSError):
        print('Montagem recusada: confira a sessão, os insumos e as permissões de escrita.', file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
