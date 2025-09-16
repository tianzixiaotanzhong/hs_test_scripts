#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CPU压力测试监控系统 - 统一入口
"""

import sys
import io
import os
from pathlib import Path

# 强制禁用输出缓冲，确保实时显示
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

# 确保输出立即显示的函数
def print_realtime(*args, **kwargs):
    """实时打印函数，确保立即显示"""
    print(*args, **kwargs)
    sys.stdout.flush()

def print_inline(*args, **kwargs):
    """同行实时打印函数"""
    print(*args, end='', flush=True, **kwargs)

import logging
from datetime import datetime
import importlib.util

# 动态导入模块，避免sys.path.append
def import_module_from_file(module_name, file_path):
    """从文件路径导入模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# 导入所需模块
src_dir = Path(__file__).parent / 'src'
config_loader = import_module_from_file('config_loader', src_dir / 'config_loader.py')
connection_manager = import_module_from_file('connection_manager', src_dir / 'connection_manager.py')
stress_monitor = import_module_from_file('stress_monitor', src_dir / 'stress_monitor.py')
temperature_monitor = import_module_from_file('temperature_monitor', Path(__file__).parent / 'temperature_monitor.py')
logger_manager = import_module_from_file('logger_manager', src_dir / 'logger_manager.py')

# 从模块中获取类
Config = config_loader.Config
ConnectionFactory = connection_manager.ConnectionFactory
StressTestMonitor = stress_monitor.StressTestMonitor
TemperatureMonitor = temperature_monitor.TemperatureMonitor


def run_stress_test(config_file='config.json'):
    """运行压力测试"""
    config = Config.from_file(config_file)
    
    if not config.validate():
        print("配置文件验证失败")
        return
    
    # 设置日志系统 - 确保输出目录在程序开始时就确定
    output_dir = config.output.get_output_dir()
    log_manager = logger_manager.LoggerManager(output_dir)
    
    print_realtime(f"连接目标: {config.ssh.username}@{config.ssh.hostname}:{config.ssh.port}")
    print_realtime(f"输出目录: {output_dir}")
    
    # 创建连接
    try:
        connection = ConnectionFactory.create_connection(
            config.connection_type,
            **config.get_connection_params()
        )
    except Exception as e:
        print_realtime(f"创建连接失败: {e}")
        return
    
    print_inline("正在建立SSH连接...")
    try:
        if not connection.connect():
            print_realtime(" 失败")
            return
        print_realtime(" 成功")
    except Exception as e:
        print_realtime(f" 异常: {e}")
        return
    
    # 设置控制台日志
    connection.setup_console_log(log_manager.get_console_logger())
    
    # 创建监控器并运行
    try:
        monitor = StressTestMonitor(config, connection)
    except Exception as e:
        print(f"创建监控器失败: {e}")
        return
    
    try:
        if not monitor.start():
            print("启动监控失败")
            return
        
        # 检查环境
        monitor.check_environment()
        
        # 运行测试
        monitor.run_continuous_tests()
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    finally:
        monitor.stop()
        monitor.generate_report()
        connection.disconnect()
        print("\n测试完成")


def run_temperature_monitor(config_file='config.json'):
    """运行温度监控"""
    config = Config.from_file(config_file)
    
    if not config.validate():
        print("配置文件验证失败")
        return
    
    # 设置日志系统
    output_dir = config.output.get_output_dir()
    log_manager = logger_manager.LoggerManager(output_dir)
    
    print(f"\n温度监控")
    print(f"连接类型: {config.connection_type}")
    print(f"采样间隔: {config.monitor.temperature_interval}秒\n")
    
    # 创建连接
    connection = ConnectionFactory.create_connection(
        config.connection_type,
        **config.get_connection_params()
    )
    
    if not connection.connect():
        print("连接失败")
        return
    
    print("[OK] 连接成功")
    
    # 设置控制台日志
    connection.setup_console_log(log_manager.get_console_logger())
    
    # 创建温度监控器，使用相同的输出目录
    temp_monitor = TemperatureMonitor(connection, output_dir, config)
    
    try:
        # 开始监控
        temp_monitor.start_monitoring(
            interval=config.monitor.temperature_interval
        )
        
        print("温度监控运行中，按 Ctrl+C 停止...")
        
        # 持续显示状态
        import time
        while temp_monitor.monitoring:
            time.sleep(10)
            if temp_monitor.current_temp > 0:
                print(f"当前温度: {temp_monitor.current_temp:.1f}°C")
            
    except KeyboardInterrupt:
        print("\n\n用户中断")
    finally:
        temp_monitor.stop_monitoring()
        temp_monitor.save_summary()
        connection.disconnect()
        print("\n监控结束")


def main():
    """主入口 - 直接运行压力测试"""
    config_file = 'config.json'
    
    # 检查配置文件，如果不存在则生成
    if not Path(config_file).exists():
        print_realtime("配置文件不存在，正在生成默认配置...")
        config = Config()
        config.connection_type = 'ssh'
        config.ssh.hostname = '10.2.0.18'  # 使用当前的主机地址
        config.ssh.username = 'sunrise'
        config.ssh.password = 'sunrise'
        config.save(config_file)
        print_realtime(f"配置文件已生成: {config_file}")
        print_realtime("请根据需要修改配置文件，然后重新运行程序")
        return
    
    print_realtime("\n" + "="*50)
    print_realtime("CPU压力测试监控系统")
    print_realtime("="*50)
    print_realtime("按 Ctrl+C 停止测试并生成报告")
    print_realtime("="*50)
    
    # 直接运行压力测试
    run_stress_test(config_file)


if __name__ == "__main__":
    main()