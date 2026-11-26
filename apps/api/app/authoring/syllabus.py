"""Syllabus maps: `<content>/syllabus/cbse/<class>/<subject>.yaml`. Draft keys must exist here."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class MapTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    title: str
    outcomes: list[str] = []
    kind: Literal["fact", "concept", "diagram", "computed"]
    diagram: bool = False


class MapChapter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    title: str
    confidence: Literal["high", "medium", "low"] = "high"
    topics: list[MapTopic] = Field(min_length=1)


class SyllabusMap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_: int = Field(alias="class")
    subject: str
    syllabus_basis: str = ""
    chapters: list[MapChapter] = Field(min_length=1)


def map_path(content_root: Path, grade: int, subject: str) -> Path:
    return content_root / "syllabus" / "cbse" / str(grade) / f"{subject}.yaml"


def duplicate_keys(smap: SyllabusMap) -> list[str]:
    """Chapter keys must be unique in a map and topic keys unique across the whole map (a topic
    key becomes part of a skill id, so it must name exactly one topic)."""
    errors: list[str] = []
    chapters: set[str] = set()
    topics: dict[str, str] = {}
    for chapter in smap.chapters:
        if chapter.key in chapters:
            errors.append(f"duplicate chapter key {chapter.key!r}")
        chapters.add(chapter.key)
        for topic in chapter.topics:
            if topic.key in topics:
                errors.append(
                    f"duplicate topic key {topic.key!r} (in {topics[topic.key]!r} and "
                    f"{chapter.key!r})"
                )
            topics[topic.key] = chapter.key
    return errors


def load_map(content_root: Path, grade: int, subject: str) -> SyllabusMap:
    """Load and validate one map. Raises ValueError with a readable message."""
    path = map_path(content_root, grade, subject)
    if not path.is_file():
        raise ValueError(f"no syllabus map at {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        smap = SyllabusMap.model_validate(raw)
    except (yaml.YAMLError, ValidationError) as exc:
        raise ValueError(f"syllabus map {path}: {str(exc).splitlines()[0]}") from exc
    if smap.class_ != grade or smap.subject != subject:
        raise ValueError(f"syllabus map {path} says class {smap.class_} {smap.subject}")
    errors = duplicate_keys(smap)
    if errors:
        raise ValueError(f"syllabus map {path}: " + "; ".join(errors))
    return smap


def all_maps(content_root: Path) -> list[SyllabusMap]:
    """Every map under the syllabus folder, in class then subject order."""
    base = content_root / "syllabus" / "cbse"
    found: list[SyllabusMap] = []
    if not base.is_dir():
        return found
    for grade_dir in sorted(p for p in base.iterdir() if p.is_dir() and p.name.isdigit()):
        for path in sorted(grade_dir.glob("*.yaml")):
            found.append(load_map(content_root, int(grade_dir.name), path.stem))
    return found


def topic_index(smap: SyllabusMap) -> dict[tuple[str, str], MapTopic]:
    """(chapter key, topic key) -> topic."""
    return {(c.key, t.key): t for c in smap.chapters for t in c.topics}
