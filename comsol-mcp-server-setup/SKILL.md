---
name: comsol-mcp-server-setup
description: "Use when an agent needs to upgrade an existing comsol-mcp-automation skill so the host AI tool can drive COMSOL end-to-end through the open-source wjc9011 COMSOL MCP server (80+ MCP tools). This skill encodes the full setup recipe: shallow-clone the server, install it, register it in the host config, fix the local probe to discover COMSOL bundled JRE, and rewrite the skill runtime-mode decision tree so the MCP server is Priority 1. Reproducible across machines with no hardcoded paths."
---

# COMSOL MCP Server Setup

This skill takes an existing `comsol-mcp-automation` skill (which by default only knows about MPh, Java export, and `.mph` batch) and upgrades it with a fourth, higher-priority runtime mode: the wjc9011 COMSOL MCP server. After this skill runs, the host agent can build COMSOL models from scratch through MCP tool calls (`geometry_add_block`, `physics_add_heat_transfer`, `mesh_create`, `study_solve`, …) instead of writing Java or MPh by hand.

## When to use

Run this once per machine, when:

- The user's `comsol-mcp-automation` skill exists but only mentions MPh / Java export / batch.
- COMSOL Multiphysics is installed (5.x or 6.x).
- The host agent supports stdio MCP servers and has a JSON config with an `mcpServers` section (Claude Code's `~/.claude.json`, opencode's `opencode.json`, etc.).

Skip if the MCP server is already registered — the upgraded probe will say `recommendation: mcp_server_ready`.

## Prerequisites the agent must verify first

