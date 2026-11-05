#!/usr/bin/env python3
"""Verifica fontes, vínculos de regras e citações localizadas na matriz/minuta."""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys

from documentos import caminho_seguro, hash_arquivo, sem_links, validar_schema
from fontes_jt import conferir_corpus, ler_json, normalizar_texto
from verificar_pedidos import verificar as verificar_pedidos

LEGAL = re.compile(r'\b(?:CLT|CPC|CF\s*/?\s*88|Constitui[çc][ãa]o|art(?:s|igo|igos)?\.?\s*\d+|'
                   r'Lei\s+(?:n[ºo°.]*\s*)?\d+|S[úu]mula\b|OJ\s*\d+|Tema\s*\d+|'
                   r'ADC\s*\d+|ADI\s*\d+|IRR\b|STF\b|TST\b|TRT\s*\d*\b)|https?://[^\s<>]+', re.IGNORECASE)
ASPAS = re.compile(r'"[^"\n]+"|“[^”]+”|«[^»]+»|^\s*>[^\n]+', re.MULTILINE)
PALAVRAS = re.compile(r'\w+', re.UNICODE)


def alvos_matriz(valor, caminho=''):
    """Campos discursivos; metadados, IDs e transcrições usadas só como evidência não são minuta."""
    saida = {}
    if isinstance(valor, dict):
        for chave, item in valor.items():
            ponteiro = caminho + '/' + chave.replace('~', '~0').replace('/', '~1')
            if isinstance(item, str) and chave in ('valor', 'fundamentacao', 'justificativa', 'analise'):
                saida[('matriz', ponteiro)] = item
            elif chave not in ('referencias', 'provas', 'decisao_referencias'):
                saida.update(alvos_matriz(item, ponteiro))
    elif isinstance(valor, list):
        for i, item in enumerate(valor):
            saida.update(alvos_matriz(item, caminho+'/'+str(i)))
    return saida


def regras_usadas(valor):
    saida = set()
    if isinstance(valor, dict):
        for chave, item in valor.items():
            if chave == 'regra_ids':
                saida.update(item)
            else:
                saida.update(regras_usadas(item))
    elif isinstance(valor, list):
        for item in valor:
            saida.update(regras_usadas(item))
    return saida


def conferir_revisao(revisao, local, erros, pendencias):
    if revisao['estado'] != 'conferida':
        pendencias.append(f'Revisão de pertinência/cobertura pendente: {local}')
    elif revisao['data'] > date.today().isoformat():
        erros.append(f'Revisão no futuro: {local}')


def arquivos_alvo(modo):
    if modo not in ('padrao', 'analise', 'candidata'):
        raise ValueError('Modo de referências inválido.')
    return {'padrao': ('referencias-minuta.json', 'minuta.md'),
            'analise': ('referencias-analise.json', None),
            'candidata': ('referencias-candidata.json', 'minuta-candidata.md')}[modo]


def contexto(workspace, modo='padrao'):
    _, minuta = arquivos_alvo(modo)
    raiz = sem_links(workspace)
    resultado = {'numero_cnj': ler_json(raiz, 'caso.json')['numero_cnj']}
    for chave, arquivo in [('fontes', 'fontes-juridicas.json'), ('documentos', 'documentos.json'),
                           ('pedidos', 'pedidos.json'), ('matriz', 'matriz-pedidos.json'),
                           ('regras', 'regras-juridicas.json'), ('minuta', minuta)]:
        if arquivo is None:
            resultado[chave+'_sha256'] = None
            continue
        caminho = caminho_seguro(raiz, arquivo)
        resultado[chave+'_sha256'] = hash_arquivo(caminho) if caminho.is_file() else None
    return resultado


