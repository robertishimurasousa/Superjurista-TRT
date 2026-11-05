# Fase 3 — modelo do caso e análise trabalhista

> Registro da entrega de análise. A integração de fontes e referências foi acrescentada na [fase 4](fase-4-fontes.md).

[Voltar ao índice](README.md) · [Plano](../plan/feature-justica-trabalho-1.md) · [Ingestão](fase-2-ingestao.md)

Esta entrega acrescenta contratos, agentes e verificação para produzir um inventário do caso, uma triagem e uma matriz provisória por pedido. Os agentes geram os arquivos no Claude Code; o script verifica os critérios implementados. Não há comando automático de geração nem fluxo de sentença nesta fase.

## Artefatos e responsabilidades

| Artefato na pasta do caso | Responsável pela produção | Contrato |
| --- | --- | --- |
| `pedidos.json` | `relator-trabalhista`, seguido de conferência humana do inventário | [pedidos.schema.json](../spec/schemas/pedidos.schema.json) |
| `triagem.json` | `triador-trabalhista` | [triagem.schema.json](../spec/schemas/triagem.schema.json) |
| `matriz-pedidos.json` | `analista-trabalhista` | [matriz-pedidos.schema.json](../spec/schemas/matriz-pedidos.schema.json) |
| `regras-juridicas.json` | Registro local com conferência do responsável de domínio | [regra-juridica.schema.json](../spec/schemas/regra-juridica.schema.json) |

O perfil instala os três agentes, os schemas, `scripts/verificar_pedidos.py` e a skill [analise-trabalhista](../scaffold/skills/analise-trabalhista/SKILL.md). Os requisitos Python/OCR permanecem os da fase 2. Instalações antigas com arquivos diferentes continuam exigindo revisão dos conflitos ou instalação em outra pasta; não há atualização destrutiva automática.

## Executar por etapas

1. Ingerir os PDFs e conferir `verificar_documentos.py PASTA --gate`.
2. Obter o contexto pelo comando abaixo. Fornecer ao agente os valores retornados, os caminhos do caso, dos schemas e do arquivo de saída. Hashes são calculados pelo script, nunca pelo modelo.
3. Pedir ao `relator-trabalhista` a produção de `pedidos.json`. Conferir a inicial/aditamentos e registrar o responsável/data em `conferencia_inventario` somente após a revisão humana.
4. Validar o relatório. Encaminhá-lo ao `triador-trabalhista`, obter contexto atualizado e validar a triagem. Impedimentos devem permanecer como `bloqueada` com explicação.
5. Fornecer ao `analista-trabalhista` os artefatos, a skill, o contexto atualizado e as regras locais disponíveis. Produzir a matriz provisória e validá-la. Quando a triagem estiver bloqueada ou faltar fonte conferida, produzir matriz bloqueada/inconclusiva preservando as informações úteis.

No terminal do projeto instalado:

```bash
python scripts/verificar_pedidos.py data/casos/CNJ-CONFIRMADO --contexto
python scripts/verificar_pedidos.py data/casos/CNJ-CONFIRMADO --etapa relatorio --gate
python scripts/verificar_pedidos.py data/casos/CNJ-CONFIRMADO --etapa triagem --gate
python scripts/verificar_pedidos.py data/casos/CNJ-CONFIRMADO --etapa analise --gate
```

Execute cada verificação depois que o respectivo arquivo existir. O script não escreve nos artefatos e não chama IA, portais ou MCPs. `--contexto` apenas exibe identidade, hashes atuais e pendências documentais; código 0 nesse modo não aprova uma etapa.

## Modelo dos dados

O relatório contém partes (`PAR-001`), contratos (`CON-001`), pedidos (`PED-001`), atos de audiência (`ATO-001`), cobertura de páginas e pendências. Preserve IDs nas correções. Pedidos acessórios apontam para um principal existente. Cada pedido identifica reclamante, reclamadas e contratos e contém uma defesa por reclamada; múltiplas empresas não são fundidas numa resposta genérica.

Campos factuais informados exigem valor e referência ao documento, à página física e a um trecho literal curto. O verificador procura o trecho no texto bruto, normalizando apenas Unicode e espaços. Encontrar o trecho confirma sua localização; não comprova que ele sustente a interpretação atribuída pelo agente.

Um dado ausente é representado assim:

```json
{
  "estado": "nao-informado",
  "valor": null,
  "referencias": [],
  "motivo": "A data de término não foi localizada nos documentos recebidos."
}
```

Ausência de valor pedido ou de campos coletivos não aplicáveis aparece em `lacunas` e não é preenchida automaticamente. Campos necessários à matéria geram pendência impeditiva: descrição/fatos/defesas, período inicial, período final nas matérias distintas de vínculo, função para vínculo/jornada e salário para verbas salariais/rescisórias. Esse conjunto inicial é conservador e não esgota os requisitos jurídicos de cada pretensão.

A cobertura contabiliza cada página e os pedidos nela identificados. O verificador detecta pedido existente no inventário que foi omitido da triagem/matriz, pedido sem página de cobertura, IDs duplicados e possíveis duplicatas de objeto/período. Não consegue identificar por si só um pedido que o relator nunca extraiu; por isso o inventário exige conferência humana contra os autos.

