# Coupling Verification & Physics Inspection Lessons

Battle-tested lessons from a **Tertiary Current Distribution (Nernst-Planck) +
Bubble Flow (k-ε)** coupled model for cathodic Cu electrodeposition. Use this
file when you need to **verify that a coupled electrochemistry-flow model's
physics fields are actually wired correctly**, not just that the parameter
table looks right.

---

## 1. Hardcoded Uncoupling: The #1 Silent Killer

When a model is built by copy/paste from a working baseline (e.g., scaling
4000 A → 5500 A), the global parameter table updates but the **physics feature
properties keep the old literal values**. The simulation runs, converges, and
produces plausible results — at the wrong physics.

### Audit checklist for electrodeposition models

| Feature | Property | What it should reference | Hardcode smell |
|---|---|---|---|
| `tcd.es1` (anode, TotalCurrent) | `Itl` | `Itot*step1((t/4.0)[1/s])` | `4000.0[A]*step1(...)` |
| `tcd.es2.er1` (cathode dep) | `i0_ref` | `i0c_Cu` (constant, see §3) | `i0c_Cu*(0.5*(cCu+sqrt(...))/c0Cu)` |
| `tcd.es2.er1` (cathode dep) | `clim` | `clim` (global param) | `1e-3[mol/m^3]` (disables protection) |
| `tcd.es1.er1` (anode O₂) | `clim` | `clim` (global param) | `1e-3[mol/m^3]` |

### Inspection script

```python
import mph
client = mph.Client(cores=6)
model = client.load('model.mph')
tcd = model.java.physics('tcd')
for es in ('es1', 'es2'):
    feat = tcd.feature(es)
    print(f"=== {es} ===")
    for p in ('Itl', 'clim', 'i0_ref'):
        try:
            print(f"  {p} = {feat.getString(p)}")
        except Exception:
            pass
    for er in feat.feature().tags():
        sub = feat.feature(er)
        print(f"--- {es}.{er} ---")
        for p in ('i0_ref', 'clim', 'alphaa', 'alphac', 'i0Type'):
            try:
                print(f"  {p} = {sub.getString(p)}")
            except Exception:
                pass
```

**Always run this on both the candidate model and the validated baseline,
then diff.**

---

## 2. Three Couplings to Verify in TCD + Bubble Flow

A correctly wired electrochemistry-bubble flow model has three implicit
couplings (no Multiphysics node needed — they work via variable references):

### Coupling A: Bubble source ← electrode current

```
bf.wallbc2.Nrhogeff = (tcd.iloc_er1) * Mw_O2 / (4*F_const) * step1(t[1/s])
```

- `tcd.iloc_er1` = local current density from the anode reaction
- Faraday's law: gas mass flux = i × M / (n × F)
- `step1(t)` ramps the source over ~4 s to avoid startup singularity
- **Verify**: the anode wall (GasFlux BC) references `tcd.iloc_er1`, not a
  hardcoded number

### Coupling B: Electrolyte velocity ← liquid holdup

```
tcd.sep1.u = min(max(bf.phil, 1e-4), 1) * u
```

- `phil` = liquid volume fraction (1 − gas holdup)
- When bubbles accumulate, effective electrolyte velocity drops
- **Verify**: the separator domain's velocity expression references `bf.phil`

### Coupling C: Bruggeman porosity ← liquid holdup

```
tcd.sep1.epsl = min(max(bf.phil, 1e-4), 1)
```

With `IonicCorrModel = Bruggeman`, `ElectricCorrModel = Bruggeman`,
`DiffusionCorrModel = Bruggeman`, `Migration = Bruggeman`.

- All transport properties scale as ε_l^1.5
- **Verify**: `epsl` references `bf.phil`, and all four correction models are
  set to Bruggeman

If any of these three are missing or hardcoded, the coupling is broken.

---

## 3. MassActionLaw `i0_ref` Must Be Constant

In Tertiary Current Distribution, when `i0Type = MassActionLaw`, the
Butler-Volmer equation internally multiplies `i0_ref` by concentration-dependent
terms. Setting `i0_ref` to a concentration-dependent expression causes
**double substitution → Jacobian singularity**.

| `i0Type` | `i0_ref` should be | Example |
|---|---|---|
| `MassActionLaw` | Pure constant | `i0c_Cu` (= 100 A/m²) |
| `ConcentrationDependent` | Can include concentration | `i0c_Cu*(cCu/c0Cu)` |
| `UserDefined` | Full expression | Anything valid |

**Failure symptom**: `cCu undefined variable` on electrode boundaries at the
first timestep.

---

## 4. Gravity in Bubble Flow Is a Packed Vector — Don't Trust `getString`

The Bubble Flow k-ε Gravity node (`gr1`) stores gravity as a 3D vector in
COMSOL's packed format. The mph Client API `.getString('g')` returns **only
the first component** (typically `gx = 0`), masking the real gravity setting.

