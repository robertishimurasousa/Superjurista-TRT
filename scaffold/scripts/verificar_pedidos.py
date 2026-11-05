#!/usr/bin/env python3
"""Confere inventário, triagem e análise provisória, sem decidir o mérito."""
import argparse
from datetime import date
import json
from pathlib import Path
import sys
import unicodedata
from urllib.parse import urlsplit

from documentos import caminho_seguro, hash_arquivo, sem_links, validar_schema
from verificar_documentos import verificar as verificar_documentos

TEMAS_PROCESSUAIS = {'processo', 'honorarios', 'custas', 'gratuidade', 'atualizacao'}


def normalizar(texto):
    return ' '.join(unicodedata.normalize('NFC', texto).split())


def ler(raiz, nome, schema=None):
    valor = json.loads(caminho_seguro(raiz, nome).read_text(encoding='utf-8'))
    if schema:
        validar_schema(valor, schema)
    return valor


def contexto(workspace):
    raiz = sem_links(workspace)
    resultado = verificar_documentos(raiz)
    if resultado['erros']:
        raise ValueError('Corrija a integridade documental antes de preparar a análise.')
    caso = ler(raiz, 'caso.json')
    saida = {'numero_cnj': caso['numero_cnj'], 'pendencias_documentais': resultado['pendencias']}
    for campo, arquivo in [('documentos', 'documentos.json'), ('pedidos', 'pedidos.json'),
                           ('triagem', 'triagem.json'), ('regras', 'regras-juridicas.json')]:
        caminho = caminho_seguro(raiz, arquivo)
        saida[campo + '_sha256'] = hash_arquivo(caminho) if caminho.is_file() else None
    return saida


