#!/usr/bin/env python3
"""Validação local/CI com relatório técnico sanitizado, sem executar agentes ou serviços."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time
import unittest

RAIZ=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(RAIZ/'scaffold/scripts'))
from documentos import hash_arquivo, salvar_json
from perfil import carregar_perfil


def hash_pacote():
    m=json.loads((RAIZ/'scaffold/perfis/jt-1g-local.json').read_text())
    arquivos={i['origem']:hash_arquivo(RAIZ/i['origem']) for i in m['arquivos']}
    return hashlib.sha256(json.dumps(arquivos,sort_keys=True).encode()).hexdigest()


def hash_validacao():
    caminhos=[RAIZ/'requirements-dev.txt',RAIZ/'.github/workflows/validacao.yml']
    for pasta in ('scripts','tests','spec/schemas'):
        caminhos.extend(p for p in (RAIZ/pasta).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    arquivos={p.relative_to(RAIZ).as_posix():hash_arquivo(p) for p in caminhos}
    return hashlib.sha256(json.dumps(arquivos,sort_keys=True).encode()).hexdigest()


def estaticos():
    from jsonschema import Draft202012Validator
    carregar_perfil(RAIZ/'scaffold/perfis/jt-1g-local.json',RAIZ)
    manifesto=json.loads((RAIZ/'scaffold/perfis/jt-1g-local.json').read_text())
    for nome in {i['origem'] for i in manifesto['arquivos'] if i['origem'].endswith('.py')} | {
            str(p.relative_to(RAIZ)) for pasta in ['scripts','tests'] for p in (RAIZ/pasta).rglob('*.py')}:
        ast.parse((RAIZ/nome).read_text(encoding='utf-8'),filename=nome)
    for p in (RAIZ/'spec/schemas').glob('*.json'):Draft202012Validator.check_schema(json.loads(p.read_text()))
    for p in [RAIZ/'README.md',*(RAIZ/'docs').rglob('*.md'),*(RAIZ/'plan').glob('*.md')]:
        for href in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            href=href.split('#')[0]
            if href and '://' not in href and not href.startswith(('mailto:','/')):
                if not (p.parent/href).exists():raise ValueError(f'Link local ausente em {p.relative_to(RAIZ)}: {href}')
    corpus=json.loads((RAIZ/'tests/fixtures/jt/manifesto.json').read_text())
    if corpus['natureza']!='sintetico-sem-dados-reais' or len(corpus['casos'])!=12 or len({c['id'] for c in corpus['casos']})!=12:
        raise ValueError('Corpus sintético inválido.')
    # A allowlist com hashes impede inclusão silenciosa de PDFs/dados reais nas fixtures.
    inventario=json.loads((RAIZ/'tests/fixtures/inventario-seguranca.json').read_text())
    atuais={p.relative_to(RAIZ/'tests/fixtures').as_posix():hash_arquivo(p) for p in (RAIZ/'tests/fixtures').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.name!='inventario-seguranca.json'}
    if atuais!=inventario['arquivos']:raise ValueError('Fixtures divergem do inventário sintético revisável. Atualize os hashes somente após conferir conteúdo e origem.')
    segredo=re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{32,}')
    for pasta in ['tests','docs/validacao']:
        for p in (RAIZ/pasta).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and segredo.search(p.read_bytes().decode('utf-8',errors='ignore')):
                raise ValueError(f'Possível segredo em {p.relative_to(RAIZ)}; conteúdo não exibido.')
    subprocess.run([sys.executable,'-m','pip','check'],check=True,cwd=RAIZ)
    subprocess.run(['git','-c','safe.directory='+str(RAIZ),'diff','--check'],check=True,cwd=RAIZ)
    with tempfile.TemporaryDirectory() as tmp:
        projeto=Path(tmp).resolve()/'instalado'
        subprocess.run([sys.executable,str(RAIZ/'scripts/instalar_perfil.py'),'--perfil','jt-1g-local','--destino',str(projeto)],check=True,capture_output=True)
        comandos={p.name for p in (projeto/'.claude/commands').iterdir()}
        if comandos!={'pipeline-sentenca-trabalhista.md'}:raise ValueError('Instalação contém comandos inesperados.')
        subprocess.run([sys.executable,str(projeto/'scripts/verificar_sentenca_jt.py'),'--help'],check=True,capture_output=True,cwd=projeto)


def versoes():
    bibliotecas={n:importlib.metadata.version(n) for n in ['pdfplumber','pypdf','pdf2image','pytesseract','Pillow','jsonschema','reportlab']}
    binarios={}
    for nome,args in [('tesseract',['tesseract','--version']),('poppler',['pdftoppm','-v'])]:
        try:
            r=subprocess.run(args,capture_output=True,text=True,check=True); binarios[nome]=(r.stdout or r.stderr).splitlines()[0]
        except (OSError,subprocess.CalledProcessError):binarios[nome]=None
    por=Path(os.environ.get('TESSDATA_PREFIX','/usr/share/tesseract-ocr/5/tessdata'))/'por.traineddata'
    return {'python':platform.python_version(),'sistema':platform.system(),'arquitetura':platform.machine(),
            'bibliotecas':bibliotecas,'binarios':binarios,'por_sha256':hash_arquivo(por) if por.is_file() else None}


class Resultado(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.registros=[]
    def addSuccess(self,test):super().addSuccess(test);self.registros.append({'teste':test.id(),'estado':'passou'})
    def addFailure(self,test,err):super().addFailure(test,err);self.registros.append({'teste':test.id(),'estado':'falhou'})
    def addError(self,test,err):super().addError(test,err);self.registros.append({'teste':test.id(),'estado':'erro'})
    def addSkip(self,test,reason):super().addSkip(test,reason);self.registros.append({'teste':test.id(),'estado':'ignorado'})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--saida',type=Path,required=True);p.add_argument('--exigir-ocr',action='store_true')
    a=p.parse_args();inicio=datetime.now(timezone.utc).isoformat();tempo=time.monotonic()
    rel={'schema_version':1,'natureza':'validacao-deterministica','inicio':inicio,'pacote_sha256':hash_pacote(),
         'manifesto_sha256':hash_arquivo(RAIZ/'tests/fixtures/jt/manifesto.json'),'validacao_sha256':hash_validacao(),'ambiente':versoes(),
         'execucoes_com_agentes':0,'homologacao_juridica':'pendente','aceite_humano':'nao-registrado'}
    try:
        if a.exigir_ocr and os.environ.get('TESTAR_OCR')!='1':raise ValueError('TESTAR_OCR=1 obrigatório.')
        estaticos()
        resultado=unittest.TextTestRunner(verbosity=2,resultclass=Resultado).run(unittest.defaultTestLoader.discover(str(RAIZ/'tests')))
        ok=resultado.wasSuccessful() and (not a.exigir_ocr or not resultado.skipped)
        rel.update(estado='passou' if ok else 'falhou',testes=resultado.testsRun,ignorados=len(resultado.skipped),
                   falhas=len(resultado.failures),erros=len(resultado.errors),resultados=resultado.registros)
    except (ValueError,OSError,subprocess.CalledProcessError,ImportError) as exc:
        print('Validação interrompida: '+str(exc),file=sys.stderr);ok=False;rel.update(estado='falhou',erro_tipo=type(exc).__name__)
    rel.update(fim=datetime.now(timezone.utc).isoformat(),duracao_segundos=round(time.monotonic()-tempo,3))
    a.saida.parent.mkdir(parents=True,exist_ok=True);salvar_json(a.saida,rel)
    return 0 if ok else 1

if __name__=='__main__':sys.exit(main())
