# 智能水厂控制系统开发者指南

## 目录

1. [项目概述](#项目概述)
2. [开发环境搭建](#开发环境搭建)
3. [项目结构](#项目结构)
4. [核心组件](#核心组件)
5. [API 接口](#api-接口)
6. [数据模型](#数据模型)
7. [开发规范](#开发规范)
8. [测试指南](#测试指南)
9. [部署指南](#部署指南)
10. [贡献指南](#贡献指南)

## 项目概述

智能水厂控制系统是一个基于 Python 的工业控制系统，用于模拟和控制水处理厂的运行。系统采用模块化设计，支持多种控制算法，提供实时监控和数据分析功能。

### 主要特性

- **模拟仿真**：高精度的水厂工艺过程模拟
- **控制算法**：支持 PID、开关控制等多种算法
- **实时监控**：Web 界面和 API 接口
- **数据分析**：历史数据分析和趋势预测
- **可扩展性**：模块化设计，易于扩展

### 技术栈

- **后端**：Python 3.8+, Flask, SQLAlchemy
- **数据库**：PostgreSQL, Redis
- **前端**：HTML5, CSS3, JavaScript, Chart.js
- **容器化**：Docker, Docker Compose
- **监控**：Prometheus, Grafana
- **测试**：pytest, unittest

## 开发环境搭建

### 系统要求

- Python 3.8 或更高版本
- Git
- Docker 和 Docker Compose（可选）
- PostgreSQL 13+（本地开发）
- Redis 6.0+（本地开发）

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/your-org/SmartWaterFactory.git
   cd SmartWaterFactory
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境**
   ```bash
   # 复制配置文件
   cp config/development.json.example config/development.json
   
   # 编辑配置文件
   vim config/development.json
   ```

5. **初始化数据库**
   ```bash
   # 启动 PostgreSQL 和 Redis（使用 Docker）
   docker-compose up -d postgres redis
   
   # 或者使用本地安装的数据库
   # 创建数据库
   createdb waterplant
   ```

6. **运行应用**
   ```bash
   python run_simulation.py --api-server
   ```

### IDE 配置

#### VS Code 配置

创建 `.vscode/settings.json`：

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

#### PyCharm 配置

1. 设置 Python 解释器为虚拟环境
2. 配置代码格式化工具为 Black
3. 启用 pytest 作为测试运行器
4. 配置代码检查工具

## 项目结构

```
SmartWaterFactory/
├── water_plant_controller/          # 核心控制器模块
│   ├── __init__.py
│   ├── control/                     # 控制算法
│   │   ├── __init__.py
│   │   ├── pid_controller.py        # PID 控制器
│   │   └── on_off_controller.py     # 开关控制器
│   ├── models/                      # 数据模型
│   │   ├── __init__.py
│   │   └── water_quality.py         # 水质数据模型
│   └── simulation/                  # 仿真模块
│       ├── __init__.py
│       └── plant_simulator.py       # 水厂仿真器
├── utils/                           # 工具模块
│   ├── api_server.py               # API 服务器
│   ├── logging_system.py           # 日志系统
│   ├── performance.py              # 性能监控
│   ├── optimization.py             # 优化工具
│   └── visualization.py            # 可视化工具
├── config/                          # 配置文件
│   ├── development.json            # 开发环境配置
│   ├── production.json             # 生产环境配置
│   ├── testing.json                # 测试环境配置
│   ├── environments.py             # 环境管理
│   ├── settings.py                 # 设置管理
│   └── validator.py                # 配置验证
├── tests/                           # 测试文件
│   ├── test_*.py                   # 各模块测试
│   └── __init__.py
├── examples/                        # 示例代码
│   ├── 01_basic_simulation/        # 基础仿真示例
│   ├── 02_tuning_pid_controller/   # PID 调优示例
│   └── ...
├── docs/                           # 文档
│   ├── api.md                      # API 文档
│   ├── deployment_guide.md         # 部署指南
│   └── developer_guide.md          # 开发者指南
├── scripts/                        # 运维脚本
│   ├── deploy.sh                   # 部署脚本
│   ├── backup.py                   # 备份脚本
│   └── monitor.py                  # 监控脚本
├── k8s/                            # Kubernetes 配置
├── deploy/                         # 部署配置
├── logs/                           # 日志文件
├── data/                           # 数据文件
├── requirements.txt                # Python 依赖
├── docker-compose.yml              # Docker Compose 配置
├── Dockerfile                      # Docker 镜像配置
└── run_simulation.py               # 主程序入口
```

## 核心组件

### 1. 水厂仿真器 (PlantSimulator)

水厂仿真器是系统的核心组件，负责模拟水处理过程。

```python
from water_plant_controller.simulation.plant_simulator import PlantSimulator
from water_plant_controller.models.water_quality import WaterQuality

# 创建仿真器实例
simulator = PlantSimulator()

# 设置初始水质参数
initial_quality = WaterQuality(
    ph=7.0,
    turbidity=10.0,
    dissolved_oxygen=8.0,
    temperature=20.0
)

# 运行仿真步骤
result = simulator.step(
    pump_speed=50.0,
    valve_position=0.7,
    current_quality=initial_quality
)

print(f"新的水质参数: {result}")
```

### 2. PID 控制器

PID 控制器用于自动调节系统参数以达到目标值。

```python
from water_plant_controller.control.pid_controller import PIDController

# 创建 PID 控制器
pid = PIDController(
    kp=1.0,    # 比例增益
    ki=0.1,    # 积分增益
    kd=0.05,   # 微分增益
    setpoint=7.0  # 目标值（pH）
)

# 计算控制输出
current_ph = 6.5
control_output = pid.compute(current_ph)

print(f"控制输出: {control_output}")
```

### 3. 水质数据模型

水质数据模型定义了水质参数的结构。

```python
from water_plant_controller.models.water_quality import WaterQuality
from datetime import datetime

# 创建水质数据实例
water_quality = WaterQuality(
    ph=7.2,
    turbidity=5.0,
    dissolved_oxygen=9.5,
    temperature=22.0,
    timestamp=datetime.now()
)

# 验证数据
if water_quality.is_valid():
    print("水质数据有效")
else:
    print("水质数据无效")

# 转换为字典
data_dict = water_quality.to_dict()
print(data_dict)
```

### 4. API 服务器

API 服务器提供 RESTful 接口和 WebSocket 支持。

```python
from utils.api_server import APIServer

# 创建 API 服务器
api_server = APIServer(
    host='0.0.0.0',
    port=5000,
    debug=True
)

# 启动服务器
api_server.run()
```

## API 接口

### 基础接口

#### 健康检查

```http
GET /health
```

响应：
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "version": "1.0.0",
    "uptime": 3600
}
```

#### 系统状态

```http
GET /api/status
```

响应：
```json
{
    "simulation_running": true,
    "control_mode": "automatic",
    "current_time": "2024-01-01T12:00:00Z",
    "system_load": 0.65
}
```

### 水质监控接口

#### 获取当前水质

```http
GET /api/water-quality/current
```

响应：
```json
{
    "ph": 7.2,
    "turbidity": 5.0,
    "dissolved_oxygen": 9.5,
    "temperature": 22.0,
    "timestamp": "2024-01-01T12:00:00Z"
}
```

#### 获取历史水质数据

```http
GET /api/water-quality/history?start=2024-01-01&end=2024-01-02&limit=100
```

响应：
```json
{
    "data": [
        {
            "ph": 7.2,
            "turbidity": 5.0,
            "dissolved_oxygen": 9.5,
            "temperature": 22.0,
            "timestamp": "2024-01-01T12:00:00Z"
        }
    ],
    "total": 100,
    "page": 1,
    "per_page": 100
}
```

### 控制接口

#### 获取控制器状态

```http
GET /api/control/status
```

响应：
```json
{
    "mode": "automatic",
    "controller_type": "pid",
    "setpoint": 7.0,
    "current_value": 7.2,
    "output": 45.5,
    "parameters": {
        "kp": 1.0,
        "ki": 0.1,
        "kd": 0.05
    }
}
```

#### 更新控制参数

```http
PUT /api/control/parameters
Content-Type: application/json

{
    "kp": 1.2,
    "ki": 0.15,
    "kd": 0.08,
    "setpoint": 7.5
}
```

响应：
```json
{
    "success": true,
    "message": "控制参数已更新",
    "parameters": {
        "kp": 1.2,
        "ki": 0.15,
        "kd": 0.08,
        "setpoint": 7.5
    }
}
```

### WebSocket 接口

#### 实时数据推送

```javascript
// 连接 WebSocket
const ws = new WebSocket('ws://localhost:5000/ws');

// 监听消息
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('实时数据:', data);
};

// 发送命令
ws.send(JSON.stringify({
    'type': 'control_command',
    'action': 'set_pump_speed',
    'value': 60.0
}));
```

## 数据模型

### 水质数据模型

```python
@dataclass
class WaterQuality:
    """水质数据模型"""
    ph: float                    # pH 值 (6.0-9.0)
    turbidity: float            # 浊度 NTU (0-100)
    dissolved_oxygen: float     # 溶解氧 mg/L (0-20)
    temperature: float          # 温度 °C (0-50)
    timestamp: datetime = None  # 时间戳
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def is_valid(self) -> bool:
        """验证数据有效性"""
        return (
            6.0 <= self.ph <= 9.0 and
            0 <= self.turbidity <= 100 and
            0 <= self.dissolved_oxygen <= 20 and
            0 <= self.temperature <= 50
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'ph': self.ph,
            'turbidity': self.turbidity,
            'dissolved_oxygen': self.dissolved_oxygen,
            'temperature': self.temperature,
            'timestamp': self.timestamp.isoformat()
        }
```

### 控制器状态模型

```python
@dataclass
class ControllerState:
    """控制器状态模型"""
    mode: str                   # 控制模式: 'manual', 'automatic'
    controller_type: str        # 控制器类型: 'pid', 'on_off'
    setpoint: float            # 设定值
    current_value: float       # 当前值
    output: float              # 控制输出
    error: float               # 误差
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.error is None:
            self.error = self.setpoint - self.current_value
```

## 开发规范

### 代码风格

项目使用 [Black](https://black.readthedocs.io/) 进行代码格式化，[flake8](https://flake8.pycqa.org/) 进行代码检查。

```bash
# 格式化代码
black .

# 检查代码风格
flake8 .

# 类型检查
mypy water_plant_controller/
```

### 命名规范

- **文件名**：使用小写字母和下划线，如 `water_quality.py`
- **类名**：使用 PascalCase，如 `WaterQuality`
- **函数名**：使用 snake_case，如 `get_current_quality`
- **常量**：使用大写字母和下划线，如 `MAX_PH_VALUE`
- **变量名**：使用 snake_case，如 `current_ph`

### 文档字符串

使用 Google 风格的文档字符串：

```python
def calculate_control_output(self, current_value: float) -> float:
    """计算控制输出。
    
    Args:
        current_value: 当前测量值
        
    Returns:
        控制输出值
        
    Raises:
        ValueError: 当输入值超出有效范围时
        
    Example:
        >>> controller = PIDController(1.0, 0.1, 0.05, 7.0)
        >>> output = controller.calculate_control_output(6.5)
        >>> print(output)
        0.5
    """
    pass
```

### 类型注解

所有公共函数和方法都应该包含类型注解：

```python
from typing import List, Dict, Optional, Union

def process_water_quality_data(
    data: List[WaterQuality],
    filter_invalid: bool = True
) -> Dict[str, Union[float, int]]:
    """处理水质数据。"""
    pass
```

### 错误处理

使用适当的异常类型和错误消息：

```python
class WaterQualityError(Exception):
    """水质相关错误。"""
    pass

class ControllerError(Exception):
    """控制器相关错误。"""
    pass

def validate_ph_value(ph: float) -> None:
    """验证 pH 值。"""
    if not 0 <= ph <= 14:
        raise WaterQualityError(f"pH 值 {ph} 超出有效范围 [0, 14]")
```

## 测试指南

### 测试结构

```
tests/
├── __init__.py
├── test_water_quality.py        # 水质模型测试
├── test_pid_controller.py       # PID 控制器测试
├── test_plant_simulator.py      # 仿真器测试
├── test_api_server.py          # API 服务器测试
├── test_integration.py         # 集成测试
└── conftest.py                 # pytest 配置
```

### 单元测试示例

```python
import pytest
from water_plant_controller.models.water_quality import WaterQuality
from datetime import datetime

class TestWaterQuality:
    """水质模型测试。"""
    
    def test_valid_water_quality(self):
        """测试有效的水质数据。"""
        wq = WaterQuality(
            ph=7.0,
            turbidity=5.0,
            dissolved_oxygen=8.0,
            temperature=20.0
        )
        assert wq.is_valid()
    
    def test_invalid_ph(self):
        """测试无效的 pH 值。"""
        wq = WaterQuality(
            ph=15.0,  # 超出范围
            turbidity=5.0,
            dissolved_oxygen=8.0,
            temperature=20.0
        )
        assert not wq.is_valid()
    
    def test_to_dict(self):
        """测试转换为字典。"""
        timestamp = datetime.now()
        wq = WaterQuality(
            ph=7.0,
            turbidity=5.0,
            dissolved_oxygen=8.0,
            temperature=20.0,
            timestamp=timestamp
        )
        
        data = wq.to_dict()
        assert data['ph'] == 7.0
        assert data['timestamp'] == timestamp.isoformat()
```

### 集成测试示例

```python
import pytest
from utils.api_server import APIServer
from water_plant_controller.simulation.plant_simulator import PlantSimulator

class TestIntegration:
    """集成测试。"""
    
    @pytest.fixture
    def api_client(self):
        """创建测试客户端。"""
        app = APIServer(testing=True)
        with app.test_client() as client:
            yield client
    
    def test_health_endpoint(self, api_client):
        """测试健康检查接口。"""
        response = api_client.get('/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'healthy'
    
    def test_water_quality_endpoint(self, api_client):
        """测试水质接口。"""
        response = api_client.get('/api/water-quality/current')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'ph' in data
        assert 'turbidity' in data
        assert 'dissolved_oxygen' in data
        assert 'temperature' in data
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_water_quality.py

# 运行特定测试方法
pytest tests/test_water_quality.py::TestWaterQuality::test_valid_water_quality

# 生成覆盖率报告
pytest --cov=water_plant_controller --cov-report=html

# 运行性能测试
pytest --benchmark-only
```

## 部署指南

### 本地开发部署

```bash
# 启动开发服务器
python run_simulation.py --api-server --debug

# 或使用 Flask 开发服务器
export FLASK_APP=utils.api_server:app
export FLASK_ENV=development
flask run
```

### Docker 部署

```bash
# 构建镜像
docker build -t water-plant-app .

# 运行容器
docker run -p 5000:5000 water-plant-app

# 使用 Docker Compose
docker-compose up -d
```

### Kubernetes 部署

```bash
# 应用配置
kubectl apply -f k8s/

# 检查部署状态
kubectl get pods -n water-plant

# 查看日志
kubectl logs -f deployment/water-plant-app -n water-plant
```

## 贡献指南

### 开发流程

1. **Fork 项目**
   ```bash
   git clone https://github.com/your-username/SmartWaterFactory.git
   cd SmartWaterFactory
   ```

2. **创建功能分支**
   ```bash
   git checkout -b feature/new-feature
   ```

3. **开发和测试**
   ```bash
   # 编写代码
   vim water_plant_controller/new_module.py
   
   # 编写测试
   vim tests/test_new_module.py
   
   # 运行测试
   pytest tests/test_new_module.py
   ```

4. **代码检查**
   ```bash
   # 格式化代码
   black .
   
   # 检查代码风格
   flake8 .
   
   # 类型检查
   mypy water_plant_controller/
   ```

5. **提交代码**
   ```bash
   git add .
   git commit -m "feat: 添加新功能"
   git push origin feature/new-feature
   ```

6. **创建 Pull Request**
   - 在 GitHub 上创建 Pull Request
   - 填写详细的描述
   - 等待代码审查

### 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
type(scope): description

[optional body]

[optional footer]
```

类型：
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `style`: 代码格式化
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

示例：
```
feat(controller): 添加自适应 PID 控制器

实现了基于模糊逻辑的自适应 PID 控制器，
可以根据系统响应自动调整 PID 参数。

Closes #123
```

### 代码审查清单

- [ ] 代码符合项目风格规范
- [ ] 包含适当的测试用例
- [ ] 测试覆盖率不低于 80%
- [ ] 包含必要的文档字符串
- [ ] 没有引入新的安全漏洞
- [ ] 性能没有明显下降
- [ ] 向后兼容性良好

### 发布流程

1. **更新版本号**
   ```bash
   # 更新 __init__.py 中的版本号
   vim water_plant_controller/__init__.py
   ```

2. **更新变更日志**
   ```bash
   vim CHANGELOG.md
   ```

3. **创建发布标签**
   ```bash
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   ```

4. **构建和发布**
   ```bash
   # 构建 Docker 镜像
   docker build -t water-plant-app:v1.2.0 .
   
   # 推送到镜像仓库
   docker push water-plant-app:v1.2.0
   ```

## 常见问题

### Q: 如何添加新的控制算法？

A: 在 `water_plant_controller/control/` 目录下创建新的控制器类，继承基础控制器接口：

```python
from abc import ABC, abstractmethod

class BaseController(ABC):
    @abstractmethod
    def compute(self, current_value: float) -> float:
        pass

class MyController(BaseController):
    def compute(self, current_value: float) -> float:
        # 实现控制算法
        return control_output
```

### Q: 如何扩展水质参数？

A: 修改 `WaterQuality` 数据类，添加新的参数：

```python
@dataclass
class WaterQuality:
    ph: float
    turbidity: float
    dissolved_oxygen: float
    temperature: float
    chlorine: float = 0.0  # 新参数
    
    def is_valid(self) -> bool:
        return (
            # 现有验证逻辑
            and 0 <= self.chlorine <= 5.0  # 新参数验证
        )
```

### Q: 如何添加新的 API 接口？

A: 在 `utils/api_server.py` 中添加新的路由：

```python
@app.route('/api/new-endpoint', methods=['GET'])
def new_endpoint():
    # 实现接口逻辑
    return jsonify({'result': 'success'})
```

### Q: 如何配置日志级别？

A: 在配置文件中设置日志级别：

```json
{
    "logging": {
        "level": "DEBUG",
        "format": "detailed"
    }
}
```

## 参考资源

- [项目 GitHub 仓库](https://github.com/your-org/SmartWaterFactory)
- [API 文档](docs/api.md)
- [部署指南](docs/deployment_guide.md)
- [运维手册](docs/operations_manual.md)
- [Python 官方文档](https://docs.python.org/3/)
- [Flask 文档](https://flask.palletsprojects.com/)
- [pytest 文档](https://docs.pytest.org/)
- [Docker 文档](https://docs.docker.com/)

---

如有问题或建议，请通过以下方式联系我们：

- 📧 邮箱：dev@waterplant.com
- 💬 讨论区：https://github.com/your-org/SmartWaterFactory/discussions
- 🐛 问题报告：https://github.com/your-org/SmartWaterFactory/issues