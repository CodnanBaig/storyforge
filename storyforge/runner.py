"""Bounded optional subprocess workers. Interactive hosts use claim/submit instead."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
from threading import Event
from typing import Callable

from .pipeline import TASKS
from .prompts import task_prompt, write_task_packet
from .store import Run, StateError
from .util import ROOT, write_json


def run_pipeline(run: Run, provider: str, *, workers: int = 3, timeout_seconds: int = 900,
                 model: str | None = None, max_turns: int = 20, until: str | None = None,
                 on_event: Callable[[dict], None] = lambda e: None) -> dict:
    from .adapters import adapter_available, run_agent
    if not adapter_available(provider): raise StateError(f"{provider} CLI is unavailable. Use native host claim/submit or install and authenticate that CLI.")
    if not 1 <= workers <= 8: raise StateError("workers must be between 1 and 8")
    if not 30 <= timeout_seconds <= 7200: raise StateError("Worker timeout must be between 30 and 7200 seconds")
    if until is not None and until not in TASKS: raise StateError("Unknown --until task")
    allowed = set(TASKS)
    cancellation = Event()
    if until:
        allowed = {until}
        def parents(task: str) -> None:
            for d in TASKS[task].needs:
                if d not in allowed: allowed.add(d); parents(d)
        parents(until)

    def work(task_id: str, claim: dict) -> dict:
        workspace = Path(claim["workspace"])
        try:
            write_task_packet(run, task_id, workspace)
            answer = run_agent(provider, task_prompt(run, task_id, workspace), workspace,
                               ROOT / "schemas" / "task-result.schema.json",
                               timeout_seconds=timeout_seconds, model=model, max_turns=max_turns, cancel_event=cancellation)
            write_json(workspace / "result.json", answer.payload)
            write_json(workspace / "usage.json", answer.usage)
            # Adapter redacts common credentials before returning logs. Logs stay local.
            (workspace / "worker.stdout.log").write_text(answer.stdout, encoding="utf-8")
            (workspace / "worker.stderr.log").write_text(answer.stderr, encoding="utf-8")
            return run.submit(task_id, claim["token"], answer.payload)
        except Exception as ex:
            reason = f"{type(ex).__name__}: {ex}"
            # AdapterError diagnostics have already been bounded and redacted.
            from .adapters import AdapterError
            if isinstance(ex, AdapterError):
                (workspace / "worker.stdout.log").write_text(ex.stdout, encoding="utf-8")
                (workspace / "worker.stderr.log").write_text(ex.stderr, encoding="utf-8")
            try: run.fail(task_id, claim["token"], reason)
            except StateError: pass  # Revoked lease must not alter another worker's state.
            return {"task_id": task_id, "status": "failed", "error": reason}

    run.resume()
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="storyforge") as pool:
        active: dict = {}
        blocked_launch: set[str] = set()
        try:
            while True:
                status = run.status()
                ready = [t for t in status["ready"] if t in allowed and t not in blocked_launch]
                for task in ready:
                    if len(active) >= workers: break
                    try:
                        claim = run.claim(task, f"{provider}-worker", lease_seconds=timeout_seconds+60, model_call=True)
                    except StateError as ex:
                        on_event({"task_id": task, "status": "not_launched", "error": str(ex)})
                        blocked_launch.add(task)
                        continue
                    on_event({"task_id": task, "status": "running", "attempt": claim["attempt"]})
                    active[pool.submit(work, task, claim)] = task
                if not active: break
                done, _ = wait(active, timeout=1, return_when=FIRST_COMPLETED)
                for future in done:
                    del active[future]
                    on_event(future.result())
        except BaseException:
            cancellation.set()
            for future in active: future.cancel()
            raise
    return run.status()
