"""Caso inteiramente fictício para verificar contratos; não contém orientação jurídica."""
import copy
import json
from pathlib import Path
from reportlab.pdfgen import canvas
from documentos import hash_arquivo, salvar_json
from ingerir_documentos import ingerir

TEXTO = ['CASO INTEIRAMENTE FICTICIO - SEM VALOR JURIDICO',
         'Ana Ficticia contra Empresa Alfa Ficticia e Empresa Beta Ficticia.',
         'Empregadores privados. Demanda individual. Conhecimento. Rito ordinario.',
         'Contrato: 2025-01-01 a 2025-12-31. Funcao: atendente. Salario: 2000.00.',
         'Categoria comercio. Territorio Florianopolis. Jornada contestada por ambas as empresas.',
         'Pedido de horas extras e reflexos. Defesa Alfa: horario regular.',
         'Defesa Beta: nega responsabilidade. Competencia trabalhista a conferir.',
         'Ata ficticia de 2026-01-15. Testemunha relata jornada de 08 a 18 horas.',
         'Instrumento coletivo ficticio de 2025-01-01 a 2025-12-31: comercio em Florianopolis.']


def criar(pasta):
    entrada = pasta / 'entrada'
    entrada.mkdir()
    pdf = canvas.Canvas(str(entrada / 'autos.pdf'), invariant=1)
    for i, linha in enumerate(TEXTO):
        pdf.drawString(30, 800-i*25, linha)
    pdf.save()
    caso = json.loads((Path(__file__).parent / 'jt/caso.json').read_text())
    caso['documentos'] = [{'arquivo': 'autos.pdf', 'tipo': 'desconhecido', 'obrigatorio': True}]
    salvar_json(pasta / 'caso.json', caso)
    workspace = pasta / 'workspace'
    ingerir(entrada, workspace, pasta / 'caso.json')
    doc = json.loads((workspace / 'documentos.json').read_text())['documentos'][0]['id']
    referencia = {'documento_id': doc, 'pagina': 1, 'trecho': TEXTO[0]}

    def dado(valor, linha=0):
        return {'estado': 'informado', 'valor': valor,
                'referencias': [{**referencia, 'trecho': TEXTO[linha]}], 'motivo': None}

    ausente = {'estado': 'nao-informado', 'valor': None, 'referencias': [], 'motivo': 'Não consta do conjunto fictício.'}
    periodo = {'inicio': dado('2025-01-01', 3), 'fim': dado('2025-12-31', 3)}
    defesas = [{'reclamada_id': 'PAR-002', 'alegacao': dado('Horário regular.', 5)},
               {'reclamada_id': 'PAR-003', 'alegacao': dado('Nega responsabilidade.', 6)}]
    pedido = {'id': 'PED-001', 'natureza': 'principal', 'principal_id': None, 'tema': 'jornada',
              'descricao': dado('Horas extras.', 5), 'reclamante_id': 'PAR-001',
              'reclamadas_ids': ['PAR-002', 'PAR-003'], 'contratos_ids': ['CON-001'],
              'periodo': periodo, 'valor': copy.deepcopy(ausente),
              'fatos': [dado('Jornada controvertida.', 4)], 'defesas': defesas,
              'norma_coletiva': {'necessaria': False, 'justificativa': dado('Sem aplicação coletiva nesta hipótese de teste.', 8),
                                 'documento_id': None, 'vigencia': {'inicio': copy.deepcopy(ausente), 'fim': copy.deepcopy(ausente)},
                                 'categoria': copy.deepcopy(ausente), 'territorio': copy.deepcopy(ausente)}}
    partes = [{'id': 'PAR-001', 'polo': 'reclamante', 'nome': dado('Ana Ficticia', 1), 'natureza': dado('pessoa-fisica', 1)}]
    for i, nome in [(2, 'Empresa Alfa Ficticia'), (3, 'Empresa Beta Ficticia')]:
        partes.append({'id': f'PAR-{i:03d}', 'polo': 'reclamado', 'nome': dado(nome, 1), 'natureza': dado('empregador-privado', 2)})
    rel = {'schema_version': 1, 'numero_cnj': caso['numero_cnj'], 'documentos_sha256': hash_arquivo(workspace / 'documentos.json'),
           'partes': partes, 'contratos': [{'id': 'CON-001', 'reclamante_id': 'PAR-001',
             'reclamadas_ids': ['PAR-002', 'PAR-003'], 'periodo': periodo, 'funcao': dado('atendente', 3),
             'salario': dado('2000.00', 3), 'categoria': dado('comercio', 4), 'territorio': dado('Florianopolis', 4)}],
           'pedidos': [pedido], 'atos_audiencia': [{'id': 'ATO-001', 'tipo': dado('Ata', 7), 'data': dado('2026-01-15', 7), 'descricao': dado('Depoimento fictício.', 7)}],
           'cobertura': [{'documento_id': doc, 'pagina': 1, 'estado': 'revisada', 'pedidos_ids': ['PED-001'], 'observacao': 'Leitura sintética integral.'}],
           'conferencia_inventario': {'estado': 'conferida', 'responsavel': 'Revisor fictício de teste', 'data': '2026-01-16'}, 'pendencias': []}
    tri = {'schema_version': 1, 'numero_cnj': caso['numero_cnj'], 'pedidos_sha256': '0'*64,
           'escopo': {k: {'estado': 'confirmado', 'justificativa': dado('Conferência fictícia de escopo.', 2)} for k in
                     ['competencia', 'rito', 'fase', 'demanda_individual', 'empregadores_privados']},
           'questoes': [{'pedido_id': 'PED-001', 'estado': 'apta', 'motivos': [],
                        'provas_necessarias': [{'descricao': 'Ata fictícia.', 'decisiva': True, 'estado': 'disponivel', 'referencias': [referencia]}],
                        'fontes_necessarias': ['Regra de jornada e ônus aplicável ao período.']}], 'estado': 'apta', 'pendencias': []}
    regras = {'schema_version': 1, 'regras': []}
    temas = ['jornada', 'onus', 'processo', 'honorarios', 'custas', 'gratuidade', 'atualizacao']
    (workspace / 'fontes').mkdir()
    for i, tema in enumerate(temas, 1):
        texto = f'REGRA SINTETICA DE TESTE {tema}. NAO E FONTE JURIDICA REAL.'
        caminho = f'fontes/regra-{i}.txt'
        (workspace / caminho).write_text(texto, encoding='utf-8')
        regras['regras'].append({'id': f'REG-{i:03d}', 'tema': tema, 'tipo': 'legislacao',
                                'referencia': 'Referência fictícia', 'orgao': 'Órgão fictício',
                                'url_oficial': 'https://www.tst.jus.br/', 'arquivo': caminho,
                                'sha256': hash_arquivo(workspace / caminho), 'texto': texto,
                                'vigencia': {'inicio': '2025-01-01', 'fim': None}, 'situacao': 'vigente',
                                'conferencia': {'estado': 'conferida', 'responsavel': 'Responsável fictício', 'data': '2026-01-16'},
                                'contexto_temporal': 'Somente teste de estrutura; não representa regra jurídica.'})
    analise = {'pedido_id': 'PED-001', 'estado': 'analisada',
               'fatos': [{'descricao': dado('Alegação de jornada.', 4), 'situacao': 'controvertido'}],
               'defesas': copy.deepcopy(defesas), 'provas': [referencia],
               'onus': {'atribuicao': 'reclamante', 'justificativa': 'Hipótese fictícia para teste.', 'regra_ids': ['REG-002'], 'decisao_referencias': []},
               'regra_ids': ['REG-001'], 'parametros': [],
               'norma_coletiva': {'estado': 'nao-necessaria', 'justificativa': 'Teste sem norma coletiva necessária.', 'documento_id': None},
               'conclusao': {'resultado': 'hipotese-parcial', 'fundamentacao': 'Hipótese fictícia sem efeito jurídico.', 'regra_ids': ['REG-001'], 'referencias': [referencia]},
               'pendencias': []}
    matriz = {'schema_version': 1, 'numero_cnj': caso['numero_cnj'], 'pedidos_sha256': '0'*64,
              'triagem_sha256': '0'*64, 'regras_sha256': '0'*64, 'analises': [analise],
              'questoes_processuais': [{'tema': tema, 'estado': 'analisada', 'analise': 'Exame fictício para teste.', 'regra_ids': [f'REG-{i:03d}'], 'referencias': [referencia]} for i, tema in enumerate(temas[2:], 3)],
              'pendencias': []}
    return workspace, rel, tri, regras, matriz


def gravar(workspace, rel, tri, regras, matriz):
    salvar_json(workspace / 'pedidos.json', rel)
    tri['pedidos_sha256'] = hash_arquivo(workspace / 'pedidos.json')
    salvar_json(workspace / 'triagem.json', tri)
    salvar_json(workspace / 'regras-juridicas.json', regras)
    matriz['pedidos_sha256'] = tri['pedidos_sha256']
    matriz['triagem_sha256'] = hash_arquivo(workspace / 'triagem.json')
    matriz['regras_sha256'] = hash_arquivo(workspace / 'regras-juridicas.json')
    salvar_json(workspace / 'matriz-pedidos.json', matriz)
