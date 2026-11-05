# Fase 4 — fontes oficiais locais e citações rastreáveis

[Voltar ao índice](README.md) · [Plano](../plan/feature-justica-trabalho-1.md) · [Análise](fase-3-analise.md)

A fase 4 importa arquivos oficiais locais, registra sua conferência e vincula regras/citações ao conteúdo preservado. Os scripts não fazem buscas, downloads, autenticação ou chamadas à IA. O pesquisador organiza o acervo local e registra consultas externas necessárias como pendências.

## Arquivos e contratos

| Artefato | Função |
| --- | --- |
| `.claude/perfis/fonte.exemplo.json` | Modelo de metadados a preencher antes da importação |
| `fontes/importadas/FON-<hash>/` | Original, texto extraído, páginas de PDF e registro `fonte.json` |
| `fontes-juridicas.json` | Corpus consolidado das revisões explicitamente selecionadas |
| `regras-juridicas.json` | Regras analíticas da fase 3, apontando para os textos das fontes |
| `pesquisa-fontes.md` | Organização por tema, situação, âmbito, pertinência e lacunas |
| `referencias-minuta.json` | Vínculos de regras e referências localizadas na matriz e eventual minuta |

Os contratos estão em [metadados](../spec/schemas/fonte-metadados.schema.json), [conferência](../spec/schemas/conferencia-fonte.schema.json), [corpus](../spec/schemas/fontes-juridicas.schema.json) e [referências](../spec/schemas/referencias-minuta.schema.json). Os requisitos continuam os da fase 2. O perfil inclui os novos componentes; instalações antigas com conflitos exigem revisão ou outra pasta, sem sobrescrita automática.

## 1. Importar arquivo oficial local

Com o caso já ingerido, copie o modelo para `data/fonte-metadados.json` e preencha os campos. Mantenha o arquivo oficial de entrada fora da pasta do caso, por exemplo em `data/fontes-entrada/`:

```bash
cp .claude/perfis/fonte.exemplo.json data/fonte-metadados.json
python scripts/importar_fontes_jt.py data/casos/CNJ-CONFIRMADO \
  --input data/fontes-entrada/documento-oficial.pdf \
  --metadados data/fonte-metadados.json
```

Metadados exigem tipo (`legislacao`, `precedente`, `norma-coletiva`), órgão, referência, URL oficial, data de consulta, situação, modalidade, temas, âmbito, vigência e contexto temporal. Os temas usados para vincular regras devem corresponder aos nomes do contrato da fase 3, como `jornada`, `onus` e `honorarios`.

Precedentes identificam `STF`, `TST` ou `TRT1` a `TRT24`. O domínio declarado deve corresponder ao órgão; TRT exige âmbito regional coerente. Norma coletiva exige âmbito coletivo, categoria e território. Documento de outro TRT gera pendência no piloto; eventual uso comparativo exige revisão do recorte, sem trocar artificialmente a região.

URLs exigem HTTPS e domínio `.gov.br`, `.jus.br` ou `.leg.br`, sem credenciais na autoridade. Isso valida o endereço declarado, não autentica o arquivo baixado. O exemplo começa com situação `incerta`, que não permite publicação no corpus conferido.

PDF usa extração preservadora por página e OCR quando necessário. HTML/TXT devem estar em UTF-8; HTML é convertido em texto sem executar scripts nem carregar recursos externos. Imagens e conteúdo dinâmico do HTML não são interpretados como texto. Confira o resultado contra o original, inclusive tabelas e anexos. Originais são preservados mesmo quando o PDF está protegido ou a extração fica incompleta.

A importação retorna um ID `FON-...` e pendência de conferência: **código 1 após importar não significa que o arquivo foi perdido**. O registro fica em `fontes/importadas/ID/fonte.json`, com os caminhos e hashes. Arquivo com o mesmo hash de um original dos autos é recusado como fonte independente; a origem declarada e a conferência humana continuam necessárias para identificar outros casos de reprodução indevida.

