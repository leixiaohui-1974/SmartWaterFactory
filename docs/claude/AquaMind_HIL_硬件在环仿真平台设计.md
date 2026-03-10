# AquaMind·HIL 精准加药-精准曝气硬件在环仿真平台

> **文档编号**：CHS-HIL-PDA-001 · Ver 1.0  
> **定位**：以实时数学模型替代物理水处理构筑物，真实控制硬件照常接入，  
> 实现"零试剂、零污水、全工况可重复"的控制算法验证环境  
> **框架**：Cybernetics of Hydro Systems（CHS）· HydroClaw · HydroOS

---

## 一、HIL 系统概念与价值

### 1.1 什么是硬件在环仿真

```
传统实验路径：
  控制算法 → [真实PLC] → [真实泵/MFC] → [真实水处理构筑物] → [真实传感器] → 反馈

HIL 仿真路径：
  控制算法 → [真实PLC] → [真实泵/MFC] ──→ [实时数字孪生模型] ──→ [虚拟传感器信号] → 反馈
                                            （替代物理构筑物）      （模拟4-20mA/RS485输出）
```

**核心思想**：砍掉造价最高的部分（水池、管路、药剂、污水处理），保留最有价值的部分（控制硬件、接口、算法）。

### 1.2 HIL vs 纯软件仿真 vs 物理实验

| 维度 | 纯软件仿真 | **HIL 仿真（本方案）** | 物理实验台 |
|------|-----------|----------------------|-----------|
| 控制硬件真实性 | 无（全仿真）| **✅ 真实 PLC/泵/MFC** | ✅ 真实 |
| 信号路径真实性 | 无 | **✅ 真实 4-20mA/RS485** | ✅ 真实 |
| 水处理过程 | 模型 | **模型（ASM1+CFD）** | 真实 |
| 极端工况测试 | 容易 | **✅ 容易且安全** | 危险/不可行 |
| 试剂消耗 | 无 | **零消耗** | 每次实验消耗 |
| 构建成本 | 极低 | **低（见三档方案）** | 高 |
| 算法验证可信度 | 低 | **高（含硬件时延/噪声）** | 最高 |
| 可重复性 | 完美 | **完美** | 受水质波动影响 |
| HydroClaw 接入 | 部分 | **✅ 全接入** | ✅ 全接入 |

### 1.3 HIL 能验证什么

- **控制算法性能**：PID/MPC/RL 在各种工况下的响应特性
- **硬件时延影响**：PLC 扫描周期、通信延迟对控制稳定性的影响
- **传感器故障场景**：注入漂移/断线/噪声，测试控制器鲁棒性
- **极端工况**：进水浊度突变、有毒冲击负荷、停电重启
- **HydroClaw 云边协同**：MPC 指令延迟、网络中断降级控制
- **安全联锁逻辑**：故障注入后 SafetyWatcher 响应是否正确

---

## 二、HIL 系统总体架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                     HIL 仿真平台总体架构                               │
│                                                                        │
│  ┌──────────────┐     真实信号      ┌──────────────────────────────┐  │
│  │  真实控制硬件  │◄──────────────►│      实时仿真计算机             │  │
│  │              │   4-20mA/RS485  │                              │  │
│  │ ·西门子S7 PLC │◄── DO信号(模拟)──│  ┌──────────────────────┐  │  │
│  │ ·蠕动泵(兰格) │◄── pH信号(模拟)──│  │   实时水处理模型        │  │  │
│  │ ·MFC(Brooks) │◄── 浊度信号     ──│  │   ASM1+混凝动力学      │  │  │
│  │ ·变频风机     │                  │  │   CFD曝气传质          │  │  │
│  │ ·触摸屏HMI   │──泵速指令────────►│  │   步长: 100ms～1s     │  │  │
│  └──────────────┘  MFC流量指令     │  └──────────────────────┘  │  │
│                                    │                              │  │
│  ┌──────────────┐                  │  ┌──────────────────────┐  │  │
│  │  信号调理板   │◄────模拟I/O──────│  │   虚拟传感器生成器     │  │  │
│  │ (DAQ接口层)  │                  │  │   含噪声/漂移/延迟    │  │  │
│  └──────────────┘                  │  └──────────────────────┘  │  │
│                                    └──────────────────────────────┘  │
│                                              │ MQTT/OPC-UA           │
│                                    ┌─────────▼───────────┐          │
│                                    │  HydroClaw 云端平台   │          │
│                                    │  MPC求解 · AI助教     │          │
│                                    └─────────────────────┘          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 三、三档 HIL 平台方案

### 方案 A：教育轻量版（AquaMind-HIL-Edu）

**定位**：本科生算法验证，纯软件+最小硬件，桌面运行

