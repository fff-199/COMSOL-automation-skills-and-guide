# COMSOL Electrochem + Flow Case Map

Use this file to map a user problem to the closest local COMSOL example before building or automating anything.

Install root pattern used here:

- `%COMSOL_ROOT%\applications`

## Electrochemistry Core

- `Electrochemistry_Module\Applications\cyclic_voltammetry.mph`
  Use for transient electrode kinetics with diffusion-limited transport.
- `Electrochemistry_Module\Electroanalysis\microdisk_voltammetry.mph`
  Use for axisymmetric diffusion to microelectrodes and electroanalysis.
- `Electrochemistry_Module\Electroanalysis\impedance_spectroscopy.mph`
  Use for EIS setup and frequency-domain electrochemical response.
- `Electrochemistry_Module\Tutorials\diffuse_double_layer.mph`
  Use for electric double layer and migration effects.
- `Electrochemistry_Module\Tutorials\diffuse_double_layer_with_charge_transfer.mph`
  Use when double layer and Faradaic kinetics are both required.

## Electrochemistry + Species Transport / Separation

- `Electrochemistry_Module\Electrochemical_Engineering\electrodialysis.mph`
  Use for membrane transport, ionic separation, and migration-diffusion.
- `Electrochemistry_Module\Electrochemical_Engineering\capacitive_deionization.mph`
  Use for porous electrodes and salt removal with charging cycles.
- `Electrochemistry_Module\Electrochemical_Engineering\chlor_alkali.mph`
  Use for industrial electrolysis with transport and current distribution.
- `Electrochemistry_Module\Electrochemical_Engineering\isoelectric_focusing.mph`
  Use for electric-field-driven separation with species focusing.
- `Electrochemistry_Module\Electrochemical_Engineering\zone_electrophoresis.mph`
  Use for electrophoretic transport in channels.

## Electrolyzers and Fuel Cells

- `Fuel_Cell_and_Electrolyzer_Module\Electrolyzers\alkaline_electrolyzer.mph`
  Use for alkaline electrolysis fundamentals and polarization behavior.
- `Fuel_Cell_and_Electrolyzer_Module\Electrolyzers\pem_electrolyzer.mph`
  Use for PEM electrolyzer cell-level electrochemistry.
- `CFD_Module\Multiphase_Flow\pem_electrolyzer.mph`
  Use when gas evolution and multiphase flow matter in PEM electrolysis.
- `Fuel_Cell_and_Electrolyzer_Module\Electrolyzers\soec.mph`
  Use for solid oxide electrolysis with high-temperature transport.
- `Fuel_Cell_and_Electrolyzer_Module\Fuel_Cells\nonisothermal_pem_fuel_cell.mph`
  Use for coupled electrochemistry, flow, and heat in PEMFCs.
- `Fuel_Cell_and_Electrolyzer_Module\Fuel_Cells\pemfc_serpentine_flow_field.mph`
  Use for flow-field/channel distribution in PEM fuel cells.
- `Fuel_Cell_and_Electrolyzer_Module\Fuel_Cells\two_phase_pemfc.mph`
  Use when liquid water and gas coexist in PEMFC channels or GDLs.
- `Fuel_Cell_and_Electrolyzer_Module\Fuel_Cells\ht_pem_flow_field.mph`
  Use for heat transfer plus flow-field effects.

## Electrodeposition and Plating

- `Electrodeposition_Module\Tutorials\decorative_plating.mph`
  Use for baseline plating thickness distribution.
- `Electrodeposition_Module\Tutorials\electroplating_rack.mph`
  Use for multi-part plating uniformity and rack effects.
- `Electrodeposition_Module\Tutorials\pcb_designer.mph`
  Use for plating/current distribution on PCB-like layouts.
- `Electrodeposition_Module\Tutorials\cu_electrowinning_bubbly_flow.mph`
  Use for electrochemistry plus bubbly flow and gas-evolving electrodes.
- `Electrodeposition_Module\Tutorials\fountain_flow.mph`
  Use for forced convection plating baths.
