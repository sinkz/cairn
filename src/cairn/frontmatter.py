from __future__ import annotations

from dataclasses import dataclass


class FrontmatterError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedDocument:
    frontmatter: dict[str, object]
    body: str


def _parse_scalar(value: str) -> object:
    value = value.strip()
    if value == "":
        return ""
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip('"').strip("'") for part in inner.split(",")]
    return value.strip('"').strip("'")


def _parse_frontmatter(lines: list[str]) -> dict[str, object]:
    data: dict[str, object] = {}
    current_list_key: str | None = None
    for raw in lines:
        if not raw.strip():
            continue
        if raw.startswith("  - ") and current_list_key:
            data.setdefault(current_list_key, [])
            value = raw[4:].strip().strip('"').strip("'")
            cast = data[current_list_key]
            if isinstance(cast, list):
                cast.append(value)
            continue
        if raw[:1].isspace():
            raise FrontmatterError(f"unsupported indented frontmatter line: {raw}")
        if ":" not in raw:
            raise FrontmatterError(f"invalid frontmatter line: {raw}")
        key, value = raw.split(":", 1)
        key = key.strip()
        if not key:
            raise FrontmatterError("empty frontmatter key")
        parsed = _parse_scalar(value)
        data[key] = parsed
        current_list_key = key if value.strip() == "" else None
        if current_list_key:
            data[key] = []
    return data


def parse_document(text: str) -> ParsedDocument:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("missing YAML frontmatter block")
    end_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        raise FrontmatterError("unterminated YAML frontmatter block")
    fm_lines = [line.rstrip("\n") for line in lines[1:end_index]]
    body = "".join(lines[end_index + 1 :])
    if body.startswith("\r\n"):
        body = body[2:]
    elif body.startswith("\n"):
        body = body[1:]
    return ParsedDocument(frontmatter=_parse_frontmatter(fm_lines), body=body)
