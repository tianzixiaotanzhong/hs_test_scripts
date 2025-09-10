"""
雷赛L7伺服驱动器综合测试脚本
整合所有测试功能
"""

import time
import logging
from test_framework import L7TestBase, TestSuite, test_connection, test_read_position, test_read_speed, test_servo_enable, test_alarm_reset

logger = logging.getLogger(__name__)


# 扩展测试函数
def test_parameter_read(test_base: L7TestBase):
    """测试参数读取"""
    params_to_test = [
        ('encoder_position', '编码器位置'),
        ('motor_position_cmd_unit', '电机位置(指令单位)'),
        ('command_position', '指令位置'),
        ('position_error', '位置误差'),
        ('pr_current_position', 'PR当前位置'),
    ]
    
    for param_name, desc in params_to_test:
        try:
            value = test_base.driver.read_parameter(param_name)
            logger.info(f"{desc}: {value}")
        except Exception as e:
            logger.warning(f"读取 {param_name} 失败: {e}")


def test_jog_motion(test_base: L7TestBase):
    """测试JOG运动"""
    # 确保伺服使能
    if not test_base.driver.is_servo_on():
        test_base.driver.reset_alarm()
        time.sleep(0.5)
        test_base.driver.servo_on()
        time.sleep(0.5)
    
    # 正向JOG
    logger.info("开始正向JOG运动 (100 RPM)")
    test_base.driver.jog(100, True)
    time.sleep(2)
    
    speed = test_base.driver.get_speed()
    logger.info(f"JOG运动中速度: {speed} RPM")
    
    # 停止JOG
    test_base.driver.stop_jog()
    logger.info("停止JOG运动")
    time.sleep(1)
    
    # 反向JOG
    logger.info("开始反向JOG运动 (-100 RPM)")
    test_base.driver.jog(100, False)
    time.sleep(2)
    
    speed = test_base.driver.get_speed()
    logger.info(f"JOG运动中速度: {speed} RPM")
    
    # 停止JOG
    test_base.driver.stop_jog()
    logger.info("停止JOG运动")
    time.sleep(1)


def test_position_control(test_base: L7TestBase):
    """测试位置控制"""
    # 确保伺服使能
    if not test_base.driver.is_servo_on():
        test_base.driver.reset_alarm()
        time.sleep(0.5)
        test_base.driver.servo_on()
        time.sleep(0.5)
    
    # 记录初始位置
    initial_pos = test_base.driver.get_position()
    logger.info(f"初始位置: {initial_pos} 脉冲")
    
    # 相对移动测试
    logger.info("执行相对移动 +10000 脉冲")
    test_base.driver.move_relative(10000, speed=500)
    time.sleep(3)
    
    current_pos = test_base.driver.get_position()
    logger.info(f"移动后位置: {current_pos} 脉冲")
    
    # 回到初始位置
    logger.info("返回初始位置")
    test_base.driver.move_absolute(initial_pos, speed=500)
    time.sleep(3)
    
    final_pos = test_base.driver.get_position()
    logger.info(f"最终位置: {final_pos} 脉冲")


def test_io_status(test_base: L7TestBase):
    """测试IO状态读取"""
    try:
        # 读取数字输入
        di_status = test_base.driver.get_digital_inputs()
        logger.info(f"数字输入状态: {bin(di_status)} ({di_status})")
        
        # 读取数字输出
        do_status = test_base.driver.get_digital_outputs()
        logger.info(f"数字输出状态: {bin(do_status)} ({do_status})")
        
    except Exception as e:
        logger.warning(f"读取IO状态失败: {e}")


def test_temperature(test_base: L7TestBase):
    """测试温度读取"""
    try:
        temp = test_base.driver.get_temperature()
        logger.info(f"驱动器温度: {temp}°C")
        
        # 温度警告检查
        if temp > 70:
            logger.warning(f"温度过高警告: {temp}°C")
        elif temp > 50:
            logger.info(f"温度正常偏高: {temp}°C")
        else:
            logger.info(f"温度正常: {temp}°C")
            
    except Exception as e:
        logger.warning(f"读取温度失败: {e}")


def test_control_mode(test_base: L7TestBase):
    """测试控制模式切换"""
    from leisai_l7_driver.leisai.core.constants import ControlMode
    
    modes = [
        (ControlMode.POSITION, "位置控制"),
        (ControlMode.SPEED, "速度控制"),
        (ControlMode.TORQUE, "转矩控制"),
    ]
    
    for mode, desc in modes:
        try:
            logger.info(f"切换到{desc}模式")
            test_base.driver.set_control_mode(mode)
            time.sleep(0.5)
            
            current_mode = test_base.driver.get_control_mode()
            assert current_mode == mode, f"模式切换失败，期望{mode}，实际{current_mode}"
            logger.info(f"成功切换到{desc}模式")
            
        except Exception as e:
            logger.warning(f"切换到{desc}模式失败: {e}")
    
    # 恢复到位置控制模式
    test_base.driver.set_control_mode(ControlMode.POSITION)


