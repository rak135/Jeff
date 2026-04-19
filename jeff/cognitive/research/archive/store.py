"""Project-scoped JSON persistence for the research archive layer."""

from __future__ import annotations

import json
from pathlib import Path

from .models import HISTORY_FAMILIES, ResearchArchiveArtifact, artifact_from_payload, artifact_to_payload


class ResearchArchiveStore:
    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def artifacts_dir_for(self, project_id: str) -> Path:
        return self.root_dir / "projects" / project_id / "research" / "artifacts"

    def history_dir_for(self, project_id: str) -> Path:
        return self.root_dir / "projects" / project_id / "research" / "history"

    def path_for(self, artifact: ResearchArchiveArtifact) -> Path:
        base_dir = self.history_dir_for(str(artifact.project_id)) if artifact.artifact_family in HISTORY_FAMILIES else self.artifacts_dir_for(str(artifact.project_id))
        return base_dir / f"{artifact.artifact_id}.json"

    def save(self, artifact: ResearchArchiveArtifact) -> Path:
        path = self.path_for(artifact)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artifact_to_payload(artifact), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def get_by_id(self, project_id: str, artifact_id: str) -> ResearchArchiveArtifact | None:
        for path in self._candidate_paths(project_id=project_id, artifact_id=artifact_id):
            if path.exists():
                return self._load_path(path)
        return None

    def list_project_records(self, project_id: str) -> tuple[ResearchArchiveArtifact, ...]:
        records: list[ResearchArchiveArtifact] = []
        for directory in (self.artifacts_dir_for(project_id), self.history_dir_for(project_id)):
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.json")):
                records.append(self._load_path(path))
        records.sort(key=_sort_key, reverse=True)
        return tuple(records)

    def _candidate_paths(self, *, project_id: str, artifact_id: str) -> tuple[Path, Path]:
        return (
            self.artifacts_dir_for(project_id) / f"{artifact_id}.json",
            self.history_dir_for(project_id) / f"{artifact_id}.json",
        )

    def _load_path(self, path: Path) -> ResearchArchiveArtifact:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed persisted research archive file: {path.stem}") from exc
        return artifact_from_payload(payload)


def _sort_key(artifact: ResearchArchiveArtifact) -> tuple[str, str, str]:
    history_anchor = artifact.event_date or artifact.observed_date or artifact.effective_date or artifact.effective_period or ""
    return (history_anchor, artifact.generated_at, str(artifact.artifact_id))