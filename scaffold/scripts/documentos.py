"""Contratos e operações comuns da ingestão; sem interpretação jurídica."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone

from cnj import validar_cnj
from perfil import caminho_relativo

TIPOS = ['peticao', 'defesa', 'replica', 'ata', 'jornada', 'contracheque', 'trct',
         'fgts', 'laudo', 'instrumento-coletivo', 'desconhecido']


def agora():
    return datetime.now(timezone.utc).isoformat()


def hash_arquivo(caminho):
    h = hashlib.sha256()
    with Path(caminho).open('rb') as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b''):
            h.update(bloco)
    return h.hexdigest()


def validar_schema(objeto, nome):
    from jsonschema import Draft202012Validator, FormatChecker
    scripts = Path(__file__).resolve().parent
    candidatos = [scripts.parent / '.claude/schemas' / nome,
                  scripts.parent.parent / 'spec/schemas' / nome]
    schema = next((p for p in candidatos if p.is_file()), None)
    if schema is None:
        raise ValueError(f'Schema não instalado: {nome}')
    validador = Draft202012Validator(json.loads(schema.read_text(encoding='utf-8')),
                                    format_checker=FormatChecker())
    erros = sorted(validador.iter_errors(objeto), key=lambda e: str(e.json_path))
    if erros:
        # Não imprime valores potencialmente sensíveis da instância.
        raise ValueError(f'{nome}: contrato inválido em {erros[0].json_path} ({erros[0].validator}).')


def validar_caso(caso):
    validar_schema(caso, 'caso.schema.json')
    dados = validar_cnj(caso['numero_cnj'], caso['trt'])
    if caso['unidade_codigo'] != dados['unidade_codigo']:
        raise ValueError('Unidade confirmada diverge do CNJ.')
    vistos = set()
    for item in caso['documentos']:
        caminho_relativo(item['arquivo'])
        nome = item['arquivo'].casefold()
        if not nome.endswith('.pdf') or nome in vistos:
            raise ValueError('Documento declarado inválido ou repetido.')
        vistos.add(nome)
    return caso


def caminho_seguro(raiz, relativo):
    caminho_relativo(relativo)
    atual = Path(raiz)
    for parte in Path(relativo).parts:
        atual = atual / parte
        if atual.is_symlink():
            raise ValueError(f'Link simbólico não permitido: {relativo}')
    if not atual.resolve().is_relative_to(Path(raiz).resolve()):
        raise ValueError('Arquivo fora da pasta de trabalho.')
    return atual


def sem_links(caminho):
    caminho = Path(os.path.abspath(caminho))
    for parte in [*reversed(caminho.parents), caminho]:
        if parte.is_symlink():
            raise ValueError('Use caminhos reais, sem links simbólicos.')
    return caminho


def salvar_json(caminho, objeto):
    caminho = Path(caminho)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=caminho.parent,
                                     prefix='.json-', delete=False) as f:
        temporario = Path(f.name)
        try:
            json.dump(objeto, f, ensure_ascii=False, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        except Exception:
            temporario.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporario, caminho)
    finally:
        temporario.unlink(missing_ok=True)