## 2. Registrar a conferência humana

Compare original, texto extraído, órgão/URL, referência, situação e contexto temporal. Prepare `data/conferencia-fonte.json` com estes campos, usando os hashes reais presentes em `fonte.json`:

```text
responsavel                 nome do responsável pela conferência
data                       data da conferência, AAAA-MM-DD
valida_ate                 prazo escolhido para revisar a conferência, AAAA-MM-DD
original_sha256            campo sha256 da fonte
texto_sha256               hash do texto extraído
metadados_sha256           hash dos metadados
declaracao_origem_oficial  true, somente após conferir a origem
```

O arquivo deve ser JSON conforme o schema. A data não pode estar no futuro nem anteceder a consulta, e a validade não pode anteceder a conferência. O prazo é registrado pelo responsável, sem um número de dias presumido pelo sistema.

```bash
python scripts/importar_fontes_jt.py data/casos/CNJ-CONFIRMADO \
  --fonte FON-ID-RETORNADO \
  --conferencia data/conferencia-fonte.json
```

Os três hashes devem corresponder à importação. O agente não registra essa declaração por conta própria. A conferência é um registro nominal, não assinatura autenticada, certificação de origem ou prova de atualização do portal.

## 3. Consolidar as revisões selecionadas

```bash
python scripts/merge_fontes_jt.py data/casos/CNJ-CONFIRMADO \
  --fontes FON-PRIMEIRA-FONTE FON-SEGUNDA-FONTE
```

A publicação de `fontes-juridicas.json` só acontece se todo o conjunto selecionado passar: contratos, identidade, arquivos/hashes, páginas, âmbito, situação e conferência válida. Corpus vazio, fonte não conferida, conferência vencida, extração incompleta, situação incerta/revogada/superada/suspensa/vencida ou tema apenas afetado/suspenso impedem a publicação. Temas afetados/suspensos podem ser preservados e relatados na pesquisa, mas não viram tese firmada.

IDs repetidos são deduplicados. Versões conflitantes da mesma referência/conteúdo exigem seleção explícita de uma revisão. A normalização de chaves reaproveita o utilitário legado; citações diretas usam comparação própria, preservando acentos e caixa. O contrato de saída do merge federal foi mantido e o script ainda funciona isoladamente.

Cada ID representa uma revisão dos bytes originais e de todos os metadados. Repetir a mesma importação preserva o registro; mudar metadados ou conteúdo cria outro ID. Para corrigir metadados ou reprocessar uma extração, prepare uma revisão explicada e selecione-a novamente, preservando a anterior. Renovar a conferência do mesmo ID invalida a cópia antiga no corpus e exige nova consolidação.

Importação e consolidação usam lock local. A nova importação é publicada por renomeação de pasta; conferência e corpus usam substituição atômica. Falha não publica subconjunto aprovado nem substitui um corpus anterior por resultado parcial. Um corpus anterior preservado não representa sucesso da última tentativa. Após interrupção abrupta, confirme que não há processo em execução antes de tratar lock/temporários residuais; não há recuperação automática de queda de energia.

## 4. Vincular regras, matriz e citações

Cada regra usada na matriz deve apontar para `texto` e `texto_sha256` de sua fonte, conservar tipo/órgão/URL coerentes e declarar tema presente nos metadados. `referencias-minuta.json` registra exatamente um vínculo por regra usada. O verificador confere que o trecho está na fonte e que a regra não amplia sua vigência declarada. A pertinência e o direito intertemporal continuam sujeitos a revisão.

Forneça o corpus, as regras, a matriz, a eventual minuta e o contexto ao agente `pesquisador-fontes-trabalhista`:

```bash
python scripts/verificar_referencias_jt.py data/casos/CNJ-CONFIRMADO --contexto
python scripts/verificar_referencias_jt.py data/casos/CNJ-CONFIRMADO --gate
```

