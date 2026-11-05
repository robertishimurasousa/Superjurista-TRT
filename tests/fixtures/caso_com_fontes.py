"""Corpus fictício compartilhado entre testes de fontes e minuta; sem valor jurídico."""
from datetime import date, timedelta
from caso_trabalhista import criar, gravar
from documentos import salvar_json
from fontes_jt import carregar_fonte
from importar_fontes_jt import importar, confirmar
from merge_fontes_jt import consolidar
from verificar_referencias_jt import contexto

def meta(tipo='precedente', orgao='TST', referencia='Referência inteiramente fictícia'):
    return {'origem': 'arquivo-oficial-local', 'tipo': tipo, 'orgao': orgao, 'referencia': referencia,
            'url_oficial': 'https://www.tst.jus.br/', 'data_consulta': date.today().isoformat(),
            'situacao': 'vigente', 'modalidade': 'tese-firmada' if tipo == 'precedente' else 'legislacao',
            'temas': ['jornada'], 'ambito': {'nivel': 'nacional', 'trt': None, 'categoria': None, 'territorio': None},
            'vigencia': {'inicio': '2025-01-01', 'fim': None}, 'contexto_temporal': 'SOMENTE TESTE, SEM VALOR JURIDICO.'}


def conferencia(fonte):
    return {'responsavel': 'Pessoa fictícia de teste', 'data': date.today().isoformat(),
            'valida_ate': (date.today()+timedelta(days=30)).isoformat(),
            'original_sha256': fonte['sha256'], 'texto_sha256': fonte['texto_sha256'],
            'metadados_sha256': fonte['metadados_sha256'], 'declaracao_origem_oficial': True}


def revisao():
    return {'estado': 'conferida', 'responsavel': 'Revisor fictício', 'data': date.today().isoformat(),
            'justificativa': 'Teste sintético de estrutura e vínculos; não é avaliação jurídica.'}


def criar_com_fontes(pasta, rito='ordinario'):
    workspace, rel, tri, regras, matriz = criar(pasta, rito=rito)
    ids, vinculos = [], []
    for i, regra in enumerate(regras['regras']):
        entrada = pasta/f'fonte-{i}.txt'
        entrada.write_text(regra['texto'], encoding='utf-8')
        metadata = meta('legislacao', regra['orgao'], regra['referencia']+str(i))
        metadata['temas'] = [regra['tema']]
        ident = importar(workspace, entrada, metadata)['id']
        fonte = carregar_fonte(workspace, ident)
        confirmar(workspace, ident, conferencia(fonte))
        ids.append(ident)
        regra.update(arquivo=fonte['texto'], sha256=fonte['texto_sha256'], url_oficial=metadata['url_oficial'])
        vinculos.append({'regra_id': regra['id'], 'fonte_id': ident, 'revisao_pertinencia': revisao()})
    gravar(workspace, rel, tri, regras, matriz)
    consolidar(workspace, ids)
    registro = {'schema_version': 1, **contexto(workspace), 'vinculos_regras': vinculos,
                    'referencias': [], 'revisao_cobertura': {'matriz': revisao(), 'minuta': None}}
    salvar_json(workspace/'referencias-minuta.json', registro)
    return workspace, ids, registro
