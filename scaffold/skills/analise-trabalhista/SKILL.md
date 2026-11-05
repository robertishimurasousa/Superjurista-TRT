---
name: analise-trabalhista
description: Use ao analisar vínculo, jornada e verbas salariais ou rescisórias no piloto trabalhista de primeiro grau com PDFs locais.
---

# Análise trabalhista rastreável

Esta skill organiza perguntas, provas e lacunas para uma matriz provisória. Leia `references/matriz-normativa.md` para o roteiro de conferência jurídica. Não contém teses pré-aprovadas ou parâmetros de cálculo.

## Por matéria

| Matéria | Dados a confrontar | Lacunas que exigem explicação |
| --- | --- | --- |
| Vínculo | Partes, função, período alegado, forma da prestação, contraprestação e versões de cada reclamada | Data/função ausente, regime incerto, divergência sobre empregadora ou responsabilidade |
| Jornada | Períodos, registros diários, intervalos, escalas, acordos e depoimentos | Meses sem controles, OCR que alterou horários, incompatibilidade entre cartões e prova oral |
| Verbas salariais | Rubricas, competências, recibos, salário informado e fundamentos de cada diferença | Parcela sem período, ausência de recibo, dúvida sobre base ou natureza da rubrica |
| Verbas rescisórias | Término, modalidade alegada, documentos rescisórios, pagamentos e controvérsias | Data/modalidade incerta, comprovantes ausentes, controvérsia sobre quitação |
| Norma coletiva | Instrumento, vigência, categoria, base territorial e cláusula pertinente | Instrumento ausente, âmbito incompatível, período descoberto ou aplicabilidade controvertida |

A lista orienta investigação; não cria presunções nem substitui norma aplicável. Não preencha informações faltantes com “padrões” de contratos ou de outros processos.

## Valoração e ônus

Reaproveite a disciplina de localizar a prova, identificar sua origem, examinar integridade, contexto, impugnações e contradições. As lentes genéricas de análise probatória do legado foram revistas para este recorte: não importar standards penais, notas de confiabilidade ou probabilidades bayesianas como limiares de procedência. Evite somar quantidade de documentos como medida de força probatória.

Distinga a alegação da parte, o conteúdo de um documento e a inferência do analista. A qualidade do OCR não prova autenticidade; uma coincidência textual não prova pertinência. Explicite hipótese alternativa e elementos contrários. Não atribua comportamento ou credibilidade a categorias pessoais.

A proposta sobre ônus exige regra aplicável e contexto processual. Redistribuição não é automática: registre a decisão disponível e eventual pendência de contraditório. O sistema não decide se o encargo foi juridicamente satisfeito.

## Saída e bloqueios

Use os schemas instalados para `pedidos.json`, `triagem.json`, `matriz-pedidos.json` e `regras-juridicas.json`. Regras sem conferência humana, conteúdo local ou situação conhecida impedem a conclusão que dependa delas. Citá-las nos autos não supre essa conferência.

Registre questões processuais e matérias examináveis de ofício separadas do inventário de pedidos. Não invente pedidos para preencher a matriz. Preserve todos os acessórios declarados e a vinculação ao principal. Bloqueios de triagem continuam na matriz com conclusão inconclusiva.

A validade técnica pode ser verificada por script; pertinência da prova, completude semântica da extração e correção jurídica exigem revisão humana. As fontes oficiais locais e as referências de futura minuta são verificadas pelos scripts da fase 4. Vincule cada regra usada ao corpus conferido e execute o gate de referências. Não produza sentença nesta fase.
