"""
雷赛L7伺服驱动器PR模式循环测试
循环触发PR0、PR1、PR2、PR3位置运动
(PR参数已通过上位机配置)
"""

import time
import logging
from test_framework import L7TestBase

logger = logging.getLogger(__name__)


class PRCycleTest:
    """PR模式循环测试类"""
    
    def __init__(self):
        self.test_base = L7TestBase()
        
    def trigger_pr(self, driver, pr_num):
        """触发指定PR运动（直接写0x6002，等价于串口帧）"""
        print(f"\n触发 PR{pr_num}...")
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
    """主函数（简化版）"""
    print("\n雷赛L7伺服驱动器 - PR模式循环测试")
    print("=" * 50)
    print("注意: PR参数需要预先通过上位机配置")
    
    test = PRCycleTest()
    with test.test_base.connect_driver() as driver:
        if not driver:
            print("✗ 无法连接到驱动器")
            return
        print(f"✓ 成功连接到 {test.test_base.connected_port}")
        
        # 直接尝试使能并进入简洁菜单/循环
        try:
            driver.servo_on()
            time.sleep(0.3)
            print("\n操作: [0]PR0  [1]PR1  [2]PR2  [3]PR3  [C]循环  [E]急停  [Q]退出")
            while True:
                sel = input("> ").strip().lower()
                if sel in ('0', '1', '2', '3'):
                    test.trigger_pr(driver, int(sel))
                elif sel == 'c':
                    test.run_cycle(driver, cycles=1, delay=1.0)
                elif sel == 'e':
                    print("急停...")
                    driver.stop_pr_motion()
                elif sel == 'q':
                    break
                else:
                    print("无效选择")
        finally:
            print("\n禁用伺服...")
            try:
                driver.servo_off()
            except Exception:
                pass
            print("✓ 伺服已禁用")
    print("\n测试结束")


if __name__ == "__main__":
    main()