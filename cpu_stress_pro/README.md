# CPU压力测试监控系统 V3.0

一个用于CPU压力测试和温度监控的综合系统，支持SSH和串口连接。

## 快速开始

```bash
# Windows用户双击运行
run.bat

# 或使用命令行
python monitor.py stress  # 压力测试
python monitor.py temp    # 温度监控
```

## 文件结构

```
stress_pro/
├── src/                        # 源代码目录
│   ├── config_loader.py       # 配置加载器
│   ├── connection_manager.py  # 连接管理(SSH/串口)
│   ├── stress_monitor.py      # 压力测试监控
│   └── logger_manager.py      # 统一日志管理
├── results/                    # 测试结果目录
│   └── result_*/              # 各次测试结果
│       ├── program.log        # 程序日志
│       ├── console.log        # 控制台日志
│       ├── debug.log          # 调试日志
│       └── test_results.csv   # 测试数据
├── monitor.py                  # 统一入口
├── temperature_monitor.py      # 温度监控
├── config.json                # 配置文件
├── run.bat                    # Windows启动器
└── requirements.txt           # Python依赖
```

## 配置说明

编辑 `config.json`:

```json
{
  "connection_type": "ssh",  // 或 "serial"
  "ssh": {
    "hostname": "10.1.0.237",
    "username": "root",
    "password": "12345"
  }
}
```

## 使用方法

1. **压力测试**: `run.bat` → 选择 [1]
2. **温度监控**: `run.bat` → 选择 [2]
3. **环境设置**: `run.bat` → 选择 [3]

## 命令行

```bash
# 压力测试
python monitor.py stress --config config.json

# 温度监控
python monitor.py temp --config config.json

# 生成配置
python monitor.py stress --generate-config
```