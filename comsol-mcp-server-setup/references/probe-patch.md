# Probe Patch — `comsol-mcp-automation/scripts/probe_comsol_env.py`

Three changes required so the probe (a) finds COMSOL's bundled JRE without polluting PATH, and (b) reports whether the wjc9011 MCP server is registered.

## 1. Java fallback to bundled JRE

Add a helper and change the signature of `get_java_info`.

**Before:**

```python
def get_java_info() -> dict[str, object]:
    java = shutil.which("java")
    info: dict[str, object] = {
        "available": java is not None,
        "path": java,
        "java_home": os.environ.get("JAVA_HOME"),
    }
    if java is None:
        return info
    # ... unchanged version-output block ...
```

**After:**

```python
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
    # ... keep existing version-output subprocess block ...
```

Then in `build_report()` change `get_java_info()` → `get_java_info(roots)`.

In the human-readable printer, surface `source`:

```python
print(f"  - source: {java_info.get('source')}")
```

## 2. MCP server detection

Add a new function:

```python
def get_mcp_server_info() -> dict[str, object]:
    """Detect whether the wjc9011 COMSOL MCP server is installed/registered."""
    info: dict[str, object] = {
        "package_importable": False,
        "registered_in_claude_json": False,
        "local_clones": [],
    }
    try:
        import importlib.util
        spec = importlib.util.find_spec("comsol_mcp")
        if spec is not None:
            info["package_importable"] = True
            info["package_origin"] = getattr(spec, "origin", None)
    except Exception as exc:
        info["package_error"] = str(exc)

    config_path = Path.home() / ".claude.json"  # adapt for opencode etc.
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
        except Exception as exc:
            info["config_error"] = str(exc)

    candidates = [
        Path.cwd() / "COMSOL_Multiphysics_MCP",
        Path.home() / "COMSOL_Multiphysics_MCP",
    ]
    info["local_clones"] = [str(p) for p in candidates if p.exists()]
    return info
```

Wire it into `build_report()`:

```python
mcp_info = get_mcp_server_info()
# ... existing report dict ...
"mcp_server": mcp_info,
```

## 3. Promote `mcp_server_ready` to Priority 1 in recommendation

```python
recommendation = "manual_setup_needed"
if roots and mcp_info.get("registered_in_claude_json"):
    recommendation = "mcp_server_ready"
elif roots and mph_info.get("available"):
    recommendation = "direct_mph_ready"
elif roots:
    recommendation = "java_or_batch_ready"
elif toolkits:
    recommendation = "toolkit_present_but_comsol_missing"
```

Also extend `print_human` with an "MCP server" section before "Local toolkits".

## Verification

After patching, the probe on a freshly-set-up machine should print:

```
Java:
  - path: <COMSOL_ROOT>/java/win64/jre/bin/java.exe
  - source: comsol_bundled_jre
  - openjdk version "11.0.x" ...
COMSOL MCP server (wjc9011):
  - registered: ['comsol']
Recommendation: mcp_server_ready
```
