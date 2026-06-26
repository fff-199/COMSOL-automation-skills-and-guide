# COMSOL Multiphysics 自动化与 AI Agent 接口工具链
## COMSOL Multiphysics Automation & AI Agent Toolchain

[中文](#中文说明) | [English](#english-description)

---

## 中文说明

本仓库开源了一套专为 COMSOL Multiphysics 自动化控制及 AI Agent（如 Antigravity, Claude Code 等）设计的工具链与集成规范（Skills & MCP Server）。工具链打通了从**多物理场方案决策、仿真环境一键部署、到仿真模型自动构建与求解**的全流程自动化。

特别针对**电化学-流体传热传质耦合（EC-CFD）** 仿真提供了系统的方法论、公式设计模式与检索案例，适合用于开发自主进行科学物理计算与优化设计的自动化脚本及智能体。

### 📂 目录结构

本工具链包含三个核心模块：
*   **[comsol-electrochem-fluid](./comsol-electrochem-fluid)** (物理场决策与检索)：规范电化学及流体流态分类（四轴分类法），提供官方 Application Library 范例检索，指导物理场退化和维度递进策略。
*   **[comsol-mcp-server-setup](./comsol-mcp-server-setup)** (服务一键部署)：自动探测系统环境、安装 Python 依赖（`mph`, `chromadb`, `torch` 等）、向配置文件注入运行环境变量（如 COMSOL 绑定的 JRE 和 HuggingFace 镜像站），生成标准 stdio MCP 接口。
*   **[comsol-mcp-automation](./comsol-mcp-automation)** (COMSOL MCP 自动化执行终端)：基于 wjc9011 的 COMSOL MCP Server 提供 80+ 级操作接口，或通过 MPh 直接修改参数、构建几何、控制选择集、求解并提取图形和数据。

---

### ⚡ 关键避坑：JVM 启动死锁修复（JPype + FastMCP/AnyIO）

在基于 stdio 管道和异步框架（如 FastMCP、anyio、asyncio）构建 COMSOL 自动化服务时，存在一个底层冲突：

> [!WARNING]
> **JPype JVM 启动死锁**
> FastMCP 会自动将同步定义的工具（如 `@mcp.tool()`）分配到 `ThreadPoolExecutor`（子线程池）中异步执行。在 Windows 环境下，通过子线程调用 `jpype.startJVM()` 或初始化 `mph.Client()` 会与主线程的事件循环以及管道数据重定向发生锁冲突，导致 **JVM 进程永久卡死** 在 `Starting Java virtual machine` 阶段。

#### 🛠️ 解决方案
不要在工具回调函数（子线程）中延迟加载 JVM。在服务的主入口 `main()` 函数启动后、`mcp.run()` 运行之前，强制在**主线程**内预启动 COMSOL 会话：

```python
# 示例：在主入口预加载 JVM
def main() -> None:
    logger.info("Starting COMSOL MCP Server...")
    
    register_all_tools()
    register_all_resources()
    
    # 核心修复：在主线程启动阶段预加载 JVM，绕过 AnyIO 子线程池死锁
    logger.info("Pre-starting COMSOL session on main thread...")
    try:
        from .tools.session import session_manager
        res = session_manager.start() # 内部执行 mph.Client() 初始化 JVM
        if res.get("success"):
            logger.info(f"COMSOL session pre-started successfully: {res}")
        else:
            logger.error(f"Failed to pre-start: {res.get('error')}")
    except Exception as e:
        logger.error(f"Failed to pre-start: {e}")
        
    mcp.run() # 启动 FastMCP 服务
```
后续的工具调用只需检测 `session_manager.client` 是否就绪，若已就绪直接执行 `.clear()` 即可瞬间返回响应，消除了任何卡死隐患。

---

### 🧪 电化学-流体耦合（EC-CFD）建模指南

在设计涉及电极反应、电解质传质、多相气泡演化及对流换热的耦合系统时，推荐遵循以下设计范式：

#### 1. 四轴分类框架 (Four-Axis Classification)

| 轴向 | 分类档次（由低到高） | 选择依据与边界 |
| :--- | :--- | :--- |
| **电化学保真度** | 1. 一次电流分布 (Primary)<br>2. 二次电流分布 (Secondary)<br>3. 三次电流分布 (Tertiary / Nernst-Planck)<br>4. 多孔电极 / 电池接口 | - 若电解质浓度差很小，使用一次/二次电流分布（仅求解 Ohm 定律）。<br>- 若传质阻抗不可忽略（如高电流密度下极限扩散电流），必须使用三次电流分布。<br>- 锂电池、燃料电池催化层等复杂夹层介质使用专用多孔电极接口。 |
| **流体流态** | 1. 无流动<br>2. 层流 (Laminar)<br>3. 湍流 (Turbulent)<br>4. 微流控 (Microfluidics)<br>5. 多孔介质流动 (Darcy/Brinkman)<br>6. 多相流 (Multiphase) | - 若 Peclet 数很小，对流可忽略。<br>- 气化产物（如析氢/析氧）会改变电导率，须引入多相气泡流。<br>- 多孔电极内部的气相/液相流动使用 Darcy/Brinkman 方程。 |
| **耦合场** | 1. EC + 传质 (浓度场对流)<br>2. EC + 传质 + 流体 (析气电导率变化)<br>3. EC + 流体 + 传热 (非等温系统) | - 浓度场对流：流体流速 \(u\) 作为对流项引入稀物质传递。<br>- 电导率变化：气泡体积分数 \(\phi_g\) 降低有效电导率 \(\sigma_{\text{eff}} = \sigma_0 (1-\phi_g)^{1.5}\)。 |
| **空间维度** | 1. 1D 动力学<br>2. 2D / 2D Axisymmetric 传质<br>3. 3D 流道设计 | - 1D 用于 Tafel 斜率、活化能等动力学参数的标定与拟合。<br>- 2D 轴对称用于旋转圆盘电极（RDE）、单电极局部流动模拟。<br>- 3D 仅用于非对称的复杂流道（如蛇形流道）或非均匀多部件组装体。 |

#### 2. 耦合变量与公式设计模式

在自动生成或修改模型时，需要正确绑定以下耦合项：

```
                              [流体场 (Laminar Flow)]
                                        │
                                        │ (流动速度 u)
                                        ▼
    [电化学场 (Tertiary EC)] ──(反应源项 R)──> [稀物质传递 (tds)]
           ▲                                    │
           │                                    │ (电解质电导率 / 浓度 C)
           └────────────────────────────────────┘
```

*   **流动对电化学传质的耦合**：流体流速 \(\mathbf{u}\) 必须输入到稀物质传递（`tds`）或三次电流分布接口的对流项中。
*   **电化学反应对传质的源项耦合**：反应产生的物质摩尔源项 \(R_i\) 与局部电流密度 \(i_{loc}\) 和法拉第常数 \(F\) 相关：
    \[
    R_i = -\frac{\nu_i \cdot i_{loc}}{n \cdot F}
    \]
*   **两相流中的电导率修正 (Maxwell 关系)**：若电极析气产生气泡，有效电解液电导率 \(\kappa_{\text{eff}}\) 必须根据局部气含率 \(\phi_g\) 进行修正：
    \[
    \kappa_{\text{eff}} = \kappa_0 \cdot (1 - \phi_g)^{1.5}
    \]

#### 3. 典型耦合 Starter 模板

在 Application Library 中，建议优先加载以下经典范例作为基础 seed 文件进行修改，避免从头构建几何与物理场：

1.  **电沉积与析气流强耦合**：`Electrodeposition_Module\Tutorials\cu_electrowinning_bubbly_flow.mph`
    *   *特点*：三次电流分布 + 稀物质传递 + 气泡流（Bubbly Flow）。非常适合用于设计带气液分离的电化学反应器。
2.  **非等温燃料电池强耦合**：`Fuel_Cell_and_Electrolyzer_Module\Fuel_Cells\nonisothermal_pem_fuel_cell.mph`
    *   *特点*：电化学反应 + 多孔介质传质 + 气体流道流动 + 固体/液体传热。是理解非等温多相流 EC 系统的经典模板。
3.  **电渗流微阀控制**：`Microfluidics_Module\Fluid_Flow\electrokinetic_valve.mph`
    *   *特点*：静电场（库伦力） + 层流流动（电渗体力的源项引入）。适用于微流控芯片设计。

---

### 🧪 自动化工作流示例

以下是一个典型的“加载并修改电化学仿真参数”的工具调用工作流示例：

#### Step 1: 获取 COMSOL 会话状态
```json
// Call Tool: comsol_status
{}
// Response:
// { "connected": true, "version": "6.3", "standalone": true }
```

#### Step 2: 加载物理仿真模型
```json
// Call Tool: model_load
{ "file_path": "C:\\COMSOL_Models\\vacuum_drying.mph" }
// Response:
// { "success": true, "model": { "name": "vacuum_drying", ... } }
```

#### Step 3: 修改蒸发速率常数和加热温度
```json
// Call Tool: param_set
{
  "name": "kvap",
  "expression": "5e-6[1/s]"
}
// Call Tool: param_set
{
  "name": "Th",
  "expression": "75[degC]"
}
```

#### Step 4: 重建几何与求解
```json
// Call Tool: geometry_build
{}
// Call Tool: study_solve
{
  "study_name": "Study 1"
}
```

#### Step 5: 评估与导出计算图表
```json
// Call Tool: results_evaluate
{
  "expression": "ht.Tmax",
  "unit": "degC"
}
// Call Tool: results_export_image
{
  "plot_group": "Temperature (ht)",
  "file_path": "C:\\COMSOL_Models\\T_max_distribution.png"
}
```

---

## English Description

This repository open-sources a complete toolkit and integration specification (Skills & MCP Server) designed to automate COMSOL Multiphysics via Python and AI Agents (e.g., Antigravity, Claude Code). The toolchain streamlines the entire lifecycle from **multiphysics design decisions and environment deployment to automated model building and solving**.

It provides a systematic methodology, coupling formulation templates, and application library retrieval cases for **Electrochemistry-Fluid Dynamics (EC-CFD) coupling** simulations, making it ideal for developing automated scientific computing scripts and intelligent optimization agents.

### 📂 Repository Structure

The toolchain consists of three core modules:
*   **[comsol-electrochem-fluid](./comsol-electrochem-fluid)** (Multiphysics Decision & Retrieval): Standardizes electrochemistry and fluid flow classification (Four-Axis Classification), searches official Application Library examples, and provides strategies for physical dimension reduction and physics degradation.
*   **[comsol-mcp-server-setup](./comsol-mcp-server-setup)** (Environment Setup & Server Registration): Automatically detects host environments, installs Python dependencies (`mph`, `chromadb`, `torch`, etc.), configures runtime variables (such as COMSOL-bundled JRE and HuggingFace mirrors), and registers standard stdio MCP interfaces.
*   **[comsol-mcp-automation](./comsol-mcp-automation)** (COMSOL MCP Execution Terminal): Exposes 80+ operation APIs based on wjc9011's COMSOL MCP Server, or invokes MPh directly to adjust parameters, build geometry, configure selections, solve studies, and extract plots or dataset values.

---

### ⚡ Critical Workaround: JVM Startup Deadlock (JPype + FastMCP/AnyIO)

When building COMSOL automation services using stdio pipes and asynchronous frameworks (such as FastMCP, anyio, or asyncio), a low-level thread conflict occurs:

> [!WARNING]
> **JPype JVM Startup Deadlock**
> FastMCP automatically schedules synchronous tools (decorated with `@mcp.tool()`) to run asynchronously inside a `ThreadPoolExecutor` (worker threads). On Windows, calling `jpype.startJVM()` or initializing `mph.Client()` from a worker thread conflicts with the main thread's event loop and stdio capture redirection, causing the **JVM initialization to hang indefinitely** at the `Starting Java virtual machine` phase.

#### 🛠️ The Solution
Do not defer the JVM loading to the tool callback execution (worker thread). Instead, force the COMSOL session to pre-start on the **main thread** during the server startup phase (right after `main()` starts and before running `mcp.run()`):

```python
# Example: Pre-loading JVM in the main thread
def main() -> None:
    logger.info("Starting COMSOL MCP Server...")
    
    register_all_tools()
    register_all_resources()
    
    # Crucial Fix: Pre-start COMSOL session on the main thread to bypass AnyIO worker thread deadlock
    logger.info("Pre-starting COMSOL session on main thread...")
    try:
        from .tools.session import session_manager
        res = session_manager.start() # Runs mph.Client() to initialize the JVM
        if res.get("success"):
            logger.info(f"COMSOL session pre-started successfully: {res}")
        else:
            logger.error(f"Failed to pre-start: {res.get('error')}")
    except Exception as e:
        logger.error(f"Failed to pre-start: {e}")
        
    mcp.run() # Start the FastMCP service
```
Subsequent tool calls will verify if `session_manager.client` is ready. If so, they execute `.clear()` and return instantly, eliminating any hang risks.

---

### 🧪 Electrochemistry-Fluid Dynamics (EC-CFD) Coupling Guide

When designing coupled systems that involve electrode reactions, electrolyte mass transport, multiphase gas bubble evolution, and convective heat transfer, the following design paradigm is recommended:

#### 1. Four-Axis Classification Framework

| Axis | Levels (Low to High) | Selection Criteria & Boundary |
| :--- | :--- | :--- |
| **Electrochemistry Fidelity** | 1. Primary Current Distribution<br>2. Secondary Current Distribution<br>3. Tertiary Current Distribution (Nernst-Planck)<br>4. Porous Electrode / Battery interfaces | - If concentration gradients in the electrolyte are negligible, use Primary or Secondary Current Distribution (solves Ohm's law only).<br>- If mass transport resistance cannot be ignored (e.g., limit diffusion current at high current densities), Tertiary Current Distribution is required.<br>- For complex interlayer media like lithium batteries and fuel cell catalyst layers, use dedicated porous electrode interfaces. |
| **Fluid Flow Regime** | 1. Stationary / No Flow<br>2. Laminar Flow<br>3. Turbulent Flow<br>4. Microfluidics<br>5. Porous Medium Flow (Darcy/Brinkman)<br>6. Multiphase Flow | - Convective transport can be neglected if the Peclet number is very small.<br>- Gas generation (e.g., hydrogen/oxygen evolution) alters electrolyte conductivity, requiring multiphase Bubbly Flow interfaces.<br>- For gas-liquid transport inside porous electrodes, use Darcy/Brinkman equations. |
| **Coupled Physics** | 1. EC + Mass Transport (Convective transport)<br>2. EC + Mass Transport + Fluid (Bubble conductivity effects)<br>3. EC + Fluid + Heat Transfer (Non-isothermal systems) | - Convective Transport: Fluid velocity \(u\) is coupled as the convective term in dilute species transport.<br>- Conductivity Correction: Gas bubble volume fraction \(\phi_g\) lowers effective conductivity \(\sigma_{\text{eff}} = \sigma_0 (1-\phi_g)^{1.5}\). |
| **Spatial Dimension** | 1. 1D Kinetics<br>2. 2D / 2D Axisymmetric Transport<br>3. 3D Flow Channel Design | - 1D models are used for parameter fitting of Tafel slopes and activation energies.<br>- 2D Axisymmetric models simulate Rotating Disk Electrodes (RDE) or local electrode flows.<br>- 3D models are reserved for asymmetric channels (e.g., serpentine flow channels) or complex multi-component assemblies. |

#### 2. Coupling Variables & Formulation Patterns

When programmatically generating or modifying models, ensure the following coupling variables are correctly mapped:

```
                                [Laminar Flow]
                                      │
                                      │ (Velocity field u)
                                      ▼
     [Tertiary EC] ──(Reaction Source R)──> [Transport of Dilute Species (tds)]
           ▲                                    │
           │                                    │ (Electrolyte Conductivity / Concentration C)
           └────────────────────────────────────┘
```

*   **Fluid-to-Mass Transport Coupling**: The fluid velocity vector \(\mathbf{u}\) must be inputted into the convection term of the Transport of Dilute Species (`tds`) or Tertiary Current Distribution interface.
*   **Reaction-to-Transport Source Term**: The reaction molar source term \(R_i\) is directly calculated from the local current density \(i_{loc}\) and Faraday's constant \(F\):
    \[
    R_i = -\frac{\nu_i \cdot i_{loc}}{n \cdot F}
    \]
*   **Conductivity Correction in Multiphase Flow (Maxwell Relation)**：If gas evolution occurs at the electrode, the effective electrolyte conductivity \(\kappa_{\text{eff}}\) must be adjusted based on the local gas volume fraction \(\phi_g\):
    \[
    \kappa_{\text{eff}} = \kappa_0 \cdot (1 - \phi_g)^{1.5}
    \]

#### 3. Recommended Starter Templates

In the COMSOL Application Library, it is recommended to start from the following verified example `.mph` files rather than building geometry and physics from scratch:

1.  **Electrodeposition and Bubbly Flow**: `Electrodeposition_Module\Tutorials\cu_electrowinning_bubbly_flow.mph`
    *   *Features*: Tertiary Current Distribution + Transport of Dilute Species + Bubbly Flow. Perfect for designing electrochemical reactors with gas-liquid separation.
2.  **Non-Isothermal Fuel Cell**: `Fuel_Cell_and_Electrolyzer_Module\Fuel_Cells\nonisothermal_pem_fuel_cell.mph`
    *   *Features*: Electrochemical reactions + porous transport + gas channel flow + solid/liquid heat transfer. A classic benchmark for non-isothermal multiphase EC-CFD systems.
3.  **Electrokinetic Valve Control**: `Microfluidics_Module\Fluid_Flow\electrokinetic_valve.mph`
    *   *Features*: Electrostatics (Coulombic force) + Laminar Flow (electrokinetic body force source term). Best for microfluidics lab-on-a-chip designs.

---

### 🧪 Automation Workflow Example

Below is an example workflow showing how tool calls are executed programmatically to load and modify model parameters:

#### Step 1: Query COMSOL Session Status
```json
// Call Tool: comsol_status
{}
// Response:
// { "connected": true, "version": "6.3", "standalone": true }
```

#### Step 2: Load Simulation Model
```json
// Call Tool: model_load
{ "file_path": "C:\\COMSOL_Models\\vacuum_drying.mph" }
// Response:
// { "success": true, "model": { "name": "vacuum_drying", ... } }
```

#### Step 3: Modify Parameters (Evaporation Rate & Temperature)
```json
// Call Tool: param_set
{
  "name": "kvap",
  "expression": "5e-6[1/s]"
}
// Call Tool: param_set
{
  "name": "Th",
  "expression": "75[degC]"
}
```

#### Step 4: Rebuild Geometry and Solve
```json
// Call Tool: geometry_build
{}
// Call Tool: study_solve
{
  "study_name": "Study 1"
}
```

#### Step 5: Evaluate Results and Export Image
```json
// Call Tool: results_evaluate
{
  "expression": "ht.Tmax",
  "unit": "degC"
}
// Call Tool: results_export_image
{
  "plot_group": "Temperature (ht)",
  "file_path": "C:\\COMSOL_Models\\T_max_distribution.png"
}
```
