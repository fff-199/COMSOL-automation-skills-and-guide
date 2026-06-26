# Inspection & Solve Gotchas (Cu Electrowinning Project, 2026-06)

Battle-tested lessons from inspecting and solving a Tertiary Current Distribution
(Nernst-Planck) + Bubble Flow (k-ε) coupled model for cathodic Cu electrodeposition.
The patterns below generalize to any COMSOL model that mixes MPh Client API
inspection with long transient solves on Windows.

Use this file when the goal is **verifying the real physics settings stored in a
`.mph` file** or **running long transient solves unattended on Windows**.

---

## 1. mph Client API Has a Vector Property Blind Spot

The mph Client (standalone mode) `.getString('g')` and `.properties()` calls
**return only the first component of a packed vector property**.

### Symptom (real case)

Bubble Flow `bf` interface Gravity node `gr1` stores gravity as a 3D vector
`[gx, gy, gz]`. `dmodel.xml` shows the packed form:

```xml
<param T="33" param="g" value="3|1,'0'|1,'-g_const'|1,'0'"></param>
```

This decodes to `g = [0, -g_const, 0]` (i.e. `gy = -9.81 m/s²`, buoyancy active).

But:

```python
bf.feature('gr1').getString('g')        # returns '0' (only gx)
bf.feature('gr1').properties()           # returns ['g', 'StudyStep', 'showPhysicsSymbols']
bf.feature('gr1').hasProperty('gy')      # returns False
bf.feature('gr1').hasProperty('g_y')     # returns False
bf.feature('gr1').hasProperty('g#2')     # returns False
```

A naive audit flags `g=0` as a critical bug. **It is not** — the gravity vector
is correctly set, the API just hides the other two components.

### Mitigation

- Never trust `.getString('g')` for a property known to accept a vector.
- Probe `hasProperty` for `gx`/`gy`/`gz`, `g_x`/`g_y`/`g_z`, `g#1`/`g#2`/`g#3`
  first. If none return True, **assume the property is a packed vector** and
  fall through to §2 (XML extraction) for ground truth.
- The same packed-vector format (`3|1,'a'|1,'b'|1,'c'`) is used for any vector
  parameter stored by COMSOL's GUI (initial values, BC vectors, etc.).

---

## 2. Extract `dmodel.xml` From the `.mph` ZIP For Definitive Truth

A `.mph` file is a ZIP archive. The authoritative model definition lives in
`dmodel.xml`. When the MPh/MCP API gives ambiguous or partial answers, read
the XML directly.

### `.mph` internal structure

| Path | Purpose |
|---|---|
| `dmodel.xml` | Main model definition (parameters, physics, studies, features, **all property strings**) |
| `model.xml` | Tiny pointer / metadata |
| `savepoint{N}/savepoint.xml` | Variable declarations, state snapshots |
| `solution{N}.mphbin` | Solution data |
| `xmesh{N}.mphbin` | Extended mesh |
| `geometry{N}.mphbin` | Geometry |

### Extraction snippet (PowerShell, no Python needed)

```powershell
$mph = "D:\path\to\model.mph"
$tmp = "$env:TEMP\comsol_inspect"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($mph, $tmp)
# Read the packed vector form:
Select-String -Path "$tmp\dmodel.xml" -Pattern 'param="g"' |
    ForEach-Object { $_.Line }
```

### What to grep for

| You want to know | Grep pattern | Example hit |
|---|---|---|
| Vector property value | `param="<prop>"` | `<param T="33" param="g" value="3\|1,'0'\|1,'-g_const'\|1,'0'">` |
| Feature expression | `<expr` or `name="<prop>"` | `<expr name="Itl">Itot*step1((t/4.0)[1/s])</expr>` |
| Hardcoded literal | `value="<number>[unit]"` | `<value>4000.0[A]*step1(...)` |

**The packed-vector decode key:** `<N>|1,'a'|1,'b'|1,'c'` means a length-N
vector with components `a, b, c`. The `1,` prefix repeats for each component.

---

## 3. `MassActionLaw` i0_ref Must Be a Constant

In Tertiary Current Distribution electrode reactions, when `i0Type =
MassActionLaw`, the exchange current density reference `i0_ref` must be a
**constant**. COMSOL internally multiplies it by concentration-dependent
factors.

