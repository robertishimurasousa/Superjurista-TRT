# Documentação do SuperJurista TRT

Documentação em português brasileiro para usuários e mantenedores deste repositório. Os guias descrevem os arquivos distribuídos, sem pressupor homologação em tribunal ou disponibilidade atual de serviços externos.

## Roteiro de leitura

1. [Instalação](instalacao.md): preparar um projeto de trabalho e suas dependências.
2. [Uso e comandos](uso.md): escolher o fluxo, localizar os artefatos e verificar pendências.
3. [Integrações](integracoes.md): configurar MCP, PDF/OCR e acesso ao PJe.
4. [Adaptação para TRT](adaptacao-trt.md): identificar dependências herdadas e critérios para validar uma adaptação.
5. [Dados e segurança](seguranca.md): tratar documentos, sessões e compartilhamento de resultados.

## Referências para manutenção

- [Fase 1: perfis e importação](fase-1-perfis.md): infraestrutura implementada e limites atuais.

- [Diagnóstico de adaptação à Justiça do Trabalho](diagnostico-justica-trabalho.md): evidências no código e bloqueios do fluxo atual.
- [Plano do piloto de 1º grau com PDFs locais](../plan/feature-justica-trabalho-1.md): tarefas, dependências e critérios de aceite.
- [Arquitetura](arquitetura.md): camadas, contratos, verificadores e versões.
- [Desenvolvimento](desenvolvimento.md): alterações, verificações locais e sincronização.
- [Solução de problemas](solucao-de-problemas.md): sintomas e diagnósticos.
- [Como contribuir](../CONTRIBUTING.md).
- [Créditos e licença](../CREDITOS.md).
- [Histórico de alterações](../CHANGELOG.md).
- [Especificações herdadas](../spec/README.md) e [padrão soberano](../skills/criar-sistema/references/padrao-soberano.md).

## Como interpretar os caminhos

**Repositório do plugin:** contém `commands/`, `agents/`, `skills/` e `scaffold/`. É onde se mantém o código distribuído.

**Projeto de trabalho:** é a pasta que recebe a instalação. Nela, os componentes ficam em `.claude/`, os verificadores em `scripts/` e os dados em `data/`.

Exemplos com `python scripts/...` devem ser executados no projeto de trabalho. Para examinar o equivalente no repositório, use `scaffold/scripts/...`. Arquivos gerados por agentes não são entregues prontos no repositório.

## Idioma e identificadores

A documentação editorial é escrita em português. Nomes de arquivos, chaves JSON, parâmetros de comandos e identificadores de ferramentas são mantidos como definidos no código. O texto original da licença MIT é preservado em [LICENSE](../LICENSE).
