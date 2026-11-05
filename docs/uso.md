# Uso e comandos

[Voltar ao índice](README.md)

O piloto local usa `/pipeline-sentenca-trabalhista PDF_OU_PASTA --caso caso.json`, documentado na [fase 5](fase-5-minuta.md). Os comandos federais abaixo pertencem ao legado e não são instalados nesse perfil.


> Os fluxos judiciais deste guia são herdados do sistema federal e exigem instalação explícita com `--legado-federal`. O perfil `jt-1g-local` oferece [ingestão de PDFs](fase-2-ingestao.md), [modelo do caso e análise provisória](fase-3-analise.md) e [fontes/citações](fase-4-fontes.md), sem esses comandos federais.

Execute comandos iniciados por `/` dentro do Claude Code. Comandos iniciados por `python` pertencem ao terminal. Os exemplos pressupõem um [projeto instalado](instalacao.md); `NUMERO-CNJ` representa o número completo do processo, não um caso real.

## Preparar um caso

Organize os documentos de cada caso em uma pasta própria:

```text
data/sentenca/NUMERO-CNJ/
├── processo.pdf
└── processo.txt
```

Para converter um PDF pelo script distribuído:

```bash
python .claude/skills/converter-pdf/scripts/pdf_para_txt.py --input data/sentenca/NUMERO-CNJ/processo.pdf --output data/sentenca/NUMERO-CNJ
```

O padrão é OCR. Para PDF com texto digital utilizável, acrescente `--digital`. Confira o texto extraído, a legibilidade e a presença dos documentos relevantes antes de iniciar a análise. Não é necessário usar download do PJe para trabalhar com arquivos locais.

## Fluxos judiciais

Os nomes abaixo correspondem aos arquivos de [comandos do scaffold](../scaffold/commands/), copiados para `.claude/commands/` durante a instalação.

| Comando | Argumento | Finalidade e observações |
| --- | --- | --- |
| `/relatar-processo` | Número ou caminho do processo | Produz linha do tempo e relatório |
| `/pipeline-sentenca` | Caminho do `processo.txt` | Fluxo com triagem, análise, fundamentação e consolidação; pode exigir pesquisa externa |
| `/pipeline-minutar-pdf` | Caminho do PDF | Encadeia conversão e elaboração de minuta |
| `/pipeline-sentenca-team` | Caminho do processo | Variante com Agent Teams; exige recursos específicos do Claude Code |
| `/pipeline-embargos` | Caminho do processo | Análise de embargos e minuta de decisão |
| `/pipeline-pesquisa` | Tema ou pasta de trabalho e tema | Pesquisa em fontes distintas e consolida resultados |
| `/planejamento-epistemico` | Solicitação de pesquisa | Estrutura perguntas, dimensões de pesquisa e plano |
| `/pipeline-probatica` | Número ou pasta do processo | Combina análises Pearl, Haack e FBD |
| `/skill-probatica` | Número do processo | Inventaria provas, seleciona analistas e identifica lacunas |
| `/tribunal-probatico` | Caminho do `processo.txt` | Gera instruções para debate entre agentes de um Agent Team |
| `/pipeline-revisao-minuta` | Caminho da minuta ou da pasta | Revisores de fontes, cálculos, honorários, remessa e embargabilidade |
| `/baixar-pje` | Quantidade e modo `sentenca` ou `decisao` | Download de PDFs com sessão PJe válida |
| `/baixar-converter` | Quantidade e modo | Download seguido de conversão |
| `/baixar-inteligente` | Número, opcionalmente `--merge --converter` | Seleção de documentos de um processo específico |
| `/analisar-lista` | Caminho de arquivo `.docx` | Análise de lista de julgamento do TRF5; contém componentes legados |
| `/fork-terminal` | Caminhos de processos separados por espaço | Abre tarefas em abas do Windows Terminal |

As integrações de PJe são herdadas do TRF5. Consulte [adaptação para TRT](adaptacao-trt.md) antes de utilizá-las em outro tribunal. Não há equivalência automática entre os fluxos `pipeline-sentenca`, `pipeline-minutar-pdf` e `pipeline-sentenca-team`: são instruções distintas.

## Executar e retomar uma sentença

Dentro do Claude Code:

```text
/pipeline-sentenca data/sentenca/NUMERO-CNJ/processo.txt
```

O fluxo principal grava arquivos com prefixo do número do processo, incluindo `-linha-tempo.md`, `-relatorio.md`, `-triagem.md`, `-analise.md`, `-fundamentacao.md` e `-sentenca.md`. Pesquisa e análise probatória condicionais acrescentam seus próprios artefatos. As fontes de citações são reunidas em `-fontes.json`.

No terminal, consulte o estado:

```bash
python scripts/verificar_sentenca.py data/sentenca/NUMERO-CNJ --numero NUMERO-CNJ
python scripts/verificar_sentenca.py data/sentenca/NUMERO-CNJ --numero NUMERO-CNJ --etapa relatorio
python scripts/verificar_sentenca.py data/sentenca/NUMERO-CNJ --numero NUMERO-CNJ --gate
```

| Modo | Interpretação |
| --- | --- |
| Sem opção de etapa | Lista os estados e imprime `PENDENTES`; pode terminar com código 0 mesmo havendo pendências |
| `--etapa relatorio` | Confere somente o relatório; código 0 indica validade segundo o script |
| `--etapa analise` | Também pode retornar código 3, sinalizando `ESCALAR` para trabalho adicional |
| `--rota` | Lê a rota estruturada da triagem |
| `--gate` | Retorna código 1 se houver etapa ausente ou inválida |

Erros de argumentos ou de identificação podem retornar código 2. Use `--numero` quando o nome da pasta não permitir inferir o identificador.

Para retomar, invoque novamente o fluxo para a mesma pasta. A varredura orienta o reaproveitamento das etapas válidas. Se alterar os autos ou um artefato intermediário, revise também os resultados posteriores: a verificação de formato não comprova que eles foram produzidos a partir da entrada atual.

O verificador de citações é uma conferência separada:

```bash
python scripts/verificar_citacoes.py data/sentenca/NUMERO-CNJ --id NUMERO-CNJ
```

O padrão é conferir `-fundamentacao.md`. Veja `--help` para selecionar outro documento. O fluxo de sentença prevê essa conferência; executar apenas `verificar_sentenca.py --gate` não substitui todos os controles do fluxo.

## Ferramentas de criação

Estas ferramentas pertencem ao plugin e usam o prefixo `superjurista-dev:`:

| Comando | Finalidade |
| --- | --- |
| `/superjurista-dev:instalar-superjurista` | Copiar o sistema para o projeto atual |
| `/superjurista-dev:planejar-sistema` | Planejar componentes, fluxo e contratos |
| `/superjurista-dev:criar-agente` | Criar um agente especializado |
| `/superjurista-dev:criar-orquestrador` | Criar um fluxo coordenador |
| `/superjurista-dev:criar-skill` | Criar uma skill com instruções e validação |
| `/superjurista-dev:criar-team` | Criar uma equipe de agentes |

As quatro skills da raiz são `criar-sistema`, `criar-skill`, `criar-mcp-precedente` e `criar-pje-download`. Consulte os respectivos arquivos em [skills](../skills/) para argumentos e dependências. A criação de uma integração não comprova que ela funciona no serviço externo: essa validação precisa ser registrada separadamente.