- `Electrodeposition_Module\Tutorials_with_Deforming_Geometries\cu_deposition_trench.mph`
  Use for evolving geometry during deposition.
- `Electrodeposition_Module\Tutorials_with_Deforming_Geometries\pulse_reverse_plating.mph`
  Use for transient waveform-driven deposition control.

## Corrosion

- `Corrosion_Module\Atmospheric_Corrosion\atmospheric_corrosion.mph`
  Use for thin electrolyte layers and atmospheric corrosion films.
- `Corrosion_Module\Galvanic_Corrosion\galvanic_corrosion_mg_alloy.mph`
  Use for galvanic couples and dissimilar materials.
- `Corrosion_Module\Crevice_and_Pitting_Corrosion\pitting_corrosion.mph`
  Use for localized corrosion initiation and growth.
- `Corrosion_Module\General_Corrosion\localized_corrosion.mph`
  Use for moving-boundary or localized corrosion studies.
- `Corrosion_Module\Cathodic_Protection\pipeline_corrosion_protection_iccp.mph`
  Use for impressed-current cathodic protection.
- `Corrosion_Module\Cathodic_Protection\ship_hull.mph`
  Use for large protected structures in electrolytes.
- `Corrosion_Module\General_Corrosion\co2_corrosion.mph`
  Use for corrosion chemistry in process fluids.

## Flow, Microfluidics, Porous, and Pipe

- `CFD_Module\Single-Phase_Flow\backstep.mph`
  Use for separation/reattachment and baseline laminar/turbulent CFD validation.
- `CFD_Module\Single-Phase_Flow\turbulent_mixing.mph`
  Use for mixer-like industrial single-phase flow.
- `CFD_Module\Nonisothermal_Flow\heat_sink.mph`
  Use for conjugate heat-transfer style cooling flows.
- `Microfluidics_Module\Fluid_Flow\electrokinetic_valve.mph`
  Use for electric-field-driven microchannel flow control.
- `Microfluidics_Module\Micromixers\electroosmotic_mixer.mph`
  Use for electroosmotic flow plus mixing.
- `Porous_Media_Flow_Module\Heat_Transfer\convection_porous_medium.mph`
  Use for porous convection and Darcy/Brinkman plus heat.
- `Porous_Media_Flow_Module\Heat_Transfer\porous_microchannel_heat_sink.mph`
  Use for porous-assisted thermal management.
- `Pipe_Flow_Module\Tutorials\heat_exchanger_plate.mph`
  Use for networked pipe flow and thermal exchange.
- `Pipe_Flow_Module\Tutorials\slurry_transport.mph`
  Use for particle-laden pipe transport.

## Good Coupling Starters

Use these first when the user explicitly needs multiphysics coupling instead of a single-interface model:

- electrochemistry + flow:
  `cu_electrowinning_bubbly_flow.mph`, `electrokinetic_valve.mph`, `electroosmotic_mixer.mph`
- electrochemistry + heat + flow:
  `nonisothermal_pem_fuel_cell.mph`, `ht_pem_flow_field.mph`
- electrochemistry + two-phase:
  `two_phase_pemfc.mph`, `pem_electrolyzer.mph` under `CFD_Module\Multiphase_Flow`
- electrochemistry + porous transport:
  `capacitive_deionization.mph`, `pem_gdl_species_transport_2d.mph`, battery/fuel-cell porous electrode examples
- corrosion + transport / moving boundary:
  `localized_corrosion.mph`, `localized_corrosion_ls.mph`, `pitting_corrosion.mph`
- flow + heat:
  `heat_sink.mph`, `convection_porous_medium.mph`, `heat_exchanger_plate.mph`

## Notes

- `*_geom_sequence.mph` files are usually geometry-builder companions; use the main `.mph` unless geometry scripting itself is the target.
- Start from the module-specific example before reaching for a generic `COMSOL_Multiphysics` example.
- For automation, use the closest example as the COMSOL Desktop seed and export Java from there.

