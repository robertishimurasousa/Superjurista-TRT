# Diagnóstico de adaptação à Justiça do Trabalho

Data: 05/11/2026. Base examinada: commit `22da97af489116eee6518b9c7eb44b3e026f555e`.

[Documentação](README.md) · [Plano de implementação](../plan/feature-justica-trabalho-1.md)

## Conclusão

A arquitetura de agentes, arquivos e verificadores pode ser reaproveitada. O fluxo atual ainda não é apropriado para produzir minutas trabalhistas: contém pressupostos federais na triagem, na fundamentação, na pesquisa, na revisão e nos contratos de saída. Trocar nomes e URLs deixaria esses pressupostos ativos.

O escopo confirmado para a primeira entrega é **1º grau, com PDFs locais**. A proposta é criar um perfil `jt-1g-local` e um comando próprio de sentença trabalhista, com entrada documental rastreável, análise por pedido e revisão humana. A integração PJe, os recursos de 2º grau e a automação de cálculos ficam fora desse primeiro piloto.

## Método e limites da análise

Foram examinados agentes, comandos, verificadores Python, conversão de PDF, scripts PJe, instalador e sincronizador. Foram feitas sondagens locais de funções com dados sintéticos, sem executar agentes, acessar sessões PJe ou processar autos reais. Claude Code não está disponível neste ambiente; a execução completa não foi verificada.

As fontes externas consultadas são oficiais. O portal de jurisprudência do TST apresentou dependência de JavaScript, e páginas de precedentes apresentaram proteção de acesso. Não foi demonstrada a existência de uma API pública utilizável por este projeto. A obtenção automatizada de jurisprudência precisa de investigação própria.

## Achados e impactos

