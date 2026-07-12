"""Export strict Phase 3 assurance/authoring schemas independently."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from econ_theorist.authoring import AUTHORING_PAYLOAD_MODELS  # noqa: E402


def schema_filename(model_name: str) -> str:
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", model_name).lower()
    return f"{words}.schema.json"


def rendered_schemas() -> dict[str, str]:
    rendered: dict[str, str] = {}
    for entity_type, model in sorted(AUTHORING_PAYLOAD_MODELS.items()):
        filename = schema_filename(entity_type)
        schema = model.model_json_schema(mode="validation")
        schema["$id"] = (
            f"https://econ-theorist.ai/schemas/authoring/v1/{filename}"
        )
        rendered[filename] = json.dumps(
            schema,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
    return rendered


def export(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    expected = rendered_schemas()
    for filename, content in expected.items():
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
    destination = ROOT / "schemas" / "authoring" / "v1"
    if args == ["--check"]:
        return 0 if check(destination) else 1
    if args:
        raise SystemExit("usage: export_authoring_schemas.py [--check]")
    export(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
