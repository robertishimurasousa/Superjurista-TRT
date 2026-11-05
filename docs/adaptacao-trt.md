# Adaptação para TRT

[Voltar ao índice](README.md)

O nome SuperJurista TRT identifica o propósito deste derivado. Os arquivos presentes ainda incluem fluxos e integrações da base SuperJurista voltados à Justiça Federal. A documentação não estabelece homologação em um TRT específico.

O escopo inicial escolhido é um **piloto de 1º grau com PDFs locais**. Consulte o [diagnóstico detalhado](diagnostico-justica-trabalho.md) e o [plano de implementação](../plan/feature-justica-trabalho-1.md), elaborados em 05/11/2026. As [fases 1](fase-1-perfis.md), [2](fase-2-ingestao.md) e [3](fase-3-analise.md) implementam instalação, ingestão, rastreabilidade e análise provisória por pedido. A [fase 4](fase-4-fontes.md) acrescenta fontes oficiais locais e referências rastreáveis. A [fase 5](fase-5-minuta.md) entrega redação, revisão e retomada. A homologação jurídica e a validação do piloto permanecem pendentes.

## Evidências na base atual

| Área | Estado observado | Consequência para a adaptação |
| --- | --- | --- |
| Captura PJe | Referências a `pje1g.trf5.jus.br` na skill de sessão | Validar autenticação, domínios e cookies do PJe de destino |
| Downloads | Scripts e referências orientados a tarefas e API PJe herdadas | Conferir endpoints, identificadores, paginação e documentos |
| Sentença | O verificador exige a expressão normalizada `juiz federal` em determinados artefatos | Alterar agentes e contratos em conjunto antes de aceitar minutas trabalhistas |
| Pesquisa | Componentes para BNP, CJF, TCU, TJSC e TNU, além de dependências JULIA/STJ | Definir as fontes pertinentes e implementar ou configurar as integrações necessárias |
| TST/TRTs | Nenhum servidor dedicado distribuído em `scaffold/mcp-servers/` | A cobertura desejada precisa ser demonstrada por integração e consultas reais |
| Listas de julgamento | `/analisar-lista` e agentes `lista-trf` orientados ao TRF5 | Rever formato de entrada, etapas e componentes legados |
| Revisão | Agentes de cálculos, honorários e remessa com referências herdadas | Revisar os critérios e materiais com os responsáveis pelo domínio |

## Sequência de adaptação

1. Definir o tribunal, a instância, o perfil de acesso e os tipos de demanda atendidos.
2. Preparar exemplos sintéticos ou anonimizados que representem documentos e resultados esperados.
3. Mapear as diferenças de autenticação e API do PJe sem distribuir sessões ou credenciais.
4. Revisar prompts, modelos, assinaturas e contratos de saída em conjunto.
5. Definir fontes de pesquisa e verificar as ferramentas exigidas pelos agentes.
6. Executar os verificadores locais e o fluxo completo no ambiente de teste.
7. Registrar a revisão dos resultados por responsáveis pelo domínio e as limitações encontradas.

Essa sequência é um roteiro de trabalho; não indica que as etapas já foram concluídas. As mudanças devem respeitar a origem do `scaffold` e o processo descrito em [desenvolvimento](desenvolvimento.md).

## Registro de validação

Para cada validação, registre a revisão do repositório, ambiente, componente, entrada anonimizada, resultado esperado, resultado observado e responsável pela revisão. Separe os estados:

- **Verificação local:** sintaxe e contratos dos arquivos.
- **Integração:** acesso efetivo ao serviço externo e resposta utilizável.
- **Fluxo completo:** execução de todas as etapas com os componentes configurados.
- **Aceite de domínio:** revisão do conteúdo e adequação ao uso pretendido.

Uma verificação local bem-sucedida não comprova os demais estados.
