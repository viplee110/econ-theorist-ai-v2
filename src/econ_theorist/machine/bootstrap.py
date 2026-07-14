"""Pure bootstrap planning and post-install engine inventory verification."""

from __future__ import annotations

import importlib.metadata
import os
import platform
import re
import shutil
import stat
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath
from typing import Iterable
from urllib.parse import urlsplit

from .. import __version__
from ..codec import canonical_json_bytes, sha256_digest
from ..doctor import doctor_report
from ..distribution_resources import (
    DistributionResourceError,
    installed_resource_root,
)
from ..ids import utc_now
from .models import (
    BootstrapDescriptorV1,
    CapabilityReceiptV1,
    CapabilityV1,
    DiagnosticV1,
    EngineManifestV1,
    EngineReleaseInventoryV1,
    EngineResourceV1,
    EngineVerificationV1,
    InstallPlanV1,
    InstalledDistributionV1,
)
from .resources import (
    HOST_MANIFEST_V1_HASH,
    NAVIGATION_REGISTRY_HASH,
    load_compatibility_support,
    load_host_manifest,
    load_navigation_registry,
)


class BootstrapError(RuntimeError):
    """Bootstrap trust, descriptor, inventory, or launcher verification failed."""


def _safe_artifact_filename(value: str) -> str:
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        not value
        or posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or len(posix.parts) != 1
        or len(windows.parts) != 1
        or value in {".", ".."}
    ):
        raise BootstrapError(f"unsafe bootstrap artifact filename: {value!r}")
    return value


