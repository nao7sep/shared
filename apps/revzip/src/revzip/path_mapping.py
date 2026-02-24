"""Path mapping and startup validation."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .errors import PathMappingError, StartupValidationError
from .models import ResolvedPaths

_WINDOWS_DRIVE_RELATIVE_RE = re.compile(r"^[A-Za-z]:[^/\\]")


def resolve_startup_paths(
    *,
    source_arg_raw: str,
    dest_arg_raw: str,
    ignore_arg_raw: str | None,
    app_root_abs: Path,
) -> ResolvedPaths:
    if not app_root_abs.is_absolute():
        raise StartupValidationError("App root must be an absolute path.")

    source_dir_abs = map_path_argument(
        raw_path=source_arg_raw,
        app_root_abs=app_root_abs,
        argument_name="--source",
    )
    dest_dir_abs = map_path_argument(
        raw_path=dest_arg_raw,
        app_root_abs=app_root_abs,
        argument_name="--dest",
    )
    ignore_file_abs = (
        map_path_argument(
            raw_path=ignore_arg_raw,
            app_root_abs=app_root_abs,
            argument_name="--ignore",
        )
        if ignore_arg_raw is not None
        else None
    )

    _validate_source_exists(source_dir_abs)
    _validate_source_dest_do_not_overlap(source_dir_abs, dest_dir_abs)
    _validate_dest(dest_dir_abs)
    _validate_ignore(ignore_file_abs)

    return ResolvedPaths(
        source_arg_raw=source_arg_raw,
        source_dir_abs=source_dir_abs,
        dest_arg_raw=dest_arg_raw,
        dest_dir_abs=dest_dir_abs,
        ignore_arg_raw=ignore_arg_raw,
        ignore_file_abs=ignore_file_abs,
    )


def map_path_argument(
    *,
    raw_path: str | None,
    app_root_abs: Path,
    argument_name: str,
) -> Path:
    if raw_path is None:
        raise PathMappingError(f"{argument_name} path is missing.")

    normalized_input = unicodedata.normalize("NFC", raw_path)
    if "\0" in normalized_input:
        raise PathMappingError(f"{argument_name} contains NUL (\\0).")
    if _is_windows_rooted_not_fully_qualified(normalized_input):
        raise PathMappingError(
            f"{argument_name} uses an unsupported Windows rooted-not-qualified path."
        )

    mapped = _map_special_prefixes(normalized_input, app_root_abs)
    if not mapped.is_absolute():
        raise PathMappingError(
            f"{argument_name} must be absolute or start with '~' or '@'."
        )

    return mapped.resolve(strict=False)


def _map_special_prefixes(path_text: str, app_root_abs: Path) -> Path:
    if path_text.startswith("~"):
        return Path(path_text).expanduser()
    if path_text.startswith("@"):
        return _map_app_root_path(path_text, app_root_abs)
    return Path(path_text)


def _map_app_root_path(path_text: str, app_root_abs: Path) -> Path:
    remainder = path_text[1:]
    if remainder == "":
        return app_root_abs

    remainder = remainder.lstrip("/\\")
    if remainder == "":
        return app_root_abs

    segments = [segment for segment in re.split(r"[\\/]+", remainder) if segment]
    return app_root_abs.joinpath(*segments)


def _is_windows_rooted_not_fully_qualified(path_text: str) -> bool:
    if path_text.startswith("\\") and not path_text.startswith("\\\\"):
        return True
    return _WINDOWS_DRIVE_RELATIVE_RE.match(path_text) is not None


def _validate_source_exists(source_dir_abs: Path) -> None:
    if not source_dir_abs.exists():
        raise StartupValidationError(f"--source does not exist: {source_dir_abs}")
    if not source_dir_abs.is_dir():
        raise StartupValidationError(f"--source must be a directory: {source_dir_abs}")


def _validate_dest(dest_dir_abs: Path) -> None:
    if dest_dir_abs.exists() and not dest_dir_abs.is_dir():
        raise StartupValidationError(f"--dest must be a directory: {dest_dir_abs}")
    if not dest_dir_abs.exists():
        try:
            dest_dir_abs.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StartupValidationError(
                f"Failed to create --dest directory: {dest_dir_abs}"
            ) from exc


def _validate_ignore(ignore_file_abs: Path | None) -> None:
    if ignore_file_abs is None:
        return
    if not ignore_file_abs.exists():
        raise StartupValidationError(f"--ignore file does not exist: {ignore_file_abs}")
    if not ignore_file_abs.is_file():
        raise StartupValidationError(f"--ignore must point to a file: {ignore_file_abs}")


def _validate_source_dest_do_not_overlap(source_dir_abs: Path, dest_dir_abs: Path) -> None:
    source_resolved = source_dir_abs.resolve(strict=False)
    dest_resolved = dest_dir_abs.resolve(strict=False)
    if (
        source_resolved == dest_resolved
        or _is_ancestor(source_resolved, dest_resolved)
        or _is_ancestor(dest_resolved, source_resolved)
    ):
        raise StartupValidationError(
            "--source and --dest must not overlap (same path, ancestor, or descendant)."
        )


def _is_ancestor(ancestor: Path, descendant: Path) -> bool:
    try:
        descendant.relative_to(ancestor)
    except ValueError:
        return False
    return True
