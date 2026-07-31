# Servidor MCP para Redmine

Conecta o Claude Desktop / Claude Code ao seu Redmine local via API REST.

## 1. Pré-requisitos

- Python 3.10+
- Sua API key do Redmine:
  1. No Redmine, vá em **Administração → Configurações → API** e habilite
     "Ativar serviço web REST" (se ainda não estiver ativo).
  2. Vá em **Minha conta → Chave de acesso à API** e copie o valor.

## 2. Instalação

```bash
cd redmine-mcp
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

## 3. Testar localmente (opcional)

```bash
export REDMINE_URL="http://redmine.ubuntuserver.vmw"
export REDMINE_API_KEY="sua_chave_aqui"
python server.py
```

Se não der erro de conexão, o servidor está pronto (ele fica esperando
mensagens MCP via stdin/stdout — é normal não "acontecer nada" no terminal).

## 4. Configurar no Claude Desktop

Edite (ou crie) o arquivo de configuração do Claude Desktop:

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

Adicione (ajuste os caminhos para o local real do projeto na sua máquina):

```json
{
  "mcpServers": {
    "redmine": {
      "command": "/caminho/completo/para/redmine-mcp/venv/bin/python",
      "args": ["/caminho/completo/para/redmine-mcp/server.py"],
      "env": {
        "REDMINE_URL": "http://redmine.ubuntuserver.vmw",
        "REDMINE_API_KEY": "sua_chave_aqui"
      }
    }
  }
}
```

Depois, reinicie o Claude Desktop. O ícone de ferramentas (🔨) deve mostrar
as ferramentas do Redmine disponíveis.

## 5. Configurar no Claude Code

No terminal, dentro do seu projeto (ou globalmente):

```bash
claude mcp add redmine \
  --env REDMINE_URL=http://redmine.ubuntuserver.vmw \
  --env REDMINE_API_KEY=sua_chave_aqui \
  -- /caminho/completo/para/redmine-mcp/venv/bin/python /caminho/completo/para/redmine-mcp/server.py