| Prioridade | Evidência no repositório | Impacto | Encaminhamento |
| --- | --- | --- | --- |
| P0 | [fundamentador-marmelstein.md](../scaffold/agents/analise/fundamentador-marmelstein.md), linhas 31, 181 e 219–253 | Domínio previdenciário/cível, assinatura federal e honorários orientados pelo CPC | Criar fundamentador trabalhista e contrato próprio; revisar a base normativa |
| P0 | [verificar_sentenca.py](../scaffold/scripts/verificar_sentenca.py), linhas 54–67 | Fundamentação e sentença exigem `juiz federal` | Gate trabalhista separado, com identificação do juízo e estrutura conforme o rito |
| P0 | [triador-processual.md](../scaffold/agents/analise/triador-processual.md), linhas 4, 104 e 136–137 | Triagem usa BNP/JULIA e convergência de turmas do TRF5 | Triagem por pedido, prova, rito e fontes adequadas à JT |
| P0 | [pipeline-sentenca.md](../scaffold/commands/pipeline-sentenca.md), linhas 239–274 | Pesquisa básica é BNP/CJF/JULIA; STJ/TNU opcionais | Novo fluxo local, sem dependência obrigatória desses serviços |
| P0 | [merge_fontes.py](../scaffold/scripts/merge_fontes.py), linhas 46–51 | Lista de origens autorizadas não inclui TST/TRT; rejeita nova origem trabalhista | Contrato de fontes do perfil JT, com origem oficial verificável |
| P0 | [verificar_citacoes.py](../scaffold/scripts/verificar_citacoes.py), linhas 69–84 e 106–123 | Junta jurisprudência e autos no mesmo corpus; examina aspas longas, sem exigir registro de toda referência | Separar fontes jurídicas de provas; validar identificadores e vínculos entre afirmações e fontes |
| P0 | [verificador-honorarios.md](../scaffold/agents/revisao/verificador-honorarios.md), linhas 15 e 138–152 | Regras de vara federal/JEF podem ser aplicadas indevidamente | Revisor trabalhista de honorários, custas e gratuidade, com regras temporais verificadas |
| P0 | [verificador-calculos.md](../scaffold/agents/revisao/verificador-calculos.md), linhas 13–35 e 67–77 | Contexto federal e regra de correção aplicada como fallback quando a matéria é desconhecida | Remover fallback no perfil JT; produzir parâmetros e pendências, sem liquidação automática |
| P0 | [merge_sentenca.py](../scaffold/scripts/merge_sentenca.py), linhas 36–47 | Concatena obrigatoriamente relatório e fundamentação | Composição conforme rito; resumo analítico interno separado do documento final |
| P0 | [pdf_para_txt.py](../scaffold/skills/converter-pdf/scripts/pdf_para_txt.py), linhas 145–172 e 207–231 | Há marcadores de página, mas a limpeza remove linhas repetidas e não mantém índice estruturado de documentos | Preservar texto bruto; evitar perda silenciosa de jornadas/rubricas repetidas; registrar documento e página |
| P0 | [verificar_pipeline.py](../scaffold/scripts/verificar_pipeline.py) e [verificar_sentenca.py](../scaffold/scripts/verificar_sentenca.py), função `verificar_etapa` | Retomada baseada no artefato existente, sem assinatura dos insumos | Invalidar resultados quando documentos, perfil, prompts ou fontes mudarem |
| P0 | [sync-scaffold.ps1](../sync-scaffold.ps1), linhas 24–49 | Caminhos fixos do ambiente original; remove áreas antes de copiá-las | Definir o scaffold versionado como fonte do derivado e tornar importação upstream uma operação revisável |
| P1 | [verificador-remessa.md](../scaffold/agents/revisao/verificador-remessa.md) e [verificar_revisao.py](../scaffold/scripts/verificar_revisao.py) | Revisão de remessa federal aparece como etapa fixa | Classificar aplicabilidade; no piloto privado, registrar inaplicabilidade fundamentada; casos públicos/especiais exigem revisão própria |
| P1 | [pipeline-minutar-pdf.md](../scaffold/commands/pipeline-minutar-pdf.md), linhas 142–148 | Fluxo alternativo mantém contratos antigos, apesar de receber PDF diretamente | Direcionar o piloto a uma única entrada e impedir execução acidental do legado nesse perfil |
| P1 | [project-gitignore](../scaffold/project-gitignore) | Não exclui todos os artefatos processuais, HAR ou `.env` | Ignorar toda a pasta de casos e manter testes sintéticos separados |
| P2 | [listar_processos.py](../scaffold/skills/pje-download/scripts/listar_processos.py), linhas 24–88, e [baixar_pdfs.py](../scaffold/skills/pje-download/scripts/baixar_pdfs.py), linhas 29–108 | URL, tarefas, cabeçalhos e autenticação específicos do TRF5 | Adaptador PJe por tribunal em projeto posterior; não interfere na entrada local |

P0 significa necessário antes de considerar uma minuta apta à revisão no piloto; P1 completa a operação controlada e sua validação; P2 é evolução posterior. Um protótipo incompleto pode gerar relatórios técnicos, mas não deve se apresentar como fluxo trabalhista validado.

## Verificações locais reproduzidas

| Sondagem | Resultado observado | Limite da conclusão |
| --- | --- | --- |
| `merge_fontes.validar_item()` com `origem_mcp=tst-jurisprudencia` e demais campos preenchidos | Rejeição: origem não autorizada | Confirma bloqueio do contrato atual; não testa um servidor TST |
| `verificar_citacoes.verificar()` com afirmação sem aspas, corpus vazio e limiar 60 | Nenhum problema e zero citações conferidas | Confirma que a checagem não cobre toda referência jurídica |
| `verificar_sentenca.RE_CNJ.fullmatch()` com exemplo sintético do segmento 5 | Aceita o formato | O formato trabalhista já cabe na regex; não há validação de dígitos verificadores ou ramo |
| Leitura de `ETAPAS` da sentença | As duas saídas finais exigem `juiz federal` | Trocar apenas o redator faria o gate reprovar |