| 组件 | 选型 | 单价 | 说明 |
|------|------|------|------|
| 仿真主机 | Jetson Orin NX 16GB | ¥3,500 | 运行实时模型 |
| I/O 接口板 | Arduino Due（84MHz ARM Cortex-M3）| ¥280 | 模拟信号 I/O |
| DAQ 扩展 | ADS1256 8通道24bit ADC + DAC8552 | ¥320 | 精度2μV |
| 信号调理 | 4-20mA 收发模块 × 8 路 | ¥960 | 匹配 PLC 信号 |
| RS485 接口 | MAX3485 模块 × 4 路 | ¥120 | Modbus 仿真 |
| 微型PLC（可选）| 西门子 LOGO! 8 | ¥2,800 | 学生真实 PLC 编程 |
| 小型蠕动泵 | 兰格 BT100-1L × 2 | ¥2,400 | 真实泵特性验证 |
| 总计 | — | **约 ¥10,380** | 含 Jetson |

**软件栈**：Python 3.11 + asyncio + PREEMPT_RT（Jetson JetPack）+ Grafana + MQTT

**精度与步长**：
- 模型步长：500ms～1s（教学可接受）
- 信号延迟：< 10ms
- DO 仿真精度：±0.05 mg/L

---

### 方案 B：科研标准版（AquaMind-HIL-Research）

**定位**：研究生算法开发，工业级 PLC 全接入，支持发表论文

| 组件 | 选型 | 单价 | 说明 |
|------|------|------|------|
| 实时仿真计算机 | 研华 IPC-610 i9-12900H / 32G / NVMe | ¥18,000 | RT-Linux PREEMPT_RT |
| 多功能 DAQ 卡 | NI PCIe-6323，32AI/4AO/48DIO，250kS/s | ¥28,000 | 工业级精度 |
| 信号调理机箱 | NI SCXI-1000 + 1102C/1124 模块 | ¥12,000 | 4-20mA 完整覆盖 |
| 工业 PLC | 西门子 S7-1214C（含扩展模块全套）| ¥18,000 | 与物理版相同 PLC |
| 蠕动泵（全套）| 兰格 BT100-2J × 4 台 | ¥15,200 | 真实泵 HIL |
| MFC | Brooks SLA5850 × 2 套 | ¥24,000 | 真实 MFC HIL |
| 变频风机 | RB-033（0.4kW，变频）| ¥3,500 | 真实风机 HIL |
| 信号端子板 | NI TB-2715 + 屏蔽电缆 | ¥3,500 | 降噪接线 |
| 总计 | — | **约 ¥122,200** | 研究级 |

**软件栈**：RT-Linux + Python-RTE + NI-DAQmx Python API + Siemens TIA Portal + OPC-UA + InfluxDB + Grafana + HydroOS Agent SDK

**精度与步长**：
- 模型步长：**100ms**（工业实时控制级）
- 信号延迟：< 2ms
- 仿真时钟抖动：< 500μs（PREEMPT_RT 内核）

---

### 方案 C：全数字纯软件版（AquaMind-HIL-Digital）

**定位**：零硬件成本，完全在 PC/云端运行，适合远程教学和初步算法验证

| 组件 | 选型 | 说明 |
|------|------|------|
| 宿主机 | 任意 Windows/Linux 笔记本 | 无特殊要求 |
| 软 PLC | CODESYS SoftPLC（免费版）| 完整 IEC 61131-3 |
| 仿真核心 | Python + asyncio（本文件提供）| 浏览器或本地运行 |
| SCADA | Node-RED + Grafana | 可视化监控 |
| 通信 | OPC-UA（本地回环）/ MQTT | 软连接 |
| 总计 | **¥0 硬件成本** | 纯软件 |

**局限**：无法验证硬件时延、无法测试真实泵的非线性特性，但足以验证控制算法逻辑。

---

## 四、实时仿真核心设计

### 4.1 实时调度架构

```
HIL 实时调度器（100ms 步长，PREEMPT_RT 内核）
│
├── 高优先级任务（RT，周期 100ms）
│   ├── 读取 PLC/执行器状态（Modbus/OPC-UA）
│   ├── ASM1 ODE 步进（RK4，Δt=100ms）
│   ├── 虚拟传感器信号生成
│   └── 输出信号到 DAQ（4-20mA/RS485）
│
├── 中优先级任务（准RT，周期 1s）
│   ├── LSTM 软测量推理更新
│   ├── KLa 在线辨识
│   └── 状态量写入 InfluxDB
│
└── 低优先级任务（普通，周期 10s）
    ├── HydroClaw 云端状态同步（MQTT）
    ├── MPC 指令接收
    └── Web 仪表盘推送（WebSocket）
```

### 4.2 虚拟传感器模型

每个虚拟传感器 = 理想模型输出 + 动态响应延迟 + 传感器噪声 + 慢漂移

