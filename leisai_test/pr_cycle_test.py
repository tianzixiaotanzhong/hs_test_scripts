"""
雷赛L7伺服驱动器PR模式循环测试
循环触发PR0、PR1、PR2、PR3位置运动
(PR参数已通过上位机配置)
"""

import time
import logging
from test_framework import L7TestBase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PRCycleTest:
    """PR模式循环测试类"""
    
    def __init__(self):
        self.test_base = L7TestBase()
        
    def trigger_pr(self, driver, pr_num):
        """触发指定PR运动"""
        print(f"\n触发 PR{pr_num}...")
        
        # 触发PR运动
        success = driver.trigger_pr(pr_num)
        if not success:
            print(f"✗ PR{pr_num} 触发失败")
            return False
            
        print(f"✓ PR{pr_num} 已触发")
        
        # 等待运动开始
        time.sleep(0.1)
        
        # 监控运动状态
        start_time = time.time()
        timeout = 30  # 30秒超时
        last_position = None
        
        while time.time() - start_time < timeout:
            # 获取当前状态
            position = driver.get_position()
            speed = driver.get_speed()
            
            # 检查是否到达目标位置（速度为0且位置不再变化）
            if speed == 0 and last_position is not None and position == last_position:
                print(f"✓ PR{pr_num} 完成 - 当前位置: {position} 脉冲")
                return True
                
            # 显示当前状态
            print(f"  位置: {position:8d} 脉冲 | 速度: {speed:4d} RPM", end='\r')
            
            last_position = position
            time.sleep(0.1)
            
        print(f"\n✗ PR{pr_num} 运动超时")
        return False
        
    def run_cycle(self, driver, cycles=1, delay=1.0):
        """运行PR循环"""
        print(f"\n开始PR循环测试 (循环次数: {cycles})")
        print("=" * 50)
        
        for cycle in range(cycles):
            print(f"\n===== 第 {cycle + 1}/{cycles} 轮循环 =====")
            
            # 循环触发PR0到PR3
            for pr_num in range(4):
                success = self.trigger_pr(driver, pr_num)
                
                if not success:
                    print(f"\n✗ PR{pr_num} 执行失败，停止循环")
                    return False
                    
                # 延迟后继续
                if pr_num < 3 or cycle < cycles - 1:
                    print(f"等待 {delay:.1f} 秒...")
                    time.sleep(delay)
                    
        print("\n✓ PR循环测试完成")
        return True
        
    def run_continuous_cycle(self, driver):
        """连续循环模式（按Ctrl+C停止）"""
        print("\n开始连续PR循环测试 (按Ctrl+C停止)")
        print("=" * 50)
        
        cycle_count = 0
        try:
            while True:
                cycle_count += 1
                print(f"\n===== 第 {cycle_count} 轮循环 =====")
                
                # 循环触发PR0到PR3
                for pr_num in range(4):
                    success = self.trigger_pr(driver, pr_num)
                    
                    if not success:
                        print(f"\n✗ PR{pr_num} 执行失败")
                        # 询问是否继续
                        response = input("是否继续循环? (y/n): ")
                        if response.lower() != 'y':
                            return
                            
                    # 短暂延迟
                    time.sleep(0.5)
                    
        except KeyboardInterrupt:
            print(f"\n\n用户中断 - 完成了 {cycle_count} 轮循环")
            

def main():
    """主函数"""
    print("\n雷赛L7伺服驱动器 - PR模式循环测试")
    print("=" * 50)
    print("注意: PR参数需要预先通过上位机配置")
    
    # 创建测试实例
    test = PRCycleTest()
    
    # 连接驱动器
    with test.test_base.connect_driver() as driver:
        if not driver:
            print("✗ 无法连接到驱动器")
            return
            
        print(f"✓ 成功连接到 {test.test_base.connected_port}")
        
        try:
            # 清除报警
            driver.reset_alarm()
            print("✓ 报警已清除")
            
            # 切换到PR模式
            print("\n切换到PR模式...")
            success = driver.set_control_mode('pr')
            if not success:
                print("✗ 无法切换到PR模式")
                return
            print("✓ 已切换到PR模式")
            
            # 使能伺服
            print("\n使能伺服...")
            driver.servo_on()
            if not driver.is_servo_on():
                print("✗ 伺服使能失败")
                return
            print("✓ 伺服已使能")
            
            # 等待稳定
            time.sleep(0.5)
            
            # 选择测试模式
            print("\n选择测试模式:")
            print("1. 单次循环 (PR0→PR1→PR2→PR3)")
            print("2. 多次循环 (指定循环次数)")
            print("3. 连续循环 (按Ctrl+C停止)")
            
            choice = input("\n请选择 (1/2/3): ")
            
            if choice == '1':
                # 单次循环
                test.run_cycle(driver, cycles=1, delay=1.0)
                
            elif choice == '2':
                # 多次循环
                try:
                    cycles = int(input("请输入循环次数: "))
                    delay = float(input("请输入每个PR之间的延迟(秒): "))
                    test.run_cycle(driver, cycles=cycles, delay=delay)
                except ValueError:
                    print("✗ 输入无效")
                    
            elif choice == '3':
                # 连续循环
                test.run_continuous_cycle(driver)
                
            else:
                print("✗ 无效的选择")
                
        except Exception as e:
            logger.error(f"测试过程中出错: {e}")
            print(f"\n✗ 测试过程中出错: {e}")
            
        finally:
            # 禁用伺服
            print("\n禁用伺服...")
            driver.servo_off()
            print("✓ 伺服已禁用")
            
    print("\n测试结束")


if __name__ == "__main__":
    main()