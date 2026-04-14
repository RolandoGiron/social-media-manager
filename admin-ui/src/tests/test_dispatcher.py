"""Nyquist dispatcher tests for Phase 6 social-publish workflow.

These tests introspect n8n/workflows/social-publish.json as a JSON document.
They do NOT require a running n8n instance, docker, or database — they
verify the CONTRACT of the workflow at the JSON level so a careless edit
(e.g. replacing the HTTP mock with a Set node, or losing SKIP LOCKED)
fails loudly in CI.

Covers VALIDATION.md SOCIAL-02:
  - Skip-locked claim pattern (idempotent dispatcher)
  - MOCK_SOCIAL branch isolation (mock path is HTTP, not Set; Meta API
    unreachable from the mock branch)
"""
from __future__ import annotations

import json
from pathlib import Path

import os

import pytest

# REPO_ROOT env var allows the test to locate the workflow JSON regardless of
# whether it runs on the host or inside a Docker container.
# Inside Docker: set REPO_ROOT=/repo (or wherever the repo is bind-mounted).
# On host: defaults to the repository root derived from the file location.
# The host path is admin-ui/src/tests/test_dispatcher.py -> parents[3] = repo root.
# Inside Docker the mount is /app/tests/test_dispatcher.py -> only 2 levels exist.
_self = Path(__file__).resolve()
_parents = list(_self.parents)
_DEFAULT_REPO_ROOT = _parents[3] if len(_parents) > 3 else _self.parent
REPO_ROOT = Path(os.environ.get("REPO_ROOT", str(_DEFAULT_REPO_ROOT)))
WORKFLOW_PATH = REPO_ROOT / "n8n" / "workflows" / "social-publish.json"


@pytest.fixture(scope="module")
def workflow() -> dict:
    if not WORKFLOW_PATH.exists():
        pytest.skip(
            f"social-publish.json not found at {WORKFLOW_PATH}. "
            "Set REPO_ROOT env var to the repository root to enable these tests."
        )
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _node_by_name(wf: dict, name: str) -> dict | None:
    for n in wf.get("nodes", []):
        if n.get("name") == name:
            return n
    return None


def _sql_of(node: dict) -> str:
    """Return the SQL body of a Postgres Execute Query node."""
    params = node.get("parameters", {}) or {}
    # n8n Postgres node v2 uses `query`; older uses `queryText`. Accept both.
    return params.get("query") or params.get("queryText") or ""


# --- SOCIAL-02: skip-locked claim pattern -----------------------------------

def test_skip_locked_claim_pattern_present(workflow: dict) -> None:
    """Dispatcher MUST use FOR UPDATE SKIP LOCKED on the claim step.

    Without this, the 1-minute cron + webhook path could race and publish
    the same row twice (RESEARCH Pitfall 5).
    """
    claim = _node_by_name(workflow, "Claim Pending Rows")
    assert claim is not None, "Claim Pending Rows node missing"
    sql = _sql_of(claim)
    assert "FOR UPDATE SKIP LOCKED" in sql, (
        "Claim Pending Rows must use FOR UPDATE SKIP LOCKED to be idempotent"
    )
    assert "status = 'scheduled'" in sql, "must filter scheduled rows"
    assert "status = 'publishing'" in sql, "must transition to publishing in same statement"


def test_claim_limit_bounded(workflow: dict) -> None:
    """LIMIT clause prevents a compromised/bugged dispatcher from mass-publishing."""
    claim = _node_by_name(workflow, "Claim Pending Rows")
    assert claim is not None
    sql = _sql_of(claim)
    assert "LIMIT" in sql.upper(), "Claim query must have a LIMIT"


# --- SOCIAL-02: MOCK_SOCIAL branch isolation --------------------------------

def test_mock_mode_gate_exists(workflow: dict) -> None:
    gate = _node_by_name(workflow, "Mock Mode?")
    assert gate is not None, "Mock Mode? IF node missing"


def test_mock_publish_is_http_not_set_node(workflow: dict) -> None:
    """D-17: the mock path MUST be a real HTTP call to an internal webhook,
    NOT a Set node with static JSON. This guarantees the mock path exercises
    the same HTTP node + retry/error wiring as the real Meta API branch.
    """
    mock = _node_by_name(workflow, "Mock Publish Call")
    assert mock is not None, "Mock Publish Call node missing"
    assert mock.get("type") == "n8n-nodes-base.httpRequest", (
        f"Mock Publish Call must be an HTTP Request node, got {mock.get('type')}"
    )
    params = mock.get("parameters", {}) or {}
    url = params.get("url", "")
    assert "mock-social-log" in url, (
        f"Mock Publish Call must POST to /webhook/mock-social-log, got {url}"
    )


def test_mock_log_webhook_entry_exists(workflow: dict) -> None:
    """The internal mock-log endpoint must live in this workflow (or a
    sibling — see plan note). A Webhook node with path='mock-social-log'
    is the simplest valid shape.
    """
    mock_hook = _node_by_name(workflow, "Webhook mock-social-log")
    assert mock_hook is not None, (
        "Webhook mock-social-log entry point missing (required by D-17)"
    )
    params = mock_hook.get("parameters", {}) or {}
    assert params.get("path") == "mock-social-log"


def test_meta_api_nodes_not_reachable_from_mock_branch(workflow: dict) -> None:
    """Meta Graph API HTTP nodes must exist only in the FALSE branch of
    Mock Mode?. A simple contract: no connection edge goes from 'Mock Publish Call'
    to any node whose URL contains 'graph.facebook.com'.
    """
    meta_names = [
        n.get("name")
        for n in workflow.get("nodes", [])
        if "graph.facebook.com" in ((n.get("parameters") or {}).get("url") or "")
    ]
    assert meta_names, "Expected at least one Meta Graph API node in the workflow"

    # Walk connections from Mock Publish Call and ensure none reach a meta node.
    connections = workflow.get("connections", {}) or {}
    visited: set[str] = set()

    def walk(node_name: str) -> None:
        if node_name in visited:
            return
        visited.add(node_name)
        outs = connections.get(node_name, {}).get("main", []) or []
        for out_list in outs:
            for edge in out_list or []:
                target = edge.get("node")
                if target:
                    walk(target)

    walk("Mock Publish Call")
    leaked = [m for m in meta_names if m in visited]
    assert not leaked, (
        f"Mock branch leaks into Meta API nodes: {leaked}. "
        "MOCK_SOCIAL=true must NEVER call Meta Graph API."
    )


# --- Sanity: workflow wiring basics -----------------------------------------

def test_workflow_name_is_social_publish(workflow: dict) -> None:
    assert workflow.get("name") == "social-publish"


def test_no_deprecated_schema_names(workflow: dict) -> None:
    raw = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "scheduled_posts" not in raw, "deprecated table name present (use social_posts)"
    assert "image_path" not in raw, "deprecated column name present (use image_url)"
