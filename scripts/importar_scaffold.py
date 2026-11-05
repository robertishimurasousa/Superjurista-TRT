#!/usr/bin/env python3
"""Prepara uma comparação upstream sem modificar o scaffold versionado."""
import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

RAIZ = Path(__file__).resolve().parent.parent
GLOBAIS = ('bnp-api', 'cjf-jurisprudencia', 'tnu-eproc')
LOCAIS = ('tcu-jurisprudencia', 'tjsc-eproc')
IGNORAR = ('.git', '__pycache__', '*.pyc', '*credentials*', '.env*', '*.log',
           'sessao*.json', 'pje_session*', '*.har', '*cookies*', '.DS_Store')
EXCLUIR = {
    'agents/pesquisa/pesquisador-george.md', 'agents/redacao/criar-palestra.md',
    'commands/criar-agente.md', 'commands/criar-orquestrador.md',
    'commands/criar-skill.md', 'commands/criar-team.md', 'commands/planejar-sistema.md',
    'skills/criar-skill', 'skills/criar-mcp-precedente',
}


def hash_arquivo(caminho):
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def selecionar_arquivos(projeto, scripts, globais):
    """Valida todas as origens antes de criar a área temporária."""
    origens = [(projeto / nome, nome) for nome in ('agents', 'commands', 'skills')]
    origens += [(scripts, 'scripts')]
    origens += [(globais / nome, 'mcp-servers/' + nome) for nome in GLOBAIS]
    origens += [(projeto / 'mcp-servers' / nome, 'mcp-servers/' + nome) for nome in LOCAIS]
    selecionados = {}
    for origem, prefixo in origens:
        if origem.is_symlink() or not origem.is_dir():
            raise ValueError(f'Origem ausente ou não permitida: {origem}')
        for arquivo in sorted(origem.rglob('*')):
            relativo = arquivo.relative_to(origem)
            destino = Path(prefixo) / relativo
            if any(fnmatch.fnmatchcase(parte.lower(), padrao.lower())
                   for parte in relativo.parts for padrao in IGNORAR):
                continue
            if any(destino.as_posix() == item or destino.as_posix().startswith(item + '/')
                   for item in EXCLUIR):
                continue
            if arquivo.is_symlink():
                raise ValueError(f'Link simbólico não permitido na origem: {arquivo}')
            if not arquivo.is_file():
                continue
            if prefixo == 'scripts' and (len(relativo.parts) != 1
                                        or arquivo.suffix != '.py'
                                        or arquivo.name.startswith('test_')):
                continue
            selecionados[destino.as_posix()] = arquivo
    if not selecionados:
        raise ValueError('Nenhum arquivo elegível nas origens.')
    return selecionados


def importar(projeto, scripts, globais, referencia=RAIZ / 'scaffold'):
    selecionados = selecionar_arquivos(projeto, scripts, globais)
    if not referencia.is_dir():
        raise ValueError(f'Scaffold de referência inexistente: {referencia}')
    area = Path(tempfile.mkdtemp(prefix='superjurista-importacao-'))
    try:
        candidato = area / 'scaffold'
        entradas = []
        for relativo, origem in selecionados.items():
            destino = candidato / relativo
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origem, destino)
            atual = referencia / relativo
            anterior = hash_arquivo(atual) if atual.is_file() and not atual.is_symlink() else None
            novo = hash_arquivo(destino)
            entradas.append({'arquivo': relativo, 'sha256_atual': anterior,
                             'sha256_candidato': novo,
                             'estado': 'igual' if anterior == novo else
                             ('alterado' if anterior else 'novo')})
        apenas_local = sorted(p.relative_to(referencia).as_posix()
                              for p in referencia.rglob('*') if p.is_file()
                              and p.relative_to(referencia).as_posix() not in selecionados
                              and '__pycache__' not in p.parts)
        relatorio = {'referencia': str(referencia.resolve()), 'candidato': str(candidato),
                     'alteracoes_aplicadas': False, 'arquivos': entradas,
                     'apenas_na_referencia_preservados': apenas_local}
        (area / 'comparacao.json').write_text(json.dumps(relatorio, ensure_ascii=False, indent=2)
                                             + '\n', encoding='utf-8')
        return area
    except Exception:
        shutil.rmtree(area)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--projeto', required=True, type=Path, help='Diretório .claude de origem')
    parser.add_argument('--scripts', required=True, type=Path, help='Scripts do projeto de origem')
    parser.add_argument('--mcps-globais', required=True, type=Path, help='Diretório dos MCPs globais')
    args = parser.parse_args()
    try:
        area = importar(args.projeto, args.scripts, args.mcps_globais)
    except (ValueError, OSError) as erro:
        print(f'[ERRO] {erro}')
        return 2
    print(f'[OK] Candidato e comparação: {area}')
    print('[FIM] Nenhuma alteração aplicada. Revise comparacao.json e os arquivos candidatos.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
