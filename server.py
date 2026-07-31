#!/usr/bin/env python3
"""
Servidor MCP para integração com Redmine.

Expõe ferramentas para o Claude (Desktop ou Code) consultar e manipular
projetos, issues e usuários de uma instância Redmine via API REST.

Configuração via variáveis de ambiente:
  REDMINE_URL     - URL base do Redmine (ex: http://redmine.ubuntuserver.vmw)
  REDMINE_API_KEY - Chave de API (Minha conta > Chave de acesso à API)
"""

import os
import sys
import json
import mimetypes
import requests
from mcp.server.fastmcp import FastMCP

REDMINE_URL = os.environ.get("REDMINE_URL", "").rstrip("/")
REDMINE_API_KEY = os.environ.get("REDMINE_API_KEY", "")

if not REDMINE_URL or not REDMINE_API_KEY:
    print(
        "ERRO: defina REDMINE_URL e REDMINE_API_KEY nas variáveis de ambiente "
        "(configuradas no claude_desktop_config.json).",
        file=sys.stderr,
    )

mcp = FastMCP("redmine")

HEADERS = {
    "X-Redmine-API-Key": REDMINE_API_KEY,
    "Content-Type": "application/json",
}


# Motivos prováveis por status, para quem lê a mensagem sem ter a documentação
# do Redmine aberta ao lado.
_MOTIVOS_HTTP = {
    401: "API key inválida ou ausente",
    403: "sem permissão para esta operação, ou módulo desabilitado no projeto",
    404: "não encontrado (confira o ID, ou o endpoint pode não existir nesta versão)",
    409: "conflito — o recurso foi alterado por outra pessoa",
    422: "dados recusados pela validação do Redmine",
}


def _erro_resposta(resp) -> str:
    """
    Traduz uma resposta de erro do Redmine em uma frase legível.

    Em falhas de validação o Redmine devolve {"errors": [...]} no corpo, e é ali
    que está a explicação de verdade — campo obrigatório em branco, relação
    circular, ID inexistente. Quando não há corpo útil, cai no status com o
    motivo provável.
    """
    try:
        erros = resp.json().get("errors")
        if erros:
            return "; ".join(str(e) for e in erros)
    except ValueError:
        pass

    motivo = _MOTIVOS_HTTP.get(resp.status_code)
    return f"HTTP {resp.status_code}" + (f" — {motivo}" if motivo else "")


def _request(method: str, path: str, **kwargs):
    """
    Executa a chamada à API do Redmine.

    Em caso de falha levanta RuntimeError já com a mensagem tratada, em vez do
    texto cru do requests. Isso vale para todas as ferramentas: as que capturam
    a exceção acrescentam o próprio contexto, e as que não capturam deixam o
    FastMCP exibir a mensagem, que já é legível por si.
    """
    url = f"{REDMINE_URL}{path}"
    try:
        resp = requests.request(method, url, headers=HEADERS, timeout=15, **kwargs)
    except requests.RequestException as exc:
        raise RuntimeError(f"falha de rede ao acessar o Redmine: {exc}") from None

    if not resp.ok:
        raise RuntimeError(_erro_resposta(resp))

    if resp.text.strip():
        return resp.json()
    return {}


def _erro_redmine(exc: Exception) -> str:
    """
    Devolve a mensagem de uma exceção vinda de _request.

    Desde que o tratamento passou para dentro do _request, a exceção já chega
    com o texto pronto. A checagem de 'response' permanece para o caso de uma
    HTTPError vinda de outro caminho.
    """
    resposta = getattr(exc, "response", None)
    if resposta is not None:
        return _erro_resposta(resposta)
    return str(exc)


@mcp.tool()
def listar_projetos() -> str:
    """Lista todos os projetos disponíveis no Redmine."""
    data = _request("GET", "/projects.json?limit=100")
    projetos = [
        {"id": p["id"], "nome": p["name"], "identifier": p["identifier"]}
        for p in data.get("projects", [])
    ]
    return json.dumps(projetos, ensure_ascii=False, indent=2)


@mcp.tool()
def listar_issues(
    projeto_identifier: str = "",
    status: str = "open",
    limite: int = 25,
) -> str:
    """
    Lista issues (tarefas/chamados) do Redmine.

    Args:
        projeto_identifier: identificador do projeto (ex: 'meu-projeto'). Vazio = todos os projetos.
        status: 'open', 'closed' ou '*' (todos).
        limite: número máximo de issues retornadas.
    """
    params = {"status_id": status, "limit": limite}
    if projeto_identifier:
        params["project_id"] = projeto_identifier

    data = _request("GET", "/issues.json", params=params)
    issues = [
        {
            "id": i["id"],
            "assunto": i["subject"],
            "status": i["status"]["name"],
            "prioridade": i["priority"]["name"],
            "projeto": i["project"]["name"],
            "atribuido_a": i.get("assigned_to", {}).get("name", "-"),
            "atualizado_em": i.get("updated_on"),
        }
        for i in data.get("issues", [])
    ]
    return json.dumps(issues, ensure_ascii=False, indent=2)


@mcp.tool()
def detalhar_issue(issue_id: int) -> str:
    """Retorna todos os detalhes de uma issue específica, incluindo descrição e comentários."""
    data = _request("GET", f"/issues/{issue_id}.json?include=journals")
    return json.dumps(data.get("issue", {}), ensure_ascii=False, indent=2)


def _campos_opcionais_issue(
    categoria_id: int = 0,
    versao_id: int = 0,
    responsavel_id: int = 0,
    tarefa_pai_id: int = 0,
    data_inicio: str = "",
    data_prevista: str = "",
    percentual_concluido: int = -1,
    horas_estimadas: float = -1.0,
    campos_personalizados: dict | None = None,
) -> dict:
    """
    Monta os campos opcionais comuns a criar_issue e atualizar_issue.

    Só entra no payload o que foi informado — os sentinelas (0, "", -1) significam
    "não mexer neste campo". Isso importa em atualizar_issue: mandar um campo com
    valor vazio apagaria o conteúdo existente no Redmine.
    """
    campos: dict = {}

    if categoria_id:
        campos["category_id"] = categoria_id
    if versao_id:
        campos["fixed_version_id"] = versao_id
    if responsavel_id:
        campos["assigned_to_id"] = responsavel_id
    if tarefa_pai_id:
        campos["parent_issue_id"] = tarefa_pai_id
    if data_inicio:
        campos["start_date"] = data_inicio
    if data_prevista:
        campos["due_date"] = data_prevista
    if percentual_concluido >= 0:
        campos["done_ratio"] = percentual_concluido
    if horas_estimadas >= 0:
        campos["estimated_hours"] = horas_estimadas
    if campos_personalizados:
        campos["custom_fields"] = [
            {"id": int(cid), "value": valor}
            for cid, valor in campos_personalizados.items()
        ]

    return campos


