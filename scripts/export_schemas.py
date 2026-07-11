"""Export the versioned public JSON schemas from the strict Pydantic models."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from econ_theorist.models import (  # noqa: E402
    ArtifactRegistration,
    ContextManifest,
    Decision,
    EntityVersion,
    RelationVersion,
    RouteRun,
    Snapshot,
    Transaction,
)


MODELS = {
    "artifact-registration": ArtifactRegistration,
    "context-manifest": ContextManifest,
    "decision": Decision,
    "entity-version": EntityVersion,
    "relation-version": RelationVersion,
    "route-run": RouteRun,
    "snapshot": Snapshot,
    "transaction": Transaction,
}


def rendered_schemas() -> dict[str, str]:
    rendered: dict[str, str] = {}
    for name, model in MODELS.items():
        schema = model.model_json_schema(mode="validation")
        schema["$id"] = f"https://econ-theorist.ai/schemas/v1/{name}.schema.json"
        rendered[name] = json.dumps(
            schema,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ) + "\n"
    return rendered


def export(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    expected = rendered_schemas()
    for name, text in expected.items():
        (destination / f"{name}.schema.json").write_text(text, encoding="utf-8")


def check(destination: Path) -> bool:
    expected = rendered_schemas()
    actual_names = {path.name for path in destination.glob("*.schema.json")}
    expected_names = {f"{name}.schema.json" for name in expected}
    if actual_names != expected_names:
        return False
    return all(
        (destination / f"{name}.schema.json").read_text(encoding="utf-8") == text
        for name, text in expected.items()
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    destination = ROOT / "schemas" / "v1"
    if args == ["--check"]:
        return 0 if check(destination) else 1
    if args:
        raise SystemExit("usage: export_schemas.py [--check]")
    export(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