```python
import numpy as np
from dataclasses import dataclass, field
from collections import deque
from typing import Optional

@dataclass
class SensorConfig:
    """虚拟传感器配置"""
    name:        str
    unit:        str
    tau_s:       float = 30.0    # 一阶响应时间常数（秒）
    noise_std:   float = 0.02    # 高斯白噪声标准差（量程比例）
    drift_rate:  float = 0.001   # 慢漂移速率（单位/小时）
    dead_time_s: float = 5.0     # 纯滞后（秒）
    range_min:   float = 0.0
    range_max:   float = 20.0
    fail_mode:   str   = 'none'  # 'none' / 'stuck' / 'drift_fast' / 'noise_high'


class VirtualSensor:
    """
    高保真虚拟传感器
    精确模拟工业传感器的动态特性、噪声和故障模式
    """
    def __init__(self, cfg: SensorConfig, dt_s: float = 0.1):
        self.cfg    = cfg
        self.dt     = dt_s
        self._y     = 0.0          # 当前输出
        self._drift = 0.0          # 累计漂移量
        self._t     = 0.0          # 运行时间（秒）
        # 纯滞后缓冲区（环形队列）
        buf_len = max(1, int(cfg.dead_time_s / dt_s))
        self._buf = deque([0.0] * buf_len, maxlen=buf_len)
        # 故障标志
        self._fault_active = False

    def update(self, true_value: float) -> float:
        """
        输入：物理模型的真实状态值
        输出：模拟传感器读数（含延迟/噪声/漂移）
        """
        self._t += self.dt

        # ── 故障注入 ──────────────────────────────────────
        if self.cfg.fail_mode == 'stuck':
            return self._y   # 传感器卡死
        if self.cfg.fail_mode == 'noise_high':
            true_value += np.random.normal(0, 0.5)
        if self.cfg.fail_mode == 'drift_fast':
            self._drift += 0.01 * self.dt

        # ── 纯滞后 ────────────────────────────────────────
        self._buf.append(true_value)
        delayed_val = self._buf[0]   # 最老的值 = 滞后输出

        # ── 一阶惯性（低通滤波）────────────────────────────
        alpha = self.dt / (self.cfg.tau_s + self.dt)   # 一阶滤波系数
        self._y = alpha * delayed_val + (1 - alpha) * self._y

        # ── 高斯白噪声 ────────────────────────────────────
        noise_abs = self.cfg.noise_std * (self.cfg.range_max - self.cfg.range_min)
        noise = np.random.normal(0, noise_abs)

        # ── 慢漂移（模拟传感器老化）───────────────────────
        self._drift += self.cfg.drift_rate / 3600.0 * self.dt

        # ── 最终输出（量程饱和）──────────────────────────
        output = np.clip(
            self._y + noise + self._drift,
            self.cfg.range_min,
            self.cfg.range_max
        )
        return float(output)

    def inject_fault(self, mode: str):
        """运行时注入故障"""
        self.cfg.fail_mode = mode
        print(f"[FAULT INJECT] {self.cfg.name}: {mode}")

    def clear_fault(self):
        self.cfg.fail_mode = 'none'

    def to_mA(self, value: Optional[float] = None) -> float:
        """转换为 4-20mA 电流信号（用于 DAQ 输出）"""
        v = value if value is not None else self._y
        pct = (v - self.cfg.range_min) / (self.cfg.range_max - self.cfg.range_min)
        return 4.0 + 16.0 * np.clip(pct, 0, 1)


# 标准传感器配置库
SENSOR_CONFIGS = {
    'DO_aerobic': SensorConfig(
        name='DO_aerobic', unit='mg/L',
        tau_s=30, noise_std=0.005, drift_rate=0.002,
        dead_time_s=5, range_min=0, range_max=20
    ),
    'pH': SensorConfig(
        name='pH', unit='pH',
        tau_s=10, noise_std=0.003, drift_rate=0.001,
        dead_time_s=2, range_min=4, range_max=10
    ),
    'NTU': SensorConfig(
        name='Turbidity', unit='NTU',
        tau_s=15, noise_std=0.01, drift_rate=0.003,
        dead_time_s=8, range_min=0, range_max=200
    ),
    'NH4': SensorConfig(
        name='NH4', unit='mg/L',
        tau_s=300, noise_std=0.02, drift_rate=0.005,
        dead_time_s=300, range_min=0, range_max=100  # 分析仪响应慢
    ),
}
```

### 4.3 虚拟执行器模型

```python
@dataclass
class ActuatorConfig:
    rate_limit:   float = 5.0    # 最大变化率（单位/s）
    deadband:     float = 0.01   # 死区（防抖）
    noise_std:    float = 0.005  # 执行精度误差
    lag_tau_s:    float = 2.0    # 执行器响应时间常数
    min_val:      float = 0.0
    max_val:      float = 100.0


class VirtualActuator:
    """
    虚拟执行器
    模拟：变化率限制 / 死区 / 执行精度误差 / 一阶响应惯性
    """
    def __init__(self, cfg: ActuatorConfig, dt_s: float = 0.1):
        self.cfg = cfg
        self.dt  = dt_s
        self._actual = 0.0    # 当前实际执行值
        self._cmd    = 0.0    # 当前指令值

    def set_command(self, cmd: float):
        """接收来自 PLC/控制器的指令"""
        # 死区处理
        if abs(cmd - self._cmd) < self.cfg.deadband:
            return
        self._cmd = np.clip(cmd, self.cfg.min_val, self.cfg.max_val)

    def step(self) -> float:
        """推进一步，返回实际执行值（送入水处理模型）"""
        # 一阶惯性（执行器动态）
        alpha = self.dt / (self.cfg.lag_tau_s + self.dt)
        target = self._cmd + np.random.normal(0, self.cfg.noise_std * self._cmd)
        self._actual = alpha * target + (1 - alpha) * self._actual

        # 变化率限制
        max_delta = self.cfg.rate_limit * self.dt
        self._actual = np.clip(
            self._actual,
            self._cmd - max_delta,
            self._cmd + max_delta
        )
        return np.clip(self._actual, self.cfg.min_val, self.cfg.max_val)
```