def test_continuous_monitoring(test_base: L7TestBase):
    """连续监控测试（读取10次状态）"""
    logger.info("开始连续监控（10次）")
    
    for i in range(10):
        logger.info(f"\n--- 第 {i+1} 次读取 ---")
        status = test_base.read_status()
        
        # 只打印关键信息
        logger.info(f"位置: {status.get('position', 'N/A')} 脉冲")
        logger.info(f"速度: {status.get('speed', 'N/A')} RPM")
        logger.info(f"转矩: {status.get('torque', 'N/A')} %")
        logger.info(f"温度: {status.get('temperature', 'N/A')} °C")
        
        if status.get('alarm_code'):
            logger.warning(f"报警: {status.get('alarm_description', 'Unknown')}")
        
        time.sleep(0.5)


def run_basic_tests():
    """运行基础测试套件"""
    print("\n" + "="*60)
    print("雷赛L7伺服驱动器 - 基础测试套件")
    print("="*60 + "\n")
    
    # 创建测试基类
    test_base = L7TestBase()
    
    # 创建测试套件
    suite = TestSuite()
    
    # 添加基础测试
    suite.add_test(test_connection, "连接测试")
    suite.add_test(test_read_position, "位置读取测试")
    suite.add_test(test_read_speed, "速度读取测试")
    suite.add_test(test_alarm_reset, "报警复位测试")
    suite.add_test(test_servo_enable, "伺服使能测试")
    suite.add_test(test_parameter_read, "参数读取测试")
    suite.add_test(test_io_status, "IO状态测试")
    suite.add_test(test_temperature, "温度读取测试")
    
    # 运行测试
    suite.run(test_base)


def run_motion_tests():
    """运行运动控制测试套件"""
    print("\n" + "="*60)
    print("雷赛L7伺服驱动器 - 运动控制测试套件")
    print("="*60 + "\n")
    
    # 创建测试基类
    test_base = L7TestBase()
    
    # 创建测试套件
    suite = TestSuite()
    
    # 添加运动测试
    suite.add_test(test_connection, "连接测试")
    suite.add_test(test_alarm_reset, "报警复位测试")
    suite.add_test(test_servo_enable, "伺服使能测试")
    suite.add_test(test_jog_motion, "JOG运动测试")
    suite.add_test(test_position_control, "位置控制测试")
    suite.add_test(test_control_mode, "控制模式切换测试")
    
    # 运行测试
    suite.run(test_base)


def run_monitoring_test():
    """运行监控测试"""
    print("\n" + "="*60)
    print("雷赛L7伺服驱动器 - 连续监控测试")
    print("="*60 + "\n")
    
    # 创建测试基类
    test_base = L7TestBase()
    
    # 创建测试套件
    suite = TestSuite()
    
    # 添加监控测试
    suite.add_test(test_connection, "连接测试")
    suite.add_test(test_continuous_monitoring, "连续监控测试")
    
    # 运行测试
    suite.run(test_base)


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("雷赛L7伺服驱动器 - 完整测试套件")
    print("="*60 + "\n")
    
    # 创建测试基类
    test_base = L7TestBase()
    
    # 创建测试套件
    suite = TestSuite()
    
    # 添加所有测试
    suite.add_test(test_connection, "连接测试")
    suite.add_test(test_read_position, "位置读取测试")
    suite.add_test(test_read_speed, "速度读取测试")
    suite.add_test(test_alarm_reset, "报警复位测试")
    suite.add_test(test_servo_enable, "伺服使能测试")
    suite.add_test(test_parameter_read, "参数读取测试")
    suite.add_test(test_io_status, "IO状态测试")
    suite.add_test(test_temperature, "温度读取测试")
    suite.add_test(test_jog_motion, "JOG运动测试")
    suite.add_test(test_position_control, "位置控制测试")
    suite.add_test(test_control_mode, "控制模式切换测试")
    suite.add_test(test_continuous_monitoring, "连续监控测试")
    
    # 运行测试
    suite.run(test_base)


if __name__ == "__main__":
    import sys
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "basic":
            run_basic_tests()
        elif test_type == "motion":
            run_motion_tests()
        elif test_type == "monitor":
            run_monitoring_test()
        elif test_type == "all":
            run_all_tests()
        else:
            print("用法:")
            print("  python test_all.py basic    # 运行基础测试")
            print("  python test_all.py motion   # 运行运动控制测试")
            print("  python test_all.py monitor  # 运行监控测试")
            print("  python test_all.py all      # 运行所有测试")
            print("  python test_all.py          # 运行基础测试（默认）")
    else:
        # 默认运行基础测试
        run_basic_tests()