`--contexto` exibe hashes; não aprova o caso nem gera referências. O agente propõe `pesquisa-fontes.md` e `referencias-minuta.json`, com revisões inicialmente pendentes. O responsável revisa pertinência e cobertura antes do gate. A execução do verificador não altera a matriz/minuta.

Uma referência identifica:

- ID próprio, alvo `matriz` ou `minuta` e ponteiro JSON do campo (vazio para minuta).
- Início inclusivo e fim exclusivo, contando caracteres Unicode como no Python, com trecho exatamente igual ao intervalo do destino.
- Uso `direta`, `parafrase`, `mencao`, `relato-alegacao` ou `nao-citacao`.
- Natureza `fonte`, `prova` ou `nenhuma`, com IDs exclusivos e trecho literal da origem.
- Página física iniciada em 1 para PDF ou prova; página nula para HTML/TXT oficial.
- Revisão de pertinência, justificativa, responsável e data.

Citação direta compara o trecho do destino ao da origem sem remover negação, pontuação, acentos ou caixa; apenas Unicode e espaços são normalizados. Não há tamanho mínimo para validar uma citação registrada. Aspas ou marcador de bloco podem ficar fora do intervalo registrado. Paráfrases e menções também exigem trecho de apoio e revisão humana.

Jurisprudência reproduzida na petição não serve como fundamento oficial por ser prova dos autos. `relato-alegacao` permite relatar explicitamente a alegação de uma parte, com revisão, sem conferir validade à tese citada. `nao-citacao` trata expressão entre aspas que não constitui referência; exige justificativa/revisão e não dispensa menções jurídicas.

## Varredura, estados e limites

A varredura procura expressões jurídicas (artigos, leis, CLT, súmulas, temas, tribunais e URLs), aspas, blocos de citação e sequências literais de oito palavras presentes no corpus. Isso inclui reprodução sem aspas, mas não detecta toda paráfrase ou frase curta sem marcadores. Nesses casos, a revisão humana de cobertura é indispensável. Ambiguidades ficam como pendência; o script não decide o sentido jurídico de uma frase.

Na matriz, são examinados campos discursivos de valor factual, fundamentação, justificativa e análise; IDs, metadados e trechos armazenados apenas como evidência não são tratados como texto de minuta. A minuta, quando existir em `minuta.md`, é examinada integralmente. Texto fora desses artefatos não é coberto. Não há gerador de minuta nesta fase.

| Operação | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Importar/conferir | Sem impedimentos detectados | Registro preservado com pendências | Entrada, schema, origem, hash ou configuração recusados |
| Consolidar | Corpus publicado ou já idêntico | Conjunto impedido; corpus anterior preservado | Arquivo, schema, caminho ou configuração inválidos |
| Verificar sem `--gate` | Sem erros estruturais, podendo haver pendências | Artefato ausente, incoerente ou desatualizado | Schema, caminho ou configuração inválidos |
| Verificar com `--gate` | Sem erros ou pendências detectados | Erro ou pendência impeditiva | Schema, caminho ou configuração inválidos |

O gate de referências também executa a validação da análise da fase 3, confere o corpus contra as importações atuais e verifica hashes da matriz, regras, documentos, pedidos e eventual minuta. Aprovação técnica não prova autenticidade, vigência, pertinência ou correção jurídica. `apto_para_minuta` continua falso; a etapa de sentença/revisão será implementada na fase 5.

Em 05/11/2026, passaram **122 testes** em macOS/Python 3.12.16: 88 anteriores, incluindo OCR real, e 34 da fase 4. Foram conferidos também schemas, sintaxe, dependências, links e execução dos comandos em instalação separada. As fontes dos testes são inteiramente fictícias, mesmo quando usam um domínio oficial para testar validação de endereço. Nenhum processo ou fonte jurídica real foi importado para os testes.

O agente ainda precisa de execução no Claude Code e avaliação pelo responsável trabalhista. Não houve homologação jurídica ou validação em outros sistemas operacionais. A matriz normativa distribuída continua sendo um roteiro, sem teses ou parâmetros de cálculo previamente homologados.