### 4.4 HIL 主调度循环

```python
import asyncio
import time
from typing import Dict

class HILSimulator:
    """
    HIL 仿真主调度器
    集成：实时 ASM1 模型 + 虚拟传感器 + 虚拟执行器 + 硬件 I/O
    """
    def __init__(self, dt_s: float = 0.1):
        self.dt = dt_s
        # 水处理模型
        self.model = ASM1DigitalTwin(ASM1Params(), V=300.0)
        # 虚拟传感器（使用前面定义的 VirtualSensor）
        self.sensors: Dict[str, VirtualSensor] = {
            k: VirtualSensor(v, dt_s) for k, v in SENSOR_CONFIGS.items()
        }
        # 虚拟执行器
        self.actuators = {
            'Q_air': VirtualActuator(ActuatorConfig(
                rate_limit=2.0, lag_tau_s=3.0, max_val=20.0), dt_s),
            'D_PAC': VirtualActuator(ActuatorConfig(
                rate_limit=1.0, lag_tau_s=2.0, max_val=15.0), dt_s),
            'D_NaOH': VirtualActuator(ActuatorConfig(
                rate_limit=0.5, lag_tau_s=2.0, max_val=5.0), dt_s),
        }
        # 硬件接口（按实际选型初始化）
        self.hw_io = None   # 替换为 NI-DAQmx 或 Arduino Serial
        # 数据记录
        self.data_log = []
        self._running = False
        self._step_count = 0

    async def run(self):
        """异步实时主循环"""
        self._running = True
        t_next = time.monotonic()

        while self._running:
            t_start = time.monotonic()

            # ── 1. 读取执行器实际输出 ──────────────────────
            Q_air  = self.actuators['Q_air'].step()
            D_PAC  = self.actuators['D_PAC'].step()
            D_NaOH = self.actuators['D_NaOH'].step()

            # ── 2. 进水扰动生成（支持多场景脚本）──────────
            disturbance = self._get_disturbance(self._step_count)

            # ── 3. ASM1 模型步进 ──────────────────────────
            KLa_val = self.model.kla_id.predict_KLa(Q_air) if hasattr(
                self.model, 'kla_id') else 5.0 + Q_air * 0.3
            inputs = {
                'Q_in':    disturbance['Q_in'],
                'S_s_in':  disturbance['S_s_in'],
                'S_NH_in': disturbance['S_NH_in'],
                'X_in':    disturbance.get('X_in', 200.0),
                'DO_in':   0.5,
                'DO_sat':  VirtualSensor.do_sat(disturbance.get('T', 22.0)),
                'KLa':     KLa_val,
                'T':       disturbance.get('T', 22.0),
            }
            self.model.predict(inputs, dt_h=self.dt / 3600.0)

            # ── 4. 虚拟传感器更新（从模型状态生成信号）──────
            state = self.model.state
            sensor_readings = {
                'DO':   self.sensors['DO_aerobic'].update(state[4]),
                'pH':   self.sensors['pH'].update(7.0 + 0.3 * (state[1] / 20.0)),
                'NTU':  self.sensors['NTU'].update(
                            0.1 * state[0] + 0.001 * state[5]),
                'NH4':  self.sensors['NH4'].update(state[1]),
                'T':    disturbance.get('T', 22.0),
            }

            # ── 5. 输出信号到硬件 I/O ──────────────────────
            if self.hw_io:
                self._output_to_hardware(sensor_readings)

            # ── 6. 读取 PLC 控制指令 ──────────────────────
            if self.hw_io:
                cmds = self._read_from_hardware()
                for k, v in cmds.items():
                    if k in self.actuators:
                        self.actuators[k].set_command(v)

            # ── 7. 数据记录 ───────────────────────────────
            self._log(sensor_readings, Q_air, D_PAC, D_NaOH)
            self._step_count += 1

            # ── 8. 精确定时（保证 dt 周期）────────────────
            t_next += self.dt
            sleep_time = t_next - time.monotonic()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                # 超时警告（HIL 实时性监控）
                overrun_ms = -sleep_time * 1000
                if overrun_ms > 10:
                    print(f"[TIMING WARN] 步骤超时 {overrun_ms:.1f}ms")
                t_next = time.monotonic()

    def _get_disturbance(self, step: int) -> dict:
        """
        进水扰动场景脚本
        支持：稳定工况 / 阶跃变化 / 正弦波动 / 故障注入
        """
        t_h = step * self.dt / 3600.0
        base = {'Q_in': 25.0, 'S_s_in': 150.0, 'S_NH_in': 30.0, 'T': 22.0}

        # 示例：第 2h 时进水浊度突变（压力测试场景）
        if t_h > 2.0:
            base['S_s_in'] = 250.0  # 模拟高浓度冲击
        # 示例：正弦日变化（模拟真实进水规律）
        base['S_NH_in'] = 30.0 + 10.0 * np.sin(2 * np.pi * t_h / 24.0)
        return base

    def _log(self, sensors, Q_air, D_PAC, D_NaOH):
        """写入时序数据（内存缓冲 + 定期刷写 InfluxDB）"""
        record = {
            'time': self._step_count * self.dt,
            **sensors,
            'Q_air': Q_air,
            'D_PAC': D_PAC,
            'D_NaOH': D_NaOH,
            'COD_model': self.model.COD_eff,
            'NH4_model': self.model.NH4_eff,
        }
        self.data_log.append(record)
        if len(self.data_log) % 600 == 0:  # 每 60s 刷写一次
            self._flush_to_influxdb()

    def _flush_to_influxdb(self):
        """批量写入 InfluxDB（异步，不阻塞 RT 循环）"""
        pass  # 实现：influxdb_client.write_api().write(...)

    def inject_fault(self, sensor_name: str, fault_mode: str):
        """对外接口：注入传感器故障"""
        if sensor_name in self.sensors:
            self.sensors[sensor_name].inject_fault(fault_mode)

    def set_scenario(self, scenario_name: str):
        """切换仿真场景（稳定/冲击/高氨氮/低温/设备故障等）"""
        scenarios = {
            'steady':     {'Q_in': 25, 'S_s_in': 150, 'S_NH_in': 30, 'T': 22},
            'shock_load': {'Q_in': 40, 'S_s_in': 400, 'S_NH_in': 80, 'T': 22},
            'winter':     {'Q_in': 20, 'S_s_in': 100, 'S_NH_in': 25, 'T': 8},
            'summer':     {'Q_in': 35, 'S_s_in': 200, 'S_NH_in': 40, 'T': 30},
        }
        print(f"[SCENARIO] 切换至 {scenario_name}: {scenarios.get(scenario_name, {})}")
```

