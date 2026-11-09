"""Transactional run state with leases, immutable output snapshots, and budgets.

SQLite handles concurrent coordinators; agents write their own task folders only.
Tokens protect against late submissions from expired/retried workers. A lease is
an ownership mechanism, not an operating-system sandbox.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from typing import Any, Iterator

from .contracts import ValidationError, validate_brief, validate_envelope, validate_task
from .pipeline import PIPELINE, TASKS, descendants, ready_tasks
from .util import canonical, digest, file_hash, now, read_json, safe_path, write_json


class StateError(RuntimeError):
    pass


SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tasks (
 id TEXT PRIMARY KEY, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
 owner TEXT, token TEXT, lease_until REAL, input_hash TEXT,
 artifact TEXT, artifact_hash TEXT, error TEXT, updated TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL,
 task_id TEXT, kind TEXT NOT NULL, detail TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS media_jobs (
 job_key TEXT PRIMARY KEY, task_id TEXT NOT NULL, provider TEXT NOT NULL,
 request_hash TEXT NOT NULL, estimated_usd REAL NOT NULL,
 estimated_credits REAL NOT NULL, actual_usd REAL, actual_credits REAL,
 status TEXT NOT NULL, provider_job_id TEXT, files TEXT NOT NULL, created TEXT NOT NULL
);
"""


