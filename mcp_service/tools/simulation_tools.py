#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP仿真工具集。

封装水厂仿真相关功能，提供MCP工具接口。
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from ..models.schemas import ToolParameter, ToolParameterType, Tool
from ..registry import get_registry
from ..session import get_session_manager, SimulationInstance
from ..config import get_config

# 导入核心仿真模块
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.control.pid_controller import PIDController
from water_plant_controller.control.precision_controller import PrecisionPIDController
from water_plant_controller.control.mpc_controller import MPCFaultTolerantController
from water_plant_controller.hil import DEFAULT_HIL_SCENARIOS, HILSimulator
from config.settings import SIMULATION_DEFAULTS, PID_GAINS

logger = logging.getLogger(__name__)


def _get_session_and_simulation(session_id: Optional[str], simulation_id: str) -> tuple[Any, SimulationInstance]:
    if not session_id:
        raise ValueError("Session ID is required")

    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    simulation = session.simulations.get(simulation_id)
    if not simulation:
        raise ValueError(f"Simulation {simulation_id} not found")

    return session, simulation


def _serialize_hil_status(simulation_id: str, simulation: SimulationInstance) -> Dict[str, Any]:
    simulator = simulation.simulator
    latest_snapshot = simulation.results[-1] if simulation.results else None
    return {
        "simulation_id": simulation_id,
        "status": simulation.status,
        "current_step": simulation.current_step,
        "total_steps": simulation.total_steps,
        "scenario": getattr(simulator, "active_scenario", None),
        "available_scenarios": sorted(getattr(simulator, "scenarios", {}).keys()),
        "latest_snapshot": latest_snapshot,
        "results_count": len(simulation.results),
        "start_time": simulation.start_time.isoformat() if simulation.start_time else None,
        "end_time": simulation.end_time.isoformat() if simulation.end_time else None,
        "error": simulation.error,
    }


def _create_controller(controller_type: str, setpoint: float, is_reverse: bool = False):
    """创建控制器实例。"""
    if controller_type == "pid":
        gains = PID_GAINS.get("dosing_controller" if not is_reverse else "aeration_controller", {})
        return PIDController(
            setpoint=setpoint,
            Kp=gains.get("Kp", 1.0),
            Ki=gains.get("Ki", 0.1),
            Kd=gains.get("Kd", 0.01),
            reverse_acting=is_reverse
        )
    elif controller_type == "precision_pid":
        gains = PID_GAINS.get("dosing_controller" if not is_reverse else "aeration_controller", {})
        return PrecisionPIDController(
            setpoint=setpoint,
            Kp=gains.get("Kp", 1.0),
            Ki=gains.get("Ki", 0.1),
            Kd=gains.get("Kd", 0.01),
            reverse_acting=is_reverse
        )
    # 可以添加更多控制器类型
    else:
        raise ValueError(f"Unsupported controller type: {controller_type}")