---

## 五、硬件 I/O 接口层

### 5.1 信号对照表

| 物理信号方向 | 信号类型 | 范围 | 对应量 | HIL 接口 |
|------------|---------|------|--------|---------|
| 仿真机 → PLC（传感器） | 4-20mA 输出 | 4~20mA | DO（0~20mg/L）| DAQ AO 通道 |
| 仿真机 → PLC（传感器） | 4-20mA 输出 | 4~20mA | pH（4~10）| DAQ AO 通道 |
| 仿真机 → PLC（传感器） | 4-20mA 输出 | 4~20mA | 浊度（0~200NTU）| DAQ AO 通道 |
| 仿真机 → PLC（传感器） | RS485 Modbus | — | NH4+/COD 分析仪 | USB-RS485 + 软件从站 |
| 仿真机 → PLC（传感器） | 4-20mA 输出 | 4~20mA | 流量（0~100L/h）| DAQ AO 通道 |
| PLC → 仿真机（执行器）| 4-20mA 输入 | 4~20mA | 泵速指令 | DAQ AI 通道 |
| PLC → 仿真机（执行器）| 4-20mA 输入 | 4~20mA | MFC 设定值 | DAQ AI 通道 |
| PLC → 仿真机（执行器）| 数字输出 | 24VDC | 阀门开关 | DIO 通道 |
| PLC → 仿真机（执行器）| RS485 Modbus | — | 变频风机频率 | USB-RS485 主站 |

### 5.2 NI DAQ 接口代码（方案 B）

