"""
极简PR触发工具（循环PR0→PR1→PR2）
 - 不做报警检测/模式切换/冗余校验
 - 直接通过寄存器0x6002触发PR与急停（等同串口调试助手帧）

运行：
  自动循环触发 PR0 -> PR1 -> PR2 -> 重复
  任意键按下：立即发送急停并退出程序
"""

import time
import sys
import msvcrt  # Windows 控制台按键检测
from leisai_l7_driver.leisai.core.driver import L7Driver


def main():
    print("\n雷赛L7驱动器 - PR0/PR1/PR2 循环触发")
    print("=" * 40)
    print("提示：按任意键急停并退出")

    # 简单连接（默认COM42，如需修改可直接改这里或用L7TestBase去扫描）
    port = 'COM42'
    driver = L7Driver(port)
    if not driver.connect():
        print(f"✗ 无法连接 {port}")
        return
    print(f"✓ 已连接 {port}")

    try:
        # 先尝试伺服使能
        try:
            driver.servo_on()
        except Exception:
            pass
        
        sequence = [0, 1]
        idx = 0
        while True:
            # 检测按键：任意键急停退出
            if msvcrt.kbhit():
                _ = msvcrt.getch()
                print("\n检测到按键，执行急停并退出...")
                try:
                    driver.stop_pr_motion()
                except Exception:
                    pass
                break

            pr = sequence[idx % len(sequence)]
            ok = driver.trigger_pr(pr)
            
            if ok:
                # 电机当前位置（指令单位）
                motor_cmd_pos = driver.read_parameter('motor_position_cmd_unit')
                motor_cmd_str = f"{motor_cmd_pos}" if motor_cmd_pos is not None else "读取失败"

                # 读取PR路径配置的目标位置（指令单位），按文档：
                # PR0 -> 0x6201/0x6202，PR1 -> 0x6209/0x620A
                pr_target = driver.get_pr_configured_position(pr)
                pr_target_str = f"{pr_target}" if pr_target is not None else "读取失败"

                # 读取当前控制操作码（0x6002）
                ctrl = driver.get_control_operation()
                ctrl_str = f"0x{int(ctrl):04X}" if ctrl is not None else "读取失败"

                print(f"触发PR{pr}: 成功 | 电机位置(指令单位): {motor_cmd_str} | PR配置目标(指令单位): {pr_target_str} | 控制操作: {ctrl_str}")
            else:
                print(f"触发PR{pr}: 失败")
            
            idx += 1

            # 小延时，避免过快触发
            time.sleep(0.5)
    finally:
        try:
            driver.servo_off()
        except Exception:
            pass
        driver.disconnect()
        print("已断开连接")


if __name__ == '__main__':
    main()


