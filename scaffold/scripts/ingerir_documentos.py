#!/usr/bin/env python3
"""Copia PDFs locais e extrai texto por página sem modificar os originais."""
import argparse
import copy
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from documentos import (agora, caminho_seguro, hash_arquivo, salvar_json,
                        sem_links, validar_caso, validar_schema)
from verificar_documentos import verificar


def conversor_jt():
    raiz = Path(__file__).resolve().parent.parent
    candidatos = [raiz / '.claude/skills/converter-pdf/scripts/pdf_para_txt.py',
                  raiz / 'skills/converter-pdf/scripts/pdf_para_txt.py']
    caminho = next((p for p in candidatos if p.is_file()), None)
    if caminho is None:
        raise ValueError('Conversor não instalado.')
    spec = importlib.util.spec_from_file_location('conversor_jt', caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def versao_binario(comando):
    try:
        saida = subprocess.run(comando, capture_output=True, text=True, timeout=5, check=True)
        return (saida.stdout or saida.stderr).splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return 'indisponivel'


def listar_pdfs(entrada):
    entrada = sem_links(entrada)
    if entrada.is_file():
        arquivos = [(entrada.name, entrada)] if entrada.suffix.lower() == '.pdf' else []
    elif entrada.is_dir():
        arquivos = []
        for pasta, diretorios, nomes in os.walk(entrada, followlinks=False):
            for nome in diretorios + nomes:
                if (Path(pasta) / nome).is_symlink():
                    raise ValueError('A entrada contém link simbólico.')
            for nome in nomes:
                arquivo = Path(pasta) / nome
                if arquivo.suffix.lower() == '.pdf':
                    arquivos.append((arquivo.relative_to(entrada).as_posix(), arquivo))
    else:
        raise ValueError('Entrada inexistente.')
    arquivos.sort(key=lambda item: item[0].casefold())
    vistos = set()
    for nome, arquivo in arquivos:
        caminho_seguro(entrada.parent, nome)
        if nome.casefold() in vistos:
            raise ValueError('Nomes de entrada ambíguos entre maiúsculas e minúsculas.')
        vistos.add(nome.casefold())
    if not arquivos:
        raise ValueError('Nenhum PDF encontrado na entrada.')
    return arquivos


def ingerir(entrada, workspace, metadados):
    entrada, raiz, metadados = map(sem_links, (entrada, workspace, metadados))
    if raiz == entrada or raiz.is_relative_to(entrada) or entrada.is_relative_to(raiz):
        raise ValueError('Entrada e pasta de trabalho devem ser separadas.')
    caso = validar_caso(json.loads(metadados.read_text(encoding='utf-8')))
    arquivos = listar_pdfs(entrada)
    conversor = conversor_jt()
    dependencias = {nome: importlib.metadata.version(nome) for nome in
                   ('pdfplumber', 'pypdf', 'pdf2image', 'pytesseract', 'Pillow', 'jsonschema')}
    poppler = str(Path(conversor.POPPLER_PATH) / 'pdftoppm') if conversor.POPPLER_PATH else 'pdftoppm'
    dependencias.update(python=sys.version.split()[0],
                        conversor_sha256=hash_arquivo(conversor.__file__),
                        tesseract=versao_binario([os.environ.get('TESSERACT_CMD', 'tesseract'), '--version']),
                        poppler=versao_binario([poppler, '-v']))
    idioma = Path(os.environ.get('TESSDATA_PREFIX', '')) / 'por.traineddata'
    if os.environ.get('TESSDATA_PREFIX') and idioma.is_file():
        dependencias['por_sha256'] = hash_arquivo(idioma)
    raiz.parent.mkdir(parents=True, exist_ok=True)
    lock = raiz.parent / ('.' + raiz.name + '.ingestao.lock')
    try:
        descritor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError('Ingestão em andamento ou lock residual; confira antes de remover o lock.')
    os.close(descritor)
    criados = []
    try:
        existente = raiz.exists()
        if existente:
            atual = json.loads(caminho_seguro(raiz, 'caso.json').read_text(encoding='utf-8'))
            if atual != caso:
                raise ValueError('Metadados divergem do caso existente; use uma nova pasta de trabalho.')
            verificacao = verificar(raiz)
            if verificacao['erros']:
                raise ValueError('Integridade do caso existente comprometida; execute verificar_documentos.py.')
            indice = json.loads((raiz / 'documentos.json').read_text(encoding='utf-8'))
        else:
            indice = {'schema_version': 1, 'numero_cnj': caso['numero_cnj'],
                      'caso_sha256': '', 'documentos': [], 'historico': []}
        indice = copy.deepcopy(indice)
        with tempfile.TemporaryDirectory(prefix='.' + raiz.name + '-ingestao-', dir=raiz.parent) as pasta:
            stage = Path(pasta)
            if not existente:
                salvar_json(stage / 'caso.json', caso)
                indice['caso_sha256'] = hash_arquivo(stage / 'caso.json')
            documentos = {d['id']: d for d in indice['documentos']}
            aliases = {n.casefold(): d['id'] for d in documentos.values() for n in d['entradas']}
            declarados = {d['arquivo'].casefold(): d for d in caso['documentos']}
            eventos = []
            for nome, arquivo in arquivos:
                # O hash e a extração usam a mesma cópia, mesmo se a entrada mudar durante a leitura.
                copia = stage / '.entrada.pdf'
                with arquivo.open('rb') as origem, copia.open('xb') as destino:
                    shutil.copyfileobj(origem, destino)
                sha = hash_arquivo(copia)
                ident = 'DOC-' + sha
                declarado = declarados.get(nome.casefold())
                if nome.casefold() in aliases:
                    if aliases[nome.casefold()] != ident:
                        raise ValueError('Uma entrada já ingerida mudou de conteúdo; use outro nome para a revisão.')
                    copia.unlink()
                    continue
                if ident in documentos:
                    doc = documentos[ident]
                    if declarado and doc['classificacao'] == 'declarada' and (
                            declarado['tipo'] != doc['tipo'] or declarado.get('id_pje') != doc['id_pje']):
                        raise ValueError('Duplicata possui classificação ou ID PJe conflitante.')
                    if declarado:
                        doc.update(tipo=declarado['tipo'], id_pje=declarado.get('id_pje'),
                                   classificacao='declarada')
                    doc['entradas'].append(nome)
                    copia.unlink()
                    resultado = 'duplicado'
                else:
                    relativo = f'originais/{ident}.pdf'
                    original = stage / relativo
                    original.parent.mkdir(exist_ok=True)
                    copia.rename(original)
                    extraido = conversor.extrair_preservando_jt(original)
                    doc = {'id': ident, 'sha256': sha, 'original': relativo, 'entradas': [nome],
                           'ordem': len(documentos) + 1, 'estado': extraido['estado'],
                           'tipo': declarado['tipo'] if declarado else 'desconhecido',
                           'classificacao': 'declarada' if declarado else 'desconhecida',
                           'id_pje': declarado.get('id_pje') if declarado else None,
                           'paginas_total': extraido['paginas_total'], 'paginas': [],
                           'avisos': extraido['avisos']}
                    for pagina in extraido['paginas']:
                        registro = {k: pagina[k] for k in ('numero', 'metodo', 'estado', 'avisos')}
                        for tipo in ('bruto', 'normalizado'):
                            rel = f'texto/{ident}/pagina-{pagina["numero"]:04d}.{tipo}.txt'
                            texto = stage / rel
                            texto.parent.mkdir(parents=True, exist_ok=True)
                            texto.write_text(pagina[tipo], encoding='utf-8', newline='')
                            registro[f'texto_{tipo}'] = rel
                            registro[f'sha256_{tipo}'] = hash_arquivo(texto)
                        doc['paginas'].append(registro)
                    documentos[ident] = doc
                    indice['documentos'].append(doc)
                    resultado = 'ingerido'
                aliases[nome.casefold()] = ident
                eventos.append({'arquivo': nome, 'documento_id': ident, 'resultado': resultado})
            if eventos:
                indice['historico'].append({'data': agora(), 'conversor': conversor.VERSAO_PRESERVACAO,
                                           'dependencias': dependencias, 'entradas': eventos})
            validar_schema(indice, 'documentos.schema.json')
            if not existente:
                salvar_json(stage / 'documentos.json', indice)
                stage.rename(raiz)
            elif eventos:
                try:
                    for arquivo in sorted(stage.rglob('*')):
                        if not arquivo.is_file():
                            continue
                        destino = caminho_seguro(raiz, arquivo.relative_to(stage).as_posix())
                        destino.parent.mkdir(parents=True, exist_ok=True)
                        with destino.open('xb') as saida:
                            criados.append(destino)
                            with arquivo.open('rb') as origem:
                                shutil.copyfileobj(origem, saida)
                    salvar_json(raiz / 'documentos.json', indice)
                except Exception:
                    for arquivo in reversed(criados):
                        arquivo.unlink(missing_ok=True)
                    raise
        return verificar(raiz)
    finally:
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--caso', required=True, type=Path, help='Metadados confirmados em JSON')
    args = parser.parse_args()
    try:
        resultado = ingerir(args.input, args.workspace, args.caso)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0 if resultado['apto_tecnicamente'] else 1
    except (ValueError, OSError, ImportError) as erro:
        print(f'Ingestão não concluída: {erro}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
