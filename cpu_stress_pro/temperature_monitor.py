#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
温度监控模块 - 优化版本
可独立运行或作为模块调用
"""

import re
import time
import threading
import logging
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class TemperatureMonitor:
    """优化的温度监控器"""
    
    def __init__(self, connection=None, output_dir: Optional[Path] = None, config=None):
        """
        初始化温度监控器
        connection: SSH或串口连接对象(可选)
        output_dir: 输出目录
        config: 配置对象(可选)
        """
        self.connection = connection
        self.output_dir = output_dir or Path("results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config
        
        # 温度数据
        self.current_temp = 0.0
        self.temp_history = []
        
        # 监控控制
        self.monitoring = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        
        # 温度缓存（避免频繁调用）
        self._temp_cache = 0.0
        self._cache_time = None
        self._cache_timeout = 10  # 缓存超时10秒，避免重复调用
        
        # CSV文件
        self.csv_file = self.output_dir / "temperature_log.csv"
        self._init_csv()
        
        logger.debug(f"温度监控器初始化完成")
    
    def set_connection(self, connection):
        """设置连接对象"""
        self.connection = connection
    
    def _init_csv(self):
        """初始化CSV文件"""
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["时间戳", "温度(°C)", "备注"])
        logger.debug(f"温度日志创建: {self.csv_file}")
    
    def get_temperature(self) -> float:
        """
        获取当前温度 - 优化版本
        只使用sensors方法，支持缓存
        """
        if not self.connection:
            logger.warning("无连接可用")
            return 0.0
        
        # 检查缓存是否有效（避免频繁调用）
        if self._cache_time and self._temp_cache > 0:
            if (datetime.now() - self._cache_time).total_seconds() < self._cache_timeout:
                logger.debug(f"使用缓存温度: {self._temp_cache:.1f}°C")
                return self._temp_cache
        
        temp_value = 0.0
        
        try:
            # 只使用sensors命令读取温度，增加超时处理
            if hasattr(self, 'config') and self.config and self.config.test.enter_docker:
                output = self.connection.execute_command(
                    "docker exec vscode-server timeout 5s sensors 2>/dev/null",
                    wait_time=1,
                    read_timeout=6
                )
            else:
                # 直接在主机上运行sensors命令，使用timeout限制执行时间
                output = self.connection.execute_command(
                    "timeout 5s sensors 2>/dev/null",
                    wait_time=1,
                    read_timeout=6
                )
            
            if output and 'temp' in output.lower():
                temp_value = self._parse_sensors_output(output)
                if temp_value > 0:
                    logger.debug(f"温度读取: {temp_value:.1f}°C")
                    self.current_temp = temp_value
                    self._temp_cache = temp_value
                    self._cache_time = datetime.now()
                    return temp_value
                else:
                    logger.debug("sensors输出解析失败")
            else:
                logger.debug("sensors命令无输出或超时")
                    
        except Exception as e:
            logger.error(f"获取温度失败: {e}")
        
        # 返回缓存值（如果有）
        return self._temp_cache if self._temp_cache > 0 else temp_value
    
    def _parse_sensors_output(self, output: str) -> float:
        """
        解析sensors输出 - 优化版本
        优先使用CPU温度，返回最高值
        """
        lines = output.split('\n')
        cpu_temps = []
        all_temps = []
        
        # 逐行处理，查找CPU相关的温度
        i = 0
        processed_lines = set()  # 记录已处理的行，避免重复
        while i < len(lines):
            line = lines[i]
            # 查找CPU相关的传感器 (cpu0_thermal, cpu1_thermal, ...)
            if 'cpu' in line.lower() and 'thermal' in line.lower():
                # 查看接下来的几行
                found_temp = False
                for j in range(i+1, min(i+4, len(lines))):
                    if j in processed_lines:
                        continue
                    if 'temp' in lines[j].lower():
                        # 匹配温度格式: temp1:        +54.7 C
                        temp_match = re.search(r'temp\d*:\s*\+?(\d+\.?\d*)\s*[C°]', lines[j])
                        if temp_match:
                            try:
                                temp = float(temp_match.group(1))
                                # 排除37°C（电池温度）和异常值
                                if 30 < temp < 100 and temp != 37.0:
                                    cpu_temps.append(temp)
                                    logger.debug(f"找到CPU温度: {line.strip()} -> {temp:.1f}°C")
                                    processed_lines.add(j)
                                    found_temp = True
                                    break
                            except:
                                pass
                if found_temp:
                    i = max(i+1, j+1)  # 跳过已处理的行
                else:
                    i += 1
            else:
                i += 1
        
        # 如果没有找到CPU温度，匹配所有温度
        if not cpu_temps:
            all_temp_matches = re.findall(r'temp\d*:\s*\+?(\d+\.?\d*)\s*[C°]', output)
            for match in all_temp_matches:
                try:
                    temp = float(match)
                    if 30 < temp < 100 and temp != 37.0:
                        all_temps.append(temp)
                except:
                    pass
        
        # 返回结果
        if cpu_temps:
            # 使用CPU温度的最高值
            temp_value = max(cpu_temps)
            # 去重并记录唯一的传感器数
            unique_temps = list(set(cpu_temps))
            logger.debug(f"CPU最高温度: {temp_value:.1f}°C (从{len(unique_temps)}个CPU传感器)")
            return temp_value
        elif all_temps:
            # 使用所有温度的最高值
            temp_value = max(all_temps)
            logger.debug(f"系统最高温度: {temp_value:.1f}°C (从{len(all_temps)}个传感器)")
            return temp_value
        else:
            logger.warning("未找到有效温度数据")
        
        return 0.0
    
    def start_monitoring(self, interval: int = 10):
        """
        开始温度监控
        interval: 采样间隔(秒)
        """
        if self.monitoring:
            logger.warning("温度监控已在运行")
            return
        
        self.monitoring = True
        self.stop_event.clear()
        
        def monitor_loop():
            """监控循环"""
            logger.debug(f"温度监控线程启动，间隔: {interval}秒")
            
            while self.monitoring and not self.stop_event.wait(interval):
                try:
                    temp = self.get_temperature()
                    if temp > 0:
                        # 记录到历史
                        self.temp_history.append({
                            'time': datetime.now(),
                            'temp': temp
                        })
                        
                        # 写入CSV
                        with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow([
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                f"{temp:.1f}",
                                "自动采集"
                            ])
                        
                        logger.info(f"[温度监控] {datetime.now().strftime('%H:%M:%S')} - {temp:.1f}°C")
                
                except Exception as e:
                    logger.error(f"温度监控错误: {e}")
            
            logger.debug("温度监控线程停止")
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止温度监控"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            self.monitor_thread = None
        
        logger.debug("温度监控已停止")
    
    def get_statistics(self) -> Dict:
        """获取温度统计信息"""
        if not self.temp_history:
            return {
                "count": 0,
                "average": 0.0,
                "maximum": 0.0,
                "minimum": 0.0,
                "current": self.current_temp
            }
        
        temps = [d['temp'] for d in self.temp_history]
        return {
            "count": len(temps),
            "average": sum(temps) / len(temps),
            "maximum": max(temps),
            "minimum": min(temps),
            "current": self.current_temp
        }
    
    def save_summary(self):
        """保存温度摘要"""
        if not self.temp_history:
            logger.warning("无温度数据")
            return
        
        stats = self.get_statistics()
        summary = {
            "采样数": stats["count"],
            "平均温度": f"{stats['average']:.1f}°C",
            "最高温度": f"{stats['maximum']:.1f}°C",
            "最低温度": f"{stats['minimum']:.1f}°C",
            "当前温度": f"{stats['current']:.1f}°C"
        }
        
        summary_file = self.output_dir / "temperature_summary.json"
        import json
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"温度摘要已保存: {summary_file}")


def main():
    """独立运行温度监控"""
    import sys
    from pathlib import Path
    
    # 强制禁用输出缓冲
    import os
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    # 设置UTF-8编码
    if sys.platform == 'win32':
        import locale
        locale.setlocale(locale.LC_ALL, '')
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass
    
    # 实时打印函数
    def print_realtime(*args, **kwargs):
        print(*args, **kwargs)
        sys.stdout.flush()
    
    # 导入模块
    import importlib.util
    
    def import_module_from_file(module_name, file_path):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    src_dir = Path(__file__).parent / 'src'
    config_loader = import_module_from_file('config_loader', src_dir / 'config_loader.py')
    connection_manager = import_module_from_file('connection_manager', src_dir / 'connection_manager.py')
    
    Config = config_loader.Config
    ConnectionFactory = connection_manager.ConnectionFactory
    
    print_realtime("="*50)
    print_realtime("独立温度监控系统")
    print_realtime("="*50)
    print_realtime("按 Ctrl+C 停止监控")
    print_realtime("="*50)
    
    config_file = 'config.json'
    
    # 检查配置文件
    if not Path(config_file).exists():
        print_realtime("配置文件不存在，请先运行 python monitor.py 生成配置")
        return
    
    # 加载配置
    config = Config.from_file(config_file)
    if not config.validate():
        print_realtime("配置文件验证失败")
        return
    
    print_realtime(f"连接目标: {config.ssh.username}@{config.ssh.hostname}:{config.ssh.port}")
    print_realtime(f"采样间隔: {config.monitor.temperature_interval}秒")
    
    # 创建连接
    try:
        connection = ConnectionFactory.create_connection(
            config.connection_type,
            **config.get_connection_params()
        )
    except Exception as e:
        print_realtime(f"创建连接失败: {e}")
        return
    
    try:
        if not connection.connect():
            print_realtime("SSH连接失败")
            return
        print_realtime("SSH连接成功")
    except Exception as e:
        print_realtime(f"SSH连接异常: {e}")
        return
    
    # 使用配置文件中的输出目录设置
    output_dir = config.output.get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建温度监控器
    temp_monitor = TemperatureMonitor(connection, output_dir, config)
    
    # 测试温度读取
    print_realtime("测试温度读取...")
    temp = temp_monitor.get_temperature()
    if temp > 0:
        print_realtime(f"当前温度: {temp:.1f}°C")
    else:
        print_realtime("无法读取温度")
        connection.disconnect()
        return
    
    print_realtime(f"\n开始温度监控，输出目录: {output_dir}")
    print_realtime("-"*50)
    
    # 启动监控
    temp_monitor.start_monitoring(interval=config.monitor.temperature_interval)
    
    try:
        # 持续显示状态
        while temp_monitor.monitoring:
            time.sleep(5)
            if temp_monitor.current_temp > 0:
                print_realtime(f"[{datetime.now().strftime('%H:%M:%S')}] 当前温度: {temp_monitor.current_temp:.1f}°C")
    except KeyboardInterrupt:
        print_realtime("\n\n用户中断")
    finally:
        # 停止监控
        temp_monitor.stop_monitoring()
        temp_monitor.save_summary()
        
        # 显示统计
        stats = temp_monitor.get_statistics()
        if stats['count'] > 0:
            print_realtime("\n" + "="*50)
            print_realtime("温度监控统计:")
            print_realtime(f"  采样数: {stats['count']}")
            print_realtime(f"  平均温度: {stats['average']:.1f}°C")
            print_realtime(f"  最高温度: {stats['maximum']:.1f}°C")
            print_realtime(f"  最低温度: {stats['minimum']:.1f}°C")
            print_realtime("="*50)
        
        connection.disconnect()
        print_realtime(f"\n输出目录: {output_dir}")
        print_realtime("温度监控结束")


if __name__ == "__main__":
    main()