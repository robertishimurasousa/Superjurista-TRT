# SuperJurista TRT

**Ferramentas de inteligência artificial para apoiar a análise de processos, a pesquisa de jurisprudência e a elaboração de minutas, com foco na adaptação à Justiça do Trabalho.**

[Começar](docs/instalacao.md) · [Comandos](docs/uso.md) · [Arquitetura](docs/arquitetura.md) · [Documentação](docs/README.md)

O SuperJurista TRT reúne um plugin para **Claude Code** e uma estrutura inicial de projeto, chamada `scaffold`, com agentes especializados, fluxos de trabalho e servidores MCP. Os agentes produzem documentos em disco; scripts verificam contratos de saída e permitem retomar etapas pendentes.

Este repositório deriva do [superjurista-dev, de George Marmelstein](https://github.com/georgemarmelstein/superjurista-dev). A base distribuída mantém componentes voltados à Justiça Federal e ao TRF5. A adaptação para TRT precisa considerar o tribunal, o PJe e as fontes de jurisprudência utilizados. Veja o [estado da adaptação](docs/adaptacao-trt.md).

> [!IMPORTANT]
> Os resultados são materiais de apoio sujeitos à revisão humana. A aprovação dos verificadores confirma os critérios implementados nos scripts; não comprova a correção jurídica da minuta nem a compatibilidade com um TRT.

## Estado do piloto trabalhista

O perfil `jt-1g-local` já oferece instalação seletiva e ingestão de PDFs locais: originais preservados, hashes, texto por página, OCR em português e verificação de referências. A fase 3 acrescenta contratos e agentes para relato, triagem e análise provisória por pedido, com verificação de cobertura, referências e bloqueios. A fase 4 acrescenta importação de fontes locais, conferência por hashes, consolidação e rastreabilidade de citações. **Sentença e homologação jurídica permanecem pendentes.** Consulte os guias das [fases 1](docs/fase-1-perfis.md), [2](docs/fase-2-ingestao.md), [3](docs/fase-3-analise.md) e [4](docs/fase-4-fontes.md), além do [plano](plan/feature-justica-trabalho-1.md).

## Componentes herdados disponíveis no repositório

| Recurso | Conteúdo |
| --- | --- |
| Criação de sistemas | 6 comandos, 4 skills e 5 agentes de geração e validação |
| Processamento judicial | 16 comandos para sentença, embargos, pesquisa, provas, revisão e documentos |
| Agentes especializados | 52 agentes em 7 categorias |
| Skills de domínio | 7 skills, incluindo PJe, PDF/OCR e análise probatória |
| Pesquisa via MCP | 5 servidores: BNP/CNJ, CJF, TCU, TJSC e TNU |
| Verificação e consolidação | 10 scripts Python, incluindo validação de perfil, etapas, citações e consolidação de artefatos |

O projeto é executado dentro do Claude Code. Não há aplicação web, banco de dados próprio ou servidor HTTP central a iniciar.

## Início rápido

Requisitos da ingestão local: Git e Python **3.11 ou superior**; PDFs escaneados exigem Poppler e Tesseract com idioma `por`. O instalador isolado continua compatível com Python 3.9. Claude Code é necessário para carregar o plugin. O legado com MCP exige Python 3.10 ou superior e dependências próprias.

Clone este repositório e abra o Claude Code em uma pasta separada para os processos:

```bash
git clone https://github.com/robertishimurasousa/Superjurista-TRT.git
mkdir superjurista-trt-trabalho
cd superjurista-trt-trabalho
claude --plugin-dir ../Superjurista-TRT
```

Dentro do Claude Code, execute o instalador:

```text
/superjurista-dev:instalar-superjurista
```

O identificador técnico continua sendo `superjurista-dev`, conforme o [manifesto do plugin](.claude-plugin/plugin.json). Por isso, ele aparece no prefixo dos comandos, mesmo que o nome do repositório seja SuperJurista TRT. O carregamento local por `--plugin-dir` é documentado pelo [Claude Code](https://code.claude.com/docs/en/plugins/create).

O padrão agora é o perfil `jt-1g-local`: componentes definidos no manifesto e `data/casos/`, sem MCPs ou comandos judiciais herdados. A instalação federal exige a opção explícita `--legado-federal`, em outra pasta.

Também é possível instalar a base sem Claude Code, a partir do repositório:

```bash
python3 scripts/instalar_perfil.py --perfil jt-1g-local --destino ../superjurista-trt-trabalho --dry-run
python3 scripts/instalar_perfil.py --perfil jt-1g-local --destino ../superjurista-trt-trabalho
```

Confira conflitos e componentes preexistentes no resumo. Consulte o [guia da fase 1](docs/fase-1-perfis.md).

## Exemplo do legado federal

Os comandos abaixo pertencem ao legado federal e **não são instalados no perfil local trabalhista**. Após instalar explicitamente o legado e preparar suas integrações, use apenas um processo de teste autorizado:

```text
/relatar-processo data/sentenca/NUMERO-CNJ/processo.txt
/pipeline-sentenca data/sentenca/NUMERO-CNJ/processo.txt
```

Substitua `NUMERO-CNJ` pelo número completo do processo. Os artefatos ficam na pasta de trabalho do caso. O fluxo de sentença inclui linha do tempo, relatório, triagem, análise, fundamentação e consolidação. A triagem pode acionar pesquisas e análise probatória adicionais.

Para conferir pendências no terminal, a partir do projeto instalado:

```bash
python scripts/verificar_sentenca.py data/sentenca/NUMERO-CNJ --numero NUMERO-CNJ
```

A linha `PENDENTES` orienta a retomada. Consulte os [comandos e as verificações](docs/uso.md) para distinguir varredura de aprovação final.

## Estrutura do repositório

```text
Superjurista-TRT/
├── .claude-plugin/     # Identidade e metadados do plugin
├── commands/           # Comandos para instalar e criar componentes
├── agents/             # Geradores e validadores de componentes
├── skills/             # Criação de sistemas, skills e integrações
├── scaffold/           # Componentes copiados para o projeto de trabalho
├── spec/               # Especificações, modelos e referências do framework
├── docs/               # Guias deste repositório em português
└── sync-scaffold.ps1   # Prepara importação upstream para revisão
```

## Guias

| Preciso de… | Leia |
| --- | --- |
| Instalar e preparar o ambiente | [Instalação](docs/instalacao.md) |
| Escolher um comando e conferir resultados | [Uso e comandos](docs/uso.md) |
| Entender agentes, etapas e contratos | [Arquitetura](docs/arquitetura.md) |
| Configurar pesquisa, OCR e PJe | [Integrações](docs/integracoes.md) |
| Avaliar o que falta para um TRT | [Adaptação para TRT](docs/adaptacao-trt.md) |
| Tratar dados e credenciais | [Dados e segurança](docs/seguranca.md) |
| Diagnosticar uma falha | [Solução de problemas](docs/solucao-de-problemas.md) |
| Alterar e verificar o projeto | [Desenvolvimento](docs/desenvolvimento.md) |

O [índice da documentação](docs/README.md) também reúne os arquivos de contribuição, histórico e créditos.
