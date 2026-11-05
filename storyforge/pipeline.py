"""The dependency graph is shared by interactive hosts and subprocess workers."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    id: str
    role: str
    needs: tuple[str, ...] = ()
    production: bool = False


PIPELINE = (
    Task("discovery", "Topic scout"),
    Task("style", "Art director"),
    Task("research", "Researcher", ("discovery",)),
    Task("viability", "Audience analyst", ("discovery",)),
    Task("script", "Screenwriter", ("research", "viability")),
    Task("fact_check", "Independent fact checker", ("script", "research")),
    Task("direction", "Director", ("script", "style")),
    Task("preflight", "Production producer", ("fact_check", "direction", "viability")),
    Task("assets_3d", "Three.js asset artist", ("preflight", "direction", "style"), True),
    Task("assets_images", "Image artist", ("preflight", "direction", "style"), True),
    Task("voice", "Voice director", ("preflight", "script"), True),
    Task("sound", "Sound designer", ("preflight", "direction"), True),
    Task("edit", "Remotion editor", ("assets_3d", "assets_images", "voice", "sound", "direction"), True),
    Task("render", "Render engineer", ("edit",), True),
    Task("qa", "Independent quality reviewer", ("render", "edit", "fact_check", "preflight"), True),
    Task("package", "Release packager", ("qa",), True),
)
TASKS = {t.id: t for t in PIPELINE}


def descendants(task_id: str) -> set[str]:
    if task_id not in TASKS:
        raise ValueError(f"Unknown task: {task_id}")
    selected = {task_id}
    while True:
        new = selected | {t.id for t in PIPELINE if selected.intersection(t.needs)}
        if new == selected:
            return selected
        selected = new


def ready_tasks(states: dict[str, str]) -> list[str]:
    return [t.id for t in PIPELINE if states[t.id] == "pending"
            and all(states[d] == "complete" for d in t.needs)]
