# Fase 2 — ingestão de PDFs locais

[Voltar ao índice](README.md) · [Plano](../plan/feature-justica-trabalho-1.md)

O perfil `jt-1g-local` recebe um PDF ou uma pasta de PDFs, preserva os originais e extrai texto por página. Não consulta tribunais, PJe ou serviços de IA durante a ingestão Python. A classificação pelo agente é uma etapa separada, executada no provedor configurado no Claude Code.

## Preparação

Instale o perfil em uma pasta nova, conforme o [guia de instalação](instalacao.md). O instalador recusa substituir arquivos diferentes de uma instalação anterior: mantenha a pasta antiga preservada, instale esta versão em outra pasta e confira a transferência dos seus dados. Não copie todo o scaffold.

Na pasta instalada, usando Python **3.11 ou superior**:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Para páginas escaneadas ou com imagens, instale também Poppler (`pdfinfo` e `pdftoppm`) e Tesseract com idioma português (`por`). Confirme com `pdftoppm -v`, `tesseract --version` e `tesseract --list-langs`. Se necessário, configure `POPPLER_PATH` com a pasta dos executáveis, `TESSERACT_CMD` com o executável e `TESSDATA_PREFIX` com a pasta que contém `por.traineddata`. O modo JT usa `TESSDATA_PREFIX` ou o padrão do Tesseract; não procura automaticamente em `~/tessdata` como o legado.

No PowerShell, ative `.\.venv\Scripts\Activate.ps1` e ajuste os caminhos. A execução desta entrega foi verificada em macOS; Windows e Linux ainda precisam de teste próprio.

## Identificar e ingerir um caso

1. Coloque os PDFs em `data/entrada/`, fora da pasta de saída. Subpastas são aceitas. Somente arquivos com extensão `.pdf`, sem distinção de caixa, serão selecionados.
2. Copie `.claude/perfis/caso.exemplo.json` para `data/caso-confirmado.json` e preencha com informações conferidas nos autos. O exemplo é fictício e não serve como confirmação de um processo real.
3. Execute a ingestão e o verificador:

```bash
python scripts/ingerir_documentos.py \
  --input data/entrada \
  --workspace data/casos/CNJ-CONFIRMADO \
  --caso data/caso-confirmado.json

python scripts/verificar_documentos.py data/casos/CNJ-CONFIRMADO --gate
```

Para um único arquivo, use `--input data/entrada/inicial.pdf`. A pasta de saída pode ter qualquer nome: o número do processo vem dos metadados confirmados. `documentos[].arquivo` usa caminhos relativos à pasta de entrada ou apenas o nome quando a entrada é um PDF único. Mantenha esses nomes estáveis nas ingestões seguintes.

O contrato de [caso.json](../spec/schemas/caso.schema.json) exige número CNJ com módulo 97 válido, segmento 5, TRT de 1 a 24 coerente, unidade/código, instância 1, rito, fase, data de referência e escopo confirmado. O recorte atual aceita conhecimento, rito ordinário ou sumaríssimo. A checagem não consulta o cadastro oficial da unidade nem comprova competência ou adequação jurídica do caso.

`documentos` declara os arquivos esperados, seus tipos e se são obrigatórios. Um obrigatório ausente gera pendência. Arquivos adicionais são aceitos como `desconhecido`; declarar uma lista vazia não comprova que os autos estão completos. `id_pje` é opcional e só é copiado quando informado. `pendencias` registra questões conhecidas e impede a aprovação do gate.

## Artefatos e preservação

```text
data/casos/CNJ-CONFIRMADO/
├── caso.json
├── documentos.json
├── originais/DOC-<sha256>.pdf
├── texto/DOC-<sha256>/pagina-0001.bruto.txt
├── texto/DOC-<sha256>/pagina-0001.normalizado.txt
└── classificacao.json   # opcional, proposta produzida pelo agente
```

- O ID usa o SHA-256 completo do PDF copiado. Mesmo conteúdo sob nomes diferentes gera um único original e conserva os nomes de entrada. Declarações conflitantes para duplicatas abortam o lote.
- O índice registra ordem de ingestão, tipo declarado ou desconhecido, estados, páginas físicas iniciadas em 1 e referências aos textos. A ordem inicial é alfabética pelo caminho; acréscimos mantêm os IDs e a ordem já registrada.
- Cada texto recebe seu próprio hash. A normalização apenas uniformiza quebras de linha e Unicode NFC; não remove rodapés, assinaturas ou linhas repetidas. “Bruto” é a saída do extrator, não uma reprodução visual exata do PDF.
- Páginas sem texto ou com qualquer imagem passam por OCR em português. Quando há texto digital e imagem na mesma página, as duas extrações são preservadas, separadas por `[OCR DA MESMA PAGINA]`; pode haver conteúdo repetido.
- PDFs protegidos ou corrompidos mantêm o original e o motivo do bloqueio. Páginas com OCR indisponível, falha ou resultado vazio permanecem no índice com pendência. Não se tenta descobrir senhas.
- O histórico registra data, versão e hash do conversor, versões Python/pacotes/Poppler/Tesseract e entradas de cada lote. Quando `TESSDATA_PREFIX` aponta para o idioma, registra também seu hash.

