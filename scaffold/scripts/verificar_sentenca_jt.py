#!/usr/bin/env python3
"""Gates da redação, revisão e publicação; não realiza julgamento nem aceite humano."""
import argparse
import json
from pathlib import Path
import sys

from documentos import caminho_seguro, hash_arquivo, sem_links, validar_schema
from fontes_jt import ler_json
from verificar_pipeline import _norm
from verificar_referencias_jt import verificar as referencias, regras_usadas

TEMAS = {'processo', 'honorarios', 'custas', 'gratuidade', 'atualizacao'}
ITENS = {'pedidos-provas', 'fontes', 'rito', 'honorarios', 'custas', 'gratuidade',
         'parametros-calculo', 'dispositivo'}
NA = {'honorarios', 'custas', 'gratuidade', 'parametros-calculo'}
DEPENDENCIAS = {'pedidos': 'pedidos.json', 'matriz': 'matriz-pedidos.json',
                'fontes': 'fontes-juridicas.json', 'referencias_analise': 'referencias-analise.json'}


def template(rito):
    raiz = Path(__file__).resolve().parent.parent
    pasta = raiz/'.claude/templates/jt' if (raiz/'.claude/templates/jt').is_dir() else raiz/'templates/jt'
    if rito not in ('ordinario', 'sumarissimo'):
        raise ValueError('Rito não suportado.')
    return sem_links(pasta/(rito+'.md')).read_text(encoding='utf-8')


def contexto(workspace):
    raiz = sem_links(workspace)
    caso = ler_json(raiz, 'caso.json')
    return {'numero_cnj': caso['numero_cnj'], 'rito': caso['rito'],
            **{k+'_sha256': hash_arquivo(caminho_seguro(raiz, v)) for k, v in DEPENDENCIAS.items()}}


def renderizar(redacao):
    """Montagem determinística; não interpreta ou completa o texto do agente."""
    blocos = lambda itens, chave: '\n\n'.join('### '+i[chave]+'\n\n'+i['texto'] for i in itens)
    parametros = '\n'.join(f"- {i['pedido_id']} / {i['nome']}: {i['valor']} (regras: {', '.join(i['regra_ids'])})"
                           for i in redacao['parametros']) or 'Nenhum parâmetro numérico definido na matriz. Conferir a revisão.'
    return template(redacao['rito']).format(numero_cnj=redacao['numero_cnj'],
        relatorio=redacao['relatorio'] or '', fundamentos=blocos(redacao['fundamentos'], 'pedido_id'),
        questoes=blocos(redacao['questoes_processuais'], 'tema'), parametros=parametros,
        dispositivo=blocos(redacao['dispositivo'], 'pedido_id')+'\n\n'+blocos(redacao['dispositivo_processual'], 'tema'))


def conferir_lista(itens, chave, esperados, local, erros):
    ids = [i[chave] for i in itens]
    if len(ids) != len(set(ids)) or set(ids) != esperados:
        erros.append(f'Cobertura incompleta, repetida ou desconhecida: {local}.')


