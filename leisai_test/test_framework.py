"""
雷赛L7伺服驱动器测试框架
提供统一的测试基类和工具函数
"""

import logging
import os
import time
import json
from typing import Optional, List, Dict, Any, Callable
from contextlib import contextmanager
from datetime import datetime
from leisai_l7_driver.leisai import L7Driver
from leisai_l7_driver.leisai.core.constants import ControlMode, ServoStatus

# 配置日志：统一写入 logs 目录
_LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs') if '__file__' in globals() else 'logs'
os.makedirs(_LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(_LOG_DIR, f'test_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class L7TestBase:
    """L7驱动器测试基类"""
    
    # 默认测试配置
    DEFAULT_CONFIG = {
        'com_ports': ['COM42', 'COM3', 'COM4', 'COM5'],
        'baudrate': 38400,
        'slave_id': 1,
        'timeout': 1.0,
        'retry_count': 3,
        'retry_delay': 0.5
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化测试类
        
        Parameters
        ----------
        config : dict, optional
            测试配置，如果不提供则使用默认配置
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.driver: Optional[L7Driver] = None
        self.connected_port: Optional[str] = None
        self.test_results = []
        
    @contextmanager
    def connect_driver(self):
        """
        上下文管理器，自动连接和断开驱动器
        
        Yields
        ------
        L7Driver
            已连接的驱动器实例
        """
        try:
            if self._connect():
                yield self.driver
            else:
                yield None
        finally:
            self._disconnect()
    
    def _connect(self) -> bool:
        """尝试连接到驱动器"""
        for port in self.config['com_ports']:
            try:
                logger.info(f"尝试连接 {port}...")
                self.driver = L7Driver(
                    port,
                    slave_id=self.config['slave_id'],
                    baudrate=self.config['baudrate'],
                    timeout=self.config['timeout']
                )
                self.driver.connect()
                self.connected_port = port
                logger.info(f"成功连接到 {port}")
                return True
            except Exception as e:
                logger.warning(f"无法连接 {port}: {e}")
                if self.driver:
                    try:
                        self.driver.disconnect()
                    except:
                        pass
                self.driver = None
                time.sleep(self.config['retry_delay'])
        
        logger.error("无法连接到任何COM端口")
        return False
    
    def _disconnect(self):
        """断开驱动器连接"""
        if self.driver:
            try:
                # 确保伺服关闭
                self.driver.servo_off()
            except:
                pass
            
            try:
                self.driver.disconnect()
                logger.info(f"已断开与 {self.connected_port} 的连接")
            except Exception as e:
                logger.error(f"断开连接时出错: {e}")
            finally:
                self.driver = None
                self.connected_port = None
    
    def retry_on_fail(self, func: Callable, *args, **kwargs) -> Any:
        """
        重试机制装饰器
        
        Parameters
        ----------
        func : callable
            要执行的函数
        args : tuple
            函数参数
        kwargs : dict
            函数关键字参数
            
        Returns
        -------
        Any
            函数返回值
        """
        last_error = None
        for attempt in range(self.config['retry_count']):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(f"第 {attempt + 1} 次尝试失败: {e}")
                if attempt < self.config['retry_count'] - 1:
                    time.sleep(self.config['retry_delay'])
        
        raise last_error
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """
        记录测试结果
        
        Parameters
        ----------
        test_name : str
            测试名称
        success : bool
            测试是否成功
        details : str
            测试详情
        """
        result = {
            'test': test_name,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        self.test_results.append(result)
        
        if success:
            logger.info(f"✓ {test_name}: 成功 {details}")
        else:
            logger.error(f"✗ {test_name}: 失败 {details}")
    
    def save_test_results(self, filename: Optional[str] = None):
        """
        保存测试结果到JSON文件
        
        Parameters
        ----------
        filename : str, optional
            文件名，如果不提供则使用时间戳
        """
        if not filename:
            filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"测试结果已保存到 {filename}")
    
    def read_status(self) -> Dict[str, Any]:
        """
        读取驱动器完整状态
        
        Returns
        -------
        dict
            包含各种状态信息的字典
        """
        status = {}
        
        if not self.driver:
            logger.error("驱动器未连接")
            return status
        
        try:
            # 基本状态
            status['position'] = self.driver.get_position()
            status['speed'] = self.driver.get_speed()
            status['torque'] = self.driver.get_torque()
            
            # 伺服状态
            status['servo_enabled'] = self.driver.is_servo_on()
            status['control_mode'] = self.driver.get_control_mode()
            
            # 报警信息
            alarm_code = self.driver.get_alarm_code()
            status['alarm_code'] = alarm_code
            status['alarm_description'] = self.driver.get_alarm_description(alarm_code) if alarm_code else "无报警"
            
            # 温度
            status['temperature'] = self.driver.get_temperature()
            
            # IO状态
            status['digital_inputs'] = self.driver.get_digital_inputs()
            status['digital_outputs'] = self.driver.get_digital_outputs()
            
        except Exception as e:
            logger.error(f"读取状态时出错: {e}")
        
        return status
    
    def print_status(self, status: Optional[Dict[str, Any]] = None):
        """
        打印驱动器状态
        
        Parameters
        ----------
        status : dict, optional
            状态字典，如果不提供则自动读取
        """
        if status is None:
            status = self.read_status()
        
        print("\n" + "="*50)
        print("驱动器状态")
        print("="*50)
        
        for key, value in status.items():
            if key == 'alarm_code' and value:
                print(f"{key:20}: 0x{value:04X}")
            else:
                print(f"{key:20}: {value}")
        
        print("="*50 + "\n")


class TestSuite:
    """测试套件管理器"""
    
    def __init__(self):
        self.tests = []
        self.results = []
        
    def add_test(self, test_func: Callable, name: str = None):
        """
        添加测试函数
        
        Parameters
        ----------
        test_func : callable
            测试函数
        name : str, optional
            测试名称
        """
        test_name = name or test_func.__name__
        self.tests.append((test_name, test_func))
    
    def run(self, test_base: L7TestBase):
        """
        运行所有测试
        
        Parameters
        ----------
        test_base : L7TestBase
            测试基类实例
        """
        logger.info(f"开始执行测试套件，共 {len(self.tests)} 个测试")
        
        with test_base.connect_driver():
            for test_name, test_func in self.tests:
                logger.info(f"\n{'='*20} 执行测试: {test_name} {'='*20}")
                try:
                    test_func(test_base)
                    test_base.log_test_result(test_name, True)
                except Exception as e:
                    logger.error(f"测试失败: {e}")
                    test_base.log_test_result(test_name, False, str(e))
                
                # 测试间隔
                time.sleep(0.5)
        
        # 输出测试总结
        self._print_summary(test_base)
        
        # 保存结果
        test_base.save_test_results()
    
    def _print_summary(self, test_base: L7TestBase):
        """打印测试总结"""
        total = len(test_base.test_results)
        passed = sum(1 for r in test_base.test_results if r['success'])
        failed = total - passed
        
        print("\n" + "="*50)
        print("测试总结")
        print("="*50)
        print(f"总计: {total} 个测试")
        print(f"通过: {passed} 个")
        print(f"失败: {failed} 个")
        print(f"通过率: {passed/total*100:.1f}%")
        print("="*50 + "\n")


# 常用测试函数
def test_connection(test_base: L7TestBase):
    """测试连接"""
    assert test_base.driver is not None, "驱动器未连接"
    assert test_base.driver._connected, "连接状态异常"


def test_read_position(test_base: L7TestBase):
    """测试读取位置"""
    position = test_base.driver.get_position()
    logger.info(f"当前位置: {position} 脉冲")
    assert position is not None, "无法读取位置"


def test_read_speed(test_base: L7TestBase):
    """测试读取速度"""
    speed = test_base.driver.get_speed()
    logger.info(f"当前速度: {speed} RPM")
    assert speed is not None, "无法读取速度"


def test_servo_enable(test_base: L7TestBase):
    """测试伺服使能"""
    # 清除报警
    test_base.driver.reset_alarm()
    time.sleep(0.5)
    
    # 使能伺服
    test_base.driver.servo_on()
    time.sleep(0.5)
    
    assert test_base.driver.is_servo_on(), "伺服使能失败"
    logger.info("伺服使能成功")
    
    # 禁用伺服
    test_base.driver.servo_off()
    time.sleep(0.5)
    
    assert not test_base.driver.is_servo_on(), "伺服禁用失败"
    logger.info("伺服禁用成功")


def test_alarm_reset(test_base: L7TestBase):
    """测试报警复位"""
    success = test_base.driver.reset_alarm()
    assert success, "报警复位失败"
    
    alarm_code = test_base.driver.get_alarm_code()
    assert alarm_code == 0, f"仍有报警: 0x{alarm_code:04X}"
    logger.info("报警复位成功")