"""
测试PR模式修复
验证代码修复是否有效
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'leisai_l7_driver'))

def test_imports():
    """测试导入是否正常"""
    try:
        from leisai_l7_driver.leisai.core.constants import ControlMode
        print("✓ 成功导入 ControlMode")
        
        # 检查PR模式是否已添加
        if hasattr(ControlMode, 'PR'):
            print(f"✓ PR模式已添加: {ControlMode.PR} = {ControlMode.PR.value}")
        else:
            print("✗ PR模式未找到")
            return False
            
        from leisai_l7_driver.leisai import L7Driver
        print("✓ 成功导入 L7Driver")
        
        # 检查PR方法是否已添加
        pr_methods = ['trigger_pr', 'set_pr_path', 'stop_pr_motion', 
                     'get_current_pr_path', 'get_pr_position', 'is_pr_complete']
        
        for method in pr_methods:
            if hasattr(L7Driver, method):
                print(f"✓ 方法 {method} 已添加")
            else:
                print(f"✗ 方法 {method} 未找到")
                return False
                
        return True
        
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_control_mode():
    """测试控制模式设置"""
    try:
        from leisai_l7_driver.leisai.core.constants import ControlMode
        
        # 测试PR模式
        pr_mode = ControlMode.PR
        print(f"✓ PR模式值: {pr_mode.value}")
        
        # 测试所有模式
        modes = [ControlMode.POSITION, ControlMode.SPEED, ControlMode.TORQUE, ControlMode.PR]
        print("✓ 所有控制模式:")
        for mode in modes:
            print(f"  - {mode.name}: {mode.value}")
            
        return True
        
    except Exception as e:
        print(f"✗ 控制模式测试失败: {e}")
        return False

def test_driver_creation():
    """测试驱动器创建（不连接）"""
    try:
        from leisai_l7_driver.leisai import L7Driver
        
        # 创建驱动器实例（不连接）
        driver = L7Driver('COM99')  # 使用不存在的端口
        
        # 检查PR方法是否存在
        assert hasattr(driver, 'trigger_pr'), "trigger_pr方法不存在"
        assert hasattr(driver, 'set_pr_path'), "set_pr_path方法不存在"
        assert hasattr(driver, 'stop_pr_motion'), "stop_pr_motion方法不存在"
        
        print("✓ 驱动器创建成功，PR方法已添加")
        return True
        
    except Exception as e:
        print(f"✗ 驱动器创建测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("雷赛L7驱动器PR模式修复测试")
    print("=" * 40)
    
    tests = [
        ("导入测试", test_imports),
        ("控制模式测试", test_control_mode),
        ("驱动器创建测试", test_driver_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 20)
        if test_func():
            passed += 1
            print(f"✓ {test_name} 通过")
        else:
            print(f"✗ {test_name} 失败")
    
    print(f"\n测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！PR模式修复成功！")
        return True
    else:
        print("❌ 部分测试失败，需要进一步修复")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)