def conferir_redacao(raiz, erros, pendencias):
    from estado_execucao import conferir_entrada
    if not caminho_seguro(raiz, 'classificacao.json').is_file():
        erros.append('Classificação documental obrigatória ausente.')
    erros.extend(conferir_entrada(raiz))
    base = referencias(raiz, 'analise')
    erros.extend(base['erros']); pendencias.extend(base['pendencias'])
    r = ler_json(raiz, 'redacao.json'); validar_schema(r, 'redacao.schema.json')
    for chave, valor in contexto(raiz).items():
        if r[chave] != valor:
            erros.append(f'Redação desatualizada ou identidade divergente: {chave}.')
    matriz = ler_json(raiz, 'matriz-pedidos.json')
    pedidos = {p['id'] for p in ler_json(raiz, 'pedidos.json')['pedidos']}
    conferir_lista(r['fundamentos'], 'pedido_id', pedidos, 'fundamentos', erros)
    conferir_lista(r['dispositivo'], 'pedido_id', pedidos, 'dispositivo', erros)
    conferir_lista(r['questoes_processuais'], 'tema', TEMAS, 'questões processuais', erros)
    conferir_lista(r['dispositivo_processual'], 'tema', TEMAS, 'dispositivo processual', erros)
    if r['rito'] == 'ordinario' and not (r['relatorio'] or '').strip():
        erros.append('Rito ordinário exige relatório.')
    # O relatório analítico permanece nos pedidos; o sumaríssimo não o insere automaticamente.
    if r['rito'] == 'sumarissimo' and r['relatorio'] is not None:
        erros.append('No modelo sumaríssimo, mantenha o relatório analítico em pedidos.json.')
    resultados = {'hipotese-deferimento': 'deferimento', 'hipotese-indeferimento': 'indeferimento', 'hipotese-parcial': 'parcial'}
    dispositivos = {i['pedido_id']: i for i in r['dispositivo']}
    parametros = []
    for a in matriz['analises']:
        esperado = resultados.get(a['conclusao']['resultado'])
        if esperado is None or dispositivos.get(a['pedido_id'], {}).get('resultado') != esperado:
            erros.append('Dispositivo diverge da conclusão da matriz: '+a['pedido_id'])
        for p in a['parametros']:
            if p['valor']['estado'] != 'informado':
                pendencias.append('Parâmetro ausente: '+a['pedido_id']+'/'+p['nome'])
            parametros.append({'pedido_id': a['pedido_id'], 'nome': p['nome'],
                               'valor': p['valor']['valor'], 'regra_ids': p['regra_ids']})
    ordenar = lambda itens: sorted(json.dumps(i, sort_keys=True, ensure_ascii=False) for i in itens)
    if ordenar(parametros) != ordenar(r['parametros']):
        erros.append('Parâmetros devem reproduzir exatamente os valores e regras da matriz.')
    pendencias.extend(r['pendencias'])
    return r


def contexto_revisao(raiz):
    return {'numero_cnj': ler_json(raiz, 'caso.json')['numero_cnj'],
            **{k+'_sha256': hash_arquivo(caminho_seguro(raiz, v)) for k, v in {
                'redacao': 'redacao.json', 'minuta': 'minuta-candidata.md',
                'referencias': 'referencias-candidata.json', 'matriz': 'matriz-pedidos.json'}.items()}}


def conferir_revisao(raiz, erros, pendencias):
    r = ler_json(raiz, 'revisao.json'); validar_schema(r, 'revisao.schema.json')
    for k, v in contexto_revisao(raiz).items():
        if r[k] != v:
            erros.append('Revisão desatualizada: '+k)
    conferir_lista(r['verificacoes'], 'item', ITENS, 'revisão', erros)
    pedidos = {p['id'] for p in ler_json(raiz, 'pedidos.json')['pedidos']}
    matriz = ler_json(raiz, 'matriz-pedidos.json')
    regras = regras_usadas(matriz)
    por_tema = {q['tema']: set(q['regra_ids']) for q in matriz['questoes_processuais']}
    for item in r['verificacoes']:
        if item['estado'] == 'pendente':
            pendencias.append('Revisão pendente: '+item['item'])
        if item['estado'] == 'nao-aplicavel' and item['item'] not in NA:
            erros.append('Revisão obrigatória não pode ser dispensada: '+item['item'])
        if set(item['pedido_ids']) - pedidos or set(item['regra_ids']) - regras:
            erros.append('Revisão com pedido/regra inexistente ou não analisado.')
        if item['item'] in ('pedidos-provas', 'dispositivo') and set(item['pedido_ids']) != pedidos:
            erros.append('Revisão não abrange todos os pedidos: '+item['item'])
        exigidas = (regras if item['item'] == 'fontes' else por_tema.get(item['item'], set()))
        if item['item'] == 'parametros-calculo':
            exigidas = por_tema['atualizacao'] | {r for a in matriz['analises'] for p in a['parametros'] for r in p['regra_ids']}
        if exigidas - set(item['regra_ids']):
            pendencias.append('Revisão sem cobertura da base normativa: '+item['item'])
    if r['resultado'] != 'sem-pendencias':
        pendencias.append('Revisor não liberou tecnicamente a candidata.')
    pendencias.extend(r['pendencias'])