### Failure mode

Setting `es2.er1.i0_ref = 'i0c_Cu*(cCu/c0Cu)'` (a concentration-dependent
expression) causes a **Jacobian singularity** at solve time:

```
cCu undefined variable
```

on electrode boundaries, because the MassActionLaw formulation already
substitutes `cCu` into the Butler-Volmer prefactor.

### Fix

Set `i0_ref = 'i0c_Cu'` (the constant base, here `100 [A/m²]`). If you need
a concentration-dependent exchange current, switch the reaction to
`ConcentrationDependent` or `UserDefined` i0 formulation instead of
`MassActionLaw`. Verify by reading the kinetics section in the relevant
electrochemistry module PDF via `pdf_search`.

---

## 4. Hardcoded Uncoupling Checklist (Electrode Surface Features)

When a model was built by copy/paste from a working baseline, physics feature
fields often still carry **literal numeric values from the donor model**
instead of references to the new global parameters. The user-facing parameter
table looks correct; the physics field does not.

### Audit procedure

For each `ElectrodeSurface` (`es1`, `es2`, …) in a `tcd` interface, dump the
following properties and compare against the global parameter list:

| Feature | Property | Expected | Common hardcode smell |
|---|---|---|---|
| `esN` (TotalCurrent) | `Itl` | `Itot*step1((t/4.0)[1/s])` | `4000.0[A]*step1(...)` (old current) |
| `esN.erM` (Cu dep) | `i0_ref` | `i0c_Cu` (if MassActionLaw) | `i0c_Cu*(0.5*(cCu+sqrt(...))/c0Cu)` (hyperbolic smooth) |
| `esN.erM` (Cu dep) | `clim` | `clim` (global param) | `1e-3[mol/m^3]` (near-zero, disables protection) |
| `esN.erM` (O2 evol) | `clim` | `clim` (global param) | `1e-3[mol/m^3]` |

### Inspection script template

```python
import mph, sys
client = mph.Client(cores=6)
model = client.load(sys.argv[1])
tcd = model.java.physics('tcd')
for es_tag in ('es1', 'es2'):
    es = tcd.feature(es_tag)
    print(f"=== {es_tag} ===")
    for p in es.properties():
        print(f"  {p} = {es.getString(p)}")
    for er_tag in es.feature().tags():
        er = es.feature(er_tag)
        print(f"--- {es_tag}.{er_tag} ---")
        for p in er.properties():
            print(f"  {p} = {er.getString(p)}")
```

Run on both the candidate model and the validated baseline, diff the output.

---

## 5. Long Solves Must Use a Detached Windows Process

The MCP `comsol_study_solve` tool and the shell tool both have hard timeouts
(MCP ~minutes, shell 900 s). Any transient solve over ~10 minutes will be
killed mid-run, leaving the model in an indeterminate state.

### Solution: WMI detached process

Launch the solve script via `Invoke-WmiMethod`. It runs independently of the
shell session and survives even if the agent process restarts.

```powershell
$cmd = 'python "D:\path\to\solve_script.py" > "D:\path\to\solve_log.txt" 2>&1'
$proc = Invoke-WmiMethod -Class Win32_Process -Name Create -ArgumentList $cmd
$pid = $proc.ProcessId
Write-Host "Launched PID $pid"

# Poll status:
Get-Process -Id $pid -ErrorAction SilentlyContinue
# When null, the solve finished. Read solve_log.txt for the result.
```

### Solve script skeleton

```python
import mph, sys, time
client = mph.Client(cores=6)
model = client.load(sys.argv[1])
t0 = time.time()
# Run init studies first so dependent datasets exist:
for std in ['研究 1', '研究 2']:
    model.sol(std).run()
# Then the long transient:
model.sol('研究 3 (0-100s 连续化)').run()
print(f"Solve time: {(time.time()-t0)/60:.1f} min")
model.save(sys.argv[1].replace('.mph', '_solved.mph'))
```

MCP and shell are still fine for short jobs (init studies <60 s, mesh,
geometry rebuild). Use WMI only for the long transient itself.

---

## 6. MPh `inner=[list]` Is Buggy — Single-Step Instead

