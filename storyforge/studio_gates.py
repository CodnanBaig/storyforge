"""Opt-in, hash-bound human decisions for StoryForge Studio.

This journal tracks explicit owner decisions; it is not user authentication.
Never call approve on a user's behalf without a concrete human decision.
"""
from __future__ import annotations

import json
from pathlib import Path

from .util import now, safe_path

PROFILE = "unified_studio_v1"
GATE_SOURCES = {"niche": "discovery", "visual": "style", "script": "script", "final": "package"}
TASK_GATES = {"research": "niche", "viability": "niche", "direction": "visual", "preflight": "script"}
DDL = """CREATE TABLE IF NOT EXISTS studio_approvals (
 gate TEXT PRIMARY KEY, source_task TEXT NOT NULL, source_hash TEXT NOT NULL,
 choice TEXT NOT NULL, actor TEXT NOT NULL, evidence TEXT NOT NULL,
 approved_at TEXT NOT NULL
)"""


def enabled(brief: dict) -> bool:
    return brief.get("constraints", {}).get("workflow_profile") == PROFILE


def _source(rows: dict, gate: str) -> tuple[str, dict] | None:
    row = rows[GATE_SOURCES[gate]]
    if row["status"] != "complete" or not row["artifact_hash"] or not row["artifact"]:
        return None
    return row["artifact_hash"], json.loads(row["artifact"])["result"]


def choices(rows: dict, gate: str) -> list[str]:
    source = _source(rows, gate)
    if not source:
        return []
    data = source[1].get("data", {})
    if gate == "niche":
        return [x["id"] for x in data.get("candidates", [])
                if isinstance(x, dict) and isinstance(x.get("id"), str)]
    if gate == "visual":
        return [x["id"] for x in data.get("visual_concepts", [])
                if isinstance(x, dict) and isinstance(x.get("id"), str)]
    return ["approve"]


def _files_intact(run_dir: Path, result: dict) -> bool:
    for rel in result.get("files", []):
        try:
            path = safe_path(run_dir, rel)
            if not path.is_file() or path.stat().st_size <= 0:
                return False
        except (OSError, ValueError):
            return False
    return True


def _status(c, rows: dict, gate: str, run_dir: Path) -> dict:
    src = _source(rows, gate)
    options = choices(rows, gate)
    record = c.execute("SELECT * FROM studio_approvals WHERE gate=?", (gate,)).fetchone()
    state = "waiting_for_stage" if src is None else "awaiting_human"
    selected = None
    if record:
        selected = record["choice"]
        if src and record["source_hash"] == src[0] and selected in options and _files_intact(run_dir, src[1]):
            state = "approved"
        else:
            state = "stale"
    return {"gate": gate, "source_task": GATE_SOURCES[gate], "status": state,
            "choices": options, "choice": selected, "source_hash": src[0] if src else None,
            "evidence": record["evidence"] if record and state == "approved" else None}


def status(c, rows: dict, run_dir: Path, brief: dict) -> list[dict]:
    if not enabled(brief):
        return []
    c.execute(DDL)
    return [_status(c, rows, name, run_dir) for name in GATE_SOURCES]


def guard(c, rows: dict, run_dir: Path, brief: dict, task_id: str) -> None:
    if not enabled(brief) or task_id not in TASK_GATES:
        return
    from .store import StateError
    gate = TASK_GATES[task_id]
    record = next(g for g in status(c, rows, run_dir, brief) if g["gate"] == gate)
    if record["status"] != "approved":
        raise StateError(f"Human {gate} approval required before {task_id}; gate status: {record['status']}")


def approve(c, rows: dict, run_dir: Path, brief: dict, gate: str,
            choice: str, evidence: str, actor: str) -> dict:
    from .store import StateError
    if not enabled(brief):
        raise StateError(f"Brief must set constraints.workflow_profile={PROFILE}")
    if gate not in GATE_SOURCES:
        raise StateError("Unknown human checkpoint")
    if not isinstance(evidence, str) or len(evidence.strip()) < 8:
        raise StateError("Record a concrete human decision (at least 8 characters)")
    if actor != "human-owner":
        raise StateError("Only human-owner is supported; this value does not authenticate an identity")
    c.execute(DDL)
    src = _source(rows, gate)
    if src is None:
        raise StateError(f"Cannot approve {gate} until {GATE_SOURCES[gate]} is complete")
    options = choices(rows, gate)
    if choice not in options:
        raise StateError(f"Invalid {gate} choice {choice!r}; choose from: {options}")
    if not _files_intact(run_dir, src[1]):
        raise StateError("Source artifacts are missing or empty")
    if gate == "visual":
        concepts = src[1].get("data", {}).get("visual_concepts", [])
        if len(concepts) < 3 or any(not isinstance(x, dict) or
                                   not x.get("code_proof_path") or
                                   x["code_proof_path"] not in src[1].get("files", [])
                                   for x in concepts):
            raise StateError("Visual selection requires three declared code render proof files")
    previous = c.execute("SELECT choice FROM studio_approvals WHERE gate=?", (gate,)).fetchone()
    if previous and previous["choice"] != choice:
        downstream = {"niche": {"research", "viability", "script", "fact_check", "preflight", "direction", "edit", "package"},
                      "visual": {"direction", "preflight", "edit", "package"},
                      "script": {"preflight", "edit", "package"}, "final": set()}[gate]
        if any(rows[task]["status"] != "pending" for task in downstream):
            raise StateError("Choice changed after production began; invalidate affected work first")
    c.execute("INSERT OR REPLACE INTO studio_approvals (gate,source_task,source_hash,choice,actor,evidence,approved_at) VALUES (?,?,?,?,?,?,?)",
              (gate, GATE_SOURCES[gate], src[0], choice, actor, evidence.strip(), now()))
    return _status(c, rows, gate, run_dir)


def revoke(c, tasks: set[str]) -> None:
    c.execute(DDL)
    for source in sorted(tasks.intersection(GATE_SOURCES.values())):
        c.execute("DELETE FROM studio_approvals WHERE source_task=?", (source,))
