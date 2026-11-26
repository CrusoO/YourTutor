"""Synthetic fixtures. The 'book' here is invented text; no real book is ever used in tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.bookcheck.settings import Settings

# Unusual words so a leak into console output is unmistakable.
BOOK_RUN = "zephyrine quotient measured dividing distance elapsed time every single morning"
BOOK_PAGES = [
    "Contents\nChapter 1 Motion\nChapter 2 Force and Laws of Motion",
    "Chapter 1 Motion\n1.1 Speed and velocity\n"
    f"Remember that the {BOOK_RUN} by careful learners.\n"
    "The speed of light in vacuum has a value of 3 x 10^8 m/s.\n"
    "The acceleration due to gravity has a value of 9.8 m/s2.\n"
    "Speed is called the rate of change of distance.",
    "Average speed of a cyclist is distance divided by time. Density, which is mass divided by "
    "volume, is a different quantity but the average speed of a cyclist measure sometimes "
    "confuses learners.",
    "Chapter 2 Force and Laws of Motion\n2.1 Balanced and unbalanced forces\n"
    "A force can change the state of rest of an object. Newton studied inertia of rest.",
]

SYLLABUS = """class: 9
subject: physics
chapters:
  - key: motion
    title: "Motion"
    confidence: high
    topics:
      - key: speed_and_velocity
        title: "Speed and velocity"
        kind: concept
  - key: force
    title: "Force and laws of motion"
    confidence: low
    topics:
      - key: balanced_forces
        title: "Balanced and unbalanced forces"
        kind: concept
  - key: sound
    title: "Sound waves"
    confidence: low
    topics:
      - key: echo
        title: "Echo and reflection of sound"
        kind: concept
"""


def item_yaml(items: list[str]) -> str:
    return "class: 9\nsubject: physics\nchapter: motion\nitems:\n" + "".join(items)


def item(
    topic: str, stem: str, correct: str, wrong: list[str] | None = None, expl: str = "ok"
) -> str:
    lines = [
        f"- topic: {topic}\n",
        "  type: mcq\n",
        f"  stem: {json.dumps(stem)}\n",
        f"  correct: {json.dumps(correct)}\n",
        "  wrong:\n" if wrong else "  wrong: []\n",
    ]
    for text in wrong or []:
        lines.append(f"  - text: {json.dumps(text)}\n    mistake: x\n")
    lines.append(f"  explanation: {json.dumps(expl)}\n")
    lines.append("  hints: [one hint]\n")
    return "".join(lines)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(tmp_path / "books", tmp_path / "out", None)


@pytest.fixture
def content(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    (root / "syllabus" / "cbse" / "9").mkdir(parents=True)
    (root / "syllabus" / "cbse" / "9" / "physics.yaml").write_text(SYLLABUS, encoding="utf-8")
    (root / "authoring" / "drafts" / "9" / "physics").mkdir(parents=True)
    return root


def write_drafts(content: Path, items: list[str], name: str = "motion") -> None:
    path = content / "authoring" / "drafts" / "9" / "physics" / f"{name}.yaml"
    path.write_text(item_yaml(items), encoding="utf-8", newline="\n")


def write_book(
    settings: Settings,
    pages: list[str] | None = None,
    sha: str = "a" * 64,
    grade: int = 9,
    subject: str = "physics",
) -> str:
    """Write a page cache and manifest entry directly, so no PDF is needed."""
    pages = BOOK_PAGES if pages is None else pages
    folder = settings.out_dir / "cache" / sha
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / "pages.jsonl", "w", encoding="utf-8", newline="\n") as handle:
        for number, text in enumerate(pages, 1):
            handle.write(json.dumps({"p": number, "t": text}) + "\n")
    manifest_path = settings.out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"books": []}
    manifest["books"].append(
        {"file": f"{grade}/{subject}/x.pdf", "sha": sha, "class": grade, "subject": subject,
         "pages": len(pages), "needs_ocr": [], "status": "ok"}
    )  # fmt: skip
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return sha


def minimal_pdf(texts: list[str]) -> bytes:
    """A tiny valid PDF with one page per text (an empty string makes a blank page)."""
    objects: list[bytes] = []
    n = len(texts)
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode())
    font = 3 + 2 * n
    for i, text in enumerate(texts):
        page, content_id = 3 + 2 * i, 4 + 2 * i
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_id} 0 R "
            f"/Resources << /Font << /F1 {font} 0 R >> >> >>".encode()
        )
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode() if text else b""
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        assert page == 3 + 2 * i
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % index + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)
