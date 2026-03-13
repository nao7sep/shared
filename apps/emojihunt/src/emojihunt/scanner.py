"""Directory scanner using os.scandir() for lazy traversal.

Checks ignore patterns before entering directories. Reads files line by line.
Knows nothing about emojis or HTML — yields file content and path status records.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path
from typing import TextIO

from .filter import PathFilter
from .models import HandledPath, HandledPathStatus
from .output_segments import start_output_segment


class FileContent:
    """A successfully opened file, readable line by line."""

    def __init__(self, path: Path, target_root: Path) -> None:
        self.path = path
        self.target_root = target_root

    def read_lines(self) -> Generator[str, None, None]:
        """Yield lines from the file. Caller handles the iteration."""
        with self.path.open("r", encoding="utf-8") as fh:
            yield from fh


class ScanResult:
    """Result for a single file encountered during scanning."""

    def __init__(
        self,
        handled_path: HandledPath,
        file_content: FileContent | None = None,
    ) -> None:
        self.handled_path = handled_path
        self.file_content = file_content


class DirectoryScanner:
    """Lazy directory scanner using os.scandir().

    For each target path:
    - If it's a directory, recurse into it using os.scandir().
    - If it's a file, process it directly.
    - Check ignore patterns before entering directories.
    """

    def __init__(
        self,
        targets: list[Path],
        path_filter: PathFilter,
        *,
        warning_file: TextIO | None = None,
    ) -> None:
        self._targets = targets
        self._filter = path_filter
        self._warning_file = warning_file or sys.stderr

    def scan(self) -> Generator[ScanResult, None, None]:
        """Yield ScanResult for every file encountered across all targets."""
        for target in self._targets:
            if target.is_file():
                yield self._process_file(target, target.parent)
            elif target.is_dir():
                yield from self._scan_directory(target, target)
            else:
                self._warn(f"Target does not exist or is not accessible: {target}")

    def _scan_directory(
        self, directory: Path, target_root: Path
    ) -> Generator[ScanResult, None, None]:
        """Recursively scan a directory using os.scandir()."""
        try:
            entries = sorted(os.scandir(directory), key=lambda e: e.name)
        except OSError as exc:
            self._warn(f"Cannot read directory: {directory} ({exc})")
            return

        dirs_to_recurse: list[Path] = []

        for entry in entries:
            entry_path = Path(entry.path)
            try:
                relative = entry_path.relative_to(target_root)
            except ValueError:
                relative = entry_path
            relative_str = str(relative)

            if entry.is_dir(follow_symlinks=False):
                if not self._filter.is_ignored(relative_str):
                    dirs_to_recurse.append(entry_path)
            elif entry.is_file(follow_symlinks=False):
                if not self._filter.is_ignored(relative_str):
                    yield self._process_file(entry_path, target_root)

        for subdir in dirs_to_recurse:
            yield from self._scan_directory(subdir, target_root)

    def _process_file(self, file_path: Path, target_root: Path) -> ScanResult:
        """Attempt to open a file as UTF-8 text. Return a ScanResult."""
        abs_path = str(file_path.resolve())

        # Try opening as UTF-8 to detect binary files
        try:
            with file_path.open("r", encoding="utf-8") as fh:
                # Read a small chunk to verify it's valid UTF-8
                fh.read(8192)
        except UnicodeDecodeError:
            self._warn(f"Binary file skipped: {abs_path}")
            return ScanResult(
                handled_path=HandledPath(abs_path, HandledPathStatus.SKIPPED),
            )
        except OSError as exc:
            self._warn(f"Cannot read file: {abs_path} ({exc})")
            return ScanResult(
                handled_path=HandledPath(abs_path, HandledPathStatus.ERROR, str(exc)),
            )

        return ScanResult(
            handled_path=HandledPath(abs_path, HandledPathStatus.OK),
            file_content=FileContent(file_path, target_root),
        )

    def _warn(self, message: str) -> None:
        """Print a warning segment to the warning output."""
        start_output_segment(file=self._warning_file)
        print(f"WARNING: {message}", file=self._warning_file)
