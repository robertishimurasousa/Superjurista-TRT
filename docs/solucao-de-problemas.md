# Solução de problemas

[Voltar ao índice](README.md)

| Sintoma | O que verificar |
| --- | --- |
| O instalador não aparece | Inicie com `claude --plugin-dir CAMINHO-DO-REPOSITORIO` e procure `/superjurista-dev:instalar-superjurista` |
| Os fluxos judiciais não aparecem | Confira a cópia para `.claude/commands/` no projeto de trabalho e reinicie a sessão |
| `python` não é encontrado | Ative o ambiente virtual e confira o executável configurado em `.mcp.json` |
| `ModuleNotFoundError` | Instale as dependências com o mesmo Python que executa o script ou MCP |
| Falha ao instalar `mcp` | Confira Python 3.10 ou superior e os requisitos da versão resolvida pelo `pip` |
| MCP não aparece ou não conecta | Confira `.mcp.json`, caminhos absolutos, dependências e o estado em `/mcp` |
| Ferramenta JULIA ou PESQUISA_STJ ausente | Essas integrações não estão entre os cinco servidores distribuídos; consulte [integrações](integracoes.md) |
| OCR não encontra português | Confira se `tesseract --list-langs` inclui `por` e se os dados de idioma estão acessíveis |
| Conversão falha ao abrir páginas | Confira Poppler, `pdftoppm` e, quando necessário, `POPPLER_PATH` |
| Texto extraído vazio ou incompleto | Confira se o PDF é digital ou digitalizado; use OCR quando a extração digital não produzir texto suficiente |
| PJe retorna erro de autenticação | Confira validade da sessão e compatibilidade com o tribunal; não reutilize automaticamente a configuração TRF5 em TRT |
| `fork-terminal` falha no macOS/Linux | A implementação distribuída depende de Windows Terminal e PowerShell |
| Varredura retorna 0 com pendências | Esse é o comportamento de inventário; use `--gate` para exigir todas as etapas válidas |
| Etapa aparece como inválida | Confira prefixo, arquivo, tamanho, marcadores e seções exigidos pelo verificador |
| Análise retorna código 3 | O contrato sinaliza `ESCALAR`; o fluxo deve executar o trabalho adicional previsto |
| Minuta de TRT falha na assinatura | Há contratos herdados que exigem `juiz federal`; adapte agente e verificador em conjunto |
| Alterações desaparecem após sincronizar | `sync-scaffold.ps1` recria áreas geradas; consulte [desenvolvimento](desenvolvimento.md) |

## Diagnóstico mínimo

No projeto de trabalho, com o ambiente virtual ativo:

```bash
python --version
python -m pip check
python scripts/verificar_sentenca.py --help
```

Para um caso específico, execute a varredura e guarde apenas as mensagens de estado necessárias. Evite compartilhar os autos ou a sessão para demonstrar um erro.

Ao [abrir um chamado](https://github.com/robertishimurasousa/Superjurista-TRT/issues), informe o componente, as etapas para reproduzir, o comportamento esperado e o observado. Distinga falha local, falha da integração externa e problema no conteúdo produzido.
