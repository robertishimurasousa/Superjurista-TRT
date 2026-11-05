#!/usr/bin/env python3
"""Instala somente os arquivos declarados no perfil, preservando conflitos."""
import argparse
import json
import os
from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'scaffold' / 'scripts'))
from perfil import carregar_perfil, arquivo_do_pacote  # noqa: E402


def conferir_destino(caminho):
    """Não segue links e detecta arquivo usado como diretório ou colisão de caixa."""
    partes = list(reversed(caminho.parents)) + [caminho]
    for atual in partes:
        if atual.is_symlink():
            raise ValueError(f'Link simbólico no destino: {atual}')
        if atual != caminho and atual.exists() and not atual.is_dir():
            raise ValueError(f'Arquivo impede a criação de diretório: {atual}')
        if atual.parent.is_dir() and atual.name:
            for vizinho in atual.parent.iterdir():
                if vizinho.name != atual.name and vizinho.name.casefold() == atual.name.casefold():
                    raise ValueError(f'Nome conflitante por maiúsculas/minúsculas: {vizinho}')


def planejar_instalacao(raiz, perfil_id, destino):
    if perfil_id != 'jt-1g-local':
        raise ValueError(f'Perfil não suportado: {perfil_id}')
    raiz = raiz.resolve()
    destino = Path(os.path.abspath(destino))
    conferir_destino(destino)
    if destino.exists() and not destino.is_dir():
        raise ValueError('O destino deve ser um diretório.')
    if destino.is_relative_to(raiz) or raiz.is_relative_to(destino):
        raise ValueError('Use uma pasta de trabalho separada do repositório do plugin.')
    origem_perfil = arquivo_do_pacote(raiz, f'scaffold/perfis/{perfil_id}.json')
    perfil = carregar_perfil(origem_perfil, raiz)
    operacoes, conflitos = [], []
    for item in perfil['arquivos']:
        alvo = destino / item['destino']
        conferir_destino(alvo)
        conteudo = arquivo_do_pacote(raiz, item['origem']).read_bytes()
        if alvo.exists():
            if not alvo.is_file() or alvo.read_bytes() != conteudo:
                conflitos.append(item['destino'])
                estado = 'conflito'
            else:
                estado = 'identico'
        else:
            estado = 'novo'
        operacoes.append({'destino': item['destino'], 'estado': estado, 'conteudo': conteudo})
    for nome in perfil['diretorios']:
        alvo = destino / nome
        conferir_destino(alvo)
        if alvo.exists() and not alvo.is_dir():
            conflitos.append(nome)
    declarados = {item['destino'] for item in perfil['arquivos']}
    extras = []
    for pasta in (destino / '.claude', destino / 'scripts'):
        if pasta.is_symlink():
            raise ValueError(f'Link simbólico no destino: {pasta}')
        if pasta.is_dir():
            extras += [p.relative_to(destino).as_posix() for p in pasta.rglob('*')
                       if (p.is_file() or p.is_symlink())
                       and p.relative_to(destino).as_posix() not in declarados
                       and '__pycache__' not in p.parts]
    if (destino / '.mcp.json').exists() or (destino / '.mcp.json').is_symlink():
        extras.append('.mcp.json')
    return perfil, destino, operacoes, conflitos, sorted(extras)


def instalar(raiz, perfil_id, destino, dry_run=False):
    perfil, destino, operacoes, conflitos, extras = planejar_instalacao(raiz, perfil_id, destino)
    for op in operacoes:
        print(f'[{op["estado"].upper()}] {op["destino"]}')
    if extras:
        print('[AVISO] Componentes preexistentes fora do perfil foram preservados; '
              'não há garantia de isolamento: ' + ', '.join(extras))
    if conflitos:
        print('[ERRO] Nada gravado. Revise os conflitos: ' + ', '.join(conflitos))
        return 1
    if dry_run:
        print('[FIM] Simulação concluída. Nenhum arquivo ou diretório criado.')
        return 0

    # Exclusão no rollback fica limitada aos arquivos/diretórios criados nesta chamada.
    criados, diretorios = [], []

    def criar_pasta(pasta):
        if pasta.exists():
            if not pasta.is_dir() or pasta.is_symlink():
                raise ValueError(f'Diretório mudou desde a conferência: {pasta}')
            return
        criar_pasta(pasta.parent)
        pasta.mkdir()
        diretorios.append(pasta)

    try:
        for op in operacoes:
            alvo = destino / op['destino']
            conferir_destino(alvo)
            if op['estado'] == 'identico':
                if not alvo.is_file() or alvo.read_bytes() != op['conteudo']:
                    raise ValueError(f'Arquivo mudou desde a conferência: {alvo}')
                continue
            criar_pasta(alvo.parent)
            # Criação exclusiva: jamais sobrescreve um arquivo que surgiu após a conferência.
            with alvo.open('xb') as arquivo:
                criados.append(alvo)
                arquivo.write(op['conteudo'])
        for nome in perfil['diretorios']:
            conferir_destino(destino / nome)
            criar_pasta(destino / nome)
    except Exception:
        for arquivo in reversed(criados):
            arquivo.unlink(missing_ok=True)
        for pasta in reversed(diretorios):
            try:
                pasta.rmdir()
            except OSError:
                pass  # Preserva conteúdo criado externamente durante a execução.
        raise
    print(f'[OK] Perfil {perfil_id} instalado em {destino}')
    print('[FIM] Base em desenvolvimento: ingestão, análise provisória e fontes locais disponíveis; sentença e homologação ainda não disponíveis.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--perfil', required=True, help='jt-1g-local')
    parser.add_argument('--destino', required=True, type=Path)
    parser.add_argument('--dry-run', action='store_true', help='Conferir sem criar arquivos')
    args = parser.parse_args()
    try:
        return instalar(RAIZ, args.perfil, args.destino, args.dry_run)
    except (ValueError, OSError, json.JSONDecodeError) as erro:
        print(f'[ERRO] {erro}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
