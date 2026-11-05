#!/usr/bin/env python3
"""Importa arquivo oficial local ou registra sua conferência humana, sem acesso à rede."""
import argparse
import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import sys
import tempfile

from documentos import caminho_seguro, hash_arquivo, salvar_json, sem_links, validar_schema
from fontes_jt import (carregar_fonte, caso_local, conferir_fonte, hash_json, hashes_autos,
                       identidade, lock_fontes, caminho_fonte, validar_metadados)
from ingerir_documentos import conversor_jt


class TextoHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes, self.ignorados = [], []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'head', 'noscript', 'template', 'svg'):
            self.ignorados.append(tag)
        if not self.ignorados and tag in ('p', 'div', 'br', 'tr', 'li', 'h1', 'h2', 'h3', 'section'):
            self.partes.append('\n')

    def handle_endtag(self, tag):
        if self.ignorados and tag == self.ignorados[-1]:
            self.ignorados.pop()
        if not self.ignorados and tag in ('p', 'div', 'tr', 'li', 'td', 'th', 'section'):
            self.partes.append('\n')

    def handle_data(self, data):
        if not self.ignorados:
            self.partes.append(data)


def importar(workspace, entrada, metadados):
    raiz, entrada = sem_links(workspace), sem_links(entrada)
    caso = caso_local(raiz)
    validar_metadados(metadados)
    if entrada.is_relative_to(raiz):
        raise ValueError('Use arquivo oficial separado da pasta do caso e dos autos.')
    formato = entrada.suffix.lower().lstrip('.')
    if formato == 'htm':
        formato = 'html'
    if formato not in ('pdf', 'html', 'txt') or not entrada.is_file():
        raise ValueError('Entrada deve ser arquivo PDF, HTML ou TXT local.')
    with lock_fontes(raiz):
        pasta = caminho_seguro(raiz, 'fontes/importadas')
        pasta.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.importacao-', dir=pasta) as temporaria:
            stage = Path(temporaria)
            original = stage / ('original.' + formato)
            shutil.copyfile(entrada, original)
            sha = hash_arquivo(original)
            if sha in hashes_autos(raiz):
                raise ValueError('Arquivo dos autos não pode ser promovido a fonte oficial.')
            ident = identidade(sha, metadados)
            destino = caminho_seguro(raiz, f'fontes/importadas/{ident}')
            if destino.exists():
                atual = carregar_fonte(raiz, ident)
                erros, pendencias = conferir_fonte(raiz, atual, caso)
                if erros:
                    raise ValueError('Importação existente perdeu integridade; preserve-a e confira os arquivos.')
                return {'id': ident, 'erros': erros, 'pendencias': pendencias, 'reutilizada': True}
            prefixo = f'fontes/importadas/{ident}/'
            fonte = {'id': ident, 'metadados': copy.deepcopy(metadados), 'metadados_sha256': hash_json(metadados),
                     'formato': formato, 'original': prefixo+original.name, 'sha256': sha,
                     'estado': 'extraido', 'texto': prefixo+'texto.txt', 'texto_sha256': '',
                     'paginas_total': None, 'paginas': [], 'conferencia': None}
            if formato == 'pdf':
                extraido = conversor_jt().extrair_preservando_jt(original)
                fonte.update(estado=extraido['estado'], paginas_total=extraido['paginas_total'])
                textos = []
                for pagina in extraido['paginas']:
                    nome = f'pagina-{pagina["numero"]:04d}.txt'
                    (stage/nome).write_text(pagina['bruto'], encoding='utf-8', newline='')
                    fonte['paginas'].append({'numero': pagina['numero'], 'estado': pagina['estado'],
                                             'texto': prefixo+nome, 'sha256': hash_arquivo(stage/nome)})
                    textos.append(pagina['bruto'])
                texto = '\n\n'.join(textos)
            else:
                texto = original.read_text(encoding='utf-8-sig')
                if formato == 'html':
                    parser = TextoHTML(); parser.feed(texto); parser.close()
                    texto = ''.join(parser.partes).strip()
                if not texto.strip():
                    fonte['estado'] = 'parcial'
            (stage/'texto.txt').write_text(texto, encoding='utf-8', newline='')
            fonte['texto_sha256'] = hash_arquivo(stage/'texto.txt')
            validar_schema({'schema_version': 1, 'numero_cnj': caso['numero_cnj'], 'fontes': [fonte]}, 'fontes-juridicas.schema.json')
            salvar_json(stage/'fonte.json', fonte)
            stage.rename(destino)
        erros, pendencias = conferir_fonte(raiz, fonte, caso)
        return {'id': ident, 'erros': erros, 'pendencias': pendencias, 'reutilizada': False}


def confirmar(workspace, ident, conferencia):
    raiz = sem_links(workspace)
    caso = caso_local(raiz)
    validar_schema(conferencia, 'conferencia-fonte.schema.json')
    with lock_fontes(raiz):
        fonte = carregar_fonte(raiz, ident)
        # Conferência nova nunca corrige silenciosamente um original/texto adulterado.
        erros, _ = conferir_fonte(raiz, fonte, caso, exigir_conferencia=False)
        if erros:
            raise ValueError('Fonte com divergência de integridade; conferência recusada.')
        nova = {**fonte, 'conferencia': conferencia}
        erros, pendencias = conferir_fonte(raiz, nova, caso)
        if erros:
            raise ValueError('Conferência incompatível com hashes ou datas da importação.')
        if nova != fonte:
            salvar_json(caminho_seguro(raiz, caminho_fonte(ident)), nova)
        return {'id': ident, 'erros': [], 'pendencias': pendencias}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument('--input', type=Path)
    grupo.add_argument('--fonte')
    parser.add_argument('--metadados', type=Path)
    parser.add_argument('--conferencia', type=Path)
    args = parser.parse_args()
    if (args.input and (not args.metadados or args.conferencia)) or (args.fonte and (not args.conferencia or args.metadados)):
        parser.error('Use --input com --metadados, ou --fonte com --conferencia.')
    try:
        caminho = sem_links(args.metadados or args.conferencia)
        dados = json.loads(caminho.read_text(encoding='utf-8'))
        resultado = importar(args.workspace, args.input, dados) if args.input else confirmar(args.workspace, args.fonte, dados)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 1 if resultado['erros'] or resultado['pendencias'] else 0
    except (ValueError, OSError, ImportError):
        print('Importação/conferência recusada: confira contrato, origem, hashes, datas e caminhos.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
