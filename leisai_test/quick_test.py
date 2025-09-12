"""
雷赛L7伺服驱动器快速测试脚本（精简版）
直接使用 L7Driver 连接并读取关键状态
"""

import logging
from leisai_l7_driver.leisai.core.driver import L7Driver

logger = logging.getLogger(__name__)


def main():
    """快速测试主函数"""
    print("\n雷赛L7伺服驱动器 - 快速测试")
    print("="*40 + "\n")
    
    # 直接连接驱动器（如需更改串口请修改此处）
    port = 'COM42'
    driver = L7Driver(port)
    if not driver.connect():
        print(f"❌ 无法连接到驱动器 {port}")
        return
    print(f"✓ 成功连接到 {port}")

    # 读取并显示状态
    print("\n当前状态:")
    print("-"*40)

    try:
        # 清除报警
        driver.reset_alarm()
        print("✓ 报警已清除")

        # 读取基本信息
        position = driver.get_position()
        command_position = driver.get_command_position()
        motor_cmd_pos = driver.read_parameter('motor_position_cmd_unit')
        cmd_pos = driver.read_parameter('command_position')
        speed = driver.get_speed()
        torque = driver.get_torque()
        temp_raw = driver.read_parameter('driver_temperature')
        temp = temp_raw if temp_raw is not None else None

        print(f"电机位置: {position} 编码器单位")
        print(f"指令位置: {command_position} 编码器单位")
        print(f"电机位置: {motor_cmd_pos} 指令单位")
        print(f"指令位置: {cmd_pos} 指令单位")
        print(f"速度: {speed} RPM")
        print(f"转矩: {torque} %")
        if temp is not None:
            print(f"温度: {temp} °C")
        else:
            print("温度: 读取失败")

        # 检查伺服状态
        if driver.is_servo_on():
            print("伺服状态: 已使能")
        else:
            print("伺服状态: 未使能")

            # 询问是否进行JOG测试
            response = input("\n是否进行JOG运动测试? (y/n): ")
            if response.lower() == 'y':
                try:
                    import time
                    print("开始JOG运动 (100 RPM, 3秒)...")
                    driver.jog(100, True)
                    time.sleep(3)
                    driver.stop_jog()
                    print("✓ JOG测试完成")
                except Exception as e:
                    print(f"JOG测试失败: {e}")

        print("\n✓ 快速测试完成")

    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
    finally:
        driver.disconnect()


if __name__ == "__main__":
    main()