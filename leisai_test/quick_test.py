"""
雷赛L7伺服驱动器快速测试脚本
用于快速验证连接和基本功能
"""

from test_framework import L7TestBase
import logging

logger = logging.getLogger(__name__)


def main():
    """快速测试主函数"""
    print("\n雷赛L7伺服驱动器 - 快速测试")
    print("="*40 + "\n")
    
    # 创建测试实例
    test = L7TestBase()
    
    # 使用上下文管理器自动连接和断开
    with test.connect_driver() as driver:
        if not driver:
            print("❌ 无法连接到驱动器")
            return
        
        print(f"✓ 成功连接到 {test.connected_port}")
        
        # 读取并显示状态
        print("\n当前状态:")
        print("-"*40)
        
        try:
            # 清除报警
            driver.reset_alarm()
            print("✓ 报警已清除")
            
            # 读取基本信息
            position = driver.get_position()
            speed = driver.get_speed()
            torque = driver.get_torque()
            temp_raw = driver.read_parameter('driver_temperature')
            temp = temp_raw / 10.0 if temp_raw is not None else None
            
            print(f"位置: {position} 脉冲")
            print(f"速度: {speed} RPM")
            print(f"转矩: {torque} %")
            if temp is not None:
                print(f"温度: {temp:.1f} °C")
            else:
                print("温度: 读取失败")
            
            # 检查伺服状态
            if driver.is_servo_on():
                print("伺服状态: 已使能")
            else:
                print("伺服状态: 未使能")
                
                # 询问是否使能
                response = input("\n是否使能伺服? (y/n): ")
                if response.lower() == 'y':
                    driver.servo_on()
                    print("✓ 伺服已使能")
                    
                    # 询问是否进行JOG测试
                    response = input("是否进行JOG运动测试? (y/n): ")
                    if response.lower() == 'y':
                        import time
                        print("开始JOG运动 (100 RPM, 3秒)...")
                        driver.jog(100, True)
                        time.sleep(3)
                        driver.stop_jog()
                        print("✓ JOG测试完成")
                    
                    # 禁用伺服
                    driver.servo_off()
                    print("✓ 伺服已禁用")
            
            print("\n✓ 快速测试完成")
            
        except Exception as e:
            print(f"\n❌ 测试过程中出错: {e}")


if __name__ == "__main__":
    main()