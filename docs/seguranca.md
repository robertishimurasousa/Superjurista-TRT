# Dados e segurança

[Voltar ao índice](README.md)

## Onde os dados circulam

Os scripts gravam PDFs, textos, sessões e artefatos no projeto de trabalho. A execução de agentes pelo Claude Code pode enviar conteúdo ao serviço de modelo configurado, e as integrações de pesquisa enviam consultas a fontes externas. Armazenamento local não significa processamento inteiramente local.

Use documentos cujo tratamento no ambiente escolhido esteja autorizado. Para demonstrações, documentação, testes e chamados públicos, prefira dados sintéticos ou anonimizados.

## Sessões e credenciais

Cookies, arquivos HAR, senhas, tokens e sementes TOTP podem permitir acesso a contas e processos. Mantenha esses dados fora do controle de versão, dos exemplos e dos registros compartilhados. Consulte apenas os arquivos estritamente necessários ao diagnóstico.

Os `.gitignore` existentes não cobrem todos os possíveis arquivos sensíveis. O modelo do projeto ignora alguns dados, mas não protege automaticamente todos os documentos Markdown produzidos pelos agentes. Se versionar o projeto de trabalho, revise as exclusões, incluindo conforme o ambiente:

```gitignore
.venv/
.env
.env.*
!.env.example
data/
*.har
*cookies*.json
pje_session*.json
*credentials*
```

Esse bloco é uma orientação para o projeto de trabalho, não uma alteração automática no repositório. Arquivos já rastreados não deixam de ser versionados pela inclusão no `.gitignore`.

## Compartilhar diagnósticos

Informe o comando, a versão do Python, o sistema operacional e a mensagem de erro sanitizada. Remova identificadores pessoais, trechos dos autos, cabeçalhos de autenticação e URLs com tokens. Revise também capturas de tela e anexos.

Se ocorrer exposição de credencial, revogue ou renove o acesso correspondente e avalie as cópias e o histórico envolvidos. Não publique o segredo em um chamado para demonstrar o problema. Não há um canal privado específico de segurança documentado neste repositório.

## Revisão dos resultados

Confira a fidelidade aos autos, a origem das fontes e a correspondência entre pedidos, fundamentação e dispositivo antes de usar uma minuta. Os scripts de validação oferecem controles técnicos delimitados; não substituem a revisão do responsável pelo trabalho.