@mcp.tool()
def criar_issue(
    projeto_identifier: str,
    assunto: str,
    descricao: str = "",
    tracker_id: int = 1,
    prioridade_id: int = 2,
    status_id: int = 0,
    categoria_id: int = 0,
    versao_id: int = 0,
    responsavel_id: int = 0,
    tarefa_pai_id: int = 0,
    data_inicio: str = "",
    data_prevista: str = "",
    horas_estimadas: float = -1.0,
    campos_personalizados: dict | None = None,
) -> str:
    """
    Cria uma nova issue no Redmine.

    Args:
        projeto_identifier: identificador do projeto (ex: 'meu-projeto').
        assunto: título da issue.
        descricao: descrição detalhada.
        tracker_id: ID do tipo de tarefa (varia por instância; use listar_trackers).
        prioridade_id: ID da prioridade (use listar_status_e_prioridades).
        status_id: ID do status (0 = usa o status inicial do fluxo de trabalho).
        categoria_id: ID da categoria de tarefa (use listar_categorias_projeto).
        versao_id: ID da versão prevista (use listar_versoes_projeto).
        responsavel_id: ID do usuário responsável.
        tarefa_pai_id: ID da issue pai, para criar como sub-tarefa.
        data_inicio: data de início, formato AAAA-MM-DD.
        data_prevista: data prevista de conclusão, formato AAAA-MM-DD.
        horas_estimadas: tempo estimado em horas (-1 = não informa).
        campos_personalizados: mapa {id_do_campo: valor}, ex: {"1": "5"}.
            Use listar_campos_personalizados para descobrir os IDs.

    Todos os campos além de projeto e assunto são opcionais; o que não for
    informado fica a cargo dos padrões do projeto.
    """
    issue_payload = {
        "project_id": projeto_identifier,
        "subject": assunto,
        "description": descricao,
        "tracker_id": tracker_id,
        "priority_id": prioridade_id,
    }
    if status_id:
        issue_payload["status_id"] = status_id

    issue_payload.update(
        _campos_opcionais_issue(
            categoria_id=categoria_id,
            versao_id=versao_id,
            responsavel_id=responsavel_id,
            tarefa_pai_id=tarefa_pai_id,
            data_inicio=data_inicio,
            data_prevista=data_prevista,
            horas_estimadas=horas_estimadas,
            campos_personalizados=campos_personalizados,
        )
    )

    try:
        data = _request("POST", "/issues.json", json={"issue": issue_payload})
    except Exception as exc:
        return f"Erro ao criar issue: {_erro_redmine(exc)}"

    return json.dumps(data.get("issue", {}), ensure_ascii=False, indent=2)


@mcp.tool()
def atualizar_issue(
    issue_id: int,
    status_id: int = 0,
    notas: str = "",
    assunto: str = "",
    descricao: str = "",
    prioridade_id: int = 0,
    tracker_id: int = 0,
    categoria_id: int = 0,
    versao_id: int = 0,
    responsavel_id: int = 0,
    tarefa_pai_id: int = 0,
    data_inicio: str = "",
    data_prevista: str = "",
    percentual_concluido: int = -1,
    horas_estimadas: float = -1.0,
    campos_personalizados: dict | None = None,
) -> str:
    """
    Atualiza uma issue existente. Só altera os campos informados.

    Args:
        issue_id: ID da issue a atualizar.
        status_id: novo ID de status (0 = não altera).
        notas: comentário a adicionar no histórico (não substitui a descrição).
        assunto: novo título (vazio = não altera).
        descricao: nova descrição — SUBSTITUI a existente por inteiro.
        prioridade_id: nova prioridade (0 = não altera).
        tracker_id: novo tipo de tarefa (0 = não altera).
        categoria_id: nova categoria de tarefa (0 = não altera).
        versao_id: nova versão prevista (0 = não altera).
        responsavel_id: novo responsável (0 = não altera).
        tarefa_pai_id: nova issue pai (0 = não altera).
        data_inicio: nova data de início, AAAA-MM-DD (vazio = não altera).
        data_prevista: nova data prevista, AAAA-MM-DD (vazio = não altera).
        percentual_concluido: 0 a 100 (-1 = não altera).
        horas_estimadas: tempo estimado em horas (-1 = não altera).
        campos_personalizados: mapa {id_do_campo: valor}, ex: {"1": "5"}.

    Sentinelas de "não altera": 0 para IDs, string vazia para texto e data,
    -1 para percentual e horas. Não há como limpar um campo por aqui — para
    esvaziar uma data ou remover um responsável, use a tela do Redmine.
    """
    issue_payload = {}
    if status_id:
        issue_payload["status_id"] = status_id
    if notas:
        issue_payload["notes"] = notas
    if assunto:
        issue_payload["subject"] = assunto
    if descricao:
        issue_payload["description"] = descricao
    if prioridade_id:
        issue_payload["priority_id"] = prioridade_id
    if tracker_id:
        issue_payload["tracker_id"] = tracker_id

    issue_payload.update(
        _campos_opcionais_issue(
            categoria_id=categoria_id,
            versao_id=versao_id,
            responsavel_id=responsavel_id,
            tarefa_pai_id=tarefa_pai_id,
            data_inicio=data_inicio,
            data_prevista=data_prevista,
            percentual_concluido=percentual_concluido,
            horas_estimadas=horas_estimadas,
            campos_personalizados=campos_personalizados,
        )
    )

    if not issue_payload:
        return f"Nada a atualizar em #{issue_id}: nenhum campo foi informado."

    try:
        _request("PUT", f"/issues/{issue_id}.json", json={"issue": issue_payload})
    except Exception as exc:
        return f"Erro ao atualizar #{issue_id}: {_erro_redmine(exc)}"

    alterados = sorted(k for k in issue_payload if k != "notes")
    resumo = ", ".join(alterados) if alterados else "apenas comentário"
    return f"Issue #{issue_id} atualizada com sucesso ({resumo})."


@mcp.tool()
def excluir_issue(issue_id: int) -> str:
    """
    Exclui uma issue permanentemente.

    ATENÇÃO: é irreversível e leva junto as sub-tarefas, os lançamentos de horas
    e o histórico da issue. O Redmine não tem lixeira. Prefira mover para um
    status fechado (ex: Cancelada) quando o objetivo for apenas tirar do board.

    Args:
        issue_id: ID da issue a excluir.
    """
    try:
        _request("DELETE", f"/issues/{issue_id}.json")
    except Exception as exc:
        return f"Erro ao excluir #{issue_id}: {_erro_redmine(exc)}"
    return f"Issue #{issue_id} excluída permanentemente."


@mcp.tool()
def listar_status_e_prioridades() -> str:
    """Lista os status de issue e níveis de prioridade disponíveis nesta instância Redmine."""
    statuses = _request("GET", "/issue_statuses.json")
    priorities = _request("GET", "/enumerations/issue_priorities.json")
    return json.dumps(
        {
            "status": statuses.get("issue_statuses", []),
            "prioridades": priorities.get("issue_priorities", []),
        },
        ensure_ascii=False,
        indent=2,
    )


