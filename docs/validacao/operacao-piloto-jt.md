# Operação e validação do piloto trabalhista

O fluxo continua sendo comando → agentes → artefatos → verificadores. Esta fase acrescenta corpus, regressão, evidências e fichas de revisão; não amplia a competência do piloto nem substitui o responsável pelo julgamento.

## Responsabilidade e estado

O próprio mantenedor indicou que será o responsável pela revisão jurídica. Essa indicação não significa aprovação dos casos. O nome, data, confirmação do recorte e aceite de cada ficha devem ser preenchidos por ele após examinar as três repetições. A homologação permanece pendente até concluir TASK-030 e TASK-031. Consulte o [relatório de evidências](piloto-jt-local.md) e o [plano](../../plan/feature-justica-trabalho-1.md).

O recorte continua: primeiro grau, conhecimento, demandas individuais contra empregadores privados, ritos ordinário/sumaríssimo e PDFs locais. Não há assinatura, protocolo, integração PJe ou liquidação automática. A referência a TRT12 nos casos é fictícia e não representa homologação desse tribunal.

## Instalar e preparar

Use uma instalação separada conforme [instalação](../instalacao.md), Python 3.11+ e `requirements-dev.txt` para gerar o corpus/testá-lo. O projeto operacional usa `requirements.txt`. Instale Poppler, Tesseract e o idioma `por`. O controle de sessão requer macOS/Linux.

Na raiz deste repositório:

```bash
python scripts/preparar_avaliacao_jt.py --destino data/avaliacao-piloto
```

Isso cria 12 pastas de entradas sintéticas, um `avaliacao.json` com 36 registros não executados e 12 fichas humanas pendentes. A preparação exige destino novo e não sobrescreve avaliação anterior. Os PDFs contêm aviso de ficção e uma instrução adversarial claramente identificada como dado dos autos.

Os geradores de **oráculos técnicos**, em `tests/fixtures/`, também preenchem respostas e conferências fictícias para exercitar os verificadores. Esses workspaces são exclusivos dos testes de software. Nunca reutilize as regras, fontes, revisões ou minutas dos oráculos como referência jurídica ou resultado de Claude Code. O comando de preparação acima gera somente entradas, sem oráculos.

## Executar os 12 casos três vezes com Claude Code

1. Prepare fontes oficiais locais reais e regras pertinentes ao corpus, com conferência do responsável conforme a [fase 4](../fase-4-fontes.md). URLs oficiais ou texto fictício não substituem fontes. No cenário `fonte-nao-conferida`, deixe a fonte designada sem conferência para exercitar o bloqueio.
2. Registre a versão do Claude Code e o identificador exato do modelo. Use o mesmo pacote/manifesto da preparação; o verificador detecta mudanças. Uma mudança relevante exige novo conjunto de avaliação, preservando o anterior.
3. Para cada caso, use uma pasta e sessão independentes por repetição. Execute `/pipeline-sentenca-trabalhista` com o PDF, `--caso` e `--workspace`. Não forneça ao agente as respostas dos testes. Não repita uma sessão já concluída como se fosse nova execução.
4. Registre início/fim com fuso e duração real. Preserve uma transcrição local distinta por execução, incluindo pausas, erros, intervenções e revisão humana. Confira as solicitações de inventário/fontes/referências; não peça ao agente que ateste conferências em seu nome. O tempo total inclui as pausas humanas, que devem ser descritas em `observacoes`.
5. Confira resultado e etapa com o manifesto. Uma falha de contrato ou falta de dependência não equivale ao bloqueio jurídico/documental esperado. No bloqueio de fontes sem corpus publicado, o inventário verifica as importações e mantém a consolidação pendente.
6. Salve o retorno do gate em `resultado-gate.json` no workspace dos casos bloqueados. Para minutas, execute `verificar_sentenca_jt.py PASTA --gate`; o recibo e as referências devem acompanhar os mesmos bytes.
7. Preencha o registro correspondente em `avaliacao.json`: `estado: executada`, modelo, versão, timestamps, duração, caminhos relativos de `workspace`/`transcricao`, hash da transcrição, resultado (`minuta-tecnica` ou `bloqueio`), etapa, observações e mapa `artefatos_sha256`. Preserve os hashes de entrada fornecidos na preparação.