def verificar(workspace, modo='padrao'):
    arquivo_registro, arquivo_minuta = arquivos_alvo(modo)
    raiz = sem_links(workspace)
    erros, pendencias = [], []
    obrigatorios = ['fontes-juridicas.json', arquivo_registro, 'regras-juridicas.json', 'matriz-pedidos.json']
    for nome in obrigatorios:
        if not caminho_seguro(raiz, nome).is_file():
            erros.append(f'Artefato ausente: {nome}')
    if erros:
        return resultado(erros, pendencias)
    base = verificar_pedidos(raiz)
    erros.extend(base['erros']); pendencias.extend(base['pendencias'])
    # Referências nunca contornam falhas de integridade da análise ou dos autos.
    if erros:
        return resultado(erros, pendencias)
    corpus, e, p = conferir_corpus(raiz)
    erros.extend(e); pendencias.extend(p)
    if erros:
        return resultado(erros, pendencias)
    registro = ler_json(raiz, arquivo_registro)
    validar_schema(registro, 'referencias-minuta.schema.json')
    atual = contexto(raiz, modo)
    for campo, valor in atual.items():
        if registro[campo] != valor:
            erros.append(f'Referências desatualizadas: {campo}')
    matriz = ler_json(raiz, 'matriz-pedidos.json')
    regras = {r['id']: r for r in ler_json(raiz, 'regras-juridicas.json')['regras']}
    fontes = {f['id']: f for f in corpus['fontes']}
    textos_fontes = {ident: caminho_seguro(raiz, f['texto']).read_text(encoding='utf-8') for ident, f in fontes.items()}
    usadas, vinculadas = regras_usadas(matriz), set()
    for vinculo in registro['vinculos_regras']:
        ident, fonte_id = vinculo['regra_id'], vinculo['fonte_id']
        if ident in vinculadas:
            erros.append(f'Regra vinculada mais de uma vez: {ident}')
        vinculadas.add(ident)
        conferir_revisao(vinculo['revisao_pertinencia'], ident, erros, pendencias)
        regra, fonte = regras.get(ident), fontes.get(fonte_id)
        if regra is None or fonte is None:
            erros.append(f'Vínculo aponta para regra/fonte inexistente: {ident}')
            continue
        meta = fonte['metadados']
        if (regra['arquivo'] != fonte['texto'] or regra['sha256'] != fonte['texto_sha256'] or
                regra['url_oficial'] != meta['url_oficial'] or regra['orgao'] != meta['orgao'] or
                regra['tipo'] != meta['tipo'] or regra['tema'] not in meta['temas']):
            erros.append(f'Regra não deriva da fonte oficial vinculada: {ident}')
        if normalizar_texto(regra['texto']) not in normalizar_texto(textos_fontes[fonte_id]):
            erros.append(f'Trecho de regra ausente da fonte vinculada: {ident}')
        for limite in ('inicio', 'fim'):
            fonte_limite, regra_limite = meta['vigencia'][limite], regra['vigencia'][limite]
            if fonte_limite and (not regra_limite or (limite == 'inicio' and regra_limite < fonte_limite)
                                or (limite == 'fim' and regra_limite > fonte_limite)):
                pendencias.append(f'Regra amplia vigência declarada da fonte: {ident}')
    if vinculadas != usadas:
        erros.append('Vínculos não correspondem exatamente às regras usadas na matriz.')
    alvos = alvos_matriz(matriz)
    minuta = caminho_seguro(raiz, arquivo_minuta) if arquivo_minuta else None
    if modo == 'candidata' and not minuta.is_file():
        erros.append('Minuta candidata ausente.')
    if minuta is not None and minuta.exists():
        alvos[('minuta', '')] = minuta.read_text(encoding='utf-8')
        if registro['revisao_cobertura']['minuta'] is None:
            pendencias.append('Minuta sem revisão de cobertura das citações.')
        else:
            conferir_revisao(registro['revisao_cobertura']['minuta'], 'minuta', erros, pendencias)
    elif registro['revisao_cobertura']['minuta'] is not None:
        erros.append('Revisão de minuta declarada sem minuta local.')
    conferir_revisao(registro['revisao_cobertura']['matriz'], 'matriz', erros, pendencias)
    docs = {d['id']: d for d in ler_json(raiz, 'documentos.json')['documentos']}
    coberturas, vistos = {}, set()
    for citacao in registro['referencias']:
        ident = citacao['id']
        if ident in vistos:
            erros.append(f'ID de citação repetido: {ident}')
        vistos.add(ident)
        chave = (citacao['alvo'], citacao['ponteiro'])
        texto = alvos.get(chave)
        inicio, fim = citacao['inicio'], citacao['fim']
        if texto is None or not 0 <= inicio < fim <= len(texto) or texto[inicio:fim] != citacao['trecho']:
            erros.append(f'Localizador/trecho de destino inválido: {ident}')
            continue
        intervalos = coberturas.setdefault(chave, [])
        if any(inicio < b and fim > a for a, b in intervalos):
            erros.append(f'Registros sobrepostos: {ident}')
        intervalos.append((inicio, fim))
        conferir_revisao(citacao['revisao_pertinencia'], ident, erros, pendencias)
        uso, natureza = citacao['tipo_uso'], citacao['natureza']
        if uso == 'nao-citacao':
            if natureza != 'nenhuma' or any(citacao[c] is not None for c in ('fonte_id', 'documento_id', 'pagina', 'trecho_origem')):
                erros.append(f'Dispensa de citação possui origem indevida: {ident}')
            if LEGAL.search(citacao['trecho']):
                pendencias.append(f'Menção jurídica exige fonte ou relato de alegação, não dispensa: {ident}')
            continue
        origem = None
        if natureza == 'fonte' and citacao['documento_id'] is None:
            fonte = fontes.get(citacao['fonte_id'])
            if fonte is not None:
                if fonte['formato'] == 'pdf':
                    pagina = next((p for p in fonte['paginas'] if p['numero'] == citacao['pagina']), None)
                    if pagina:
                        origem = caminho_seguro(raiz, pagina['texto']).read_text(encoding='utf-8')
                elif citacao['pagina'] is None:
                    origem = textos_fontes[fonte['id']]
            if uso == 'relato-alegacao':
                erros.append(f'Relato de alegação exige prova dos autos: {ident}')
        elif natureza == 'prova' and citacao['fonte_id'] is None:
            doc = docs.get(citacao['documento_id'])
            pagina = next((p for p in doc['paginas'] if p['numero'] == citacao['pagina']), None) if doc else None
            if pagina:
                origem = caminho_seguro(raiz, pagina['texto_bruto']).read_text(encoding='utf-8')
            if LEGAL.search(citacao['trecho']) and uso != 'relato-alegacao':
                pendencias.append(f'Citação jurídica dos autos não substitui fonte oficial: {ident}')
        if origem is None:
            erros.append(f'Origem ou página da citação inexistente/incompatível: {ident}')
            continue
        trecho_origem = citacao['trecho_origem']
        if not trecho_origem or normalizar_texto(trecho_origem) not in normalizar_texto(origem):
            erros.append(f'Trecho de origem não encontrado: {ident}')
        elif uso == 'direta' and normalizar_texto(citacao['trecho']) != normalizar_texto(trecho_origem):
            erros.append(f'Citação direta não corresponde literalmente à origem: {ident}')
    # Varredura conservadora: expressões jurídicas, aspas e passagens literais sem aspas.
    corpus_palavras = [' ' + ' '.join(PALAVRAS.findall(t.casefold())) + ' ' for t in textos_fontes.values()]
    for chave, texto in alvos.items():
        candidatos = [(m.start(), m.end()) for m in LEGAL.finditer(texto)]
        for m in ASPAS.finditer(texto):
            prefixo = re.match(r'\s*>\s*', m.group())
            candidatos.append((m.start()+prefixo.end(), m.end()) if prefixo else (m.start()+1, m.end()-1))
        tokens = list(PALAVRAS.finditer(texto))
        for i in range(max(0, len(tokens)-7)):
            frase = ' ' + ' '.join(t.group().casefold() for t in tokens[i:i+8]) + ' '
            if any(frase in t for t in corpus_palavras):
                candidatos.append((tokens[i].start(), tokens[i+7].end()))
        for inicio, fim in candidatos:
            intervalos = coberturas.get(chave, [])
            if not any(a <= inicio and b >= fim for a, b in intervalos):
                pendencias.append(f'Possível citação/menção sem registro: {chave[0]}{chave[1]}:{inicio}-{fim}')
    return resultado(erros, pendencias)


def resultado(erros, pendencias):
    erros, pendencias = list(dict.fromkeys(erros)), list(dict.fromkeys(pendencias))
    return {'erros': erros, 'pendencias': pendencias, 'sem_pendencias': not erros and not pendencias,
            'apto_para_minuta': False, 'validacao_juridica': 'nao-realizada',
            'dependencias_posteriores': ['minuta-e-revisao-fase-5']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument('--gate', action='store_true')
    modo.add_argument('--contexto', action='store_true', help='Exibir hashes atuais; não aprova etapas')
    parser.add_argument('--alvo', choices=['padrao', 'analise', 'candidata'], default='padrao')
    args = parser.parse_args()
    try:
        saida = contexto(args.workspace, args.alvo) if args.contexto else verificar(args.workspace, args.alvo)
        print(json.dumps(saida, ensure_ascii=False, indent=2))
        return 0 if args.contexto else 1 if saida['erros'] or (args.gate and saida['pendencias']) else 0
    except (ValueError, OSError, ImportError):
        print('Verificação recusada: confira schemas, arquivos, caminhos e hashes.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
