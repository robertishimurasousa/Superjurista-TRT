# Fase 5 — minuta, revisão e retomada

O perfil mantém a arquitetura original: comando orquestrador, agentes que leem/gravam artefatos, verificadores determinísticos, no máximo duas tentativas por assinatura e montagem por script. Os agentes federais e as integrações PJe continuam separados. A implementação não transforma o projeto em aplicação web nem automatiza o julgamento.

## Uso

Instale o perfil em uma pasta separada conforme [instalação](instalacao.md), instale `requirements.txt` e abra o projeto no Claude Code. O controle de sessão usa `flock`, disponível em macOS/Linux. Execute:

```text
/pipeline-sentenca-trabalhista /caminho/para/pdfs --caso /caminho/caso.json
```

Também aceita um PDF e `--workspace /caminho/para/caso`. O padrão é `data/casos/<CNJ>`. A identidade e o rito devem estar confirmados em `caso.json`. São mantidas as restrições do piloto de primeiro grau, conhecimento, demandas individuais contra empregadores privados e PDFs locais.

O comando coordena ingestão → classificação → relato/pedidos → triagem → fontes/regras → análise → referências da análise → redação → referências da candidata → revisão → publicação local. As conferências humanas do inventário, das fontes e das referências continuam obrigatórias. Uma pendência humana interrompe o fluxo, preserva os artefatos e encerra normalmente a sessão para permitir retomada posterior.

## Artefatos

| Arquivo | Finalidade |
| --- | --- |
| `referencias-analise.json` | Citações/vínculos da matriz, com hash de minuta nulo |
| `redacao.json` | Relatório, fundamentos por pedido, questões processuais, parâmetros e dispositivo proposto |
| `minuta-candidata.md` | Montagem determinística a conferir antes da publicação |
| `referencias-candidata.json` | Referências da matriz e da candidata, vinculadas aos bytes atuais |
| `revisao.json` | Revisão técnica dos oito itens obrigatórios e pendências |
| `minuta.md` | Cópia da candidata que passou pelos gates |
| `referencias-minuta.json` | Registro de referências publicado junto à minuta |
| `publicacao.json` | Recibo com assinatura dos insumos e hash da minuta |
| `entrada-execucao.json` | Caminhos locais dos PDFs/metadados para detectar mudanças na entrada |
| `execucao.json` | Estado das etapas, tentativas, assinaturas e hashes das saídas |

Os contratos novos são [redação](../spec/schemas/redacao.schema.json) e [revisão](../spec/schemas/revisao.schema.json). No ordinário, o modelo exige relatório. No sumaríssimo, o modelo não insere relatório, e `relatorio` é nulo; o relato analítico permanece em `pedidos.json`. A minuta traz aviso de revisão humana e não contém assinatura de magistrado.

Fundamentação e dispositivo devem cobrir exatamente os pedidos, inclusive acessórios. O dispositivo precisa acompanhar a hipótese registrada na matriz; conclusão inconclusiva bloqueia a minuta. As cinco questões processuais (`processo`, `honorarios`, `custas`, `gratuidade`, `atualizacao`) têm fundamentação e dispositivo próprios. Os parâmetros reproduzem exatamente a matriz; a montagem não calcula valores nem escolhe índices.

O revisor examina pedidos/provas, fontes, rito, honorários, custas, gratuidade, parâmetros de cálculo e dispositivo. `nao-aplicavel` é permitido apenas nos quatro itens pertinentes, com justificativa e base normativa; nunca dispensa informação desconhecida. A comparação determinística de estruturas, IDs e hashes não interpreta a correção jurídica do texto. Conferência de mérito e aceite final permanecem humanos.

## Gates e montagem

Exemplos no projeto instalado, substituindo `PASTA` e `TOKEN` por argumentos individuais devidamente citados:

```bash
python scripts/verificar_referencias_jt.py PASTA --contexto --alvo analise
python scripts/verificar_referencias_jt.py PASTA --gate --alvo analise
python scripts/verificar_sentenca_jt.py PASTA --contexto redacao
python scripts/verificar_sentenca_jt.py PASTA --etapa redacao
python scripts/merge_sentenca_jt.py PASTA --token TOKEN --preparar
python scripts/verificar_referencias_jt.py PASTA --contexto --alvo candidata
python scripts/verificar_sentenca_jt.py PASTA --etapa candidata
python scripts/verificar_sentenca_jt.py PASTA --contexto revisao
python scripts/verificar_sentenca_jt.py PASTA --etapa revisao
python scripts/merge_sentenca_jt.py PASTA --token TOKEN
python scripts/verificar_sentenca_jt.py PASTA --gate
```

`--contexto` fornece hashes, não aprova conteúdo. O alvo padrão do verificador de referências permanece compatível com a fase 4 (`minuta.md`/`referencias-minuta.json`). O alvo `analise` ignora minutas antigas; o alvo `candidata` exige a candidata local.

