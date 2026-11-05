# Instalação

[Voltar ao índice](README.md)

## Perfil trabalhista local — padrão

O perfil instala a base, os scripts de ingestão/verificação e os agentes de classificação, relato, triagem, análise provisória e pesquisa de fontes locais. Fontes e citações são operadas conforme o [guia da fase 4](fase-4-fontes.md). Use Python 3.11+ para a ingestão e uma pasta separada. A [fase 5](fase-5-minuta.md) acrescenta o comando `/pipeline-sentenca-trabalhista`, fundamentador, revisor e controle de sessão/retomada para macOS/Linux. O perfil não instala MCPs. Na raiz do repositório:

```bash
python3 scripts/instalar_perfil.py --perfil jt-1g-local --destino ../superjurista-trt-trabalho --dry-run
python3 scripts/instalar_perfil.py --perfil jt-1g-local --destino ../superjurista-trt-trabalho
```

No Claude Code, `/superjurista-dev:instalar-superjurista` executa essa instalação por perfil. Veja [arquivos instalados, conflitos e testes](fase-1-perfis.md). Depois da cópia, instale `requirements.txt` no ambiente virtual do projeto. Para OCR, prepare Poppler e Tesseract com idioma `por`, conforme o [guia da fase 2](fase-2-ingestao.md).

## Instalação federal legada — somente por opção explícita

O restante deste guia descreve o legado herdado, em uma pasta separada. Ele não entrega o piloto trabalhista. Selecione `--legado-federal` conforme o comando abaixo.

## Requisitos do legado

| Componente | Quando é necessário |
| --- | --- |
| Git | Clonar e atualizar o repositório |
| Claude Code instalado e autenticado | Carregar o plugin e executar agentes e comandos |
| Python 3.10 ou superior, com `pip` e `venv` | Ambiente completo com servidores MCP |
| Tesseract com idioma `por` e Poppler | Conversão por OCR |
| Integração de navegador compatível | Fluxos que usam Chrome, captura de sessão ou portais |
| Acesso autorizado ao PJe do tribunal | Download de documentos, após adaptar e validar a integração |

O requisito de Python para MCP pode ser consultado no [SDK oficial](https://github.com/modelcontextprotocol/python-sdk). A indicação antiga de Python 3.8 em documentos herdados não cobre o ambiente completo.

Os comandos de terminal abaixo usam Bash/Zsh. No Windows, o instalador também contém comandos como `cp` e `mkdir -p`: use um ambiente compatível e ajuste os caminhos. A skill `fork-terminal` é específica do Windows Terminal e PowerShell.

## 1. Obter este repositório

```bash
git clone https://github.com/robertishimurasousa/Superjurista-TRT.git
mkdir superjurista-trt-trabalho
cd superjurista-trt-trabalho
```

Mantenha o repositório do plugin e a pasta de processos separados. O marketplace do projeto original distribui o projeto original; ele não instala automaticamente este derivado.

## 2. Criar o ambiente Python

Verifique se `python3 --version` informa uma versão compatível. Depois:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

No PowerShell, ative o ambiente com `.\.venv\Scripts\Activate.ps1`.

Abra o Claude Code a partir do terminal com o ambiente ativado:

```bash
claude --plugin-dir ../Superjurista-TRT
```

Esse carregamento vale para a sessão iniciada. O nome técnico do plugin é `superjurista-dev`, usado no prefixo dos comandos. Consulte a [documentação de plugins do Claude Code](https://code.claude.com/docs/en/plugins/create).

## 3. Instalar os componentes no projeto

Dentro do Claude Code:

```text
/superjurista-dev:instalar-superjurista --legado-federal
```

O [instalador legado](../spec/referencias/instalacao-legado.md) define o tratamento dos arquivos existentes: oferece mesclagem, substituição ou cancelamento para os componentes; trata `CLAUDE.md` separadamente; preserva `README.md` e `.gitignore` se já existirem. A mesclagem preserva arquivos existentes e, portanto, pode manter componentes de versões anteriores.

Estrutura esperada:

```text
superjurista-trt-trabalho/
├── .claude/
│   ├── commands/
│   ├── agents/
│   ├── skills/
│   └── mcp-servers/
├── .mcp.json
├── scripts/
├── data/
│   ├── sentenca/
│   └── decisao/
├── CLAUDE.md
├── README.md
└── .gitignore
```

O instalador é uma instrução executada pelo Claude Code, não um pacote instalado pelo `pip`. Confirme o resumo de cópia e eventuais falhas antes de prosseguir.

## 4. Instalar as dependências

No terminal, na pasta de trabalho e com `.venv` ativo:

```bash
python -m pip install requests beautifulsoup4 pdfplumber PyPDF2 pdf2image pytesseract
python -m pip install \
  -r .claude/mcp-servers/bnp-api/requirements.txt \
  -r .claude/mcp-servers/cjf-jurisprudencia/requirements.txt \
  -r .claude/mcp-servers/tcu-jurisprudencia/requirements.txt \
  -r .claude/mcp-servers/tjsc-eproc/requirements.txt \
  -r .claude/mcp-servers/tnu-eproc/requirements.txt
```

Se for usar o gerador TOTP existente, ele também exige `pyotp`. Consulte as instruções da skill antes de configurar autenticação. O repositório não contém um arquivo de dependências travadas; a instalação precisa ser conferida no ambiente escolhido.

Para OCR, instale Tesseract e Poppler pelo procedimento do seu sistema e verifique:

```bash
tesseract --list-langs
pdftoppm -v
```

O primeiro comando deve listar `por`. O conversor aceita `POPPLER_PATH` quando os executáveis não são encontrados no caminho padrão. Veja [integrações](integracoes.md).

## 5. Conferir os MCPs

O instalador registra cinco servidores no `.mcp.json`, com caminho absoluto do `server.py` e `command: "python"`. Esse executável deve apontar para o ambiente que recebeu as dependências. Para evitar depender da ativação do terminal, configure em `command` o caminho absoluto de `.venv/bin/python` ou `.venv/Scripts/python.exe`.

Preserve outras entradas já presentes. Reinicie a sessão com o plugin carregado e confira os servidores por `/mcp`. A configuração de projeto fica em `.mcp.json`, conforme a [documentação de MCP do Claude Code](https://code.claude.com/docs/en/mcp).

## 6. Conferir a instalação local

```bash
python -m pip check
python scripts/verificar_sentenca.py --help
python scripts/verificar_pesquisa.py --help
python .claude/skills/converter-pdf/scripts/pdf_para_txt.py --help
```

Esses comandos verificam dependências e interfaces locais. A conexão de cada MCP, o download do PJe e a execução completa de um fluxo exigem verificações próprias. Comece com dados sintéticos ou anonimizados e consulte [uso](uso.md) e [adaptação para TRT](adaptacao-trt.md).


A fase 6 documenta a [operação e revisão do piloto](validacao/operacao-piloto-jt.md) e suas [evidências reais](validacao/piloto-jt-local.md). O corpus sintético e a CI validam o software; as 36 execuções com agentes e o aceite jurídico ainda precisam ser concluídos. Não use resultados de testes com regras fictícias como fontes ou minutas jurídicas.