## Triagem e matriz

A triagem registra competência, rito, fase, demanda individual e natureza dos empregadores como confirmados, incertos ou fora do escopo, com justificativas. O recorte material do plano permanece sujeito à validação de domínio: vínculo, jornada e verbas salariais/rescisórias em reclamações individuais contra empregadores privados. O bloqueio de produto não é uma decisão sobre competência judicial.

Cada questão lista provas necessárias, sua disponibilidade e caráter decisivo, além das fontes a conferir. Prova decisiva ausente, escopo incerto, matéria fora do recorte ou pendências do relatório impedem aprovação. A análise não pode ignorar a triagem bloqueada nem converter falta de defesa em concordância.

A matriz contém fatos e suas versões, defesas por reclamada, provas, proposta fundamentada de ônus, parâmetros informados, aplicabilidade coletiva e conclusão motivada. Os resultados possíveis são inconclusão ou hipóteses de deferimento, indeferimento ou acolhimento parcial. Questões de processo, honorários, custas, gratuidade e atualização são obrigatoriamente tratadas em seção própria, com regras do tema ou pendência.

Instrumento coletivo necessário exige documento e dados de vigência/categoria/território. Incompatibilidades de período ou âmbito bloqueiam para conferência; não se estende vigência automaticamente. Distribuição dinâmica de ônus exige decisão referenciada. As lentes probatórias herdadas foram revistas na skill: não se importam escores de confiabilidade, probabilidades heurísticas ou standards penais como critérios automáticos de procedência.

## Regras e dependência da fase 4

A [matriz normativa](../scaffold/skills/analise-trabalhista/references/matriz-normativa.md) é um roteiro de temas e pontos de partida oficiais. Não distribui teses homologadas, percentuais, índices ou uma coleção de regras já conferidas.

`regras-juridicas.json` é um contrato preliminar, separado dos documentos dos autos. Cada regra registra tema, tipo, referência, órgão, URL oficial, texto, arquivo local, SHA-256, vigência, situação, contexto temporal e conferência com responsável/data. Nesta fase, o conteúdo deve ser UTF-8 em `fontes/*.txt` dentro do caso; não há importador de fontes.

O verificador exige HTTPS em domínio governamental, legislativo ou judicial brasileiro, confere o hash local e a presença do trecho na fonte. Esses controles não autenticam a página de origem nem confirmam o estado jurídico da regra. A conferência humana é uma declaração registrada, não uma assinatura autenticada. Regras não conferidas, de situação incerta/suspensa/revogada/superada ou sem conteúdo válido impedem a hipótese que dependa delas. O controle de período verifica sobreposição; não resolve modulação, pertinência ou direito intertemporal.

Sem regras, a matriz pode ser registrada como bloqueada, com conclusão inconclusiva e pendências. A importação ampliada, consolidação e validação de referências/fontes continuam na fase 4. TASK-014 registra essa dependência explicitamente.

## Resultado do verificador

| Modo | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Sem `--gate` | Contratos/referências coerentes, podendo haver pendências | Artefato ausente, incoerente ou desatualizado | Schema, caminho ou configuração inválido |
| Com `--gate` | Nenhum erro ou pendência impeditiva detectado na etapa | Erro ou pendência impeditiva | Schema, caminho ou configuração inválido |

O JSON distingue `erros`, `pendencias`, `lacunas`, `valido_tecnicamente` e `sem_pendencias`. O estado é `invalida`, `bloqueada` ou `valida`. Mesmo com código 0, `apto_para_minuta` permanece **false**, `validacao_juridica` é `nao-realizada` e o aceite humano final não é registrado nesta fase.

Hashes de `documentos.json`, `pedidos.json`, `triagem.json` e do registro de regras impedem reutilização silenciosa quando esses insumos mudam. Isso não é o motor completo de retomada da fase 5: alterações em prompts/perfil, gestão de tentativas e invalidação automática ainda não estão implementadas. Não atualize apenas o hash de uma saída antiga para fazê-la passar; reavalie seu conteúdo após a mudança do insumo.

## Testes e limites

A suíte usa somente dados sintéticos, incluindo duas reclamadas, pedido acessório, prova decisiva ausente, instrumento coletivo ausente, períodos incompatíveis, campos não informados, IDs/trechos inválidos, fontes alteradas/não conferidas e bloqueios propagados. As regras da fixture são fictícias e não representam fontes jurídicas utilizáveis.

```bash
TESTAR_OCR=1 python -m unittest discover -s tests -v
```

Resultado desta entrega em macOS/Python 3.12.16: **88 testes aprovados**, incluindo os 57 anteriores e 31 testes da fase 3. O OCR real foi executado com Tesseract/`por` e Poppler, conforme a fase 2. Schemas, sintaxe, links locais, dependências e instalação independente foram conferidos.

Os testes validam o código, os contratos e o tratamento de casos sintéticos. Os três agentes não foram executados no Claude Code neste ambiente. Permanecem pendentes avaliação das extrações/conclusões por responsável trabalhista, execução com autos autorizados, validação em outros sistemas operacionais e homologação do piloto.
