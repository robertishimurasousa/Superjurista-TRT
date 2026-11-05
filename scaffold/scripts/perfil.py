"""Contrato do perfil local. Sem dependências externas; espelhado no JSON Schema."""
import json
from pathlib import Path, PurePosixPath
import re

CAMPOS = {'id', 'versao', 'estado', 'segmento', 'instancia', 'entrada', 'fontes',
          'comandos', 'agentes', 'mcps', 'arquivos', 'diretorios'}
FIXOS = {'id': 'jt-1g-local', 'versao': 1, 'segmento': 5, 'instancia': 1,
         'entrada': 'pdf-local', 'fontes': 'locais-conferidas'}
RAIZ_DESTINOS = {'README.md', 'CLAUDE.md', '.gitignore', 'requirements.txt'}
PREFIXOS_DESTINO = ('scripts/', '.claude/perfis/', '.claude/commands/',
                    '.claude/agents/', '.claude/skills/', '.claude/schemas/', '.claude/templates/')


def caminho_relativo(valor):
    if not isinstance(valor, str) or not valor or '\\' in valor or ':' in valor:
        raise ValueError(f'Caminho relativo inválido: {valor!r}')
    partes = valor.split('/')
    if any(parte in ('', '.', '..') or parte.rstrip(' .') != parte
           or any(ord(c) < 32 for c in parte) for parte in partes):
        raise ValueError(f'Caminho não canônico: {valor!r}')
    if any(parte.casefold() == '.git' for parte in partes):
        raise ValueError('Caminho .git não permitido.')
    # Evita dispositivos e nomes inválidos no Windows, mesmo validando no macOS/Linux.
    for parte in partes:
        if re.search(r'[<>"|?*]', parte) or re.fullmatch(
                r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', parte):
            raise ValueError(f'Nome de arquivo não portátil: {parte}')
    return PurePosixPath(valor)


def arquivo_do_pacote(raiz, relativo):
    caminho = caminho_relativo(relativo)
    raiz = Path(raiz).resolve()
    atual = raiz
    for parte in caminho.parts:
        atual = atual / parte
        if atual.is_symlink():
            raise ValueError(f'Link simbólico no pacote: {relativo}')
    if not atual.is_file() or not atual.resolve().is_relative_to(raiz):
        raise ValueError(f'Arquivo ausente ou fora do pacote: {relativo}')
    return atual


def validar_perfil(perfil, raiz_pacote=None):
    """Valida estrutura e, se fornecida a raiz, existência/isolamento das origens."""
    if not isinstance(perfil, dict) or set(perfil) != CAMPOS:
        raise ValueError('Campos do perfil ausentes ou desconhecidos.')
    for campo, esperado in FIXOS.items():
        if type(perfil[campo]) is not type(esperado) or perfil[campo] != esperado:
            raise ValueError(f'{campo}: valor ou versão não suportado.')
    if perfil['estado'] not in ('base-em-desenvolvimento', 'piloto'):
        raise ValueError('Estado do perfil inválido.')
    for campo in ('comandos', 'agentes', 'mcps', 'diretorios', 'arquivos'):
        if not isinstance(perfil[campo], list):
            raise ValueError(f'{campo} deve ser uma lista.')
    if perfil['mcps']:
        raise ValueError('O perfil local não instala servidores MCP.')
    destinos = set()
    for item in perfil['arquivos']:
        if not isinstance(item, dict) or set(item) != {'origem', 'destino'}:
            raise ValueError('Cada arquivo exige somente origem e destino.')
        origem, destino = item['origem'], item['destino']
        caminho_relativo(origem)
        caminho_relativo(destino)
        if not origem.startswith(('scaffold/', 'spec/schemas/')):
            raise ValueError(f'Origem fora das áreas distribuíveis: {origem}')
        if destino not in RAIZ_DESTINOS and not destino.startswith(PREFIXOS_DESTINO):
            raise ValueError(f'Destino não permitido: {destino}')
        chave = destino.casefold()
        if chave in destinos:
            raise ValueError(f'Destino duplicado: {destino}')
        destinos.add(chave)
        if raiz_pacote is not None:
            arquivo_do_pacote(raiz_pacote, origem)
    if not destinos:
        raise ValueError('Perfil sem arquivos.')
    obrigatorios = {'.claude/perfis/jt-1g-local.json', 'scripts/perfil.py',
                    'readme.md', 'claude.md', '.gitignore', 'requirements.txt',
                    '.claude/perfis/perfil.schema.json'}
    if not obrigatorios.issubset(destinos):
        raise ValueError('Perfil sem os componentes básicos obrigatórios.')
    for campo, pasta in (('comandos', '.claude/commands/'), ('agentes', '.claude/agents/')):
        nomes = perfil[campo]
        for nome in nomes:
            caminho_relativo(nome)
        esperados = {(pasta + nome + '.md').casefold() for nome in nomes}
        existentes = {d for d in destinos if d.startswith(pasta)}
        if len(esperados) != len(nomes) or esperados != existentes:
            raise ValueError(f'Lista de {campo} diverge dos arquivos do perfil.')
    diretorios = set()
    for nome in perfil['diretorios']:
        caminho_relativo(nome)
        if nome != 'data/casos':
            raise ValueError(f'Diretório não permitido: {nome}')
        if nome.casefold() in diretorios:
            raise ValueError('Diretório duplicado.')
        diretorios.add(nome.casefold())
    for nome in destinos | diretorios:
        pais = [p.as_posix() for p in PurePosixPath(nome).parents if p.as_posix() != '.']
        if any(p in destinos for p in pais) or nome in destinos & diretorios:
            raise ValueError(f'Conflito entre arquivo e diretório: {nome}')
    return perfil


def carregar_perfil(caminho, raiz_pacote=None):
    with Path(caminho).open(encoding='utf-8') as arquivo:
        perfil = json.load(arquivo)
    return validar_perfil(perfil, raiz_pacote)