### The trap

```python
gr1.getString('g')      # returns '0'  ← looks like gravity is OFF
gr1.properties()         # returns ['g', 'StudyStep', 'showPhysicsSymbols']
gr1.hasProperty('gy')    # returns False
```

### The truth (from `dmodel.xml` inside the `.mph` ZIP)

```xml
<param T="33" param="g" value="3|1,'0'|1,'-g_const'|1,'0'"></param>
```

Decoded: `g = [0, -g_const, 0]` → `gy = -9.81 m/s²` (gravity IS on).

### How to check definitively

Extract `dmodel.xml` from the `.mph` (which is a ZIP):

```python
import zipfile, re
with zipfile.ZipFile('model.mph') as z:
    xml = z.read('dmodel.xml').decode('utf-8', 'ignore')
for m in re.finditer(r'param="g"\s+value="([^"]+)"', xml):
    print(f"Gravity packed value: {m.group(1)}")
```

The packed format `N|1,'a'|1,'b'|1,'c'` means an N-component vector `[a, b, c]`.

**This applies to any vector property in COMSOL, not just gravity.**

---

## 5. Typical Bubble Flow Feature Layout (Electrodeposition)

For reference, a correctly configured Bubble Flow k-ε for electrodeposition
has these 8 features:

| Tag | Name | Type | Key settings |
|---|---|---|---|
| `fp1` | Fluid Properties | FluidProperties | `rhol=rho`, `mul=nu`, `Mg=Mw_O2`, `diamb=d_b`, DragModel=SmallSphericalBubbles |
| `init1` | Initial Values | init | `u=0`, `p=0`, `rhogeff=0`, `nd=0` |
| `wallbc1` | Wall (no gas) | WallBC | NoSlip, GasBC=**NoGasFlux** |
| `dcont1` | Flow Continuity | Continuity | — |
| `gr1` | Gravity | Gravity | `g=[0, -g_const, 0]` (packed vector!) |
| `inl1` | Liquid Inlet | InletBoundary | `U0in=Vb*step1(t)`, GasBC=NoGasFlux |
| `wallbc2` | Wall (gas source) | WallBC | GasBC=**GasFlux**, `Nrhogeff` from `tcd.iloc_er1` |
| `out1` | Outlet | OutletBoundary | Pressure, GasBC=**GasOutlet** |

The **only** gas source is `wallbc2` (anode surface). Gas exits at `out1`.
All other boundaries are gas-tight.

---

## 6. Quick Sanity Check: Is the Coupling Live?

After solving, evaluate these at a mid-domain point at t=10 s:

| Expression | Expected (working coupling) | Broken coupling signal |
|---|---|---|
| `bf.phil` | 0.85 – 0.99 (some gas present) | Exactly 1.0 everywhere (no gas) |
| `bf.phig` | 0.01 – 0.15 (gas holdup) | Exactly 0 everywhere |
| `tcd.iloc_er1` (anode) | Non-uniform, O(100-1000 A/m²) | Zero or uniform |
| `tcd.sep1.epsl` | < 1.0 where bubbles are | Exactly 1.0 everywhere |

If `bf.phil` is identically zero, the bubble source coupling is broken.
If `tcd.sep1.epsl` is identically 1.0, the Bruggeman coupling is broken.

---

## 7. Turbulent Boundary Layer Mismatch (y+ vs. Wall Functions)

In coupled turbulent flow-species transport models (e.g., $k-\epsilon$ with electrodeposition), the near-wall grid sizing must match the wall treatment.

- **The Problem**: Using a very fine grid ($y^+ \le 1$) with standard **Wall Functions** (which assume the first node is in the logarithmic region, $y^+ \in [30, 300]$) causes COMSOL to extrapolate the log-law into the viscous sublayer. This underpredicts the near-wall turbulent viscosity $\nu_T$ by 10x and the mass transfer coefficient $k_c$ by 2-3x, leading to premature concentration depletion (limiting current underprediction).
- **The Solution**: 
  1. Either **coarsen the boundary layer grid** so the first node satisfies $y^+ \approx 50$ (best for solver speed when using $k-\epsilon$ Wall Functions).
  2. Or switch to a low-Re turbulence model (like $k-\omega$ or SST) with **Automatic Wall Treatment** and keep the fine mesh ($y^+ \le 1$) to fully resolve the boundary layer. Note: Low-Re models on fine meshes are significantly slower.

---

## 8. Gas Holdup Underprediction & Bubble-Induced Mixing

In high-current density systems (like copper foil electrowinning at $5000-10000 \text{ A/m}^2$), gas evolution at the anode drives intense convective mixing.

