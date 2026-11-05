"""Identidade, integridade e conferência das fontes oficiais locais."""
from contextlib import contextmanager
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

from documentos import caminho_seguro, hash_arquivo, validar_caso, validar_schema
from normalizacao_fontes import normalizar_chave


def normalizar_texto(texto):
    return ' '.join(unicodedata.normalize('NFC', texto).split())


def hash_json(valor):
    return hashlib.sha256(json.dumps(valor, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def identidade(sha, metadados):
    return 'FON-' + hash_json({'sha256': sha, 'metadados': metadados})


def ler_json(raiz, nome):
    return json.loads(caminho_seguro(raiz, nome).read_text(encoding='utf-8'))


def caso_local(raiz):
    return validar_caso(ler_json(raiz, 'caso.json'))


def caminho_fonte(ident):
    if not re.fullmatch(r'FON-[a-f0-9]{64}', ident):
        raise ValueError('Identificador de fonte inválido.')
    return f'fontes/importadas/{ident}/fonte.json'


@contextmanager
def lock_fontes(raiz):
    pasta = caminho_seguro(raiz, 'fontes')
    pasta.mkdir(exist_ok=True)
    lock = caminho_seguro(raiz, 'fontes/.fontes.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('Operação em andamento ou lock residual; confira antes de remover o lock.')
    os.close(fd)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def validar_metadados(meta):
    validar_schema(meta, 'fonte-metadados.schema.json')
    url = urlsplit(meta['url_oficial'])
    host = (url.hostname or '').lower()
    if (url.scheme != 'https' or url.username or url.password or url.port not in (None, 443)
            or not host.endswith(('.gov.br', '.jus.br', '.leg.br'))):
        raise ValueError('URL deve usar HTTPS e domínio oficial brasileiro, sem credenciais.')
    modalidades = {'legislacao': {'legislacao'}, 'norma-coletiva': {'instrumento-coletivo'},
                   'precedente': {'acordao', 'sumula', 'oj', 'tese-firmada', 'tema-afetado', 'tema-suspenso'}}
    if meta['modalidade'] not in modalidades[meta['tipo']]:
        raise ValueError('Modalidade incompatível com o tipo da fonte.')
    ambito = meta['ambito']
    if ambito['nivel'] == 'nacional' and ambito['trt'] is not None:
        raise ValueError('Fonte nacional não deve declarar TRT regional.')
    if ambito['nivel'] == 'regional' and ambito['trt'] is None:
        raise ValueError('Fonte regional exige TRT.')
    if meta['tipo'] == 'norma-coletiva' and (ambito['nivel'] != 'coletivo' or
                                          not ambito['categoria'] or not ambito['territorio']):
        raise ValueError('Norma coletiva exige categoria e território.')
    if meta['tipo'] == 'precedente':
        orgao = meta['orgao']
        regional = re.fullmatch(r'TRT([1-9]|1[0-9]|2[0-4])', orgao)
        if orgao in ('STF', 'TST'):
            dominio = orgao.lower() + '.jus.br'
            if ambito['nivel'] != 'nacional':
                raise ValueError('Precedente STF/TST exige âmbito nacional neste contrato.')
        elif regional:
            numero = int(regional[1])
            dominio = f'trt{numero}.jus.br'
            if ambito['nivel'] != 'regional' or ambito['trt'] != numero:
                raise ValueError('Órgão e TRT da fonte divergem.')
        else:
            raise ValueError('Precedente do piloto deve identificar STF, TST ou TRT1 a TRT24.')
        if host != dominio and not host.endswith('.' + dominio):
            raise ValueError('Órgão do precedente diverge do domínio oficial.')
    inicio, fim = meta['vigencia']['inicio'], meta['vigencia']['fim']
    if inicio and fim and inicio > fim:
        raise ValueError('Vigência invertida.')
    if meta['data_consulta'] > date.today().isoformat():
        raise ValueError('Data de consulta no futuro.')
    return meta


def hashes_autos(raiz):
    indice = ler_json(raiz, 'documentos.json')
    validar_schema(indice, 'documentos.schema.json')
    return {d['sha256'] for d in indice['documentos']}


def conferir_fonte(raiz, fonte, caso, exigir_conferencia=True):
    validar_schema({'schema_version': 1, 'numero_cnj': caso['numero_cnj'], 'fontes': [fonte]}, 'fontes-juridicas.schema.json')
    meta = validar_metadados(fonte['metadados'])
    erros, pendencias = [], []
    ident = fonte['id']
    if ident != identidade(fonte['sha256'], meta) or fonte['metadados_sha256'] != hash_json(meta):
        erros.append(f'Identidade/metadados alterados: {ident}')
    prefixo = f'fontes/importadas/{ident}/'
    if fonte['original'] != prefixo + 'original.' + fonte['formato'] or fonte['texto'] != prefixo + 'texto.txt':
        erros.append(f'Caminhos de fonte incompatíveis: {ident}')
    for campo, chave in [('original', 'sha256'), ('texto', 'texto_sha256')]:
        arquivo = caminho_seguro(raiz, fonte[campo])
        if not arquivo.is_file() or hash_arquivo(arquivo) != fonte[chave]:
            erros.append(f'{campo} de fonte ausente ou alterado: {ident}')
    if fonte['sha256'] in hashes_autos(raiz):
        erros.append(f'Documento dos autos não é fonte oficial independente: {ident}')
    if fonte['estado'] != 'extraido':
        pendencias.append(f'Fonte com extração incompleta: {ident}')
    elif not erros and not caminho_seguro(raiz, fonte['texto']).read_text(encoding='utf-8').strip():
        erros.append(f'Fonte extraída sem texto: {ident}')
    if fonte['formato'] == 'pdf':
        total = fonte['paginas_total']
        original = caminho_seguro(raiz, fonte['original'])
        if original.is_file():
            from pypdf import PdfReader
            try:
                with original.open('rb') as arquivo:
                    pdf = PdfReader(arquivo)
                    if pdf.is_encrypted:
                        if fonte['estado'] != 'protegido':
                            erros.append(f'PDF protegido com estado incompatível: {ident}')
                    elif 1 <= len(pdf.pages) <= 5000:
                        if total != len(pdf.pages):
                            erros.append(f'Total de páginas diverge do PDF original: {ident}')
                    elif fonte['estado'] != 'corrompido':
                        erros.append(f'PDF fora dos limites de páginas: {ident}')
            except Exception:
                if fonte['estado'] != 'corrompido':
                    erros.append(f'PDF ilegível marcado como extraído: {ident}')
        if fonte['estado'] in ('extraido', 'parcial'):
            if not total or [p['numero'] for p in fonte['paginas']] != list(range(1, total+1)):
                erros.append(f'Cobertura de páginas da fonte incompleta: {ident}')
        elif total is not None or fonte['paginas']:
            erros.append(f'Páginas incompatíveis com estado da fonte: {ident}')
        paginas = []
        for p in fonte['paginas']:
            if p['texto'] != prefixo + f'pagina-{p["numero"]:04d}.txt':
                erros.append(f'Caminho de página inválido: {ident}')
            arquivo = caminho_seguro(raiz, p['texto'])
            if not arquivo.is_file() or hash_arquivo(arquivo) != p['sha256']:
                erros.append(f'Página da fonte alterada ou ausente: {ident}')
            else:
                paginas.append(arquivo.read_text(encoding='utf-8'))
            if p['estado'] != 'extraida':
                pendencias.append(f'Página da fonte não extraída: {ident}/{p["numero"]}')
        if not erros and '\n\n'.join(paginas) != caminho_seguro(raiz, fonte['texto']).read_text(encoding='utf-8'):
            erros.append(f'Texto integral diverge das páginas: {ident}')
    elif fonte['paginas_total'] is not None or fonte['paginas']:
        erros.append(f'TXT/HTML não usam paginação física: {ident}')
    if meta['situacao'] != 'vigente' or meta['modalidade'] in ('tema-afetado', 'tema-suspenso'):
        pendencias.append(f'Situação da fonte não autoriza uso como fundamento conferido: {ident}')
    if meta['ambito']['trt'] is not None and meta['ambito']['trt'] != caso['trt']:
        pendencias.append(f'Âmbito regional diverge do TRT do caso: {ident}')
    conferencia = fonte['conferencia']
    if conferencia is None:
        if exigir_conferencia:
            pendencias.append(f'Fonte sem conferência humana: {ident}')
    else:
        validar_schema(conferencia, 'conferencia-fonte.schema.json')
        if (conferencia['original_sha256'] != fonte['sha256'] or conferencia['texto_sha256'] != fonte['texto_sha256']
                or conferencia['metadados_sha256'] != fonte['metadados_sha256']):
            erros.append(f'Conferência não corresponde aos hashes da fonte: {ident}')
        hoje = date.today().isoformat()
        if not meta['data_consulta'] <= conferencia['data'] <= hoje or conferencia['valida_ate'] < conferencia['data']:
            erros.append(f'Datas de conferência inconsistentes: {ident}')
        if conferencia['valida_ate'] < hoje:
            pendencias.append(f'Conferência vencida: {ident}')
    return erros, pendencias


def carregar_fonte(raiz, ident):
    fonte = ler_json(raiz, caminho_fonte(ident))
    if not isinstance(fonte, dict) or fonte.get('id') != ident:
        raise ValueError('Fonte não corresponde à pasta de importação.')
    return fonte


def chave_duplicata(fonte):
    meta = fonte['metadados']
    return (meta['tipo'], normalizar_chave(meta['orgao']), normalizar_chave(meta['referencia']), fonte['sha256'])


def conferir_corpus(raiz):
    caso = caso_local(raiz)
    corpus = ler_json(raiz, 'fontes-juridicas.json')
    validar_schema(corpus, 'fontes-juridicas.schema.json')
    erros, pendencias, ids, chaves = [], [], set(), set()
    if corpus['numero_cnj'] != caso['numero_cnj']:
        erros.append('Corpus pertence a outro processo.')
    if not corpus['fontes']:
        pendencias.append('Corpus de fontes vazio.')
    for fonte in corpus['fontes']:
        chave = chave_duplicata(fonte)
        if fonte['id'] in ids or chave in chaves:
            erros.append('Fonte repetida ou versões conflitantes no corpus.')
        ids.add(fonte['id']); chaves.add(chave)
        e, p = conferir_fonte(raiz, fonte, caso)
        erros.extend(e); pendencias.extend(p)
        if carregar_fonte(raiz, fonte['id']) != fonte:
            erros.append(f'Corpus desatualizado em relação à importação: {fonte["id"]}')
    return corpus, erros, pendencias
