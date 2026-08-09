# Setup do mcp-redmine no Cline (VS Code)

O `mcp-redmine` é compatível com o Cline sem nenhuma modificação. Este guia
cobre a instalação e configuração do servidor MCP para funcionar com o Cline no
VS Code, tanto no Windows quanto em Linux/Mac.

## Pré-requisitos

- **Python 3.10+** instalado e no PATH
- **Redmine** com REST API habilitada: *Administration → Settings → API → Enable REST web service*
- **Chave de API** do Redmine: *My account → API access key*
- **Cline** instalado no VS Code

## Instalação do MCP Server

Escolha **uma** das três opções abaixo.

### Opção A: uv tool install (recomendado)

```bash
uv tool install mcp-redmine
```

Isso instala o executável `mcp-redmine` globalmente no ambiente `uv`.

### Opção B: pip

```bash
pip install mcp-redmine
```

### Opção C: from source

```bash
git clone https://github.com/alsimoes/mcp-redmine.git
cd mcp-redmine
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -e .
```

---

## Configuração no Cline

O Cline oferece **três formas** de registrar um MCP server. Escolha a que
melhor se adequa ao seu fluxo.

> **Importante:** Em todos os snippets abaixo, substitua `REDMINE_URL` e
> `REDMINE_API_KEY` pelos valores reais da sua instância Redmine.

---

### Método 1 — `.mcp.json` no workspace (zero-config para o time)

O repositório já inclui um arquivo `.mcp.json` na raiz. O Cline o detecta
automaticamente quando você abre este repositório como workspace.

1. Abra a pasta `mcp-redmine` como workspace no VS Code
2. Edite o `.mcp.json` com suas variáveis de ambiente:

```json
{
  "mcpServers": {
    "redmine": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "mcp_redmine"
      ],
      "env": {
        "REDMINE_URL": "https://redmine.seuservidor.com",
        "REDMINE_API_KEY": "sua_chave_api_aqui",
        "REDMINE_TIMEOUT": "15"
      }
    }
  }
}
```

3. Recarregue a janela do VS Code (`Ctrl+Shift+P` → *Developer: Reload Window*)

> **Nota:** Se você não usa `uv`, ajuste `command` e `args` conforme os
> exemplos da seção "Configurações prontas para copiar-colar" abaixo.

---

### Método 2 — Configuração global do Cline

1. Abra o VS Code
2. Pressione `Ctrl+Shift+P` e execute **Cline: Open MCP Config File** (ou *Cline: Abrir Arquivo de Configuração MCP*)
3. O arquivo `cline_mcp_settings.json` será aberto. Adicione o bloco:

```json
{
  "mcpServers": {
    "redmine": {
      "command": "mcp-redmine",
      "env": {
        "REDMINE_URL": "https://redmine.seuservidor.com",
        "REDMINE_API_KEY": "sua_chave_api_aqui"
      }
    }
  }
}
```

4. Salve o arquivo e reinicie o VS Code

> **Localização do arquivo:**
> - Windows: `%USERPROFILE%\.cline\cline_mcp_settings.json`
> - Linux: `~/.cline/cline_mcp_settings.json`
> - Mac: `~/Library/Application Support/Code/User/globalStorage/...` (use o comando da paleta)

---

### Método 3 — Via interface do Cline (MCP Settings UI)

1. Clique no botão do Cline na barra lateral do VS Code
2. Clique no ícone de engrenagem ao lado de "MCP Servers"
3. Em "Installed", clique em **+ Add MCP Server**
4. Preencha com os dados:

| Campo | Valor |
|---|---|
| Name | `redmine` |
| Command | `mcp-redmine` (ou `python`) |
| Args | (deixe vazio, ou `-m mcp_redmine` se command for `python`) |
| Env | `REDMINE_URL=https://redmine.seuservidor.com` |
| | `REDMINE_API_KEY=sua_chave_api_aqui` |

5. Clique em **Save** e verifique se o servidor aparece como "Connected"

