# Water Plant Process Controller

## Overview

This project provides a simple, product-oriented framework for simulating and controlling water treatment processes, specifically focusing on precise chemical dosing and aeration. It includes a basic water plant simulator and a reusable PID controller, demonstrating a closed-loop control system.

This project was built to showcase a structured approach to developing control algorithms, including simulation, control, and testing.

## Project Structure

The repository is organized as follows:

- `water_plant_controller/`: The main Python package for the project.
  - `models/`: Contains data models, such as `water_quality.py`.
  - `simulation/`: Contains the process simulator, `plant_simulator.py`.
  - `control/`: Contains control algorithms, such as the generic `pid_controller.py`.
- `tests/`: Contains all unit and integration tests.
  - `test_water_quality.py`: Unit tests for the data model.
  - `test_pid_controller.py`: Unit tests for the PID controller.
  - `test_plant_simulator.py`: Unit tests for the simulator.
  - `test_integration.py`: Integration test for the closed-loop system.
- `config/`: Contains configuration files, such as `settings.py` for simulation and controller parameters.
- `data/`: (Placeholder) For simulation data.

## Configuration

The core parameters for the simulation and PID controllers are stored in `config/settings.py`. You can modify this file to tune the system's behavior without changing the source code.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Install dependencies:**
    This project requires `matplotlib` for visualization. Install it using the provided `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

This project includes scripts to run the simulation, log the results, and visualize the output.

### 1. Running the Simulation
To run the simulation and generate a `simulation_log.csv` file, execute the following command from the root directory:
```bash
python3 run_simulation.py
```
This will run a default simulation of 300 steps. You can also customize the simulation with command-line arguments:
```bash
python3 run_simulation.py --steps 500 --turbidity-setpoint 4.5 --log-file custom_log.csv
```
You can also choose the controller type (`pid`, `on-off`, `precision-pid`, or `adaptive-pid`):
```bash
python3 run_simulation.py --controller-type precision-pid
```
The `precision-pid` controller adds feed-forward compensation, actuator constraints, and global energy budgeting.
The `adaptive-pid` controller builds on the precision mode and self-tunes the PID gains online based on recent error history. When either advanced mode is enabled, the generated CSV log includes additional diagnostic columns (`coagulant_saturated`, `aeration_saturated`, `coagulant_cost`, `aeration_cost`, `energy_scaling_factor`, `coagulant_energy_scale`, `aeration_energy_scale`, `energy_budget`, `primary_sensor_fault`, `secondary_sensor_fault`, `redundant_sensor_active`, `fault_fallback_active`) that capture saturation events, energy usage, redundant sensor decisions, and fault fallback behaviour.
The logger now also records both turbidity and dissolved oxygen fusion metrics: raw values, redundant-fused readings, Kalman-soft measurements, channel-specific reliability (`turbidity_reliability`, `dissolved_oxygen_reliability`), and their corresponding monitor scores/trip flags. These columns trace the soft-sensing layer that blends Kalman-filtered estimates with redundant probes to prevent over-dosing or over-aeration when sensor bias grows.


### 2. Visualizing the Results
After running the simulation, you can generate a plot of the results:
```bash
python3 visualize_log.py
```
This script reads `simulation_log.csv` and saves the output as `simulation_plot.png`. You can specify different input and output files:
```bash
python3 visualize_log.py --log-file custom_log.csv --output-image custom_plot.png
```
When the input log contains the precision-control diagnostics, the visualiser now renders six stacked panels:
- Setpoint tracking for turbidity and dissolved oxygen（软测量 vs 设定值）；
- 原始/融合/软测量对比（支持浊度与溶解氧双通道）；
- 可信度、故障评分与 trip 曲线，让监测改进一目了然；
- 控制输出与扰动、累计成本与饱和度概览。
运行结束后还会输出包含均值、能耗、故障次数与可靠度统计的文字摘要。

### 3. Running Tests
To verify that the system is working correctly, you can run all the tests from the root directory:
```bash
python3 -m unittest discover tests
```

### 4. Running the HIL Demo
To exercise the new hardware-in-the-loop scaffold from the command line, run:
```bash
python3 scripts/run_hil_demo.py --steps 10 --scenario steady --output outputs/hil_demo_summary.json
```
You can switch scenarios, override actuator commands, and inject a sensor fault:
```bash
python3 scripts/run_hil_demo.py --scenario turbidity_spike --coagulant-dose 6 --aeration-rate 10 --fault-sensor turbidity --fault-mode stuck --fault-value 42
```
The script writes a JSON summary containing all snapshots, the latest measurement, and the applied HIL settings.
You can also run the REST end-to-end flow with `python3 scripts/run_hil_rest_e2e.py --output outputs/hil_rest_e2e_summary.json`, then open the built-in dashboard at `http://127.0.0.1:5000/hil/dashboard` (or `http://127.0.0.1:5056/hil/dashboard` if you use the e2e script defaults). The dashboard now supports auto-stepping, one-click demo presets, summary cards, a lightweight HIL optimization leaderboard, adjustable optimization weights, optimization result export to JSON/CSV, recording export, and JSON replay for demo review.

