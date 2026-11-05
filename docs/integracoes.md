# Integrações

[Voltar ao índice](README.md)

## Servidores MCP incluídos

MCP é o protocolo usado pelo Claude Code para chamar ferramentas externas. Os cinco servidores distribuídos são processos Python locais que consultam serviços remotos.

| Identificador | Finalidade | Referência do componente |
| --- | --- | --- |
| `bnp-api` | Pesquisa no Banco Nacional de Precedentes do CNJ | [BNP](../scaffold/mcp-servers/bnp-api/README.md) |
| `cjf-jurisprudencia` | Consulta ao portal unificado do CJF | [CJF](../scaffold/mcp-servers/cjf-jurisprudencia/README.md) |
| `tcu-jurisprudencia` | Pesquisa de jurisprudência do TCU | [TCU](../scaffold/mcp-servers/tcu-jurisprudencia/README.md) |
| `tjsc-eproc` | Pesquisa de jurisprudência do TJSC via eProc | [TJSC](../scaffold/mcp-servers/tjsc-eproc/README.md) |
| `tnu-eproc` | Pesquisa e obtenção de documentos da TNU via eProc | [TNU](../scaffold/mcp-servers/tnu-eproc/README.md) |

As descrições de cobertura nos componentes registram observações históricas. Confirme a disponibilidade e atualização da fonte na consulta efetiva. O fato de um servidor carregar não significa que o portal remoto respondeu corretamente.

## Configuração no projeto

O instalador cria entradas em `.mcp.json`. Exemplo para um servidor, com caminhos ilustrativos que precisam ser substituídos:

```json
{
  "mcpServers": {
    "bnp-api": {
      "command": "/caminho/absoluto/projeto/.venv/bin/python",
      "args": ["/caminho/absoluto/projeto/.claude/mcp-servers/bnp-api/server.py"]
    }
  }
}
```

No Windows, use o caminho de `.venv/Scripts/python.exe` e caminhos JSON válidos. Preserve os demais servidores do arquivo. O [guia oficial de MCP](https://code.claude.com/docs/en/mcp) descreve o escopo de projeto e o gerenciamento das conexões.

Alguns READMEs herdados de componentes ainda indicam `settings.json`. Para a instalação descrita aqui, siga `.mcp.json`, em acordo com o [comando instalador](../commands/instalar-superjurista.md). Os documentos herdados continuam úteis para consultar ferramentas, parâmetros e sintaxe de busca.

## Dependências não incluídas

| Integração | Onde aparece | O que precisa ser preparado |
| --- | --- | --- |
| JULIA/TRF5 | Agente `pesquisador-julia` e fluxos de pesquisa | Serviço e acesso externos compatíveis com as ferramentas declaradas pelo agente |
| PESQUISA_STJ | Agente `pesquisador-stj` | Ferramentas `buscar_stj` e `obter_espelho_stj`, referenciadas pelo prefixo `mcp__claude_ai_PESQUISA_STJ__` |
| Claude no Chrome | Captura PJe e pesquisa em navegador | Integração que forneça as ferramentas esperadas pelos prompts |
| Agent Teams | Fluxos com equipes e debate | Recurso compatível e configurado no Claude Code |
| Windows Terminal/PowerShell | `fork-terminal` | Ambiente Windows e executáveis disponíveis |

A instalação dos cinco servidores locais não fornece essas integrações. Confirme as ferramentas de cada agente antes de executar um fluxo que dependa delas.

## PDF e OCR

O [conversor](../scaffold/skills/converter-pdf/scripts/pdf_para_txt.py) usa OCR por padrão e extração digital com `--digital`. As bibliotecas principais são `pdfplumber`, `pdf2image` e `pytesseract`; Tesseract e Poppler são programas do sistema.

O código consulta `POPPLER_PATH` quando não encontra o diretório Windows previsto e procura dados de idioma em locais da skill, em `~/tessdata` e no sistema. Confira `tesseract --list-langs` e mantenha o idioma português disponível.

OCR pode perder números, tabelas, assinaturas ou trechos de baixa qualidade. Revise o texto que alimentará o fluxo.

## PJe e autenticação

As skills [pje-download](../scaffold/skills/pje-download/SKILL.md) e [capturar-sessao-pje](../scaffold/skills/capturar-sessao-pje/SKILL.md) incluem automação orientada ao TRF5. URLs, cookies, cabeçalhos, tarefas e formatos de resposta precisam ser confrontados com o ambiente de destino.

A skill [criar-pje-download](../skills/criar-pje-download/SKILL.md) orienta a criação de outra integração a partir de observações da API. Arquivos HAR e sessões contêm material de autenticação: mantenha-os fora do repositório e use apenas o acesso autorizado. Consulte [dados e segurança](seguranca.md).
