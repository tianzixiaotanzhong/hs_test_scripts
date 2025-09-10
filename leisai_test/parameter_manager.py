"""
雷赛L7伺服驱动器参数管理工具
用于备份、恢复和管理驱动器参数
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from test_framework import L7TestBase
import logging

logger = logging.getLogger(__name__)


class ParameterManager(L7TestBase):
    """参数管理器"""
    
    # 重要参数列表
    IMPORTANT_PARAMS = [
        # 基本参数
        'control_mode',
        'encoder_resolution',
        'gear_ratio_numerator',
        'gear_ratio_denominator',
        
        # 位置控制参数
        'position_loop_gain',
        'position_feedforward_gain',
        'position_error_limit',
        
        # 速度控制参数
        'speed_loop_gain',
        'speed_integral_time',
        'speed_feedforward_gain',
        
        # 转矩控制参数
        'torque_limit',
        'torque_filter_time',
        
        # 加减速参数
        'acceleration_time',
        'deceleration_time',
        'jerk_time',
        
        # 限位参数
        'forward_limit_position',
        'reverse_limit_position',
        'software_limit_enable',
        
        # 原点参数
        'home_offset',
        'home_speed',
        'home_acceleration',
    ]
    
    def backup_parameters(self, filename: Optional[str] = None) -> str:
        """
        备份驱动器参数
        
        Parameters
        ----------
        filename : str, optional
            备份文件名，如果不提供则使用时间戳
            
        Returns
        -------
        str
            备份文件名
        """
        if not filename:
            filename = f"param_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        params = {}
        
        with self.connect_driver() as driver:
            if not driver:
                raise ConnectionError("无法连接到驱动器")
            
            print(f"开始备份参数...")
            
            # 读取所有重要参数
            for param_name in self.IMPORTANT_PARAMS:
                try:
                    value = driver.read_parameter(param_name)
                    params[param_name] = value
                    print(f"  ✓ {param_name}: {value}")
                except Exception as e:
                    logger.warning(f"无法读取参数 {param_name}: {e}")
                    params[param_name] = None
            
            # 添加元数据
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'port': self.connected_port,
                'parameter_count': len([v for v in params.values() if v is not None])
            }
            
            # 保存到文件
            backup_data = {
                'metadata': metadata,
                'parameters': params
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            print(f"\n✓ 参数已备份到 {filename}")
            print(f"  成功备份 {metadata['parameter_count']} 个参数")
            
            return filename
    
    def restore_parameters(self, filename: str, dry_run: bool = False) -> bool:
        """
        恢复驱动器参数
        
        Parameters
        ----------
        filename : str
            备份文件名
        dry_run : bool
            是否仅模拟恢复（不实际写入）
            
        Returns
        -------
        bool
            恢复是否成功
        """
        # 读取备份文件
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
        except Exception as e:
            logger.error(f"无法读取备份文件: {e}")
            return False
        
        metadata = backup_data.get('metadata', {})
        params = backup_data.get('parameters', {})
        
        print(f"备份信息:")
        print(f"  时间: {metadata.get('timestamp', 'Unknown')}")
        print(f"  端口: {metadata.get('port', 'Unknown')}")
        print(f"  参数数量: {metadata.get('parameter_count', 0)}")
        
        if dry_run:
            print("\n模拟恢复模式 - 不会实际写入参数")
        
        # 确认恢复
        if not dry_run:
            response = input("\n确定要恢复这些参数吗? (yes/no): ")
            if response.lower() != 'yes':
                print("取消恢复")
                return False
        
        success_count = 0
        fail_count = 0
        
        with self.connect_driver() as driver:
            if not driver:
                raise ConnectionError("无法连接到驱动器")
            
            print(f"\n开始恢复参数...")
            
            for param_name, value in params.items():
                if value is None:
                    continue
                
                try:
                    if not dry_run:
                        driver.write_parameter(param_name, value)
                    print(f"  ✓ {param_name}: {value}")
                    success_count += 1
                except Exception as e:
                    logger.error(f"  ✗ {param_name}: {e}")
                    fail_count += 1
            
            if not dry_run and success_count > 0:
                # 保存参数到EEPROM
                try:
                    driver.save_parameters()
                    print("\n✓ 参数已保存到EEPROM")
                except Exception as e:
                    logger.warning(f"保存到EEPROM失败: {e}")
        
        print(f"\n恢复完成:")
        print(f"  成功: {success_count} 个参数")
        print(f"  失败: {fail_count} 个参数")
        
        return fail_count == 0
    
    def compare_parameters(self, filename: str) -> Dict[str, Any]:
        """
        比较当前参数与备份文件
        
        Parameters
        ----------
        filename : str
            备份文件名
            
        Returns
        -------
        dict
            差异报告
        """
        # 读取备份文件
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
        except Exception as e:
            logger.error(f"无法读取备份文件: {e}")
            return {}
        
        backup_params = backup_data.get('parameters', {})
        differences = []
        
        with self.connect_driver() as driver:
            if not driver:
                raise ConnectionError("无法连接到驱动器")
            
            print(f"比较参数差异...")
            
            for param_name, backup_value in backup_params.items():
                if backup_value is None:
                    continue
                
                try:
                    current_value = driver.read_parameter(param_name)
                    
                    if current_value != backup_value:
                        differences.append({
                            'parameter': param_name,
                            'current': current_value,
                            'backup': backup_value
                        })
                        print(f"  ≠ {param_name}: 当前={current_value}, 备份={backup_value}")
                    else:
                        print(f"  = {param_name}: {current_value}")
                        
                except Exception as e:
                    logger.warning(f"无法读取参数 {param_name}: {e}")
        
        print(f"\n差异总结:")
        print(f"  相同参数: {len(backup_params) - len(differences)} 个")
        print(f"  不同参数: {len(differences)} 个")
        
        return {
            'total': len(backup_params),
            'same': len(backup_params) - len(differences),
            'different': len(differences),
            'differences': differences
        }
    
    def reset_to_defaults(self) -> bool:
        """
        恢复出厂默认参数
        
        Returns
        -------
        bool
            是否成功
        """
        response = input("警告：这将恢复所有参数到出厂默认值。确定继续? (yes/no): ")
        if response.lower() != 'yes':
            print("取消操作")
            return False
        
        with self.connect_driver() as driver:
            if not driver:
                raise ConnectionError("无法连接到驱动器")
            
            try:
                # 执行恢复出厂设置命令
                driver.reset_to_factory_defaults()
                print("✓ 已恢复出厂默认参数")
                
                # 重启驱动器
                print("驱动器需要重启以应用更改...")
                driver.reboot()
                
                return True
                
            except Exception as e:
                logger.error(f"恢复出厂设置失败: {e}")
                return False


def main():
    """主函数"""
    import sys
    
    manager = ParameterManager()
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python parameter_manager.py backup [filename]     # 备份参数")
        print("  python parameter_manager.py restore <filename>    # 恢复参数")
        print("  python parameter_manager.py compare <filename>    # 比较参数")
        print("  python parameter_manager.py reset                 # 恢复出厂设置")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "backup":
            filename = sys.argv[2] if len(sys.argv) > 2 else None
            manager.backup_parameters(filename)
            
        elif command == "restore":
            if len(sys.argv) < 3:
                print("请指定备份文件名")
                sys.exit(1)
            manager.restore_parameters(sys.argv[2])
            
        elif command == "compare":
            if len(sys.argv) < 3:
                print("请指定备份文件名")
                sys.exit(1)
            manager.compare_parameters(sys.argv[2])
            
        elif command == "reset":
            manager.reset_to_defaults()
            
        else:
            print(f"未知命令: {command}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"操作失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()