# ---------------------------------------------------------------------------
# Metadados: trackers, categorias, versões, campos personalizados
# ---------------------------------------------------------------------------


@mcp.tool()
def listar_trackers() -> str:
    """
    Lista os tipos de tarefa (trackers) da instância, com seus IDs.

    Os IDs variam por instância — use esta ferramenta antes de criar_issue em vez
    de assumir os padrões do Redmine.
    """
    data = _request("GET", "/trackers.json")
    trackers = [
        {"id": t["id"], "nome": t["name"]} for t in data.get("trackers", [])
    ]
    return json.dumps(trackers, ensure_ascii=False, indent=2)


@mcp.tool()
def listar_campos_personalizados() -> str:
    """
    Lista os campos personalizados visíveis pela API, com ID, formato e a que se
    aplicam. Necessário para preencher 'campos_personalizados' em criar_issue e
    atualizar_issue.

    Requer privilégio de administrador no usuário dono da API key.
    """
    try:
        data = _request("GET", "/custom_fields.json")
    except Exception as exc:
        return (
            f"Erro ao listar campos personalizados: {_erro_redmine(exc)}. "
            "Este endpoint exige usuário administrador."
        )
    campos = [
        {
            "id": c["id"],
            "nome": c["name"],
            "formato": c.get("field_format"),
            "aplica_se_a": c.get("customized_type"),
            "obrigatorio": c.get("is_required"),
            "valores_possiveis": c.get("possible_values"),
        }
        for c in data.get("custom_fields", [])
    ]
    return json.dumps(campos, ensure_ascii=False, indent=2)


@mcp.tool()
def listar_categorias_projeto(projeto_identifier: str) -> str:
    """
    Lista as categorias de tarefa de um projeto, com seus IDs.

    Args:
        projeto_identifier: identificador do projeto (ex: 'meu-projeto').
    """
    data = _request("GET", f"/projects/{projeto_identifier}/issue_categories.json")
    categorias = [
        {
            "id": c["id"],
            "nome": c["name"],
            "responsavel_padrao": c.get("assigned_to", {}).get("name"),
        }
        for c in data.get("issue_categories", [])
    ]
    return json.dumps(categorias, ensure_ascii=False, indent=2)


@mcp.tool()
def criar_categoria_projeto(
    projeto_identifier: str,
    nome: str,
    responsavel_id: int = 0,
) -> str:
    """
    Cria uma categoria de tarefa em um projeto.

    Args:
        projeto_identifier: identificador do projeto.
        nome: nome da categoria (ex: 'Infraestrutura').
        responsavel_id: usuário atribuído por padrão às issues desta categoria
            (0 = nenhum).
    """
    categoria = {"name": nome}
    if responsavel_id:
        categoria["assigned_to_id"] = responsavel_id

    try:
        data = _request(
            "POST",
            f"/projects/{projeto_identifier}/issue_categories.json",
            json={"issue_category": categoria},
        )
    except Exception as exc:
        return f"Erro ao criar categoria '{nome}': {_erro_redmine(exc)}"

    return json.dumps(data.get("issue_category", {}), ensure_ascii=False, indent=2)


@mcp.tool()
def listar_versoes_projeto(projeto_identifier: str) -> str:
    """
    Lista as versões (marcos) de um projeto, com seus IDs.

    Args:
        projeto_identifier: identificador do projeto.
    """
    data = _request("GET", f"/projects/{projeto_identifier}/versions.json")
    versoes = [
        {
            "id": v["id"],
            "nome": v["name"],
            "situacao": v.get("status"),
            "data": v.get("due_date"),
            "descricao": v.get("description"),
        }
        for v in data.get("versions", [])
    ]
    return json.dumps(versoes, ensure_ascii=False, indent=2)


@mcp.tool()
def criar_versao_projeto(
    projeto_identifier: str,
    nome: str,
    descricao: str = "",
    situacao: str = "open",
    data_prevista: str = "",
) -> str:
    """
    Cria uma versão (marco) em um projeto.

    Args:
        projeto_identifier: identificador do projeto.
        nome: nome da versão (ex: 'v0.1 - Identidade').
        descricao: descrição livre.
        situacao: 'open', 'locked' ou 'closed'.
        data_prevista: data da versão, formato AAAA-MM-DD.
    """
    if situacao not in ("open", "locked", "closed"):
        return f"Situação inválida: '{situacao}'. Use open, locked ou closed."

    versao = {"name": nome, "status": situacao}
    if descricao:
        versao["description"] = descricao
    if data_prevista:
        versao["due_date"] = data_prevista

    try:
        data = _request(
            "POST",
            f"/projects/{projeto_identifier}/versions.json",
            json={"version": versao},
        )
    except Exception as exc:
        return f"Erro ao criar versão '{nome}': {_erro_redmine(exc)}"

    return json.dumps(data.get("version", {}), ensure_ascii=False, indent=2)


@mcp.tool()
def atualizar_versao(
    versao_id: int,
    nome: str = "",
    descricao: str = "",
    situacao: str = "",
    data_prevista: str = "",
) -> str:
    """
    Atualiza uma versão existente. Só altera os campos informados.

    Args:
        versao_id: ID da versão (use listar_versoes_projeto).
        nome: novo nome (vazio = não altera).
        descricao: nova descrição (vazio = não altera).
        situacao: 'open', 'locked' ou 'closed' (vazio = não altera).
            Fechar uma versão a remove da lista de escolhas de novas issues,
            sem afetar as que já a referenciam.
        data_prevista: nova data, AAAA-MM-DD (vazio = não altera).
    """
    if situacao and situacao not in ("open", "locked", "closed"):
        return f"Situação inválida: '{situacao}'. Use open, locked ou closed."

    versao = {}
    if nome:
        versao["name"] = nome
    if descricao:
        versao["description"] = descricao
    if situacao:
        versao["status"] = situacao
    if data_prevista:
        versao["due_date"] = data_prevista

    if not versao:
        return f"Nada a atualizar na versão #{versao_id}: nenhum campo foi informado."

    try:
        _request("PUT", f"/versions/{versao_id}.json", json={"version": versao})
    except Exception as exc:
        return f"Erro ao atualizar versão #{versao_id}: {_erro_redmine(exc)}"

    return f"Versão #{versao_id} atualizada com sucesso ({', '.join(sorted(versao))})."


@mcp.tool()
def excluir_versao(versao_id: int) -> str:
    """
    Exclui uma versão. As issues que a referenciam ficam sem versão prevista.

    Para apenas tirar a versão de circulação sem perder o vínculo histórico,
    prefira atualizar_versao com situacao='closed'.

    Args:
        versao_id: ID da versão a excluir.
    """
    try:
        _request("DELETE", f"/versions/{versao_id}.json")
    except Exception as exc:
        return f"Erro ao excluir versão #{versao_id}: {_erro_redmine(exc)}"
    return f"Versão #{versao_id} excluída."


# ---------------------------------------------------------------------------
# Wiki
# ---------------------------------------------------------------------------


