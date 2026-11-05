#!/usr/bin/env python3
"""Verifica integridade, cobertura e pendências do acervo local."""
import argparse
import json
from pathlib import Path
import sys

from documentos import (caminho_seguro, hash_arquivo, sem_links,
                        validar_caso, validar_schema)


def verificar(workspace):
    raiz = sem_links(workspace)
    caso_path = caminho_seguro(raiz, 'caso.json')
    caso = validar_caso(json.loads(caso_path.read_text(encoding='utf-8')))
    indice = json.loads(caminho_seguro(raiz, 'documentos.json').read_text(encoding='utf-8'))
    validar_schema(indice, 'documentos.schema.json')
    erros, pendencias = [], list(caso['pendencias'])
    if indice['numero_cnj'] != caso['numero_cnj'] or indice['caso_sha256'] != hash_arquivo(caso_path):
        erros.append('Metadados do caso divergem do registro da ingestão.')
    docs, entradas = {}, set()
    for ordem, doc in enumerate(indice['documentos'], 1):
        ident = doc['id']
        if ident in docs or ident != 'DOC-' + doc['sha256'] or doc['ordem'] != ordem:
            erros.append(f'Identidade ou ordem inválida: {ident}')
        docs[ident] = doc
        for entrada in doc['entradas']:
            caminho_seguro(raiz, entrada)
            if entrada.casefold() in entradas:
                erros.append('Uma entrada está associada mais de uma vez.')
            entradas.add(entrada.casefold())
        original = f'originais/{ident}.pdf'
        if doc['original'] != original:
            erros.append(f'Caminho original inválido: {ident}')
        arquivo = caminho_seguro(raiz, doc['original'])
        if not arquivo.is_file() or hash_arquivo(arquivo) != doc['sha256']:
            erros.append(f'Original ausente ou alterado: {ident}')
        else:
            from pypdf import PdfReader
            try:
                with arquivo.open('rb') as f:
                    pdf = PdfReader(f)
                    if pdf.is_encrypted:
                        if doc['estado'] != 'protegido':
                            erros.append(f'Proteção incompatível com o índice: {ident}')
                    else:
                        total_real = len(pdf.pages)
                        if not 1 <= total_real <= 5000:
                            if doc['estado'] != 'corrompido':
                                erros.append(f'PDF fora dos limites marcado como legível: {ident}')
                        elif total_real != doc['paginas_total']:
                            erros.append(f'Total de páginas diverge do PDF: {ident}')
            except Exception:
                if doc['estado'] != 'corrompido':
                    erros.append(f'PDF ilegível marcado como legível: {ident}')
        total = doc['paginas_total']
        if doc['estado'] in ('extraido', 'parcial'):
            if not total or [p['numero'] for p in doc['paginas']] != list(range(1, total + 1)):
                erros.append(f'Cobertura de páginas incompleta: {ident}')
        elif total is not None or doc['paginas']:
            erros.append(f'Páginas incompatíveis com o estado do documento: {ident}')
        if doc['estado'] != 'extraido':
            pendencias.append(f'{ident}: {doc["estado"]}')
        for pagina in doc['paginas']:
            numero = pagina['numero']
            if pagina['estado'] != 'extraida':
                pendencias.append(f'{ident}, página {numero}: {pagina["estado"]}')
                if doc['estado'] == 'extraido':
                    erros.append(f'Estado do documento omite falha de página: {ident}')
            for tipo in ('bruto', 'normalizado'):
                relativo = pagina[f'texto_{tipo}']
                esperado = f'texto/{ident}/pagina-{numero:04d}.{tipo}.txt'
                if relativo != esperado:
                    erros.append(f'Referência de texto inválida: {ident}, página {numero}')
                texto = caminho_seguro(raiz, relativo)
                if not texto.is_file() or hash_arquivo(texto) != pagina[f'sha256_{tipo}']:
                    erros.append(f'Texto ausente ou alterado: {ident}, página {numero}, {tipo}')
                elif pagina['estado'] == 'extraida' and not texto.read_text(encoding='utf-8').strip():
                    erros.append(f'Página vazia marcada como extraída: {ident}, página {numero}')
    if not docs:
        pendencias.append('Nenhum PDF ingerido.')
    for declarado in caso['documentos']:
        if declarado['obrigatorio'] and declarado['arquivo'].casefold() not in entradas:
            pendencias.append(f'Documento declarado ausente: {declarado["arquivo"]}')
        for doc in docs.values():
            if declarado['arquivo'].casefold() in {n.casefold() for n in doc['entradas']}:
                if (doc['classificacao'] != 'declarada' or doc['tipo'] != declarado['tipo']
                        or doc['id_pje'] != declarado.get('id_pje')):
                    erros.append('Classificação ou ID PJe diverge dos metadados confirmados.')
    historico_aliases, origens = set(), []
    for evento in indice['historico']:
        for entrada in evento['entradas']:
            doc = docs.get(entrada['documento_id'])
            if doc is None or entrada['arquivo'] not in doc['entradas']:
                erros.append('Histórico aponta para documento ou entrada inexistente.')
            if entrada['arquivo'].casefold() in historico_aliases:
                erros.append('Histórico repete uma entrada já registrada.')
            historico_aliases.add(entrada['arquivo'].casefold())
            if entrada['resultado'] == 'ingerido':
                origens.append(entrada['documento_id'])
    if historico_aliases != entradas or len(origens) != len(docs) or set(origens) != set(docs):
        erros.append('Histórico não registra a origem de todas as entradas e documentos.')
    classificacao = caminho_seguro(raiz, 'classificacao.json')
    if classificacao.exists():
        segmentos = json.loads(classificacao.read_text(encoding='utf-8'))
        validar_schema(segmentos, 'classificacao.schema.json')
        cobertas = set()
        for segmento in segmentos['segmentos']:
            doc = docs.get(segmento['documento_id'])
            inicio, fim = segmento['pagina_inicio'], segmento['pagina_fim']
            if doc is None or not doc['paginas_total'] or not 1 <= inicio <= fim <= doc['paginas_total']:
                erros.append('Classificação aponta para páginas inexistentes.')
                continue
            for numero in range(inicio, fim + 1):
                ref = (doc['id'], numero)
                if ref in cobertas:
                    erros.append('Classificação contém páginas sobrepostas.')
                cobertas.add(ref)
        esperadas = {(d['id'], p['numero']) for d in docs.values() for p in d['paginas']}
        if cobertas != esperadas:
            erros.append('Classificação não cobre todas as páginas registradas.')
    return {'erros': erros, 'pendencias': pendencias,
            'apto_tecnicamente': not erros and not pendencias}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('--gate', action='store_true', help='Retornar 1 também para pendências')
    args = parser.parse_args()
    try:
        resultado = verificar(args.workspace)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 1 if resultado['erros'] or (args.gate and resultado['pendencias']) else 0
    except (ValueError, OSError, ImportError) as erro:
        print(f'Falha na verificação: {type(erro).__name__}. Confira contratos, caminhos e dependências.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