O mapa de artefatos deve incluir `caso.json` e `documentos.json`; em minutas, também `minuta.md`, `publicacao.json`, `revisao.json` e `referencias-minuta.json`; em bloqueios, `resultado-gate.json`. Inclua os demais arquivos examinados na revisão. Calcule SHA-256 dos bytes, sem editar saídas antigas apenas para ajustar hashes. Caminhos de evidência devem estar dentro da pasta da avaliação, sem links simbólicos.

A coleta é operacional e declarada pelo responsável. O verificador confere contratos, hashes e gates atuais; não autentica a execução de Claude Code, a identidade do revisor ou a autoria da transcrição. Inspeção da transcrição e confirmação de que o modelo ignorou a instrução adversarial fazem parte da revisão humana. Testes de scripts não demonstram resistência do modelo a injeção de instruções.

## Revisão jurídica e aceite

Cada ficha exige conferência de **fatos, pedidos, fontes, rito, encargos e dispositivo**, com observação em cada item. Mesmo os casos bloqueados devem ser revisados: o bloqueio precisa ocorrer pela razão correta, sem minuta conclusiva.

Compare as três execuções e registre variações materiais. Não aceite um caso enquanto houver defeito aberto. São críticos: fato inventado decisivo, pedido omitido, fonte falsa, regra federal indevida e conclusão fora do escopo. Após corrigir um defeito crítico, registre a correção e repita as três execuções do caso afetado, preservando o histórico anterior.

Somente o responsável preenche `estado: aceito`, nome, data, `recorte_confirmado: true`, `execucoes_revisadas: [1, 2, 3]`, critérios `conferido`, avaliação da variação e justificativa. Defeitos corrigidos registram `estado: resolvido`, `correcao` e `reexecucoes: [1, 2, 3]`. O aceite global `registrado-pelo-responsavel` também exige ação humana; não é preenchido por scripts ou agentes.

```bash
python scripts/verificar_aceite_piloto.py data/avaliacao-piloto/avaliacao.json
```

Código 0 indica completude técnica do registro e das declarações; 1 indica pendências/erros; 2 indica contrato/entrada inválidos. O comando é somente leitura. Um registro completo não é assinatura autenticada, certificação institucional ou garantia de correção jurídica.

## Bloqueios, retomada e recuperação

Siga a [fase 5](../fase-5-minuta.md). Não remova locks automaticamente, não compartilhe tokens entre casos e não altere `execucao.json` para zerar tentativas. Mudança em PDF, prompt, perfil ou fonte invalida etapas dependentes; correções devem ser reavaliadas. Uma classificação inválida pode ser corrigida sem perder a ingestão íntegra. A consolidação de fontes pendente não pode ser confundida com corpus publicado.

Em falha de publicação, preserve os arquivos e execute o gate. A minuta usa renomeio atômico, mas os três arquivos publicados não constituem transação única. Queda entre metadados e minuta exige nova publicação validada. A recuperação de sessão requer confirmar que o processo anterior terminou e registrar diagnóstico explícito.

## Testes locais, Linux e CI

```bash
TESTAR_OCR=1 python scripts/validar_repositorio.py --exigir-ocr --saida data/validacao/local.json
```

Configure `TESSDATA_PREFIX` quando o idioma não estiver no diretório padrão. O comando confere schemas, sintaxe, dependências, links, instalação temporária, corpus e testes. Gera somente metadados técnicos: versões, hashes, duração, IDs dos testes e resultados. Não executa agentes, acessa tribunais ou homologa o piloto.

```bash
docker build -f tests/Dockerfile.validacao -t superjurista-trt-validacao:fase6 .
mkdir -p data/validacao/docker
docker run --rm -v "$PWD:/app:ro" -v "$PWD/data/validacao/docker:/evidencias" superjurista-trt-validacao:fase6
```

A [CI](../../.github/workflows/validacao.yml) executa Linux/Python 3.11 e 3.12 com OCR, sem secrets do piloto, permissões de leitura e actions fixadas por SHA. Publica somente o JSON técnico. As referências das actions foram verificadas nos projetos oficiais: [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python) e [upload-artifact](https://github.com/actions/upload-artifact).

O [inventário de fixtures](../../tests/fixtures/inventario-seguranca.json) bloqueia arquivos não inventariados ou bytes alterados. Há uma varredura limitada de padrões de credenciais; ela não substitui revisão humana. É proibido adicionar autos reais, dados pessoais reais, cookies, credenciais ou transcrições privadas ao corpus versionado. Ao mudar uma fixture, revise conteúdo/origem antes de atualizar seu hash. Nenhum hash prova que um documento é sintético.
