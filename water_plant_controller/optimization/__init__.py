"""PID参数自动调优和优化模块。"""

from .pid_tuner import (
    PIDTuner,
    PIDParameters,
    TuningResult,
    TuningObjective,
    TuningConstraints,
)

from .genetic_algorithm import (
    GeneticAlgorithmTuner,
    GeneticAlgorithmConfig,
)

from .particle_swarm import (
    ParticleSwarmTuner,
    ParticleSwarmConfig,
)

from .ziegler_nichols import (
    ZieglerNicholsTuner,
    ZNMethod,
)

from .auto_tuner import (
    AutoTuner,
    TuningMethod,
    tune_pid,
)

__all__ = [
    # 基础类
    'PIDTuner',
    'PIDParameters',
    'TuningResult',
    'TuningObjective',
    'TuningConstraints',

    # 遗传算法
    'GeneticAlgorithmTuner',
    'GeneticAlgorithmConfig',

    # 粒子群优化
    'ParticleSwarmTuner',
    'ParticleSwarmConfig',

    # Ziegler-Nichols
    'ZieglerNicholsTuner',
    'ZNMethod',

    # 自动调优接口
    'AutoTuner',
    'TuningMethod',
    'tune_pid',
]