async def start_simulation_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """启动仿真的处理器。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        仿真启动结果
    """
    if not session_id:
        raise ValueError("Session ID is required")

    # 获取会话
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # 检查并发仿真限制
    config = get_config()
    active_simulations = sum(1 for sim in session.simulations.values() if sim.status == "running")
    if active_simulations >= config.max_concurrent_simulations_per_user:
        raise RuntimeError(
            f"Maximum concurrent simulations ({config.max_concurrent_simulations_per_user}) reached for this user"
        )

    # 解析参数
    steps = arguments.get("steps", 100)
    turbidity_setpoint = arguments.get("turbidity_setpoint", 2.0)
    do_setpoint = arguments.get("do_setpoint", 8.0)
    controller_type = arguments.get("controller_type", "pid")
    enable_faults = arguments.get("enable_faults", False)
    enable_disturbances = arguments.get("enable_disturbances", False)

    # 验证参数范围
    if steps > config.max_simulation_steps:
        raise ValueError(f"Steps cannot exceed {config.max_simulation_steps}")

    # 创建初始水质
    initial_quality = WaterQuality(
        timestamp=datetime.now(),
        ph=7.0,
        turbidity=25.0,
        dissolved_oxygen=4.0
    )

    # 创建仿真器
    simulator = PlantSimulator(initial_quality)

    # 创建控制器
    try:
        turbidity_controller = _create_controller(controller_type, turbidity_setpoint, is_reverse=False)
        do_controller = _create_controller(controller_type, do_setpoint, is_reverse=True)
    except Exception as e:
        raise ValueError(f"Failed to create controllers: {e}")

    # 生成仿真ID
    simulation_id = str(uuid.uuid4())

    # 创建仿真实例
    simulation_instance = SimulationInstance(
        simulator=simulator,
        status="running",
        start_time=datetime.now(),
        current_step=0,
        total_steps=steps
    )

    # 保存到会话
    session.simulations[simulation_id] = simulation_instance

    # 在后台运行仿真
    async def run_simulation():
        """后台运行仿真。"""
        try:
            results = []
            for step in range(steps):
                if simulation_instance.status != "running":
                    break

                # 获取当前水质
                current_quality = simulator.current_quality

                # 计算控制输出
                coagulant_dose = turbidity_controller.compute(current_quality.turbidity)
                aeration_rate = do_controller.compute(current_quality.dissolved_oxygen)

                # 执行仿真步骤
                simulator.step(coagulant_dose, aeration_rate)

                # 记录结果
                results.append({
                    "step": step,
                    "timestamp": datetime.now().isoformat(),
                    "turbidity": current_quality.turbidity,
                    "dissolved_oxygen": current_quality.dissolved_oxygen,
                    "ph": current_quality.ph,
                    "coagulant_dose": coagulant_dose,
                    "aeration_rate": aeration_rate
                })

                simulation_instance.current_step = step + 1

                # 短暂延迟以模拟实时性
                await asyncio.sleep(0.01)

            # 仿真完成
            simulation_instance.status = "completed"
            simulation_instance.end_time = datetime.now()
            simulation_instance.results = results

            logger.info(f"Simulation {simulation_id} completed successfully")

        except Exception as e:
            logger.error(f"Simulation {simulation_id} failed: {e}", exc_info=True)
            simulation_instance.status = "error"
            simulation_instance.error = str(e)
            simulation_instance.end_time = datetime.now()

    # 启动后台任务
    asyncio.create_task(run_simulation())

    return {
        "simulation_id": simulation_id,
        "status": "started",
        "message": f"Simulation started with {steps} steps",
        "parameters": {
            "steps": steps,
            "turbidity_setpoint": turbidity_setpoint,
            "do_setpoint": do_setpoint,
            "controller_type": controller_type,
            "enable_faults": enable_faults,
            "enable_disturbances": enable_disturbances
        }
    }


async def get_simulation_status_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """获取仿真状态的处理器。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        仿真状态信息
    """
    if not session_id:
        raise ValueError("Session ID is required")

    simulation_id = arguments.get("simulation_id")
    if not simulation_id:
        raise ValueError("simulation_id is required")

    # 获取会话
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # 获取仿真实例
    simulation = session.simulations.get(simulation_id)
    if not simulation:
        raise ValueError(f"Simulation {simulation_id} not found")

    # 计算进度
    progress = 0
    if simulation.total_steps > 0:
        progress = (simulation.current_step / simulation.total_steps) * 100

    # 计算运行时间
    elapsed_time = None
    if simulation.start_time:
        end_time = simulation.end_time or datetime.now()
        elapsed_time = (end_time - simulation.start_time).total_seconds()

    return {
        "simulation_id": simulation_id,
        "status": simulation.status,
        "current_step": simulation.current_step,
        "total_steps": simulation.total_steps,
        "progress": round(progress, 2),
        "start_time": simulation.start_time.isoformat() if simulation.start_time else None,
        "end_time": simulation.end_time.isoformat() if simulation.end_time else None,
        "elapsed_time": elapsed_time,
        "error": simulation.error,
        "results_count": len(simulation.results)
    }


