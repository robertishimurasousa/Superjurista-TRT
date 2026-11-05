"""Gera apenas documentos fictícios; requer requirements-dev.txt e Poppler."""
from io import BytesIO
from pathlib import Path
import json

from pdf2image import convert_from_bytes
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader, PdfWriter

DESTINO = Path(__file__).parent / 'jt'


def digital(linhas):
    saida = BytesIO()
    pdf = canvas.Canvas(saida, pagesize=(595, 842), invariant=1)
    pdf.setFont('Helvetica', 16)
    for i, linha in enumerate(linhas):
        pdf.drawString(40, 790 - i * 30, linha)
    pdf.save()
    return saida.getvalue()


def gerar():
    DESTINO.mkdir(exist_ok=True)
    texto = digital(['DOCUMENTO SINTETICO - SEM VALOR JURIDICO', 'CONTROLE DE JORNADA'] +
                    ['08:00 12:00 13:00 17:00'] * 8)
    (DESTINO / 'digital.pdf').write_bytes(texto)
    imagens = convert_from_bytes(digital(['DOCUMENTO SINTETICO', 'RECIBO DE SALARIO',
                                         'SALARIO BASE 2000,00']), dpi=150)
    saida = BytesIO()
    pdf = canvas.Canvas(saida, pagesize=(595, 842), invariant=1)
    pdf.drawImage(ImageReader(imagens[0]), 0, 0, width=595, height=842)
    pdf.save()
    hibrido = BytesIO()
    h = canvas.Canvas(hibrido, pagesize=(595, 842), invariant=1)
    h.drawString(40, 800, 'CABECALHO DIGITAL FICTICIO')
    h.drawImage(ImageReader(imagens[0]), 40, 400, width=250, height=350)
    h.save()
    (DESTINO / 'hibrido.pdf').write_bytes(hibrido.getvalue())
    for imagem in imagens:
        imagem.close()
    escaneado = saida.getvalue()
    (DESTINO / 'escaneado.pdf').write_bytes(escaneado)
    misto = PdfWriter()
    for dados in (texto, escaneado):
        misto.add_page(PdfReader(BytesIO(dados)).pages[0])
    misto.write(DESTINO / 'misto.pdf')
    protegido = PdfWriter()
    protegido.add_page(PdfReader(BytesIO(texto)).pages[0])
    protegido.encrypt('senha-ficticia')
    protegido.write(DESTINO / 'protegido.pdf')
    vazio = PdfWriter()
    vazio.add_blank_page(width=595, height=842)
    vazio.write(DESTINO / 'vazio.pdf')
    (DESTINO / 'corrompido.pdf').write_bytes(b'%PDF-1.7\nconteudo truncado de teste\n')
    base = '000000120265120001'
    dv = 98 - int(base + '00') % 97
    caso = {'schema_version': 1, 'numero_cnj': f'0000001-{dv:02d}.2026.5.12.0001',
            'trt': 12, 'unidade': 'Unidade fictícia para testes', 'unidade_codigo': '0001',
            'instancia': 1, 'rito': 'ordinario', 'fase': 'conhecimento',
            'data_referencia': '2026-11-05', 'escopo_confirmado': True,
            'documentos': [{'arquivo': 'digital.pdf', 'tipo': 'jornada', 'obrigatorio': True}],
            'pendencias': []}
    (DESTINO / 'caso.json').write_text(json.dumps(caso, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    gerar()
