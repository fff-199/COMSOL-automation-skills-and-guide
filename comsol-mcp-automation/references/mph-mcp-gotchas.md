# MPh and MCP Gotchas

Use this file when direct COMSOL automation starts failing for non-obvious reasons.

## 1. One Client Per Python Process

Treat the COMSOL client as effectively singleton-like within one Python process.

- avoid creating multiple clients in the same process
- prefer clearing models or reusing the active client
- if the session gets into a bad state, restart the process cleanly

## 2. Prefer Validated Model Structure Over Rebuilding Blindly

If the Desktop model already works:

- inspect it first
- preserve tags, selections, studies, and couplings
- use Java export when a hand-written reconstruction becomes fragile

## 3. Common Boundary Property Names

These names are easy to misremember:

- heat flux often uses `q0`
- fixed temperature often uses `T0`
- laminar-flow inlet velocity often uses `U0`
- laminar-flow outlet pressure often uses `p0`
- convective heat flux commonly uses `h` and `Text`

If a boundary condition call fails, verify the exact property names before assuming the selection is wrong.

## 4. Selections Drift After Geometry Changes

After boolean operations, imports, or major geometry edits:

- boundary numbers may change
- named selections may need rebuilding
- physics assignments may silently point to the wrong entities

Re-check selections whenever geometry structure changes.

## 5. `model.java` Is an Object, Not a Callable

When dropping to the Java bridge in MPh:

- use `model.java`
- do not call `model.java()`

Use the Java bridge only when the higher-level API is insufficient.

## 6. Time and Sweep Results Need Explicit Indexing

For postprocessing:

- use inner indices for time-dependent solutions
- use outer indices for parametric sweeps
- keep dataset names explicit when multiple solutions exist

Do not assume the default dataset always points at the result the user wants.

## 7. Save Milestones

For nontrivial automation:

- save a clean baseline before structural edits
- save after physics and study configuration stabilize
- save again after a successful solve if the result should be reused

This makes fallbacks much cheaper when a later edit breaks the model.

## 8. Documentation Strategy

Prefer this lookup order:

1. installed COMSOL docs under the detected COMSOL root
2. local example models and exported Java from validated baselines
3. `pdf_search` MCP tool — queries ChromaDB knowledge base (50,287 chunks, 706 PDFs) stored on `D:\COMSOL_MCP_Data\` via junction links

Do not bloat the skill by bundling manuals that should stay on disk.

## 9. JPype JVM Startup Hang inside FastMCP Server

When running the COMSOL MCP server in stdio mode (which uses FastMCP and anyio under the hood):
- **Issue**: Calling `jpype.startJVM()` or `mph.Client()` inside a synchronous tool handler (like `comsol_start`) causes the server process to hang indefinitely.
- **Cause**: FastMCP executes synchronous tool functions in a background thread of a thread pool. JPype JVM initialization will deadlock or hang when called inside these worker threads on Windows.
- **Solution**: Pre-initialize the COMSOL session (and the JVM) on the main thread in the server entry point (e.g. `main()` in `src/server.py`) before `mcp.run()` starts the event loop. Subsequent tool calls will interact with the already-started JVM safely and return immediately.

