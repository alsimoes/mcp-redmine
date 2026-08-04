"""Relations between issues: relates, precedes, blocks, duplicates, and so on."""

from __future__ import annotations

from itertools import pairwise

from mcp_redmine.app import get_client, tool
from mcp_redmine.errors import RedmineError, redmine_error_message
from mcp_redmine.format import dumps

RELATION_TYPES = (
    "relates",  # related to
    "duplicates",  # duplicates
    "duplicated",  # duplicated by
    "blocks",  # blocks
    "blocked",  # blocked by
    "precedes",  # precedes
    "follows",  # follows
    "copied_to",  # copied to
    "copied_from",  # copied from
)

# Only these two accept the delay parameter in Redmine.
DELAY_AWARE_RELATIONS = ("precedes", "follows")


@tool
def list_issue_relations(issue_id: int) -> str:
    """List an issue's relations (precedes, blocks, related to, and so on).

    Args:
        issue_id: issue ID.
    """
    data = get_client().request("GET", f"/issues/{issue_id}/relations.json")
    relations = [
        {
            "id": r["id"],
            "from": r["issue_id"],
            "to": r["issue_to_id"],
            "type": r["relation_type"],
            "delay": r.get("delay"),
        }
        for r in data.get("relations", [])
    ]
    return dumps(relations)


@tool
def create_issue_relation(
    issue_id: int,
    target_issue_id: int,
    relation_type: str = "relates",
    delay: int = 0,
) -> str:
    """Create a relation between two issues.

    Args:
        issue_id: source issue ID.
        target_issue_id: target issue ID.
        relation_type: relates, precedes, follows, blocks, blocked,
            duplicates, duplicated, copied_to, copied_from.
        delay: gap in days; only applies to 'precedes' and 'follows'.

    Warning: 'precedes' and 'follows' are date-driven — creating the relation
    makes Redmine reschedule the following issue, pushing its start date
    forward. Use 'relates' when you only want to link the issues without
    touching dates.
    """
    if relation_type not in RELATION_TYPES:
        return (
            f"Invalid relation type: '{relation_type}'. "
            f"Use one of: {', '.join(RELATION_TYPES)}."
        )

    relation = {"issue_to_id": target_issue_id, "relation_type": relation_type}
    if relation_type in DELAY_AWARE_RELATIONS:
        relation["delay"] = delay

    data = get_client().request(
        "POST", f"/issues/{issue_id}/relations.json", json={"relation": relation}
    )
    return dumps(data.get("relation", {}))


@tool
def delete_issue_relation(relation_id: int) -> str:
    """Delete a relation between issues by the relation's ID.

    Args:
        relation_id: relation ID (from the 'id' field in
            list_issue_relations).
    """
    get_client().request("DELETE", f"/relations/{relation_id}.json")
    return f"Relation #{relation_id} deleted successfully."


@tool
def chain_issues(
    issue_ids: list[int],
    relation_type: str = "precedes",
    delay: int = 0,
) -> str:
    """Chain a list of issues in sequence.

    The first relates to the second, the second to the third, and so on.
    Useful for enforcing the execution order of a set of tasks without
    opening the relations form once per pair.

    Args:
        issue_ids: IDs in the desired order (e.g. [22, 25, 49, 51]).
        relation_type: same set as create_issue_relation. Defaults to
            'precedes'.
        delay: gap in days; only applies to 'precedes' and 'follows'.

    Does not abort on the first error: it tries every pair and reports each
    result. Safe to re-run — Redmine rejects a duplicate relation with 422,
    which shows up as an error for that pair without affecting the others.
    """
    if relation_type not in RELATION_TYPES:
        return (
            f"Invalid relation type: '{relation_type}'. "
            f"Use one of: {', '.join(RELATION_TYPES)}."
        )
    if len(issue_ids) < 2:
        return "Provide at least two issues to chain."

    duplicates = {i for i in issue_ids if issue_ids.count(i) > 1}
    if duplicates:
        return (
            f"Repeated IDs in the list: {sorted(duplicates)}. "
            "An issue cannot appear twice."
        )

    client = get_client()
    results = []
    created = 0
    failed = 0

    for source, target in pairwise(issue_ids):
        relation = {"issue_to_id": target, "relation_type": relation_type}
        if relation_type in DELAY_AWARE_RELATIONS:
            relation["delay"] = delay

        try:
            client.request(
                "POST",
                f"/issues/{source}/relations.json",
                json={"relation": relation},
            )
            results.append({"from": source, "to": target, "result": "ok"})
            created += 1
        except RedmineError as exc:
            results.append(
                {
                    "from": source,
                    "to": target,
                    "result": "error",
                    "detail": redmine_error_message(exc),
                }
            )
            failed += 1

    return dumps(
        {
            "type": relation_type,
            "pairs_attempted": len(issue_ids) - 1,
            "created": created,
            "failed": failed,
            "details": results,
        }
    )
