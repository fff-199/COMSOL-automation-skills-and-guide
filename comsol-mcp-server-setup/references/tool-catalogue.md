# wjc9011 COMSOL MCP Server — Tool Catalogue

Full list of tools exposed by the server (~80+). Group names match the source tree under `src/tools/`.

## Session (4)
- `comsol_start` — launch local COMSOL client
- `comsol_connect` — attach to a remote COMSOL server
- `comsol_disconnect` — close session
- `comsol_status` — session info

## Model (9)
- `model_load` — open `.mph`
- `model_create` — initialize blank model
- `model_save` / `model_save_version`
- `model_list`, `model_set_current`, `model_clone`, `model_remove`, `model_inspect`

## Geometry (14)
- primitives: `geometry_add_block`, `_cylinder`, `_sphere`, `_rectangle`, `_circle`
- boolean: `geometry_boolean_union`, `geometry_boolean_difference`
- import / build: `geometry_import` (CAD), `geometry_build`
- introspection: `geometry_list`, `geometry_list_features`, `geometry_get_boundaries`
- generic: `geometry_create`, `geometry_add_feature`

## Physics (16)
- specific add: `physics_add_heat_transfer`, `_laminar_flow`, `_electrostatics`, `_solid_mechanics`
- guided: `physics_interactive_setup_heat`, `_setup_flow`
- generic: `physics_add`, `physics_remove`, `physics_list`, `physics_list_features`, `physics_get_available`
- BCs / materials: `physics_configure_boundary`, `physics_set_material`, `physics_setup_heat_boundaries`, `physics_boundary_selection`
- coupling: `multiphysics_add`

## Mesh (3)
- `mesh_create`, `mesh_list`, `mesh_info`

> Note: shallow surface. For swept meshes, boundary layers, or named-size mesh sequences, fall back to Java export.

## Study & Solve (8)
- sync: `study_solve`
- async: `study_solve_async`, `study_get_progress`, `study_cancel`, `study_wait`
- introspection: `study_list`, `solutions_list`, `datasets_list`

## Results & Export (9)
- evaluate: `results_evaluate`, `results_global_evaluate`
- export: `results_export_data`, `results_export_image`
- introspection: `results_plots_list`, `results_exports_list`
- indexing helpers: `results_inner_values` (time-dependent), `results_outer_values` (sweeps)

## Knowledge (8)
- `docs_get`, `docs_list`, `physics_get_guide`
- `troubleshoot`, `modeling_best_practices`
- `pdf_search`, `pdf_search_status`, `pdf_list_modules`
  - On this machine: 50,287 chunks from 706 PDFs (53 module docs + 598 gallery tutorials)
  - Data stored on `D:\COMSOL_MCP_Data\` with junction links from repo — see `comsol-mcp-automation/references/mcp-server.md`

## Canonical call sequence for from-scratch builds

```
comsol_start
  -> model_create
  -> [geometry_add_*  ... -> geometry_boolean_*  -> geometry_build]
  -> [physics_add_* | multiphysics_add]
  -> physics_configure_boundary  (per-BC)
  -> physics_set_material
  -> mesh_create
  -> study_solve  |  study_solve_async + study_get_progress + study_wait
  -> results_evaluate  |  results_export_data  |  results_export_image
  -> model_save  |  model_save_version
```