When evaluating a time-dependent expression over many frames, passing a list
of inner indices **returns identical values for every index** (a known mph
wrapper bug). The same evaluation called one index at a time works correctly.

### Broken (do not use)

```python
vals = model.evaluate('comp1.cCu', 'mol/m^3', dataset='dset6',
                      inner=list(range(1, 332)))   # returns [564.0]*331 silently
```

### Working

```python
vals = []
for idx in range(1, 332):
    v = model.evaluate('comp1.cCu', 'mol/m^3', dataset='dset6', inner=[idx])
    vals.append(float(v[0][0]))   # single point, single component
```

This is slower (~3 s per index for 40k DOF meshes) but correct. Budget ~16
minutes for 331 frames on a 6-core standalone client.

### Index mapping quirk

| `inner=` value | What you get |
|---|---|
| `[1]` | First time step |
| `[N]` (last) | Last time step |
| `[0]` | **Also the last frame** — counterintuitive, do not use 0 |

Never iterate `inner=[0]` to match array positions. Start from `1`.

---

## 7. Map Datasets to Studies Before Evaluating

`dsetN` numbering does **not** follow study order. A model with 5 studies
and 6 solutions can have `dset5` pointing at a completely different result
than the one you want. Always verify the mapping before extracting data.

### Mapping script

```python
import mph, sys
client = mph.Client(cores=6)
model = client.load(sys.argv[1])
for tag in model.java.result().dataset().tags():
    ds = model.java.result().dataset(tag)
    sol = ds.getString('solution')      # source solution tag
    label = ds.label()                  # GUI display name
    print(f"{tag}: sol={sol}  label={label}")
```

### Typical mapping (real example)

| Dataset | Solution | Study | Content |
|---|---|---|---|
| `dset1` | `sol1` | 研究 1 | Init mesh study |
| `dset2` | `sol2` | 研究 2 | Steady-state init |
| `dset4` | `solsrc` | CC_ContinueFrom5s | Continuation source |
| `dset5` | `sol3` | 研究 1a | **NOT the transient** (easy to assume wrong) |
| `dset6` | `sol4` | 研究 3 (0-100s 连续化) | **The 0-100s transient** |
| `dset7` | `sol5` | CC_ContinueFrom5s | Singular matrix, broken |

Always print the dataset → solution → study mapping and read the `label`
string; the `研究 3 (0-100s 连续化)` label is the unambiguous identifier.

---

## 8. mph Client Standalone & 2D Numerical Eval Nodes

Attempting to add `EvalVolume`, `EvalGlobal`, `MinMax`, or similar 3D numerical features through `model.java.result().create(...)` in a **2D model** fails with:

```text
在这个情景中不能创建本操作 / Cannot create operation in this context
```

### The Root Cause: Dimension Mismatch
This error occurs not because of standalone client limitations, but because the node type does not exist for the model's geometry dimension.
- In **2D models**, domains are surfaces, so you must use surface-specific evaluation nodes: `MinMaxSurface`, `MaxSurface`, `MinSurface`, `AvgSurface`, `IntSurface`.
- In **2D models**, boundaries are lines, so you must use line-specific evaluation nodes: `MinMaxLine`, `MaxLine`, `MinLine`, `AvgLine`, `IntLine`.
- Do not use `MinMax` or `EvalVolume` (which are reserved for 3D volumes) in 2D models.

### Vectorized Extraction Template (330+ frames in 1.5 seconds)
Instead of loop evaluation (which takes ~16 minutes for 331 frames over the Java-Python bridge), dynamically create the correct surface/line evaluation node, bind it to the time-dependent dataset, and call `.getReal()` to retrieve the entire time series in one go:

```python
res = model.java.result()
# 1. Create a MinSurface node on Boundary 1 (cathode in 2D model)
try: res.numerical().remove('min_c')
except Exception: pass

min_c = res.numerical().create('min_c', 'MinSurface')
min_c.set('data', 'dset6')     # Bind to transient solver dataset
min_c.set('expr', 'cCu')       # Variable expression
min_c.selection().set(np.array([1], dtype=np.int32)) # Selection array

# 2. Run and extract the entire time series at once
min_c.run()
cCu_min_arr = np.array(min_c.getReal()[0]).flatten() # Vectorized fetch!
res.numerical().remove('min_c') # Clean up
```

