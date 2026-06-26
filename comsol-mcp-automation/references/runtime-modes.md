# Runtime Modes

Use this file to decide how to automate COMSOL on the current machine.

## 1. MCP Server (wjc9011/COMSOL_Multiphysics_MCP)

Choose this when:

- the probe reports `mcp_server.registered_in_claude_json: true` AND `recommendation: mcp_server_ready`
- the task involves building geometry, adding physics, or meshing from scratch
- the user's intent is conversational ("build me a model that...") rather than scripted
- you need boolean geometry, multiple physics, or multiphysics couplings

Good fits:

- end-to-end build: primitives → booleans → physics → BCs → materials → mesh → solve → export
- multiphysics couplings via `multiphysics_add`
- async long solves via `study_solve_async` + `study_get_progress`
- from-scratch conversational modeling

Avoid this when:

- the model is already validated and only needs sweeps / re-exports — use `.mph` batch instead
- the task needs mesh sequences with explicit size / distribution / swept layers / boundary-layer meshes — the MCP server's mesh surface is shallow; fall back to Java export
- the probe reports `recommendation` is NOT `mcp_server_ready`

See [mcp-server.md](mcp-server.md) for the full tool catalogue and known limitations.

## 2. Direct MPh Control

Choose this when:

- `mph` imports successfully in the current Python environment
- the MCP server is NOT registered
- the user wants quick scripted edits
- the model is small or medium and can be recreated or modified incrementally
- you need to evaluate expressions, export results, or run modest parameter sweeps

Good fits:

- load a model, change a few parameters, solve, and export data
- create a compact scripted model from scratch
- inspect studies, datasets, plots, or parameter tables

Avoid this when:

- the Desktop model already has many fragile tags and selections
- the workflow depends on exact GUI-generated objects that are painful to recreate by hand
- long production runs matter more than interactive iteration
- the MCP server is available (prefer MCP server for from-scratch builds)

## 3. Java Export Plus COMSOL Batch

Choose this when:

- a validated COMSOL Desktop model already exists
- selections, couplings, or geometry details are fragile
- the MCP server's mesh surface is too shallow (swept layers, boundary-layer meshes)
- the user needs a robust automation baseline that mirrors a GUI-validated model
- you expect to compile and rerun the same logic repeatedly

Good fits:

- large models with many selections
- workflows where exact node tags matter
- long-lived automation around a fixed model family

Default rule:

- export Java from the working model first
- patch the generated code minimally
- use `comsolcompile` and `comsolbatch` around that exported baseline

## 4. Existing `.mph` Batch Runs

Choose this when:

- the `.mph` model already works
- only parameters, studies, or exports need to change
- the task is repetitive or throughput-oriented

Good fits:

- repeated reruns of a stable model
- overnight sweeps
- regenerating tables, reports, or plots from an existing baseline

Avoid this when:

- the physics tree still changes frequently
- you need deep scripted introspection or structural model edits

## 5. Selection Heuristic

Use this order when unsure:

1. If the wjc9011 MCP server is registered AND the task is from-scratch modeling, use the MCP server.
2. If a stable `.mph` already exists and the structure is not changing, use batch mode.
3. If the user needs exact reproduction of a complex Desktop model or detailed mesh sequences, use Java export.
4. If the user needs fast edits, scripted sweeps, or lightweight automation and the MCP server is not available, use direct MPh.

## 6. Companion Skill Boundary

If the core problem is still "which COMSOL example or coupling family should I start from", use `comsol-electrochem-fluid` first.
Once the modeling family is chosen, this skill takes over for execution, orchestration, and automation.