Não é necessário reescrever toda a numeração CNJ: falta centralizar validação de ramo, região, dígitos e consistência com o caso. O CNJ identifica a Justiça do Trabalho pelo segmento 5. [Referência oficial](https://www.cnj.jus.br/programas-e-acoes/numeracao-unica/perguntas-frequentes/).

## Domínio trabalhista que precisa entrar

A análise deve passar a organizar **pedidos, defesas, fatos controvertidos, ônus probatório, documentos e conclusão por pedido**. A entrada precisa representar vínculo, períodos contratuais, remuneração, jornada, verbas rescisórias, recolhimentos e normas coletivas quando pertinentes. Ausência de documento deve gerar pendência explícita, sem preencher fatos por suposição.

Na base normativa, revisar especialmente subsidiariedade (art. 769), honorários (791-A), prova (818) e conteúdo da decisão (832). O rito também altera a saída: o art. 852-I dispensa relatório na sentença sumaríssima. Não basta substituir a assinatura. As regras precisam considerar vigência, decisões de controle constitucional e precedentes aplicáveis ao caso. [CLT atualizada na Câmara dos Deputados](https://www2.camara.leg.br/legin/fed/declei/1940-1949/decreto-lei-5452-1-maio-1943-415500-normaatualizada-pe.html).

O primeiro conjunto de casos proposto abrange reclamações individuais contra empregadores privados, nos ritos ordinário e sumaríssimo, sobre vínculo, jornada, parcelas salariais e rescisórias. Casos com administração pública, execução, dissídios coletivos, perícia decisiva não disponibilizada, incidentes especiais ou prova audiovisual sem transcrição devem ser sinalizados para tratamento especializado, sem minuta conclusiva automática.

Esse recorte é uma proposta técnica para limitar o piloto; o usuário confirmou apenas 1º grau e PDFs locais. A identificação do TRT virá do caso, com confirmação do operador, sem presumir uma região específica.

## Pesquisa e fontes

O perfil precisa distinguir legislação, decisões do STF, precedentes qualificados do TST, súmulas/OJs, decisões do TRT competente e julgados persuasivos. Tipo, alcance, situação, datas, pertinência e eventual superação devem ser registrados; a origem em um tribunal superior não basta para resolver conflitos entre fontes.

Para a primeira entrega, usar documentos oficiais fornecidos localmente, com URL de origem, referência, data de obtenção, trechos e confirmação de conferência. Esse modo evita tornar o novo MCP um bloqueador do piloto. Ele não equivale a pesquisa exaustiva ou atualização automática: falta de cobertura deve interromper a etapa jurídica afetada.

O [portal de jurisprudência do TST](https://jurisprudencia.tst.jus.br/) e a [página de precedentes qualificados](https://www.tst.jus.br/indice-tematico-precedentes-qualificados-tst) são alvos de uma investigação posterior. Nesta consulta, o primeiro exigiu JavaScript e o segundo apresentou verificação de acesso. Não há contrato de API validado para implementar diretamente.

## Cálculos

No piloto, entregar um quadro de parâmetros, bases, períodos, reflexos e pendências para conferência. Não produzir valores finais a partir de um prompt nem aplicar automaticamente tabelas federais.

O PJe-Calc é uma ferramenta específica de cálculo trabalhista e utiliza tabelas auxiliares atualizadas. A integração posterior deve começar pela leitura/conferência de relatórios e comparação de resultados, antes de prometer geração ou importação automática de arquivos `.pjc`. [Documentação institucional do PJe-Calc](https://www.trt24.jus.br/pje-calc).

## Reaproveitamento recomendado

- Manter os geradores de agentes, a separação por capacidades e os artefatos em disco.
- Reutilizar o motor de etapas após acrescentar verificação de dependências e versões.
- Reutilizar as lentes de análise probatória com revisão do enquadramento trabalhista.
- Manter o conversor como base técnica, preservando o original e corrigindo a limpeza para o novo perfil.
- Preservar os componentes federais como legado explícito; não copiá-los automaticamente para o perfil trabalhista.

O detalhamento de arquivos novos, tarefas, dependências e aceite está no [plano de implementação](../plan/feature-justica-trabalho-1.md).