---

## 9. `mph.Client` Is a Separate COMSOL Instance From the MCP Server

`mph.Client(cores=N)` launches its own COMSOL backend. It does **not** share
models with the MCP `comsol_*` tools, even on the same machine.

### Consequence

- A model loaded via MCP `comsol_model_load` is invisible to a Python script
  using `mph.Client()`, and vice versa.
- Saving a model in mph does not push it to the MCP session.
- Running both in parallel doubles COMSOL license consumption and RAM.

### Rule

Pick one runtime per task. For a full inspect→fix→solve→extract pipeline on
Windows, use **mph Client + WMI detached process** end-to-end (see §5). Use
the MCP server only for short interactive probes.

---

## 10. Document the Fix History Next to the Model

When you patch a model via MPh, the `.mph` file does not record what changed.
Keep a sibling Markdown file with the same base name:

```
amp4000_fixed_v2_solved.mph
amp4000_fixed_v2_solved.notes.md   ← what was changed, why, solver settings
```

Include: original hardcoded values, new expressions, parameter values at
solve time, solver settings (tlist, BDF order, init dt, maxstepbdf), solve
time, core count, DOF, and the headline result. This is the only reliable
way to reproduce the run three months later.

---

## Related references

- [mph-mcp-gotchas.md](mph-mcp-gotchas.md) — generic MPh/MCP API pitfalls
- [workflow.md](workflow.md) — end-to-end automation sequence
- [runtime-modes.md](runtime-modes.md) — choosing between MCP, MPh, Java, batch

---

## 11. mph Client: Interface-Level `set()`/`getString()` Fail — Use `.prop()`

In mph Client (standalone) mode, the physics **interface** object
(`PhysicsClient`, e.g. `model.java.physics('bf')`) has **no `set` or
`getString` methods**. Only **feature-level** objects have them. This bites
when you try to change physics-wide settings like the turbulence model.

### What fails

```python
bf = model.java.physics('bf')
bf.getString('TurbulenceModel')   # AttributeError: PhysicsClient has no 'getString'
bf.set('TurbulenceModel','komega')  # AttributeError: PhysicsClient has no 'set'
```

The same call on a feature works fine (this is how §4 patches `es1.Itl`,
`er1.clim`, etc.):

```python
tcd.feature('es1').set('Itl','Itot*step1(...)')   # OK — feature level
```

### The correct accessor for interface-level property groups

COMSOL stores interface-wide settings in **property groups** (XML tag `prop`,
accessed via `.prop('GroupName')`). The turbulence model lives in
`TurbulenceModelProperty`:

```python
bf = model.java.physics('bf')
turb = bf.prop('TurbulenceModelProperty')          # <-- .prop(), not .feature()/.propertyGroup()
turb.getString('TurbulenceModel')                  # 'keps'
turb.set('TurbulenceModel','komega')               # SUCCESS
turb.set('WallTreatment','Automatic')              # SUCCESS
```

### How to discover available property groups

```python
bf.prop().tags()
# ['PhysicsSymbols','ShapeProperty','EquationForm','PhysicalModelProperty',
#  'TurbulenceModelProperty','ConsistentStabilization','InconsistentStabilization',
#  'AdvancedSettingProperty', ...]
```

Note `.propertyGroup()` does **not** exist on `PhysicsClient`; `.prop()` is the
one that works in mph 1.3.x client mode.

### Decision rule

| You want to change | Object | Accessor |
|---|---|---|
| A boundary/feature property (Itl, clim, i0_ref, u0, Nrhogeff) | feature | `bf.feature('fp1').set(...)` / `tcd.feature('es1').feature('er1').set(...)` |
| An interface-wide property group (turbulence model, wall treatment, stabilization) | property group | `bf.prop('TurbulenceModelProperty').set(...)` |
| A global parameter | parameter list | `model.java.param().set('Itot','6000[A]')` |

---

## 12. Boundary-Only Variables Cannot Be Evaluated on a Domain Dataset

Variables that exist **only on a boundary** (electrode-reaction local current
`iloc_er1`, gas source `Nrhogeff`, wall `yPlus`, `uTau`, `wDist`, turbulent
viscosity `mut`) raise `无法计算表达式 / Cannot evaluate expression` when you
call `model.evaluate(...)` over a **domain** dataset (`dset6`, the transient
volume solution).

