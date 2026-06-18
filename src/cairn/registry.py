from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


REGISTRY_ENV = "APOLLOKAIRN_REGISTRY_PATH"


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class VaultRecord:
    name: str
    path: Path
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class VaultStatus:
    name: str
    path: Path
    active: bool
    exists: bool
    is_vault: bool
    message: str


@dataclass
class VaultRegistry:
    active: str | None = None
    vaults: dict[str, VaultRecord] = field(default_factory=dict)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def registry_path() -> Path:
    override = os.environ.get(REGISTRY_ENV)
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "ApolloKairn" / "vaults.json"
        return Path.home() / "AppData" / "Roaming" / "ApolloKairn" / "vaults.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ApolloKairn" / "vaults.json"
    base = os.environ.get("XDG_CONFIG_HOME")
    config_root = Path(base).expanduser() if base else Path.home() / ".config"
    return config_root / "apollokairn" / "vaults.json"


def _record_from_json(name: str, data: object) -> VaultRecord:
    if not isinstance(data, dict):
        raise RegistryError(f"invalid registry record for '{name}'")
    raw_path = data.get("path")
    created_at = data.get("created_at")
    updated_at = data.get("updated_at")
    if not isinstance(raw_path, str) or not isinstance(created_at, str) or not isinstance(updated_at, str):
        raise RegistryError(f"invalid registry record for '{name}'")
    return VaultRecord(name=name, path=Path(raw_path), created_at=created_at, updated_at=updated_at)


def load_registry() -> VaultRegistry:
    path = registry_path()
    if not path.exists():
        return VaultRegistry()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryError(f"registry invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RegistryError("registry root must be an object")
    active = data.get("active")
    if active is not None and not isinstance(active, str):
        raise RegistryError("registry active must be a string or null")
    raw_vaults = data.get("vaults", {})
    if not isinstance(raw_vaults, dict):
        raise RegistryError("registry vaults must be an object")
    vaults = {name: _record_from_json(name, item) for name, item in raw_vaults.items() if isinstance(name, str)}
    if active is not None and active not in vaults:
        active = None
    return VaultRegistry(active=active, vaults=vaults)


def save_registry(registry: VaultRegistry) -> VaultRegistry:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "active": registry.active if registry.active in registry.vaults else None,
        "vaults": {
            name: {
                "path": str(record.path),
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            }
            for name, record in sorted(registry.vaults.items())
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return load_registry()


def _validate_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise RegistryError("vault name cannot be empty")
    if "/" in normalized or "\\" in normalized:
        raise RegistryError("vault name cannot contain path separators")
    return normalized


def _assert_existing_vault(path: Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise RegistryError(f"vault path does not exist: {resolved}")
    if not (resolved / ".cairn" / "config.json").exists():
        raise RegistryError(f"path is not an ApolloKairn vault: {resolved}")
    return resolved


def add_vault(path: Path, name: str, set_active: bool = False) -> VaultRecord:
    registry = load_registry()
    vault_name = _validate_name(name)
    if vault_name in registry.vaults:
        raise RegistryError(f"vault '{vault_name}' is already registered")
    now = _now()
    record = VaultRecord(
        name=vault_name,
        path=_assert_existing_vault(path),
        created_at=now,
        updated_at=now,
    )
    registry.vaults[vault_name] = record
    if set_active:
        registry.active = vault_name
    save_registry(registry)
    return record


def remove_vault(name: str) -> VaultRecord:
    registry = load_registry()
    vault_name = _validate_name(name)
    try:
        record = registry.vaults.pop(vault_name)
    except KeyError as exc:
        raise RegistryError(f"vault '{vault_name}' is not registered") from exc
    if registry.active == vault_name:
        registry.active = None
    save_registry(registry)
    return record


def use_vault(name: str) -> VaultRecord:
    registry = load_registry()
    vault_name = _validate_name(name)
    try:
        record = registry.vaults[vault_name]
    except KeyError as exc:
        raise RegistryError(f"vault '{vault_name}' is not registered") from exc
    if not _is_vault(record.path):
        raise RegistryError(f"vault '{record.name}' is not available: {record.path}")
    registry.active = vault_name
    save_registry(registry)
    return record


def list_vaults() -> list[VaultRecord]:
    return [record for _, record in sorted(load_registry().vaults.items())]


def show_vault(name: str) -> VaultRecord:
    registry = load_registry()
    vault_name = _validate_name(name)
    try:
        return registry.vaults[vault_name]
    except KeyError as exc:
        raise RegistryError(f"vault '{vault_name}' is not registered") from exc


def current_vault() -> VaultRecord | None:
    registry = load_registry()
    if registry.active is None:
        return None
    return registry.vaults.get(registry.active)


def _is_vault(path: Path) -> bool:
    return path.exists() and (path / ".cairn" / "config.json").exists()


def status_for(record: VaultRecord, active: bool = False) -> VaultStatus:
    exists = record.path.exists()
    is_vault = _is_vault(record.path)
    if not exists:
        message = "path missing"
    elif not is_vault:
        message = "missing .cairn/config.json"
    else:
        message = "ok"
    return VaultStatus(
        name=record.name,
        path=record.path,
        active=active,
        exists=exists,
        is_vault=is_vault,
        message=message,
    )


def doctor_vaults() -> list[VaultStatus]:
    registry = load_registry()
    return [
        status_for(record, active=(name == registry.active))
        for name, record in sorted(registry.vaults.items())
    ]


def resolve_vault_path(path: Path | str | None, vault_name: str | None) -> Path:
    if path is not None:
        return Path(path).expanduser().resolve()
    if vault_name:
        record = show_vault(vault_name)
        if not _is_vault(record.path):
            raise RegistryError(f"registered vault '{record.name}' is not available: {record.path}")
        return record.path
    active = current_vault()
    if active is None:
        return Path.cwd()
    if not _is_vault(active.path):
        raise RegistryError(f"active vault '{active.name}' is not available: {active.path}")
    return active.path