async def stop_simulation_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """停止仿真的处理器。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        停止结果
    """
    if not session_id:
        raise ValueError("Session ID is required")

    simulation_id = arguments.get("simulation_id")
    if not simulation_id:
        raise ValueError("simulation_id is required")

    # 获取会话
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # 获取仿真实例
    simulation = session.simulations.get(simulation_id)
    if not simulation:
        raise ValueError(f"Simulation {simulation_id} not found")

    if simulation.status != "running":
        return {
            "simulation_id": simulation_id,
            "message": f"Simulation is not running (current status: {simulation.status})"
        }

    # 停止仿真
    simulation.status = "stopped"
    simulation.end_time = datetime.now()

    return {
        "simulation_id": simulation_id,
        "status": "stopped",
        "message": "Simulation stopped successfully",
        "steps_completed": simulation.current_step
    }


async def get_simulation_results_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """获取仿真结果的处理器。

    Args:
        arguments: 工具参数
        session_id: 会话ID

    Returns:
        仿真结果数据
    """
    if not session_id:
        raise ValueError("Session ID is required")

    simulation_id = arguments.get("simulation_id")
    if not simulation_id:
        raise ValueError("simulation_id is required")

    # 获取会话
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # 获取仿真实例
    simulation = session.simulations.get(simulation_id)
    if not simulation:
        raise ValueError(f"Simulation {simulation_id} not found")

    # 获取结果范围
    start_step = arguments.get("start_step", 0)
    end_step = arguments.get("end_step", len(simulation.results))
    limit = arguments.get("limit", 1000)

    # 限制返回数据量
    results = simulation.results[start_step:end_step]
    if len(results) > limit:
        results = results[:limit]

    return {
        "simulation_id": simulation_id,
        "total_results": len(simulation.results),
        "returned_results": len(results),
        "start_step": start_step,
        "end_step": min(end_step, len(simulation.results)),
        "results": results
    }


async def start_hil_simulation_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    if not session_id:
        raise ValueError("Session ID is required")

    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    config = get_config()
    active_simulations = sum(1 for sim in session.simulations.values() if sim.status == "running")
    if active_simulations >= config.max_concurrent_simulations_per_user:
        raise RuntimeError(
            f"Maximum concurrent simulations ({config.max_concurrent_simulations_per_user}) reached for this user"
        )

    scenario = arguments.get("scenario", "steady")
    dt_s = arguments.get("dt_s", 1.0)
    random_seed = arguments.get("random_seed")
    initial_turbidity = arguments.get("initial_turbidity", 25.0)
    initial_do = arguments.get("initial_dissolved_oxygen", 4.0)
    initial_ph = arguments.get("initial_ph", 7.0)

    simulator = HILSimulator(
        WaterQuality(
            timestamp=datetime.now(),
            ph=initial_ph,
            turbidity=initial_turbidity,
            dissolved_oxygen=initial_do,
        ),
        dt_s=dt_s,
        scenario=scenario,
        random_seed=random_seed,
    )

    simulation_id = str(uuid.uuid4())
    simulation_instance = SimulationInstance(
        simulator=simulator,
        status="running",
        start_time=datetime.now(),
        current_step=0,
        total_steps=0,
    )
    session.simulations[simulation_id] = simulation_instance

    return {
        "simulation_id": simulation_id,
        "status": "started",
        "mode": "hil",
        "scenario": scenario,
        "dt_s": dt_s,
        "available_scenarios": sorted(DEFAULT_HIL_SCENARIOS.keys()),
    }


async def step_hil_simulation_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    simulation_id = arguments.get("simulation_id")
    if not simulation_id:
        raise ValueError("simulation_id is required")

    _, simulation = _get_session_and_simulation(session_id, simulation_id)
    if not isinstance(simulation.simulator, HILSimulator):
        raise ValueError(f"Simulation {simulation_id} is not a HIL simulation")

    steps = int(arguments.get("steps", 1))
    if steps < 1:
        raise ValueError("steps must be at least 1")

    snapshots = [simulation.simulator.step().to_dict() for _ in range(steps)]
    simulation.results.extend(snapshots)
    simulation.current_step += steps
    simulation.total_steps = simulation.current_step

    return {
        "simulation_id": simulation_id,
        "status": simulation.status,
        "steps_executed": steps,
        "current_step": simulation.current_step,
        "latest_snapshot": snapshots[-1],
    }


