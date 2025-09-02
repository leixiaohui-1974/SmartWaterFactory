#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能水厂控制系统 API 客户端示例

本示例展示如何使用 API 接口进行：
1. 用户认证
2. 获取实时水质数据
3. 控制系统操作
4. 数据分析和报告
5. WebSocket 实时通信

作者: 智能水厂开发团队
日期: 2024-01-01
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
import websocket
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class WaterPlantAPIClient:
    """智能水厂 API 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1"
        self.token = None
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def authenticate(self, username: str, password: str) -> bool:
        """用户认证"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                self.token = data['data']['access_token']
                self.session.headers.update({
                    'Authorization': f'Bearer {self.token}'
                })
                print(f"✅ 认证成功，用户: {username}")
                return True
            else:
                print(f"❌ 认证失败: {data.get('error', {}).get('message')}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 认证请求失败: {e}")
            return False
    
    def get_system_status(self) -> Optional[Dict]:
        """获取系统状态"""
        try:
            response = self.session.get(
                f"{self.api_base}/system/status",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                return data['data']
            else:
                print(f"❌ 获取系统状态失败: {data.get('error', {}).get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 系统状态请求失败: {e}")
            return None
    
    def get_current_water_quality(self) -> Optional[Dict]:
        """获取当前水质数据"""
        try:
            response = self.session.get(
                f"{self.api_base}/water-quality/current",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                return data['data']
            else:
                print(f"❌ 获取水质数据失败: {data.get('error', {}).get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 水质数据请求失败: {e}")
            return None
    
    def get_water_quality_history(
        self, 
        start: str, 
        end: str, 
        interval: str = "1h",
        parameters: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """获取历史水质数据"""
        params = {
            'start': start,
            'end': end,
            'interval': interval
        }
        
        if parameters:
            params['parameters'] = ','.join(parameters)
        
        try:
            response = self.session.get(
                f"{self.api_base}/water-quality/history",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                return data['data']
            else:
                print(f"❌ 获取历史数据失败: {data.get('error', {}).get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 历史数据请求失败: {e}")
            return None
    
    def get_controller_status(self) -> Optional[Dict]:
        """获取控制器状态"""
        try:
            response = self.session.get(
                f"{self.api_base}/control/status",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                return data['data']
            else:
                print(f"❌ 获取控制器状态失败: {data.get('error', {}).get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 控制器状态请求失败: {e}")
            return None
    
    def update_controller_parameters(
        self, 
        controller_type: str,
        parameters: Dict,
        setpoint: Optional[float] = None
    ) -> bool:
        """更新控制器参数"""
        payload = {
            'controller_type': controller_type,
            'parameters': parameters
        }
        
        if setpoint is not None:
            payload['setpoint'] = setpoint
        
        try:
            response = self.session.put(
                f"{self.api_base}/control/parameters",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                print(f"✅ 控制器参数更新成功")
                return True
            else:
                print(f"❌ 控制器参数更新失败: {data.get('error', {}).get('message')}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 控制器参数更新请求失败: {e}")
            return False
    
    def switch_control_mode(self, mode: str, manual_output: Optional[float] = None) -> bool:
        """切换控制模式"""
        payload = {'mode': mode}
        
        if mode == 'manual' and manual_output is not None:
            payload['manual_output'] = manual_output
        
        try:
            response = self.session.post(
                f"{self.api_base}/control/mode",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                print(f"✅ 控制模式切换成功: {mode}")
                return True
            else:
                print(f"❌ 控制模式切换失败: {data.get('error', {}).get('message')}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 控制模式切换请求失败: {e}")
            return False
    
    def get_devices_status(self) -> Optional[Dict]:
        """获取设备状态"""
        try:
            response = self.session.get(
                f"{self.api_base}/control/devices",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                return data['data']
            else:
                print(f"❌ 获取设备状态失败: {data.get('error', {}).get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 设备状态请求失败: {e}")
            return None
    
    def control_device(self, device_id: str, command: str, parameters: Dict) -> bool:
        """控制设备"""
        payload = {
            'command': command,
            'parameters': parameters,
            'confirm': True
        }
        
        try:
            response = self.session.post(
                f"{self.api_base}/control/devices/{device_id}/command",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                print(f"✅ 设备控制成功: {device_id} - {command}")
                return True
            else:
                print(f"❌ 设备控制失败: {data.get('error', {}).get('message')}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 设备控制请求失败: {e}")
            return False
    
    def get_anomalies(self, severity: Optional[str] = None) -> Optional[Dict]:
        """获取异常检测结果"""
        params = {}
        if severity:
            params['severity'] = severity
        
        try:
            response = self.session.get(
                f"{self.api_base}/analysis/anomalies",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                return data['data']
            else:
                print(f"❌ 获取异常数据失败: {data.get('error', {}).get('message')}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 异常数据请求失败: {e}")
            return None


class WaterPlantWebSocketClient:
    """智能水厂 WebSocket 客户端"""
    
    def __init__(self, ws_url: str = "ws://localhost:5000/ws", token: str = None):
        self.ws_url = ws_url
        self.token = token
        self.ws = None
        self.subscriptions = set()
        self.callbacks = {}
    
    def connect(self):
        """建立 WebSocket 连接"""
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            print("🔌 正在连接 WebSocket...")
            self.ws.run_forever()
        except Exception as e:
            print(f"❌ WebSocket 连接失败: {e}")
    
    def _on_open(self, ws):
        """连接建立回调"""
        print("✅ WebSocket 连接已建立")
        
        # 发送认证信息
        if self.token:
            auth_message = {
                'type': 'auth',
                'token': self.token
            }
            ws.send(json.dumps(auth_message))
            print("🔐 已发送认证信息")
    
    def _on_message(self, ws, message):
        """消息接收回调"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            # 处理认证响应
            if message_type == 'auth_response':
                if data.get('success'):
                    print("✅ WebSocket 认证成功")
                else:
                    print(f"❌ WebSocket 认证失败: {data.get('message')}")
                return
            
            # 调用相应的回调函数
            if message_type in self.callbacks:
                self.callbacks[message_type](data)
            else:
                print(f"📨 收到消息: {message_type}")
                
        except json.JSONDecodeError as e:
            print(f"❌ 消息解析失败: {e}")
    
    def _on_error(self, ws, error):
        """错误回调"""
        print(f"❌ WebSocket 错误: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """连接关闭回调"""
        print(f"🔌 WebSocket 连接已关闭: {close_status_code} - {close_msg}")
    
    def subscribe(self, channel: str, callback=None, parameters: Optional[List[str]] = None):
        """订阅数据通道"""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            message = {
                'type': 'subscribe',
                'channel': channel
            }
            
            if parameters:
                message['parameters'] = parameters
            
            self.ws.send(json.dumps(message))
            self.subscriptions.add(channel)
            
            if callback:
                self.callbacks[channel] = callback
            
            print(f"📡 已订阅通道: {channel}")
        else:
            print("❌ WebSocket 未连接，无法订阅")
    
    def send_command(self, action: str, parameters: Dict):
        """发送控制命令"""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            message = {
                'type': 'control_command',
                'action': action,
                'parameters': parameters
            }
            
            self.ws.send(json.dumps(message))
            print(f"📤 已发送命令: {action}")
        else:
            print("❌ WebSocket 未连接，无法发送命令")


def print_water_quality(data: Dict):
    """打印水质数据"""
    print("\n💧 实时水质数据:")
    print(f"  pH值: {data.get('ph', 'N/A')}")
    print(f"  浊度: {data.get('turbidity', 'N/A')} NTU")
    print(f"  溶解氧: {data.get('dissolved_oxygen', 'N/A')} mg/L")
    print(f"  温度: {data.get('temperature', 'N/A')} °C")
    print(f"  时间: {data.get('timestamp', 'N/A')}")


def print_controller_status(data: Dict):
    """打印控制器状态"""
    print("\n🎛️ 控制器状态:")
    print(f"  模式: {data.get('mode', 'N/A')}")
    print(f"  类型: {data.get('controller_type', 'N/A')}")
    print(f"  设定值: {data.get('setpoint', 'N/A')}")
    print(f"  当前值: {data.get('current_value', 'N/A')}")
    print(f"  输出: {data.get('output', 'N/A')}")


def print_alert(data: Dict):
    """打印报警信息"""
    payload = data.get('payload', {})
    severity = payload.get('severity', 'unknown')
    
    severity_icons = {
        'low': '🟡',
        'medium': '🟠', 
        'high': '🔴'
    }
    
    icon = severity_icons.get(severity, '⚠️')
    
    print(f"\n{icon} 系统报警:")
    print(f"  严重程度: {severity}")
    print(f"  参数: {payload.get('parameter', 'N/A')}")
    print(f"  当前值: {payload.get('value', 'N/A')}")
    print(f"  阈值: {payload.get('threshold', 'N/A')}")
    print(f"  消息: {payload.get('message', 'N/A')}")


def main():
    """主函数 - API 客户端示例"""
    print("🏭 智能水厂控制系统 API 客户端示例")
    print("=" * 50)
    
    # 创建 API 客户端
    client = WaterPlantAPIClient()
    
    # 1. 用户认证
    print("\n1️⃣ 用户认证")
    if not client.authenticate("admin", "admin123"):
        print("❌ 认证失败，退出程序")
        return
    
    # 2. 获取系统状态
    print("\n2️⃣ 系统状态")
    status = client.get_system_status()
    if status:
        print(f"  仿真运行: {'✅' if status.get('simulation_running') else '❌'}")
        print(f"  控制模式: {status.get('control_mode')}")
        print(f"  系统负载: {status.get('system_load', 0):.2%}")
        print(f"  内存使用: {status.get('memory_usage', 0):.2%}")
        print(f"  CPU使用: {status.get('cpu_usage', 0):.2%}")
    
    # 3. 获取当前水质
    print("\n3️⃣ 当前水质")
    water_quality = client.get_current_water_quality()
    if water_quality:
        print_water_quality(water_quality)
    
    # 4. 获取控制器状态
    print("\n4️⃣ 控制器状态")
    controller = client.get_controller_status()
    if controller:
        print_controller_status(controller)
    
    # 5. 获取历史数据
    print("\n5️⃣ 历史数据（最近1小时）")
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    
    history = client.get_water_quality_history(
        start=start_time.isoformat(),
        end=end_time.isoformat(),
        interval="5m",
        parameters=["ph", "turbidity"]
    )
    
    if history and history.get('records'):
        records = history['records']
        print(f"  获取到 {len(records)} 条记录")
        if records:
            latest = records[-1]
            print(f"  最新记录: pH={latest.get('ph')}, 浊度={latest.get('turbidity')}")
    
    # 6. 获取设备状态
    print("\n6️⃣ 设备状态")
    devices = client.get_devices_status()
    if devices:
        pumps = devices.get('pumps', [])
        valves = devices.get('valves', [])
        sensors = devices.get('sensors', [])
        
        print(f"  水泵数量: {len(pumps)}")
        print(f"  阀门数量: {len(valves)}")
        print(f"  传感器数量: {len(sensors)}")
        
        if pumps:
            pump = pumps[0]
            print(f"  主水泵状态: {pump.get('status')}")
            print(f"  主水泵转速: {pump.get('speed')}%")
    
    # 7. 获取异常检测结果
    print("\n7️⃣ 异常检测")
    anomalies = client.get_anomalies()
    if anomalies:
        summary = anomalies.get('summary', {})
        print(f"  总异常数: {summary.get('total', 0)}")
        print(f"  活跃异常: {summary.get('active', 0)}")
        print(f"  已解决异常: {summary.get('resolved', 0)}")
        
        active_anomalies = [a for a in anomalies.get('anomalies', []) if a.get('status') == 'active']
        if active_anomalies:
            print("  活跃异常列表:")
            for anomaly in active_anomalies[:3]:  # 只显示前3个
                print(f"    - {anomaly.get('parameter')}: {anomaly.get('description')}")
    
    # 8. 控制操作示例
    print("\n8️⃣ 控制操作示例")
    
    # 更新 PID 参数
    print("  更新 PID 控制器参数...")
    success = client.update_controller_parameters(
        controller_type="pid",
        parameters={"kp": 1.2, "ki": 0.15, "kd": 0.08},
        setpoint=7.5
    )
    
    if success:
        # 等待一下再获取更新后的状态
        time.sleep(1)
        updated_controller = client.get_controller_status()
        if updated_controller:
            print(f"  新设定值: {updated_controller.get('setpoint')}")
    
    print("\n✅ API 客户端示例完成")


def websocket_example():
    """WebSocket 客户端示例"""
    print("\n🔌 WebSocket 客户端示例")
    print("=" * 50)
    
    # 首先获取认证令牌
    client = WaterPlantAPIClient()
    if not client.authenticate("admin", "admin123"):
        print("❌ 认证失败，无法启动 WebSocket")
        return
    
    # 创建 WebSocket 客户端
    ws_client = WaterPlantWebSocketClient(token=client.token)
    
    # 设置回调函数
    ws_client.callbacks = {
        'water_quality': lambda data: print_water_quality(data.get('payload', {})),
        'controller_status': lambda data: print_controller_status(data.get('payload', {})),
        'alert': print_alert
    }
    
    # 连接并订阅（这会阻塞）
    try:
        # 在实际应用中，你可能需要在单独的线程中运行这个
        ws_client.connect()
    except KeyboardInterrupt:
        print("\n👋 用户中断，关闭 WebSocket 连接")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="智能水厂 API 客户端示例")
    parser.add_argument(
        "--mode", 
        choices=["api", "websocket"], 
        default="api",
        help="运行模式: api (REST API示例) 或 websocket (WebSocket示例)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "api":
        main()
    elif args.mode == "websocket":
        websocket_example()