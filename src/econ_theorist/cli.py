"""Small deterministic CLI for the Phase 1 walking substrate."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .doctor import doctor_report
from .decisions import commit_decision, read_decision
from .errors import EconTheoristError
from .models import Actor, FACET_ORDER
from .project import init_project
from .runs import begin_run
from .runtime import StoreLayout
from .runtime.freshness import stale_reason_chains
from .runtime.recovery import recover
from .runtime.render import render_current, render_status
from .runtime.replay import replay
from .staging import commit_run, stage_candidate


PURPOSE_DEFAULTS = {
    "frame.question_and_benchmarks": "research_framing",
    "repair.dependency": "research_repair",
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _print_json(value: Any) -> None:
    print(json.dumps(_jsonable(value), ensure_ascii=False, indent=2, sort_keys=True))


def _layout(args: argparse.Namespace) -> StoreLayout:
    return StoreLayout.at(Path(args.project))


def _parse_artifacts(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--artifact must use ARTIFACT_ID=PATH")
        artifact_id, raw_path = value.split("=", 1)
        if not artifact_id or not raw_path or artifact_id in result:
            raise ValueError("artifact IDs and paths must be non-empty and unique")
        result[artifact_id] = Path(raw_path)
    return result


def _cmd_init(args: argparse.Namespace) -> int:
    snapshot = init_project(
        args.project,
        name=args.name,
        actor_id=args.actor,
        project_id=args.project_id,
    )
    _print_json(
        {
            "status": "initialized",
            "project_id": snapshot.project_id,
            "head": snapshot.head,
        }
    )
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    snapshot = replay(_layout(args))
    _print_json(
        {
            "valid": True,
            "project_id": snapshot.project_id,
            "head": snapshot.head,
            "transactions": len(snapshot.chain),
            "entities": len(snapshot.entity_versions),
            "relations": len(snapshot.relation_versions),
            "artifacts": len(snapshot.artifacts),
        }
    )
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    snapshot = replay(_layout(args))
    if args.json:
        _print_json(snapshot)
    else:
        print(render_status(snapshot), end="")
    return 0


def _cmd_begin(args: argparse.Namespace) -> int:
    layout = _layout(args)
    snapshot = replay(layout)
    purpose = args.purpose or PURPOSE_DEFAULTS.get(args.route)
    if purpose is None:
        raise ValueError("--purpose is required for this route")
    run = begin_run(
        layout,
        snapshot,
        route_id=args.route,
        actor=Actor(kind=args.actor_kind, actor_id=args.actor),
        purpose=purpose,
        compartments=tuple(args.compartment),
        privacy_clearance=args.privacy_clearance,
        focus_entity_ids=tuple(args.focus),
        budget_units=args.budget,
    )
    _print_json(
        {
            "status": run.status,
            "route_run_id": run.route_run_id,
            "base_revision": run.base_revision,
            "context_hash": run.context_hash,
        }
    )
    return 0


def _cmd_stage(args: argparse.Namespace) -> int:
    digest = stage_candidate(
        _layout(args),
        args.run,
        args.candidate,
        artifacts=_parse_artifacts(args.artifact),
    )
    _print_json({"status": "staged", "candidate_digest": digest})
    return 0


def _cmd_commit(args: argparse.Namespace) -> int:
    result = commit_run(_layout(args), args.run, digest=args.candidate_digest)
    _print_json(result)
    return 0 if result.status == "committed" else 3


def _cmd_decide(args: argparse.Namespace) -> int:
    result = commit_decision(_layout(args), read_decision(args.decision))
    _print_json(result)
    return 0 if result.status == "committed" else 3


def _cmd_stale(args: argparse.Namespace) -> int:
    snapshot = replay(_layout(args))
    status = snapshot.derived_status.get(args.entity)
    if status is None:
        raise ValueError(f"unknown current entity: {args.entity}")
    facets = (args.facet,) if args.facet else FACET_ORDER
    result: dict[str, Any] = {
        "entity_id": args.entity,
        "source_head": snapshot.head,
        "facets": {},
    }
    for facet in facets:
        freshness = status.freshness.get(facet, "fresh")
        chains = stale_reason_chains(snapshot, args.entity, facet)
        result["facets"][facet] = {
            "freshness": freshness,
            "why": [
                [reason.model_dump(mode="json") for reason in chain]
                for chain in chains
            ],
        }
    _print_json(result)
    return 0


def _cmd_recover(args: argparse.Namespace) -> int:
    report = recover(_layout(args))
    _print_json(report)
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    result = render_current(_layout(args))
    _print_json(
        {
            "status": "rendered",
            "source_head": result.source_head,
            "path": result.path,
        }
    )
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    root = Path(args.project)
    report = doctor_report(root if (root / ".econ-theorist").exists() else None)
    _print_json(report)
    return 0 if report["required_ok"] else 4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="etai",
        description="Theory-only, provenance-preserving research substrate",
    )
    parser.add_argument(
        "--project",
        default=".",
        help="theory project root (default: current directory)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    command = subparsers.add_parser("init", help="initialize one theory project")
    command.add_argument("--name", required=True)
    command.add_argument("--actor", default="local_human")
    command.add_argument("--project-id")
    command.set_defaults(handler=_cmd_init)

    command = subparsers.add_parser("validate", help="verify and replay canonical state")
    command.set_defaults(handler=_cmd_validate)

    command = subparsers.add_parser("status", help="show the generated compact status")
    command.add_argument("--json", action="store_true")
    command.set_defaults(handler=_cmd_status)

    command = subparsers.add_parser("begin", help="begin an isolated route run")
    command.add_argument("route")
    command.add_argument("--actor-kind", choices=("human", "agent"), default="agent")
    command.add_argument("--actor", default="local_agent")
    command.add_argument("--purpose")
    command.add_argument("--compartment", action="append", default=["project_research"])
    command.add_argument(
        "--privacy-clearance",
        choices=("public", "project_private", "restricted", "local_only"),
        default="project_private",
    )
    command.add_argument("--focus", action="append", default=[])
    command.add_argument("--budget", type=int, default=4000)
    command.set_defaults(handler=_cmd_begin)

    command = subparsers.add_parser("stage", help="stage one preserved run candidate")
    command.add_argument("run")
    command.add_argument("candidate")
    command.add_argument("--artifact", action="append", default=[])
    command.set_defaults(handler=_cmd_stage)

    command = subparsers.add_parser("commit", help="atomically commit a staged candidate")
    command.add_argument("run")
    command.add_argument("--candidate-digest")
    command.set_defaults(handler=_cmd_commit)

    command = subparsers.add_parser(
        "decide", help="persist one explicit Decision JSON record"
    )
    command.add_argument("decision")
    command.set_defaults(handler=_cmd_decide)

    command = subparsers.add_parser("stale", help="explain derived facet freshness")
    command.add_argument("--why", dest="entity", required=True)
    command.add_argument("--facet", choices=FACET_ORDER)
    command.set_defaults(handler=_cmd_stale)

    command = subparsers.add_parser("recover", help="replay and rebuild projections")
    command.set_defaults(handler=_cmd_recover)

    command = subparsers.add_parser("render", help="regenerate the noncanonical status view")
    command.set_defaults(handler=_cmd_render)

    command = subparsers.add_parser("doctor", help="report required and optional capabilities")
    command.set_defaults(handler=_cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (EconTheoristError, RuntimeError, ValueError, OSError) as exc:
        print(f"etai: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


__all__ = ["build_parser", "main"]