O modo independente do conversor é `python .claude/skills/converter-pdf/scripts/pdf_para_txt.py --input ARQUIVO.pdf --output PASTA-NOVA --preservar-jt`. Ele grava `paginas.json` com o resultado por página; não substitui a ingestão com originais, metadados e índice. O comportamento legado sem essa opção foi preservado.

## Repetição, acréscimos e falhas

Repetir a mesma entrada não reescreve os artefatos nem acrescenta eventos. Novos PDFs ou novos nomes de duplicatas podem ser acrescentados mantendo o mesmo `caso.json`. Uma entrada já conhecida com conteúdo diferente é recusada; apresente a revisão com outro nome. Metadados divergentes exigem uma nova pasta de trabalho nesta fase.

A preparação ocorre em uma pasta temporária. Na primeira ingestão, a pasta pronta é publicada por renomeação. Nos acréscimos, os novos arquivos são escritos sem sobrescrever existentes e o índice é substituído atomicamente ao final; erros de gravação tratados removem os arquivos novos. Um lock impede duas ingestões simultâneas na mesma pasta.

Uma interrupção abrupta do processo ou falta de energia pode deixar lock, temporários ou arquivos não referenciados. Antes de remover um lock, confirme que não há ingestão em execução, preserve os artefatos e confira o índice. Esta fase não oferece recuperação automática de interrupções abruptas. PDFs com falha não são reprocessados silenciosamente ao repetir a entrada; após corrigir o OCR ou obter um arquivo legível, use uma nova pasta para reprocessar o conjunto.

## Verificação e classificação

O verificador confere contratos, identidade do caso, hashes dos originais/textos, total real de páginas, cobertura contínua, caminhos, histórico, arquivos declarados e referências da classificação, quando presente. Rejeita links simbólicos e caminhos que escapem da pasta. Os hashes detectam divergências contra o índice; não constituem assinatura digital ou prova de autenticidade.

| Execução | Código 0 | Código 1 | Código 2 |
| --- | --- | --- | --- |
| Ingestão | Sem erros ou pendências detectados | Artefatos gravados com bloqueios/pendências | Entrada, configuração ou operação inválida |
| Verificador | Sem erros de integridade; pendências ainda são exibidas | Erro de integridade | Contrato/caminho/configuração inválido |
| Verificador `--gate` | Sem erros ou pendências detectados | Erro ou pendência | Contrato/caminho/configuração inválido |

O agente [extrator-caso](../scaffold/agents/trabalhista/extrator-caso.md) propõe intervalos de páginas para petição, defesa, réplica, ata, jornada, contracheque, TRCT, FGTS, laudo, instrumento coletivo ou desconhecido. No Claude Code, peça explicitamente o uso desse agente com a pasta do caso e confira a saída. Ele não é executado automaticamente pela ingestão.

Se `classificacao.json` existir, cada página registrada deve aparecer exatamente uma vez, sem intervalos inexistentes ou sobrepostos, conforme o [schema](../spec/schemas/classificacao.schema.json). Após acrescentar documentos, a classificação anterior pode ficar incompleta: atualize-a e execute o gate novamente. Ausência de classificação ou tipo desconhecido não bloqueia o gate de ingestão; a validação jurídica das fases seguintes deverá avaliar essas lacunas.

## Evidências e limites da entrega

Em 05/11/2026, a suíte completa passou com **57 testes**, incluindo OCR real, em macOS com Python 3.12.16, Tesseract 5.5.4, Poppler 26.05.0 e as dependências fixadas nos arquivos de requisitos. O idioma português usado veio de [tessdata_fast, revisão 8741641](https://github.com/tesseract-ocr/tessdata_fast/tree/87416418657359cb625c412a48b6e1d6d41c29bd).

Na raiz do repositório, após instalar `requirements-dev.txt`:

```bash
TESTAR_OCR=1 python -m unittest discover -s tests -v
```

Sem `TESTAR_OCR=1`, o teste de OCR real é explicitamente ignorado. As fixtures versionadas são sintéticas e podem ser recriadas com `python tests/fixtures/gerar_pdfs.py`; a geração também requer Poppler. São cobertos PDFs digitais, escaneados, mistos, página híbrida, vazios, protegidos e corrompidos, linhas repetidas, duplicatas, ausência de documento, alterações de conteúdo, rollback, caminhos e instalação fora do repositório. Não se exige igualdade literal entre saídas de OCR de ambientes diferentes.

O OCR pode produzir texto incorreto sem falhar tecnicamente; compare tabelas, valores e trechos relevantes com o original. A extração usa limites de 5.000 páginas por PDF, 30 milhões de pixels por página a 200 DPI e 60 segundos por chamada de renderização/OCR. Não há limite global de duração do lote nem validação semântica automática de legibilidade.

O agente foi escrito e incluído na instalação, mas sua execução em Claude Code não foi testada neste ambiente. Não houve uso de autos reais, homologação por TRT ou validação jurídica. Análise de pedidos/provas, fontes oficiais, minuta e retomada das etapas jurídicas permanecem nas fases seguintes.