---

## Configurações prontas para copiar-colar

Escolha o snippet que corresponde à sua instalação e método de execução.

### Instalado com `uv tool install` (Opção A)

```json
{
  "mcpServers": {
    "redmine": {
      "command": "mcp-redmine",
      "env": {
        "REDMINE_URL": "https://redmine.seuservidor.com",
        "REDMINE_API_KEY": "sua_chave_api_aqui"
      }
    }
  }
}
```

### Instalado com `pip` / from source, via módulo Python

```json
{
  "mcpServers": {
    "redmine": {
      "command": "python",
      "args": ["-m", "mcp_redmine"],
      "env": {
        "REDMINE_URL": "https://redmine.seuservidor.com",
        "REDMINE_API_KEY": "sua_chave_api_aqui"
      }
    }
  }
}
```

### From source, usando o script `server.py` (Windows, caminho absoluto)

```json
{
  "mcpServers": {
    "redmine": {
      "command": "python",
      "args": ["C:/dev/repos/mcp-redmine/server.py"],
      "env": {
        "REDMINE_URL": "https://redmine.seuservidor.com",
        "REDMINE_API_KEY": "sua_chave_api_aqui",
        "REDMINE_TIMEOUT": "15"
      }
    }
  }
}
```

### From source, usando `uv run`

```json
{
  "mcpServers": {
    "redmine": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_redmine"],
      "env": {
        "REDMINE_URL": "https://redmine.seuservidor.com",
        "REDMINE_API_KEY": "sua_chave_api_aqui"
      }
    }
  }
}
```

### From source, com virtual environment (caminho absoluto)

```json
{
  "mcpServers": {
    "redmine": {
      "command": "C:/dev/repos/mcp-redmine/venv/Scripts/python.exe",
      "args": ["-m", "mcp_redmine"],
      "env": {
        "REDMINE_URL": "https://redmine.seuservidor.com",
        "REDMINE_API_KEY": "sua_chave_api_aqui"
      }
    }
  }
}
```

---

## Verificando se está funcionando

1. **Verifique o Output do Cline:** abra o painel *Output* do VS Code
   (`Ctrl+Shift+U`), selecione **Cline** no dropdown. O servidor MCP deve
   aparecer como conectado sem erros.

2. **Verifique as ferramentas:** peça algo simples ao Cline:
   > List my Redmine projects
   
   Se as ferramentas estiverem carregadas, o Cline usará `list_projects`
   automaticamente.

3. **Teste manual:** você também pode rodar o servidor diretamente no terminal
   para confirmar que as variáveis de ambiente estão corretas:
   ```bash
   # Windows (cmd):
   set REDMINE_URL=https://redmine.seuservidor.com
   set REDMINE_API_KEY=sua_chave_api_aqui
   mcp-redmine
   ```
   Se o servidor iniciar sem erro de configuração (ficará esperando mensagens
   MCP no stdio), a conexão está funcionando. Pressione `Ctrl+C` para sair.

---

## Troubleshooting

### "REDMINE_URL and REDMINE_API_KEY must be set"

As variáveis de ambiente não estão sendo passadas para o processo filho.
Verifique:
- O bloco `env` está corretamente dentro da configuração do servidor
- Não há erros de sintaxe no JSON (vírgulas extras, aspas desbalanceadas)
- No `.mcp.json`, variáveis com sintaxe `${VAR}` podem não ser expandidas pelo
  Cline — use valores literais em vez disso

### "No module named 'mcp.server.fastmcp'"

O pacote `mcp[cli]` não está instalado. Execute:
```bash
pip install "mcp[cli]>=1.0.0,<2.0.0"
```

### "No module named 'mcp_redmine'"

O pacote `mcp-redmine` não está instalado no Python que o Cline está chamando.
- Se usa `command: "python"`, confirme que `pip install mcp-redmine` foi
  executado no **mesmo** Python que está no PATH do VS Code
