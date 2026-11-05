# SuperJurista TRT — projeto de trabalho

Este projeto recebe agentes, comandos, skills e integrações do [SuperJurista TRT](https://github.com/robertishimurasousa/Superjurista-TRT), derivado do SuperJurista de George Marmelstein. Ele oferece apoio à leitura de processos, pesquisa de jurisprudência, análise de provas e elaboração de minutas dentro do Claude Code.

A base instalada ainda contém referências à Justiça Federal e ao TRF5. O uso em TRT exige adaptação e validação do ambiente, dos agentes e dos contratos de saída. Toda minuta precisa de revisão humana.

## Preparar o ambiente

Use Python 3.10 ou superior para o ambiente completo com MCP. Em um ambiente virtual ativo, instale as dependências de documentos e de cada servidor:

```bash
python -m pip install requests beautifulsoup4 pdfplumber PyPDF2 pdf2image pytesseract
python -m pip install -r .claude/mcp-servers/bnp-api/requirements.txt
python -m pip install -r .claude/mcp-servers/cjf-jurisprudencia/requirements.txt
python -m pip install -r .claude/mcp-servers/tcu-jurisprudencia/requirements.txt
python -m pip install -r .claude/mcp-servers/tjsc-eproc/requirements.txt
python -m pip install -r .claude/mcp-servers/tnu-eproc/requirements.txt
```

OCR também exige Tesseract com idioma português (`por`) e Poppler. Confira o executável Python e os caminhos dos servidores em `.mcp.json`; reinicie a sessão e verifique as conexões por `/mcp`.

JULIA/TRF5, PESQUISA_STJ, integração de navegador e recursos de Agent Teams não são fornecidos pelos cinco servidores locais. Configure as dependências exigidas pelo fluxo escolhido. O [guia de instalação](https://github.com/robertishimurasousa/Superjurista-TRT/blob/main/docs/instalacao.md) detalha o preparo.

## Primeiro caso com arquivo local

Prepare um texto sintético ou anonimizado em `data/sentenca/NUMERO-CNJ/processo.txt`, substituindo o marcador pelo número completo do caso. Dentro do Claude Code:

```text
/relatar-processo data/sentenca/NUMERO-CNJ/processo.txt
/pipeline-sentenca data/sentenca/NUMERO-CNJ/processo.txt
```

O fluxo de sentença pode exigir pesquisas externas durante a triagem. Os resultados ficam na pasta do caso, com prefixo do número do processo: linha do tempo, relatório, triagem, análise, fundamentação e sentença consolidada, além dos artefatos condicionais.

No terminal, confira as pendências e depois os critérios finais:

```bash
python scripts/verificar_sentenca.py data/sentenca/NUMERO-CNJ --numero NUMERO-CNJ
python scripts/verificar_sentenca.py data/sentenca/NUMERO-CNJ --numero NUMERO-CNJ --gate
```

A varredura pode terminar com código 0 mesmo com pendências; `--gate` exige as etapas válidas. A conferência de citações é feita por um script separado. Nenhuma dessas verificações substitui a revisão do conteúdo.

## Organização

| Caminho | Conteúdo |
| --- | --- |
| `.claude/commands/` | Fluxos de trabalho instalados |
| `.claude/agents/` | Agentes especializados |
| `.claude/skills/` | Instruções e scripts de domínio |
| `.claude/mcp-servers/` | Servidores de pesquisa |
| `.mcp.json` | Registro e executáveis dos servidores |
| `scripts/` | Verificadores e consolidadores |
| `data/sentenca/` e `data/decisao/` | Documentos e artefatos dos casos |
| `CLAUDE.md` | Instruções do projeto para o Claude Code |

## Dados e acesso ao PJe

As integrações PJe distribuídas são orientadas ao TRF5. Não presuma compatibilidade com outro tribunal. Valide URLs, sessão, tarefas e downloads antes do uso.

Mantenha documentos, sessões, cookies, arquivos HAR e credenciais fora do controle de versão. Revise o `.gitignore`: ele não cobre automaticamente todas as saídas dos agentes. O uso do Claude Code e das fontes externas pode transmitir conteúdo aos serviços configurados; armazenamento local não significa processamento inteiramente local.

## Documentação e suporte

- [Uso e comandos](https://github.com/robertishimurasousa/Superjurista-TRT/blob/main/docs/uso.md).
- [Integrações](https://github.com/robertishimurasousa/Superjurista-TRT/blob/main/docs/integracoes.md).
- [Adaptação para TRT](https://github.com/robertishimurasousa/Superjurista-TRT/blob/main/docs/adaptacao-trt.md).
- [Dados e segurança](https://github.com/robertishimurasousa/Superjurista-TRT/blob/main/docs/seguranca.md).
- [Solução de problemas](https://github.com/robertishimurasousa/Superjurista-TRT/blob/main/docs/solucao-de-problemas.md).
- [Chamados deste repositório](https://github.com/robertishimurasousa/Superjurista-TRT/issues).