### Symptom (real case — trying to read the bubble source strength)

```python
for expr in ['tcd.iloc_er1','bf.wallbc2.Nrhogeff','bf.mut','bf.yPlus','bf.uTau']:
    model.evaluate(expr, ..., dataset='dset6', inner='last')
    # FlException: 无法计算表达式 / 未定义变量  for ALL of them
```

Meanwhile **volume-defined** variables on the same dataset work fine:
`cCu`, `bf.phig`, `bf.phil`, `bf.nuT` (note `nuT` works, `mut` does not),
`tcd.Itot_es1` (a scalar integrated quantity), `u`, `v`, `tcd.V`.

### Why

mph Client standalone cannot create boundary-integration numerical nodes
(see §8), and `model.evaluate` over a domain dataset returns NaN for any
boundary-scoped expression. There is no clean API path to get a surface
integral of a boundary variable from mph Client.

### Workarounds (in order of preference)

1. **Use a volume proxy.** For mass-transfer analysis, back-calculate `kc`
   from volume fields: `kc = iloc_mean / (n*F*(c_bulk - c_surf))`, where
   `iloc_mean = Itot / electrode_area` and `c_surf` = `cCu` evaluated on nodes
   closest to the cathode (filter by radial coordinate). This avoids boundary
   evaluation entirely.
2. **Filter domain nodes by geometry.** Identify the near-wall layer by
   coordinate (e.g. nodes with `r > 1.358` are within 0.3 mm of the anode at
   `R=1.361`). Evaluate volume variables on that subset to approximate the
   wall value. Coarser than a true boundary integral but numerically valid.
3. **For true boundary integrals, use Desktop or Java export** — mph Client
   cannot do it (§8).

### Diagnostic implication

If an audit needs `iloc_er1` or `Nrhogeff` to verify a coupling, **do not
trust a "cannot evaluate" result as proof the coupling is broken**. The
coupling may be perfectly active inside the solver; mph Client simply cannot
surface the boundary variable. Cross-check via a conservation scalar that mph
*can* read (`tcd.Itot_es1` should equal the prescribed `Itot` to ~6 figures
if the electrode current is correctly solved).

---

## 13. `model.xml` Is a 207-Byte Stub — Read `dmodel.xml` Instead

§2 says the authoritative definition lives in `dmodel.xml`. Add the explicit
warning: **`model.xml` is NOT the model.** In COMSOL 6.3 `.mph` archives,
`model.xml` is a ~207-byte pointer/metadata stub. Grepping it for physics
properties returns nothing.

```python
data = z.read('model.xml').decode(...)    # 207 chars, no physics content
data = z.read('dmodel.xml').decode(...)   # ~2.2 MB, the real definition
```

Always read `dmodel.xml` for property/value grep. The earlier `read_turb_xml.py`
wasted a cycle grepping `model.xml` and reported "not found" before the author
noticed the file size.

---

## 14. Verify Mesh–Turbulence-Model Consistency (y+ vs Wall Treatment)

A mesh can be "very fine" and still wrong for the chosen turbulence wall
treatment. This is a physics-setup consistency check, not an API gotcha, but
it caused a 2× mass-transfer-coefficient error that looked like a hard
physical limit.

### The mismatch pattern

| Component | Setting | Requirement |
|---|---|---|
| Boundary-layer first cell | very thin, `y+ ≈ 0.2` | suits Low-Re / Automatic (resolves viscous sublayer) |
| Turbulence wall treatment | `WallFunctions` | requires `y+ ∈ [30, 300]` (log-law region) |

When both are true, the wall function extrapolates the log-law into the
viscous sublayer where it does not hold, under-predicting near-wall turbulent
viscosity (`nuT/ν ≈ 7` instead of `~50+`), which suppresses the turbulent
mass-transfer coefficient `kc` by ~2×.

### How to detect

1. **Read the wall treatment from XML** (§2, §13):
   ```xml
   <param param="WallTreatment" value="1|1,'WallFunctions'"></param>
   <param param="TurbulenceModel" value="1|1,'keps'"></param>
   ```