A publicação exige redação, candidata, fontes, referências e revisão válidas e sem pendências. Escreve referências e recibo antes do último renomeio atômico para `minuta.md`. Falha capturada restaura os metadados anteriores e preserva a minuta anterior. Uma interrupção abrupta entre renomeios pode deixar metadados divergentes: o gate recusa o conjunto, e a retomada deve repetir a publicação validada. Não há transação única envolvendo três arquivos, nem garantia contra edição externa concorrente arbitrária. O fluxo compara assinaturas antes da publicação e o gate revalida os artefatos.

Mesmo quando válida, a saída registra `validacao_juridica: nao-realizada` e `aceite_humano: nao-registrado`. Não existe estado “sentença aprovada” nem envio ao tribunal.

## Retomada e exclusão de concorrência

`estado_execucao.py iniciar PASTA` cria uma sessão exclusiva e devolve o token. O bloqueio persistente fica ao lado do workspace; um segundo processo recebe erro. Cada operação também adquire um bloqueio do sistema operacional, impedindo gravações concorrentes com o mesmo token. O orquestrador não paraleliza agentes que escrevem no mesmo caso.

```bash
python scripts/estado_execucao.py entrada PASTA --token TOKEN --entrada PDF_OU_PASTA --caso METADADOS_JSON
python scripts/estado_execucao.py inventario PASTA --token TOKEN
python scripts/estado_execucao.py iniciar-etapa PASTA --token TOKEN --etapa redacao
# Executar o produtor e o merge de preparação.
python scripts/estado_execucao.py concluir-etapa PASTA --token TOKEN --etapa redacao
python scripts/estado_execucao.py encerrar PASTA --token TOKEN
```

A assinatura inclui PDFs externos registrados, metadados, originais/textos locais, saídas anteriores, perfil, prompts, schemas, modelos, scripts e fontes locais. Mudanças invalidam a etapa e seus descendentes. Alteração do pacote invalida conservadoramente todas as etapas. A validação de saídas é repetida antes de reutilizá-las, inclusive conferências vencidas. O estado preserva tentativas entre sessões; cada assinatura admite no máximo duas. Uma interrupção consome a tentativa iniciada. Mudança real de insumos inicia outro ciclo, sem apagar os artefatos anteriores.

Na carga inicial, a ingestão cria o workspace antes do registro das etapas; depois é validada e incorporada ao inventário. Fontes/regras devem estar importadas e conferidas antes de iniciar sua etapa. A assinatura inclui esses arquivos; mudança durante a etapa impede sua conclusão e exige novo inventário.

Se uma etapa já produziu um artefato correto, mas nunca foi registrada, inicie a etapa e conclua após o gate, sem regenerá-lo. Corrigir apenas hashes para aprovar conteúdo antigo é proibido. PDF externo divergente exige reingestão ou novo workspace conforme as restrições da fase 2. Um arquivo-fonte externo removido também impede retomada válida; preserve os caminhos de entrada usados no piloto.

## Bloqueio residual

Execute `python scripts/estado_execucao.py diagnostico PASTA`. Confira a sessão anterior e confirme que seu orquestrador, agentes e scripts já terminaram. Só depois registre explicitamente a recuperação:

```bash
python scripts/estado_execucao.py recuperar PASTA --token TOKEN_ANTERIOR --confirmar-interrupcao --diagnostico "Execução anterior encerrada; motivo e conferências realizadas."
```

O comando arquiva o diagnóstico ao lado do workspace e libera a sessão, preservando os artefatos e tentativas. Não identifica sozinho se um agente remoto ainda está ativo; a confirmação é operacional. Não execute recuperação automaticamente nem apague o lock silenciosamente. Um novo `iniciar` fornece outro token. Falhas normais usam `encerrar`; a recuperação é reservada a interrupções diagnosticadas.

## Migração e limites de validação

Para um caso da fase 4 sem minuta, copie `referencias-minuta.json` para `referencias-analise.json` somente se `minuta_sha256` for nulo e o destino não existir; execute o gate do alvo `analise`. Instalações anteriores com diferenças continuam apresentando conflitos, sem sobrescrita automática. Prefira nova instalação e preserve os dados do caso.

Os testes desta fase usam PDFs, regras e revisões inteiramente fictícios. Cobrem montagem dos dois ritos, omissões, inconsistências, citações ausentes, revisão pendente, alterações de insumos, limite de tentativas, exclusão de segundo processo, recuperação e falha de publicação. Não equivalem aos 12 casos, 36 execuções com modelo e aceite jurídico da fase 6. Claude Code e homologação de domínio ainda precisam ser exercitados no ambiente do piloto.

Em 05/11/2026, passaram **146 testes** em macOS/Python 3.12.16, incluindo OCR real: os 122 testes anteriores e 24 da fase 5. A instalação separada executou preparação, publicação e gate com os scripts e modelos instalados. Também passaram a conferência de schemas, sintaxe do pacote, dependências (`pip check`), links locais e `git diff --check`. O executável Claude Code não estava disponível neste ambiente; não houve execução dos agentes nem uso de autos reais.
