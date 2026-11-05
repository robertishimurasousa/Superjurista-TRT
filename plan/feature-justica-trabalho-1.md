---
goal: 'Implementar um piloto de análise e minuta trabalhista de primeiro grau com PDFs locais'
version: '1.0'
date_created: '2026-11-05'
last_updated: '2026-11-05'
owner: 'Mantenedores do SuperJurista TRT'
status: 'Em andamento'
tags: ['justica-do-trabalho', 'primeiro-grau', 'pdf-local', 'adaptacao']
---

# Introdução

![Estado: Em andamento](https://img.shields.io/badge/estado-em_andamento-yellow)

Plano baseado na revisão `22da97af489116eee6518b9c7eb44b3e026f555e` e no [diagnóstico técnico](../docs/diagnostico-justica-trabalho.md). O usuário escolheu **piloto de 1º grau com PDFs locais**. As fases 1 a 4 estão implementadas tecnicamente. A suíte passou localmente; execução dos agentes no Claude Code, conferência jurídica das fontes de cada caso, minuta e homologação do piloto permanecem pendentes. Veja as [evidências da fase 1](../docs/fase-1-perfis.md) e as evidências e limitações das [fases 2](../docs/fase-2-ingestao.md), [3](../docs/fase-3-analise.md) e [4](../docs/fase-4-fontes.md).

Resultado pretendido: um perfil instalável `jt-1g-local`, capaz de receber documentos de um caso, preservar suas referências, estruturar pedidos e provas, consultar um conjunto local de fontes oficiais conferidas, produzir uma minuta e apresentar pendências para revisão humana. O sistema não assina, protocola ou publica decisões.

A implementação será incremental. Fases 1–6 compõem o piloto; fase 7 é evolução posterior e não bloqueia a entrega local. Não é necessário criar aplicação web ou banco de dados para este escopo.

## 1. Requisitos e restrições

- **REQ-001**: Instalar o perfil `jt-1g-local` sem exigir PJe, JULIA, CJF, STJ, TNU ou novo MCP do TST. Preservar o legado federal como opção explícita e manter `superjurista-dev` como identificador técnico do plugin.
- **REQ-002**: Aceitar PDF único ou pasta de PDFs; exigir identificação confirmada do caso, tribunal, instância, rito, fase e data de referência. Não inferir rito exclusivamente pelo valor da causa nem jurisdição apenas pelo nome do arquivo.
- **REQ-003**: Preservar PDF original, hash SHA-256, texto por página, índice de documentos e histórico de extração. Cada afirmação sobre os autos deve indicar documento/página ou ser marcada como inferência ou pendência.
- **REQ-004**: Manter matriz de pedidos com defesa, fatos, prova, ônus, normas, conclusão e correspondência no dispositivo. Cobrir todos os pedidos identificados e separar questões processuais e matérias examináveis de ofício.
- **REQ-005**: Distinguir artefatos analíticos internos de minuta final; gerar a estrutura apropriada ao rito, sem exigir assinatura federal ou copiar regras federais de honorários/cálculos.
- **REQ-006**: Registrar fontes jurídicas separadas das provas. Exigir identificador, tipo, tribunal/órgão, referência, URL oficial, conteúdo local, hash, data de consulta, situação, contexto temporal e responsável pela conferência. Não interpretar indisponibilidade como ausência de precedentes.
- **REQ-007**: Retomar etapas somente quando perfil, entradas, prompts, fontes e dependências mantiverem as versões registradas. Mudanças devem invalidar os descendentes afetados.
- **REQ-008**: Exibir separadamente validade técnica, pendências jurídicas e aceite humano. Um código de saída 0 nunca significa homologação do mérito.
- **SEC-001**: Manter documentos processuais e segredos fora do Git; testes devem usar dados sintéticos. Registrar autorização de tratamento antes de execução com autos reais e respeitar o provedor configurado no Claude Code.
- **SEC-002**: Tratar textos dos autos e fontes como dados não confiáveis: instruções inseridas nesses documentos não podem alterar ferramentas, perfil ou critérios de validação do fluxo.
- **CON-001**: Primeiro recorte proposto: reclamações individuais contra empregadores privados, fase de conhecimento, ritos ordinário e sumaríssimo; matérias de vínculo, jornada, parcelas salariais e rescisórias. O usuário ainda não confirmou esse detalhamento material; validá-lo com o responsável de domínio antes da homologação.
- **CON-002**: Não incluir no piloto integração PJe, protocolo, assinatura, recursos de 2º grau, execução, cálculos finais automáticos ou transcrição automática de audiovisual. Casos fora do recorte devem terminar com pendência explicada, preservando os relatórios já produzidos.
- **CON-003**: Não há TRT específico escolhido. Extrair a região do CNJ, confrontar com os autos e solicitar confirmação quando houver conflito. Regras regionais dependem de fontes da região identificada.
- **CON-004**: Leis, precedentes e parâmetros temporais exigem conferência de domínio antes de publicação do perfil. O plano não fixa percentuais, índices de atualização ou entendimentos jurídicos por memória do modelo.
- **PAT-001**: Implementar um fluxo trabalhista próprio, reaproveitando utilitários comuns. Evitar substituições globais de `federal` por `trabalhista` e renomeações de provedores sem adequar seus contratos.

### Contratos propostos

Os nomes a seguir são contratos de implementação. O perfil de distribuição existe desde a fase 1. Caso, documentos, textos e classificação estão implementados na fase 2. Relatório, triagem, matriz provisória e contrato preliminar de regras estão implementados na fase 3; fontes locais e referências estão implementadas na fase 4; minuta permanece planejada.

| Artefato no projeto instalado | Conteúdo mínimo |
| --- | --- |
| `.claude/perfis/jt-1g-local.json` | `id`, `versao`, `segmento=5`, `instancia=1`, `entrada=pdf-local`, comandos/agentes permitidos e `fontes=locais-conferidas` |
| `data/casos/<cnj>/caso.json` | `schema_version`, `numero_cnj`, `trt`, `unidade`, `rito`, `fase`, `data_referencia`, `escopo_confirmado`, `documentos`, `pendencias` |
| `data/casos/<cnj>/documentos.json` | Documento estável, caminho relativo, SHA-256, ordem, tipo, páginas, ID PJe quando fornecido e estado da extração |
| `data/casos/<cnj>/texto/` | Texto bruto e normalizado por documento/página; mapa para o original |
| `data/casos/<cnj>/pedidos.json` | Partes, contratos, pedidos, defesas, atos de audiência, referências, cobertura e conferência do inventário |
| `data/casos/<cnj>/triagem.json` | Escopo, provas/fontes necessárias, impedimentos e estado por pedido |
| `data/casos/<cnj>/regras-juridicas.json` | Registro preliminar de regras, conteúdo local e conferência humana; integração ampliada na fase 4 |
| `data/casos/<cnj>/matriz-pedidos.json` | IDs estáveis, pedidos principais/acessórios, defesa, fatos, provas, ônus, parâmetros, conclusão e justificativa |
| `data/casos/<cnj>/fontes-juridicas.json` | Fontes tipadas `legislacao`, `precedente` ou `norma-coletiva`; conteúdo conferido, metadados e âmbito de aplicação |
| `data/casos/<cnj>/referencias-minuta.json` | ID da afirmação, seção/trecho da minuta, IDs de provas/fontes, tipo de uso e revisão de pertinência |
| `data/casos/<cnj>/execucao.json` | Perfil, versões, hashes de insumos, dependências das etapas, estados e duração |
| `data/casos/<cnj>/minuta.md` | Documento destinado à revisão; identificação de minuta e nenhuma assinatura digital |
| `data/casos/<cnj>/revisao.json` | Conferências técnicas e jurídicas, pendências, responsável e estado de aceite humano |

Estados das etapas: `pendente`, `executando`, `valida`, `invalida`, `bloqueada`, `desatualizada`. Código 0: contrato técnico atendido; 1: artefato ausente/inválido/desatualizado ou pendência impeditiva; 2: configuração/entrada inválida; 3: tarefa adicional exigida pela triagem. O comando de inventário pode listar estados sem aprovar o fluxo; a aprovação técnica sempre usa `--gate`.

## 2. Etapas de implementação

### Fase 1 — Base mantida pelo derivado e instalação por perfil

- **GOAL-001**: Instalar um ambiente trabalhista isolado das dependências federais. Dependências: nenhuma fase anterior. Saída: projeto temporário instalado pelo perfil e inventário dos componentes conferido.

| Tarefa | Descrição e critério de conclusão | Concluída | Data |
| --- | --- | --- | --- |
| TASK-001 | Em `docs/desenvolvimento.md`, registrar `scaffold/` versionado como fonte do derivado. Alterar `sync-scaffold.ps1` para importar fontes explicitamente configuradas para área temporária e gerar comparação; remover a exclusão direta de áreas de trabalho. Sem parâmetros de origem válidos, sair antes de qualquer mutação. Testar com diretórios temporários. | Sim | 2026-11-05 |
| TASK-002 | Criar `scaffold/perfis/jt-1g-local.json` e `spec/schemas/perfil.schema.json`, com lista explícita de componentes. Implementar `scaffold/scripts/perfil.py:carregar_perfil()` e `validar_perfil()`. Rejeitar versão desconhecida, caminho fora do pacote e referência a arquivo inexistente. Depende de TASK-001. | Sim | 2026-11-05 |
| TASK-003 | Criar `scripts/instalar_perfil.py` com `--perfil`, `--destino` e `--dry-run`; atualizar `commands/instalar-superjurista.md` para invocá-lo. Copiar apenas componentes do manifesto; no perfil local não registrar MCPs nem copiar comandos federais/PJe. Conflitos existentes devem ser apresentados antes de sobrescrever. Depende de TASK-002 e se completa com os componentes das fases seguintes. | Base e expansão TASK-026 entregues | 2026-11-05 |
| TASK-004 | Atualizar `.gitignore` e `scaffold/project-gitignore` para excluir casos, sessões, HAR, `.env` e ambientes virtuais. Manter `tests/fixtures/` para conteúdo sintético; testar `git check-ignore` com Markdown de caso e arquivos de autenticação. | Sim | 2026-11-05 |
| TASK-005 | Criar `requirements-dev.txt` e `scaffold/requirements-jt.txt` com dependências efetivamente usadas, Python mínimo e versões testadas. Criar `tests/test_instalacao_jt.py` para manifesto, cópia, preservação de arquivos e instalação sem servidores federais. Executar em destino temporário; nenhuma chamada a tribunal. Depende de TASK-003 e TASK-004. | Sim | 2026-11-05 |

### Fase 2 — Entrada de PDFs e rastreabilidade

- **GOAL-002**: Transformar PDFs locais em um caso com referências recuperáveis. Dependência: contratos de TASK-002; instalação completa pode ser concluída em paralelo ao desenvolvimento das etapas. Saída: corpus sintético convertido sem perda silenciosa conhecida.

| Tarefa | Descrição e critério de conclusão | Concluída | Data |
| --- | --- | --- | --- |
| TASK-006 | Criar `scaffold/scripts/cnj.py:validar_cnj()` e schemas `spec/schemas/caso.schema.json` e `documentos.schema.json`. Validar módulo 97, segmento 5, região coerente e metadados confirmados; rejeitar segmento federal no perfil. Aceitar organização em pasta sem extrair a identidade apenas do nome. | Sim | 2026-11-05 |
| TASK-007 | Criar `scaffold/scripts/ingerir_documentos.py` com `--input`, `--workspace` e `--caso`. Aceitar arquivo ou pasta, preservar cópia original, gerar IDs/hashes e detectar duplicatas, PDF corrompido/protegido e entrada vazia. Registrar falhas sem substituir documentos já ingeridos. Depende de TASK-006. | Sim | 2026-11-05 |
| TASK-008 | Adaptar `scaffold/skills/converter-pdf/scripts/pdf_para_txt.py` com modo explícito de preservação para JT. Conservar texto bruto e página original; não remover linhas repetidas de tabelas/contracheques. OCR por página quando necessário; detectar mistura de páginas digitais e escaneadas e registrar páginas ilegíveis. Depende de TASK-007. | Sim | 2026-11-05 |
| TASK-009 | Criar `scaffold/agents/trabalhista/extrator-caso.md` e `scaffold/scripts/verificar_documentos.py`. Classificar petição, defesa, réplica, atas, controles de jornada, contracheques, TRCT, FGTS, laudos e instrumentos coletivos; marcar desconhecidos. O gate confere que todas as páginas são contabilizadas e que referências apontam para IDs existentes. Depende de TASK-008. | Sim | 2026-11-05 |
| TASK-010 | Criar `tests/test_ingestao_jt.py` e fixtures com PDF digital, escaneado, misto, repetição de linhas, duplicatas e documento ausente. Exigir preservação de linhas esperadas e rastreio de página; não exigir igualdade literal do OCR em ambientes diferentes. Depende de TASK-009. | Sim | 2026-11-05 |

### Fase 3 — Modelo do caso e análise trabalhista

- **GOAL-003**: Produzir análise por pedido, com fatos e lacunas identificados. Dependência: fase 2. Saída: matriz revisável e triagem que bloqueia os casos fora do escopo.

| Tarefa | Descrição e critério de conclusão | Concluída | Data |
| --- | --- | --- | --- |
| TASK-011 | Criar `spec/schemas/pedidos.schema.json` e `scaffold/agents/trabalhista/relator.md`. Extrair partes, contratos/períodos, pedidos e acessórios, defesas, documentos e atos de audiência. Cada dado deve ter referência ou estado `nao-informado`; proibir completar datas/valores ausentes. | Sim | 2026-11-05 |
| TASK-012 | Criar `scaffold/agents/trabalhista/triador.md`. Verificar rito/fase/escopo, classificar questões por prova e fonte necessária, e registrar `bloqueada` para competência/rito incertos, prova decisiva indisponível ou matérias fora do recorte. Não exigir BNP/JULIA e não tratar silêncio dos autos como fato incontroverso. Depende de TASK-011. | Sim | 2026-11-05 |
| TASK-013 | Criar `scaffold/agents/trabalhista/analista.md` e `scaffold/skills/analise-trabalhista/SKILL.md`, com referências de vínculo, jornada e verbas. Produzir matriz de pedidos com alegações contrapostas, ônus, provas, normas coletivas aplicáveis por período/categoria/território e conclusão motivada. Rever as lentes probatórias reutilizadas; não converter probabilidades heurísticas em fatos provados. Depende de TASK-012. | Sim | 2026-11-05 |
| TASK-014 | Criar `scaffold/skills/analise-trabalhista/references/matriz-normativa.md` e `spec/schemas/regra-juridica.schema.json`. Registrar tema, texto/precedente oficial, vigência, situação, data de conferência e responsável. Cobrir processo, honorários, custas, gratuidade e parâmetros de atualização sem fallback federal. Regras ainda não conferidas bloqueiam a conclusão que delas dependa. Depende de TASK-013 e das fontes da fase 4. | Contrato, roteiro e integração entregues; conferência jurídica de domínio pendente | 2026-11-05 |
| TASK-015 | Criar `scaffold/scripts/verificar_pedidos.py` e `tests/test_pedidos_jt.py`. Conferir unicidade, pedidos omitidos/duplicados, referência inexistente, inconsistência entre partes/períodos e dados obrigatórios por questão. Testar também reclamação com múltiplos empregadores e instrumento coletivo ausente. Depende de TASK-011 e TASK-013. | Sim | 2026-11-05 |

### Fase 4 — Fontes oficiais locais e citações rastreáveis

- **GOAL-004**: Sustentar a análise com fontes verificadas sem novo MCP obrigatório. Dependência: identificação/documentos da fase 2; pode avançar em paralelo à fase 3. Saída: registro tipado, conferência de referências e bloqueio por fonte insuficiente.

| Tarefa | Descrição e critério de conclusão | Concluída | Data |
| --- | --- | --- | --- |
| TASK-016 | Criar `spec/schemas/fontes-juridicas.schema.json` e `scaffold/scripts/importar_fontes_jt.py`. Importar PDF/HTML/TXT oficial local com metadados, hash e conferência humana. Diferenciar fonte de prova dos autos, legislação, norma coletiva e jurisprudência. Documento com URL declarada mas sem conferência não se torna automaticamente fonte oficial validada. | Sim | 2026-11-05 |
| TASK-017 | Criar `scaffold/agents/trabalhista/pesquisador-fontes.md`. Organizar STF, TST e TRT competente por tipo, âmbito, situação e pertinência; distinguir tese firmada de tema afetado/suspenso, bem como súmula/OJ de julgamento qualificado. Registrar necessidade de consulta externa sem inventar resultado. Depende de TASK-016. | Sim | 2026-11-05 |
| TASK-018 | Criar `scaffold/scripts/merge_fontes_jt.py`, reutilizando normalização/deduplicação de `merge_fontes.py`. Manter schema versionado próprio, IDs estáveis e metadados de conferência; preservar o contrato legado. Gravar de forma atômica e rejeitar registros incompletos sem publicar consolidado aprovado. Depende de TASK-016. | Sim | 2026-11-05 |
| TASK-019 | Criar `scaffold/scripts/verificar_referencias_jt.py` e schema `referencias-minuta.schema.json`. Validar referências explícitas a fontes e provas, correspondência de citações diretas e existência dos vínculos usados na matriz/minuta. Exigir revisão de pertinência para paráfrases; detectar referências textuais sem registro e encaminhar casos ambíguos à revisão. Proibir uso de uma citação da petição como jurisprudência oficialmente conferida. Depende de TASK-017 e TASK-018. | Sim | 2026-11-05 |
| TASK-020 | Criar `tests/test_fontes_jt.py`. Cobrir origem TST/TRT válida, fonte não conferida, fonte com status vencido/desconhecido, alteração do conteúdo/hash, legislação citada, citação sem aspas, citação curta, corpus vazio e jurisprudência apenas reproduzida nos autos. Falta de cobertura deve impedir conclusão da questão jurídica, não inventar fonte substituta. Depende de TASK-019. | Sim | 2026-11-05 |

### Fase 5 — Minuta, revisão e retomada

- **GOAL-005**: Entregar um único fluxo trabalhista com saída adequada ao rito e revisão explícita. Dependências: fases 3 e 4. Saída: minuta rastreável ou bloqueio explicado; retomada sem reutilizar resultado obsoleto.

| Tarefa | Descrição e critério de conclusão | Concluída | Data |
| --- | --- | --- | --- |
| TASK-021 | Criar `scaffold/agents/trabalhista/fundamentador.md` e modelos em `scaffold/templates/jt/`. Gerar proposta por pedido e dispositivo correspondente, tratar questões processuais separadamente, preservar parâmetros e pendências. Produzir minuta ordinária ou sumaríssima conforme perfil do caso; manter relatório analítico interno sem inseri-lo obrigatoriamente no sumaríssimo. Depende de TASK-014, TASK-015 e TASK-019. | Implementado; validação de domínio pendente na fase 6 | 2026-11-05 |
| TASK-022 | Criar `scaffold/agents/trabalhista/revisor.md`, com revisões explícitas de pedidos/provas, fontes, honorários/custas/gratuidade e parâmetros de cálculo. Retornar `nao-aplicavel` com motivo quando pertinente; dados/regra insuficientes retornam pendência. No piloto, nenhuma liquidação automática ou fallback de índices federais. Depende de TASK-021. | Implementado; validação de domínio pendente na fase 6 | 2026-11-05 |
| TASK-023 | Criar `scaffold/scripts/verificar_sentenca_jt.py` e `merge_sentenca_jt.py`. Reutilizar funções genéricas do motor, mas validar estrutura própria, referências, questões/pedidos, rito, identificação e pendências. Validar antes de renomear arquivo temporário para `minuta.md`; impedir estado aprovado se revisão/referências falharem. Depende de TASK-022. | Implementado; validação de domínio pendente na fase 6 | 2026-11-05 |
| TASK-024 | Criar `scaffold/scripts/estado_execucao.py` com `calcular_assinatura_etapa()` e `invalidar_descendentes()`. Usar SHA-256 de insumos, perfil, prompts, versão dos scripts e fontes; escrever estado atomicamente e impedir duas execuções simultâneas no mesmo caso. Bloqueio residual exige diagnóstico explícito, sem apagar artefatos silenciosamente. Depende dos contratos das fases 2–4. | Implementado; validação de domínio pendente na fase 6 | 2026-11-05 |
| TASK-025 | Criar `scaffold/commands/pipeline-sentenca-trabalhista.md` com argumento de arquivo/pasta e `--caso`. Encadear ingestão, extração, matriz, triagem, fontes, análise, redação, revisão e gate; usar o inventário de pendências e limites de tentativas. Incluir somente agentes do perfil e impedir que documentos de entrada alterem suas instruções. Depende de TASK-023 e TASK-024. | Implementado; validação de domínio pendente na fase 6 | 2026-11-05 |
| TASK-026 | Atualizar `scaffold/perfis/jt-1g-local.json`, instalador e instruções de projeto para expor o novo comando. Comandos federais alternativos não devem aparecer numa instalação limpa desse perfil. Em instalação já existente, registrar conflitos e preservar arquivos sem alegar isolamento garantido. Depende de TASK-025 e TASK-003. | Implementado; validação de domínio pendente na fase 6 | 2026-11-05 |

Entrega da fase 5: [guia operacional](../docs/fase-5-minuta.md). O aceite humano final permanece não registrado; `revisao.json` registra a proposta técnica do agente, e as conferências humanas das referências continuam no contrato da fase 4. O estado acrescenta `interrompida` para diagnóstico de tentativa consumida. A retomada usa dependências sequenciais conservadoras, incluindo hashes do pacote completo. Código 3 permanece reservado para extensão futura; nesta fase, demandas adicionais são pendências bloqueantes com código 1. Integração dos PRs empilhados e execução com Claude Code não se confundem com entrega local.

### Fase 6 — Validação do piloto e documentação operacional

- **GOAL-006**: Demonstrar funcionamento técnico e obter aceite de domínio separado. Dependência: fases 1–5. Saída: relatório de evidências, limitações conhecidas e decisão explícita de aceite.

| Tarefa | Descrição e critério de conclusão | Concluída | Data |
| --- | --- | --- | --- |
| TASK-027 | Criar `tests/fixtures/jt/manifesto.json` com 12 casos sintéticos: ordinário simples, sumaríssimo, vínculo controvertido, jornada com tabela repetida, verbas rescisórias, múltiplos réus, norma coletiva ausente, prova oral sem transcrição, documento decisivo ausente, PDF misto, fonte não conferida e caso fora do escopo. Definir saída esperada, pendências e critérios de revisão de cada caso. | Implementado; corpus sintético técnico | 2026-11-05 |
| TASK-028 | Criar testes de retomada e integração dos scripts em `tests/test_pipeline_jt.py`: alteração do PDF, do prompt, da fonte e do perfil invalida descendentes; execução interrompida retoma corretamente; falha de escrita não publica resultado parcial; dois processos não misturam dados. Executar sem serviços externos. Depende de TASK-024 e TASK-027. | Implementado; integração dos scripts | 2026-11-05 |
| TASK-029 | Criar `.github/workflows/validacao.yml` para schemas, sintaxe, testes determinísticos, instalação temporária e links da documentação. Proibir dados reais e credenciais nos testes. Registrar versões testadas de Python/dependências e validar em Linux; executar instalação e conversão também no macOS utilizado pelo mantenedor. Depende de TASK-005, TASK-010, TASK-015, TASK-020 e TASK-028. | Implementado; evidências de ambiente no relatório | 2026-11-05 |
| TASK-030 | Em ambiente com Claude Code, executar os 12 casos da fixture três vezes cada. Gravar em `docs/validacao/piloto-jt-local.md` hashes, versões de prompts/modelo, duração, falhas, variação e resultado por caso, sem conteúdo sensível. Todos os bloqueios esperados devem ocorrer; divergência material entre repetições exige análise e correção. Depende de TASK-026 e TASK-029. | Pendente: Claude Code indisponível; 0/36; coleta preparada | 2026-11-05 |
| TASK-031 | Submeter as minutas e bloqueios do corpus a profissional responsável pelo domínio; preencher uma ficha por caso com fatos, pedidos, fontes, rito, encargos e dispositivo. Exigir zero defeito crítico aberto: fato inventado decisivo, pedido omitido, fonte falsa, regra federal aplicada indevidamente ou saída conclusiva fora do escopo. O registro de aceite identifica responsável/data e não é preenchido pelo modelo em seu nome. Depende de TASK-030 e da confirmação de CON-001. | Pendente: usuário se indicou como responsável; 0/12 aceites | 2026-11-05 |
| TASK-032 | Atualizar `README.md`, `docs/instalacao.md`, `docs/uso.md`, `docs/adaptacao-trt.md`, `scaffold/project-readme.md`, `scaffold/project-claude.md` e `CHANGELOG.md`. Documentar perfil, dependências, fontes locais, tratamento de bloqueios, limites e resultados reais da validação; só declarar piloto aceito após TASK-031. Depende de TASK-031. | Documentação operacional entregue; aceite final pendente de TASK-031 | 2026-11-05 |

Evidências e limitações da fase 6: [relatório](../docs/validacao/piloto-jt-local.md) e [operação](../docs/validacao/operacao-piloto-jt.md). O usuário indicou que fará a revisão jurídica; isso não preenche CON-001 ou o aceite em seu nome. A fase permanece aberta para TASK-030/TASK-031 e fechamento documental após aceite.

### Fase 7 — Evoluções posteriores ao piloto

- **GOAL-007**: Reduzir trabalho manual sem alterar os critérios de rastreabilidade. Dependência: piloto aceito e definição de escopo para cada integração. Estas tarefas não integram o aceite inicial.

| Tarefa | Descrição e critério de conclusão | Concluída | Data |
| --- | --- | --- | --- |
| TASK-033 | Produzir `docs/investigacoes/fontes-tst-trt.md`: testar acesso autorizado aos portais oficiais, obter exemplos sanitizados e documentar busca, paginação, inteiro teor, status e limites. Somente após confirmar o contrato, implementar adaptadores em `scaffold/mcp-servers/jt-jurisprudencia/` para as fontes demonstradas; indisponibilidade preserva o modo local. | Não | — |
| TASK-034 | Produzir `docs/investigacoes/pje-trt.md` após escolher TRT, grau e perfil de acesso. Parametrizar clientes de `scaffold/skills/pje-download/scripts/` e captura de sessão; testar listagem/download e segregação de credenciais sem presumir os endpoints TRF5. Manter entrada local funcional. | Não | — |
| TASK-035 | Produzir `docs/investigacoes/pje-calc.md` e um comparador de relatórios exportados, após definir versão e formato. Validar bases, períodos, índices e resultados com calculista responsável; geração automática de `.pjc` só pode ser planejada após contrato de formato e importação comprovados. | Não | — |
| TASK-036 | Abrir planos próprios para embargos, execução, 2º grau, temas especiais e áudio/vídeo. Cada plano deve definir entradas, contratos, fontes, corpus e responsável pelo aceite; não ampliar automaticamente o comando de sentença do piloto. | Não | — |

### Ordem de entrega

| Entrega sugerida | Tarefas | Resultado revisável |
| --- | --- | --- |
| PR 1 | TASK-001 a TASK-005 | Base de distribuição e contratos de perfil; manifesto inicialmente validado contra os componentes já criados |
| PR 2 | TASK-006 a TASK-010 | Ingestão e extração rastreáveis |
| PR 3 | TASK-011 a TASK-015 | Modelo trabalhista e análise; regras ainda sem conferência permanecem bloqueadas |
| PR 4 | TASK-016 a TASK-020 | Fontes locais e conferência de referências; libera dependência de TASK-014 |
| PR 5 | TASK-021 a TASK-026 | Fluxo de minuta e retomada integrados |
| PR 6 | TASK-027 a TASK-032 | Evidências, revisão de domínio e documentação de operação |
| Depois do piloto | TASK-033 a TASK-036 | Integrações e ampliação de escopo |

Tarefas com dependências de outro PR só são consideradas concluídas após sua integração. A divisão pode ser ajustada para manter cada PR verificável; não publicar um manifesto que referencie arquivos inexistentes. O corpus de TASK-027 deve ser iniciado na fase 2 e ampliado durante as demais fases.

## 3. Alternativas

- **ALT-001**: Substituir expressões federais por trabalhistas em todos os arquivos. Descartada porque mantém regras jurídicas e contratos incompatíveis.
- **ALT-002**: Reescrever todo o projeto. Descartada porque geração de componentes, execução por etapas e boa parte dos utilitários podem ser reaproveitados.
- **ALT-003**: Exigir integração PJe e MCP TST antes do piloto. Adiada conforme a escolha por PDFs locais e pela incerteza sobre acesso automatizado aos portais.
- **ALT-004**: Manter um único prompt genérico para todas as jurisdições. Descartada para o piloto; perfis explícitos tornam dependências e critérios verificáveis.
- **ALT-005**: Fazer cálculos finais pelo modelo de linguagem. Descartada; o piloto define parâmetros e uma futura integração será comparada com resultados de ferramenta especializada.

## 4. Dependências

- **DEP-001**: Claude Code instalado/autenticado e autorização de uso do provedor para os dados escolhidos. Necessário para TASK-030; não para testes determinísticos.
- **DEP-002**: Python compatível, bibliotecas de PDF, Tesseract `por` e Poppler, com versões registradas. Necessários para a conversão real do corpus.
- **DEP-003**: Profissional responsável pela revisão jurídica e confirmação do recorte material. Necessário para conferir regras e concluir TASK-031; não impede iniciar infraestrutura e ingestão.
- **DEP-004**: Fontes oficiais conferidas e documentos sintéticos de referência. A simples presença de URL ou texto não comprova validade/atualidade.
- **DEP-005**: TRT e acesso institucional específicos, apenas para TASK-034; formato/versão e responsável por cálculos, apenas para TASK-035.

## 5. Arquivos

- **FILE-001**: `sync-scaffold.ps1`, `commands/instalar-superjurista.md`, `scripts/instalar_perfil.py` e `scaffold/perfis/jt-1g-local.json`: origem da distribuição, seleção e instalação.
- **FILE-002**: `spec/schemas/*.schema.json`: contratos de perfil, caso, documentos, pedidos, regras, fontes e referências.
- **FILE-003**: `scaffold/scripts/perfil.py`, `cnj.py`, `ingerir_documentos.py` e `verificar_documentos.py`: identidade e entrada.
- **FILE-004**: `scaffold/skills/converter-pdf/scripts/pdf_para_txt.py`: conversão com preservação de referências.
- **FILE-005**: `scaffold/agents/trabalhista/*.md`, `scaffold/skills/analise-trabalhista/` e `scaffold/templates/jt/`: domínio, revisão e modelos.
- **FILE-006**: `scaffold/scripts/importar_fontes_jt.py`, `merge_fontes_jt.py` e `verificar_referencias_jt.py`: cadeia de fontes trabalhistas.
- **FILE-007**: `scaffold/scripts/verificar_pedidos.py`, `verificar_sentenca_jt.py`, `merge_sentenca_jt.py` e `estado_execucao.py`: gates e retomada.
- **FILE-008**: `scaffold/commands/pipeline-sentenca-trabalhista.md`: entrada única do piloto.
- **FILE-009**: `tests/`, `.github/workflows/validacao.yml`, `requirements-dev.txt` e `scaffold/requirements-jt.txt`: regressão e ambiente reproduzível.
- **FILE-010**: `.gitignore`, `scaffold/project-*`, `README.md`, `CHANGELOG.md` e `docs/`: operação, privacidade, limitações e evidências.

## 6. Testes e critérios de aceite

- **TEST-001**: Instalação limpa em pasta temporária produz somente componentes declarados e nenhum MCP federal obrigatório. Reinstalação não sobrescreve customização silenciosamente.
- **TEST-002**: CNJ válido do segmento 5 passa; dígito inválido, ramo incorreto e metadados conflitantes impedem o início conclusivo do caso.
- **TEST-003**: Os documentos e páginas das fixtures são contabilizados; duplicatas, páginas ilegíveis e faltas são sinalizadas. Linhas repetidas relevantes permanecem disponíveis.
- **TEST-004**: Todos os pedidos esperados nas fixtures aparecem uma vez na matriz e têm correspondência no dispositivo ou pendência impeditiva explícita. Essa métrica vale para o corpus de referência, sem alegação de garantia universal.
- **TEST-005**: Os casos ordinário e sumaríssimo produzem estruturas aprovadas pelo responsável de domínio; nenhuma saída do perfil exige ou usa assinatura de juiz federal.
- **TEST-006**: Fontes inexistentes/não conferidas, corpus vazio com referências, citação apenas nos autos e status jurídico desconhecido geram bloqueio pertinente. Verificar também paráfrases sem lastro e IDs órfãos.
- **TEST-007**: Sem dados necessários para encargos ou cálculo, a saída declara pendência; nenhuma regra de correção/honorários federais é aplicada por fallback.
- **TEST-008**: Mudança de entrada, fonte, prompt ou perfil invalida as etapas dependentes; retomar sem mudanças preserva resultados válidos e não mistura casos.
- **TEST-009**: Um PDF com instruções adversariais não altera ferramentas, contratos ou perfil. Arquivos de caso não são incluídos no Git e os registros de teste não contêm segredos.
- **TEST-010**: As 36 execuções do corpus (12 casos × 3 repetições) registram resultados completos; bloqueios esperados ocorrem em todas. Qualquer defeito crítico impede o aceite até correção e repetição dos casos afetados.
- **TEST-011**: Gate técnico, revisão jurídica e aceite humano aparecem em campos separados; o modelo não produz um aceite em nome de pessoa real.

## 7. Riscos e premissas

- **RISK-001**: A extração pode omitir tabelas, ordem de documentos ou prova oral. Mitigação: originais preservados, índice/páginas e bloqueio por documento essencial ausente.
- **RISK-002**: Uma fonte oficial pode estar superada, suspensa ou fora do âmbito do caso. Mitigação: situação, vigência, conferência e revisão de pertinência; não usar ordem fixa de tribunais como solução universal.
- **RISK-003**: Verificações estruturais não detectam todo erro de fundamentação. Mitigação: corpus revisado, testes negativos e aceite de domínio independente.
- **RISK-004**: Uma sincronização upstream pode apagar a adaptação. Mitigação: executar TASK-001 antes de editar as áreas geradas.
- **RISK-005**: Contextos longos podem truncar provas relevantes. Mitigação: extração por documento/pedido com índice completo, contagem de cobertura e registro dos trechos usados.
- **RISK-006**: O provedor de IA pode receber dados de autos locais. Mitigação: ambiente autorizado e corpus sintético durante desenvolvimento; PDF local não é sinônimo de inferência offline.
- **ASSUMPTION-001**: Entrada por PDFs locais está confirmada pelo usuário. O acesso a fontes oficiais pode começar por importação manual conferida.
- **ASSUMPTION-002**: A minuta é apoio ao responsável pelo julgamento; não há autorização nem escopo para proferir, assinar ou protocolar atos.
- **ASSUMPTION-003**: A implementação poderá introduzir arquivos novos no scaffold após definir sua manutenção no derivado. A política foi alterada na fase 1: o scaffold versionado passou a ser a fonte deste derivado, com importações upstream apenas para revisão.

## 8. Especificações relacionadas e fontes

- [Diagnóstico técnico e evidências](../docs/diagnostico-justica-trabalho.md).
- [Arquitetura atual](../docs/arquitetura.md) e [padrão soberano herdado](../skills/criar-sistema/references/padrao-soberano.md).
- [CLT atualizada — Câmara dos Deputados](https://www2.camara.leg.br/legin/fed/declei/1940-1949/decreto-lei-5452-1-maio-1943-415500-normaatualizada-pe.html): referência para revisão dos requisitos processuais; aplicação exige conferência de vigência e precedentes.
- [Numeração única — CNJ](https://www.cnj.jus.br/programas-e-acoes/numeracao-unica/perguntas-frequentes/): identificação dos segmentos e estrutura do número.
- [Pesquisa de jurisprudência — TST](https://jurisprudencia.tst.jus.br/): portal apresentou dependência de JavaScript nesta consulta.
- [Índice de precedentes qualificados — TST](https://www.tst.jus.br/indice-tematico-precedentes-qualificados-tst): página apresentou proteção de acesso; não tratada como API validada.
- [PJe-Calc — TRT24](https://www.trt24.jus.br/pje-calc): finalidade da ferramenta e tabelas auxiliares; a integração automatizada permanece futura.

Fontes consultadas em 05/11/2026. O acesso ao texto da CLT no Planalto foi bloqueado; utilizou-se a publicação atualizada da Câmara. Não houve validação autenticada de PJe, pesquisa automatizada TST/TRT, execução de Claude Code ou aceite jurídico. A validação técnica da fase 1 está registrada no guia correspondente.