```

Confirme com:

```bash
claude mcp list
```

## 6. Ferramentas disponíveis

### Issues

| Ferramenta | O que faz |
|---|---|
| `listar_projetos` | Lista todos os projetos do Redmine |
| `listar_issues` | Lista issues, com filtro por projeto e status |
| `detalhar_issue` | Mostra detalhes e histórico de uma issue |
| `criar_issue` | Cria uma nova issue em um projeto |
| `atualizar_issue` | Atualiza qualquer campo da issue, ou adiciona comentário |
| `atualizar_issues_em_lote` | Aplica a mesma alteração a várias issues |
| `excluir_issue` | Exclui uma issue permanentemente |

`listar_issues` filtra por tracker, categoria, versão, responsável, autor,
tarefa pai, texto no assunto, intervalo de datas e campo personalizado; ordena
por qualquer campo; e pagina com `limite` + `deslocamento`. Também executa uma
consulta salva via `consulta_id` — nesse caso o Redmine ignora os demais filtros.

A resposta traz `total`, `devolvidas`, `deslocamento` e `restantes`, para dar
para saber se falta paginar sem ter que adivinhar.

`detalhar_issue` traz anexos, relações, observadores e sub-tarefas, além do
histórico. O histórico pode ser desligado com `incluir_historico=False` em issues
muito longas.

`atualizar_issues_em_lote` existe porque corrigir a categoria de 30 issues não
deveria custar 30 chamadas. Não aborta no primeiro erro — tenta todas e devolve o
resultado individual. **Não há equivalente para criação**: cada issue tem
conteúdo próprio, e agrupá-las numa chamada não economizaria nada.

`criar_issue` e `atualizar_issue` aceitam, além do básico: `categoria_id`,
`versao_id`, `responsavel_id`, `tarefa_pai_id`, `data_inicio`, `data_prevista`,
`horas_estimadas` e `campos_personalizados`. `atualizar_issue` aceita ainda
`percentual_concluido` e `descricao`.

**Só altera o que você informar.** Os sentinelas de "não mexe neste campo" são
`0` para IDs, string vazia para texto e data, `-1` para percentual e horas. A
consequência é que **não dá para limpar um campo por aqui** — esvaziar uma data
ou remover um responsável tem que ser feito na tela.

`descricao` em `atualizar_issue` **substitui** a descrição inteira. Para
acrescentar um registro sem perder o que já existe, use `notas`, que vira
comentário no histórico.

### Metadados

| Ferramenta | O que faz |
|---|---|
| `listar_status_e_prioridades` | IDs de status e prioridade da instância |
| `listar_trackers` | IDs dos tipos de tarefa |
| `listar_campos_personalizados` | IDs, formato e valores possíveis dos campos personalizados |
| `listar_categorias_projeto` | Categorias de tarefa de um projeto, com IDs |
| `criar_categoria_projeto` | Cria uma categoria de tarefa |
| `listar_versoes_projeto` | Versões (marcos) de um projeto, com IDs |
| `criar_versao_projeto` | Cria uma versão |
| `atualizar_versao` | Renomeia, redata ou muda a situação de uma versão |
| `excluir_versao` | Exclui uma versão |

Todos os IDs do Redmine variam por instância. Consulte estas ferramentas antes
de chamar `criar_issue`, em vez de assumir os valores padrão da documentação.

> `listar_campos_personalizados` exige **usuário administrador** — é restrição do
> Redmine, não do servidor. Sem privilégio, ele devolve o erro explicando isso.

> Excluir versão deixa as issues que a referenciam sem versão prevista. Para tirar
> de circulação preservando o vínculo, use `atualizar_versao` com
> `situacao="closed"`.

### Usuários e papéis

| Ferramenta | O que faz |
|---|---|
| `usuario_atual` | Quem é o dono da API key, e se é administrador |
| `listar_usuarios` | Lista usuários, com filtro por situação e nome |
| `detalhar_usuario` | Detalha um usuário, com projetos e papéis |
| `listar_papeis` | Papéis da instância, com IDs |
| `detalhar_papel` | Permissões concedidas a um papel |

`listar_usuarios` exige administrador. `usuario_atual` funciona com qualquer key
e é a forma mais direta de confirmar sob qual identidade o agente está operando.

`detalhar_papel` é o atalho para entender uma recusa: em vez de tentar de novo às
cegas, veja se a permissão existe.

### Busca e consultas salvas

| Ferramenta | O que faz |
|---|---|
| `buscar` | Busca por texto em issues, wiki e notícias |
| `listar_consultas` | Consultas (filtros) salvas visíveis para o usuário |

`buscar` aceita restrição por projeto, só títulos, só issues abertas, e a escolha
entre exigir todas as palavras ou qualquer uma delas.

### Observadores, comentários e notícias

| Ferramenta | O que faz |
|---|---|
| `adicionar_observador` | Adiciona watcher a uma issue |
| `remover_observador` | Remove watcher |
| `atualizar_comentario` | Edita o texto de um comentário já postado |
| `listar_noticias` | Lista notícias, por projeto ou da instância |
| `criar_noticia` | Publica uma notícia em um projeto |

> `atualizar_comentario` usa `PUT /journals/:id.json`, marcado como **alpha** na
> documentação do Redmine. Se responder 404, a sua versão não tem esse endpoint.
> O ID pedido é o do comentário (`journals[].id` em `detalhar_issue`), não o da issue.

> `criar_noticia` dispara notificação por e-mail conforme a configuração da
> instância — não é um rascunho silencioso.

### Relações entre issues

| Ferramenta | O que faz |
|---|---|
| `listar_relacoes_issue` | Lista as relações de uma issue, com o ID de cada relação |
| `criar_relacao_issue` | Cria uma relação entre duas issues |
| `excluir_relacao_issue` | Exclui uma relação pelo ID |
| `encadear_issues` | Encadeia uma lista de issues em sequência, um par por vez |

Tipos aceitos: `relates`, `precedes`, `follows`, `blocks`, `blocked`,
`duplicates`, `duplicated`, `copied_to`, `copied_from`.

```
encadear_issues(issue_ids=[22, 25, 49, 51], tipo="precedes")
  → #22 precede #25 precede #49 precede #51
