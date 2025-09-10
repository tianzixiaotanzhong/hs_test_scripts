#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
温度监控模块 - 简化稳定版本
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
    """简化的温度监控器 - 参考stress_monitor_pro.py实现"""
    
    def __init__(self, connection=None, output_dir: Optional[Path] = None):
        """
        初始化温度监控器
        connection: SSH或串口连接对象(可选)
        output_dir: 输出目录
        """
        self.connection = connection
        self.output_dir = output_dir or Path("results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
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
        self._cache_timeout = 2  # 缓存超时2秒
        
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
        获取当前温度 - 使用与stress_monitor_pro.py相同的逻辑
        优先获取CPU温度，使用最高值
        注意：如果监控线程正在运行，直接返回当前值，避免重复调用
        """
        if not self.connection:
            logger.warning("无连接可用")
            return 0.0
        
        # 如果监控线程正在运行，直接返回当前值
        if self.monitoring and self.current_temp > 0:
            return self.current_temp
        
        # 检查缓存是否有效
        if self._cache_time and self._temp_cache > 0:
            if (datetime.now() - self._cache_time).total_seconds() < self._cache_timeout:
                return self._temp_cache
        
        temp_value = 0.0
        
        try:
            # 运行sensors命令
            output = self.connection.execute_command(
                "docker exec vscode-server sensors 2>/dev/null",
                wait_time=2,
                read_timeout=3
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
                    # sensors命令返回了输出但解析失败，尝试备用方法
                    logger.debug("sensors输出解析失败，尝试thermal_zone")
            else:
                # sensors命令没有返回输出，尝试备用方法
                logger.debug("sensors无输出，尝试thermal_zone")
                
                # 备用方法: thermal_zone
                output = self.connection.execute_command(
                    "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | grep -v '^0$'",
                    wait_time=1,
                    read_timeout=2
                )
                
                if output:
                    temps = []
                    for line in output.strip().split('\n'):
                        try:
                            line = line.strip()
                            if line and line.isdigit() and line != '0':
                                temp = int(line) / 1000.0
                                if 20 < temp < 100:
                                    temps.append(temp)
                        except:
                            pass
                    
                    if temps:
                        # 使用最高温度，与参考实现一致
                        temp_value = max(temps)
                        logger.debug(f"温度(thermal): {temp_value:.1f}°C")
                        self.current_temp = temp_value
                        self._temp_cache = temp_value
                        self._cache_time = datetime.now()
                        return temp_value
                    
        except Exception as e:
            logger.error(f"获取温度失败: {e}")
        
        # 返回缓存值（如果有）
        return self._temp_cache if self._temp_cache > 0 else temp_value
    
    def _parse_sensors_output(self, output: str) -> float:
        """
        解析sensors输出 - 与stress_monitor_pro.py保持一致
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
        
        logger.info("温度监控已停止")
        
        # 保存摘要
        self.save_summary()
    
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
    import argparse
    import sys
    from pathlib import Path
    
    # 直接导入connection_manager（不用sys.path.append）
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "connection_manager", 
        Path(__file__).parent / "src" / "connection_manager.py"
    )
    connection_manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(connection_manager)
    
    spec = importlib.util.spec_from_file_location(
        "config_loader",
        Path(__file__).parent / "src" / "config_loader.py"
    )
    config_loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_loader)
    
    parser = argparse.ArgumentParser(description='温度监控工具')
    parser.add_argument('--config', '-c', default='config.json',
                       help='配置文件路径 (默认: config.json)')
    parser.add_argument('--interval', '-i', type=int, default=10,
                       help='采样间隔(秒) (默认: 10)')
    parser.add_argument('--duration', '-d', type=int, default=0,
                       help='监控时长(分钟)，0表示持续监控 (默认: 0)')
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    print("="*60)
    print("温度监控工具 - 独立运行模式")
    print("="*60)
    
    # 加载配置
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        sys.exit(1)
    
    config = config_loader.Config.from_file(args.config)
    
    # 创建连接
    try:
        connection = connection_manager.ConnectionFactory.create_connection(
            config.connection_type,
            **config.get_connection_params()
        )
    except Exception as e:
        print(f"创建连接失败: {e}")
        sys.exit(1)
    
    # 建立连接
    if not connection.connect():
        print("连接失败")
        sys.exit(1)
    
    print(f"[OK] 连接成功 ({config.connection_type})")
    
    # 设置输出目录和日志
    output_dir = Path("results") / f"temperature_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建简单的控制台日志器
    console_logger = logging.getLogger('ssh_console')
    console_logger.setLevel(logging.DEBUG)
    console_handler = logging.FileHandler(
        output_dir / "console.log", encoding='utf-8', mode='w'
    )
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    )
    console_logger.addHandler(console_handler)
    connection.setup_console_log(console_logger)
    
    # 创建温度监控器
    monitor = TemperatureMonitor(connection, output_dir)
    
    # 测试温度读取
    print("\n测试温度读取...")
    temp = monitor.get_temperature()
    if temp > 0:
        print(f"[OK] 当前温度: {temp:.1f}°C")
    else:
        print("[ERROR] 无法读取温度")
        connection.disconnect()
        sys.exit(1)
    
    # 开始监控
    print(f"\n开始温度监控 (间隔: {args.interval}秒)")
    print("按 Ctrl+C 停止监控")
    print("-"*60)
    
    monitor.start_monitoring(args.interval)
    
    try:
        if args.duration > 0:
            # 定时监控
            time.sleep(args.duration * 60)
        else:
            # 持续监控
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n用户中断")
    
    # 停止监控
    monitor.stop_monitoring()
    
    # 显示统计
    stats = monitor.get_statistics()
    if stats['count'] > 0:
        print("\n" + "="*60)
        print("温度统计:")
        print(f"  采样数: {stats['count']}")
        print(f"  平均温度: {stats['average']:.1f}°C")
        print(f"  最高温度: {stats['maximum']:.1f}°C")
        print(f"  最低温度: {stats['minimum']:.1f}°C")
        print(f"  当前温度: {stats['current']:.1f}°C")
        print("="*60)
    
    # 断开连接
    connection.disconnect()
    print(f"\n输出目录: {output_dir}")
    print("监控结束")


if __name__ == "__main__":
    main()