1. **Run the existing probe** (`<skill_root>/comsol-mcp-automation/scripts/probe_comsol_env.py`). Capture:
   - `comsol_roots[0]` — the install root
   - `mph.available` — should be true
   - whether `java` is on PATH (often false on Windows; that's fine — see step 4)
2. If COMSOL is not detected, stop and ask the user for the install root. Do not guess.
3. Identify the host's MCP config file (`~/.claude.json`, `opencode.json`, etc.) and the Python interpreter where the MCP server should land. Get user confirmation on the clone target directory — the repo is large.

## Steps

### 1. Shallow-clone the MCP server

The repo is ~491 MB because it ships a PDF knowledge base. **Always shallow-clone**, otherwise the full-history clone can balloon past 800 MB and stall on slow networks.

```bash
git clone --depth 1 --single-branch --branch main \
  https://github.com/wjc9011/COMSOL_Multiphysics_MCP.git \
  <user-chosen-target-dir>/COMSOL_Multiphysics_MCP
```

If a previous full clone is already in progress and stuck, `TaskStop` it and `rm -rf` the partial directory first.

### 2. Install in editable mode

```bash
cd <target-dir>/COMSOL_Multiphysics_MCP
python -m pip install -e .
```

This pulls heavy deps: `mcp`, `mph`, `pydantic`, `pymupdf`, `chromadb`, `sentence-transformers`, `torch`. Expect ~600 MB of wheels. Use a Python ≥3.10 that is **not** the Windows Store build.

After install, the entry point script `comsol-mcp` (or `comsol-mcp.exe` on Windows) appears in the interpreter's `Scripts/` (Windows) or `bin/` (Unix) directory. Resolve its absolute path with `python -c "import shutil; print(shutil.which('comsol-mcp'))"`.

### 3. Register in the host's MCP config

Back up the config first (`cp <config> <config>.before_comsol_mcp`), then merge a `comsol` entry under `mcpServers`. Use stdio mode and inject `JAVA_HOME` pointing at COMSOL's bundled JRE so the server doesn't need system Java.

JSON shape (Claude Code `~/.claude.json`):

```json
"comsol": {
  "type": "stdio",
  "command": "<absolute path to comsol-mcp executable>",
  "args": [],
  "env": {
    "JAVA_HOME": "<COMSOL_ROOT>/java/win64/jre",
    "HF_ENDPOINT": "https://hf-mirror.com"
  }
}
```

Notes:
- On Windows, `<COMSOL_ROOT>/java/win64/jre/bin/java.exe` is the bundled OpenJDK 11 — works for MPh.
- On Linux/macOS the bundled JRE path is different (`<root>/java/<arch>/jre`); detect with the probe.
- `HF_ENDPOINT` is optional but recommended in regions where huggingface.co is slow — the server's PDF semantic search downloads sentence-transformers on first start.

Use a Python script (encoding="utf-8") to mutate the JSON — do not hand-edit if the file contains non-ASCII content.

### 4. Upgrade the local probe

The default `probe_comsol_env.py` reports Java as unavailable when it's not on PATH, even though COMSOL ships its own JRE. It also doesn't know about the MCP server. Three patches needed — see `references/probe-patch.md` for the exact diff:

1. Add `_bundled_jre(roots)` and have `get_java_info` accept the roots, fall back to `<root>/java/win64/jre/bin/java.exe`, and report a `source` field (`PATH` / `comsol_bundled_jre`).
2. Add `get_mcp_server_info()`: reads the host's MCP config, checks if any `mcpServers` key contains "comsol", and tries `importlib.util.find_spec("comsol_mcp")`.
3. Add a new top-priority recommendation: `mcp_server_ready` when COMSOL roots exist AND the MCP server is registered.

### 5. Rewrite the skill's decision tree

In the existing `comsol-mcp-automation` skill, three files need updates — see `references/skill-edits.md` for exact instructions:

1. `SKILL.md` — promote MCP server to Priority 1 in the runtime-mode list; mention the bundled JRE in the probe checklist.
2. `references/runtime-modes.md` — insert a new §1 "MCP Server" describing when to pick it; renumber the existing three modes; update the four-line selection heuristic.
3. New file `references/mcp-server.md` — full 80+ tool catalogue grouped by Session / Model / Geometry / Physics / Mesh / Study / Results / Knowledge, plus install steps and known limitations (mesh control is shallow → fall back to Java export for swept layers / boundary-layer meshes).

### 6. Verify

Re-run the probe. Expected output:

```
Java: source: comsol_bundled_jre
COMSOL MCP server (wjc9011): registered: ['comsol']
Recommendation: mcp_server_ready
```

Then **restart the host agent**. After restart, MCP tools named `mcp__comsol__*` (or your host's namespacing equivalent) should appear: `model_create`, `geometry_add_block`, `geometry_boolean_union`, `physics_add_heat_transfer`, `physics_configure_boundary`, `multiphysics_add`, `mesh_create`, `study_solve`, `study_solve_async`, `results_evaluate`, `results_export_image`, etc.

## Rollback

The setup writes exactly two reversible artifacts:

1. The MCP server config block in `~/.claude.json` (or equivalent). To remove: restore the `.before_comsol_mcp` backup.
2. The `comsol-mcp` package installed editable from the clone. To remove: `python -m pip uninstall comsol-mcp` and `rm -rf` the clone.

The probe and SKILL edits are local skill files; revert via git or by re-pasting the original.

## Known pitfalls

- **Repo size**: ~491 MB upstream. Always `--depth 1`. A full clone has been observed to grow to 400 MB+ before checkout starts and feels stuck.
- **One COMSOL client per Python process**: the server is singleton inside its process. If a session goes bad, restart the MCP server process — do not spawn a second client in the same process.
- **JVM Startup Hang inside FastMCP**: On Windows, initializing the JVM (`jpype.startJVM()` or `mph.Client()`) inside a synchronous tool handler will deadlock/hang indefinitely because FastMCP executes the tool in an AnyIO worker thread. To solve this, always pre-initialize the COMSOL session (`session_manager.start()`) on the main thread in `src/server.py` before calling `mcp.run()`.
- **Mesh control is shallow**: only `mesh_create` / `_list` / `_info`. For sequences with size, distribution, swept layers, or boundary-layer meshes, fall back to Java export.
- **First start is slow**: sentence-transformers downloads model weights from huggingface; set `HF_ENDPOINT` to a mirror in restricted networks. On this machine, the model is already cached and data lives on `D:\COMSOL_MCP_Data\` (see `comsol-mcp-automation/references/mcp-server.md` for full path details).
- **Optional deps are required by pyproject**: `chromadb`/`sentence-transformers`/`torch` are listed as required even though the README calls them optional. Don't try to install without them — pip will fail. If the user wants a slim install, fork the repo and remove them from `pyproject.toml`.

## References

- `references/probe-patch.md` — exact code blocks to add/replace in `probe_comsol_env.py`.
- `references/skill-edits.md` — the SKILL.md / runtime-modes.md / mcp-server.md edits, copy-pasteable.
- `references/tool-catalogue.md` — full 80+ MCP tool reference.
- Upstream: <https://github.com/wjc9011/COMSOL_Multiphysics_MCP>
