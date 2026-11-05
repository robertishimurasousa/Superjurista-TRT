"""Normalização compartilhada de chaves; nunca usada para aprovar citações diretas."""
import re
import unicodedata


def normalizar_chave(texto):
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn').casefold()
    return re.sub(r'\s+', ' ', texto).strip()
