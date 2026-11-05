#!/usr/bin/env python3
"""Inventário, assinaturas e sessão exclusiva do pipeline local (macOS/Linux)."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import uuid

from documentos import agora, caminho_seguro, hash_arquivo, salvar_json, sem_links, validar_schema
from fontes_jt import conferir_corpus, ler_json

ETAPAS = ('ingestao', 'classificacao', 'relatorio', 'triagem', 'fontes', 'analise',
          'referencias_analise', 'redacao', 'referencias_minuta', 'revisao', 'publicacao')
SAIDAS = {
    'ingestao': ['caso.json', 'documentos.json'], 'classificacao': ['classificacao.json'],
    'relatorio': ['pedidos.json'], 'triagem': ['triagem.json'],
    'fontes': ['fontes-juridicas.json', 'regras-juridicas.json'], 'analise': ['matriz-pedidos.json'],
    'referencias_analise': ['referencias-analise.json'], 'redacao': ['redacao.json', 'minuta-candidata.md'],
    'referencias_minuta': ['referencias-candidata.json'], 'revisao': ['revisao.json'],
    'publicacao': ['minuta.md', 'referencias-minuta.json', 'publicacao.json']}


def pacote():
    raiz = Path(__file__).resolve().parent.parent
    instalado = raiz/'.claude/perfis/jt-1g-local.json'
    if instalado.is_file():
        manifesto = json.loads(instalado.read_text(encoding='utf-8'))
        return raiz, [i['destino'] for i in manifesto['arquivos']]
    raiz = raiz.parent
    manifesto = json.loads((raiz/'scaffold/perfis/jt-1g-local.json').read_text(encoding='utf-8'))
    return raiz, [i['origem'] for i in manifesto['arquivos']]


def hashes(raiz, nomes):
    return {n: hash_arquivo(caminho_seguro(raiz, n)) if caminho_seguro(raiz, n).is_file() else None for n in sorted(set(nomes))}


def arquivos_arvore(raiz, pasta):
    caminho = caminho_seguro(raiz, pasta)
    if not caminho.exists():
        return []
    arquivos = []
    for p in sorted(caminho.rglob('*')):
        sem_links(p)
        if p.is_file():
            arquivos.append(p.relative_to(raiz).as_posix())
    return arquivos


def calcular_assinatura_etapa(workspace, etapa):
    if etapa not in ETAPAS:
        raise ValueError('Etapa desconhecida.')
    raiz = sem_links(workspace)
    i = ETAPAS.index(etapa)
    anteriores = [n for e in ETAPAS[:i] for n in SAIDAS[e]]
    # Originais/textos também entram na assinatura: não confiar apenas no manifesto.
    anteriores += ['entrada-execucao.json']
    if etapa != 'ingestao':
        for pasta in ('originais', 'texto'):
            anteriores += arquivos_arvore(raiz, pasta)
    if i >= ETAPAS.index('fontes'):
        anteriores += arquivos_arvore(raiz, 'fontes')
    origem, nomes = pacote()
    dados = {'etapa': etapa, 'insumos': hashes(raiz, anteriores), 'pacote': hashes(origem, nomes)}
    entrada = caminho_seguro(raiz, 'entrada-execucao.json')
    if entrada.exists():
        registro = ler_json(raiz, entrada.name)
        externo = sem_links(registro['entrada'])
        if externo.is_dir():
            nomes = []
            for p in sorted(externo.rglob('*')):
                sem_links(p)
                if p.is_file() and p.suffix.lower() == '.pdf':
                    nomes.append(p.relative_to(externo).as_posix())
            dados['entrada_externa'] = hashes(externo, nomes)
        else:
            dados['entrada_externa'] = hash_arquivo(externo) if externo.is_file() else None
        caso = sem_links(registro['caso'])
        dados['caso_externo'] = hash_arquivo(caso) if caso.is_file() else None
    return hashlib.sha256(json.dumps(dados, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def invalidar_descendentes(estado, etapa):
    for nome in ETAPAS[ETAPAS.index(etapa)+1:]:
        item = estado['etapas'].get(nome)
        if item:
            item['estado'] = 'desatualizada'


def validar_etapa(raiz, etapa):
    from verificar_documentos import verificar as documentos
    from verificar_pedidos import verificar as pedidos
    from verificar_referencias_jt import verificar as referencias
    from verificar_sentenca_jt import verificar as sentenca, renderizar
    try:
        if any(not caminho_seguro(raiz, n).is_file() for n in SAIDAS[etapa]):
            return {'erros': ['Saída obrigatória ausente.'], 'pendencias': []}
        if etapa in ('ingestao', 'classificacao'):
            r = documentos(raiz, incluir_classificacao=etapa == 'classificacao')
            r['erros'].extend(conferir_entrada(raiz))
            return r
        if etapa in ('relatorio', 'triagem', 'analise'):
            return pedidos(raiz, etapa)
        if etapa == 'fontes':
            _, e, p = conferir_corpus(raiz)
            validar_schema(ler_json(raiz, 'regras-juridicas.json'), 'regra-juridica.schema.json')
            return {'erros': e, 'pendencias': p}
        if etapa == 'referencias_analise':
            return referencias(raiz, 'analise')
        if etapa == 'referencias_minuta':
            return sentenca(raiz, 'candidata')
        if etapa == 'redacao':
            r = sentenca(raiz, 'redacao')
            if caminho_seguro(raiz, 'minuta-candidata.md').read_bytes() != renderizar(ler_json(raiz, 'redacao.json')).encode():
                r['erros'].append('Candidata não corresponde à redação.')
            return r
        return sentenca(raiz, etapa)
    except (ValueError, OSError, KeyError, TypeError):
        return {'erros': ['Contrato, arquivo ou caminho inválido.'], 'pendencias': []}


def conferir_entrada(raiz):
    """Entrada externa alterada não pode ser aprovada apenas atualizando o estado."""
    if not caminho_seguro(raiz, 'entrada-execucao.json').exists():
        return []  # Verificadores também suportam acervo local anterior à fase 5.
    from ingerir_documentos import listar_pdfs
    registro = ler_json(raiz, 'entrada-execucao.json')
    if json.loads(sem_links(registro['caso']).read_text(encoding='utf-8')) != ler_json(raiz, 'caso.json'):
        return ['Metadados externos divergem do caso ingerido.']
    esperados = {n.casefold(): d['sha256'] for d in ler_json(raiz, 'documentos.json')['documentos'] for n in d['entradas']}
    arquivos = listar_pdfs(sem_links(registro['entrada']))
    atuais = {n.casefold(): hash_arquivo(p) for n, p in arquivos}
    return [] if atuais == esperados else ['PDFs externos divergem dos originais/aliases ingeridos; confira a ingestão.']


def passou(resultado):
    return not resultado['erros'] and not resultado['pendencias']


def caminho_lock(raiz):
    return raiz.parent/('.'+raiz.name+'.execucao.lock')


@contextmanager
def operacao(workspace, token=None):
    """Serializa comandos da mesma sessão; flock é liberado pelo SO após interrupção."""
    import fcntl
    raiz = sem_links(workspace)
    raiz.parent.mkdir(parents=True, exist_ok=True)
    caminho = sem_links(raiz.parent/('.'+raiz.name+'.operacao.lock'))
    with caminho.open('a') as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('Outra operação está em andamento neste caso.') from exc
        try:
            if token is not None:
                lock = json.loads(sem_links(caminho_lock(raiz)).read_text(encoding='utf-8'))
                if lock.get('token') != token:
                    raise ValueError('Token não corresponde à sessão exclusiva do caso.')
            yield raiz
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def iniciar(workspace):
    with operacao(workspace) as raiz:
        p = sem_links(caminho_lock(raiz))
        if p.exists():
            raise ValueError('Sessão existente ou bloqueio residual. Use diagnostico; não remova sem apurar a execução anterior.')
        token = uuid.uuid4().hex
        with p.open('x', encoding='utf-8') as f:
            json.dump({'token': token, 'inicio': agora(), 'host': socket.gethostname()}, f)
            f.flush(); os.fsync(f.fileno())
        return {'token': token, 'workspace': str(raiz)}


def diagnostico(workspace):
    p = sem_links(caminho_lock(sem_links(workspace)))
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'estado': 'sem-sessao'}


def encerrar(workspace, token, diagnostico_recuperacao=None):
    with operacao(workspace, token) as raiz:
        if diagnostico_recuperacao is not None:
            if not diagnostico_recuperacao.strip():
                raise ValueError('Diagnóstico explícito obrigatório.')
            # Registro permanente ao lado do caso, inclusive se a ingestão ainda não criou a pasta.
            salvar_json(raiz.parent/('.'+raiz.name+'.recuperacao-'+uuid.uuid4().hex+'.json'),
                        {'data': agora(), 'sessao': diagnostico(raiz), 'diagnostico': diagnostico_recuperacao})
        sem_links(caminho_lock(raiz)).unlink()
    return {'estado': 'sessao-encerrada'}


def carregar(raiz):
    arquivo = caminho_seguro(raiz, 'execucao.json')
    estado = ler_json(raiz, 'execucao.json') if arquivo.exists() else {'schema_version': 1, 'etapas': {}}
    if estado.get('schema_version') != 1 or not isinstance(estado.get('etapas'), dict) or set(estado['etapas']) - set(ETAPAS):
        raise ValueError('Estado de execução inválido.')
    return estado


def inventario_interno(raiz, estado):
    resultado = []
    anterior_valida = True
    for etapa in ETAPAS:
        assinatura = calcular_assinatura_etapa(raiz, etapa)
        item = estado['etapas'].get(etapa)
        if item and item.get('assinatura') != assinatura:
            item.update(estado='desatualizada', tentativas=0, assinatura=assinatura)
            invalidar_descendentes(estado, etapa)
        gate = validar_etapa(raiz, etapa) if anterior_valida else {'erros': [], 'pendencias': ['Etapa anterior pendente.']}
        valida = bool(anterior_valida and item and item.get('estado') == 'valida' and
                      item.get('saidas') == hashes(raiz, SAIDAS[etapa]) and passou(gate))
        if item and item.get('estado') == 'valida' and not valida:
            item['estado'] = 'desatualizada'; invalidar_descendentes(estado, etapa)
        resultado.append({'etapa': etapa, 'estado': 'valida' if valida else item.get('estado', 'pendente') if item else 'pendente',
                          'tentativas': item.get('tentativas', 0) if item else 0, 'erros': gate['erros'], 'pendencias': gate['pendencias']})
        anterior_valida = valida
    return resultado


def inventario(workspace, token):
    with operacao(workspace, token) as raiz:
        estado = carregar(raiz)
        itens = inventario_interno(raiz, estado)
        salvar_json(caminho_seguro(raiz, 'execucao.json'), estado)
        return {'etapas': itens, 'proxima': next((i['etapa'] for i in itens if i['estado'] != 'valida'), None),
                'aceite_humano': 'nao-registrado'}


def registrar_entrada(workspace, token, entrada, caso):
    with operacao(workspace, token) as raiz:
        dados = {'entrada': str(sem_links(entrada)), 'caso': str(sem_links(caso))}
        p = caminho_seguro(raiz, 'entrada-execucao.json')
        if p.exists() and ler_json(raiz, p.name) != dados:
            raise ValueError('Entrada já registrada com outro caminho; preserve o caso e use novo workspace.')
        salvar_json(p, dados)
    return dados


def transicao(workspace, token, etapa, concluir=False):
    if etapa not in ETAPAS:
        raise ValueError('Etapa desconhecida.')
    with operacao(workspace, token) as raiz:
        estado = carregar(raiz)
        itens = inventario_interno(raiz, estado)
        i = ETAPAS.index(etapa)
        if any(e['estado'] != 'valida' for e in itens[:i]):
            raise ValueError('Há etapas anteriores pendentes; consulte o inventário.')
        assinatura = calcular_assinatura_etapa(raiz, etapa)
        item = estado['etapas'].setdefault(etapa, {'estado': 'pendente', 'tentativas': 0, 'assinatura': assinatura})
        if concluir:
            if item['estado'] != 'executando' or item['assinatura'] != assinatura:
                raise ValueError('Etapa não iniciada ou insumos alterados durante a execução.')
            gate = validar_etapa(raiz, etapa)
            item.update(estado='valida' if passou(gate) else 'invalida' if gate['erros'] else 'bloqueada', saidas=hashes(raiz, SAIDAS[etapa]), fim=agora())
            resposta = {**item, 'gate': gate}
        else:
            if item['estado'] == 'valida':
                return {'estado': 'valida', 'acao': 'reutilizar'}
            if item['estado'] == 'executando' and item.get('sessao') == token:
                raise ValueError('Etapa já iniciada nesta sessão; conclua-a antes de repetir.')
            if item['estado'] == 'executando':
                # Após retomada explícita, a tentativa interrompida continua consumida.
                item['estado'] = 'interrompida'
            if item['tentativas'] >= 2:
                raise ValueError('Limite de duas tentativas atingido para estes insumos; diagnóstico necessário.')
            item.update(estado='executando', tentativas=item['tentativas']+1, assinatura=assinatura, inicio=agora(), sessao=token)
            invalidar_descendentes(estado, etapa)
            resposta = dict(item)
        salvar_json(caminho_seguro(raiz, 'execucao.json'), estado)
        return resposta


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('acao', choices=['iniciar', 'diagnostico', 'encerrar', 'recuperar', 'inventario', 'entrada', 'iniciar-etapa', 'concluir-etapa'])
    p.add_argument('workspace', type=Path); p.add_argument('--token'); p.add_argument('--etapa', choices=ETAPAS)
    p.add_argument('--entrada', type=Path); p.add_argument('--caso', type=Path)
    p.add_argument('--diagnostico'); p.add_argument('--confirmar-interrupcao', action='store_true')
    a = p.parse_args()
    try:
        if a.acao in ('iniciar', 'diagnostico'):
            r = iniciar(a.workspace) if a.acao == 'iniciar' else diagnostico(a.workspace)
        else:
            if not a.token: raise ValueError('Token obrigatório.')
            if a.acao == 'recuperar':
                if not a.confirmar_interrupcao or not a.diagnostico: raise ValueError('Confirme a interrupção anterior e registre o diagnóstico.')
                r = encerrar(a.workspace, a.token, a.diagnostico)
            elif a.acao == 'encerrar': r = encerrar(a.workspace, a.token)
            elif a.acao == 'inventario': r = inventario(a.workspace, a.token)
            elif a.acao == 'entrada':
                if not a.entrada or not a.caso: raise ValueError('Entrada e caso obrigatórios.')
                r = registrar_entrada(a.workspace, a.token, a.entrada, a.caso)
            else: r = transicao(a.workspace, a.token, a.etapa, a.acao == 'concluir-etapa')
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 1 if r.get('estado') in ('invalida', 'bloqueada') else 0
    except (ValueError, OSError, KeyError, TypeError) as e:
        print('Operação recusada: '+str(e), file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
