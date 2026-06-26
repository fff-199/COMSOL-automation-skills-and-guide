# Modeling Patterns for Electrochemistry, Flow, and Coupling

## 1. Pick the minimum electrochemistry fidelity that closes the physics

- use current distribution only when electrolyte composition is effectively fixed
- add species transport when concentration gradients or limiting current matter
- add migration and double-layer physics when interfacial charge structure matters
- move to porous-electrode, battery, fuel-cell, or electrolyzer interfaces when layered electrochemical media dominate the behavior

Representative examples:

- current distribution / electroanalysis:
  `cyclic_voltammetry`, `microdisk_voltammetry`
- double layer:
  `diffuse_double_layer`, `diffuse_double_layer_with_charge_transfer`
- industrial electrochemistry:
  `chlor_alkali`, `electrodialysis`, `capacitive_deionization`

## 2. Add flow only when convection changes the answer

Add flow when one or more are true:

- Peclet number is not small
- reactant delivery is channel-driven
- gas evolution changes local conductivity or coverage
- electroosmotic or electrophoretic body forces drive the liquid
- heat removal is flow-limited

Representative examples:

- forced-convection electrochemistry:
  `fountain_flow`, `cu_electrowinning_bubbly_flow`
- electrokinetics:
  `electrokinetic_valve`, `electroosmotic_mixer`
- flow-field devices:
  `pemfc_serpentine_flow_field`, `ht_pem_flow_field`

## 3. Use the right coupling family

### Electrochemistry + species + flow

Use for plating baths, electrolysis cells, and microfluidic separation.

Typical building blocks:

- electrochemistry interface
- transport of diluted species or built-in species transport
- laminar flow or microfluidics
- optional moving mesh or deformed geometry

Starter examples:

- `chlor_alkali`
- `electrodialysis`
- `cu_electrowinning_bubbly_flow`

### Electrochemistry + heat + flow

Use for fuel cells, electrolyzers, and battery thermal management.

Starter examples:

- `nonisothermal_pem_fuel_cell`
- `ht_pem_flow_field`
- `li_battery_thermal_3d`

### Electrochemistry + two-phase flow

Use when gas evolution, water flooding, droplet motion, or bubbly transport is central.

Starter examples:

- `two_phase_pemfc`
- `pem_electrolyzer` in `CFD_Module\Multiphase_Flow`
- `electrocoalescence`

### Electrochemistry + porous media

Use for GDLs, porous electrodes, separators, packed beds, and deionization media.

Starter examples:

- `capacitive_deionization`
- `pem_gdl_species_transport_2d`
- battery porous-electrode examples under `Battery_Design_Module`

### Corrosion + deformation or moving boundaries

Use when the geometry evolves or stresses feed back into corrosion.

Starter examples:

- `localized_corrosion`
- `pitting_corrosion`
- `galvanic_corrosion_with_deformation`
- `cp_with_anode_deformation`

## 4. Dimensional escalation strategy

- start with 1D for kinetics or porous-electrode calibration
- move to 2D or axisymmetric for transport and current distribution
- move to 3D only when channel layout, manifold effects, or localized geometry control the answer

Good examples for each level:

- 1D:
  `cyclic_voltammetry_1d`, `pem_mea_1d`, `li_battery_1d`
- 2D / axisymmetric:
  `microdisk_voltammetry`, `rising_bubble_2daxi`, `li_battery_thermal_2d_axi`
- 3D:
  `pemfc_serpentine_flow_field`, `heat_sink`, `electroplating_rack`

## 5. Automation path on this machine

When the user wants reproducible or AI-driven modeling:

1. find the closest example
2. open it in COMSOL Desktop
3. inspect the exact interface names, couplings, solver setup, and variables
4. export Java from the validated model
5. integrate the exported code with `%COMSOL_AUTOMATION_ROOT%`

Use the local toolkit in `%COMSOL_AUTOMATION_ROOT%` for:

- COMSOL path detection
- Java source templating
- `comsolcompile` and `comsolbatch` execution
- existing `.mph` batch sweeps

## 6. Common mistakes

- starting from a generic CFD example when a domain-specific electrochemistry example exists
- jumping to 3D before proving the kinetics and transport in 1D or 2D
- using flow coupling when diffusion is dominant and the extra model cost buys nothing
- forgetting porous, thermal, or two-phase effects in PEMFC, electrolyzer, and battery models
- treating `*_geom_sequence.mph` as the final example model instead of the helper geometry model