- **The Problem**: The default bubble diameter ($d_b = 50\,\mu\text{m}$) or drag model (e.g., SmallSphericalBubbles) in the Bubbly Flow interface may sweep gas out of the narrow channel too quickly. This underpredicts the gas volume fraction $\phi_g$ (e.g., $0.97\%$ simulated vs. $7.6\%$ theoretical holdup), suppressing the bubble-induced turbulent mass transfer at the cathode.
- **The Solution**: Calibrate bubbly flow parameters (such as bubble diameter $d_b$, drag model like Schiller-Naumann, or dispersion coefficients) to match the theoretical gas holdup, ensuring the 2-3x mass transfer enhancement is correctly captured.

---

## 9. Background Conductivity vs. Active Species Migration

Upward corrections of background ion transport properties (e.g., temperature-dependent diffusion for $H^+$ and $HSO_4^-$) can negatively affect the active species.

- **The Phenomenon**: Correcting background ion diffusion coefficients upwards increases electrolyte conductivity, which flattens the electric potential gradient. Because positive active ions (like $Cu^{2+}$) rely on migration along this potential gradient to move towards the cathode, the reduced electric field decreases the total mass transport rate, slightly lowering the limiting current (by ~3.2% in Cu foil cells). Pair conductivity corrections with accurate boundary layer models to capture this tradeoff.

---

## 10. Performance Tip: Component Couplings vs. Loop Evaluation

Evaluating species concentration fields over the Java-Python bridge can be a major bottleneck.

- **The Problem**: Calling `model.evaluate('cCu', ..., inner=[idx])` inside a loop of 300+ frames transfers the entire mesh array (~150k nodes, ~1.2 MB per frame) over a local socket, taking ~10 minutes.
- **The Solution**: Instead of transferring full arrays to Python, define a **Minimum Component Coupling** node in COMSOL (`minop1` on the cathode boundary) and create a Global Variable `cCu_min = minop1(cCu)`. Evaluating the single scalar `cCu_min` over time takes less than a second.

---

## 11. Limiting Current Density Singularity & Overpotential Overflow (Jacobian NaN)

In Tertiary Current Distribution (Nernst-Planck) models, setting `LimitingCurrentDensity = 1` (Enabled) with a constant limit `ilim` (e.g., $2000 \text{ A/m}^2$) on a reaction feature (e.g., `es2.er1`) introduces a hard horizontal asymptote in the kinetics equation:
\[
i_{\text{loc}} = \frac{i_{\text{Bv}}}{1 + |i_{\text{Bv}} / i_{\text{lim}}|}
\]
When the global current constraint (e.g., $10000\text{ A}$) forces the average current density to exceed this limit (e.g., average $2028 \text{ A/m}^2 > 2000 \text{ A/m}^2$), the solver tries to satisfy the constraint by driving the local overpotential $\eta$ to negative infinity ($-\infty$). 

### Symptom & Root Cause
- **Symptom**: The transient solver crashes at a specific current value, with `Jacobian NaN` in the electrolyte potential `phil` or active species concentration `cCu` variables.
- **Diagnostics**: Extracting boundary values at the crash frame shows the integrated overpotential $\eta$ reaching $-30\text{ V}$ to $-150\text{ V}$. At these values, the Butler-Volmer exponential term $\exp(-\alpha_c F \eta / (R T))$ reaches $\approx 10^{280}$, overflowing the double-precision floating-point range ($1.79 \times 10^{308}$) during subsequent Newton predictor steps.
- **Solution**:
  1. **Disable reaction-level limiting current density**: Set `LimitingCurrentDensity = 0` on the reaction feature. The mass transfer diffusion limitation is already naturally modeled by the concentration variable `cCu` at the boundary.
  2. **Increase ilim**: If the cap is absolutely required, set `ilim` to an artificially large value (e.g., `1e5[A/m^2]`) to avoid the mathematical singularity.

---

## 12. Concentration Floor Protection in Newton Iterations

During the line search and predictor steps of the Newton solver, the species concentration `cCu` can temporarily fluctuate to negative values before converging. If the exchange current density `i0` depends on concentration via a fractional power (e.g., $i_0 \propto c_{\text{Cu}}^{0.5}$ under `MassActionLaw`), evaluating a negative concentration returns complex numbers or NaN, immediately crashing the Jacobian.

### Solution
Change `i0Type` to `UserDefined` and implement a smooth floor protection using `max()` or COMSOL's smooth step functions:
```text
i0 = i0c_Cu * (max(cCu, 1e-3[mol/m^3])/cref)^0.5
```
This guarantees that the base is always strictly positive, providing smooth and defined derivatives for the Jacobian at all times.

---

## Related references

- [case-map.md](case-map.md) — which Application Library example to start from
- [modeling-patterns.md](modeling-patterns.md) — interface and coupling selection heuristics
- `../../comsol-mcp-automation/references/inspection-gotchas.md` — MPh/MCP API pitfalls (vector blind spot, WMI solves, inner index quirks)

