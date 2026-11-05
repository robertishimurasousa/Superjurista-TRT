# Fase 1 — distribuição por perfil

> Registro da entrega inicial. A distribuição atual inclui também a [fase 2 de ingestão](fase-2-ingestao.md), com componentes e requisitos adicionais.

[Voltar ao índice](README.md) · [Plano](../plan/feature-justica-trabalho-1.md)

## Estado da entrega

A base de instalação do perfil `jt-1g-local` está implementada. Ela entrega **sete arquivos declarados no manifesto** e o diretório `data/casos/`, sem agentes, fluxos judiciais ou servidores MCP. A ingestão de PDFs e a produção de minutas pertencem às fases seguintes.

O requisito mínimo desta base é Python 3.9. A execução do instalador, do importador e do validador usa apenas a biblioteca padrão. A dependência `jsonschema` é de desenvolvimento, para conferir o contrato formal nos testes. Os requisitos Python 3.10+ dos MCPs continuam aplicáveis ao legado federal.

## Instalar e conferir

A partir do repositório, escolha uma pasta de trabalho separada. Estes exemplos usam uma pasta irmã:

```bash
python3 scripts/instalar_perfil.py --perfil jt-1g-local --destino ../superjurista-trt-trabalho --dry-run
python3 scripts/instalar_perfil.py --perfil jt-1g-local --destino ../superjurista-trt-trabalho
```

A simulação não cria o destino. A instalação confere todas as origens e os destinos antes de gravar. Arquivos idênticos são preservados sem regravação; arquivos diferentes ou diretórios conflitantes impedem a instalação inteira. Não existe opção de sobrescrita automática: revise os conflitos e faça a mesclagem desejada antes de tentar novamente.

O perfil instalado contém README, instruções `CLAUDE.md`, `.gitignore`, `requirements.txt`, manifesto, schema e `scripts/perfil.py`. Somente os arquivos explicitamente declarados em [jt-1g-local.json](../scaffold/perfis/jt-1g-local.json) são copiados. O [schema](../spec/schemas/perfil.schema.json) descreve a estrutura; o [validador Python](../scaffold/scripts/perfil.py) acrescenta existência, caminhos permitidos, links simbólicos, colisões e coerência entre componentes.

Caminhos simbólicos são recusados; use o caminho real do diretório. Componentes de outra instalação já presentes são preservados e listados como aviso, sem garantia de isolamento. Para obter uma instalação isolada, use uma pasta vazia.

| Código | Significado |
| --- | --- |
| 0 | Instalação ou simulação concluída; não significa piloto jurídico validado |
| 1 | Conflitos de conteúdo; nenhum arquivo novo gravado |
| 2 | Perfil, caminho, origem ou operação de arquivos inválida |

O instalador usa criação exclusiva para não sobrescrever arquivos surgidos depois da conferência. Falhas de gravação removem os arquivos novos daquela chamada e preservam os preexistentes. Não edite a pasta de destino durante a instalação.

## Claude Code e legado

O comando `/superjurista-dev:instalar-superjurista` usa o perfil local por padrão. Ele primeiro executa `--dry-run` e depois a instalação, quando não há conflitos.

A instalação federal antiga permanece como opção explícita:

```text
/superjurista-dev:instalar-superjurista --legado-federal
```

As instruções herdadas estão em [instalacao-legado.md](../spec/referencias/instalacao-legado.md). Essa opção exige outra pasta e não representa suporte trabalhista. O identificador do plugin permanece `superjurista-dev`.

## Importar atualizações upstream

O `scaffold/` versionado passou a ser a fonte da distribuição deste derivado. A sincronização destrutiva foi substituída por preparação de uma cópia para revisão.

Informe explicitamente o diretório `.claude` do projeto de origem, seus scripts e a pasta dos MCPs globais. Substitua os caminhos ilustrativos por origens reais:

```bash
python3 scripts/importar_scaffold.py --projeto /origem/projeto/.claude --scripts /origem/projeto/scripts --mcps-globais /origem/global/mcp-servers
```

No PowerShell, a entrada equivalente é:

```powershell
./sync-scaffold.ps1 -Projeto 'C:/origem/projeto/.claude' -ProjetoScripts 'C:/origem/projeto/scripts' -GlobalMcp 'C:/origem/global/mcp-servers' -Python python
```

O importador exige as áreas `agents`, `commands`, `skills`, os scripts e os cinco servidores do legado nas respectivas origens. Se alguma origem estiver ausente, falha antes de criar a área temporária.

O resultado é um diretório temporário com `scaffold/` candidato e `comparacao.json`. O relatório classifica arquivos novos, alterados e iguais por SHA-256; lista arquivos existentes somente no derivado como preservados. Não executa o código importado, não atualiza o plugin, não apaga arquivos locais e não faz commit. Depois da revisão, aplique somente as mudanças desejadas e descarte a área temporária quando não precisar mais dela.

Artefatos pessoais e meta-ferramentas herdadas são excluídos conforme a lista do importador. Nomes de sessão, cookies, HAR, `.env`, credenciais e caches também são filtrados. Esse filtro de nomes não é um detector de segredos inseridos em conteúdo; revise os arquivos candidatos antes de incorporá-los.

## Testes e evidências

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m pip check
```

Validação em 05/11/2026: macOS, Python 3.9.6, **33 testes aprovados**, executados em diretórios temporários. Bibliotecas resolvidas: `jsonschema 4.23.0`, `attrs 26.1.0`, `jsonschema-specifications 2025.9.1`, `referencing 0.36.2`, `rpds-py 0.27.1` e `typing-extensions 4.16.0`. A versão direta está fixada; as transitivas são resolvidas pelo pip, sem alegação de lockfile completo.

A suíte verifica contratos, CLI sem pacotes externos, idempotência, conflitos, simulação, rollback de falha de escrita, proteção de caminhos, exclusões Git e importação sem mutação. O wrapper PowerShell e a execução dentro do Claude Code não foram executados neste ambiente, onde esses programas não estão disponíveis. Os testes não acessam tribunais nem comprovam análise jurídica.