2. **Estimate y+ from the mesh + solution.** Measure the first-layer
   thickness from node coordinates (filter nodes by radial distance to the
   wall), then `y+ ≈ ρ·u_τ·dy₁/μ` with `u_τ ≈ V·√(f/8)`, `f ≈ 0.079·Re^{-0.25}`.
3. **Cross-check `kc` independently.** Back-calculate `kc` from the solved
   concentration field, then compare to Dittus-Boelter / Chilton-Colburn /
   Shaw-Hanratty predictions from the actual Reynolds and Schmidt numbers. A
   model `kc` that is 1.5–2× below all correlations signals a wall-treatment
   mismatch, not a physical limit.

### The resolution trap

Switching turbulence model alone is **not** enough if the mesh stays
mismatched:

- `k-ω` + `Automatic` on a `y+ ≈ 0.2` mesh is theoretically correct but the
  BDF time step collapses (a 0–5 s probe took 22 min and did not finish).
  This looks like "the switch failed" but is really "the mesh is too fine
  for stable low-Re integration at this Reynolds number."
- `k-ε` + `WallFunctions` needs the first cell **coarsened** to `y+ ≈ 30–50`
  (e.g. first layer 1.5 µm → ~1.5 mm), not just a model swap.

**Rule: when changing the turbulence wall treatment, always re-target the
first-layer thickness to the treatment's required y+ band in the same edit.**
A model/mesh consistency table belongs in every turbulence-model change
record:

| Target | First-layer thickness | y+ | Model | Wall treatment |
|---|---|---|---|---|
| robust + fast | ~1.5 mm | ~50 | k-ε | WallFunctions |
| accurate near-wall | ~7 µm | ~1 | k-ω SST | Automatic |
| (avoid) | ~1.5 µm | ~0.2 | either | either |

### Switching turbulence model in mph Client

Use the `.prop()` accessor from §11, not the interface-level `set`:

```python
bf = model.java.physics('bf')
turb = bf.prop('TurbulenceModelProperty')
turb.set('TurbulenceModel','komega')      # keps / komega / sst
turb.set('WallTreatment','Automatic')     # WallFunctions / Automatic / LowRe
```

After switching, the old solution's turbulence variables (`bf.ep` for k-ε,
`bf.om` for k-ω) become unevaluable on the existing dataset — this is
expected, not a bug. Re-solve from the init studies.

---

## 15. Concentration-Profile Bin Reveals Whether Depletion Is Bulk or Surface-Limited

When diagnosing "why does `cCu_min` hit a low value", the single most
informative plot is the **radial concentration profile across the
electrode gap**, not the global minimum time series.

### Procedure

Normalize position across the gap: `s = (r - R_inner)/(R_outer - R_inner)`,
so `s=0` is the cathode surface and `s=1` is the anode. Bin all domain nodes
by `s` and report `cCu` min/mean per bin:

```python
r = np.sqrt(x**2 + y**2)
s = (r - R_inner)/(R_outer - R_inner)
for slo, shi in [(0,0.1),(0.1,0.3),(0.3,0.5),(0.5,0.7),(0.7,0.9),(0.9,1.0)]:
    mask = (s>=slo)&(s<shi)
    print(f"s[{slo:.1f},{shi:.1f}]: min={cCu[mask].min():.1f} mean={cCu[mask].mean():.1f}")
```

### Interpretation

| Profile shape | Diagnosis | Fix direction |
|---|---|---|
| Bulk (s≈0.5) ≈ inlet, only s<0.05 depleted | **surface mass-transfer limit** (diffusion layer) — supply is fine | increase turbulence at wall (kc), not flow rate |
| Bulk also dropping along flow direction | **bulk depletion** — electrolyte residence time too long vs consumption | increase flow rate, inlet concentration, or electrode area |
| Depletion localized to one angular/height zone | **stagnant region / short-circuit flow** | check inlet/outlet placement, dead zones |

A global `cCu_min` time series cannot distinguish these. Always pull the
radial profile first. In the Cu-foil case this single plot overturned an
earlier (wrong) "bulk depletion" diagnosis: bulk stayed at 564 mol/m³
everywhere, only the 1 mm cathode diffusion layer dropped to 52.
