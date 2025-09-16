# CPU压力测试系统

一个简洁的CPU压力测试和温度监控工具，支持SSH连接远程设备进行测试。

## 快速开始

### 方式1：直接运行Python脚本（推荐）
```bash
python monitor.py
```

### 方式2：使用批处理文件
```bash
# Windows用户双击运行
run.bat
```

## 配置文件

程序会自动读取 `config.json` 配置文件：

```json
{
  "connection_type": "ssh",
  "ssh": {
    "hostname": "10.2.0.18",
    "username": "sunrise", 
    "password": "sunrise",
    "port": 22
  },
  "test": {
    "interval_seconds": 5,
    "max_tests": 1000,
    "timeout_seconds": 60,
    "enter_docker": false,
    "install_stress_ng": true
  }
}
```

如果配置文件不存在，程序会自动生成默认配置。

## 功能特点

- ✅ **一键启动**：直接运行 `python monitor.py` 即可
- ✅ **实时显示**：测试进度实时更新，无缓冲延迟
- ✅ **温度监控**：测试前后自动获取CPU温度
- ✅ **快速响应**：Ctrl+C 可立即停止并生成报告
- ✅ **自动报告**：生成性能图表和CSV数据文件
- ✅ **智能优化**：压力测试期间暂停温度监控，避免资源竞争

## 输出结果

测试结果保存在 `results/result_YYYYMMDD_HHMMSS/` 目录下：
- `test_results.csv` - 测试数据
- `performance_chart.png` - 性能图表
- `temperature_log.csv` - 温度记录
- `summary.json` - 测试摘要

## 依赖安装

```bash
pip install -r requirements.txt
```