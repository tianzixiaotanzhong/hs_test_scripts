# 雷赛L7伺服驱动器Python控制库

专业的Python驱动库，用于控制雷赛L7/L7RS/L7EC系列交流伺服控制器。

## 📋 目录

- [产品特性](#产品特性)
- [系统要求](#系统要求)
- [安装指南](#安装指南)
- [快速开始](#快速开始)
- [详细教程](#详细教程)
- [API参考](#api参考)
- [故障排除](#故障排除)
- [技术支持](#技术支持)

## 产品特性

### 核心功能
- ✅ **完整的Modbus RTU协议** - 支持CRC16校验、自动重试、错误处理
- ✅ **多种控制模式** - 位置控制、速度控制、转矩控制
- ✅ **PR路径控制** - 支持16条可编程运动路径
- ✅ **实时状态监控** - 连续监控伺服状态、报警、I/O信号
- ✅ **参数管理** - 参数读写、导入导出、EEPROM保存
- ✅ **自动调谐** - 支持刚性调整、惯量识别、振动抑制

### 设计优势
- 🏗️ **模块化架构** - 遵循Python标准库设计模式
- 🔒 **线程安全** - 支持多线程应用
- 📝 **类型注解** - 完整的类型提示，提升IDE体验
- 🧪 **单元测试** - 完善的测试覆盖
- 📚 **详细文档** - 中英文文档、丰富示例

## 系统要求

- Python 3.7 或更高版本
- Windows/Linux/macOS 操作系统
- RS232/RS485 串口（或USB转串口）
- pyserial 3.5+

## 安装指南

### 方式一：使用pip安装（推荐）

```bash
pip install leisai-l7-driver
```

### 方式二：从源码安装

```bash
# 克隆仓库
git clone https://github.com/leisai/python-l7-driver.git
cd python-l7-driver

# 安装
pip install -e .
```

### 方式三：开发模式安装

```bash
# 安装开发依赖
pip install -e .[dev]
```

## 快速开始

### 1. 基础连接

```python
from leisai import L7Driver

# 创建驱动器实例
driver = L7Driver(
    port='COM3',      # 串口号：Windows用'COM3'，Linux用'/dev/ttyUSB0'
    slave_id=1,       # 从站ID，默认为1
    baudrate=38400,   # 波特率，默认38400
    timeout=1.0       # 超时时间（秒）
)

# 连接伺服
if driver.connect():
    print("连接成功！")
    
    # 读取当前状态
    position = driver.get_position()
    speed = driver.get_speed()
    print(f"当前位置：{position} 脉冲")
    print(f"当前速度：{speed} RPM")
    
    # 断开连接
    driver.disconnect()
```

### 2. 使用上下文管理器（推荐）

```python
from leisai import L7Driver

# 自动管理连接
with L7Driver('COM3') as driver:
    # 伺服使能
    driver.servo_on()
    
    # 执行操作
    print(f"位置：{driver.get_position()}")
    
    # 伺服断使能
    driver.servo_off()
    # 退出时自动断开连接
```

## 详细教程

### 📍 位置控制模式

位置控制模式适用于需要精确定位的应用场景。

```python
from leisai import L7Driver, ControlMode

with L7Driver('COM3') as driver:
    # 1. 设置为位置控制模式
    driver.set_control_mode(ControlMode.POSITION)
    
    # 2. 配置电子齿轮比
    # 设置10000脉冲/转（根据实际需求调整）
    driver.write_parameter('gear_ratio_numerator', 10000)    # 分子
    driver.write_parameter('gear_ratio_denominator', 131072) # 分母
    
    # 3. 设置位置环增益
    driver.write_parameter('position_loop_gain', 250)  # 25.0/s
    
    # 4. 设置位置偏差报警阈值
    driver.write_parameter('position_error_limit', 10000)  # 10000脉冲
    
    # 5. 伺服使能
    driver.servo_on()
    
    # 6. 监控位置（位置指令通常由外部脉冲输入）
    for _ in range(10):
        position = driver.get_position()
        error = driver.read_parameter('position_error')
        print(f"位置：{position}, 偏差：{error}")
        time.sleep(0.1)
```

### 🚀 速度控制模式

速度控制模式适用于需要恒速运行的应用。

```python
from leisai import L7Driver, ControlMode
import time

with L7Driver('COM3') as driver:
    # 1. 设置为速度控制模式
    driver.set_control_mode(ControlMode.SPEED)
    
    # 2. 配置速度环参数
    driver.write_parameter('speed_loop_gain', 100)        # 速度环增益
    driver.write_parameter('speed_loop_integral', 50)     # 积分时间
    
    # 3. 设置加减速时间
    driver.write_parameter('acceleration_time', 500)      # 500ms加速
    driver.write_parameter('deceleration_time', 500)      # 500ms减速
    
    # 4. 设置S曲线时间（使加减速更平滑）
    driver.write_parameter('s_curve_time', 50)            # 50ms
    
    # 5. 伺服使能
    driver.servo_on()
    
    # 6. 速度控制
    speeds = [500, 1000, 1500, 1000, 500, 0]  # RPM
    for target_speed in speeds:
        driver.write_parameter('speed_command_1', target_speed)
        print(f"目标速度：{target_speed} RPM")
        
        # 等待到达目标速度
        for _ in range(20):
            current_speed = driver.get_speed()
            print(f"  当前速度：{current_speed} RPM")
            time.sleep(0.1)
    
    driver.servo_off()
```

### ⚡ 转矩控制模式

转矩控制模式适用于需要控制输出力矩的应用。

```python
from leisai import L7Driver, ControlMode

with L7Driver('COM3') as driver:
    # 1. 设置为转矩控制模式
    driver.set_control_mode(ControlMode.TORQUE)
    
    # 2. 设置转矩限制
    driver.write_parameter('torque_limit_1', 80)  # 限制到额定转矩的80%
    
    # 3. 设置转矩指令滤波（减少转矩波动）
    driver.write_parameter('torque_filter_time', 5)  # 5ms滤波
    
    # 4. 伺服使能
    driver.servo_on()
    
    # 5. 监控转矩
    for _ in range(50):
        torque = driver.get_torque()
        speed = driver.get_speed()
        print(f"转矩：{torque}%, 速度：{speed} RPM")
        time.sleep(0.1)
    
    driver.servo_off()
```

### 🎯 JOG运动控制

JOG（点动）适用于手动调试和定位。

```python
with L7Driver('COM3') as driver:
    driver.servo_on()
    
    # 正向JOG
    print("正向点动 300 RPM...")
    driver.jog(speed=300, direction=True)
    time.sleep(3)
    
    # 反向JOG
    print("反向点动 300 RPM...")
    driver.jog(speed=300, direction=False)
    time.sleep(3)
    
    # 停止JOG
    driver.stop_jog()
    print("点动停止")
    
    driver.servo_off()
```

### 🏠 回零控制

自动回零功能，支持多种回零模式。

```python
from leisai.core.constants import HomingMode

with L7Driver('COM3') as driver:
    driver.servo_on()
    
    # 配置回零参数
    driver.write_parameter('pr_home_mode', HomingMode.ORIGIN_FORWARD)
    driver.write_parameter('pr_home_speed_high', 500)  # 高速500 RPM
    driver.write_parameter('pr_home_speed_low', 50)    # 低速50 RPM
    driver.write_parameter('pr_home_offset', 1000)     # 偏移1000脉冲
    
    # 开始回零
    print("开始回零...")
    driver.home(mode=0, high_speed=500, low_speed=50)
    
    # 等待回零完成
    while not driver.is_homing_complete():
        position = driver.get_position()
        print(f"回零中... 当前位置：{position}")
        time.sleep(0.5)
    
    print("回零完成！")
    print(f"零点位置：{driver.get_position()}")
    
    driver.servo_off()
```

### 📊 PR路径控制

PR（Program Route）路径控制允许预设多条运动路径。

```python
from leisai.core.motion import PRPath

with L7Driver('COM3') as driver:
    # 1. 配置路径参数
    paths = [
        PRPath(
            path_id=0,
            position=10000,      # 目标位置：10000脉冲
            speed=1000,          # 速度：1000 RPM
            acceleration=100,    # 加速时间：100 ms/kRPM
            deceleration=100,    # 减速时间：100 ms/kRPM
            delay=500,           # 延时：500ms
            s_curve=20           # S曲线：20ms
        ),
        PRPath(
            path_id=1,
            position=20000,      # 第二个位置
            speed=1500,
            acceleration=200,
            deceleration=200,
            delay=1000,
            s_curve=30
        ),
        PRPath(
            path_id=2,
            position=0,          # 返回原点
            speed=2000,
            acceleration=150,
            deceleration=150,
            delay=0,
            s_curve=25
        )
    ]
    
    # 2. 写入路径到驱动器
    for path in paths:
        driver._motion.set_pr_path(path)
        print(f"路径 {path.path_id} 已配置")
    
    # 3. 伺服使能
    driver.servo_on()
    
    # 4. 依次执行路径
    for i in range(3):
        print(f"\n执行路径 {i}...")
        driver._motion.execute_pr_path(i)
        
        # 等待路径完成
        while not driver._motion.is_pr_complete():
            position = driver._motion.get_pr_position()
            print(f"  当前位置：{position}")
            time.sleep(0.5)
        
        print(f"路径 {i} 完成")
    
    driver.servo_off()
```

### ⚙️ 参数管理

完整的参数读写和管理功能。

```python
with L7Driver('COM3') as driver:
    # 1. 读取参数
    params = {
        'rigidity_level': '刚性等级',
        'inertia_ratio': '惯量比',
        'position_loop_gain': '位置环增益',
        'speed_loop_gain': '速度环增益',
        'motor_max_speed': '最大速度限制'
    }
    
    print("当前参数：")
    for param, name in params.items():
        value = driver.read_parameter(param)
        print(f"  {name}：{value}")
    
    # 2. 修改参数
    driver.set_rigidity(20)              # 设置刚性为20
    driver.set_inertia_ratio(250)        # 设置惯量比为250%
    print("\n参数已修改")
    
    # 3. 导出参数到文件
    driver.export_parameters('my_servo_config.json')
    print("参数已导出到 my_servo_config.json")
    
    # 4. 保存到EEPROM（断电保持）
    driver.save_parameters()
    print("参数已保存到EEPROM")
    
    # 5. 从文件导入参数
    # driver.import_parameters('my_servo_config.json')
    
    # 6. 恢复出厂设置
    # driver.restore_defaults()
```

### 🔧 自动调谐

自动优化伺服性能参数。

```python
with L7Driver('COM3') as driver:
    # 1. 基础参数设置
    driver.set_rigidity(15)          # 初始刚性
    driver.set_inertia_ratio(100)    # 初始惯量比
    
    # 2. 启动自动调谐
    print("开始自动调谐...")
    driver.auto_tune(mode=1)  # mode: 0-关闭, 1-标准, 2-大惯量
    
    # 3. 执行测试运动（调谐需要实际运动）
    driver.servo_on()
    
    # 进行往复运动以供调谐
    for _ in range(5):
        # 这里应该发送位置指令进行往复运动
        time.sleep(2)
    
    # 4. 调谐完成后读取优化后的参数
    print("\n调谐后的参数：")
    print(f"刚性：{driver.read_parameter('rigidity_level')}")
    print(f"惯量比：{driver.read_parameter('inertia_ratio')}")
    print(f"位置环增益：{driver.read_parameter('position_loop_gain')}")
    
    driver.servo_off()
```

### 📡 实时状态监控

设置回调函数监控状态变化和报警。

```python
from leisai import L7Driver, AlarmCode
import threading
import time

class ServoMonitor:
    def __init__(self):
        self.position_history = []
        self.alarm_history = []
    
    def on_status_change(self, status):
        """状态变化回调"""
        self.position_history.append(status['position'])
        print(f"[状态] 位置：{status['position']}, "
              f"速度：{status['speed']}, "
              f"转矩：{status['torque']}%")
    
    def on_alarm(self, alarm_code):
        """报警回调"""
        self.alarm_history.append(alarm_code)
        if alarm_code != AlarmCode.NO_ALARM:
            print(f"⚠️ [报警] 代码：0x{alarm_code:02X}")
        else:
            print("✅ [报警] 已清除")

# 使用监控
monitor = ServoMonitor()

with L7Driver('COM3') as driver:
    # 设置回调
    driver.set_status_callback(monitor.on_status_change)
    driver.set_alarm_callback(monitor.on_alarm)
    
    # 开始监控（后台线程）
    print("开始监控（10秒）...")
    
    driver.servo_on()
    
    # 执行一些操作
    for _ in range(10):
        # 检查特定状态
        if driver.is_ready():
            print("伺服就绪")
        
        time.sleep(1)
    
    driver.servo_off()
    
    # 查看历史记录
    print(f"\n位置记录数：{len(monitor.position_history)}")
    print(f"报警记录数：{len(monitor.alarm_history)}")
```

### 🛡️ 错误处理

完善的异常处理机制。

```python
from leisai import L7Driver
from leisai.core.exceptions import *

driver = L7Driver('COM3')

try:
    # 连接
    driver.connect()
    
    # 检查报警
    alarm = driver.get_alarm()
    if alarm:
        raise AlarmError(alarm, driver.get_alarm_description(alarm))
    
    # 伺服使能
    driver.servo_on()
    
    # 参数操作
    driver.set_rigidity(35)  # 可能超范围
    
except ConnectionError as e:
    print(f"连接失败：{e}")
    
except AlarmError as e:
    print(f"伺服报警：{e.description}")
    # 尝试复位报警
    driver.reset_alarm()
    
except ParameterOutOfRangeError as e:
    print(f"参数超范围：{e}")
    
except ModbusError as e:
    print(f"通信错误：{e.exception_code}")
    
except Exception as e:
    print(f"未知错误：{e}")
    
finally:
    driver.disconnect()
```

## API参考

### L7Driver 主类

#### 构造函数
```python
L7Driver(
    port: str,                # 串口号
    slave_id: int = 1,       # 从站ID
    baudrate: int = 38400,   # 波特率
    timeout: float = 1.0     # 超时时间
)
```

#### 连接管理
| 方法 | 说明 | 返回值 |
|-----|------|--------|
| `connect()` | 连接伺服 | bool |
| `disconnect()` | 断开连接 | None |
| `is_connected` | 连接状态 | bool |

#### 伺服控制
| 方法 | 说明 | 返回值 |
|-----|------|--------|
| `servo_on()` | 伺服使能 | bool |
| `servo_off()` | 伺服断使能 | bool |
| `emergency_stop()` | 紧急停止 | bool |
| `reset_alarm()` | 复位报警 | bool |
| `set_control_mode(mode)` | 设置控制模式 | bool |

#### 运动控制
| 方法 | 说明 | 返回值 |
|-----|------|--------|
| `get_position()` | 获取位置(脉冲) | int |
| `get_speed()` | 获取速度(RPM) | int |
| `get_torque()` | 获取转矩(%) | int |
| `jog(speed, direction)` | JOG运动 | bool |
| `stop_jog()` | 停止JOG | bool |
| `home(mode, high_speed, low_speed)` | 回零 | bool |
| `is_homing_complete()` | 回零是否完成 | bool |

#### 参数管理
| 方法 | 说明 | 返回值 |
|-----|------|--------|
| `read_parameter(name)` | 读参数 | Any |
| `write_parameter(name, value)` | 写参数 | bool |
| `set_rigidity(level)` | 设置刚性(0-31) | bool |
| `set_inertia_ratio(ratio)` | 设置惯量比(%) | bool |
| `auto_tune(mode)` | 自动调谐 | bool |
| `save_parameters()` | 保存到EEPROM | bool |
| `restore_defaults()` | 恢复出厂设置 | bool |
| `export_parameters(filename)` | 导出参数 | bool |
| `import_parameters(filename)` | 导入参数 | bool |

#### 状态监控
| 方法 | 说明 | 返回值 |
|-----|------|--------|
| `get_status()` | 获取状态 | ServoStatus |
| `get_alarm()` | 获取报警代码 | AlarmCode |
| `get_alarm_description(code)` | 获取报警描述 | str |
| `is_ready()` | 是否就绪 | bool |
| `set_status_callback(func)` | 设置状态回调 | None |
| `set_alarm_callback(func)` | 设置报警回调 | None |

### 常量定义

#### ControlMode 控制模式
```python
ControlMode.POSITION      # 位置控制
ControlMode.SPEED         # 速度控制
ControlMode.TORQUE        # 转矩控制
```

#### ServoStatus 伺服状态
```python
ServoStatus.IDLE          # 空闲
ServoStatus.RUNNING       # 运行中
ServoStatus.ERROR         # 错误
ServoStatus.HOMING        # 回零中
ServoStatus.EMERGENCY_STOP # 急停
ServoStatus.DISABLED      # 已禁用
```

#### AlarmCode 报警代码
```python
AlarmCode.NO_ALARM           # 0x00 无报警
AlarmCode.OVER_CURRENT       # 0x10 过电流
AlarmCode.OVER_VOLTAGE       # 0x20 过电压
AlarmCode.UNDER_VOLTAGE      # 0x21 欠电压
AlarmCode.DRIVER_OVERHEAT    # 0x30 驱动器过热
AlarmCode.MOTOR_OVERHEAT     # 0x31 电机过热
AlarmCode.ENCODER_ERROR      # 0x40 编码器错误
AlarmCode.POSITION_ERROR     # 0x50 位置偏差过大
AlarmCode.OVER_SPEED         # 0x60 超速
AlarmCode.OVER_LOAD          # 0x70 过载
AlarmCode.COMMUNICATION_ERROR # 0x80 通信错误
```

## 故障排除

### 1. 连接问题

#### 问题：无法连接到伺服
```python
# 检查串口
import serial.tools.list_ports

# 列出所有可用串口
ports = serial.tools.list_ports.comports()
for port in ports:
    print(f"{port.device}: {port.description}")

# 测试连接
driver = L7Driver('COM3', baudrate=38400, timeout=2.0)
try:
    if driver.connect():
        print("连接成功")
    else:
        print("连接失败，请检查：")
        print("1. 串口号是否正确")
        print("2. 波特率是否匹配（默认38400）")
        print("3. 从站ID是否正确（默认1）")
        print("4. 接线是否正确")
finally:
    driver.disconnect()
```

### 2. 通信错误

#### 问题：Modbus通信错误
- 检查接线：A+/B- 是否接反
- 终端电阻：RS485需要120Ω终端电阻
- 线缆屏蔽：使用屏蔽双绞线
- 通信距离：RS485最大1200米

### 3. 报警处理

#### 常见报警及解决方法

| 报警代码 | 说明 | 解决方法 |
|---------|------|----------|
| 0x10 | 过电流 | 检查电机接线、减小加速度 |
| 0x20 | 过电压 | 检查电源电压、制动电阻 |
| 0x30 | 过热 | 改善散热、降低负载 |
| 0x40 | 编码器异常 | 检查编码器线缆 |
| 0x50 | 位置偏差过大 | 增大偏差阈值、降低速度 |

```python
# 报警处理示例
alarm = driver.get_alarm()
if alarm != AlarmCode.NO_ALARM:
    print(f"报警：{driver.get_alarm_description(alarm)}")
    
    # 尝试复位
    driver.reset_alarm()
    time.sleep(1)
    
    # 再次检查
    if driver.get_alarm() == AlarmCode.NO_ALARM:
        print("报警已清除")
    else:
        print("报警无法清除，请检查硬件")
```

### 4. 性能优化

#### 提高响应速度
```python
# 1. 增加刚性
driver.set_rigidity(25)  # 范围：0-31

# 2. 优化惯量比
driver.set_inertia_ratio(200)  # 实际惯量比

# 3. 使用自动调谐
driver.auto_tune(mode=1)
```

#### 减少振动
```python
# 1. 降低刚性
driver.set_rigidity(10)

# 2. 增加滤波
driver.write_parameter('torque_filter_time', 10)

# 3. 启用振动抑制
driver.write_parameter('notch1_frequency', 500)  # 陷波频率
driver.write_parameter('notch1_depth', 50)       # 陷波深度
```

## 项目结构

```
leisai-l7-driver/
├── leisai/                 # 主包
│   ├── __init__.py        # 包初始化，导出公共API
│   ├── core/              # 核心功能模块
│   │   ├── driver.py      # L7Driver主类
│   │   ├── constants.py   # 常量和枚举定义
│   │   ├── exceptions.py  # 自定义异常类
│   │   ├── parameters.py  # 参数管理器
│   │   ├── motion.py      # 运动控制器
│   │   └── monitor.py     # 状态监控器
│   └── protocols/         # 通信协议实现
│       ├── modbus.py      # Modbus RTU协议
│       └── serial.py      # 串口通信层
├── tests/                 # 单元测试
│   └── test_modbus.py    # Modbus协议测试
├── examples/             # 使用示例
│   └── basic_usage.py    # 基础用法示例
├── docs/                 # 文档
├── setup.py             # 安装配置
├── pyproject.toml       # 项目配置
├── requirements.txt     # 依赖列表
├── README.md           # 英文说明
└── README_CN.md        # 中文说明
```

## 技术支持

### 联系方式
- 📧 邮箱：support@leisai.com
- 📞 电话：0755-26433338
- 🌐 网站：www.leisai.com

### 相关资源
- [产品手册](leisai_doc.txt) - L7系列伺服使用手册
- [GitHub仓库](https://github.com/leisai/python-l7-driver) - 源代码
- [问题反馈](https://github.com/leisai/python-l7-driver/issues) - Bug报告

### 常见问题

**Q: 支持哪些操作系统？**
A: Windows、Linux、macOS都支持，需要Python 3.7+。

**Q: 如何确定串口号？**
A: Windows设备管理器查看COM口，Linux一般是/dev/ttyUSB0或/dev/ttyACM0。

**Q: 可以同时控制多个伺服吗？**
A: 可以，通过不同的从站ID区分，最多支持31个。

**Q: 位置单位是什么？**
A: 脉冲数，默认131072脉冲/圈（17位编码器）。

**Q: 如何提高通信速度？**
A: 提高波特率（最高115200），减少超时时间，使用缓存读取。

## 版本历史

### v1.0.0 (2025-01-04)
- ✨ 首次发布
- ✅ 完整Modbus RTU实现
- ✅ 三种控制模式
- ✅ PR路径控制
- ✅ 实时监控
- ✅ 参数管理
- ✅ 中英文文档

## 许可证

MIT License - 详见 LICENSE 文件

---

💡 **提示**：遇到问题请先查看故障排除章节，如果仍无法解决，欢迎提交Issue或联系技术支持。