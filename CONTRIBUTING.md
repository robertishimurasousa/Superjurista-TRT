# Como contribuir

Contribuições para o SuperJurista TRT podem melhorar documentação, contratos de agentes, verificadores e integrações. Consulte primeiro a [documentação](docs/README.md) e o [estado da adaptação para TRT](docs/adaptacao-trt.md).

## Relatar um problema

Abra um [chamado neste repositório](https://github.com/robertishimurasousa/Superjurista-TRT/issues) em português, informando:

- O componente e a revisão ou versão utilizada.
- O sistema operacional e a versão do Python, quando relevantes.
- Os passos mínimos para reproduzir.
- O resultado esperado e o resultado observado.
- Mensagens de erro sanitizadas, sem credenciais nem dados processuais identificáveis.

Para uma proposta de funcionalidade, descreva a necessidade, o comportamento esperado e como será possível verificar o resultado.

## Enviar uma alteração

1. Crie uma ramificação com escopo claro.
2. Consulte os contratos e componentes afetados.
3. Implemente a alteração e atualize os guias correspondentes em português.
4. Execute as [verificações pertinentes](docs/desenvolvimento.md).
5. Revise o diff e abra uma solicitação de alteração com problema, solução e evidências de validação.

Use exemplos sintéticos ou anonimizados. Não inclua sessões PJe, arquivos HAR, sementes TOTP, documentos reais ou saídas que exponham informações pessoais.

## Convenções

- Escreva explicações em português brasileiro, com acentuação.
- Preserve nomes técnicos exigidos pelas interfaces e contratos.
- Atualize agentes e verificadores em conjunto quando o formato da saída mudar.
- Separe verificação local de integração externa e de aceite de domínio.
- Preserve os avisos de autoria e a licença dos componentes reutilizados.

O `scaffold/` versionado é a fonte deste derivado. As importações upstream são preparadas em área temporária para revisão, sem regeneração destrutiva. Consulte [desenvolvimento e manutenção](docs/desenvolvimento.md).