class Run:
    def __init__(self, directory: Path | str):
        self.path = Path(directory).resolve()
        self.db = self.path / "state.sqlite3"
        if not self.db.is_file(): raise StateError(f"Not a StoryForge run: {self.path}")

    @classmethod
    def create(cls, brief: dict, runs_dir: Path, *, demo: bool = False, project_root: Path | None = None) -> "Run":
        validate_brief(brief)
        slug = re.sub(r"[^a-z0-9]+", "-", brief["project_name"].lower()).strip("-")[:48] or "video"
        run_id = f"{slug}-{uuid4().hex[:10]}"
        path = runs_dir.resolve() / run_id
        path.mkdir(parents=True, exist_ok=False)
        for folder in ("tasks", "artifacts", "media", "delivery", "logs"):
            (path / folder).mkdir()
        write_json(path / "brief.json", brief)
        conn = sqlite3.connect(path / "state.sqlite3")
        try:
            conn.executescript(SCHEMA)
            values = {"run_id": run_id, "brief": brief, "brief_hash": digest(brief), "demo": demo,
                      "created_at": now(), "worker_calls": 0, "schema_version": "1.0"}
            if project_root is not None:
                values["project_root"] = str(project_root.expanduser().resolve())
            conn.executemany("INSERT INTO meta VALUES (?, ?)", [(k, canonical(v)) for k, v in values.items()])
            conn.executemany("INSERT INTO tasks(id,status,updated) VALUES (?,?,?)", [(t.id, "pending", now()) for t in PIPELINE])
            conn.commit()
        finally: conn.close()
        return cls(path)

    def project_root(self) -> Path | None:
        """Remember the originating project when runs use an external directory.

        Older/standalone runs have no binding and continue to resolve by their
        ancestry. This is read-only metadata access; no lease is acquired.
        """
        conn = sqlite3.connect(self.db)
        try:
            row = conn.execute("SELECT value FROM meta WHERE key='project_root'").fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        value = json.loads(row[0])
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise StateError("Saved project origin is invalid for this run")
        return Path(value)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally: conn.close()

    @staticmethod
    def _meta(c: sqlite3.Connection, key: str) -> Any:
        row = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        if row is None: raise StateError(f"Missing run metadata: {key}")
        return json.loads(row["value"])

    @staticmethod
    def _event(c: sqlite3.Connection, task: str | None, kind: str, detail: Any) -> None:
        c.execute("INSERT INTO events(at,task_id,kind,detail) VALUES (?,?,?,?)", (now(), task, kind, canonical(detail)))

    @staticmethod
    def _rows(c: sqlite3.Connection) -> dict[str, dict]:
        return {row["id"]: dict(row) for row in c.execute("SELECT * FROM tasks")}

    @staticmethod
    def _outputs(rows: dict[str, dict]) -> dict[str, dict]:
        return {k: json.loads(v["artifact"])["result"] for k, v in rows.items() if v["artifact"]}

    def _audit(self, c: sqlite3.Connection, rows: dict[str, dict]) -> None:
        if digest(read_json(self.path / "brief.json")) != self._meta(c, "brief_hash"):
            raise StateError("brief.json changed. Use amend --brief FILE to invalidate prior work deliberately.")
        for task_id, row in rows.items():
            if row["status"] != "complete": continue
            stored = json.loads(row["artifact"])
            for relative, expected in stored["file_hashes"].items():
                try:
                    actual = file_hash(safe_path(self.path, relative))
                except (ValueError, OSError): actual = None
                if actual != expected:
                    raise StateError(f"Completed artifact changed: {relative}. Invalidate {task_id} and its dependents before resubmitting.")

    def _input_hash(self, c: sqlite3.Connection, rows: dict[str, dict], task_id: str) -> str:
        from .studio_gates import enabled, TASK_GATES, status as studio_status
        decision = None
        if enabled(self._meta(c, "brief")) and task_id in TASK_GATES:
            gate = TASK_GATES[task_id]
            decision = next((g["choice"] for g in studio_status(c, rows, self.path, self._meta(c, "brief"))
                             if g["gate"] == gate and g["status"] == "approved"), None)
        return digest({"brief": self._meta(c, "brief_hash"), "contract": "1.0",
                       "dependencies": {d: rows[d]["artifact_hash"] for d in TASKS[task_id].needs},
                       **({"human_selection": decision} if decision is not None else {})})

    def status(self) -> dict:
        with self.transaction() as c:
            rows = self._rows(c)
            self._audit(c, rows)
            jobs = [dict(j) for j in c.execute("SELECT * FROM media_jobs ORDER BY created")]
            counts = {s: sum(v["status"] == s for v in rows.values()) for s in ("pending", "running", "complete", "blocked", "failed")}
            from .studio_gates import status as studio_status, TASK_GATES
            gates = studio_status(c, rows, self.path, self._meta(c, "brief"))
            gated = {task for task, gate in TASK_GATES.items()
                     if any(g["gate"] == gate and g["status"] != "approved" for g in gates)}
            ready = [task for task in ready_tasks({k: v["status"] for k, v in rows.items()}) if task not in gated]
            packaged = rows["package"]["status"] == "complete" and not self._meta(c, "demo")
            finished = packaged and not any(g["gate"] == "final" and g["status"] != "approved" for g in gates)
            return {"run_id": self._meta(c, "run_id"), "path": str(self.path), "demo": self._meta(c, "demo"),
                    "counts": counts, "ready": ready, "gates": gates, "packaged": packaged,
                    "worker_calls": self._meta(c, "worker_calls"), "budget": self._meta(c, "brief")["budget"],
                    "tasks": [{k: v[k] for k in ("id", "status", "attempts", "owner", "lease_until", "error")} for v in rows.values()],
                    "media_jobs": [{k: j[k] for k in ("job_key", "task_id", "provider", "status", "provider_job_id", "estimated_usd", "estimated_credits", "actual_usd", "actual_credits")} for j in jobs],
                    "delivered": finished}

    def approve_studio_gate(self, gate: str, choice: str, evidence: str, actor: str = "human-owner") -> dict:
        from .studio_gates import approve
        with self.transaction() as c:
            rows = self._rows(c)
            self._audit(c, rows)
            result = approve(c, rows, self.path, self._meta(c, "brief"), gate, choice, evidence, actor)
            self._event(c, result["source_task"], "human_gate_approved",
                        {"gate": gate, "choice": choice, "source_hash": result["source_hash"], "actor": actor})
            return result

    def context(self, task_id: str) -> dict:
        if task_id not in TASKS: raise StateError(f"Unknown task {task_id}")
        with self.transaction() as c:
            rows = self._rows(c)
            self._audit(c, rows)
            media_jobs = [{**dict(job), "files": json.loads(job["files"])} for job in c.execute(
                "SELECT * FROM media_jobs WHERE task_id=? ORDER BY created, job_key", (task_id,))]
            from .studio_gates import status as studio_status
            return {"run_id": self._meta(c, "run_id"), "run_dir": str(self.path), "demo": self._meta(c, "demo"),
                    "brief": self._meta(c, "brief"), "task_id": task_id, "task": rows[task_id],
                    "dependencies": self._outputs(rows), "media_jobs": media_jobs,
                    "studio_gates": studio_status(c, rows, self.path, self._meta(c, "brief"))}

    def claim(self, task_id: str, owner: str, *, lease_seconds: int = 1200, model_call: bool = False) -> dict:
        if task_id not in TASKS: raise StateError(f"Unknown task {task_id}")
        if not owner.strip(): raise StateError("Worker name cannot be empty")
        if not 10 <= lease_seconds <= 86400: raise StateError("Lease must be between 10 and 86400 seconds")
        with self.transaction() as c:
            rows = self._rows(c)
            self._audit(c, rows)
            ready = ready_tasks({k: v["status"] for k, v in rows.items()})
            if task_id not in ready: raise StateError(f"Task {task_id} is not ready; ready tasks: {', '.join(ready) or 'none'}")
            from .studio_gates import guard
            guard(c, rows, self.path, self._meta(c, "brief"), task_id)
            brief = self._meta(c, "brief")
            max_attempts = 1 + brief["budget"]["max_retries_per_task"]
            if rows[task_id]["attempts"] >= max_attempts: raise StateError(f"Retry budget exhausted for {task_id}")
            if self._meta(c, "demo") and TASKS[task_id].production:
                raise StateError("Offline fixtures stop before production. Create a real run to generate media.")
            if model_call:
                calls = self._meta(c, "worker_calls")
                if calls >= brief["budget"]["max_model_calls"]: raise StateError("Worker invocation budget exhausted")
                c.execute("UPDATE meta SET value=? WHERE key='worker_calls'", (canonical(calls+1),))
            token = uuid4().hex
            expiry = time.time() + lease_seconds
            attempt = rows[task_id]["attempts"] + 1
            input_hash = self._input_hash(c, rows, task_id)
            c.execute("UPDATE tasks SET status='running', attempts=?, owner=?, token=?, lease_until=?, input_hash=?, error=NULL, updated=? WHERE id=?",
                      (attempt, owner, token, expiry, input_hash, now(), task_id))
            self._event(c, task_id, "claimed", {"owner": owner, "attempt": attempt, "input_hash": input_hash})
            workspace = self.path / "tasks" / task_id / f"attempt-{attempt}"
            workspace.mkdir(parents=True, exist_ok=False)
            return {"task_id": task_id, "token": token, "lease_until": expiry, "workspace": str(workspace), "attempt": attempt}

    def heartbeat(self, task_id: str, token: str, lease_seconds: int = 1200) -> dict:
        if not 10 <= lease_seconds <= 86400: raise StateError("Lease must be 10–86400 seconds")
        with self.transaction() as c:
            row = self._rows(c).get(task_id)
            self._check_lease(row, token)
            until = time.time() + lease_seconds
            c.execute("UPDATE tasks SET lease_until=?,updated=? WHERE id=?", (until, now(), task_id))
            return {"task_id": task_id, "lease_until": until}

    @staticmethod
    def _check_lease(row: dict | None, token: str) -> None:
        if not row or row["status"] != "running" or row["token"] != token:
            raise StateError("Task lease token is stale or does not own the running task")
        if row["lease_until"] < time.time(): raise StateError("Task lease expired. Resume, then claim a new attempt.")

    def submit(self, task_id: str, token: str, result: dict) -> dict:
        with self.transaction() as c:
            rows = self._rows(c)
            row = rows.get(task_id)
            self._check_lease(row, token)
            self._audit(c, rows)
            if row["input_hash"] != self._input_hash(c, rows, task_id): raise StateError("Task inputs changed while worker was running")
            e = validate_envelope(result, self._meta(c, "run_id"), task_id, self.path)
            if not e:
                try:
                    e = validate_task(task_id, result, self._meta(c, "brief"), self._outputs(rows), self.path, demo=self._meta(c, "demo"))
                except (TypeError, KeyError, IndexError, AttributeError, ValueError) as ex:
                    e = [f"Malformed task data: {type(ex).__name__}: {ex}"]
            if not e and task_id in {"research", "viability"} and result["status"] == "complete":
                from .studio_gates import enabled, status as studio_status
                brief = self._meta(c, "brief")
                if enabled(brief):
                    chosen = next(g["choice"] for g in studio_status(c, rows, self.path, brief) if g["gate"] == "niche")
                    if result.get("data", {}).get("selected_candidate_id") != chosen:
                        e.append("data.selected_candidate_id must equal the human-approved niche choice")
            if e:
                c.execute("UPDATE tasks SET status='blocked', error=?,token=NULL,lease_until=NULL,updated=? WHERE id=?", (canonical(e), now(), task_id))
                self._event(c, task_id, "validation_failed", e)
                rejected = self.path / "artifacts" / f"{task_id}.rejected-{row['attempts']}.json"
                write_json(rejected, {"errors": e, "result": result})
                return {"accepted": False, "task_id": task_id, "status": "blocked", "errors": e}
            status = result["status"]
            stored = {"result": result, "file_hashes": {f: file_hash(safe_path(self.path, f)) for f in result["files"]}, "input_hash": row["input_hash"]}
            artifact_hash = digest(stored)
            snapshot = self.path / "artifacts" / f"{task_id}.attempt-{row['attempts']}.json"
            write_json(snapshot, stored)
            c.execute("UPDATE tasks SET status=?,artifact=?,artifact_hash=?,error=?,token=NULL,lease_until=NULL,updated=? WHERE id=?",
                      (status, canonical(stored), artifact_hash, canonical(result["blockers"]) if status == "blocked" else None, now(), task_id))
            self._event(c, task_id, status, {"artifact_hash": artifact_hash, "snapshot": str(snapshot.relative_to(self.path))})
            return {"accepted": status == "complete", "task_id": task_id, "status": status, "artifact_hash": artifact_hash,
                    "blockers": result["blockers"]}

    def fail(self, task_id: str, token: str, reason: str) -> None:
        with self.transaction() as c:
            row = self._rows(c).get(task_id)
            if not row or row["status"] != "running" or row["token"] != token:
                raise StateError("Cannot fail task owned by another lease")
            c.execute("UPDATE tasks SET status='failed',error=?,token=NULL,lease_until=NULL,updated=? WHERE id=?", (reason[:4000], now(), task_id))
            self._event(c, task_id, "failed", reason[:4000])

    def resume(self) -> list[str]:
        recovered: list[str] = []
        with self.transaction() as c:
            max_attempts = 1 + self._meta(c, "brief")["budget"]["max_retries_per_task"]
            for task, row in self._rows(c).items():
                if row["status"] == "running" and row["lease_until"] < time.time():
                    state = "pending" if row["attempts"] < max_attempts else "failed"
                    c.execute("UPDATE tasks SET status=?,owner=NULL,token=NULL,lease_until=NULL,error=?,updated=? WHERE id=?",
                              (state, "Lease expired; inspect existing provider jobs before retrying media", now(), task))
                    self._event(c, task, "lease_expired", {"next_status": state})
                    recovered.append(task)
        return recovered

    def retry(self, task_id: str) -> None:
        with self.transaction() as c:
            rows = self._rows(c)
            row = rows.get(task_id)
            if not row or row["status"] not in {"failed", "blocked"}: raise StateError("Only failed or blocked tasks can retry")
            if row["attempts"] >= 1 + self._meta(c, "brief")["budget"]["max_retries_per_task"]: raise StateError("Retry budget exhausted")
            c.execute("UPDATE tasks SET status='pending',owner=NULL,token=NULL,lease_until=NULL,artifact=NULL,artifact_hash=NULL,error=NULL,updated=? WHERE id=?", (now(), task_id))
            self._event(c, task_id, "retry_requested", {})

    def invalidate(self, task_id: str, reason: str) -> list[str]:
        selected = descendants(task_id)
        if not reason.strip(): raise StateError("Invalidation requires a reason")
        with self.transaction() as c:
            from .studio_gates import revoke
            revoke(c, selected)
            # Revoke running leases. Late workers cannot submit over the new state.
            for task in selected:
                c.execute("UPDATE tasks SET status='pending',owner=NULL,token=NULL,lease_until=NULL,input_hash=NULL,artifact=NULL,artifact_hash=NULL,error=NULL,updated=? WHERE id=?", (now(), task))
                self._event(c, task, "invalidated", {"root": task_id, "reason": reason})
        return sorted(selected)

    def amend(self, brief: dict) -> None:
        validate_brief(brief)
        with self.transaction() as c:
            if any(r["status"] == "running" for r in self._rows(c).values()): raise StateError("Stop or finish running tasks before amending the brief")
            write_json(self.path / "brief.json", brief)
            c.execute("UPDATE meta SET value=? WHERE key='brief'", (canonical(brief),))
            c.execute("UPDATE meta SET value=? WHERE key='brief_hash'", (canonical(digest(brief)),))
            c.execute("UPDATE tasks SET status='pending',owner=NULL,token=NULL,lease_until=NULL,input_hash=NULL,artifact=NULL,artifact_hash=NULL,error=NULL,updated=?", (now(),))
            from .studio_gates import revoke
            revoke(c, set(TASKS))
            self._event(c, None, "brief_amended", {"brief_hash": digest(brief), "note": "Attempts and usage retained"})

    def reserve_media(self, task_id: str, token: str, *, job_key: str, provider: str, request: dict,
                      estimated_usd: float, estimated_credits: float) -> dict:
        from .contracts import number
        if not re.fullmatch(r"[a-zA-Z0-9_-]{3,100}", job_key): raise StateError("Job key must be 3–100 safe characters")
        if not provider.strip() or not isinstance(request, dict): raise StateError("Provider and request object required")
        if not number(estimated_usd) or not number(estimated_credits) or min(estimated_usd, estimated_credits) < 0:
            raise StateError("Media estimates must be known nonnegative values; unknown is not zero")
        with self.transaction() as c:
            rows = self._rows(c)
            self._check_lease(rows.get(task_id), token)
            self._audit(c, rows)
            if task_id not in {"voice", "sound", "assets_images", "assets_3d"}: raise StateError("Media jobs must belong to an asset/voice/sound task")
            if rows["preflight"]["status"] != "complete": raise StateError("Production preflight has not passed")
            existing = c.execute("SELECT * FROM media_jobs WHERE job_key=?", (job_key,)).fetchone()
            fingerprint = digest({"task_id": task_id, "provider": provider, "request": request})
            if existing:
                if existing["request_hash"] != fingerprint: raise StateError("Idempotency key reused for a different request")
                return {**dict(existing), "reused": True, "may_generate": False}
            unresolved = c.execute("SELECT job_key,status FROM media_jobs WHERE request_hash=? AND status IN ('reserved','submitted','uncertain')", (fingerprint,)).fetchone()
            if unresolved:
                raise StateError(f"Identical media request already has unresolved job {unresolved['job_key']} ({unresolved['status']}); recover it before creating another key")
            budget = self._meta(c, "brief")["budget"]
            jobs = [dict(j) for j in c.execute("SELECT * FROM media_jobs")]
            reserved_usd = sum(j["actual_usd"] if j["actual_usd"] is not None else j["estimated_usd"] for j in jobs)
            reserved_credits = sum(j["actual_credits"] if j["actual_credits"] is not None else j["estimated_credits"] for j in jobs)
            if len(jobs) >= budget["max_media_jobs"]: raise StateError("Media job cap exhausted")
            if reserved_usd + estimated_usd > budget["max_media_cost_usd"] + 1e-8: raise StateError("Media USD budget exceeded")
            if reserved_credits + estimated_credits > budget["max_media_credits"] + 1e-8: raise StateError("Media credit budget exceeded")
            c.execute("INSERT INTO media_jobs(job_key,task_id,provider,request_hash,estimated_usd,estimated_credits,status,files,created) VALUES (?,?,?,?,?,?,?,?,?)",
                      (job_key, task_id, provider, fingerprint, estimated_usd, estimated_credits, "reserved", "[]", now()))
            self._event(c, task_id, "media_reserved", {"job_key": job_key, "provider": provider, "estimated_usd": estimated_usd, "estimated_credits": estimated_credits})
            return {"job_key": job_key, "status": "reserved", "reused": False, "may_generate": True}

    def record_media(self, job_key: str, *, status: str, provider_job_id: str | None = None,
                     actual_usd: float | None = None, actual_credits: float | None = None, files: list[str] | None = None) -> dict:
        from .contracts import number
        if status not in {"submitted", "complete", "failed", "uncertain"}: raise StateError("Invalid media job status")
        if status in {"submitted", "complete"} and (not isinstance(provider_job_id, str) or not provider_job_id.strip()):
            raise StateError("Record actual provider job/request ID before completion")
        for cost in (actual_usd, actual_credits):
            if cost is not None and (not number(cost) or cost < 0): raise StateError("Actual costs must be nonnegative or unknown")
        files = files or []
        for f in files: safe_path(self.path, f)
        if status == "complete" and not files: raise StateError("Completed media job must have actual output files")
        with self.transaction() as c:
            row = c.execute("SELECT * FROM media_jobs WHERE job_key=?", (job_key,)).fetchone()
            if not row: raise StateError("Unknown media reservation")
            if row["provider_job_id"] and provider_job_id and row["provider_job_id"] != provider_job_id: raise StateError("Reservation already belongs to a different provider job")
            if row["status"] == "complete" and status != "complete": raise StateError("Cannot downgrade a completed media job")
            c.execute("UPDATE media_jobs SET status=?,provider_job_id=COALESCE(?,provider_job_id),actual_usd=COALESCE(?,actual_usd),actual_credits=COALESCE(?,actual_credits),files=? WHERE job_key=?",
                      (status, provider_job_id, actual_usd, actual_credits, canonical(files), job_key))
            self._event(c, row["task_id"], "media_updated", {"job_key": job_key, "status": status, "provider_job_id": provider_job_id})
            return {"job_key": job_key, "status": status, "note": "Unknown/failed jobs retain reservation; inspect provider before any retry"}

    def events(self) -> list[dict]:
        with self.transaction() as c:
            return [{**dict(row), "detail": json.loads(row["detail"])} for row in c.execute("SELECT * FROM events ORDER BY sequence")]
