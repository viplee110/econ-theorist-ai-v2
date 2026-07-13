"""Export strict Phase 5A machine-protocol schemas independently."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from econ_theorist.machine.models import MACHINE_SCHEMA_MODELS  # noqa: E402


SCHEMA_ID_ROOT = "https://econ-theorist.ai/schemas/machine/v1"


def schema_filename(model_name: str) -> str:
    """Return the stable v1 filename for one versioned machine model."""

    unversioned_name = re.sub(r"V1$", "", model_name)
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", unversioned_name).lower()
    return f"{words}.schema.json"


def model_files() -> dict[str, type]:
    """Map every public machine model to exactly one schema filename."""

    mapped = {
        schema_filename(model.__name__): model for model in MACHINE_SCHEMA_MODELS
    }
    if len(mapped) != len(MACHINE_SCHEMA_MODELS):
        raise RuntimeError("machine schema filename collision")
    return dict(sorted(mapped.items()))


def rendered_schemas() -> dict[str, str]:
    rendered: dict[str, str] = {}
    for filename, model in model_files().items():
        schema = model.model_json_schema(mode="validation")
        schema["$id"] = f"{SCHEMA_ID_ROOT}/{filename}"
        rendered[filename] = json.dumps(
            schema,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
    return rendered


def export(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for filename, content in rendered_schemas().items():
        (destination / filename).write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )


def check(destination: Path) -> bool:
    expected = rendered_schemas()
    actual_names = {path.name for path in destination.glob("*.schema.json")}
    if actual_names != set(expected):
        return False
    return all(
        (destination / filename).read_text(encoding="utf-8") == content
        for filename, content in expected.items()
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    destination = ROOT / "schemas" / "machine" / "v1"
    if args == ["--check"]:
        return 0 if check(destination) else 1
    if args:
        raise SystemExit("usage: export_machine_schemas.py [--check]")
    export(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
