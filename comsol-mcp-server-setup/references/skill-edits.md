# Skill Edits — upgrade `comsol-mcp-automation` to four runtime modes

After installing and registering the MCP server, three skill files need rewrites so the agent picks the new mode automatically.

## 1. `SKILL.md` — frontmatter and Quick Start

Update the `description` line so it lists four runtime modes instead of three:

> Use when the user wants to automate COMSOL Multiphysics on this Windows machine through an **MCP server**, MPh, Java export, or batch workflows: …

In the Quick Start, replace the three-mode list with the four-mode priority order:

```markdown
2. Choose the runtime mode deliberately, in this priority order:
   - **MCP server (`wjc9011/COMSOL_Multiphysics_MCP`)** when the probe reports `registered_in_claude_json: true` — most complete path for from-scratch automation.
   - direct MPh control when MCP server is not registered but `mph` imports.
   - Java export plus `comsolcompile` / `comsolbatch` for GUI-validated models or when MPh's high-level API is too narrow.
   - existing `.mph` batch runs when only parameters/studies/exports change.
```

In the "Probe first" checklist, add two bullets:

```markdown
- Is the **wjc9011 COMSOL MCP server** registered in `~/.claude.json` (`mcp_server.registered_in_claude_json`)?
- Is Java available — either on PATH/JAVA_HOME, or as the COMSOL-bundled JRE under `<root>/java/win64/jre/bin/java.exe` (`java.source == comsol_bundled_jre`)?
```

And after the checklist:

> If `java.available` is false but a COMSOL root was detected, tell the user the bundled JRE path so they can set `JAVA_HOME` or call it directly — do not claim Java is unavailable.

In the "Choose execution path" section, list the MCP server first with its tool names; keep MPh / Java export / batch as fallbacks.

In the "Use the direct MPh sequence" section, retitle to "Use the MCP server or direct MPh sequence" and explicitly note: *if MPh is the only option, drop to `model.java` for boolean ops, physics interface registration, materials, named selections, and mesh sequences — these are not stable in MPh's high-level API.*

In the References list at the bottom, add `references/mcp-server.md`.

## 2. `references/runtime-modes.md` — insert §1, renumber

Insert a new first section:

```markdown
## 1. MCP Server (wjc9011/COMSOL_Multiphysics_MCP)

Choose this when:

- the probe reports `mcp_server.registered_in_claude_json: true`
- the task involves building geometry, adding physics, or meshing from scratch
- the user's intent is conversational ("build me a model that...") rather than scripted

Good fits:

- end-to-end build: primitives → booleans → physics → BCs → materials → mesh → solve → export
- multiphysics couplings via `multiphysics_add`
- async long solves via `study_solve_async` + `study_get_progress`

Avoid this when:

- the model is already validated and only needs sweeps / re-exports — use `.mph` batch instead
- the task needs mesh sequences with explicit size / distribution / swept layers / boundary-layer meshes — the MCP server's mesh surface is shallow; fall back to Java export

See [mcp-server.md](mcp-server.md) for the full tool catalogue.
```

Renumber the existing "Direct MPh Control" → §2, "Java Export Plus COMSOL Batch" → §3, "Existing `.mph` Batch Runs" → §4.

Update the "Selection Heuristic" section to four steps:

```markdown
1. If the wjc9011 MCP server is registered AND the task is from-scratch modeling, use the MCP server.
2. If a stable `.mph` already exists and the structure is not changing, use batch mode.
3. If the user needs exact reproduction of a complex Desktop model or detailed mesh sequences, use Java export.
4. If the user needs fast edits, scripted sweeps, or lightweight automation and the MCP server is not available, use direct MPh.
```

Renumber the "Companion Skill Boundary" section to §6.

## 3. New file `references/mcp-server.md`

Create with this content (adapt path placeholders to the local machine):

```markdown
# wjc9011 COMSOL MCP Server

Reference for the most complete from-scratch automation path.

Upstream: https://github.com/wjc9011/COMSOL_Multiphysics_MCP

## When to prefer it

- end-to-end build from natural language
- boolean geometry, multiple physics, or coupled physics
- MPh's high-level API would force frequent drops to `model.java`

Skip when the model is validated and only needs sweeps/exports.

## Install

```bash
git clone --depth 1 --single-branch --branch main \
  https://github.com/wjc9011/COMSOL_Multiphysics_MCP.git
cd COMSOL_Multiphysics_MCP
python -m pip install -e .
```

Repo is ~491 MB (PDF knowledge base committed). Always shallow-clone.

**This machine note**: Data has been moved off C drive. PDF and knowledge base data lives on `D:\COMSOL_MCP_Data\` with junction links from the repo. See `comsol-mcp-automation/references/mcp-server.md` for current paths.

Register in host MCP config (~/.claude.json or equivalent) under `mcpServers`:

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

Restart the host agent after editing.

## Tool catalogue

See `references/tool-catalogue.md` (in `comsol-mcp-server-setup`) — Session (4) / Model (9) / Geometry (14) / Physics (16) / Mesh (3) / Study (8) / Results (9) / Knowledge (8).

## Known limitations

- One COMSOL client per Python process (singleton).
- Mesh control is shallow (3 tools, auto-mesh oriented). For mesh sequences with size, distribution, swept layers, or boundary-layer meshes, fall back to Java export.
- First start is slow — sentence-transformers model download.
```