@mcp.tool()
def listar_paginas_wiki(projeto_identifier: str) -> str:
    """
    Lista todas as páginas de wiki de um projeto.

    Args:
        projeto_identifier: identificador do projeto (ex: 'meu-projeto').
    """
    data = _request("GET", f"/projects/{projeto_identifier}/wiki/index.json")
    paginas = [
        {
            "titulo": p["title"],
            "versao": p.get("version"),
            "atualizado_em": p.get("updated_on"),
            "pai": p.get("parent", {}).get("title") if p.get("parent") else None,
        }
        for p in data.get("wiki_pages", [])
    ]
    return json.dumps(paginas, ensure_ascii=False, indent=2)


@mcp.tool()
def ler_pagina_wiki(projeto_identifier: str, titulo: str, versao: int = 0) -> str:
    """
    Lê o conteúdo de uma página de wiki específica.

    Args:
        projeto_identifier: identificador do projeto.
        titulo: título da página (ex: 'Pagina_inicial'). Case-sensitive conforme o Redmine.
        versao: número da versão a ler (0 = versão mais recente).
    """
    path = f"/projects/{projeto_identifier}/wiki/{titulo}.json"
    if versao:
        path = f"/projects/{projeto_identifier}/wiki/{titulo}/{versao}.json"
    data = _request("GET", path)
    pagina = data.get("wiki_page", {})
    return json.dumps(
        {
            "titulo": pagina.get("title"),
            "texto": pagina.get("text"),
            "versao": pagina.get("version"),
            "autor": pagina.get("author", {}).get("name"),
            "atualizado_em": pagina.get("updated_on"),
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def criar_ou_editar_pagina_wiki(
    projeto_identifier: str,
    titulo: str,
    texto: str,
    comentario: str = "",
) -> str:
    """
    Cria uma nova página de wiki ou atualiza uma existente (o Redmine usa o
    mesmo endpoint PUT para ambos os casos).

    Args:
        projeto_identifier: identificador do projeto.
        titulo: título da página (ex: 'Pagina_inicial').
        texto: conteúdo em formato Textile ou Markdown (depende da config do Redmine).
        comentario: comentário sobre a edição (aparece no histórico da página).
    """
    payload = {
        "wiki_page": {
            "text": texto,
            "comments": comentario,
        }
    }
    _request("PUT", f"/projects/{projeto_identifier}/wiki/{titulo}.json", json=payload)
    return f"Página de wiki '{titulo}' criada/atualizada com sucesso em '{projeto_identifier}'."


@mcp.tool()
def excluir_pagina_wiki(projeto_identifier: str, titulo: str) -> str:
    """
    Exclui uma página de wiki (e suas subpáginas, conforme comportamento padrão do Redmine).

    Args:
        projeto_identifier: identificador do projeto.
        titulo: título da página a excluir.
    """
    _request("DELETE", f"/projects/{projeto_identifier}/wiki/{titulo}.json")
    return f"Página de wiki '{titulo}' excluída de '{projeto_identifier}'."


# ---------------------------------------------------------------------------
# Time tracking
# ---------------------------------------------------------------------------


@mcp.tool()
def listar_horas(
    projeto_identifier: str = "",
    issue_id: int = 0,
    usuario_id: str = "",
    data_inicio: str = "",
    data_fim: str = "",
    limite: int = 50,
) -> str:
    """
    Lista lançamentos de horas (time entries) com filtros opcionais.

    Args:
        projeto_identifier: filtra por projeto (identifier ou id).
        issue_id: filtra por issue específica (0 = ignora este filtro).
        usuario_id: filtra por usuário; use 'me' para o usuário da API key.
        data_inicio: data mínima no formato AAAA-MM-DD.
        data_fim: data máxima no formato AAAA-MM-DD.
        limite: número máximo de registros retornados.
    """
    params = {"limit": limite}
    if projeto_identifier:
        params["project_id"] = projeto_identifier
    if issue_id:
        params["issue_id"] = issue_id
    if usuario_id:
        params["user_id"] = usuario_id
    if data_inicio:
        params["from"] = data_inicio
    if data_fim:
        params["to"] = data_fim

    data = _request("GET", "/time_entries.json", params=params)
    entradas = [
        {
            "id": e["id"],
            "issue_id": e.get("issue", {}).get("id"),
            "projeto": e.get("project", {}).get("name"),
            "usuario": e.get("user", {}).get("name"),
            "horas": e.get("hours"),
            "atividade": e.get("activity", {}).get("name"),
            "comentario": e.get("comments"),
            "data": e.get("spent_on"),
        }
        for e in data.get("time_entries", [])
    ]
    total_horas = sum(e["horas"] or 0 for e in entradas)
    return json.dumps(
        {"total_horas": total_horas, "lancamentos": entradas},
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def registrar_horas(
    horas: float,
    data: str,
    issue_id: int = 0,
    projeto_identifier: str = "",
    atividade_id: int = 0,
    comentario: str = "",
) -> str:
    """
    Registra (lança) horas trabalhadas no Redmine, vinculadas a uma issue ou a um projeto.

    Args:
        horas: quantidade de horas trabalhadas (ex: 2.5).
        data: data do trabalho no formato AAAA-MM-DD.
        issue_id: ID da issue (use isto OU projeto_identifier, não precisa dos dois).
        projeto_identifier: identificador do projeto (se não vincular a uma issue específica).
        atividade_id: ID do tipo de atividade (varia por instância; use listar_atividades_horas para ver as opções).
        comentario: descrição do que foi feito.
    """
    if not issue_id and not projeto_identifier:
        return "Erro: informe issue_id ou projeto_identifier."

    entry = {
        "hours": horas,
        "spent_on": data,
        "comments": comentario,
    }
    if issue_id:
        entry["issue_id"] = issue_id
    if projeto_identifier:
        entry["project_id"] = projeto_identifier
    if atividade_id:
        entry["activity_id"] = atividade_id

    data_resp = _request("POST", "/time_entries.json", json={"time_entry": entry})
    return json.dumps(data_resp.get("time_entry", {}), ensure_ascii=False, indent=2)


@mcp.tool()
def atualizar_lancamento_horas(
    time_entry_id: int,
    horas: float = 0,
    comentario: str = "",
    atividade_id: int = 0,
) -> str:
    """
    Atualiza um lançamento de horas existente.

    Args:
        time_entry_id: ID do lançamento de horas a atualizar.
        horas: novo valor de horas (0 = não altera).
        comentario: novo comentário (vazio = não altera).
        atividade_id: novo ID de atividade (0 = não altera).
    """
    entry = {}
    if horas:
        entry["hours"] = horas
    if comentario:
        entry["comments"] = comentario
    if atividade_id:
        entry["activity_id"] = atividade_id

    _request("PUT", f"/time_entries/{time_entry_id}.json", json={"time_entry": entry})
    return f"Lançamento de horas #{time_entry_id} atualizado com sucesso."


@mcp.tool()
def excluir_lancamento_horas(time_entry_id: int) -> str:
    """Exclui um lançamento de horas pelo ID."""
    _request("DELETE", f"/time_entries/{time_entry_id}.json")
    return f"Lançamento de horas #{time_entry_id} excluído com sucesso."


@mcp.tool()
def listar_atividades_horas() -> str:
    """Lista os tipos de atividade disponíveis para lançamento de horas (ex: Desenvolvimento, Design, Suporte)."""
    data = _request("GET", "/enumerations/time_entry_activities.json")
    return json.dumps(data.get("time_entry_activities", []), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Relações entre issues
# ---------------------------------------------------------------------------

TIPOS_RELACAO = (
    "relates",       # relacionada a
    "duplicates",    # duplica
    "duplicated",    # duplicada por
    "blocks",        # bloqueia
    "blocked",       # bloqueada por
    "precedes",      # precede
    "follows",       # segue
    "copied_to",     # copiada para
    "copied_from",   # copiada de
)

# Só estes dois aceitam o parâmetro de atraso (delay) no Redmine.
TIPOS_COM_ATRASO = ("precedes", "follows")


@mcp.tool()
def listar_relacoes_issue(issue_id: int) -> str:
    """
    Lista as relações de uma issue (precede, bloqueia, relacionada a, etc.).

    Args:
        issue_id: ID da issue.
    """
    data = _request("GET", f"/issues/{issue_id}/relations.json")
    relacoes = [
        {
            "id": r["id"],
            "de": r["issue_id"],
            "para": r["issue_to_id"],
            "tipo": r["relation_type"],
            "atraso": r.get("delay"),
        }
        for r in data.get("relations", [])
    ]
    return json.dumps(relacoes, ensure_ascii=False, indent=2)


@mcp.tool()
def criar_relacao_issue(
    issue_id: int,
    issue_alvo_id: int,
    tipo: str = "relates",
    atraso: int = 0,
) -> str:
    """
    Cria uma relação entre duas issues.

    Args:
        issue_id: ID da issue de origem.
        issue_alvo_id: ID da issue de destino.
        tipo: relates (relacionada a), precedes (precede), follows (segue),
              blocks (bloqueia), blocked (bloqueada por), duplicates (duplica),
              duplicated (duplicada por), copied_to, copied_from.
        atraso: dias de intervalo; só vale para 'precedes' e 'follows'.

    Atenção: 'precedes' e 'follows' são dirigidos por data — ao criar a relação
    o Redmine reagenda a issue seguinte, empurrando a data de início dela.
    Use 'relates' quando quiser apenas vincular, sem mexer em datas.
    """
    if tipo not in TIPOS_RELACAO:
        return (
            f"Tipo de relação inválido: '{tipo}'. "
            f"Use um destes: {', '.join(TIPOS_RELACAO)}."
        )

    relacao = {"issue_to_id": issue_alvo_id, "relation_type": tipo}
    if tipo in TIPOS_COM_ATRASO:
        relacao["delay"] = atraso

    try:
        data = _request("POST", f"/issues/{issue_id}/relations.json", json={"relation": relacao})
    except Exception as exc:
        return f"Erro ao relacionar #{issue_id} -> #{issue_alvo_id}: {_erro_redmine(exc)}"

    return json.dumps(data.get("relation", {}), ensure_ascii=False, indent=2)


@mcp.tool()
def excluir_relacao_issue(relacao_id: int) -> str:
    """
    Exclui uma relação entre issues pelo ID da relação.

    Args:
        relacao_id: ID da relação (obtido em listar_relacoes_issue, campo 'id').
    """
    try:
        _request("DELETE", f"/relations/{relacao_id}.json")
    except Exception as exc:
        return f"Erro ao excluir relação #{relacao_id}: {_erro_redmine(exc)}"
    return f"Relação #{relacao_id} excluída com sucesso."


@mcp.tool()
def encadear_issues(
    issue_ids: list[int],
    tipo: str = "precedes",
    atraso: int = 0,
) -> str:
    """
    Encadeia uma lista de issues em sequência: a primeira se relaciona com a
    segunda, a segunda com a terceira, e assim por diante.

    Útil para impor a ordem de execução de um conjunto de tarefas sem precisar
    abrir o formulário de relações uma vez por par.

    Args:
        issue_ids: IDs na ordem desejada (ex: [22, 25, 49, 51]).
        tipo: mesmo conjunto de criar_relacao_issue. Padrão 'precedes'.
        atraso: dias de intervalo; só vale para 'precedes' e 'follows'.

    Não aborta no primeiro erro: tenta todos os pares e devolve o resultado de
    cada um. Reexecutar é seguro — o Redmine recusa relação duplicada com 422,
    que aparece como erro daquele par e não afeta os demais.
    """
    if tipo not in TIPOS_RELACAO:
        return (
            f"Tipo de relação inválido: '{tipo}'. "
            f"Use um destes: {', '.join(TIPOS_RELACAO)}."
        )
    if len(issue_ids) < 2:
        return "Informe pelo menos duas issues para encadear."

    duplicados = {i for i in issue_ids if issue_ids.count(i) > 1}
    if duplicados:
        return f"IDs repetidos na lista: {sorted(duplicados)}. Uma issue não pode aparecer duas vezes."

    resultados = []
    criadas = 0
    falhas = 0

    for origem, destino in zip(issue_ids, issue_ids[1:]):
        relacao = {"issue_to_id": destino, "relation_type": tipo}
        if tipo in TIPOS_COM_ATRASO:
            relacao["delay"] = atraso

        try:
            _request("POST", f"/issues/{origem}/relations.json", json={"relation": relacao})
            resultados.append({"de": origem, "para": destino, "resultado": "ok"})
            criadas += 1
        except Exception as exc:
            resultados.append({"de": origem, "para": destino, "resultado": "erro", "detalhe": _erro_redmine(exc)})
            falhas += 1

    return json.dumps(
        {
            "tipo": tipo,
            "pares_tentados": len(issue_ids) - 1,
            "criadas": criadas,
            "falhas": falhas,
            "detalhes": resultados,
        },
        ensure_ascii=False,
        indent=2,
    )


# ---------------------------------------------------------------------------
# Usuários e papéis
# ---------------------------------------------------------------------------


@mcp.tool()
def usuario_atual() -> str:
    """
    Retorna o usuário dono da API key configurada neste servidor.

    Útil para confirmar sob qual identidade as issues estão sendo criadas, e se
    esse usuário é administrador.
    """
    data = _request("GET", "/users/current.json")
    u = data.get("user", {})
    return json.dumps(
        {
            "id": u.get("id"),
            "login": u.get("login"),
            "nome": f"{u.get('firstname', '')} {u.get('lastname', '')}".strip(),
            "email": u.get("mail"),
            "administrador": u.get("admin"),
            "criado_em": u.get("created_on"),
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def listar_usuarios(status: int = 1, nome: str = "", limite: int = 50) -> str:
    """
    Lista os usuários do Redmine.

    Requer privilégio de administrador.

    Args:
        status: 1 = ativos, 2 = registrados aguardando ativação, 3 = bloqueados.
        nome: filtra por login, nome, sobrenome ou e-mail (busca parcial).
        limite: número máximo de usuários retornados.
    """
    params = {"status": status, "limit": limite}
    if nome:
        params["name"] = nome

    try:
        data = _request("GET", "/users.json", params=params)
    except Exception as exc:
        return (
            f"Erro ao listar usuários: {_erro_redmine(exc)}. "
            "Este endpoint exige usuário administrador."
        )

    usuarios = [
        {
            "id": u["id"],
            "login": u.get("login"),
            "nome": f"{u.get('firstname', '')} {u.get('lastname', '')}".strip(),
            "email": u.get("mail"),
            "administrador": u.get("admin"),
        }
        for u in data.get("users", [])
    ]
    return json.dumps(usuarios, ensure_ascii=False, indent=2)


@mcp.tool()
def detalhar_usuario(usuario_id: int) -> str:
    """
    Detalha um usuário, incluindo os projetos de que participa e com qual papel.

    Args:
        usuario_id: ID do usuário.
    """
    try:
        data = _request("GET", f"/users/{usuario_id}.json?include=memberships,groups")
    except Exception as exc:
        return f"Erro ao detalhar usuário #{usuario_id}: {_erro_redmine(exc)}"
    return json.dumps(data.get("user", {}), ensure_ascii=False, indent=2)


@mcp.tool()
def listar_papeis() -> str:
    """Lista os papéis (roles) da instância, com seus IDs."""
    data = _request("GET", "/roles.json")
    papeis = [{"id": p["id"], "nome": p["name"]} for p in data.get("roles", [])]
    return json.dumps(papeis, ensure_ascii=False, indent=2)


@mcp.tool()
def detalhar_papel(papel_id: int) -> str:
    """
    Detalha um papel, incluindo a lista completa de permissões concedidas.

    Serve para conferir por que uma operação está sendo recusada, antes de
    tentar de novo.

    Args:
        papel_id: ID do papel (use listar_papeis).
    """
    try:
        data = _request("GET", f"/roles/{papel_id}.json")
    except Exception as exc:
        return f"Erro ao detalhar papel #{papel_id}: {_erro_redmine(exc)}"
    return json.dumps(data.get("role", {}), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Busca e consultas salvas
# ---------------------------------------------------------------------------


@mcp.tool()
def buscar(
    termo: str,
    projeto_identifier: str = "",
    apenas_titulos: bool = False,
    apenas_abertas: bool = False,
    todas_as_palavras: bool = True,
    limite: int = 25,
) -> str:
    """
    Busca por texto em issues, wiki, notícias e demais objetos do Redmine.

    Args:
        termo: texto a procurar.
        projeto_identifier: restringe a um projeto (vazio = toda a instância).
        apenas_titulos: procura só em títulos, não no corpo.
        apenas_abertas: restringe a issues abertas.
        todas_as_palavras: exige todas as palavras do termo; False = qualquer uma.
        limite: número máximo de resultados.
    """
    params = {"q": termo, "limit": limite}
    if apenas_titulos:
        params["titles_only"] = 1
    if apenas_abertas:
        params["open_issues"] = 1
    if todas_as_palavras:
        params["all_words"] = 1

    caminho = "/search.json"
    if projeto_identifier:
        caminho = f"/projects/{projeto_identifier}/search.json"

    try:
        data = _request("GET", caminho, params=params)
    except Exception as exc:
        return f"Erro na busca por '{termo}': {_erro_redmine(exc)}"

    resultados = [
        {
            "id": r.get("id"),
            "tipo": r.get("type"),
            "titulo": r.get("title"),
            "url": r.get("url"),
            "data": r.get("datetime"),
        }
        for r in data.get("results", [])
    ]
    return json.dumps(
        {"total": data.get("total_count"), "resultados": resultados},
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def listar_consultas(projeto_identifier: str = "") -> str:
    """
    Lista as consultas salvas (filtros) visíveis para o usuário da API key.

    Args:
        projeto_identifier: filtra as consultas de um projeto (vazio = todas).
    """
    params = {"limit": 100}
    if projeto_identifier:
        params["project_id"] = projeto_identifier

    data = _request("GET", "/queries.json", params=params)
    consultas = [
        {
            "id": c["id"],
            "nome": c["name"],
            "publica": c.get("is_public"),
            "projeto_id": c.get("project_id"),
        }
        for c in data.get("queries", [])
    ]
    return json.dumps(consultas, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Observadores, comentários e notícias
# ---------------------------------------------------------------------------


@mcp.tool()
def adicionar_observador(issue_id: int, usuario_id: int) -> str:
    """
    Adiciona um observador (watcher) a uma issue.

    Args:
        issue_id: ID da issue.
        usuario_id: ID do usuário a observar (use listar_usuarios).
    """
    try:
        _request("POST", f"/issues/{issue_id}/watchers.json", json={"user_id": usuario_id})
    except Exception as exc:
        return f"Erro ao adicionar observador em #{issue_id}: {_erro_redmine(exc)}"
    return f"Usuário #{usuario_id} passou a observar a issue #{issue_id}."


@mcp.tool()
def remover_observador(issue_id: int, usuario_id: int) -> str:
    """
    Remove um observador de uma issue.

    Args:
        issue_id: ID da issue.
        usuario_id: ID do usuário a remover.
    """
    try:
        _request("DELETE", f"/issues/{issue_id}/watchers/{usuario_id}.json")
    except Exception as exc:
        return f"Erro ao remover observador de #{issue_id}: {_erro_redmine(exc)}"
    return f"Usuário #{usuario_id} deixou de observar a issue #{issue_id}."


@mcp.tool()
def atualizar_comentario(comentario_id: int, texto: str) -> str:
    """
    Edita o texto de um comentário já postado no histórico de uma issue.

    O ID do comentário é o campo 'id' de cada entrada em 'journals', visível em
    detalhar_issue — não confundir com o ID da issue.

    Este endpoint é marcado como alpha na documentação do Redmine e pode não
    existir em versões mais antigas; se falhar com 404, é esse o motivo.

    Args:
        comentario_id: ID da entrada de histórico (journal).
        texto: novo texto do comentário.
    """
    try:
        _request("PUT", f"/journals/{comentario_id}.json", json={"journal": {"notes": texto}})
    except Exception as exc:
        return f"Erro ao editar comentário #{comentario_id}: {_erro_redmine(exc)}"
    return f"Comentário #{comentario_id} atualizado."


@mcp.tool()
def listar_noticias(projeto_identifier: str = "", limite: int = 25) -> str:
    """
    Lista notícias do Redmine.

    Args:
        projeto_identifier: restringe a um projeto (vazio = todos).
        limite: número máximo de notícias.
    """
    caminho = "/news.json"
    if projeto_identifier:
        caminho = f"/projects/{projeto_identifier}/news.json"

    data = _request("GET", caminho, params={"limit": limite})
    noticias = [
        {
            "id": n["id"],
            "titulo": n.get("title"),
            "resumo": n.get("summary"),
            "autor": n.get("author", {}).get("name"),
            "projeto": n.get("project", {}).get("name"),
            "criada_em": n.get("created_on"),
        }
        for n in data.get("news", [])
    ]
    return json.dumps(noticias, ensure_ascii=False, indent=2)


@mcp.tool()
def criar_noticia(
    projeto_identifier: str,
    titulo: str,
    descricao: str,
    resumo: str = "",
) -> str:
    """
    Publica uma notícia em um projeto.

    Notícia é conteúdo visível a todos os membros do projeto e dispara
    notificação por e-mail conforme a configuração da instância.

    Args:
        projeto_identifier: identificador do projeto.
        titulo: título da notícia.
        descricao: corpo da notícia.
        resumo: linha de resumo exibida na listagem.
    """
    noticia = {"title": titulo, "description": descricao}
    if resumo:
        noticia["summary"] = resumo

    try:
        data = _request(
            "POST",
            f"/projects/{projeto_identifier}/news.json",
            json={"news": noticia},
        )
    except Exception as exc:
        return f"Erro ao criar notícia: {_erro_redmine(exc)}"

    if data:
        return json.dumps(data.get("news", {}), ensure_ascii=False, indent=2)
    return f"Notícia '{titulo}' publicada em '{projeto_identifier}'."


# ---------------------------------------------------------------------------
# Anexos
# ---------------------------------------------------------------------------

# Limite defensivo. O Redmine tem o seu próprio, configurável em
# Administração -> Configurações -> Arquivos; este aqui só evita descobrir o
# limite depois de empurrar dezenas de megabytes pela rede.
_TAMANHO_MAXIMO_UPLOAD = 50 * 1024 * 1024


def _enviar_binario(caminho: str, nome_arquivo: str = "") -> tuple:
    """
    Envia um arquivo para /uploads.json e devolve (token, nome, tipo_mime).

    Não passa pelo _request porque o upload exige Content-Type
    application/octet-stream, enquanto o HEADERS global fixa application/json.

    O caminho é resolvido na máquina onde este servidor MCP roda — não na do
    agente que chama a ferramenta.
    """
    if not os.path.isfile(caminho):
        raise RuntimeError(f"arquivo não encontrado: {caminho}")

    tamanho = os.path.getsize(caminho)
    if tamanho > _TAMANHO_MAXIMO_UPLOAD:
        mb = tamanho / (1024 * 1024)
        raise RuntimeError(
            f"arquivo tem {mb:.1f} MB, acima do limite de "
            f"{_TAMANHO_MAXIMO_UPLOAD // (1024 * 1024)} MB deste servidor"
        )
    if tamanho == 0:
        raise RuntimeError("arquivo vazio — o Redmine recusa upload de 0 byte")

    nome = nome_arquivo or os.path.basename(caminho)
    tipo = mimetypes.guess_type(nome)[0] or "application/octet-stream"

    cabecalhos = {
        "X-Redmine-API-Key": REDMINE_API_KEY,
        "Content-Type": "application/octet-stream",
    }

    try:
        with open(caminho, "rb") as arquivo:
            resp = requests.post(
                f"{REDMINE_URL}/uploads.json",
                headers=cabecalhos,
                data=arquivo,
                timeout=120,
            )
    except requests.RequestException as exc:
        raise RuntimeError(f"falha de rede no upload: {exc}") from None
    except OSError as exc:
        raise RuntimeError(f"não consegui ler o arquivo: {exc}") from None

    if not resp.ok:
        raise RuntimeError(_erro_resposta(resp))

    token = resp.json().get("upload", {}).get("token")
    if not token:
        raise RuntimeError("o Redmine aceitou o upload mas não devolveu token")

    return token, nome, tipo


@mcp.tool()
def anexar_arquivo_issue(
    issue_id: int,
    caminho_arquivo: str,
    descricao: str = "",
    comentario: str = "",
    nome_arquivo: str = "",
) -> str:
    """
    Anexa um arquivo local a uma issue.

    Faz o upload e vincula à issue em seguida — as duas etapas que a API do
    Redmine exige, numa chamada só.

    O caminho é lido na máquina onde este servidor MCP roda.

    Args:
        issue_id: ID da issue.
        caminho_arquivo: caminho completo do arquivo na máquina do servidor.
        descricao: descrição do anexo, exibida ao lado do nome.
        comentario: nota a acrescentar no histórico junto com o anexo.
        nome_arquivo: nome a exibir no Redmine (vazio = usa o nome do arquivo).
    """
    try:
        token, nome, tipo = _enviar_binario(caminho_arquivo, nome_arquivo)
    except Exception as exc:
        return f"Erro no upload: {_erro_redmine(exc)}"

    anexo = {"token": token, "filename": nome, "content_type": tipo}
    if descricao:
        anexo["description"] = descricao

    issue = {"uploads": [anexo]}
    if comentario:
        issue["notes"] = comentario

    try:
        _request("PUT", f"/issues/{issue_id}.json", json={"issue": issue})
    except Exception as exc:
        return (
            f"Upload de '{nome}' funcionou, mas falhou ao vincular à issue "
            f"#{issue_id}: {_erro_redmine(exc)}. O token expira sozinho."
        )

    return f"'{nome}' ({tipo}) anexado à issue #{issue_id}."


@mcp.tool()
def detalhar_anexo(anexo_id: int) -> str:
    """
    Detalha um anexo: nome, tamanho, tipo, autor e URL de download.

    Args:
        anexo_id: ID do anexo (aparece em detalhar_issue, na lista 'attachments').
    """
    try:
        data = _request("GET", f"/attachments/{anexo_id}.json")
    except Exception as exc:
        return f"Erro ao detalhar anexo #{anexo_id}: {_erro_redmine(exc)}"

    a = data.get("attachment", {})
    return json.dumps(
        {
            "id": a.get("id"),
            "nome": a.get("filename"),
            "tamanho_bytes": a.get("filesize"),
            "tipo": a.get("content_type"),
            "descricao": a.get("description"),
            "autor": a.get("author", {}).get("name"),
            "criado_em": a.get("created_on"),
            "url": a.get("content_url"),
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def excluir_anexo(anexo_id: int) -> str:
    """
    Exclui um anexo permanentemente. O arquivo sai do disco do servidor.

    Args:
        anexo_id: ID do anexo.
    """
    try:
        _request("DELETE", f"/attachments/{anexo_id}.json")
    except Exception as exc:
        return f"Erro ao excluir anexo #{anexo_id}: {_erro_redmine(exc)}"
    return f"Anexo #{anexo_id} excluído."


# ---------------------------------------------------------------------------
# Projetos e membros
# ---------------------------------------------------------------------------


@mcp.tool()
def detalhar_projeto(projeto_identifier: str) -> str:
    """
    Detalha um projeto: descrição, módulos habilitados, trackers e categorias.

    Args:
        projeto_identifier: identificador do projeto.
    """
    try:
        data = _request(
            "GET",
            f"/projects/{projeto_identifier}.json?include=trackers,issue_categories,enabled_modules",
        )
    except Exception as exc:
        return f"Erro ao detalhar projeto '{projeto_identifier}': {_erro_redmine(exc)}"
    return json.dumps(data.get("project", {}), ensure_ascii=False, indent=2)


@mcp.tool()
def criar_projeto(
    nome: str,
    identifier: str,
    descricao: str = "",
    projeto_pai_id: int = 0,
    publico: bool = False,
) -> str:
    """
    Cria um projeto.

    Args:
        nome: nome exibido.
        identifier: identificador na URL — minúsculas, números e hífen, imutável
            depois de criado.
        descricao: descrição do projeto.
        projeto_pai_id: ID do projeto pai, para criar como subprojeto.
        publico: se visível a usuários não membros. O padrão aqui é privado,
            mais conservador que o do Redmine.
    """
    projeto = {"name": nome, "identifier": identifier, "is_public": publico}
    if descricao:
        projeto["description"] = descricao
    if projeto_pai_id:
        projeto["parent_id"] = projeto_pai_id

    try:
        data = _request("POST", "/projects.json", json={"project": projeto})
    except Exception as exc:
        return f"Erro ao criar projeto '{nome}': {_erro_redmine(exc)}"

    return json.dumps(data.get("project", {}), ensure_ascii=False, indent=2)


@mcp.tool()
def atualizar_projeto(
    projeto_identifier: str,
    nome: str = "",
    descricao: str = "",
    homepage: str = "",
) -> str:
    """
    Atualiza um projeto. Só altera os campos informados.

    O 'identifier' não pode ser alterado depois da criação — é limitação do
    Redmine, não deste servidor.

    Args:
        projeto_identifier: identificador do projeto.
        nome: novo nome exibido (vazio = não altera).
        descricao: nova descrição (vazio = não altera).
        homepage: URL do projeto (vazio = não altera).
    """
    projeto = {}
    if nome:
        projeto["name"] = nome
    if descricao:
        projeto["description"] = descricao
    if homepage:
        projeto["homepage"] = homepage

    if not projeto:
        return f"Nada a atualizar em '{projeto_identifier}': nenhum campo informado."

    try:
        _request("PUT", f"/projects/{projeto_identifier}.json", json={"project": projeto})
    except Exception as exc:
        return f"Erro ao atualizar projeto '{projeto_identifier}': {_erro_redmine(exc)}"

    return f"Projeto '{projeto_identifier}' atualizado ({', '.join(sorted(projeto))})."


@mcp.tool()
def arquivar_projeto(projeto_identifier: str, arquivar: bool = True) -> str:
    """
    Arquiva ou desarquiva um projeto.

    Projeto arquivado fica somente leitura e some das listagens, sem perder
    nada. É a alternativa reversível à exclusão — que este servidor não expõe
    de propósito, por ser irreversível e levar junto issues, horas e wiki.
    Excluir projeto é operação de tela.

    Args:
        projeto_identifier: identificador do projeto.
        arquivar: True arquiva, False desarquiva.
    """
    acao = "archive" if arquivar else "unarchive"
    try:
        _request("PUT", f"/projects/{projeto_identifier}/{acao}.json")
    except Exception as exc:
        return (
            f"Erro ao {'arquivar' if arquivar else 'desarquivar'} "
            f"'{projeto_identifier}': {_erro_redmine(exc)}"
        )
    return f"Projeto '{projeto_identifier}' {'arquivado' if arquivar else 'desarquivado'}."


@mcp.tool()
def listar_membros_projeto(projeto_identifier: str) -> str:
    """
    Lista os membros de um projeto e os papéis de cada um.

    Args:
        projeto_identifier: identificador do projeto.
    """
    try:
        data = _request("GET", f"/projects/{projeto_identifier}/memberships.json?limit=100")
    except Exception as exc:
        return f"Erro ao listar membros de '{projeto_identifier}': {_erro_redmine(exc)}"

    membros = [
        {
            "id_associacao": m["id"],
            "usuario_ou_grupo": (m.get("user") or m.get("group") or {}).get("name"),
            "usuario_id": (m.get("user") or {}).get("id"),
            "papeis": [p["name"] for p in m.get("roles", [])],
        }
        for m in data.get("memberships", [])
    ]
    return json.dumps(membros, ensure_ascii=False, indent=2)


@mcp.tool()
def adicionar_membro_projeto(
    projeto_identifier: str,
    usuario_id: int,
    papel_ids: list[int],
) -> str:
    """
    Adiciona um usuário como membro de um projeto, com um ou mais papéis.

    Args:
        projeto_identifier: identificador do projeto.
        usuario_id: ID do usuário (use listar_usuarios).
        papel_ids: lista de IDs de papel (use listar_papeis).
    """
    if not papel_ids:
        return "Informe ao menos um papel — membro sem papel não tem permissão nenhuma."

    try:
        data = _request(
            "POST",
            f"/projects/{projeto_identifier}/memberships.json",
            json={"membership": {"user_id": usuario_id, "role_ids": papel_ids}},
        )
    except Exception as exc:
        return f"Erro ao adicionar membro: {_erro_redmine(exc)}"

    return json.dumps(data.get("membership", {}), ensure_ascii=False, indent=2)


@mcp.tool()
def atualizar_membro_projeto(associacao_id: int, papel_ids: list[int]) -> str:
    """
    Substitui os papéis de um membro. A lista informada passa a ser a lista
    completa — papel que não estiver nela é removido.

    Args:
        associacao_id: ID da associação (campo 'id_associacao' em
            listar_membros_projeto), não o ID do usuário.
        papel_ids: nova lista completa de IDs de papel.
    """
    if not papel_ids:
        return "Informe ao menos um papel. Para tirar o acesso, use remover_membro_projeto."

    try:
        _request(
            "PUT",
            f"/memberships/{associacao_id}.json",
            json={"membership": {"role_ids": papel_ids}},
        )
    except Exception as exc:
        return f"Erro ao atualizar associação #{associacao_id}: {_erro_redmine(exc)}"

    return f"Associação #{associacao_id} agora tem os papéis {papel_ids}."


@mcp.tool()
def remover_membro_projeto(associacao_id: int) -> str:
    """
    Remove um membro do projeto.

    O usuário perde acesso, mas o que ele criou permanece — issues, comentários
    e lançamentos de horas continuam registrados em nome dele.

    Args:
        associacao_id: ID da associação (campo 'id_associacao' em
            listar_membros_projeto), não o ID do usuário.
    """
    try:
        _request("DELETE", f"/memberships/{associacao_id}.json")
    except Exception as exc:
        return f"Erro ao remover associação #{associacao_id}: {_erro_redmine(exc)}"
    return f"Associação #{associacao_id} removida."


if __name__ == "__main__":
    mcp.run(transport="stdio")
