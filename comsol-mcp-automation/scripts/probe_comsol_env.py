from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None  # type: ignore

try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None  # type: ignore


DOC_RELATIVE_PATHS = [
    Path("doc/pdf/COMSOL_Multiphysics/ApplicationProgrammingGuide.pdf"),
    Path("doc/pdf/COMSOL_Multiphysics/COMSOL_ProgrammingReferenceManual.pdf"),
    Path("doc/help/wtpwebapps/ROOT/doc/com.comsol.help.comsol/api/com/comsol/model/util/ModelUtil.html"),
]

REPO_ROOT = Path(__file__).resolve().parents[2]


def _unique_existing(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        try:
            resolved = str(path.resolve())
        except OSError:
            resolved = str(path)
        if resolved in seen or not path.exists():
            continue
        seen.add(resolved)
        result.append(path)
    return result


def _coerce_root(path: Path) -> Path | None:
    candidates = [path]
    candidates.extend(path.parents)
    for candidate in candidates:
        if (candidate / "Multiphysics" / "applications").exists():
            return candidate / "Multiphysics"
        if (candidate / "applications").exists() and (candidate / "bin" / "win64").exists():
            return candidate
    return None


def _from_registry() -> list[Path]:
    if winreg is None:
        return []

    roots: list[Path] = []
    uninstall_roots = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]

    for hive in hives:
        for uninstall_root in uninstall_roots:
            try:
                with winreg.OpenKey(hive, uninstall_root) as root_key:
                    count, _, _ = winreg.QueryInfoKey(root_key)
                    for index in range(count):
                        subkey_name = winreg.EnumKey(root_key, index)
                        if "COMSOL" not in subkey_name.upper():
                            continue
                        try:
                            with winreg.OpenKey(root_key, subkey_name) as subkey:
                                for value_name in ("InstallLocation", "UninstallString"):
                                    try:
                                        value, _ = winreg.QueryValueEx(subkey, value_name)
                                    except OSError:
                                        continue
                                    root = _path_from_registry_value(str(value))
                                    if root is not None:
                                        roots.append(root)
                        except OSError:
                            continue
            except OSError:
                continue
    return _unique_existing(roots)


def _path_from_registry_value(value: str) -> Path | None:
    direct = _coerce_root(Path(value.strip('"')))
    if direct is not None:
        return direct

    match = re.search(r"([A-Za-z]:\\[^\"\r\n]+)", value)
    if not match:
        return None
    raw = Path(match.group(1))
    return _coerce_root(raw)


def _from_common_locations() -> list[Path]:
    roots: list[Path] = []
    for drive in ("C", "D", "E", "F", "G"):
        top_level = Path(f"{drive}:\\")
        if not top_level.exists():
            continue

        program_files = top_level / "Program Files"
        if program_files.exists():
            roots.extend(_scan_for_comsol(program_files))

        roots.extend(_scan_for_comsol(top_level))
    return _unique_existing(roots)


def _scan_for_comsol(base: Path) -> list[Path]:
    roots: list[Path] = []
    try:
        children = list(base.iterdir())
    except OSError:
        return roots

    for child in children:
        if not child.is_dir():
            continue
        if "COMSOL" not in child.name.upper():
            continue
        for candidate in (child, child / "Multiphysics"):
            root = _coerce_root(candidate)
            if root is not None:
                roots.append(root)
        try:
            grandchildren = list(child.iterdir())
        except OSError:
            continue
        for grandchild in grandchildren:
            if not grandchild.is_dir():
                continue
            root = _coerce_root(grandchild)
            if root is not None:
                roots.append(root)
    return roots


def find_comsol_roots() -> list[Path]:
    roots: list[Path] = []
    for env_name in ("COMSOL_ROOT", "COMSOL_HOME"):
        value = os.environ.get(env_name)
        if value:
            root = _coerce_root(Path(value))
            if root is not None:
                roots.append(root)
    roots.extend(_from_registry())
    roots.extend(_from_common_locations())
    return _unique_existing(roots)


def get_mph_info() -> dict[str, object]:
    info: dict[str, object] = {"available": False}
    try:
        import mph  # type: ignore

        info["available"] = True
        info["module_path"] = str(Path(mph.__file__).resolve())
        try:
            info["version"] = importlib.metadata.version("mph")
        except importlib.metadata.PackageNotFoundError:
            info["version"] = getattr(mph, "__version__", "unknown")
    except Exception as exc:
        info["error"] = str(exc)
    return info