```python
import nidaqmx
from nidaqmx.constants import AcquisitionType, TerminalConfiguration

class NIDAQInterface:
    """
    NI PCIe-6323 硬件 I/O 接口
    实现：4-20mA 传感器信号输出 + PLC 控制指令读取
    """
    SENSOR_OUT_CHANNELS = {
        'DO':    'Dev1/ao0',   # 0~10V → 4~20mA（外部 V/I 转换）
        'pH':    'Dev1/ao1',
        'NTU':   'Dev1/ao2',
        'Flow':  'Dev1/ao3',
    }
    ACTUATOR_IN_CHANNELS = {
        'pump_PAC':  'Dev1/ai0',
        'pump_PAM':  'Dev1/ai1',
        'MFC_air':   'Dev1/ai2',
        'blower_Hz': 'Dev1/ai3',
    }

    def __init__(self):
        self._ao_task = None
        self._ai_task = None
        self._init_tasks()

    def _init_tasks(self):
        # 模拟输出任务（传感器仿真输出）
        self._ao_task = nidaqmx.Task()
        for ch in self.SENSOR_OUT_CHANNELS.values():
            self._ao_task.ao_channels.add_ao_voltage_chan(ch, min_val=0, max_val=10)

        # 模拟输入任务（读取 PLC 输出的控制指令）
        self._ai_task = nidaqmx.Task()
        for ch in self.ACTUATOR_IN_CHANNELS.values():
            self._ai_task.ai_channels.add_ai_voltage_chan(
                ch, terminal_config=TerminalConfiguration.RSE,
                min_val=0, max_val=10
            )

    def write_sensors(self, sensor_values: dict):
        """将虚拟传感器读数写入模拟输出（4-20mA 对应 1-5V，含 250Ω 电阻）"""
        voltages = []
        for name in self.SENSOR_OUT_CHANNELS:
            mA_val = sensor_values.get(name + '_mA', 12.0)  # 默认中间值
            V_out  = (mA_val - 4.0) / 16.0 * 4.0 + 1.0    # 4~20mA → 1~5V
            voltages.append(V_out)
        self._ao_task.write(voltages)

    def read_actuators(self) -> dict:
        """读取 PLC 控制指令（0~10V 对应 0~100% 量程）"""
        voltages = self._ai_task.read()
        return {
            name: v / 10.0  # 归一化
            for name, v in zip(self.ACTUATOR_IN_CHANNELS.keys(), voltages)
        }

    def close(self):
        if self._ao_task:  self._ao_task.close()
        if self._ai_task:  self._ai_task.close()
```

### 5.3 Arduino 接口代码（方案 A 教育版）

```python
import serial
import struct

class ArduinoHILInterface:
    """
    Arduino Due HIL 接口（教育版，低成本）
    协议：自定义二进制帧，16 字节
    帧格式：[0xAA] [CMD] [16×float32] [CRC8] [0x55]
    """
    def __init__(self, port: str = '/dev/ttyACM0', baud: int = 115200):
        self.ser = serial.Serial(port, baud, timeout=0.05)

    def write_sensors(self, readings: dict):
        """将传感器读数发送给 Arduino → 转 4-20mA 输出"""
        values = [
            readings.get('DO',  2.0),
            readings.get('pH',  7.2),
            readings.get('NTU', 5.0),
            readings.get('NH4', 15.0),
            readings.get('Flow', 25.0),
            readings.get('T',   22.0),
        ]
        frame = bytes([0xAA, 0x01])  # Header + CMD_WRITE_SENSORS
        frame += struct.pack('<6f', *values)
        frame += bytes([self._crc8(frame), 0x55])
        self.ser.write(frame)

    def read_actuators(self) -> dict:
        """从 Arduino 读取 PLC 发来的控制指令（ADC 读取4-20mA）"""
        self.ser.write(bytes([0xAA, 0x02, 0x55]))  # CMD_READ_ACTUATORS
        resp = self.ser.read(32)
        if len(resp) == 32 and resp[0] == 0xAA:
            values = struct.unpack('<6f', resp[2:26])
            return {
                'Q_air':   values[0],  # L/min
                'D_PAC':   values[1],  # mL/min
                'D_NaOH':  values[2],
                'D_PAM':   values[3],
                'blower_Hz': values[4],
            }
        return {}

    @staticmethod
    def _crc8(data: bytes) -> int:
        crc = 0
        for b in data:
            crc ^= b
            for _ in range(8):
                crc = (crc << 1) ^ 0x07 if crc & 0x80 else crc << 1
        return crc & 0xFF
```

---

## 六、仿真场景脚本库

### 6.1 标准测试场景

