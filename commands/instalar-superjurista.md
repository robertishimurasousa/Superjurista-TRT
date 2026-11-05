---
description: Instala a base do perfil trabalhista local ou, explicitamente, o sistema federal legado
argument-hint: "[--perfil jt-1g-local | --legado-federal]"
allowed-tools: Bash Read Write AskUserQuestion Glob
---

# Instalar o SuperJurista por perfil

O padrão deste derivado é `jt-1g-local`. O perfil inclui ingestão de PDFs locais, classificação documental, análise provisória por pedido e fontes/citações rastreáveis e o comando de minuta, revisão e retomada `/pipeline-sentenca-trabalhista`. A homologação jurídica permanece pendente.

## Procedimento

1. Interprete `$ARGUMENTS`. Aceite vazio ou `--perfil jt-1g-local`. Rejeite outros argumentos e combinações de opções. O destino é a pasta atual do usuário, separada do repositório do plugin.
2. Execute a conferência, usando o Python disponível no ambiente:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/instalar_perfil.py" --perfil jt-1g-local --destino . --dry-run
```

3. Se houver conflito (código 1) ou configuração inválida (código 2), apresente a lista e pare. Não sobrescreva, remova ou renomeie arquivos para contornar o conflito. O usuário pode revisar/mesclar o conteúdo antes de repetir a instalação.
4. Se a conferência passar, execute o mesmo comando sem `--dry-run`. A solicitação de instalar já autoriza a criação dos arquivos novos; não é necessária outra confirmação.
5. Apresente o resumo real do script. Se existirem componentes fora do perfil, informe que foram preservados e que a pasta não está isolada. Não registre MCPs, não instale dependências federais e não copie o scaffold inteiro.

## Opção federal legada

Somente se `$ARGUMENTS` for exatamente `--legado-federal`, leia `${CLAUDE_PLUGIN_ROOT}/spec/referencias/instalacao-legado.md` e siga o instalador original. Não execute o legado em pasta que contenha `.claude/perfis/jt-1g-local.json`; indique uma pasta separada.

O identificador do plugin continua `superjurista-dev`. Use português e diferencie minuta técnica, conferências humanas e homologação jurídica. O fluxo de sessão requer macOS/Linux.
