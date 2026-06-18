from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from cairn.secret_scan import scan_text


def _should_skip(rel: str) -> bool:
    parts = rel.split("/")
    if "__pycache__" in parts:
        return True
    if rel == ".cairn/index.db" or rel.endswith(".pyc"):
        return True
    return False


def _export_files(root: Path, output: Path) -> list[Path]:
    resolved_output = output.resolve()
    return [
        path
        for path in sorted(item for item in root.rglob("*") if item.is_file())
        if path.resolve() != resolved_output and not _should_skip(path.relative_to(root).as_posix())
    ]


def _check_secrets(root: Path, paths: list[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        findings = scan_text(text)
        if not findings:
            continue
        rel = path.relative_to(root).as_posix()
        finding = findings[0]
        raise ValueError(f"potential secret detected in {rel}: {finding.kind} on line {finding.line}")


def export_vault(root: Path, output: Path) -> Path:
    root = Path(root)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    paths = _export_files(root, output)
    _check_secrets(root, paths)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as zf:
        for path in paths:
            rel = path.relative_to(root).as_posix()
            zf.write(path, rel)
    return output


def import_vault(archive: Path, root: Path) -> Path:
    archive = Path(archive)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as zf:
        for info in zf.infolist():
            rel = Path(info.filename)
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError(f"unsafe archive path: {info.filename}")
            target = (root / rel).resolve()
            if root.resolve() not in target.parents and target != root.resolve():
                raise ValueError(f"unsafe archive path: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as source, target.open("wb") as dest:
                dest.write(source.read())
    return root
