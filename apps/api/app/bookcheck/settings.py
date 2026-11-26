"""Where the private book folders live. Read from the environment, never from the repo.

Both folders must resolve outside the git repository root: book text must never be able to end up
in a commit. A path inside OneDrive (or another synced folder) only draws a warning.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

BOOKS_ENV = "BOOKCHECK_BOOKS_DIR"
OUT_ENV = "BOOKCHECK_OUT_DIR"
DEFAULT_BOOKS = r"C:\private-books"
DEFAULT_OUT = r"C:\private-books-out"

CLASSES = (9, 10, 11, 12)
SUBJECTS = ("maths", "physics", "chemistry", "biology", "science")
# A combined science book (classes 9 and 10) covers these three subjects.
SCIENCE_PARTS = ("physics", "chemistry", "biology")
COMBINED_SCIENCE_CLASSES = (9, 10)
BOARD_DIR = "cbse"


class SettingsError(Exception):
    """A configured folder is not allowed. The message never contains book text."""


def find_repo_root(start: Path | None = None) -> Path | None:
    here = (start or Path(__file__)).resolve()
    for parent in [here, *here.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class Settings:
    books_dir: Path
    out_dir: Path
    repo_root: Path | None

    def check(self) -> list[str]:
        """Raise SettingsError when a folder is inside the repo; return warnings otherwise."""
        warnings: list[str] = []
        for label, path in (("books folder", self.books_dir), ("output folder", self.out_dir)):
            if self.repo_root is not None and is_inside(path, self.repo_root):
                raise SettingsError(
                    f"the {label} is inside the git repository; choose a folder outside it "
                    f"(set {BOOKS_ENV} / {OUT_ENV})"
                )
            if "onedrive" in str(path).casefold():
                warnings.append(
                    f"the {label} looks like it is inside OneDrive; prefer a local folder"
                )
        if is_inside(self.out_dir, self.books_dir) or is_inside(self.books_dir, self.out_dir):
            raise SettingsError(
                "the books folder and the output folder must not contain each other"
            )
        return warnings


def load_settings(
    env: dict[str, str] | None = None, repo_root: Path | None = None, strict: bool = True
) -> Settings:
    source = os.environ if env is None else env
    books = Path(source.get(BOOKS_ENV) or DEFAULT_BOOKS)
    out = Path(source.get(OUT_ENV) or DEFAULT_OUT)
    settings = Settings(books, out, repo_root if repo_root is not None else find_repo_root())
    for warning in settings.check():
        print(f"warning: {warning}", file=sys.stderr)
    return settings