- Se usa venv, confirme que o caminho do `python.exe` está correto

### O servidor aparece como "Disconnected"

No painel *Output* → **Cline**, procure pela linha de erro. As causas comuns são:
- **Caminho errado do `command`**: verifique se o executável existe
- **Python não está no PATH**: use o caminho absoluto (ex:
  `C:/Python310/python.exe`)
- **Firewall bloqueando**: o servidor precisa de acesso de rede à URL do Redmine
- **Erro 401**: chave de API inválida ou REST API não habilitada no Redmine

### Cline não reconhece o `.mcp.json`

- Confirme que o arquivo se chama exatamente `.mcp.json` (com o ponto no início)
- O arquivo precisa estar na **raiz do workspace** aberto no VS Code
- Recarregue a janela: `Ctrl+Shift+P` → *Developer: Reload Window*

### Erro 403 em ferramentas específicas

A chave de API pertence a um usuário do Redmine que não tem permissão para
aquela operação. Use `get_role` para verificar quais permissões o papel (role)
do usuário possui. Considere criar um usuário dedicado com as permissões exatas
que você quer conceder ao agente.

---

## 73 ferramentas disponíveis

Uma vez configurado, o Cline terá acesso a todas as ferramentas do Redmine:

| Recurso | Ferramentas |
|---|---|
| Issues | `list_issues`, `get_issue`, `create_issue`, `update_issue`, `bulk_update_issues`, `delete_issue`, `add_watcher`, `remove_watcher`, `update_journal_note` |
| Issue relations | `list_issue_relations`, `create_issue_relation`, `delete_issue_relation`, `chain_issues` |
| Projects | `list_projects`, `get_project`, `create_project`, `update_project`, `archive_project` |
| Memberships | `list_project_members`, `add_project_member`, `update_project_member`, `remove_project_member` |
| Versions | `list_project_versions`, `create_project_version`, `update_version`, `delete_version` |
| Categories | `list_project_categories`, `create_project_category`, `update_project_category`, `delete_project_category` |
| Users | `get_current_user`, `list_users`, `get_user`, `create_user`, `update_user`, `update_my_account` |
| Groups | `list_groups`, `get_group`, `create_group`, `update_group`, `delete_group`, `add_user_to_group`, `remove_user_from_group` |
| Roles | `list_roles`, `get_role` |
| Wiki | `list_wiki_pages`, `get_wiki_page`, `create_or_update_wiki_page`, `attach_file_to_wiki_page`, `delete_wiki_page` |
| Time tracking | `list_time_entries`, `get_time_entry`, `log_time`, `update_time_entry`, `delete_time_entry`, `list_time_entry_activities` |
| Attachments | `attach_file_to_issue`, `get_attachment`, `update_attachment`, `delete_attachment` |
| Project files | `list_project_files`, `upload_project_file` |
| News | `list_news`, `get_news_item`, `create_news`, `update_news`, `delete_news` |
| Search | `search`, `list_saved_queries` |
| Metadata | `list_statuses_and_priorities`, `list_trackers`, `list_custom_fields`, `list_document_categories` |

Para a referência completa de assinaturas e parâmetros, veja [docs/TOOLS.md](docs/TOOLS.md).

---

## Por que funciona sem adaptações?

O `mcp-redmine` foi construído sobre o **protocolo MCP padrão** (transporte
stdio), que é o mesmo protocolo que o Cline implementa. Ele não depende de
nenhuma API ou extensão específica do Claude Desktop. Os três pilares da
compatibilidade são:

1. **FastMCP / MCP SDK padrão** — o servidor usa `mcp[cli]>=1.0.0`, a
   implementação oficial do protocolo MCP
2. **Variáveis de ambiente** — o Cline suporta o bloco `env` na configuração de
   servidores MCP, assim como o Claude Desktop
3. **Transporte stdio** — o servidor se comunica via stdin/stdout, sem
   dependência de WebSockets, HTTP, ou qualquer outro transporte proprietário