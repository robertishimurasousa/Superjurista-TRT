# SuperJurista TRT — piloto com PDFs locais

Perfil `jt-1g-local`, versão de contrato 1, estado **base em desenvolvimento**. A fase 2 entrega ingestão, rastreabilidade e classificação documental proposta. Análise jurídica e sentença permanecem pendentes.

## Preparar e executar

Use Python 3.11 ou superior. Crie um ambiente virtual e instale `requirements.txt`. Para OCR, disponibilize Poppler (`pdfinfo`/`pdftoppm`) e Tesseract com idioma português `por`. Variáveis opcionais: `POPPLER_PATH`, `TESSERACT_CMD` e `TESSDATA_PREFIX`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
mkdir -p data/entrada
cp .claude/perfis/caso.exemplo.json data/caso-confirmado.json
```

Preencha os metadados com informações conferidas nos autos. O exemplo é fictício. Coloque os PDFs em `data/entrada`, declare os documentos esperados em `data/caso-confirmado.json` e execute:

```bash
python scripts/ingerir_documentos.py --input data/entrada --workspace data/casos/CNJ-CONFIRMADO --caso data/caso-confirmado.json
python scripts/verificar_documentos.py data/casos/CNJ-CONFIRMADO --gate
```

Também é aceito um único PDF em `--input`. A identidade vem do JSON confirmado, não do nome da pasta. O diretório de saída deve ser separado da entrada.

Originais e textos por página recebem SHA-256; duplicatas compartilham um original. Repetir os mesmos arquivos preserva os resultados. PDFs protegidos/corrompidos, páginas ilegíveis e documentos obrigatórios ausentes geram pendências. Código 0 no gate significa apenas aprovação técnica dos critérios implementados.

## Componentes e limites

O inventário está em `.claude/perfis/jt-1g-local.json` e os contratos em `.claude/schemas/`. O agente `extrator-caso` pode propor `classificacao.json` com tipos e intervalos de páginas; requer conferência humana e nova execução do gate. Não é acionado automaticamente pelos scripts Python.

A ingestão/OCR é local. Ao usar o agente, os textos passam pelo provedor configurado no Claude Code; confirme a autorização de tratamento antes de usar autos reais. Mantenha casos em `data/`, ignorado pelo Git.

Não são instalados MCPs, autenticação PJe ou comandos federais. Uma pasta preexistente pode conter componentes externos ao perfil: confira os avisos do instalador.

O OCR pode errar palavras e números. Metadados confirmados não podem ser substituídos em uma ingestão posterior; para correção ou reprocessamento após falha, preserve o caso anterior e use outra pasta. A classificação pode precisar de atualização após acrescentar PDFs.

[Guia completo da fase 2](https://github.com/robertishimurasousa/Superjurista-TRT/blob/main/docs/fase-2-ingestao.md) · [Plano](https://github.com/robertishimurasousa/Superjurista-TRT/blob/main/plan/feature-justica-trabalho-1.md)
