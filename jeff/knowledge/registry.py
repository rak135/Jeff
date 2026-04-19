"""Project-scoped persistence and registry views for compiled knowledge."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import CompiledKnowledgeArtifact, artifact_from_payload, artifact_to_payload

FAMILY_DIRECTORIES = {
    "source_digest": "source_digests",
    "topic_note": "topic_notes",
}


@dataclass(frozen=True, slots=True)
class KnowledgeRegistryEntry:
    artifact_id: str
    artifact_family: str
    project_id: str
    work_unit_id: str | None
    run_id: str | None
    title: str
    topic_key: str | None
    status: str
    generated_at: str
    updated_at: str
    source_refs: tuple[str, ...]
    supporting_artifact_ids: tuple[str, ...]
    related_artifact_ids: tuple[str, ...]
    supersedes_artifact_id: str | None
    superseded_by_artifact_id: str | None


class KnowledgeStore:
    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def knowledge_dir_for(self, project_id: str) -> Path:
        return self.root_dir / "projects" / project_id / "research" / "knowledge"

    def family_dir_for(self, project_id: str, artifact_family: str) -> Path:
        if artifact_family not in FAMILY_DIRECTORIES:
            raise ValueError(f"unsupported compiled knowledge artifact_family: {artifact_family}")
        return self.knowledge_dir_for(project_id) / FAMILY_DIRECTORIES[artifact_family]

    def registry_path_for(self, project_id: str) -> Path:
        return self.knowledge_dir_for(project_id) / "registry.json"

    def path_for(self, artifact: CompiledKnowledgeArtifact) -> Path:
        return self.family_dir_for(artifact.project_id, artifact.artifact_family) / f"{artifact.artifact_id}.json"

    def save(self, artifact: CompiledKnowledgeArtifact) -> Path:
        registry = KnowledgeRegistry(self)
        duplicate = registry.find_duplicate_topic_note(
            project_id=artifact.project_id,
            topic_key=artifact.topic_key,
            supporting_artifact_ids=artifact.supporting_artifact_ids,
        )
        if (
            artifact.artifact_family == "topic_note"
            and duplicate is not None
            and duplicate.artifact_id != str(artifact.artifact_id)
            and duplicate.artifact_id != artifact.supersedes_artifact_id
            and duplicate.status not in {"superseded", "quarantined"}
        ):
            raise ValueError("duplicate active topic_note already exists for this bounded support set")

        path = self.path_for(artifact)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artifact_to_payload(artifact), indent=2, sort_keys=True), encoding="utf-8")
        registry.upsert_entry(artifact)
        return path

    def get_by_id(self, project_id: str, artifact_id: str) -> CompiledKnowledgeArtifact | None:
        registry = KnowledgeRegistry(self)
        entry = registry.get_entry(project_id=project_id, artifact_id=artifact_id)
        if entry is not None:
            path = self.family_dir_for(project_id, entry.artifact_family) / f"{artifact_id}.json"
            if path.exists():
                return artifact_from_payload(json.loads(path.read_text(encoding="utf-8")))
        for artifact_family in FAMILY_DIRECTORIES:
            path = self.family_dir_for(project_id, artifact_family) / f"{artifact_id}.json"
            if path.exists():
                return artifact_from_payload(json.loads(path.read_text(encoding="utf-8")))
        return None

    def list_project_records(self, project_id: str) -> tuple[CompiledKnowledgeArtifact, ...]:
        records: list[CompiledKnowledgeArtifact] = []
        for artifact_family in FAMILY_DIRECTORIES:
            family_dir = self.family_dir_for(project_id, artifact_family)
            if not family_dir.exists():
                continue
            for path in sorted(family_dir.glob("*.json")):
                records.append(artifact_from_payload(json.loads(path.read_text(encoding="utf-8"))))
        records.sort(key=lambda item: (item.updated_at, str(item.artifact_id)), reverse=True)
        return tuple(records)


class KnowledgeRegistry:
    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store

    def get_entry(self, *, project_id: str, artifact_id: str) -> KnowledgeRegistryEntry | None:
        return next(
            (entry for entry in self.list_entries(project_id=project_id) if entry.artifact_id == artifact_id),
            None,
        )

    def list_entries(
        self,
        *,
        project_id: str,
        artifact_family: str | None = None,
        work_unit_id: str | None = None,
        run_id: str | None = None,
        topic_key: str | None = None,
    ) -> tuple[KnowledgeRegistryEntry, ...]:
        entries = self._load_entries(project_id)
        filtered = [
            entry
            for entry in entries
            if (artifact_family is None or entry.artifact_family == artifact_family)
            and (work_unit_id is None or entry.work_unit_id == work_unit_id)
            and (run_id is None or entry.run_id == run_id)
            and (topic_key is None or entry.topic_key == topic_key)
        ]
        filtered.sort(key=lambda entry: (entry.updated_at, entry.artifact_id), reverse=True)
        return tuple(filtered)

    def find_duplicate_topic_note(
        self,
        *,
        project_id: str,
        topic_key: str | None,
        supporting_artifact_ids: tuple[str, ...],
    ) -> KnowledgeRegistryEntry | None:
        if topic_key is None:
            return None
        support_key = tuple(sorted(supporting_artifact_ids))
        for entry in self.list_entries(project_id=project_id, artifact_family="topic_note", topic_key=topic_key):
            if tuple(sorted(entry.supporting_artifact_ids)) == support_key:
                return entry
        return None

    def upsert_entry(self, artifact: CompiledKnowledgeArtifact) -> None:
        path = self.store.registry_path_for(artifact.project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        entries = [entry for entry in self._load_entries(artifact.project_id) if entry.artifact_id != str(artifact.artifact_id)]
        entries.append(
            KnowledgeRegistryEntry(
                artifact_id=str(artifact.artifact_id),
                artifact_family=artifact.artifact_family,
                project_id=artifact.project_id,
                work_unit_id=artifact.work_unit_id,
                run_id=artifact.run_id,
                title=artifact.title,
                topic_key=artifact.topic_key,
                status=artifact.status,
                generated_at=artifact.generated_at,
                updated_at=artifact.updated_at,
                source_refs=artifact.source_refs,
                supporting_artifact_ids=artifact.supporting_artifact_ids,
                related_artifact_ids=artifact.related_artifact_ids,
                supersedes_artifact_id=artifact.supersedes_artifact_id,
                superseded_by_artifact_id=artifact.superseded_by_artifact_id,
            )
        )
        payload = {
            "entries": [
                {
                    "artifact_id": entry.artifact_id,
                    "artifact_family": entry.artifact_family,
                    "project_id": entry.project_id,
                    "work_unit_id": entry.work_unit_id,
                    "run_id": entry.run_id,
                    "title": entry.title,
                    "topic_key": entry.topic_key,
                    "status": entry.status,
                    "generated_at": entry.generated_at,
                    "updated_at": entry.updated_at,
                    "source_refs": list(entry.source_refs),
                    "supporting_artifact_ids": list(entry.supporting_artifact_ids),
                    "related_artifact_ids": list(entry.related_artifact_ids),
                    "supersedes_artifact_id": entry.supersedes_artifact_id,
                    "superseded_by_artifact_id": entry.superseded_by_artifact_id,
                }
                for entry in sorted(entries, key=lambda item: (item.updated_at, item.artifact_id), reverse=True)
            ]
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _load_entries(self, project_id: str) -> tuple[KnowledgeRegistryEntry, ...]:
        path = self.store.registry_path_for(project_id)
        if not path.exists():
            return ()
        payload = json.loads(path.read_text(encoding="utf-8"))
        return tuple(
            KnowledgeRegistryEntry(
                artifact_id=str(item["artifact_id"]),
                artifact_family=str(item["artifact_family"]),
                project_id=str(item["project_id"]),
                work_unit_id=item.get("work_unit_id"),
                run_id=item.get("run_id"),
                title=str(item["title"]),
                topic_key=item.get("topic_key"),
                status=str(item["status"]),
                generated_at=str(item["generated_at"]),
                updated_at=str(item["updated_at"]),
                source_refs=tuple(item.get("source_refs", ())),
                supporting_artifact_ids=tuple(item.get("supporting_artifact_ids", ())),
                related_artifact_ids=tuple(item.get("related_artifact_ids", ())),
                supersedes_artifact_id=item.get("supersedes_artifact_id"),
                superseded_by_artifact_id=item.get("superseded_by_artifact_id"),
            )
            for item in payload.get("entries", ())
        )