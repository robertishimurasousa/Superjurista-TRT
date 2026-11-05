"""Regressão da distribuição local; apenas arquivos sintéticos temporários."""
import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from jsonschema import Draft202012Validator

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'scripts'))
sys.path.insert(0, str(RAIZ / 'scaffold' / 'scripts'))
import instalar_perfil
import importar_scaffold
from perfil import carregar_perfil, validar_perfil

MANIFESTO = RAIZ / 'scaffold/perfis/jt-1g-local.json'


class PerfilTests(unittest.TestCase):
    def setUp(self):
        self.perfil = json.loads(MANIFESTO.read_text())

    def test_manifesto_e_schema(self):
        schema = json.loads((RAIZ / 'spec/schemas/perfil.schema.json').read_text())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(self.perfil)
        self.assertEqual(carregar_perfil(MANIFESTO, RAIZ), self.perfil)

    def test_versao_identidade_e_tipos_invalidos(self):
        for campo, valor in [('id', 'federal'), ('versao', 2), ('versao', True),
                              ('segmento', 4), ('instancia', 2), ('comandos', 'x'),
                              ('estado', 'homologado'), ('fontes', 'julia')]:
            with self.subTest(campo=campo, valor=valor):
                perfil = copy.deepcopy(self.perfil)
                perfil[campo] = valor
                with self.assertRaises(ValueError):
                    validar_perfil(perfil, RAIZ)

    def test_campo_desconhecido(self):
        self.perfil['executar'] = 'comando arbitrário'
        with self.assertRaises(ValueError):
            validar_perfil(self.perfil)

    def test_caminhos_invalidos(self):
        for campo in ('origem', 'destino'):
            for valor in ('../fora', '/tmp/fora', 'scaffold/../fora', 'C:/fora',
                          'scaffold\\arquivo', 'scripts//arquivo', 'scripts/.git/config',
                          'scripts/CON.py', 'scripts/arquivo. ', 'scripts/a\n.py'):
                with self.subTest(campo=campo, valor=valor):
                    perfil = copy.deepcopy(self.perfil)
                    perfil['arquivos'][0][campo] = valor
                    with self.assertRaises(ValueError):
                        validar_perfil(perfil, RAIZ)

    def test_origem_ausente(self):
        self.perfil['arquivos'][0]['origem'] = 'scaffold/inexistente.md'
        with self.assertRaisesRegex(ValueError, 'ausente'):
            validar_perfil(self.perfil, RAIZ)

    def test_destino_duplicado_inclusive_caixa(self):
        for destino in ('README.md', 'readme.md'):
            with self.subTest(destino=destino):
                perfil = copy.deepcopy(self.perfil)
                perfil['arquivos'].append({'origem': 'scaffold/project-readme.md', 'destino': destino})
                with self.assertRaises(ValueError):
                    validar_perfil(perfil, RAIZ)

    def test_mcps_e_arquivo_mcp_proibidos(self):
        self.perfil['mcps'] = ['julia']
        with self.assertRaises(ValueError):
            validar_perfil(self.perfil)
        self.perfil['mcps'] = []
        self.perfil['arquivos'][0]['destino'] = '.mcp.json'
        with self.assertRaises(ValueError):
            validar_perfil(self.perfil)

    def test_agente_nao_declarado(self):
        self.perfil['arquivos'].append({'origem': 'scaffold/project-readme.md',
                                       'destino': '.claude/agents/indevido.md'})
        with self.assertRaisesRegex(ValueError, 'agentes'):
            validar_perfil(self.perfil, RAIZ)

    def test_comando_sem_arquivo(self):
        self.perfil['comandos'] = ['sentenca']
        with self.assertRaisesRegex(ValueError, 'comandos'):
            validar_perfil(self.perfil)

    def test_origem_simbolica(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp).resolve()
            (raiz / 'scaffold').symlink_to(RAIZ / 'scaffold', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'simbólico'):
                validar_perfil(self.perfil, raiz)

    def test_arquivo_como_ancestral_de_arquivo(self):
        self.perfil['arquivos'].append({'origem': 'scaffold/project-readme.md',
                                       'destino': 'scripts/perfil.py/filho'})
        with self.assertRaisesRegex(ValueError, 'Conflito'):
            validar_perfil(self.perfil, RAIZ)


class InstalacaoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.destino = self.base / 'projeto com espaços'

    def instalar(self, dry_run=False):
        saida = io.StringIO()
        with redirect_stdout(saida):
            codigo = instalar_perfil.instalar(RAIZ, 'jt-1g-local', self.destino, dry_run)
        return codigo, saida.getvalue()

    def test_dry_run_nao_cria_destino(self):
        codigo, _ = self.instalar(True)
        self.assertEqual(codigo, 0)
        self.assertFalse(self.destino.exists())

    def test_instala_exatamente_manifesto_sem_mcps(self):
        codigo, saida = self.instalar()
        self.assertEqual(codigo, 0)
        perfil = carregar_perfil(MANIFESTO)
        arquivos = {p.relative_to(self.destino).as_posix()
                    for p in self.destino.rglob('*') if p.is_file()}
        self.assertEqual(arquivos, {item['destino'] for item in perfil['arquivos']})
        self.assertTrue((self.destino / 'data/casos').is_dir())
        self.assertFalse((self.destino / '.mcp.json').exists())
        self.assertFalse((self.destino / '.claude/commands').exists())
        self.assertIn('ainda não disponíveis', saida)
        instalado = json.loads((self.destino / '.claude/perfis/jt-1g-local.json').read_text())
        self.assertEqual(instalado, perfil)

    def test_reinstalacao_idempotente(self):
        self.instalar()
        antes = {p: p.stat().st_mtime_ns for p in self.destino.rglob('*') if p.is_file()}
        codigo, _ = self.instalar()
        self.assertEqual(codigo, 0)
        self.assertEqual(antes, {p: p.stat().st_mtime_ns for p in antes})

    def test_conflito_preserva_tudo_e_impede_copia_parcial(self):
        self.destino.mkdir()
        customizado = self.destino / 'README.md'
        customizado.write_text('Conteúdo do usuário')
        codigo, saida = self.instalar()
        self.assertEqual(codigo, 1)
        self.assertIn('README.md', saida)
        self.assertEqual(customizado.read_text(), 'Conteúdo do usuário')
        self.assertEqual(list(self.destino.iterdir()), [customizado])

    def test_customizacao_em_instalacao_existente(self):
        self.instalar()
        alvo = self.destino / 'scripts/perfil.py'
        alvo.write_text('# customizado')
        codigo, _ = self.instalar()
        self.assertEqual(codigo, 1)
        self.assertEqual(alvo.read_text(), '# customizado')

    def test_mcp_e_legado_preexistentes_sao_preservados_com_aviso(self):
        pasta = self.destino / '.claude/commands'
        pasta.mkdir(parents=True)
        legado = pasta / 'legado.md'
        legado.write_text('legado sintético')
        mcp = self.destino / '.mcp.json'
        mcp.write_text('{"existente": true}')
        codigo, saida = self.instalar()
        self.assertEqual(codigo, 0)
        self.assertIn('não há garantia de isolamento', saida)
        self.assertEqual(mcp.read_text(), '{"existente": true}')
        self.assertEqual(legado.read_text(), 'legado sintético')

    def test_link_no_destino_nao_escreve_fora(self):
        externo = self.base / 'externo'
        externo.mkdir()
        self.destino.mkdir()
        (self.destino / '.claude').symlink_to(externo, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'simbólico'):
            self.instalar()
        self.assertEqual(list(externo.iterdir()), [])
        self.assertEqual(len(list(self.destino.iterdir())), 1)

    def test_link_na_raiz_do_destino(self):
        externo = self.base / 'externo'
        externo.mkdir()
        self.destino.symlink_to(externo, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.instalar()

    def test_arquivo_bloqueando_diretorio(self):
        self.destino.mkdir()
        (self.destino / 'scripts').write_text('preservar')
        with self.assertRaises(ValueError):
            self.instalar()
        self.assertEqual((self.destino / 'scripts').read_text(), 'preservar')
        self.assertEqual(len(list(self.destino.iterdir())), 1)

    def test_nome_conflitante_por_caixa(self):
        self.destino.mkdir()
        (self.destino / 'readme.md').write_text('preservar')
        with self.assertRaises(ValueError):
            self.instalar()

    def test_destino_no_repositorio_rejeitado(self):
        with self.assertRaisesRegex(ValueError, 'separada'):
            instalar_perfil.planejar_instalacao(RAIZ, 'jt-1g-local', RAIZ / 'projeto')

    def test_destino_com_parentes_nao_contorna_isolamento(self):
        with self.assertRaisesRegex(ValueError, 'separada'):
            instalar_perfil.planejar_instalacao(
                RAIZ, 'jt-1g-local', RAIZ / '..' / RAIZ.name / 'projeto')

    def test_diretorio_no_lugar_de_arquivo_impede_toda_instalacao(self):
        (self.destino / 'README.md').mkdir(parents=True)
        codigo, _ = self.instalar()
        self.assertEqual(codigo, 1)
        self.assertFalse((self.destino / '.claude').exists())

    def test_manifesto_invalido_nao_cria_destino(self):
        with patch.object(instalar_perfil, 'carregar_perfil', side_effect=ValueError('manifesto inválido')):
            with self.assertRaises(ValueError):
                self.instalar()
        self.assertFalse(self.destino.exists())

    def test_falha_de_escrita_reverte_arquivos_novos(self):
        original = Path.open
        def abrir(caminho, *args, **kwargs):
            if caminho.name == 'CLAUDE.md' and args and args[0] == 'xb':
                raise OSError('Falha de escrita simulada')
            return original(caminho, *args, **kwargs)
        with patch.object(Path, 'open', abrir):
            with self.assertRaises(OSError):
                self.instalar()
        self.assertFalse(self.destino.exists())

    def test_cli_sem_dependencias_ou_argumentos_validos(self):
        comando = [sys.executable, '-S', str(RAIZ / 'scripts/instalar_perfil.py')]
        sem_args = subprocess.run(comando, capture_output=True, text=True)
        self.assertEqual(sem_args.returncode, 2)
        sucesso = subprocess.run(comando + ['--perfil', 'jt-1g-local', '--destino', str(self.destino)],
                                 capture_output=True, text=True)
        self.assertEqual(sucesso.returncode, 0, sucesso.stderr + sucesso.stdout)

    def test_gitignore_em_repositorio_e_projeto(self):
        for arquivo in (RAIZ / '.gitignore', RAIZ / 'scaffold/project-gitignore'):
            with self.subTest(arquivo=arquivo):
                projeto = self.base / arquivo.name.replace('.', '_')
                projeto.mkdir(exist_ok=True)
                subprocess.run(['git', 'init', '-q', str(projeto)], check=True)
                shutil.copyfile(arquivo, projeto / '.gitignore')
                for nome in ('data/casos/exemplo/minuta.md', '.env', '.env.local', 'sessao-teste.json',
                             'pje_session_backup.json', 'captura.har', 'cookies.json', '.venv/bin/python'):
                    r = subprocess.run(['git', '-C', str(projeto), 'check-ignore', '-q', nome])
                    self.assertEqual(r.returncode, 0, nome)
                for nome in ('tests/fixtures/jt/exemplo.pdf', 'tests/fixtures/caso.json', '.env.example'):
                    r = subprocess.run(['git', '-C', str(projeto), 'check-ignore', '-q', nome])
                    self.assertEqual(r.returncode, 1, nome)


class ImportacaoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.projeto = self.base / 'origem/.claude'
        self.scripts = self.base / 'origem/scripts'
        self.globais = self.base / 'global/mcp-servers'
        self.referencia = self.base / 'repositorio/scaffold'
        for pasta in ('agents', 'commands', 'skills'):
            (self.projeto / pasta).mkdir(parents=True)
        self.scripts.mkdir()
        self.referencia.mkdir(parents=True)
        for nome in importar_scaffold.GLOBAIS:
            pasta = self.globais / nome
            pasta.mkdir(parents=True)
            (pasta / 'server.py').write_text('# sintético')
        for nome in importar_scaffold.LOCAIS:
            pasta = self.projeto / 'mcp-servers' / nome
            pasta.mkdir(parents=True)
            (pasta / 'server.py').write_text('# sintético')

    def test_importacao_filtrada_sem_mutacao_no_scaffold(self):
        (self.projeto / 'agents/novo.md').write_text('novo')
        (self.projeto / 'commands/igual.md').write_text('igual')
        (self.projeto / 'commands/alterado.md').write_text('depois')
        (self.projeto / 'commands/criar-team.md').write_text('não distribuir')
        for nome in ('.env.local', 'segredo.har', 'cookies.json', 'sessao1.json'):
            (self.projeto / 'skills' / nome).write_text('segredo sintético')
        (self.scripts / 'test_excluido.py').write_text('excluir')
        (self.scripts / 'verificador.py').write_text('# incluir')
        (self.referencia / 'commands').mkdir()
        (self.referencia / 'commands/igual.md').write_text('igual')
        (self.referencia / 'commands/alterado.md').write_text('antes')
        (self.referencia / 'somente-jt.md').write_text('preservar')
        antes = {p.relative_to(self.referencia): p.read_bytes() for p in self.referencia.rglob('*') if p.is_file()}
        area = importar_scaffold.importar(self.projeto, self.scripts, self.globais, self.referencia)
        self.addCleanup(shutil.rmtree, area)
        rel = json.loads((area / 'comparacao.json').read_text())
        estados = {item['arquivo']: item['estado'] for item in rel['arquivos']}
        self.assertEqual(estados['agents/novo.md'], 'novo')
        self.assertEqual(estados['commands/igual.md'], 'igual')
        self.assertEqual(estados['commands/alterado.md'], 'alterado')
        self.assertFalse(rel['alteracoes_aplicadas'])
        self.assertIn('somente-jt.md', rel['apenas_na_referencia_preservados'])
        self.assertNotIn('commands/criar-team.md', estados)
        self.assertNotIn('scripts/test_excluido.py', estados)
        self.assertFalse(any(nome.startswith('skills/') for nome in estados))
        self.assertEqual(antes, {p.relative_to(self.referencia): p.read_bytes()
                                for p in self.referencia.rglob('*') if p.is_file()})

    def test_origem_invalida_nao_cria_area_temporaria(self):
        with patch.object(importar_scaffold.tempfile, 'mkdtemp') as criar:
            with self.assertRaises(ValueError):
                importar_scaffold.importar(self.base / 'inexistente', self.scripts,
                                           self.globais, self.referencia)
            criar.assert_not_called()

    def test_mcp_ausente_nao_cria_area_temporaria(self):
        shutil.rmtree(self.globais / 'bnp-api')
        with patch.object(importar_scaffold.tempfile, 'mkdtemp') as criar:
            with self.assertRaises(ValueError):
                importar_scaffold.importar(self.projeto, self.scripts, self.globais, self.referencia)
            criar.assert_not_called()

    def test_link_na_origem_nao_e_copiado(self):
        (self.projeto / 'agents/link.md').symlink_to(self.scripts / 'ausente')
        with patch.object(importar_scaffold.tempfile, 'mkdtemp') as criar:
            with self.assertRaisesRegex(ValueError, 'simbólico'):
                importar_scaffold.importar(self.projeto, self.scripts, self.globais, self.referencia)
            criar.assert_not_called()

    def test_cli_exige_origens_explicitas(self):
        r = subprocess.run([sys.executable, str(RAIZ / 'scripts/importar_scaffold.py')],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


if __name__ == '__main__':
    unittest.main()
