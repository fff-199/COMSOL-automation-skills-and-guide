# Automation Workflow

This file describes the default automation loop for COMSOL tasks.

## 1. Probe First

Before writing or running automation:

- detect the COMSOL root
- confirm whether `mph` is importable
- confirm Java availability
- check whether the application library and docs are present
- check whether there is an existing local automation repo or toolkit

Use the bundled probe script and keep the detected paths in the run notes.

## 2. Define the Contract

Make these explicit before implementation:

- source model or template
- parameters to edit
- study to run
- required outputs
- destination paths for saved artifacts

If any of these are missing, infer the smallest safe default and state it.

## 3. Direct MPh or MCP Loop

When the runtime mode is direct control, use this order:

1. Start or connect to COMSOL.
2. Load or create the model.
3. Update parameters before geometry rebuilds.
4. Build geometry and verify selections.
5. Add or inspect physics.
6. Mesh the intended geometry.
7. Solve the intended study.
8. Evaluate, export, and save outputs.

Conceptual MCP-style sequence:

```text
comsol_start -> model_load -> param_set -> geometry_build
-> physics update -> mesh_create -> study_solve
-> results_evaluate/results_export -> model_save
```

Conceptual MPh-style sequence:

```python
client = mph.Client()
model = client.load("baseline.mph")
model.parameter("L", "10[mm]")
model.build()
model.mesh()
model.solve("std1")
value = model.evaluate("T", unit="K")
model.save("baseline_updated.mph")
```

## 4. Java Export Loop

When direct reconstruction is fragile:

1. Open the validated model in COMSOL Desktop.
2. Confirm studies, materials, selections, and outputs.
3. Export Java.
4. Patch only the parameter and output handling around the generated code.
5. Compile and run through the COMSOL toolchain.

Use this path to preserve the exact Desktop-authored model structure.

## 5. Batch Loop for Stable `.mph` Models

When the baseline model is already correct:

1. Duplicate or version the baseline.
2. Change only the intended parameters or studies.
3. Run through batch mode.
4. Export just the requested outputs.
5. Preserve enough run metadata to reproduce the result later.

## 6. Long-Running Solves

For long solves:

- prefer async orchestration or batch execution over blocking local scripts
- keep progress and cancellation support when available
- avoid restarting from scratch if the user only needs more output extraction

## 7. Domain Handoff

When the user asks questions like:

- which example to adapt
- which multiphysics interface family to choose
- whether the model should be 1D, 2D, axisymmetric, or 3D

handoff to `comsol-electrochem-fluid` first, then return here for automation.
