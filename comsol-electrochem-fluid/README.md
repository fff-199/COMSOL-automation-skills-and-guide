# comsol-electrochem-fluid

Use when the user wants to build, adapt, troubleshoot, benchmark, or automate COMSOL models involving electrochemistry, batteries, corrosion, electrodeposition, electrolyzers, fuel cells, fluid flow, microfluidics, porous flow, pipe flow, nonisothermal flow, or electrochemistry-flow couplings on this Windows machine. This skill probes the local COMSOL Application Library through `COMSOL_ROOT`, the Windows registry, and common install locations, shortlists relevant `.mph` examples, maps the problem to the right interface or coupling family, and hands off direct automation to `comsol-mcp-automation` or to local Java or batch toolchains when available.

## Portable Entry Point

- Start here if you are using this repository from a non-Codex agent.
- The original Codex-oriented source remains in `SKILL.md` for reference.
- Run bundled scripts relative to this folder, for example `./comsol-electrochem-fluid/scripts/...` from the repo root.

## Adapted Instructions

# COMSOL Electrochem Fluid

## Quick Start

1. Classify the user's problem on four axes:
   - electrochemistry fidelity: current distribution only, species transport, double layer, porous electrode, battery/fuel cell
   - flow regime: none, laminar, turbulent, microfluidic, porous, pipe, multiphase
   - coupling: heat, species, deformation, two-phase, porous transport
   - geometry scale: 1D, 2D, axisymmetric, 3D
2. Use `scripts/find_examples.py` to shortlist local `.mph` examples from the COMSOL Application Library.
3. Read [references/case-map.md](references/case-map.md) for curated example families and [references/modeling-patterns.md](references/modeling-patterns.md) for interface and coupling choices.
4. Prefer adapting the closest existing `.mph` example before rebuilding from scratch.
5. If the user wants direct execution after choosing the example, hand off to `comsol-mcp-automation`. If the model is already validated in COMSOL Desktop and needs a durable script, export Java from COMSOL Desktop and automate around that baseline.

## Workflow

### 1. Shortlist examples

Run the bundled search script first.

Common commands:

```powershell
python "<repo-root>\comsol-electrochem-fluid\scripts\find_examples.py"
python "<repo-root>\comsol-electrochem-fluid\scripts\find_examples.py" --keyword electrolyzer --keyword pem
python "<repo-root>\comsol-electrochem-fluid\scripts\find_examples.py" --module Electrochemistry_Module --module CFD_Module --keyword bubbly
python "<repo-root>\comsol-electrochem-fluid\scripts\find_examples.py" --module Corrosion_Module --keyword localized
```

If `python` is not on `PATH`, use the full interpreter path instead of the literal `python` command.

Default search scope already includes the most relevant modules:

- `Electrochemistry_Module`
- `Fuel_Cell_and_Electrolyzer_Module`
- `Electrodeposition_Module`
- `Corrosion_Module`
- `Battery_Design_Module`
- `CFD_Module`
- `Microfluidics_Module`
- `Porous_Media_Flow_Module`
- `Pipe_Flow_Module`
- `COMSOL_Multiphysics`

By default the script skips `*_geom_sequence.mph` because those are geometry-helper models, not the main study model.

### 2. Choose the closest modeling family

Use these families as the first-pass decision tree:

- electroanalysis and basic electrochemistry:
  use `cyclic_voltammetry`, `microdisk_voltammetry`, `impedance_spectroscopy`, `diffuse_double_layer`
- electrochemistry plus transport or separation:
  use `electrodialysis`, `capacitive_deionization`, `chlor_alkali`, `isoelectric_focusing`, `zone_electrophoresis`
- electrolyzers and fuel cells:
  use `alkaline_electrolyzer`, `pem_electrolyzer`, `soec`, `nonisothermal_pem_fuel_cell`, `two_phase_pemfc`, `pemfc_serpentine_flow_field`
- electrodeposition and plating:
  use `decorative_plating`, `electroplating_rack`, `pcb_designer`, `cu_electrowinning_bubbly_flow`, `cu_deposition_trench`
- corrosion:
  use `atmospheric_corrosion`, `galvanic_corrosion_mg_alloy`, `pitting_corrosion`, `localized_corrosion`, `pipeline_corrosion_protection_iccp`
- pure or supporting flow:
  use `backstep`, `turbulent_mixing`, `heat_sink`, `electrokinetic_valve`, `electroosmotic_mixer`, `convection_porous_medium`, `heat_exchanger_plate`

### 3. Reuse examples deliberately

- Keep the example if the user's geometry and physics are close; only swap geometry, parameters, materials, and BCs.
- Combine a domain example and a coupling example when one example is too narrow.
- Prefer lower-dimensional examples first when the user is still deciding on governing physics.
- Move to 3D only after the 1D or 2D physics closes and converges.

### 4. Move to automation when needed

For automation tasks, prefer detected local paths over hardcoded ones:

- Detect the COMSOL root through `scripts/find_examples.py` or the probe in `comsol-mcp-automation`.
- Under the detected COMSOL root, prefer these relative docs when present:
  - `doc\pdf\COMSOL_Multiphysics\ApplicationProgrammingGuide.pdf`
  - `doc\pdf\COMSOL_Multiphysics\COMSOL_ProgrammingReferenceManual.pdf`
  - `doc\help\wtpwebapps\ROOT\doc\com.comsol.help.comsol\api\com\comsol\model\util\ModelUtil.html`
- Reuse any existing local automation repo or batch wrapper only after verifying it actually exists on this machine.

Recommended automation path:

1. Open the closest `.mph` example in COMSOL Desktop.
2. Verify interfaces, couplings, study steps, materials, and solver settings.
3. Export the model to Java.
4. Fold the generated Java into the local automation pipeline instead of hand-writing the full API from scratch, or hand off direct orchestration to `comsol-mcp-automation`.
5. For existing `.mph` sweeps, prefer batch mode on the `.mph` directly.

## References

- Read [references/case-map.md](references/case-map.md) for curated examples and where each family is useful.
- Read [references/modeling-patterns.md](references/modeling-patterns.md) for interface selection and coupling heuristics.

## Resource Map

### Scripts
- `scripts/find_examples.py`

### References
- `references/case-map.md`
- `references/modeling-patterns.md`

## Portability Notes

- Use repository-relative paths or set `SKILLS_ROOT` instead of relying on a platform-specific install path.
- Review Windows absolute paths before running. Replace them with local paths or environment variables.
- This skill assumes Windows-native tools. Validate tool availability before use on other systems.

## Source

- Original skill definition: `SKILL.md`
