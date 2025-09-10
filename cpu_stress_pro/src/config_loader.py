"""配置文件加载模块"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SerialConfig:
    """串口连接配置"""
    port: str = "COM38"
    baudrate: int = 115200
    timeout: int = 1


@dataclass
class SSHConfig:
    """SSH连接配置"""
    hostname: str = ""
    username: str = ""
    password: Optional[str] = None
    port: int = 22
    key_file: Optional[str] = None


@dataclass
class TestConfig:
    """测试配置"""
    duration_minutes: Optional[int] = None
    interval_seconds: int = 1
    max_tests: int = 3000
    timeout_seconds: int = 60
    enter_docker: bool = True
    install_stress_ng: bool = True


@dataclass
class MonitorConfig:
    """监控配置"""
    temperature_interval: int = 10
    temperature_duration: Optional[int] = None
    enable_temperature: bool = True


@dataclass
class OutputConfig:
    """输出配置"""
    base_dir: str = "results"
    create_timestamp_dir: bool = True
    save_charts: bool = True
    save_summary: bool = True
    
    def get_output_dir(self) -> Path:
        """获取输出目录路径"""
        base_path = Path(self.base_dir)
        if self.create_timestamp_dir:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return base_path / f"result_{timestamp}"
        return base_path


@dataclass
class Config:
    """主配置类"""
    connection_type: str = "serial"  # serial, ssh, multi_ssh
    serial: SerialConfig = field(default_factory=SerialConfig)
    ssh: SSHConfig = field(default_factory=SSHConfig)
    ssh_list: list[SSHConfig] = field(default_factory=list)
    test: TestConfig = field(default_factory=TestConfig)
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """从JSON文件加载配置"""
        config_path = Path(config_path)
        
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_path}")
            return cls()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return cls.from_dict(data)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return cls()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """从字典创建配置"""
        config = cls()
        
        # 基本配置
        config.connection_type = data.get('connection_type', 'serial')
        
        # 串口配置
        if 'serial' in data:
            config.serial = SerialConfig(**data['serial'])
        
        # SSH配置
        if 'ssh' in data:
            config.ssh = SSHConfig(**data['ssh'])
        
        # 多SSH配置
        if 'ssh_list' in data:
            config.ssh_list = [SSHConfig(**ssh_cfg) for ssh_cfg in data['ssh_list']]
        
        # 测试配置
        if 'test' in data:
            config.test = TestConfig(**data['test'])
        
        # 监控配置
        if 'monitor' in data:
            config.monitor = MonitorConfig(**data['monitor'])
        
        # 输出配置
        if 'output' in data:
            config.output = OutputConfig(**data['output'])
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'connection_type': self.connection_type,
            'serial': asdict(self.serial),
            'ssh': asdict(self.ssh),
            'ssh_list': [asdict(ssh) for ssh in self.ssh_list],
            'test': asdict(self.test),
            'monitor': asdict(self.monitor),
            'output': asdict(self.output)
        }
    
    def save(self, config_path: str) -> None:
        """保存配置到文件"""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        
        logger.info(f"配置已保存到: {config_path}")
    
    def validate(self) -> bool:
        """验证配置有效性"""
        if self.connection_type == 'serial':
            if not self.serial.port:
                logger.error("串口配置缺少端口")
                return False
        
        elif self.connection_type == 'ssh':
            if not self.ssh.hostname or not self.ssh.username:
                logger.error("SSH配置缺少主机名或用户名")
                return False
            if not self.ssh.password and not self.ssh.key_file:
                logger.error("SSH配置需要密码或密钥文件")
                return False
        
        elif self.connection_type == 'multi_ssh':
            if not self.ssh_list:
                logger.error("多SSH配置缺少SSH列表")
                return False
            for i, ssh_cfg in enumerate(self.ssh_list):
                if not ssh_cfg.hostname or not ssh_cfg.username:
                    logger.error(f"SSH配置 {i+1} 缺少主机名或用户名")
                    return False
        
        else:
            logger.error(f"不支持的连接类型: {self.connection_type}")
            return False
        
        return True
    
    def get_connection_params(self) -> Dict[str, Any]:
        """获取连接参数"""
        if self.connection_type == 'serial':
            return asdict(self.serial)
        elif self.connection_type == 'ssh':
            return asdict(self.ssh)
        elif self.connection_type == 'multi_ssh':
            return {'ssh_configs': [asdict(ssh) for ssh in self.ssh_list]}
        return {}


class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG_DIR = Path("configs")
    DEFAULT_CONFIG_FILE = "default.json"
    
    def __init__(self):
        self.configs: Dict[str, Config] = {}
        self.current_config: Optional[Config] = None
        self._ensure_default_configs()
    
    def _ensure_default_configs(self) -> None:
        """确保默认配置文件存在"""
        self.DEFAULT_CONFIG_DIR.mkdir(exist_ok=True)
        
        # 创建默认串口配置
        serial_config = Config()
        serial_config.connection_type = 'serial'
        serial_config.save(self.DEFAULT_CONFIG_DIR / "serial_default.json")
        
        # 创建默认SSH配置模板
        ssh_config = Config()
        ssh_config.connection_type = 'ssh'
        ssh_config.ssh = SSHConfig(
            hostname="192.168.1.100",
            username="root",
            password="password"
        )
        ssh_config.save(self.DEFAULT_CONFIG_DIR / "ssh_template.json")
    
    def load(self, config_name: str) -> Config:
        """加载配置"""
        if config_name in self.configs:
            return self.configs[config_name]
        
        # 尝试从文件加载
        config_path = Path(config_name)
        if not config_path.exists():
            config_path = self.DEFAULT_CONFIG_DIR / f"{config_name}.json"
        
        config = Config.from_file(str(config_path))
        self.configs[config_name] = config
        self.current_config = config
        return config
    
    def create_config_from_args(self, **kwargs) -> Config:
        """从参数创建配置"""
        config = Config()
        
        # 设置连接类型
        if 'connection_type' in kwargs:
            config.connection_type = kwargs['connection_type']
        
        # 设置串口参数
        if config.connection_type == 'serial':
            if 'port' in kwargs:
                config.serial.port = kwargs['port']
            if 'baudrate' in kwargs:
                config.serial.baudrate = kwargs['baudrate']
        
        # 设置SSH参数
        elif config.connection_type == 'ssh':
            if 'hostname' in kwargs:
                config.ssh.hostname = kwargs['hostname']
            if 'username' in kwargs:
                config.ssh.username = kwargs['username']
            if 'password' in kwargs:
                config.ssh.password = kwargs['password']
            if 'ssh_port' in kwargs:
                config.ssh.port = kwargs['ssh_port']
            if 'key_file' in kwargs:
                config.ssh.key_file = kwargs['key_file']
        
        # 设置测试参数
        if 'duration' in kwargs and kwargs['duration']:
            config.test.duration_minutes = kwargs['duration']
        if 'interval' in kwargs:
            config.test.interval_seconds = kwargs['interval']
        if 'max_tests' in kwargs:
            config.test.max_tests = kwargs['max_tests']
        
        self.current_config = config
        return config