class Conferencia:
    def __init__(self, workspace):
        self.raiz = sem_links(workspace)
        documental = verificar_documentos(self.raiz)
        self.erros = list(documental['erros'])
        self.pendencias = list(documental['pendencias'])
        self.lacunas = []
        self.caso = ler(self.raiz, 'caso.json')
        self.docs = {d['id']: d for d in ler(self.raiz, 'documentos.json')['documentos']}
        self.textos = {}

    def resultado(self):
        erros, pendencias = list(dict.fromkeys(self.erros)), list(dict.fromkeys(self.pendencias))
        return {'estado': 'invalida' if erros else 'bloqueada' if pendencias else 'valida',
                'erros': erros, 'pendencias': pendencias, 'lacunas': self.lacunas,
                'valido_tecnicamente': not erros, 'sem_pendencias': not erros and not pendencias,
                'apto_para_minuta': False, 'validacao_juridica': 'nao-realizada',
                'aceite_humano': 'nao-registrado',
                'dependencias_posteriores': ['fontes-juridicas-fase-4', 'minuta-e-revisao-fase-5']}

    def carregar(self, nome, schema):
        if not caminho_seguro(self.raiz, nome).is_file():
            self.erros.append(f'Artefato ausente: {nome}')
            return None
        valor = ler(self.raiz, nome, schema)
        if 'numero_cnj' in valor and valor['numero_cnj'] != self.caso['numero_cnj']:
            self.erros.append(f'Identidade do caso divergente: {nome}')
        self.referencias(valor, nome)
        return valor

    def hash(self, valor, campo, nome):
        caminho = caminho_seguro(self.raiz, nome)
        atual = hash_arquivo(caminho) if caminho.is_file() else None
        if valor[campo] != atual:
            self.erros.append(f'Artefato desatualizado: {campo} diverge de {nome}')

    def referencias(self, valor, local):
        if isinstance(valor, list):
            for i, item in enumerate(valor):
                self.referencias(item, f'{local}[{i}]')
        elif isinstance(valor, dict):
            if valor.get('estado') == 'nao-informado':
                self.lacunas.append(local)
            if set(valor) == {'documento_id', 'pagina', 'trecho'}:
                doc = self.docs.get(valor['documento_id'])
                pagina = next((p for p in doc['paginas'] if p['numero'] == valor['pagina']), None) if doc else None
                if pagina is None:
                    self.erros.append(f'Referência inexistente: {local}')
                else:
                    if pagina['estado'] != 'extraida':
                        self.pendencias.append(f'Referência usa página não extraída: {local}')
                    chave = (doc['id'], pagina['numero'])
                    if chave not in self.textos:
                        caminho = caminho_seguro(self.raiz, pagina['texto_bruto'])
                        self.textos[chave] = normalizar(caminho.read_text(encoding='utf-8'))
                    if normalizar(valor['trecho']) not in self.textos[chave]:
                        self.erros.append(f'Trecho não encontrado na página indicada: {local}')
            for chave, item in valor.items():
                self.referencias(item, f'{local}.{chave}')

    def unicos(self, itens, campo, local):
        mapa = {}
        for item in itens:
            if item[campo] in mapa:
                self.erros.append(f'ID duplicado: {local}/{item[campo]}')
            mapa[item[campo]] = item
        return mapa

    def cobertura_ids(self, itens, esperados, campo, local):
        mapa = self.unicos(itens, campo, local)
        if set(mapa) != set(esperados):
            self.erros.append(f'Pedidos omitidos ou estranhos ao inventário: {local}')
        return mapa

    def necessario(self, dado, local):
        if dado['estado'] != 'informado':
            self.pendencias.append(f'Dado necessário não informado: {local}')

    def periodo(self, periodo, local):
        inicio, fim = periodo['inicio']['valor'], periodo['fim']['valor']
        if inicio and fim and inicio > fim:
            self.erros.append(f'Período invertido: {local}')

    def conferir_data(self, conferencia, local):
        if conferencia['estado'] != 'conferida':
            self.pendencias.append(f'Conferência humana pendente: {local}')
        elif conferencia['data'] > date.today().isoformat():
            self.erros.append(f'Conferência no futuro: {local}')

    def relatorio(self, rel):
        self.hash(rel, 'documentos_sha256', 'documentos.json')
        self.pendencias.extend(rel['pendencias'])
        self.conferir_data(rel['conferencia_inventario'], 'inventário de pedidos')
        partes = self.unicos(rel['partes'], 'id', 'partes')
        contratos = self.unicos(rel['contratos'], 'id', 'contratos')
        pedidos = self.unicos(rel['pedidos'], 'id', 'pedidos')
        self.unicos(rel['atos_audiencia'], 'id', 'atos de audiência')
        if not pedidos:
            self.pendencias.append('Inventário sem pedidos; conferir a petição e os aditamentos.')
        reclamantes = {p['id'] for p in partes.values() if p['polo'] == 'reclamante'}
        reclamadas = {p['id'] for p in partes.values() if p['polo'] == 'reclamado'}
        if len(reclamantes) != 1 or not reclamadas:
            self.pendencias.append('Recorte exige demanda individual com reclamante e reclamadas identificados.')
        for p in partes.values():
            self.necessario(p['nome'], p['id'] + '/nome')
            self.necessario(p['natureza'], p['id'] + '/natureza')
            if p['polo'] == 'reclamado' and p['natureza']['valor'] != 'empregador-privado':
                self.pendencias.append('Natureza da reclamada incerta ou fora do recorte de empregadores privados.')
            if p['polo'] == 'reclamante' and p['natureza']['valor'] != 'pessoa-fisica':
                self.pendencias.append('Natureza do reclamante incerta ou fora do recorte individual de pessoa física.')
        for grupo in (contratos, pedidos):
            for ident, item in grupo.items():
                if item['reclamante_id'] not in reclamantes or not set(item['reclamadas_ids']) <= reclamadas:
                    self.erros.append(f'Parte inexistente ou polo incompatível: {ident}')
                self.periodo(item['periodo'], ident)
        assinaturas = set()
        for ident, pedido in pedidos.items():
            self.necessario(pedido['descricao'], ident + '/descricao')
            for i, fato in enumerate(pedido['fatos']):
                self.necessario(fato, f'{ident}/fatos/{i}')
            principal = pedido['principal_id']
            if pedido['natureza'] == 'principal' and principal is not None:
                self.erros.append(f'Pedido principal não pode depender de outro: {ident}')
            if pedido['natureza'] == 'acessorio':
                pai = pedidos.get(principal)
                if not pai or pai['natureza'] != 'principal' or pai['reclamante_id'] != pedido['reclamante_id']:
                    self.erros.append(f'Vínculo principal/acessório inválido: {ident}')
            envolvidos = set()
            periodos = []
            for contrato_id in pedido['contratos_ids']:
                contrato = contratos.get(contrato_id)
                if contrato is None or contrato['reclamante_id'] != pedido['reclamante_id']:
                    self.erros.append(f'Contrato inexistente ou de outra parte: {ident}')
                    continue
                envolvidos.update(contrato['reclamadas_ids'])
                periodos.append(contrato['periodo'])
                campos = ['funcao'] if pedido['tema'] in ('vinculo', 'jornada') else ['salario']
                for campo in campos:
                    self.necessario(contrato[campo], f'{ident}/{contrato_id}/{campo}')
            if not set(pedido['reclamadas_ids']) <= envolvidos:
                self.erros.append(f'Reclamadas sem vínculo com contratos indicados: {ident}')
            pi, pf = pedido['periodo']['inicio']['valor'], pedido['periodo']['fim']['valor']
            conhecidos = [(p['inicio']['valor'], p['fim']['valor']) for p in periodos
                          if p['inicio']['valor'] and p['fim']['valor']]
            if pi and pf and conhecidos and len(conhecidos) == len(periodos):
                if all(pf < inicio or pi > fim for inicio, fim in conhecidos):
                    self.pendencias.append(f'Período do pedido não coincide com os contratos; conferir: {ident}')
            self.necessario(pedido['periodo']['inicio'], ident + '/periodo/inicio')
            if pedido['tema'] != 'vinculo':
                self.necessario(pedido['periodo']['fim'], ident + '/periodo/fim')
            if pedido['tema'] == 'outro':
                self.pendencias.append(f'Matéria fora do recorte requer triagem bloqueada: {ident}')
            defesas = self.unicos(pedido['defesas'], 'reclamada_id', ident + '/defesas')
            if set(defesas) != set(pedido['reclamadas_ids']):
                self.erros.append(f'Defesa omitida ou atribuída a parte estranha: {ident}')
            for defesa in defesas.values():
                self.necessario(defesa['alegacao'], ident + '/defesa/' + defesa['reclamada_id'])
            norma = pedido['norma_coletiva']
            self.periodo(norma['vigencia'], ident + '/norma-coletiva')
            if norma['necessaria']:
                doc = self.docs.get(norma['documento_id'])
                if doc is None:
                    self.pendencias.append(f'Instrumento coletivo necessário ausente: {ident}')
                    if norma['documento_id'] is not None:
                        self.erros.append(f'Referência a instrumento coletivo inexistente: {ident}')
                for campo in ('categoria', 'territorio', 'justificativa'):
                    self.necessario(norma[campo], ident + '/norma-coletiva/' + campo)
                for campo in ('inicio', 'fim'):
                    self.necessario(norma['vigencia'][campo], ident + '/vigencia/' + campo)
                for c in pedido['contratos_ids']:
                    if c in contratos:
                        for campo in ('categoria', 'territorio'):
                            if (norma[campo]['valor'] and contratos[c][campo]['valor']
                                    and normalizar(norma[campo]['valor']) != normalizar(contratos[c][campo]['valor'])):
                                self.pendencias.append(f'Âmbito coletivo diverge do contrato; conferir aplicabilidade: {ident}/{campo}')
                ni, nf = norma['vigencia']['inicio']['valor'], norma['vigencia']['fim']['valor']
                pi, pf = pedido['periodo']['inicio']['valor'], pedido['periodo']['fim']['valor']
                if ni and nf and pi and pf and (ni > pi or nf < pf):
                    self.pendencias.append(f'Instrumento coletivo não cobre integralmente o período; separar intervalos: {ident}')
            elif norma['documento_id'] is not None:
                self.erros.append(f'Instrumento coletivo indicado como desnecessário mas vinculado: {ident}')
            assinatura = json.dumps([normalizar(pedido['descricao']['valor'] or '').casefold(), pedido['tema'],
                                      pedido['reclamante_id'], sorted(pedido['reclamadas_ids']),
                                      pedido['periodo']['inicio']['valor'], pedido['periodo']['fim']['valor']])
            if assinatura in assinaturas:
                self.pendencias.append(f'Possível pedido duplicado; diferenciar objeto ou período: {ident}')
            assinaturas.add(assinatura)
        esperadas = {(d['id'], p['numero']) for d in self.docs.values() for p in d['paginas']}
        vistas = set()
        pedidos_cobertos = set()
        for pagina in rel['cobertura']:
            chave = (pagina['documento_id'], pagina['pagina'])
            if chave in vistas or chave not in esperadas:
                self.erros.append('Cobertura com página repetida ou inexistente.')
            vistas.add(chave)
            if pagina['estado'] != 'revisada':
                self.pendencias.append('Leitura dos autos ainda pendente.')
            if not set(pagina['pedidos_ids']) <= set(pedidos):
                self.erros.append('Cobertura aponta para pedido inexistente.')
            pedidos_cobertos.update(pagina['pedidos_ids'])
        if vistas != esperadas:
            self.erros.append('Cobertura do relatório não contabiliza todas as páginas.')
        if pedidos_cobertos != set(pedidos):
            self.erros.append('Inventário contém pedido sem página na cobertura.')
        return pedidos

    def triagem(self, tri, pedidos):
        self.hash(tri, 'pedidos_sha256', 'pedidos.json')
        self.pendencias.extend(tri['pendencias'])
        questoes = self.cobertura_ids(tri['questoes'], pedidos, 'pedido_id', 'triagem')
        bloqueio = bool(self.pendencias)
        for campo, avaliacao in tri['escopo'].items():
            if avaliacao['estado'] != 'confirmado' or avaliacao['justificativa']['estado'] != 'informado':
                self.pendencias.append(f'Escopo não confirmado: {campo}')
                bloqueio = True
        for ident, q in questoes.items():
            impede = pedidos.get(ident, {}).get('tema') == 'outro'
            for prova in q['provas_necessarias']:
                if prova['estado'] == 'disponivel' and not prova['referencias']:
                    self.erros.append(f'Prova disponível sem referência: {ident}')
                if prova['decisiva'] and prova['estado'] != 'disponivel':
                    self.pendencias.append(f'Prova decisiva indisponível: {ident}')
                    impede = True
            if impede and q['estado'] != 'bloqueada':
                self.erros.append(f'Triagem libera questão impedida: {ident}')
            if q['estado'] == 'bloqueada':
                bloqueio = True
                self.pendencias.append(f'Questão bloqueada na triagem: {ident}')
                if not q['motivos']:
                    self.erros.append(f'Bloqueio sem motivo: {ident}')
            elif q['motivos']:
                self.erros.append(f'Questão apta com motivos de bloqueio: {ident}')
        if bloqueio and tri['estado'] != 'bloqueada':
            self.erros.append('Triagem geral libera caso com impedimentos.')
        if tri['estado'] == 'bloqueada':
            self.pendencias.append('Triagem geral bloqueada.')
        return questoes

    def regras(self, registro):
        regras = self.unicos(registro['regras'], 'id', 'regras') if registro else {}
        validas = set()
        for ident, regra in regras.items():
            url = urlsplit(regra['url_oficial'])
            host = (url.hostname or '').lower()
            if url.scheme != 'https' or url.username or url.password or not host.endswith(('.gov.br', '.jus.br', '.leg.br')):
                self.erros.append(f'URL de regra fora de domínio oficial: {ident}')
                continue
            inicio, fim = regra['vigencia']['inicio'], regra['vigencia']['fim']
            if inicio and fim and inicio > fim:
                self.erros.append(f'Vigência invertida: {ident}')
                continue
            arquivo = regra['arquivo']
            if regra['conferencia']['estado'] != 'conferida' or regra['situacao'] != 'vigente':
                continue
            self.conferir_data(regra['conferencia'], ident)
            if regra['conferencia']['data'] > date.today().isoformat():
                continue
            if not arquivo or not regra['sha256']:
                self.erros.append(f'Regra conferida sem conteúdo local e hash: {ident}')
                continue
            caminho = caminho_seguro(self.raiz, arquivo)
            if not arquivo.startswith('fontes/') or caminho.suffix != '.txt':
                self.erros.append(f'Regra deve apontar para texto UTF-8 local em fontes/: {ident}')
                continue
            if not caminho.is_file() or hash_arquivo(caminho) != regra['sha256']:
                self.erros.append(f'Conteúdo da regra ausente ou alterado: {ident}')
                continue
            if normalizar(regra['texto']) not in normalizar(caminho.read_text(encoding='utf-8')):
                self.erros.append(f'Texto da regra não consta da fonte local: {ident}')
                continue
            validas.add(ident)
        return regras, validas

    def analise(self, matriz, pedidos, tri, questoes, regras, validas):
        for campo, nome in [('pedidos_sha256', 'pedidos.json'), ('triagem_sha256', 'triagem.json'),
                            ('regras_sha256', 'regras-juridicas.json')]:
            self.hash(matriz, campo, nome)
        self.pendencias.extend(matriz['pendencias'])
        analises = self.cobertura_ids(matriz['analises'], pedidos, 'pedido_id', 'matriz')

        def conferir_regras(ids, local):
            for ident in ids:
                if ident not in regras:
                    self.erros.append(f'Regra inexistente: {local}/{ident}')
                elif ident not in validas:
                    self.pendencias.append(f'Regra não conferida ou situação impeditiva: {local}/{ident}')

        for ident, analise in analises.items():
            pedido = pedidos.get(ident)
            if pedido is None:
                continue
            self.pendencias.extend(analise['pendencias'])
            for fato in analise['fatos']:
                self.necessario(fato['descricao'], ident + '/análise/fatos')
                if fato['situacao'] == 'corroborado' and fato['descricao']['estado'] != 'informado':
                    self.erros.append(f'Fato ausente marcado como corroborado: {ident}')
            defesas = self.unicos(analise['defesas'], 'reclamada_id', ident + '/análise/defesas')
            if set(defesas) != set(pedido['reclamadas_ids']):
                self.erros.append(f'Análise omite defesa ou inclui parte estranha: {ident}')
            for defesa in defesas.values():
                self.necessario(defesa['alegacao'], ident + '/análise/defesa/' + defesa['reclamada_id'])
            onus, conclusao = analise['onus'], analise['conclusao']
            grupos = [analise['regra_ids'], onus['regra_ids'], conclusao['regra_ids']]
            grupos += [p['regra_ids'] for p in analise['parametros']]
            for ids in grupos:
                conferir_regras(ids, ident)
            usadas = {r for grupo in grupos for r in grupo}
            for r in usadas & set(regras):
                inicio, fim = regras[r]['vigencia']['inicio'], regras[r]['vigencia']['fim']
                pi, pf = pedido['periodo']['inicio']['valor'], pedido['periodo']['fim']['valor']
                if (inicio and pf and inicio > pf) or (fim and pi and fim < pi):
                    self.pendencias.append(f'Regra sem sobreposição temporal com o pedido: {ident}/{r}')
            norma = analise['norma_coletiva']
            esperada = pedido['norma_coletiva']
            if norma['documento_id'] != esperada['documento_id']:
                self.erros.append(f'Análise altera referência ao instrumento coletivo: {ident}')
            if esperada['necessaria'] and norma['estado'] != 'conferida':
                self.pendencias.append(f'Aplicabilidade coletiva pendente: {ident}')
            if not esperada['necessaria'] and norma['estado'] != 'nao-necessaria':
                self.erros.append(f'Estado coletivo diverge do inventário: {ident}')
            if onus['atribuicao'] == 'nao-definido' or not onus['regra_ids']:
                self.pendencias.append(f'Ônus da prova sem fundamento conferido: {ident}')
            elif not any(regras.get(r, {}).get('tema') == 'onus' for r in onus['regra_ids']):
                self.pendencias.append(f'Ônus sem regra identificada para o tema: {ident}')
            if onus['atribuicao'] == 'distribuicao-dinamica' and not onus['decisao_referencias']:
                self.pendencias.append(f'Distribuição dinâmica sem decisão referenciada: {ident}')
            if analise['estado'] == 'bloqueada':
                self.pendencias.append(f'Análise bloqueada: {ident}')
                if not analise['pendencias']:
                    self.erros.append(f'Análise bloqueada sem motivo: {ident}')
                if conclusao['resultado'] != 'inconclusiva':
                    self.erros.append(f'Análise bloqueada contém conclusão de mérito: {ident}')
            if tri['estado'] == 'bloqueada' or questoes.get(ident, {}).get('estado') == 'bloqueada':
                if analise['estado'] != 'bloqueada':
                    self.erros.append(f'Análise ignora bloqueio da triagem: {ident}')
            if conclusao['resultado'] != 'inconclusiva':
                if not any(regras.get(r, {}).get('tema') == pedido['tema'] for r in conclusao['regra_ids']):
                    self.pendencias.append(f'Conclusão sem regra do tema do pedido: {ident}')
                if (not conclusao['referencias'] or not analise['provas'] or not conclusao['regra_ids']
                        or not usadas <= validas or onus['atribuicao'] == 'nao-definido'
                        or analise['pendencias']):
                    self.erros.append(f'Hipótese de mérito sem suporte completo: {ident}')
            else:
                self.pendencias.append(f'Conclusão inconclusiva: {ident}')
        processuais = self.unicos(matriz['questoes_processuais'], 'tema', 'questões processuais')
        if set(processuais) != TEMAS_PROCESSUAIS:
            self.erros.append('Questões processuais obrigatórias omitidas ou duplicadas.')
        for tema, questao in processuais.items():
            conferir_regras(questao['regra_ids'], tema)
            if questao['estado'] == 'pendente' or not questao['regra_ids']:
                self.pendencias.append(f'Questão processual pendente: {tema}')
            elif not any(regras.get(r, {}).get('tema') == tema for r in questao['regra_ids']):
                self.pendencias.append(f'Questão processual sem regra do próprio tema: {tema}')


