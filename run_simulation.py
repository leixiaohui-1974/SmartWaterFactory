import csv
import argparse
import os
import sys
from datetime import datetime
from typing import Union, Dict, Any
from water_plant_controller.models.water_quality import WaterQuality
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.control.pid_controller import PIDController
from water_plant_controller.control.on_off_controller import OnOffController
from config.settings import SIMULATION_DEFAULTS, PID_GAINS
from config.validator import validate_config

def run_and_log_simulation(
    steps: int, 
    log_file: str, 
    turbidity_setpoint: float, 
    do_setpoint: float, 
    controller_type: str
) -> bool:
    """
    运行水厂模拟并将每个步骤的状态记录到CSV文件中。
    
    Args:
        steps (int): 要运行的模拟步数，必须为正整数
        log_file (str): 输出CSV日志文件的路径
        turbidity_setpoint (float): 浊度设定点，必须为正数
        do_setpoint (float): 溶解氧设定点，必须为正数
        controller_type (str): 控制器类型，'pid'或'on-off'
    
    Returns:
        bool: 模拟是否成功完成
        
    Raises:
        ValueError: 当输入参数无效时
        IOError: 当文件操作失败时
        Exception: 当模拟过程中发生其他错误时
    """
    # 输入验证
    try:
        _validate_simulation_inputs(steps, log_file, turbidity_setpoint, do_setpoint, controller_type)
    except ValueError as e:
        print(f"输入参数错误: {e}")
        return False
    
    # 0. 验证配置
    try:
        validate_config(SIMULATION_DEFAULTS, PID_GAINS)
    except (ValueError, TypeError) as e:
        print(f"配置验证失败: {e}")
        return False

    # 1. 初始化
    try:
        initial_quality = WaterQuality(
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            ph=7.0,
            turbidity=25.0,
            dissolved_oxygen=4.0
        )
        simulator = PlantSimulator(initial_quality)
    except Exception as e:
        print(f"模拟器初始化失败: {e}")
        return False

    # 2. 控制器设置
    try:
        if controller_type == 'pid':
            dosing_gains = PID_GAINS["dosing_controller"]
            aeration_gains = PID_GAINS["aeration_controller"]

            dosing_controller = PIDController(
                Kp=dosing_gains["Kp"], Ki=dosing_gains["Ki"], Kd=dosing_gains["Kd"],
                setpoint=turbidity_setpoint, reverse_acting=True
            )
            dosing_controller.set_integral_limits(-5, 5)

            aeration_controller = PIDController(
                Kp=aeration_gains["Kp"], Ki=aeration_gains["Ki"], Kd=aeration_gains["Kd"],
                setpoint=do_setpoint
            )
            aeration_controller.set_integral_limits(-15, 15)

        elif controller_type == 'on-off':
            dosing_controller = OnOffController(setpoint=turbidity_setpoint, reverse_acting=True)
            aeration_controller = OnOffController(setpoint=do_setpoint)

        else:
            raise ValueError(f"未知的控制器类型: {controller_type}")

        dosing_controller.set_output_limits(0, 10)
        aeration_controller.set_output_limits(0, 20)
    except Exception as e:
        print(f"控制器初始化失败: {e}")
        return False

    # 3. 设置CSV日志记录
    try:
        # 确保输出目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        with open(log_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'timestamp', 'turbidity', 'dissolved_oxygen',
                'turbidity_setpoint', 'do_setpoint',
                'coagulant_dose', 'aeration_rate'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # 4. 模拟循环
            print(f"运行模拟 {steps} 步... 记录到 {log_file}")
            try:
                for i in range(steps):
                    current_quality = simulator.current_quality

                    # 计算控制动作
                    try:
                        coagulant_dose = dosing_controller.calculate(current_quality.turbidity)
                        aeration_rate = aeration_controller.calculate(current_quality.dissolved_oxygen)
                    except Exception as e:
                        print(f"控制器计算错误 (步骤 {i+1}): {e}")
                        return False

                    # 将动作应用到模拟器
                    try:
                        simulator.step(coagulant_dose=coagulant_dose, aeration_rate=aeration_rate)
                    except Exception as e:
                        print(f"模拟器步进错误 (步骤 {i+1}): {e}")
                        return False

                    # 记录数据
                    try:
                        writer.writerow({
                            'timestamp': current_quality.timestamp.isoformat(),
                            'turbidity': current_quality.turbidity,
                            'dissolved_oxygen': current_quality.dissolved_oxygen,
                            'turbidity_setpoint': turbidity_setpoint,
                            'do_setpoint': do_setpoint,
                            'coagulant_dose': coagulant_dose,
                            'aeration_rate': aeration_rate
                        })
                    except Exception as e:
                        print(f"数据记录错误 (步骤 {i+1}): {e}")
                        return False
                        
                    # 进度显示
                    if (i + 1) % 50 == 0:
                        print(f"已完成 {i + 1}/{steps} 步")

                print("模拟完成。")
                return True
                
            except KeyboardInterrupt:
                print("\n模拟被用户中断。")
                return False
            except Exception as e:
                print(f"模拟循环中发生未预期错误: {e}")
                return False

    except PermissionError:
        print(f"错误：没有权限写入文件 '{log_file}'")
        return False
    except IOError as e:
        print(f"错误：无法写入日志文件 '{log_file}': {e}")
        return False
    except Exception as e:
        print(f"文件操作发生未预期错误: {e}")
        return False

def _validate_simulation_inputs(steps: int, log_file: str, turbidity_setpoint: float, 
                               do_setpoint: float, controller_type: str) -> None:
    """验证模拟输入参数"""
    if not isinstance(steps, int) or steps <= 0:
        raise ValueError(f"步数必须为正整数，得到: {steps}")
    
    if not isinstance(log_file, str) or not log_file.strip():
        raise ValueError("日志文件路径不能为空")
    
    if not isinstance(turbidity_setpoint, (int, float)) or turbidity_setpoint <= 0:
        raise ValueError(f"浊度设定点必须为正数，得到: {turbidity_setpoint}")
    
    if not isinstance(do_setpoint, (int, float)) or do_setpoint <= 0:
        raise ValueError(f"溶解氧设定点必须为正数，得到: {do_setpoint}")
    
    if controller_type not in ['pid', 'on-off']:
        raise ValueError(f"控制器类型必须为'pid'或'on-off'，得到: {controller_type}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="运行水厂模拟。")
    parser.add_argument('--steps', type=int, default=300, help='要运行的模拟步数。')
    parser.add_argument('--log-file', type=str, default='simulation_log.csv', help='输出CSV日志文件的路径。')
    parser.add_argument('--turbidity-setpoint', type=float, default=5.0, help='浊度设定点。')
    parser.add_argument('--do-setpoint', type=float, default=8.5, help='溶解氧设定点。')
    parser.add_argument('--controller-type', type=str, default='pid', choices=['pid', 'on-off'], help='要使用的控制器类型。')

    args = parser.parse_args()

    success = run_and_log_simulation(
        steps=args.steps,
        log_file=args.log_file,
        turbidity_setpoint=args.turbidity_setpoint,
        do_setpoint=args.do_setpoint,
        controller_type=args.controller_type
    )
    
    sys.exit(0 if success else 1)