For direct API-based multi-model collaboration, see `docs/AI_DIRECT_API_COLLAB.md` and route tasks with `python scripts/route_ai_task.py --task-type coding --risk medium --budget medium --stage implement --deadline urgent`.
To execute a routed lead/reviewer flow directly, use `python scripts/orchestrate_model_flow.py --task-type coding --risk medium --budget medium --stage implement --deadline urgent --prompt "your task" --dry-run`. Each run can also archive a structured report under `outputs/ai_runs/`, including split artifacts such as `*.prompt_bundle.md`, `*.lead.md`, and `*.reviewer.md`.

## Examples and Tutorials

This project includes a comprehensive set of examples that serve as a beginner-to-advanced development guide. You can find them in the `/examples` directory.

Each example is self-contained in its own folder and includes a `README.md` file that explains the concepts and the code.

-   **[Example 1: Basic Simulation](./examples/01_basic_simulation/README.md)**
-   **[Example 2: PID Controller Tuning](./examples/02_tuning_pid_controller/README.md)**
-   **[Example 3: Controller Comparison](./examples/03_comparing_controllers/README.md)**
-   **[Example 4: Advanced Simulation Features](./examples/04_advanced_simulation_features/README.md)**
-   **[Example 5: Extending the Simulator Guide](./examples/05_extending_the_simulator/README.md)**
-   **[Example 12: Adaptive vs Precision PID](./examples/12_adaptive_control_demo/README.md)**
-   **[Example 13: Sensor Fault Demo](./examples/13_sensor_fault_demo/README.md)**
-   **[Example 14: Energy Budget Demo](./examples/14_energy_budget_demo/README.md)**
-   **[Example 16: Long-Run Report](./examples/16_long_run_report/README.md)**
-   **[Example 17: MPC vs Adaptive Control](./examples/17_mpc_vs_adaptive/README.md)**

## Key Components

### `WaterQuality`
A simple dataclass located in `water_plant_controller/models/water_quality.py` that represents the state of water at a point in time.

### `PlantSimulator`
Located in `water_plant_controller/simulation/plant_simulator.py`. This class simulates the response of a water body to coagulant dosing and aeration based on a simple physics model. For a detailed explanation of the simulation principles in Chinese, see [SIMULATION_PRINCIPLES_CN.md](./SIMULATION_PRINCIPLES_CN.md).

### `PIDController`
A generic PID controller in `water_plant_controller/control/pid_controller.py`. It is reusable and can be configured for both direct-acting (e.g., heating) and reverse-acting (e.g., cooling, turbidity reduction) control loops.

### Sensor Credibility Feedback
`run_simulation.py` integrates a Kalman-filter-based monitor (`utils/sensor_monitor.py`) that now fuses redundant probes for both turbidity and dissolved oxygen. It emits `fused_turbidity`/`fused_dissolved_oxygen`, channel reliabilities, and monitor fault scores/trips (`turbidity_monitor_fault_score`, `turbidity_monitor_fault_trip`, `do_monitor_fault_score`, `do_monitor_fault_trip`). The control loop consumes these credibility-weighted readings, cutting the risk of over-dosing chemicals or over-aerating when bias emerges while the log preserves raw vs fused signals for later analysis.

### Filtering & MPC 对传感器扰动的作用
- **Kalman + 冗余传感器**：针对瞬时噪声，卡尔曼滤波提供平滑估计；当主探头发生漂移时，冗余探头及时接管，`*_reliability` 会下降以提醒控制器降低信任度。
- **可信度驱动的 PID/MPC**：`PrecisionPIDController` 与 `MPCFaultTolerantController` 会读取 `turbidity_reliability`、`dissolved_oxygen_reliability` 等指标，在可信度下降时限制积分累积与控制增量，避免将传感器扰动当成真实工况。
- **MPC 的软测量预测**：MPC 通过软测量和偏差估计修正状态预测，在传感器剧烈扰动时自动收敛到更保守的剂量，从而减少能耗和化学品浪费。

### `MPCFaultTolerantController`
Located in `water_plant_controller/control/mpc_controller.py`. This lightweight predictive controller provides a research-grade scaffold for model predictive control. It considers actuator constraints, sensor reliability, and bias estimates when choosing dosing actions and exposes diagnostics for further tuning.