def verificar(workspace, etapa='analise'):
    c = Conferencia(workspace)
    if c.erros:
        return c.resultado()
    rel = c.carregar('pedidos.json', 'pedidos.schema.json')
    if rel is None:
        return c.resultado()
    pedidos = c.relatorio(rel)
    if etapa == 'relatorio':
        return c.resultado()
    tri = c.carregar('triagem.json', 'triagem.schema.json')
    if tri is None:
        return c.resultado()
    questoes = c.triagem(tri, pedidos)
    if etapa == 'triagem':
        return c.resultado()
    matriz = c.carregar('matriz-pedidos.json', 'matriz-pedidos.schema.json')
    if matriz is not None:
        registro = c.carregar('regras-juridicas.json', 'regra-juridica.schema.json') if caminho_seguro(c.raiz, 'regras-juridicas.json').exists() else None
        regras, validas = c.regras(registro)
        c.analise(matriz, pedidos, tri, questoes, regras, validas)
    return c.resultado()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workspace', type=Path)
    parser.add_argument('--etapa', choices=['relatorio', 'triagem', 'analise'], default='analise')
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument('--gate', action='store_true', help='Retornar 1 também para pendências impeditivas')
    modo.add_argument('--contexto', action='store_true', help='Exibir hashes atuais para fornecer aos agentes; não aprova etapas')
    args = parser.parse_args()
    try:
        if args.contexto:
            print(json.dumps(contexto(args.workspace), ensure_ascii=False, indent=2))
            return 0
        resultado = verificar(args.workspace, args.etapa)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 1 if resultado['erros'] or (args.gate and resultado['pendencias']) else 0
    except (ValueError, OSError, ImportError):
        print('Contrato, caminho ou configuração inválidos. Confira os schemas e os arquivos da etapa.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
