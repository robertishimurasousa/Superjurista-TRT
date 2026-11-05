"""Validação da numeração CNJ para processos trabalhistas de primeiro grau."""
import re

PADRAO = re.compile(r'([0-9]{7})-([0-9]{2})\.([0-9]{4})\.([0-9])\.([0-9]{2})\.([0-9]{4})')


def validar_cnj(numero, trt=None):
    if not isinstance(numero, str) or not (m := PADRAO.fullmatch(numero)):
        raise ValueError('Número CNJ deve seguir NNNNNNN-DD.AAAA.J.TR.OOOO.')
    sequencia, dv, ano, segmento, regiao, unidade = m.groups()
    if segmento != '5':
        raise ValueError('O perfil exige o segmento 5 (Justiça do Trabalho).')
    if not 1 <= int(regiao) <= 24 or int(unidade) == 0 or int(sequencia) == 0:
        raise ValueError('Região, unidade ou sequência incompatível com primeiro grau.')
    if int(ano) < 1900:
        raise ValueError('Ano de autuação inválido.')
    if trt is not None and (type(trt) is not int or trt != int(regiao)):
        raise ValueError('O TRT confirmado diverge da numeração CNJ.')
    base = sequencia + ano + segmento + regiao + unidade
    if int(base + dv) % 97 != 1:
        raise ValueError('Dígitos verificadores CNJ inválidos.')
    return {'numero_cnj': numero, 'trt': int(regiao), 'unidade_codigo': unidade,
            'ano': int(ano), 'segmento': 5}
