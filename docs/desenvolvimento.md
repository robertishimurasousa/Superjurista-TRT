# Desenvolvimento e manutenção

[Voltar ao índice](README.md)

## Preparar alterações

Clone o repositório, crie uma ramificação e mantenha o projeto de trabalho separado. Para inspecionar Markdown e os verificadores que usam apenas a biblioteca padrão, não é necessário configurar acesso aos tribunais.

```bash
git switch -c codex/documentacao-ou-ajuste
git status --short
```

Leia os [modelos em spec](../spec/templates/) e o [padrão soberano](../skills/criar-sistema/references/padrao-soberano.md) ao alterar agentes ou fluxos. Uma mudança no formato produzido pode exigir mudança no verificador, no consolidado e nos exemplos de uso.

## Origem do scaffold

Neste derivado, **o conteúdo versionado de `scaffold/` é a fonte da distribuição**. Ajustes trabalhistas são mantidos diretamente no repositório, com revisão e testes. Essa política substitui a regeneração destrutiva a partir do computador do autor original.

O [sync-scaffold.ps1](../sync-scaffold.ps1) passa a ser uma entrada PowerShell para o importador portátil [importar_scaffold.py](../scripts/importar_scaffold.py). A importação exige os diretórios de origem explicitamente configurados, prepara uma cópia filtrada em diretório temporário e gera um relatório comparativo. Ela não aplica mudanças ao repositório nem remove seus componentes.

Não há mais cópia automática dos geradores globais para a raiz do plugin. Mudanças upstream nessas ferramentas devem ser revisadas separadamente. Consulte [instalação por perfil e importação](fase-1-perfis.md) para os comandos.

## Verificações locais

Na raiz do repositório:

```bash
git diff --check
python3 -m json.tool .claude-plugin/plugin.json
python3 scaffold/scripts/verificar_sentenca.py --help
python3 scaffold/scripts/verificar_pesquisa.py --help
python3 scaffold/scripts/verificar_probatica.py --help
python3 scaffold/scripts/verificar_revisao.py --help
python3 scaffold/scripts/verificar_citacoes.py --help
```

Para conferir a sintaxe dos scripts sem executá-los nem gerar arquivos de bytecode, exclua os modelos de referência que contêm marcadores a substituir:

```bash
python3 - <<'PY'
import ast
from pathlib import Path

arquivos = list(Path("scaffold").rglob("*.py")) + list(Path("skills").glob("*/assets/*.py"))
for arquivo in arquivos:
    ast.parse(arquivo.read_text(encoding="utf-8-sig"), filename=str(arquivo))
print(f"Sintaxe verificada: {len(arquivos)} arquivos Python.")
PY
```

Com Claude Code disponível, confira também o manifesto:

```bash
claude plugin validate .
```

O comando de validação é descrito na [documentação oficial](https://code.claude.com/docs/en/plugins/create). Ele não executa os fluxos judiciais. A suíte da fase 1 pode ser executada com `python -m unittest discover -s tests -v`, após instalar `requirements-dev.txt`. Ainda não há configuração de integração contínua.

## O que validar por tipo de alteração

| Alteração | Verificação pertinente |
| --- | --- |
| Documentação | Links, caminhos, exemplos, acentuação e correspondência com o código |
| Metadados | JSON válido, identificadores e endereços corretos |
| Agente ou comando | Contrato de entrada/saída e execução com dados de teste |
| Verificador | Casos válidos, inválidos, ausentes e códigos de saída |
| Servidor MCP | Importação, inicialização, ferramentas e resposta do serviço externo |
| PJe | Autenticação e download no ambiente autorizado do tribunal de destino |

## Publicação e metadados

O nome público do repositório é **SuperJurista TRT**. O identificador do plugin permanece **`superjurista-dev`**: referências internas e nomes de agentes dependem dele. Renomeá-lo exige revisar essas dependências e a documentação de comandos.

A descrição do GitHub e a descrição do manifesto devem representar a funcionalidade existente e o propósito de adaptação, sem declarar suporte já validado para todos os TRTs. A versão do manifesto não precisa ser incrementada apenas para sugerir uma publicação que ainda não ocorreu. Registre alterações pendentes na seção correspondente do [histórico](../CHANGELOG.md).

Antes de abrir uma proposta, consulte [como contribuir](../CONTRIBUTING.md) e revise o diff para evitar a inclusão de documentos processuais ou segredos.
