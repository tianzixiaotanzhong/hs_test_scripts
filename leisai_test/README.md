# 雷赛L7伺服驱动器测试工具集

## 项目结构

```
leisai_test/
├── leisai_l7_driver/       # 驱动器核心库
│   ├── leisai/            # 主驱动模块
│   ├── docs/              # 文档
│   └── setup.py           # 安装脚本
├── test_framework.py       # 测试框架基类
├── test_all.py            # 综合测试脚本
├── quick_test.py          # 快速测试脚本
├── parameter_manager.py   # 参数管理工具
└── README.md              # 本文档
```

## 功能特性

### 1. 统一测试框架 (test_framework.py)
- **L7TestBase**: 测试基类，提供自动连接、断开、重试机制
- **TestSuite**: 测试套件管理器，批量运行测试
- **自动日志记录**: 测试结果自动保存到日志文件
- **上下文管理**: 使用with语句自动管理连接

### 2. 综合测试脚本 (test_all.py)
提供多种测试模式：
- **基础测试**: 连接、参数读取、IO状态
- **运动测试**: JOG运动、位置控制、模式切换
- **监控测试**: 连续状态监控
- **完整测试**: 运行所有测试

### 3. 快速测试工具 (quick_test.py)
- 快速验证连接
- 读取基本状态
- 交互式测试（可选）

### 4. 参数管理工具 (parameter_manager.py)
- **备份参数**: 保存当前参数到JSON文件
- **恢复参数**: 从备份文件恢复参数
- **比较参数**: 对比当前参数与备份
- **恢复出厂设置**: 重置为默认参数

## 使用方法

### 安装依赖
```bash
pip install pyserial
```

### 运行测试

#### 1. 快速测试
```bash
python quick_test.py
```

#### 2. 综合测试
```bash
# 运行基础测试
python test_all.py basic

# 运行运动控制测试
python test_all.py motion

# 运行监控测试
python test_all.py monitor

# 运行所有测试
python test_all.py all
```

#### 3. 参数管理
```bash
# 备份当前参数
python parameter_manager.py backup

# 备份到指定文件
python parameter_manager.py backup my_backup.json

# 恢复参数
python parameter_manager.py restore my_backup.json

# 比较参数差异
python parameter_manager.py compare my_backup.json

# 恢复出厂设置
python parameter_manager.py reset
```

## 配置说明

### 默认配置
在 `test_framework.py` 中定义：
```python
DEFAULT_CONFIG = {
    'com_ports': ['COM42', 'COM3', 'COM4', 'COM5'],  # COM端口列表
    'baudrate': 38400,                                # 波特率
    'slave_id': 1,                                    # Modbus从站ID
    'timeout': 1.0,                                   # 通信超时(秒)
    'retry_count': 3,                                 # 重试次数
    'retry_delay': 0.5                                # 重试延迟(秒)
}
```

### 自定义配置
```python
from test_framework import L7TestBase

# 使用自定义配置
config = {
    'com_ports': ['COM1', 'COM2'],
    'baudrate': 115200,
    'timeout': 2.0
}

test = L7TestBase(config)
```

## 测试结果

### 日志文件
- 测试日志: `test_log_YYYYMMDD_HHMMSS.log`
- 测试结果: `test_results_YYYYMMDD_HHMMSS.json`

### 结果格式
```json
{
  "test": "连接测试",
  "success": true,
  "timestamp": "2024-09-10T10:30:45",
  "details": "成功连接到COM42"
}
```

## 扩展测试

### 添加自定义测试
```python
from test_framework import L7TestBase, TestSuite

def my_custom_test(test_base: L7TestBase):
    """自定义测试函数"""
    # 使用test_base.driver访问驱动器
    position = test_base.driver.get_position()
    assert position is not None, "读取位置失败"
    
# 创建测试套件
suite = TestSuite()
suite.add_test(my_custom_test, "我的自定义测试")

# 运行测试
test_base = L7TestBase()
suite.run(test_base)
```

## 注意事项

1. **安全第一**: 运行运动测试前确保设备处于安全状态
2. **参数备份**: 修改参数前建议先备份
3. **日志检查**: 测试失败时查看日志文件获取详细信息
4. **端口配置**: 根据实际情况修改COM端口列表

## 故障排除

### 连接失败
- 检查COM端口是否正确
- 确认驱动器电源已开启
- 验证通信参数（波特率、从站ID）
- 检查串口线连接

### 测试失败
- 查看日志文件中的错误信息
- 确认驱动器无报警
- 检查伺服是否已使能
- 验证参数设置是否正确

## 技术支持

如遇到问题，请查看：
1. 日志文件中的详细错误信息
2. 雷赛L7驱动器使用手册
3. `leisai_l7_driver/docs/` 目录下的文档