def _bundled_jre(roots: list[Path]) -> Path | None:
    for root in roots:
        # Windows path; on Linux/macOS use root/java/<arch>/jre/bin/java
        candidate = root / "java" / "win64" / "jre" / "bin" / "java.exe"
        if candidate.exists():
            return candidate
    return None


def get_java_info(comsol_roots: list[Path] | None = None) -> dict[str, object]:
    java = shutil.which("java")
    source = "PATH" if java else None

    if java is None and comsol_roots:
        bundled = _bundled_jre(comsol_roots)
        if bundled is not None:
            java = str(bundled)
            source = "comsol_bundled_jre"

    info: dict[str, object] = {
        "available": java is not None,
        "path": java,
        "source": source,
        "java_home": os.environ.get("JAVA_HOME"),
    }
    if java is None:
        return info

    try:
        completed = subprocess.run(
            [java, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        output = (completed.stderr or completed.stdout).strip().splitlines()
        if output:
            info["version_output"] = output[0]
    except Exception as exc:
        info["error"] = str(exc)
    return info


def get_toolkit_candidates() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ("COMSOL_AUTOMATION_ROOT",):
        value = os.environ.get(env_name)
        if value:
            candidates.append(Path(value))

    candidates.extend(
        [
            REPO_ROOT / "comsol",
            REPO_ROOT / "COMSOL_Multiphysics_MCP",
            Path.cwd() / "comsol",
            Path.cwd() / "COMSOL_Multiphysics_MCP",
            Path.cwd().parent / "comsol",
            Path.cwd().parent / "COMSOL_Multiphysics_MCP",
        ]
    )
    return _unique_existing(candidates)


def get_mcp_server_info() -> dict[str, object]:
    """Detect whether the wjc9011 COMSOL MCP server is installed/registered."""
    info: dict[str, object] = {
        "package_importable": False,
        "registered_in_claude_json": False,
        "registered_in_codex_config": False,
        "local_clones": [],
    }
    try:
        import importlib.util

        for pkg_name in ("comsol_mcp", "src"):
            spec = importlib.util.find_spec(pkg_name)
            if spec is not None and spec.origin is not None:
                origin = str(spec.origin)
                # Accept src only if it belongs to a COMSOL MCP repo
                if pkg_name == "src" and "COMSOL" not in origin.upper():
                    continue
                info["package_importable"] = True
                info["package_origin"] = origin
                info["package_name"] = pkg_name
                break
    except Exception as exc:
        info["package_error"] = str(exc)

    config_path = Path.home() / ".claude.json"
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as fh:
                config = json.load(fh)
            servers = (config.get("mcpServers") or {}).keys()
            project_servers: list[str] = []
            for proj in (config.get("projects") or {}).values():
                if isinstance(proj, dict):
                    project_servers.extend((proj.get("mcpServers") or {}).keys())
            all_names = list(servers) + project_servers
            comsol_names = [n for n in all_names if "comsol" in n.lower()]
            if comsol_names:
                info["registered_in_claude_json"] = True
                info["registered_names"] = comsol_names
                info["registered_configs"] = [str(config_path)]
        except Exception as exc:
            info["config_error"] = str(exc)

    # Also check settings.local.json
    local_config = Path.home() / ".claude" / "settings.local.json"
    if local_config.exists():
        try:
            with open(local_config, encoding="utf-8") as fh:
                local = json.load(fh)
            local_servers = (local.get("mcpServers") or {}).keys()
            local_comsol = [n for n in local_servers if "comsol" in n.lower()]
            if local_comsol:
                info["registered_in_claude_json"] = True
                existing = info.get("registered_names", [])
                info["registered_names"] = existing + local_comsol
                configs = info.get("registered_configs", [])
                info["registered_configs"] = configs + [str(local_config)]
        except Exception:
            pass

    codex_config = Path.home() / ".codex" / "config.toml"
    if codex_config.exists() and tomllib is not None:
        try:
            with open(codex_config, "rb") as fh:
                codex = tomllib.load(fh)
            codex_servers = (codex.get("mcp_servers") or {}).keys()
            codex_comsol = [n for n in codex_servers if "comsol" in n.lower()]
            if codex_comsol:
                info["registered_in_codex_config"] = True
                existing = info.get("registered_names", [])
                info["registered_names"] = existing + codex_comsol
                configs = info.get("registered_configs", [])
                info["registered_configs"] = configs + [str(codex_config)]
        except Exception as exc:
            info["codex_config_error"] = str(exc)

    # Also check opencode.json
    opencode_config = Path.home() / ".config" / "opencode" / "opencode.json"
    if opencode_config.exists():
        try:
            with open(opencode_config, encoding="utf-8") as fh:
                oc = json.load(fh)
            oc_servers = (oc.get("mcpServers") or {}).keys()
            oc_comsol = [n for n in oc_servers if "comsol" in n.lower()]
            if oc_comsol:
                info["registered_in_claude_json"] = True
                existing = info.get("registered_names", [])
                info["registered_names"] = existing + oc_comsol
                configs = info.get("registered_configs", [])
                info["registered_configs"] = configs + [str(opencode_config)]
        except Exception:
            pass

    candidates = [
        Path(os.environ.get("COMSOL_AUTOMATION_ROOT", "") or ".") / "COMSOL_Multiphysics_MCP",
        Path("D:/code/COMSOL_Multiphysics_MCP"),
        Path.home() / "code" / "COMSOL_Multiphysics_MCP",
        Path.home() / "COMSOL_Multiphysics_MCP",
    ]
    info["local_clones"] = [str(p) for p in _unique_existing(candidates)]
    return info


def build_report() -> dict[str, object]:
    roots = find_comsol_roots()
    toolkits = get_toolkit_candidates()
    mph_info = get_mph_info()
    java_info = get_java_info(roots)
    mcp_info = get_mcp_server_info()

    docs: list[str] = []
    example_library: str | None = None
    if roots:
        root = roots[0]
        app_lib = root / "applications"
        if app_lib.exists():
            example_library = str(app_lib)
        for rel in DOC_RELATIVE_PATHS:
            candidate = root / rel
            if candidate.exists():
                docs.append(str(candidate))

    recommendation = "manual_setup_needed"
    if roots and (mcp_info.get("registered_in_claude_json") or mcp_info.get("registered_in_codex_config")):
        recommendation = "mcp_server_ready"
    elif roots and mph_info.get("available"):
        recommendation = "direct_mph_ready"
    elif roots:
        recommendation = "java_or_batch_ready"
    elif toolkits:
        recommendation = "toolkit_present_but_comsol_missing"

    return {
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "comsol_roots": [str(path) for path in roots],
        "example_library": example_library,
        "docs_found": docs,
        "mph": mph_info,
        "java": java_info,
        "mcp_server": mcp_info,
        "toolkits": [str(path) for path in toolkits],
        "recommendation": recommendation,
    }


def print_human(report: dict[str, object]) -> None:
    print("COMSOL automation environment probe")
    print("=" * 40)
    print(f"Python: {report['python']['executable']}")
    print(f"Version: {report['python']['version']} on {report['python']['platform']}")
    print()

    roots = report["comsol_roots"]
    print("COMSOL roots:")
    if roots:
        for root in roots:
            print(f"  - {root}")
    else:
        print("  - none found")

    example_library = report.get("example_library")
    if example_library:
        print(f"Example library: {example_library}")

    docs = report["docs_found"]
    print("Docs:")
    if docs:
        for doc in docs:
            print(f"  - {doc}")
    else:
        print("  - no standard docs found under detected roots")

    mph_info = report["mph"]
    print("MPh:")
    if mph_info.get("available"):
        print(f"  - available: {mph_info.get('version', 'unknown')}")
        print(f"  - module path: {mph_info.get('module_path')}")
    else:
        print(f"  - unavailable: {mph_info.get('error', 'not installed')}")

    java_info = report["java"]
    print("Java:")
    if java_info.get("available"):
        src = java_info.get("source", "PATH")
        print(f"  - source: {src}")
        print(f"  - path: {java_info.get('path')}")
        if java_info.get("version_output"):
            print(f"  - {java_info['version_output']}")
    else:
        print("  - not found on PATH or in COMSOL bundled JRE")

    mcp_info = report.get("mcp_server", {})
    print("COMSOL MCP server (wjc9011):")
    if mcp_info.get("package_importable"):
        origin = mcp_info.get("package_origin", "unknown")
        print(f"  - package: importable ({origin})")
    else:
        print("  - package: not importable")
    if mcp_info.get("registered_in_claude_json") or mcp_info.get("registered_in_codex_config"):
        names = mcp_info.get("registered_names", [])
        print(f"  - registered: {names}")
        configs = mcp_info.get("registered_configs", [])
        if configs:
            print(f"  - configs: {configs}")
    else:
        print("  - not registered in host MCP config")
    clones = mcp_info.get("local_clones", [])
    if clones:
        print("  - local clones:")
        for c in clones:
            print(f"    - {c}")

    toolkits = report["toolkits"]
    print("Local toolkits:")
    if toolkits:
        for toolkit in toolkits:
            print(f"  - {toolkit}")
    else:
        print("  - none found")

    print()
    print(f"Recommendation: {report['recommendation']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe the local COMSOL automation environment.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