```

`encadear_issues` não aborta no primeiro erro: tenta todos os pares e devolve o
resultado de cada um. Reexecutar é seguro — o Redmine recusa relação duplicada
com 422, que aparece como erro daquele par sem afetar os demais.

> **Cuidado com `precedes` e `follows`**: no Redmine essas duas são dirigidas por
> data. Ao criar a relação, o Redmine **reagenda a issue seguinte**, empurrando a
> data de início dela para depois da anterior — numa corrente longa, a última
> issue acaba dezenas de dias à frente. Se você quer apenas registrar a ordem sem
> mexer em cronograma, use `relates`. O parâmetro `atraso` só tem efeito nessas
> duas relações; nas demais é ignorado.

> **Permissão**: criar e excluir relações exige "Gerenciar relações entre tarefas"
> no papel do usuário dono da API key.

### Wiki

| Ferramenta | O que faz |
|---|---|
| `listar_paginas_wiki` | Lista todas as páginas de wiki de um projeto |
| `ler_pagina_wiki` | Lê o conteúdo de uma página (com suporte a versões antigas) |
| `criar_ou_editar_pagina_wiki` | Cria ou atualiza uma página, com aninhamento |
| `anexar_arquivo_wiki` | Anexa um arquivo a uma página existente |
| `excluir_pagina_wiki` | Exclui uma página de wiki |

`criar_ou_editar_pagina_wiki` aceita `pagina_pai` para aninhar a página no índice
do wiki. Sem isso, toda página nasce na raiz.

`anexar_arquivo_wiki` relê o texto atual antes de gravar, porque o endpoint do
Redmine substitui a página inteira — anexar sem esse cuidado apagaria o conteúdo.

### Time tracking (registro de horas)

| Ferramenta | O que faz |
|---|---|
| `listar_horas` | Lista lançamentos de horas com filtros (projeto, issue, usuário, período) e soma o total |
| `registrar_horas` | Lança horas trabalhadas em uma issue ou projeto |
| `atualizar_lancamento_horas` | Atualiza um lançamento de horas existente |
| `excluir_lancamento_horas` | Exclui um lançamento de horas |
| `listar_atividades_horas` | Lista os tipos de atividade disponíveis (Desenvolvimento, Suporte, etc.) |

> **Nota sobre a Wiki**: o módulo de Wiki precisa estar habilitado no projeto
> (Configurações do projeto → Módulos → Wiki) e a permissão REST correspondente
> deve estar ativa para o seu usuário/role.

### Anexos

| Ferramenta | O que faz |
|---|---|
| `anexar_arquivo_issue` | Envia um arquivo local e vincula à issue |
| `anexar_arquivo_wiki` | Mesma coisa, para página de wiki |
| `detalhar_anexo` | Nome, tamanho, tipo, autor e URL de download |
| `excluir_anexo` | Exclui um anexo permanentemente |

A API do Redmine exige duas etapas — `POST /uploads.json` para obter um token e
depois vincular o token à issue. `anexar_arquivo_issue` faz as duas numa chamada
e devolve o `anexo_id`, que o `PUT` do Redmine não retorna: sem ele não haveria
como chamar `detalhar_anexo` nem `excluir_anexo` depois.

> **O caminho do arquivo é lido na máquina onde o servidor MCP roda**, não na de
> quem chama a ferramenta. Em uso local isso é a mesma máquina; num cenário
> remoto, não.

O upload não passa pelo `_request`, porque exige `Content-Type:
application/octet-stream` enquanto o resto da API usa JSON. Antes de tocar a
rede, o servidor recusa arquivo inexistente, arquivo vazio (o Redmine rejeita 0
byte) e arquivo acima de 50 MB — limite deste servidor, ajustável em
`_TAMANHO_MAXIMO_UPLOAD`. O tipo MIME é deduzido da extensão.

### Projetos e membros

| Ferramenta | O que faz |
|---|---|
| `detalhar_projeto` | Descrição, módulos habilitados, trackers e categorias |
| `criar_projeto` | Cria projeto ou subprojeto |
| `atualizar_projeto` | Nome, descrição e homepage |
| `arquivar_projeto` | Arquiva ou desarquiva |
| `listar_membros_projeto` | Membros e seus papéis |
| `adicionar_membro_projeto` | Adiciona usuário com um ou mais papéis |
| `atualizar_membro_projeto` | Substitui a lista de papéis de um membro |
| `remover_membro_projeto` | Remove o membro do projeto |

`criar_projeto` nasce **privado** por padrão, mais conservador que o do Redmine.
O `identifier` é imutável depois de criado — limitação do Redmine.

As três ferramentas de membro trabalham com o **ID da associação**, não o do
usuário. Ele vem no campo `id_associacao` de `listar_membros_projeto`.

> **Não existe `excluir_projeto`, de propósito.** É irreversível e leva junto
> issues, horas, wiki e anexos. Use `arquivar_projeto`, que tem o mesmo efeito
> prático — some das listagens, fica somente leitura — e se desfaz. Excluir
> projeto de verdade continua sendo operação de tela.

## 7. Mensagens de erro

O tratamento é centralizado em `_request`. Quando a API do Redmine recusa uma
chamada, o servidor lê o corpo da resposta — é lá que está a explicação real, no
campo `errors` — e devolve essa frase. Sem corpo útil, cai no status HTTP com o
motivo provável:

| Status | Mensagem |
|---|---|
| 401 | API key inválida ou ausente |
| 403 | sem permissão para esta operação, ou módulo desabilitado no projeto |
| 404 | não encontrado (confira o ID, ou o endpoint pode não existir nesta versão) |
| 409 | conflito — o recurso foi alterado por outra pessoa |
| 422 | dados recusados pela validação do Redmine |

Vale para as 40 ferramentas, de leitura e de escrita. Antes, uma falha chegava
como o texto cru do `requests`, com a URL inteira e nenhuma pista do motivo.

## 8. Observações de segurança

- A API key dá acesso equivalente ao seu usuário do Redmine — trate-a como senha.
- Como o Redmine está em rede local (`.vmw`), isso só funciona rodando o
  servidor MCP na mesma máquina/rede que tem acesso a esse host — ou seja,
  Claude Desktop/Code local, não o Claude.ai web.
- Se quiser restringir o que o agente pode fazer (ex: só leitura), basta
  remover as funções `criar_issue` e `atualizar_issue` do `server.py`.
