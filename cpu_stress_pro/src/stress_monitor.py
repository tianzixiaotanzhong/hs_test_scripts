#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CPU压力测试监控系统 V3.0
支持JSON配置文件，更Pythonic的实现
"""

import sys
import io
import time

# 设置标准输出编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import re
import csv
import signal
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

import importlib.util

# 动态导入模块
def import_module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# 导入所需模块
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
config_loader = import_module_from_file('config_loader', current_dir / 'config_loader.py')
connection_manager = import_module_from_file('connection_manager', current_dir / 'connection_manager.py')
temperature_monitor = import_module_from_file('temperature_monitor', parent_dir / 'temperature_monitor.py')

# 从模块中获取类
Config = config_loader.Config
ConfigManager = config_loader.ConfigManager
ConnectionFactory = connection_manager.ConnectionFactory
BaseConnection = connection_manager.BaseConnection
TemperatureMonitor = temperature_monitor.TemperatureMonitor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """测试结果数据类"""
    test_id: int
    timestamp: datetime
    cpu_count: int
    bogo_ops: int
    real_time: float
    bogo_ops_per_sec: float
    temperature: float
    status: str
    
    def to_csv_row(self) -> List[str]:
        """转换为CSV行"""
        return [
            str(self.test_id),
            self.timestamp.strftime('%H:%M:%S'),
            str(self.cpu_count),
            str(self.bogo_ops),
            f"{self.real_time:.2f}",
            f"{self.bogo_ops_per_sec:.2f}",
            f"{self.temperature:.1f}",
            self.status
        ]


class StressTestMonitor:
    """压力测试监控器 V3.0"""
    
    def __init__(self, config: Config, connection: BaseConnection):
        """
        初始化监控器
        config: 配置对象
        connection: 连接对象
        """
        self.config = config
        self.connection = connection
        
        # 创建输出目录
        self.output_dir = config.output.get_output_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"输出目录: {self.output_dir}")
        
        # 初始化温度监控器 - 使用简化版本
        self.temp_monitor = TemperatureMonitor(connection, self.output_dir)
        
        # 测试数据
        self.test_results: List[TestResult] = []
        self.test_count = 0
        self.successful_tests = 0
        self.failed_tests = 0
        
        # 运行状态
        self.running = False
        self._stop_requested = False
        
        # 文件路径
        self.csv_file = self.output_dir / "test_results.csv"
        
        # 环境信息
        self.current_environment = ""
        self.in_docker = None
        
        self._setup_signal_handlers()
        logger.debug("压力测试监控器初始化完成")
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，正在停止...")
        self._stop_requested = True
        self.stop()
    
    def start(self) -> bool:
        """启动监控"""
        if not self.connection.is_connected():
            logger.error("连接未建立")
            return False
        
        self.running = True
        
        # 初始化CSV文件
        self._init_csv()
        
        # 启动温度监控
        if self.config.monitor.enable_temperature:
            self.temp_monitor.start_monitoring(
                interval=self.config.monitor.temperature_interval
            )
        
        logger.debug("监控已启动")
        return True
    
    def stop(self):
        """停止监控"""
        self.running = False
        
        # 停止温度监控
        if self.temp_monitor.monitoring:
            self.temp_monitor.stop_monitoring()
        
        # 保存摘要
        self.save_summary()
        
        logger.info("监控已停止")
    
    def _init_csv(self):
        """初始化CSV文件"""
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "序号", "时间", "CPU数", "Bogo Ops", 
                "运行时间(秒)", "Bogo Ops/s", "温度(°C)", "状态"
            ])
        logger.debug(f"CSV文件创建: {self.csv_file}")
    
    def check_environment(self) -> str:
        """检查当前环境"""
        logger.debug("检查当前环境...")
        
        # 获取hostname的纯文本输出
        output = self.connection.execute_command("hostname | head -1", wait_time=1, read_timeout=2)
        hostname = output.strip().split('\n')[0] if output else ""
        
        logger.debug(f"Hostname输出: {hostname}")
        
        if 'vscode-server' in hostname:
            self.in_docker = True
            self.current_environment = "Docker容器"
        elif 'qcm6490' in hostname:
            self.in_docker = False
            self.current_environment = "主机系统"
            # 检查Docker容器是否存在
            docker_check = self.connection.execute_command(
                "docker ps | grep vscode-server", wait_time=1, read_timeout=2
            )
            if 'vscode-server' in docker_check:
                logger.info("检测到vscode-server容器运行中")
        else:
            # 如果无法通过hostname判断，检查是否在容器内
            env_check = self.connection.execute_command("cat /proc/1/cgroup | grep docker", wait_time=1, read_timeout=1)
            if 'docker' in env_check:
                self.in_docker = True
                self.current_environment = "Docker容器"
            else:
                self.in_docker = False
                self.current_environment = "主机系统"
        
        logger.debug(f"当前环境: {self.current_environment}")
        return self.current_environment
    
    def enter_docker_if_needed(self) -> bool:
        """进入Docker容器（如果需要）"""
        if not self.config.test.enter_docker:
            logger.info("跳过Docker检查")
            return True
        
        env = self.check_environment()
        
        if env == "主机系统":
            logger.info("尝试进入Docker容器...")
            output = self.connection.execute_command(
                "docker exec -it vscode-server /bin/bash",
                wait_time=2,
                read_timeout=3
            )
            
            time.sleep(2)
            env = self.check_environment()
            
            if env == "Docker容器":
                logger.info("成功进入Docker容器")
                return True
            else:
                logger.error("进入Docker容器失败")
                return False
        
        return env == "Docker容器"
    
    def check_and_install_stress_ng(self) -> bool:
        """检查并安装stress-ng"""
        if not self.config.test.install_stress_ng:
            logger.info("跳过stress-ng安装检查")
            return True
        
        logger.info("检查stress-ng...")
        
        output = self.connection.execute_command("which stress-ng", wait_time=1, read_timeout=2)
        
        if '/stress-ng' in output:
            logger.info("stress-ng已安装")
            return True
        
        logger.info("安装stress-ng...")
        
        # 更新包列表
        self.connection.execute_command("apt-get update", wait_time=10, read_timeout=15)
        
        # 安装stress-ng
        self.connection.execute_command("apt-get install -y stress-ng", wait_time=20, read_timeout=25)
        
        # 再次检查
        output = self.connection.execute_command("which stress-ng", wait_time=1, read_timeout=2)
        
        if '/stress-ng' in output:
            logger.info("stress-ng安装成功")
            return True
        else:
            logger.error("stress-ng安装失败")
            return False
    
    def parse_stress_output(self, output: str) -> Optional[TestResult]:
        """解析stress-ng输出"""
        # stress-ng输出格式: stress-ng: info:  [5823] cpu               85883     60.04    463.39      0.92      1430.44         184.97
        # 格式为: stressor_name bogo_ops real_time user_time sys_time bogo_ops_per_sec_real bogo_ops_per_sec_usr_sys
        pattern = r'stress-ng:\s+info:\s+\[\d+\]\s+cpu\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)'
        match = re.search(pattern, output)
        
        if not match:
            logger.warning(f"无法解析stress-ng输出，输出内容前200字符: {output[:200]}...")
            return None
        
        try:
            bogo_ops = int(match.group(1))  # 第1组是bogo_ops总数
            real_time = float(match.group(2))  # 第2组是real_time
            bogo_ops_per_sec = float(match.group(5))  # 第5组是bogo_ops_per_sec (real time)
            
            result = TestResult(
                test_id=self.test_count,  # test_count在run_single_test中增加
                timestamp=datetime.now(),
                cpu_count=8,  # 固定8核
                bogo_ops=bogo_ops,
                real_time=real_time,
                bogo_ops_per_sec=bogo_ops_per_sec,
                temperature=self.temp_monitor.current_temp,
                status='success'
            )
            
            self.successful_tests += 1
            self.test_results.append(result)
            
            # 保存到CSV
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(result.to_csv_row())
            
            logger.info(
                f"测试#{result.test_id}完成: "
                f"Bogo Ops={result.bogo_ops}, "
                f"性能={result.bogo_ops_per_sec:.2f} ops/s, "
                f"温度={result.temperature:.1f}°C"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"解析错误: {e}")
            self.failed_tests += 1
            return None
    
    def run_single_test(self, cpu_count: int = 0) -> bool:
        """运行单次测试"""
        timeout = self.config.test.timeout_seconds
        
        # 先增加测试计数
        self.test_count += 1
        current_test_num = self.test_count
        
        logger.info(f"开始测试#{current_test_num}: CPU={cpu_count if cpu_count else '全部'}, 时长={timeout}s")
        
        # 测试前获取温度（从监控线程读取当前值，避免重复调用）
        pre_temp = self.temp_monitor.current_temp
        if pre_temp > 0:
            logger.debug(f"测试#{current_test_num}前温度: {pre_temp:.1f}°C")
        
        # 构建命令 - 使用固定的8个CPU核心数，避免$(nproc)在某些环境下的问题
        if cpu_count == 0:
            base_cmd = f"stress-ng --cpu 8 --timeout {timeout}s --metrics-brief"
        else:
            base_cmd = f"stress-ng --cpu {cpu_count} --timeout {timeout}s --metrics-brief"
        
        # 总是在Docker容器内运行stress-ng（因为stress-ng在容器里）
        logger.debug("在Docker容器内运行stress-ng")
        cmd = f"docker exec vscode-server {base_cmd}"
        
        # 执行命令
        output = self.connection.execute_command(cmd, wait_time=1, read_timeout=timeout+5)
        
        # 解析结果
        result = self.parse_stress_output(output)
        
        # 等待3秒让温度稳定并让监控线程更新温度
        time.sleep(3)
        
        # 测试后获取温度（从监控线程读取当前值）
        post_temp = self.temp_monitor.current_temp
        if post_temp > 0:
            logger.debug(f"测试#{current_test_num}后温度: {post_temp:.1f}°C")
            # 更新结果中的温度（使用测试后温度）
            if result:
                result.temperature = post_temp
            else:
                # 如果测试失败，也记录温度
                result = TestResult(
                    test_id=current_test_num,
                    timestamp=datetime.now(),
                    bogo_ops=0,
                    runtime=timeout,
                    bogo_ops_per_sec=0.0,
                    temperature=post_temp,
                    cpu_count=cpu_count if cpu_count else 8,
                    status="failed"
                )
                self.test_results.append(result)
                self._save_result(result)
        
        if result:
            # 确保测试编号正确
            result.test_id = current_test_num
            self._print_test_result(result)
            return True
        else:
            logger.warning(f"测试 #{current_test_num} 失败 - 无法解析stress-ng输出")
            self.failed_tests += 1
            return False
    
    def _print_test_result(self, result: TestResult):
        """打印测试结果"""
        print(f"[{result.test_id:03d}] 性能: {result.bogo_ops_per_sec:8.2f} ops/s | 温度: {result.temperature:5.1f}°C | {result.status}")
    
    def run_continuous_tests(self):
        """连续运行测试"""
        start_time = datetime.now()
        
        logger.info(
            f"开始连续测试 - "
            f"持续时间: {self.config.test.duration_minutes or '无限制'}分钟, "
            f"间隔: {self.config.test.interval_seconds}秒, "
            f"最大测试数: {self.config.test.max_tests}"
        )
        
        self._print_test_config()
        
        while self.running and not self._stop_requested:
            # 检查最大测试数
            if self.test_count >= self.config.test.max_tests:
                logger.info(f"达到最大测试数 {self.config.test.max_tests}")
                break
            
            # 检查时间限制
            if self.config.test.duration_minutes:
                elapsed = (datetime.now() - start_time).total_seconds() / 60
                if elapsed >= self.config.test.duration_minutes:
                    logger.info("达到时间限制")
                    break
            
            # 运行测试
            self.run_single_test()
            
            # 打印统计
            if self.test_count > 0 and self.test_count % 10 == 0:
                self._print_statistics()
            
            # 等待间隔
            if self.running and not self._stop_requested:
                for _ in range(self.config.test.interval_seconds):
                    if self._stop_requested:
                        break
                    time.sleep(1)
    
    def _print_test_config(self):
        """打印测试配置"""
        print("\n[配置] ", end="")
        print(f"时长: {'无限' if not self.config.test.duration_minutes else f'{self.config.test.duration_minutes}分'} | ", end="")
        print(f"间隔: {self.config.test.interval_seconds}秒 | ", end="")
        print(f"最大: {self.config.test.max_tests}次 | ", end="")
        print(f"超时: {self.config.test.timeout_seconds}秒")
        print("-" * 60)
    
    def _print_statistics(self):
        """打印统计信息"""
        if not self.test_results:
            return
        
        ops_values = [r.bogo_ops_per_sec for r in self.test_results]
        avg_perf = sum(ops_values) / len(ops_values)
        
        temp_stats = self.temp_monitor.get_statistics()
        avg_temp = temp_stats.average if temp_stats else 0
        
        print(f"\n[统计] 进度: {self.test_count}/{self.config.test.max_tests} | "
              f"成功: {self.successful_tests} | 失败: {self.failed_tests} | "
              f"平均: {avg_perf:.2f} ops/s, {avg_temp:.1f}°C")
    
    def generate_report(self):
        """生成测试报告"""
        if not self.test_results:
            logger.warning("无测试数据")
            return
        
        # 生成图表
        if self.config.output.save_charts:
            self._generate_charts()
        
        # 打印报告
        self._print_report()
    
    def _generate_charts(self):
        """生成图表 - 参考stress_monitor_pro.py实现"""
        if not self.test_results:
            logger.warning("无测试数据，无法生成图表")
            return
            
        times = [r.timestamp for r in self.test_results]
        ops_per_sec = [r.bogo_ops_per_sec for r in self.test_results]
        temperatures = [r.temperature for r in self.test_results]
        
        # 创建图表 - 3个子图
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
        
        # 图1: 性能趋势图
        ax1.plot(range(1, len(ops_per_sec)+1), ops_per_sec, 'o-', 
                markersize=8, linewidth=2, color='blue', label='性能')
        ax1.set_title('CPU压力测试性能趋势', fontsize=16, fontweight='bold')
        ax1.set_xlabel('测试序号', fontsize=12)
        ax1.set_ylabel('性能 (Bogo Ops/s)', fontsize=12)
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # 添加平均线
        if ops_per_sec:
            avg = sum(ops_per_sec) / len(ops_per_sec)
            ax1.axhline(y=avg, color='red', linestyle='--', linewidth=1.5,
                       label=f'平均值: {avg:.2f} ops/s')
            ax1.legend(loc='best')
        
        # 设置Y轴范围
        if ops_per_sec:
            y_min = min(ops_per_sec) * 0.95
            y_max = max(ops_per_sec) * 1.05
            ax1.set_ylim(y_min, y_max)
        
        # 图2: 温度趋势图
        valid_temps = [t for t in temperatures if t > 0]
        if valid_temps:
            ax2.plot(range(1, len(temperatures)+1), temperatures, 'o-', 
                    markersize=8, linewidth=2, color='red', label='温度')
            ax2.set_title('系统温度变化', fontsize=14, fontweight='bold')
            ax2.set_xlabel('测试序号', fontsize=12)
            ax2.set_ylabel('温度 (°C)', fontsize=12)
            ax2.grid(True, alpha=0.3, linestyle='--')
            
            # 添加统计线
            avg_temp = sum(valid_temps) / len(valid_temps)
            max_temp = max(valid_temps)
            min_temp = min(valid_temps)
            
            ax2.axhline(y=avg_temp, color='orange', linestyle='--', linewidth=1.5,
                       label=f'平均: {avg_temp:.1f}°C')
            ax2.axhline(y=85, color='darkred', linestyle=':', linewidth=2,
                       label='高温警戒 (85°C)')
            
            # 添加最高最低标记
            ax2.axhline(y=max_temp, color='red', linestyle=':', linewidth=1, alpha=0.5,
                       label=f'最高: {max_temp:.1f}°C')
            ax2.axhline(y=min_temp, color='blue', linestyle=':', linewidth=1, alpha=0.5,
                       label=f'最低: {min_temp:.1f}°C')
            
            ax2.legend(loc='best', fontsize=10)
            
            # 设置温度范围
            y_min = min(30, min_temp - 5)
            y_max = max(90, max_temp + 5)
            ax2.set_ylim(y_min, y_max)
        
        # 图3: 性能与温度关系
        valid_data = [(t, o) for t, o in zip(temperatures, ops_per_sec) if t > 0]
        if valid_data:
            temps, ops = zip(*valid_data)
            scatter = ax3.scatter(temps, ops, alpha=0.7, s=100, c=range(len(temps)), 
                                cmap='viridis', edgecolors='black', linewidth=1)
            ax3.set_title('性能与温度关系分析', fontsize=14, fontweight='bold')
            ax3.set_xlabel('温度 (°C)', fontsize=12)
            ax3.set_ylabel('性能 (Bogo Ops/s)', fontsize=12)
            ax3.grid(True, alpha=0.3, linestyle='--')
            
            # 添加颜色条表示测试顺序
            cbar = plt.colorbar(scatter, ax=ax3)
            cbar.set_label('测试顺序', rotation=270, labelpad=15)
            
            # 添加趋势线
            if len(temps) > 1:
                z = np.polyfit(temps, ops, 1)
                p = np.poly1d(z)
                temp_range = np.linspace(min(temps), max(temps), 100)
                ax3.plot(temp_range, p(temp_range), 'r--', alpha=0.6, linewidth=2,
                        label=f'趋势线: y={z[0]:.2f}x+{z[1]:.2f}')
                ax3.legend(loc='best')
                
                # 计算相关系数
                correlation = np.corrcoef(temps, ops)[0, 1]
                ax3.text(0.05, 0.95, f'相关系数: {correlation:.3f}', 
                        transform=ax3.transAxes, fontsize=10,
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 调整布局
        plt.suptitle(f'CPU压力测试报告 - {datetime.now().strftime("%Y-%m-%d %H:%M")}', 
                    fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        # 保存图表
        chart_file = self.output_dir / "performance_chart.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"性能图表已生成: {chart_file}")
        print(f"\n[图表] 性能分析图表已保存: {chart_file}")
    
    def _print_report(self):
        """打印测试报告"""
        ops_values = [r.bogo_ops_per_sec for r in self.test_results]
        avg_perf = sum(ops_values) / len(ops_values)
        
        print(f"\n{'='*50}")
        print("测试报告")
        print("="*50)
        print(f"总测试次数: {self.test_count}")
        print(f"成功次数: {self.successful_tests}")
        print(f"失败次数: {self.failed_tests}")
        print(f"成功率: {(self.successful_tests/self.test_count*100 if self.test_count > 0 else 0):.2f}%")
        print(f"平均性能: {avg_perf:.2f} ops/s")
        print(f"最高性能: {max(ops_values):.2f} ops/s")
        print(f"最低性能: {min(ops_values):.2f} ops/s")
        
        # 温度统计
        temp_stats = self.temp_monitor.get_statistics()
        if temp_stats and temp_stats['count'] > 0:
            print(f"\n温度统计:")
            print(f"  平均温度: {temp_stats['average']:.1f}°C")
            print(f"  最高温度: {temp_stats['maximum']:.1f}°C")
            print(f"  最低温度: {temp_stats['minimum']:.1f}°C")
        
        print(f"\n输出目录: {self.output_dir}")
        print("="*50)
    
    def save_summary(self):
        """保存测试摘要"""
        if not self.config.output.save_summary:
            return
        
        summary = {
            "测试时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "测试配置": {
                "连接类型": self.config.connection_type,
                "测试时长": f"{self.config.test.duration_minutes or '无限制'}分钟",
                "测试间隔": f"{self.config.test.interval_seconds}秒",
                "最大测试数": self.config.test.max_tests
            },
            "测试结果": {
                "总测试次数": self.test_count,
                "成功次数": self.successful_tests,
                "失败次数": self.failed_tests,
                "成功率": f"{(self.successful_tests/self.test_count*100 if self.test_count > 0 else 0):.2f}%"
            }
        }
        
        if self.test_results:
            ops_values = [r.bogo_ops_per_sec for r in self.test_results]
            summary["性能统计"] = {
                "平均性能": f"{sum(ops_values)/len(ops_values):.2f} ops/s",
                "最高性能": f"{max(ops_values):.2f} ops/s",
                "最低性能": f"{min(ops_values):.2f} ops/s"
            }
        
        # 添加温度统计
        temp_stats = self.temp_monitor.get_statistics()
        if temp_stats:
            summary["温度统计"] = temp_stats  # 已经是dict了
        
        # 保存温度摘要
        self.temp_monitor.save_summary()
        
        # 保存总摘要
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"测试摘要已保存: {summary_file}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='CPU压力测试监控系统 V3.0')
    parser.add_argument('--config', '-c', default='config.json',
                       help='配置文件路径 (默认: config.json)')
    parser.add_argument('--generate-config', action='store_true',
                       help='生成默认配置文件')
    
    args = parser.parse_args()
    
    # 生成默认配置
    if args.generate_config:
        config = Config()
        config.save(args.config)
        print(f"默认配置文件已生成: {args.config}")
        print("请编辑配置文件后重新运行程序")
        return
    
    # 加载配置
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"配置文件不存在: {args.config}")
        print("使用 --generate-config 生成默认配置文件")
        return
    
    config = Config.from_file(args.config)
    
    # 验证配置
    if not config.validate():
        print("配置文件验证失败，请检查配置")
        return
    
    print("\n" + "="*50)
    print("CPU压力测试监控系统 V3.0")
    print("="*50)
    print(f"配置文件: {args.config}")
    print(f"连接类型: {config.connection_type}")
    print(f"输出目录: {config.output.get_output_dir()}")
    print("="*50)
    
    # 创建连接
    try:
        connection = ConnectionFactory.create_connection(
            config.connection_type,
            **config.get_connection_params()
        )
    except Exception as e:
        logger.error(f"创建连接失败: {e}")
        return
    
    # 建立连接
    try:
        if not connection.connect():
            print("连接失败")
            return
    except Exception as e:
        logger.error(f"连接失败: {e}")
        return
    
    print("[OK] 连接成功")
    
    # 创建监控器
    monitor = StressTestMonitor(config, connection)
    
    try:
        # 启动监控
        if not monitor.start():
            print("启动监控失败")
            return
        
        # 环境准备
        if config.test.enter_docker:
            if not monitor.enter_docker_if_needed():
                print("\n请手动进入Docker容器后重试")
                return
        
        if config.test.install_stress_ng:
            if not monitor.check_and_install_stress_ng():
                print("\n请手动安装stress-ng后重试")
                return
        
        # 运行测试
        monitor.run_continuous_tests()
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        logger.error(f"程序异常: {e}", exc_info=True)
    finally:
        # 停止监控
        monitor.stop()
        
        # 生成报告
        monitor.generate_report()
        
        # 断开连接
        connection.disconnect()
        
        print("\n程序结束")


if __name__ == "__main__":
    main()