async def set_hil_scenario_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    simulation_id = arguments.get("simulation_id")
    scenario_name = arguments.get("scenario_name")
    if not simulation_id:
        raise ValueError("simulation_id is required")
    if not scenario_name:
        raise ValueError("scenario_name is required")

    _, simulation = _get_session_and_simulation(session_id, simulation_id)
    if not isinstance(simulation.simulator, HILSimulator):
        raise ValueError(f"Simulation {simulation_id} is not a HIL simulation")

    simulation.simulator.set_scenario(scenario_name)
    return {
        "simulation_id": simulation_id,
        "status": simulation.status,
        "scenario": simulation.simulator.active_scenario,
    }


async def set_hil_control_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    simulation_id = arguments.get("simulation_id")
    if not simulation_id:
        raise ValueError("simulation_id is required")

    _, simulation = _get_session_and_simulation(session_id, simulation_id)
    if not isinstance(simulation.simulator, HILSimulator):
        raise ValueError(f"Simulation {simulation_id} is not a HIL simulation")

    applied = {}
    for actuator_name in ("coagulant_dose", "aeration_rate"):
        if actuator_name in arguments:
            simulation.simulator.set_control_command(actuator_name, float(arguments[actuator_name]))
            applied[actuator_name] = float(arguments[actuator_name])

        current_key = f"{actuator_name}_ma"
        if current_key in arguments:
            simulation.simulator.set_control_command_from_milliamps(actuator_name, float(arguments[current_key]))
            applied[current_key] = float(arguments[current_key])

    if not applied:
        raise ValueError("At least one actuator command is required")

    return {
        "simulation_id": simulation_id,
        "status": simulation.status,
        "applied": applied,
    }


async def inject_hil_fault_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    simulation_id = arguments.get("simulation_id")
    sensor_name = arguments.get("sensor_name")
    mode = arguments.get("mode")
    if not simulation_id:
        raise ValueError("simulation_id is required")
    if not sensor_name:
        raise ValueError("sensor_name is required")
    if not mode:
        raise ValueError("mode is required")

    _, simulation = _get_session_and_simulation(session_id, simulation_id)
    if not isinstance(simulation.simulator, HILSimulator):
        raise ValueError(f"Simulation {simulation_id} is not a HIL simulation")

    value = arguments.get("value")
    bias = float(arguments.get("bias", 0.0))
    simulation.simulator.inject_sensor_fault(sensor_name, mode, value=value, bias=bias)
    return {
        "simulation_id": simulation_id,
        "status": simulation.status,
        "sensor_name": sensor_name,
        "mode": mode,
        "value": value,
        "bias": bias,
    }


async def clear_hil_fault_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    simulation_id = arguments.get("simulation_id")
    sensor_name = arguments.get("sensor_name")
    if not simulation_id:
        raise ValueError("simulation_id is required")
    if not sensor_name:
        raise ValueError("sensor_name is required")

    _, simulation = _get_session_and_simulation(session_id, simulation_id)
    if not isinstance(simulation.simulator, HILSimulator):
        raise ValueError(f"Simulation {simulation_id} is not a HIL simulation")

    simulation.simulator.clear_sensor_fault(sensor_name)
    return {
        "simulation_id": simulation_id,
        "status": simulation.status,
        "sensor_name": sensor_name,
        "cleared": True,
    }