```yaml
# hil_scenarios.yaml —— 标准测试场景库
scenarios:

  steady_state:
    name: "稳态标准工况"
    description: "验证控制器稳态精度和能耗基线"
    duration_h: 8
    disturbance:
      Q_in_L_h:    25.0
      S_s_in_mg_L: 150.0
      S_NH_in_mg_L: 30.0
      T_C:          22.0
    expected_performance:
      DO_rmse: < 0.15 mg/L
      NH4_eff: < 5 mg/L
      energy_saving: > 15%

  step_turbidity:
    name: "进水浊度阶跃（混凝测试）"
    description: "测试前馈-PID 复合加药控制器动态响应"
    duration_h: 4
    events:
      - t_h: 0.5
        action: set_disturbance
        params: {S_s_in: 300.0}    # 浊度阶跃 × 2
      - t_h: 2.0
        action: set_disturbance
        params: {S_s_in: 80.0}     # 回落至低浊度
      - t_h: 3.0
        action: set_disturbance
        params: {S_s_in: 200.0}    # 再次阶跃
    expected_performance:
      settling_time_min: < 5
      overshoot_NTU:     < 10% above target

  ammonia_shock:
    name: "氨氮冲击（硝化测试）"
    description: "测试外环 DO 设定点动态调节能力"
    duration_h: 6
    events:
      - t_h: 1.0
        action: set_disturbance
        params: {S_NH_in: 80.0}    # 氨氮冲击 × 2.7
      - t_h: 4.0
        action: set_disturbance
        params: {S_NH_in: 20.0}    # 恢复正常
    expected_performance:
      NH4_effluent: < 8 mg/L during shock
      DO_sp_response: increase within 3 min

  sensor_failure:
    name: "DO 传感器故障注入"
    description: "测试 SafetyWatcher 故障检测和降级控制"
    duration_h: 3
    events:
      - t_h: 0.5
        action: inject_fault
        params: {sensor: DO_aerobic, mode: stuck}
      - t_h: 1.5
        action: clear_fault
        params: {sensor: DO_aerobic}
      - t_h: 2.0
        action: inject_fault
        params: {sensor: DO_aerobic, mode: drift_fast}
    expected_performance:
      fault_detection_time_s: < 120
      graceful_degradation: true    # 切换到开环控制

  winter_cold:
    name: "低温冬季工况"
    description: "低温下微生物活性下降，测试温度补偿算法"
    duration_h: 8
    disturbance:
      T_C: 8.0
      S_NH_in_mg_L: 30.0
      Q_in_L_h: 20.0
    expected_performance:
      NH4_eff: < 8 mg/L (宽松标准，冬季一级B)
      DO_sp_increase: > 0.5 mg/L vs summer

  mpc_vs_pid:
    name: "MPC vs PID 对比实验"
    description: "在相同扰动下对比两种控制策略的能耗和水质"
    duration_h: 12
    phases:
      - duration_h: 6
        controller: PID
        record_as: baseline
      - duration_h: 6
        controller: MPC
        compare_to: baseline
    metrics_to_compare:
      - total_energy_kWh
      - effluent_NH4_mean
      - effluent_COD_mean
      - DO_rmse
      - PAC_consumed_mL
```

### 6.2 故障注入矩阵

| 故障类型 | 触发方式 | 期望检测时间 | 期望降级行为 |
|---------|---------|------------|------------|
| DO 传感器卡死 | `inject_fault(DO, stuck)` | < 120s | 切换开环曝气（固定气量） |
| DO 传感器快速漂移 | `inject_fault(DO, drift_fast)` | < 300s | 发出 WARNING，重新标定 |
| 蠕动泵断线 | `inject_fault(PAC_pump, offline)` | < 30s | 停止混凝工段，发 ALARM |
| MFC 通信中断 | `inject_fault(MFC, timeout)` | < 60s | 风机固定频率（安全模式） |
| PLC 与仿真机通信断开 | 拔以太网线 | < 10s | 仿真机本地 PID 接管 |
| 云端 HydroClaw 断网 | 模拟网络断开 | < 30s | 边缘 MPC 本地接管 |
| 药剂桶液位低 | `inject_fault(PAC_tank, low_level)` | 立即 | WARNING + 减小投量 |

---

## 七、软件安装与部署

### 7.1 方案 A 教育版安装脚本

```bash
#!/bin/bash
# AquaMind-HIL 教育版安装脚本
# 运行于 Jetson Orin NX (JetPack 6, Ubuntu 22.04)

echo "=== AquaMind-HIL 安装开始 ==="

# 1. 系统依赖
sudo apt-get update && sudo apt-get install -y \
    python3.11 python3.11-venv python3-pip \
    git influxdb2 grafana \
    libserial-dev libmodbus-dev

# 2. Python 环境
python3.11 -m venv /opt/aquamind-hil
source /opt/aquamind-hil/bin/activate

# 3. Python 依赖
pip install --upgrade pip
pip install \
    numpy scipy pandas matplotlib \
    asyncio aiofiles \
    influxdb-client \
    pyserial pymodbus \
    paho-mqtt \
    fastapi uvicorn websockets \
    do-mpc casadi \
    torch torchvision torchaudio \
    xgboost scikit-learn

# 4. 创建目录结构
mkdir -p /opt/aquamind-hil/{config,models,logs,scenarios}

# 5. 系统服务（开机自启）
cat > /etc/systemd/system/aquamind-hil.service << 'EOF'
[Unit]
Description=AquaMind HIL Simulator
After=network.target

[Service]
Type=simple
User=aquamind
WorkingDirectory=/opt/aquamind-hil
ExecStart=/opt/aquamind-hil/bin/python -m aquamind_hil.main
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable aquamind-hil

# 6. 配置 InfluxDB（数据库初始化）
influx setup \
    --org aquamind \
    --bucket hil_data \
    --username admin \
    --password aquamind2026 \
    --force

# 7. Grafana 仪表盘导入
curl -X POST \
    -H "Content-Type: application/json" \
    -d @/opt/aquamind-hil/config/grafana_dashboard.json \
    http://localhost:3000/api/dashboards/db

echo "=== 安装完成！访问 http://localhost:3000 查看仪表盘 ==="
```

### 7.2 Docker Compose 部署（纯软件版）

