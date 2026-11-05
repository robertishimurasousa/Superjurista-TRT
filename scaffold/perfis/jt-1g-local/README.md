# SuperJurista TRT — base do piloto local

Perfil: `jt-1g-local`, versão 1. Estado: **base em desenvolvimento**.

A fase 1 instala a estrutura e o contrato de perfil. Ainda não há ingestão de PDFs, agentes trabalhistas ou comando de sentença. Não use os fluxos federais do projeto original como substitutos deste piloto.

## Arquivos instalados

- `.claude/perfis/jt-1g-local.json`: inventário explícito do perfil.
- `.claude/perfis/perfil.schema.json`: contrato legível por validadores JSON Schema.
- `scripts/perfil.py`: validação do perfil pela biblioteca padrão Python.
- `requirements.txt`: dependências desta etapa.
- `CLAUDE.md`: instruções e limites atuais.
- `.gitignore`: exclusões de dados e segredos.
- `data/casos/`: diretório reservado aos casos futuros.

Não são instalados servidores MCP, autenticação PJe, agentes ou comandos federais. Em uma pasta que já tinha esses componentes, a instalação não os remove; confira os avisos do instalador.

Python mínimo nesta base: 3.9. Dependências de PDF/OCR serão adicionadas na fase de ingestão; MCPs do legado exigem Python 3.10 ou superior.

[Plano do piloto](https://github.com/robertishimurasousa/Superjurista-TRT/blob/main/plan/feature-justica-trabalho-1.md).
