from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


REQUIRED_FIELDS = ["name", "capability", "version", "inputs", "outputs"]


def validate_file(path: Path) -> List[str]:
    errors: List[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"{path.name}:invalid_json:{e}"]

    if not isinstance(data, list):
        return [f"{path.name}:root_must_be_list"]

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"{path.name}[{i}]:item_must_be_object")
            continue
        for f in REQUIRED_FIELDS:
            if f not in item:
                errors.append(f"{path.name}[{i}]:missing:{f}")
        if "name" in item and not str(item["name"]).strip():
            errors.append(f"{path.name}[{i}]:empty:name")
        if "version" in item and not str(item["version"]).strip():
            errors.append(f"{path.name}[{i}]:empty:version")
        if "inputs" in item and not isinstance(item["inputs"], list):
            errors.append(f"{path.name}[{i}]:inputs_must_be_list")
        if "outputs" in item and not isinstance(item["outputs"], list):
            errors.append(f"{path.name}[{i}]:outputs_must_be_list")
    return errors


def main() -> int:
    skills_dir = Path(__file__).resolve().parents[1] / "skills"
    files = sorted(skills_dir.glob("*.skills.json"))
    if not files:
        sys.stderr.write("no_skills_files\n")
        return 2

    errors: List[str] = []
    seen: set[Tuple[str, str]] = set()

    for f in files:
        errors.extend(validate_file(f))
        if errors:
            continue
        items = json.loads(f.read_text(encoding="utf-8"))
        for it in items:
            if not isinstance(it, dict):
                continue
            key = (str(it.get("name", "")).strip(), str(it.get("version", "")).strip())
            if key in seen and key != ("", ""):
                errors.append(f"duplicate_skill:{key[0]}:{key[1]}")
            seen.add(key)

    if errors:
        for e in errors:
            sys.stderr.write(e + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