```yaml
# docker-compose.yml — AquaMind-HIL 纯软件版
version: '3.9'

services:
  # HIL 仿真核心
  hil-simulator:
    image: aquamind/hil-simulator:1.0
    container_name: aquamind-hil
    restart: unless-stopped
    ports:
      - "8080:8080"    # REST API
      - "8765:8765"    # WebSocket（实时数据推送）
    environment:
      - HIL_DT_MS=100          # 仿真步长 100ms
      - HIL_MODE=software      # software / edge / research
      - INFLUXDB_URL=http://influxdb:8086
      - MQTT_BROKER=mqtt
      - HYDROCLAW_API_KEY=${HYDROCLAW_API_KEY}
    volumes:
      - ./config:/app/config
      - ./scenarios:/app/scenarios
      - ./models:/app/models

  # 时序数据库
  influxdb:
    image: influxdb:2.7
    container_name: aquamind-influxdb
    ports:
      - "8086:8086"
    volumes:
      - influxdb_data:/var/lib/influxdb2
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_ORG=aquamind
      - DOCKER_INFLUXDB_INIT_BUCKET=hil_data
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=aquamind-token-2026

  # 可视化
  grafana:
    image: grafana/grafana:10.2
    container_name: aquamind-grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/grafana_provisioning:/etc/grafana/provisioning

  # MQTT Broker
  mqtt:
    image: eclipse-mosquitto:2
    container_name: aquamind-mqtt
    ports:
      - "1883:1883"
      - "9001:9001"

  # 软 PLC（CODESYS 运行时，纯软件版）
  soft-plc:
    image: codesys/runtime:4.0
    container_name: aquamind-plc
    network_mode: host
    volumes:
      - ./plc_programs:/plc

  # Node-RED 流程编排
  node-red:
    image: nodered/node-red:3.1
    container_name: aquamind-nodered
    ports:
      - "1880:1880"
    volumes:
      - ./node-red:/data

volumes:
  influxdb_data:
  grafana_data:
```

---

## 八、HIL 平台与 HydroClaw 集成

### 8.1 集成架构

HIL 平台作为 HydroClaw 生态中的一类特殊节点：**仿真验证节点（Simulation Validation Node）**

```
HydroClaw 云端
    ├── 接收 HIL 仿真数据（与真实工程数据区分标记）
    ├── 向 HIL 下发 MPC 优化指令（测试云边协同延迟）
    ├── 使用 HIL 数据训练/验证 AI 模型
    └── 允许学生模型在 HIL 上跑通后再提交至知识库

HIL 平台 MQTT 数据包格式：
{
  "node_id":     "HIL-AM-003",
  "node_type":   "simulation",         ← 区分真实节点
  "scenario":    "ammonia_shock",
  "sim_time_h":  2.5,                  ← 仿真内部时间
  "real_time":   "2026-03-10T14:23:00Z",
  "state": {
    "DO":   2.31,  "pH": 7.18,  "NTU": 3.2,
    "NH4":  28.5,  "COD_model": 89.3,  "MLSS": 3200
  },
  "controls": {
    "Q_air": 8.5,  "D_PAC": 2.3,  "D_NaOH": 0.8
  },
  "performance": {
    "energy_kWh":   0.42,
    "PAC_mL":       138,
    "effluent_ok":  true
  }
}
```

### 8.2 HIL 驱动的模型训练流水线

```
HIL 快速生成数据 → 训练软测量模型 → 部署到真实平台
      ↓                    ↓                  ↓
  24h 仿真生成          LSTM/XGBoost      提交 HydroClaw
  5000+ 数据点          5min 训练         知识库排行
```

**效率提升**：真实实验积累 100 组化验数据需要 2-3 个月，HIL 仿真 2 小时即可生成 10,000 组带标签数据（含模型真值），大幅加速模型训练。

---

## 九、三档方案成本汇总

| 指标 | 方案 A（教育轻量版）| 方案 B（科研标准版）| 方案 C（纯软件版）|
|------|-----------------|-----------------|----------------|
| 硬件成本 | **¥10,380** | **¥122,200** | **¥0** |
| 仿真步长 | 500ms～1s | **100ms** | 500ms～1s |
| 真实 PLC 接入 | 可选（¥2,800）| ✅ 全套 | 软 PLC 替代 |
| 真实泵/MFC 接入 | 2 台蠕动泵 | ✅ 全套（泵+MFC+风机）| ❌ 无 |
| 信号精度 | ±0.5%（24bit ADC）| **±0.05%（NI DAQ）** | 数值精度 |
| 适用阶段 | Year 2~4 算法验证 | 研究生/论文实验 | Year 1~2 入门 |
| HydroClaw 全接入 | ✅ | ✅ | ✅ |
| 对比物理实验台造价 | 工业版的 **1/62** | 工业版的 **1/5** | 工业版的 **0** |

**推荐组合**：
- **1 套方案 B**（科研标准版）+ **6 套方案 A**（教育版）  
  总预算 ≈ **¥18.5 万**，同时覆盖研究生科研验证和本科生教学实验  
  vs. 纯物理实验台：**¥75 万以上**，节省约 **75%**

---

*文档版本：V1.0 · 2026*  
*CHS-HIL-PDA-001 · AquaMind HIL · Cybernetics of Hydro Systems*