def _bounded_network_origins(values: Iterable[str]) -> tuple[str, ...]:
    origins = tuple(values)
    if not origins or len(set(origins)) != len(origins):
        raise BootstrapError("install plan requires unique bounded network origins")
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise BootstrapError(
                f"network origin must be an HTTPS origin without path/query: {origin!r}"
            )
    return origins


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BootstrapError(f"invalid descriptor timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise BootstrapError("descriptor timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_bootstrap_descriptor(
    descriptor: BootstrapDescriptorV1,
    *,
    trusted_source: str,
    signature_verified_by_external_bootstrap: bool,
    revoked: bool,
    now: str,
) -> tuple[bool, tuple[DiagnosticV1, ...]]:
    """Validate all 5A.1-checkable descriptor predicates.

    Signature verification is evidence supplied by a separately trusted
    pre-install verifier.  The installed engine cannot establish trust in the
    code that installed itself; real publisher keys and artifacts belong to
    the Phase 5A.5 release slice.
    """

    diagnostics: list[DiagnosticV1] = []
    if descriptor.canonical_source != trusted_source:
        diagnostics.append(
            DiagnosticV1(
                code="canonical_source_mismatch",
                severity="error",
                message="bootstrap descriptor differs from the selected trust root",
            )
        )
    if not signature_verified_by_external_bootstrap:
        diagnostics.append(
            DiagnosticV1(
                code="external_signature_verification_required",
                severity="error",
                message="a separately trusted pre-install verifier must verify the descriptor signature",
            )
        )
    if revoked:
        diagnostics.append(
            DiagnosticV1(
                code="release_revoked",
                severity="error",
                message="the selected release is revoked",
            )
        )
    issued = _parse_time(descriptor.issued_at)
    expires = _parse_time(descriptor.expires_at)
    observed = _parse_time(now)
    if issued >= expires:
        diagnostics.append(
            DiagnosticV1(
                code="descriptor_time_window_invalid",
                severity="error",
                message="descriptor expiry must follow issuance",
            )
        )
    if observed < issued:
        diagnostics.append(
            DiagnosticV1(
                code="descriptor_not_yet_valid",
                severity="error",
                message="the bootstrap descriptor is not yet valid",
            )
        )
    if observed >= expires:
        diagnostics.append(
            DiagnosticV1(
                code="descriptor_expired",
                severity="error",
                message="the bootstrap descriptor is expired",
            )
        )
    if descriptor.host_manifest_hash != HOST_MANIFEST_V1_HASH:
        diagnostics.append(
            DiagnosticV1(
                code="host_manifest_mismatch",
                severity="error",
                message="descriptor does not bind the installed host manifest",
            )
        )
    try:
        for artifact in descriptor.artifacts:
            _safe_artifact_filename(artifact.filename)
    except BootstrapError as exc:
        diagnostics.append(
            DiagnosticV1(
                code="artifact_filename_unsafe",
                severity="error",
                message=str(exc),
            )
        )
    return not any(item.severity == "error" for item in diagnostics), tuple(diagnostics)


def build_install_plan(
    descriptor: BootstrapDescriptorV1,
    *,
    environment_root: str | Path,
    absolute_launcher: str | Path,
    network_origins: Iterable[str],
    project_initialization_requested: bool = False,
    project_root: str | Path | None = None,
    project_name: str | None = None,
) -> InstallPlanV1:
    environment = Path(environment_root).expanduser().absolute()
    launcher = Path(absolute_launcher).expanduser().absolute()
    origins = _bounded_network_origins(network_origins)
    files = tuple(
        str(environment / _safe_artifact_filename(artifact.filename))
        for artifact in descriptor.artifacts
    )
    return InstallPlanV1(
        descriptor_hash=sha256_digest(canonical_json_bytes(descriptor)),
        release_version=descriptor.release_version,
        canonical_source=descriptor.canonical_source,
        installation_scope="user_isolated",
        environment_root=str(environment),
        absolute_launcher=str(launcher),
        network_origins=origins,
        files_to_create=files,
        project_initialization_requested=project_initialization_requested,
        project_root=(
            str(Path(project_root).expanduser().absolute())
            if project_root is not None
            else None
        ),
        project_name=project_name,
        requires_external_bootstrap_executor=True,
    )


def _source_repository_root() -> Path | None:
    candidate = Path(__file__).resolve().parents[3]
    if (candidate / "pyproject.toml").is_file() and (candidate / "routes").is_dir():
        return candidate
    return None


def _resource_files() -> tuple[tuple[str, Path], ...]:
    repository = _source_repository_root()
    if repository is not None:
        roots = ("routes", "schemas", "profiles", "craft", "machine")
        items = [
            (path.relative_to(repository).as_posix(), path)
            for name in roots
            for path in (repository / name).rglob("*")
            if path.is_file()
        ]
        return tuple(sorted(items))
    try:
        share = installed_resource_root()
    except DistributionResourceError as exc:
        raise BootstrapError("cannot locate installed engine resources") from exc
    return tuple(
        sorted(
            (
                path.relative_to(share).as_posix(),
                path,
            )
            for path in share.rglob("*")
            if path.is_file()
        )
    )


_GENERATED_INSTALL_METADATA = frozenset(
    {"RECORD", "INSTALLER", "REQUESTED", "direct_url.json"}
)


def _normalized_distribution_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _distribution_files(
    item: importlib.metadata.Distribution,
    *,
    share_root: Path | None,
) -> tuple[EngineResourceV1, ...]:
    """Hash normalized installed payload files, excluding generated launchers."""

    entries = item.files
    if not entries:
        raise BootstrapError(
            f"distribution has no verifiable installed-file inventory: {item.metadata['Name']}"
        )
    site_root = Path(item.locate_file("")).resolve(strict=False)
    files: list[EngineResourceV1] = []
    for entry in entries:
        entry_path = PurePosixPath(str(entry).replace("\\", "/"))
        if (
            entry_path.suffix == ".pyc"
            or "__pycache__" in entry_path.parts
            or entry_path.name in _GENERATED_INSTALL_METADATA
        ):
            continue
        resolved = Path(item.locate_file(entry)).resolve(strict=False)
        try:
            metadata = resolved.lstat()
        except FileNotFoundError as exc:
            raise BootstrapError(
                f"installed distribution file is missing: {entry_path.as_posix()}"
            ) from exc
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise BootstrapError(
                f"installed distribution file is not ordinary: {entry_path.as_posix()}"
            )
        if _is_within(resolved, site_root):
            logical = "site/" + resolved.relative_to(site_root).as_posix()
        elif share_root is not None and _is_within(resolved, share_root):
            logical = (
                "share/econ-theorist/"
                + resolved.relative_to(share_root).as_posix()
            )
        else:
            # Console launchers are installer-generated and may contain an
            # absolute shebang. Their semantic entry-point binding is carried
            # by the hashed dist-info metadata; absolute availability is
            # checked separately below.
            continue
        data = resolved.read_bytes()
        files.append(
            EngineResourceV1(
                logical_path=logical,
                sha256=sha256_digest(data),
                byte_size=len(data),
            )
        )
    files.sort(key=lambda value: value.logical_path)
    if not files or len({value.logical_path for value in files}) != len(files):
        raise BootstrapError("distribution file inventory is empty or ambiguous")
    return tuple(files)


def _source_distribution() -> InstalledDistributionV1:
    repository = _source_repository_root()
    if repository is None:  # pragma: no cover - caller invariant
        raise BootstrapError("source distribution requested outside a checkout")
    source_root = repository / "src" / "econ_theorist"
    files = tuple(
        EngineResourceV1(
            logical_path="site/econ_theorist/" + path.relative_to(source_root).as_posix(),
            sha256=sha256_digest(path.read_bytes()),
            byte_size=path.stat().st_size,
        )
        for path in sorted(source_root.rglob("*.py"))
    )
    return InstalledDistributionV1(
        name="econ-theorist-ai",
        version=__version__,
        files=files,
        file_inventory_hash=sha256_digest(canonical_json_bytes(files)),
    )


def _requirement_name(value: str) -> str | None:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", value)
    return None if match is None else _normalized_distribution_name(match.group(1))


def _source_dependency_graph() -> tuple[importlib.metadata.Distribution, ...]:
    pending = ["pydantic", "pydantic-core"]
    found: dict[str, importlib.metadata.Distribution] = {}
    while pending:
        name = _normalized_distribution_name(pending.pop())
        if name in found:
            continue
        try:
            item = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise BootstrapError(f"required distribution is unavailable: {name}") from exc
        canonical = _normalized_distribution_name(item.metadata["Name"])
        found[canonical] = item
        for requirement in item.requires or ():
            dependency = _requirement_name(requirement)
            if dependency is None or dependency in found:
                continue
            try:
                importlib.metadata.distribution(dependency)
            except importlib.metadata.PackageNotFoundError:
                # Optional/marker-false dependencies are not part of this
                # concrete interpreter's installed graph.
                continue
            pending.append(dependency)
    return tuple(found[name] for name in sorted(found))


def _installed_environment_distributions() -> tuple[importlib.metadata.Distribution, ...]:
    prefix = Path(sys.prefix).resolve(strict=False)
    found: dict[str, importlib.metadata.Distribution] = {}
    for item in importlib.metadata.distributions():
        root = Path(item.locate_file("")).resolve(strict=False)
        if not _is_within(root, prefix):
            continue
        name = _normalized_distribution_name(item.metadata["Name"])
        if name in found:
            raise BootstrapError(f"duplicate installed distribution: {name}")
        found[name] = item
    if "econ-theorist-ai" not in found:
        raise BootstrapError("installed engine distribution is unavailable")
    return tuple(found[name] for name in sorted(found))


def _installed_distribution_inventory(
    *,
    repository: Path | None,
    share_root: Path | None,
) -> tuple[InstalledDistributionV1, ...]:
    values: list[InstalledDistributionV1] = []
    if repository is not None:
        values.append(_source_distribution())
        distributions = _source_dependency_graph()
    else:
        distributions = _installed_environment_distributions()
    for item in distributions:
        files = _distribution_files(item, share_root=share_root)
        values.append(
            InstalledDistributionV1(
                name=_normalized_distribution_name(item.metadata["Name"]),
                version=item.version,
                files=files,
                file_inventory_hash=sha256_digest(canonical_json_bytes(files)),
            )
        )
    values.sort(key=lambda value: value.name)
    if len({value.name for value in values}) != len(values):
        raise BootstrapError("engine environment contains duplicate distributions")
    return tuple(values)


def build_engine_manifest(
    *, launcher_path: str | Path | None = None
) -> EngineManifestV1:
    """Inventory exact runtime paths, distributions, and policy resource bytes."""

    load_navigation_registry()
    load_host_manifest()
    load_compatibility_support()
    launcher = Path(
        launcher_path or shutil.which("etai") or sys.executable
    ).expanduser().absolute()
    repository = _source_repository_root()
    if repository is not None:
        install_mode = "development_checkout"
    else:
        try:
            importlib.metadata.distribution("econ-theorist-ai")
        except importlib.metadata.PackageNotFoundError:
            install_mode = "unknown"
        else:
            install_mode = "verified_release"
    package_root = Path(__file__).resolve().parents[1]
    resource_files = _resource_files()
    resources = tuple(
        EngineResourceV1(
            logical_path=logical,
            sha256=sha256_digest(path.read_bytes()),
            byte_size=path.stat().st_size,
        )
        for logical, path in resource_files
    )
    share_root = None
    if repository is None:
        try:
            share_root = installed_resource_root()
        except DistributionResourceError as exc:
            raise BootstrapError("cannot locate installed engine resources") from exc
    inventory = EngineReleaseInventoryV1(
        engine_version=__version__,
        distributions=_installed_distribution_inventory(
            repository=repository,
            share_root=share_root,
        ),
        resources=resources,
        host_manifest_hash=HOST_MANIFEST_V1_HASH,
        navigation_registry_hash=NAVIGATION_REGISTRY_HASH,
    )
    return EngineManifestV1(
        engine_version=__version__,
        python_executable=str(Path(sys.executable).absolute()),
        launcher_path=str(launcher),
        package_root=str(package_root),
        install_mode=install_mode,
        release_inventory=inventory,
        release_inventory_hash=sha256_digest(canonical_json_bytes(inventory)),
    )


@lru_cache(maxsize=1)
def current_engine_release_inventory_hash() -> str:
    """Return the host-neutral hash that binds code, schemas, and dependencies."""

    return build_engine_manifest().release_inventory_hash


@lru_cache(maxsize=1)
def current_engine_semantics_hash() -> str:
    """Hash host-neutral engine semantics for cross-platform work packets."""

    package_root = Path(__file__).resolve().parents[1]
    package_files = tuple(
        {
            "logical_path": "econ_theorist/" + path.relative_to(package_root).as_posix(),
            "sha256": sha256_digest(path.read_bytes()),
            "byte_size": path.stat().st_size,
        }
        for path in sorted(package_root.rglob("*.py"))
    )
    dependencies = tuple(
        {
            "name": _normalized_distribution_name(item.metadata["Name"]),
            "version": item.version,
        }
        for item in _source_dependency_graph()
    )
    resources = tuple(
        {
            "logical_path": logical,
            "sha256": sha256_digest(path.read_bytes()),
            "byte_size": path.stat().st_size,
        }
        for logical, path in _resource_files()
    )
    return sha256_digest(
        canonical_json_bytes(
            {
                "semantics_schema": "econ-theorist/engine-semantics/v1",
                "engine_version": __version__,
                "package_files": package_files,
                "dependency_versions": dependencies,
                "resources": resources,
                "host_manifest_hash": HOST_MANIFEST_V1_HASH,
                "navigation_registry_hash": NAVIGATION_REGISTRY_HASH,
            }
        )
    )


def verify_engine_inventory(
    *,
    project_root: str | Path | None = None,
    launcher_path: str | Path | None = None,
    expected_manifest_hash: str | None = None,
    external_bootstrap_verified: bool = False,
    release_manifest_hash: str | None = None,
) -> tuple[EngineManifestV1, EngineVerificationV1]:
    manifest = build_engine_manifest(launcher_path=launcher_path)
    manifest_hash = manifest.release_inventory_hash
    doctor = doctor_report(project_root)
    launcher = Path(manifest.launcher_path)
    launcher_ok = launcher.is_absolute() and launcher.is_file()
    diagnostics: list[DiagnosticV1] = []
    if not launcher_ok:
        diagnostics.append(
            DiagnosticV1(
                code="absolute_launcher_unavailable",
                severity="error",
                message="the verified absolute launcher is unavailable",
            )
        )
    if expected_manifest_hash is not None and expected_manifest_hash != manifest_hash:
        diagnostics.append(
            DiagnosticV1(
                code="engine_manifest_mismatch",
                severity="error",
                message="installed engine inventory differs from the expected manifest",
            )
        )
    if not doctor["required_ok"]:
        diagnostics.append(
            DiagnosticV1(
                code="doctor_required_check_failed",
                severity="error",
                message="one or more required engine diagnostics failed",
            )
        )
    functional = (
        launcher_ok
        and bool(doctor["required_ok"])
        and not any(item.severity == "error" for item in diagnostics)
    )
    if manifest.install_mode == "development_checkout":
        integrity = "development_only"
        verified = functional
    elif (
        manifest.install_mode != "verified_release"
        or not external_bootstrap_verified
        or expected_manifest_hash is None
    ):
        integrity = "external_bootstrap_required"
        verified = False
    else:
        integrity = "verified"
        verified = functional and expected_manifest_hash == manifest_hash
    if not verified and integrity == "verified":
        integrity = "failed"
    return manifest, EngineVerificationV1(
        verified=verified,
        release_integrity=integrity,  # type: ignore[arg-type]
        engine_manifest_hash=manifest_hash,
        expected_engine_inventory_hash=expected_manifest_hash,
        release_manifest_hash=release_manifest_hash,
        absolute_launcher_verified=launcher_ok,
        doctor_required_ok=bool(doctor["required_ok"]),
        diagnostics=tuple(diagnostics),
    )


def build_capability_receipt(
    *,
    host_product: str,
    host_version: str,
    adapter_id: str,
    adapter_version: str,
    execution_class: str,
    technically_accessible_roots: Iterable[str | Path],
    model_tool_isolation: str,
    trusted_human_channel: str,
    environment_redaction: str = "unavailable",
    credential_store_isolation: str = "unavailable",
    secret_file_denial: str = "unavailable",
    shadow_workspace_isolation: str = "unavailable",
    enforced_denied_compartments: Iterable[str] = (),
    observed_at: str | None = None,
) -> CapabilityReceiptV1:
    roots = tuple(
        str(Path(item).expanduser().absolute())
        for item in technically_accessible_roots
    )
    checks = (
        CapabilityV1(
            capability_id="python_runtime",
            available=sys.version_info >= (3, 11),
            required=True,
            evidence=platform.python_version(),
        ),
        CapabilityV1(
            capability_id="structured_process_invocation",
            available=True,
            required=True,
            evidence="host adapter declared machine JSON capture",
        ),
        CapabilityV1(
            capability_id="single_agent_topology",
            available=True,
            required=True,
            evidence="Phase 5A host manifest fixes topology=single",
        ),
    )
    return CapabilityReceiptV1(
        host_product=host_product,
        host_version=host_version,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        execution_class=execution_class,  # type: ignore[arg-type]
        technically_accessible_roots=roots,
        model_tool_isolation=model_tool_isolation,  # type: ignore[arg-type]
        trusted_human_channel=trusted_human_channel,  # type: ignore[arg-type]
        environment_redaction=environment_redaction,  # type: ignore[arg-type]
        credential_store_isolation=credential_store_isolation,  # type: ignore[arg-type]
        secret_file_denial=secret_file_denial,  # type: ignore[arg-type]
        shadow_workspace_isolation=shadow_workspace_isolation,  # type: ignore[arg-type]
        enforced_denied_compartments=tuple(
            sorted(set(enforced_denied_compartments))
        ),
        capabilities=checks,
        observed_at=observed_at or utc_now(),
    )


__all__ = [
    "BootstrapError",
    "build_capability_receipt",
    "build_engine_manifest",
    "build_install_plan",
    "current_engine_release_inventory_hash",
    "current_engine_semantics_hash",
    "validate_bootstrap_descriptor",
    "verify_engine_inventory",
]