async def get_hil_simulation_status_handler(arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    simulation_id = arguments.get("simulation_id")
    if not simulation_id:
        raise ValueError("simulation_id is required")

    _, simulation = _get_session_and_simulation(session_id, simulation_id)
    if not isinstance(simulation.simulator, HILSimulator):
        raise ValueError(f"Simulation {simulation_id} is not a HIL simulation")

    return _serialize_hil_status(simulation_id, simulation)


def register_simulation_tools():
    """注册所有仿真工具。"""
    registry = get_registry()

    # 注册 start_simulation 工具
    start_sim_tool = Tool(
        name="start_simulation",
        description="Start a water plant simulation with specified parameters",
        parameters=[
            ToolParameter(
                name="steps",
                type=ToolParameterType.INTEGER,
                description="Number of simulation steps to run",
                required=False,
                default=100,
                minimum=1,
                maximum=10000
            ),
            ToolParameter(
                name="turbidity_setpoint",
                type=ToolParameterType.NUMBER,
                description="Target turbidity value (NTU)",
                required=False,
                default=2.0,
                minimum=0.1,
                maximum=10.0
            ),
            ToolParameter(
                name="do_setpoint",
                type=ToolParameterType.NUMBER,
                description="Target dissolved oxygen value (mg/L)",
                required=False,
                default=8.0,
                minimum=2.0,
                maximum=12.0
            ),
            ToolParameter(
                name="controller_type",
                type=ToolParameterType.STRING,
                description="Type of controller to use",
                required=False,
                default="pid",
                enum=["pid", "precision_pid", "mpc", "adaptive"]
            ),
            ToolParameter(
                name="enable_faults",
                type=ToolParameterType.BOOLEAN,
                description="Enable sensor fault simulation",
                required=False,
                default=False
            ),
            ToolParameter(
                name="enable_disturbances",
                type=ToolParameterType.BOOLEAN,
                description="Enable process disturbances",
                required=False,
                default=False
            ),
        ],
        handler=start_simulation_handler,
        category="simulation",
        version="1.0.0"
    )
    registry.register(start_sim_tool)

    # 注册 get_simulation_status 工具
    status_tool = Tool(
        name="get_simulation_status",
        description="Get the current status of a running simulation",
        parameters=[
            ToolParameter(
                name="simulation_id",
                type=ToolParameterType.STRING,
                description="Simulation ID returned from start_simulation",
                required=True
            ),
        ],
        handler=get_simulation_status_handler,
        category="simulation",
        version="1.0.0"
    )
    registry.register(status_tool)

    # 注册 stop_simulation 工具
    stop_tool = Tool(
        name="stop_simulation",
        description="Stop a running simulation",
        parameters=[
            ToolParameter(
                name="simulation_id",
                type=ToolParameterType.STRING,
                description="Simulation ID to stop",
                required=True
            ),
        ],
        handler=stop_simulation_handler,
        category="simulation",
        version="1.0.0"
    )
    registry.register(stop_tool)

    # 注册 get_simulation_results 工具
    results_tool = Tool(
        name="get_simulation_results",
        description="Get results from a completed or running simulation",
        parameters=[
            ToolParameter(
                name="simulation_id",
                type=ToolParameterType.STRING,
                description="Simulation ID",
                required=True
            ),
            ToolParameter(
                name="start_step",
                type=ToolParameterType.INTEGER,
                description="Start step index",
                required=False,
                default=0
            ),
            ToolParameter(
                name="end_step",
                type=ToolParameterType.INTEGER,
                description="End step index",
                required=False
            ),
            ToolParameter(
                name="limit",
                type=ToolParameterType.INTEGER,
                description="Maximum number of results to return",
                required=False,
                default=1000,
                maximum=10000
            ),
        ],
        handler=get_simulation_results_handler,
        category="simulation",
        version="1.0.0"
    )
    registry.register(results_tool)

    start_hil_tool = Tool(
        name="start_hil_simulation",
        description="Start a hardware-in-the-loop simulation session",
        parameters=[
            ToolParameter(name="scenario", type=ToolParameterType.STRING, description="Initial HIL scenario", required=False, default="steady", enum=sorted(DEFAULT_HIL_SCENARIOS.keys())),
            ToolParameter(name="dt_s", type=ToolParameterType.NUMBER, description="Simulation step size in seconds", required=False, default=1.0, minimum=0.01, maximum=60.0),
            ToolParameter(name="random_seed", type=ToolParameterType.INTEGER, description="Optional deterministic seed", required=False),
            ToolParameter(name="initial_turbidity", type=ToolParameterType.NUMBER, description="Initial turbidity", required=False, default=25.0, minimum=0.0, maximum=200.0),
            ToolParameter(name="initial_dissolved_oxygen", type=ToolParameterType.NUMBER, description="Initial dissolved oxygen", required=False, default=4.0, minimum=0.0, maximum=20.0),
            ToolParameter(name="initial_ph", type=ToolParameterType.NUMBER, description="Initial pH", required=False, default=7.0, minimum=0.0, maximum=14.0),
        ],
        handler=start_hil_simulation_handler,
        category="simulation",
        version="1.0.0"
    )
    registry.register(start_hil_tool)

    step_hil_tool = Tool(
        name="step_hil_simulation",
        description="Advance a HIL simulation by one or more steps",
        parameters=[
            ToolParameter(name="simulation_id", type=ToolParameterType.STRING, description="HIL simulation ID", required=True),
            ToolParameter(name="steps", type=ToolParameterType.INTEGER, description="Number of steps to execute", required=False, default=1, minimum=1, maximum=1000),
        ],
        handler=step_hil_simulation_handler,
        category="simulation",
        version="1.0.0"
    )
    registry.register(step_hil_tool)

    scenario_hil_tool = Tool(
        name="set_hil_scenario",
        description="Switch the active scenario for a HIL simulation",
        parameters=[
            ToolParameter(name="simulation_id", type=ToolParameterType.STRING, description="HIL simulation ID", required=True),
            ToolParameter(name="scenario_name", type=ToolParameterType.STRING, description="Scenario name", required=True, enum=sorted(DEFAULT_HIL_SCENARIOS.keys())),
        ],
        handler=set_hil_scenario_handler,
        category="simulation",
        version="1.0.0"
    )
    registry.register(scenario_hil_tool)

    control_hil_tool = Tool(
        name="set_hil_control",
        description="Set actuator commands for a HIL simulation",
        parameters=[
            ToolParameter(name="simulation_id", type=ToolParameterType.STRING, description="HIL simulation ID", required=True),
            ToolParameter(name="coagulant_dose", type=ToolParameterType.NUMBER, description="Coagulant dosing command", required=False, minimum=0.0, maximum=20.0),
            ToolParameter(name="aeration_rate", type=ToolParameterType.NUMBER, description="Aeration command", required=False, minimum=0.0, maximum=20.0),
            ToolParameter(name="coagulant_dose_ma", type=ToolParameterType.NUMBER, description="Coagulant command in 4-20mA", required=False, minimum=4.0, maximum=20.0),
            ToolParameter(name="aeration_rate_ma", type=ToolParameterType.NUMBER, description="Aeration command in 4-20mA", required=False, minimum=4.0, maximum=20.0),
        ],
        handler=set_hil_control_handler,
        category="simulation",
        version="1.0.0"
    )
    registry.register(control_hil_tool)

    fault_hil_tool = Tool(
        name="inject_hil_fault",
        description="Inject a sensor fault into a HIL simulation",
        parameters=[
            ToolParameter(name="simulation_id", type=ToolParameterType.STRING, description="HIL simulation ID", required=True),
            ToolParameter(name="sensor_name", type=ToolParameterType.STRING, description="Sensor name", required=True, enum=["ph", "turbidity", "dissolved_oxygen"]),
            ToolParameter(name="mode", type=ToolParameterType.STRING, description="Fault mode", required=True, enum=["none", "stuck", "bias", "dropout"]),
            ToolParameter(name="value", type=ToolParameterType.NUMBER, description="Optional fault value", required=False),
            ToolParameter(name="bias", type=ToolParameterType.NUMBER, description="Optional fault bias", required=False, default=0.0),
        ],
        handler=inject_hil_fault_handler,
        category="simulation",
        version="1.0.0"
    )
    registry.register(fault_hil_tool)

    clear_fault_hil_tool = Tool(
        name="clear_hil_fault",
        description="Clear a sensor fault from a HIL simulation",
        parameters=[
            ToolParameter(name="simulation_id", type=ToolParameterType.STRING, description="HIL simulation ID", required=True),
            ToolParameter(name="sensor_name", type=ToolParameterType.STRING, description="Sensor name", required=True, enum=["ph", "turbidity", "dissolved_oxygen"]),
        ],
        handler=clear_hil_fault_handler,
        category="simulation",
        version="1.0.0"
    )
    registry.register(clear_fault_hil_tool)

    status_hil_tool = Tool(
        name="get_hil_simulation_status",
        description="Get current status and latest snapshot for a HIL simulation",
        parameters=[
            ToolParameter(name="simulation_id", type=ToolParameterType.STRING, description="HIL simulation ID", required=True),
        ],
        handler=get_hil_simulation_status_handler,
        category="simulation",
        version="1.0.0"
    )
    registry.register(status_hil_tool)

    logger.info("Registered simulation tools")
