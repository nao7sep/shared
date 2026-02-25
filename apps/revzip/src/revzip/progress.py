"""Console progress rendering helpers."""

from __future__ import annotations


class ConsoleProgressReporter:
    """Renders scan/archive progress in-place on the terminal."""

    def __init__(self) -> None:
        self._scan_line_open = False
        self._archive_line_open = False

    def report_scanned(self, scanned_dirs: int, scanned_files: int, final: bool) -> None:
        line = f"Scanned: {scanned_dirs:,} dirs | {scanned_files:,} files"
        self._render_line(line=line, phase="scan", final=final)

    def report_archived(
        self, archived_files: int, total_files: int, final: bool
    ) -> None:
        line = f"Archived: {archived_files:,} / {total_files:,} files"
        self._render_line(line=line, phase="archive", final=final)

    def close_open_lines(self) -> None:
        if self._scan_line_open:
            print()
            self._scan_line_open = False
        if self._archive_line_open:
            print()
            self._archive_line_open = False

    def _render_line(self, *, line: str, phase: str, final: bool) -> None:
        line_open_attr = "_scan_line_open" if phase == "scan" else "_archive_line_open"
        line_open = getattr(self, line_open_attr)

        if final:
            if line_open:
                print()
            else:
                print(line)
            setattr(self, line_open_attr, False)
            return

        print(f"\r{line}", end="", flush=True)
        setattr(self, line_open_attr, True)
