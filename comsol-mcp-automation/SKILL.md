---
name: comsol-mcp-automation
description: 'Use when the user wants to automate COMSOL Multiphysics on this Windows machine through an MCP server (80+ tools: geometry, physics, BCs, materials, mesh, solve, results), MPh, Java export, or batch workflows: probe the local COMSOL environment, start or connect sessions, load or create models, change parameters, build geometry, assign physics or boundary conditions, mesh, solve, extract results, export artifacts, or search installed COMSOL documentation. Prefer this skill for direct automation and execution-path decisions between MCP server, MPh, Java export, and existing .mph batch runs. Combine with comsol-electrochem-fluid when the task also needs domain-specific electrochemistry or flow example selection.'
---

# COMSOL MCP Automation

## Quick Start

1. Probe the machine before assuming any COMSOL path, Python package, Java runtime, or local toolkit location.
2. Choose the runtime mode deliberately, in this priority order:
   - **MCP server (`wjc9011/COMSOL_Multiphysics_MCP`)** when the probe reports `registered_in_claude_json: true` - most complete path for from-scratch conversational automation (80+ tools).
   - direct MPh control when MCP server is not registered but `mph` imports.
   - Java export plus `comsolcompile` or `comsolbatch` for GUI-validated models or when MPh's high-level API is too narrow.
   - existing `.mph` batch runs when the model is already stable and only inputs or outputs change.
3. If the user is still deciding which COMSOL example or coupling family to start from, combine this skill with `comsol-electrochem-fluid` first.
4. Keep four items explicit in every automation task:
   - model source
   - parameters to change
   - study or solve target
   - required outputs

## Workflow

### 1. Probe the local environment first

Run the bundled probe script:

```powershell
python "$env:USERPROFILE\.agents\skills\comsol-mcp-automation\scripts\probe_comsol_env.py"
python "$env:USERPROFILE\.agents\skills\comsol-mcp-automation\scripts\probe_comsol_env.py" --json
```

If `python` is not on `PATH`, use the full interpreter path instead of the literal `python` command.

Use the probe results to answer these questions before you automate anything:

- Is COMSOL installed on this machine, and where is the best root path?
- Is the **wjc9011 COMSOL MCP server** registered in `~/.claude.json` (`mcp_server.registered_in_claude_json`)?
- Is `mph` importable in the current Python environment?
- Is Java available - either on PATH/JAVA_HOME, or as the COMSOL-bundled JRE under `<root>/java/win64/jre/bin/java.exe` (`java.source == comsol_bundled_jre`)?
- Are COMSOL docs and the application library present under the detected root?
- Is there an existing local automation repo or toolkit worth reusing?

If `java.available` is false but a COMSOL root was detected, tell the user the bundled JRE path so they can set `JAVA_HOME` or call it directly - do not claim Java is unavailable.

If COMSOL is not detected, stop guessing paths and ask the user for the install root or model location.

### 2. Choose the execution path

Read [references/runtime-modes.md](references/runtime-modes.md) and pick the lightest path that matches the task.

Default path selection:

- Use the MCP server when the probe reports `mcp_server_ready` and the task is from-scratch conversational modeling.
- Use direct MPh control when the MCP server is not registered but the user wants scripted model edits, sweeps, or result extraction and `mph` is available.
- Use Java export when the model has already been validated in COMSOL Desktop and reproducing exact tags, selections, or couplings matters more than fast iteration.
- Use `.mph` batch runs when the model already works and only parameters, studies, or export targets need to change.

### 3. Use the MCP server or direct MPh sequence when possible

If the MCP server is registered, prefer MCP tool calls (`comsol_start`, `model_create`, `geometry_add_block`, `physics_add_*`, `mesh_create`, `study_solve`, `results_evaluate`) as listed in [references/mcp-server.md](references/mcp-server.md). These 80+ tools handle the full pipeline without writing code.

If MPh is the only option, drop to `model.java` for boolean ops, physics interface registration, materials, named selections, and mesh sequences - these are not stable in MPh's high-level API.

Read [references/workflow.md](references/workflow.md) for the detailed loop.

The canonical order is:

1. start or connect to a COMSOL session
2. load an existing model or create a new one
3. set parameters before rebuilding geometry
4. build geometry, add or inspect physics, and regenerate the mesh
5. solve the intended study
6. evaluate or export results
7. save a versioned artifact if the state should be kept

If the user mentions MCP tools explicitly, mirror that same order with tool calls like `comsol_start`, `model_load`, `param_set`, `geometry_build`, `mesh_create`, `study_solve`, and `results_evaluate`.
If the user wants plain Python automation, mirror the same order through `mph.Client` and `model` methods.

### 4. Prefer Java export for fragile GUI-built models

Use Java export when one or more are true:

- the geometry tree is large or selection-sensitive
- the model depends on tags, named selections, or couplings that are tedious to recreate by hand
- a working Desktop model already exists
- the user needs a durable scripted baseline for future edits

Recommended path:

1. validate the `.mph` interactively in COMSOL Desktop
2. export Java from the validated model
3. patch the generated Java minimally instead of rewriting it from scratch
4. compile and run it through the local COMSOL toolchain
5. move parameter sweeps and output harvesting around that validated baseline

### 5. Use `.mph` batch mode for stable repeat runs

Prefer batch mode over rebuilding the full model if:

- the geometry and physics are already correct
- the task is a parameter sweep, study rerun, or export refresh
- the user cares more about throughput than interactive edits

In that path, preserve the baseline model, vary only the intended knobs, and keep outputs and run metadata predictable.

### 6. Use docs and knowledge only as needed

Read [references/mph-mcp-gotchas.md](references/mph-mcp-gotchas.md) when you hit API or execution edge cases.

For documentation:

- prefer the installed COMSOL docs under the detected COMSOL root
- use `pdf_search` to query the local PDF knowledge base (50,287 chunks from 706 PDFs, stored on D drive via junction links — see `references/mcp-server.md` for paths)
- do not copy entire manuals into the skill; keep the skill lightweight and path-driven

### 7. Troubleshoot systematically

- If `mph` is missing but COMSOL exists, suggest installing `mph` in the active Python environment before writing a large wrapper.
- If direct scripting becomes fragile because of tags or selections, fall back to Desktop validation plus Java export.
- If boundary selections break after geometry edits or boolean operations, rebuild or re-inspect those selections before assuming the physics API is wrong.
- If long solves need progress, cancellation, or remote execution, prefer an async or batch path instead of blocking local scripting.
- If the task starts with "which example should I adapt", hand off that decision to `comsol-electrochem-fluid` before automating.

## References

- Read [references/mcp-server.md](references/mcp-server.md) for the 80+ MCP tool catalogue, install steps, and known limitations (this machine: installed, registered as `comsol`).
- Read [references/runtime-modes.md](references/runtime-modes.md) to choose between MCP server, direct MPh, Java export, and `.mph` batch runs.
- Read [references/workflow.md](references/workflow.md) for the end-to-end automation sequence and handoff points.
- Read [references/mph-mcp-gotchas.md](references/mph-mcp-gotchas.md) for common MPh and MCP implementation pitfalls.
- Read [references/inspection-gotchas.md](references/inspection-gotchas.md) for verifying real physics settings stored in `.mph` files (vector property blind spots, XML extraction, hardcoded uncoupling audit, long transient solves on Windows, MPh inner-index and dataset-mapping traps, interface-level `.prop()` accessor for turbulence-model switches, boundary-variable evaluation limits, mesh–wall-treatment y+ consistency check, radial concentration-profile diagnosis).
