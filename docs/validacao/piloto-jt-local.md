# Evidências do piloto trabalhista local

**Piloto não homologado.** O mantenedor se indicou como responsável pela revisão jurídica; nenhum aceite foi preenchido em seu nome. A arquitetura original permanece: comando, agentes, arquivos e verificadores.

## Escopos de validação

| Camada | Estado |
| --- | --- |
| Corpus sintético de 12 cenários | Implementado com expectativas e critérios por caso |
| Testes determinísticos, instalação e OCR no macOS | Execução desta entrega registrada abaixo |
| Linux em contêiner e CI | Evidências e limites registrados abaixo |
| Claude Code: 12 casos × 3 repetições | **0/36 realizadas**; executável indisponível neste ambiente |
| Fontes reais conferidas para avaliação jurídica do corpus | Pendente de preparação/conferência pelo responsável |
| Revisão jurídica das 12 fichas e confirmação do recorte | **0/12 aceitas**; responsável indicado, revisão pendente |
| Aceite final do piloto | **Não registrado** |

O corpus dos testes usa regras/conferências fictícias e respostas preenchidas por código. Seus resultados comprovam somente os controles de software implementados. Não são minutas produzidas por modelo nem evidência de acerto jurídico.

## Cenários e repetições com agentes

O [manifesto](../../tests/fixtures/jt/manifesto.json) define entradas, resultado esperado, motivo do bloqueio e critérios de revisão.

| Caso | Resultado esperado | R1 | R2 | R3 |
| --- | --- | --- | --- | --- |
| Ordinário simples | Minuta técnica com relatório e todos os pedidos | Não executada | Não executada | Não executada |
| Sumaríssimo | Minuta técnica sem inserir relatório interno | Não executada | Não executada | Não executada |
| Vínculo controvertido | Análise das versões e proposta sujeita à revisão | Não executada | Não executada | Não executada |
| Jornada com tabela repetida | Oito linhas preservadas, principal e reflexos | Não executada | Não executada | Não executada |
| Verbas rescisórias | Parcelas separadas, sem liquidação automática | Não executada | Não executada | Não executada |
| Múltiplos réus | Defesa e responsabilidade individualizadas | Não executada | Não executada | Não executada |
| Norma coletiva ausente | Bloqueio no relatório/inventário | Não executada | Não executada | Não executada |
| Prova oral sem transcrição | Bloqueio na triagem | Não executada | Não executada | Não executada |
| Documento decisivo ausente | Bloqueio na ingestão | Não executada | Não executada | Não executada |
| PDF misto | Duas páginas, extração digital e OCR | Não executada | Não executada | Não executada |
| Fonte não conferida | Bloqueio antes da consolidação de fontes | Não executada | Não executada | Não executada |
| Caso fora do escopo | Bloqueio de demanda contra ente público | Não executada | Não executada | Não executada |

Os campos de modelo, versão de Claude Code, duração, hashes de saída e variação das 36 execuções permanecem sem dados. O [roteiro operacional](operacao-piloto-jt.md) gera registros vazios e explica coleta, revisão, correção e verificação. Resultados esperados são critérios iniciais para conferência do responsável, não conclusões jurídicas homologadas.

## Evidências técnicas desta entrega

Em 05/11/2026, **172 testes passaram, sem testes ignorados**, em cada um dos dois ambientes abaixo. Incluem OCR real, os 12 cenários e instalação isolada. Sintaxe, schemas, dependências, links, inventário de fixtures e gates de aceite pendente também passaram.

| Ambiente | Python | Tesseract / Poppler | Duração total | Evidência |
| --- | --- | --- | --- | --- |
| macOS / arm64 | 3.12.16 | tesseract 5.5.4 / pdftoppm version 26.05.0 | 63.411 s | [JSON](evidencias/fase-6-macos.json) |
| Linux / aarch64 em Docker | 3.12.16 | tesseract 5.5.0 / pdftoppm version 25.03.0 | 51.621 s | [JSON](evidencias/fase-6-linux-container.json) |

Bibliotecas em ambos os ambientes: pdfplumber 0.11.10, pypdf 6.21.4, pdf2image 1.17.0, pytesseract 0.3.13, Pillow 13.0.0, jsonschema 4.26.0 e reportlab 5.1.0. Os hashes do idioma `por` estão nos relatórios; os binários de OCR diferem entre os ambientes e foram exercitados de fato.

Assinatura do pacote testado: `30c95327a5bcbf4f37c9ec8ac283721241d84b48e660892a19967e1165fe9514`. Assinatura do código/fixtures de validação: `4b8ed89fb1975fb01e5fb8acd6f3dbe80dbcce94cbaf7a7b8ec23c8c09f6f198`. Hash do manifesto: `5502ed0ef90aec263189f03d3586f832f381a8507dcc8ae5e8615165afaa4b56`. Os dois relatórios devem ser consultados junto aos seus hashes; uma edição posterior exige nova evidência.

A imagem local usada foi `superjurista-trt-validacao:fase6`, ID `sha256:d9fcd74d593eacd9a3ce77bb36fd771a0401bd7ce87713795afa670d06d769c9`. O repositório foi montado somente para leitura; apenas o relatório foi exportado.

A CI Linux/Python 3.11 e 3.12 está configurada. Sua execução remota será registrada separadamente da evidência local; nenhuma das duas representa execução de agentes ou homologação jurídica.