def assinatura_publicacao(raiz):
    # Inclui implementação, perfil, prompts, fontes e documentos, além dos artefatos finais.
    from estado_execucao import calcular_assinatura_etapa
    return calcular_assinatura_etapa(raiz, 'publicacao')


def verificar(workspace, etapa='publicacao'):
    if etapa not in ('redacao', 'candidata', 'revisao', 'publicacao'):
        raise ValueError('Etapa desconhecida.')
    raiz = sem_links(workspace)
    erros, pendencias = [], []
    try:
        redacao = conferir_redacao(raiz, erros, pendencias)
        texto = renderizar(redacao)
        candidata = caminho_seguro(raiz, 'minuta-candidata.md')
        if etapa != 'redacao':
            if candidata.read_bytes() != texto.encode('utf-8'):
                erros.append('Minuta candidata diverge da montagem determinística.')
            normal = _norm(texto)
            if not normal.startswith('# minuta') or not normal.rstrip().endswith('aceite humano nao registrado.'):
                erros.append('Âncoras da minuta inválidas.')
            ref = referencias(raiz, 'candidata')
            erros.extend(ref['erros']); pendencias.extend(ref['pendencias'])
        if etapa in ('revisao', 'publicacao'):
            conferir_revisao(raiz, erros, pendencias)
        if etapa == 'publicacao':
            recibo = ler_json(raiz, 'publicacao.json')
            if recibo != {'schema_version': 1, 'assinatura': assinatura_publicacao(raiz),
                          'minuta_sha256': hash_arquivo(candidata), 'aceite_humano': 'nao-registrado'}:
                erros.append('Publicação desatualizada ou recibo inválido.')
            if caminho_seguro(raiz, 'minuta.md').read_bytes() != candidata.read_bytes():
                erros.append('Minuta publicada diverge da candidata revisada.')
            if caminho_seguro(raiz, 'referencias-minuta.json').read_bytes() != caminho_seguro(raiz, 'referencias-candidata.json').read_bytes():
                erros.append('Referências publicadas divergem da revisão.')
    except (ValueError, OSError, KeyError, TypeError):
        erros.append('Artefato ausente, contrato inválido ou caminho inseguro; confira os arquivos desta etapa.')
    erros = list(dict.fromkeys(erros)); pendencias = list(dict.fromkeys(pendencias))
    return {'etapa': etapa, 'erros': erros, 'pendencias': pendencias,
            'valido_tecnicamente': not erros and not pendencias,
            'estado': 'invalida' if erros else 'bloqueada' if pendencias else 'valida',
            'validacao_juridica': 'nao-realizada', 'aceite_humano': 'nao-registrado'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('workspace', type=Path)
    p.add_argument('--etapa', choices=['redacao', 'candidata', 'revisao', 'publicacao'], default='publicacao')
    p.add_argument('--contexto', choices=['redacao', 'revisao'])
    p.add_argument('--gate', action='store_true', help='Compatibilidade: todas as verificações já são gates estritos.')
    a = p.parse_args()
    try:
        r = (contexto(a.workspace) if a.contexto == 'redacao' else contexto_revisao(a.workspace)) if a.contexto else verificar(a.workspace, a.etapa)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if a.contexto or r['valido_tecnicamente'] else 1
    except (ValueError, OSError):
        print('Contexto indisponível: confira os insumos.', file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
