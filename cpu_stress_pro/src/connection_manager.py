"""连接管理模块 - 更Pythonic的实现"""

import serial
import paramiko
import time
import threading
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union, TextIO
from dataclasses import dataclass
from contextlib import contextmanager
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionError(Exception):
    """连接异常基类"""
    pass


class BaseConnection(ABC):
    """连接基类 - 使用上下文管理器模式"""
    
    def __init__(self):
        self.console_logger: Optional[logging.Logger] = None
        self.enable_console_log = True
        
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_console_log()
        self.disconnect()
    
    def setup_console_log(self, console_logger: logging.Logger) -> None:
        """设置控制台日志器"""
        self.console_logger = console_logger
        logger.info("Console logger configured")
        
    def close_console_log(self) -> None:
        """关闭控制台日志"""
        # 日志器由LoggerManager管理，这里不需要关闭
        pass
            
    def log_console(self, direction: str, content: str) -> None:
        """记录控制台输出
        direction: 'SEND' 或 'RECV'
        content: 内容
        """
        if not self.enable_console_log:
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # 打印到终端
        if direction == "SEND":
            print(f"[{timestamp}] >>> {content}")
        else:
            # 处理接收的内容，去除多余的空行
            lines = content.split('\n')
            for line in lines:
                if line.strip():
                    print(f"[{timestamp}] <<< {line}")
        
        # 写入日志文件
        if self.console_logger:
            self.console_logger.info(f"[{direction}] {content}")
    
    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    def send_command(self, command: str, wait_time: float = 1) -> bool:
        """发送命令"""
        pass
    
    @abstractmethod
    def read_output(self, timeout: float = 2) -> str:
        """读取输出"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查连接状态"""
        pass
    
    def execute_command(self, command: str, wait_time: float = 1, read_timeout: float = 2) -> str:
        """执行命令并返回输出"""
        if self.send_command(command, wait_time):
            return self.read_output(read_timeout)
        return ""


class SerialConnection(BaseConnection):
    """串口连接类 - 优化实现"""
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: int = 1):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port: Optional[serial.Serial] = None
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False
        self.buffer = ""
        self.lock = threading.Lock()
        
    def connect(self) -> bool:
        """建立串口连接"""
        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_data, daemon=True)
            self.receive_thread.start()
            
            logger.info(f"Serial connection successful: {self.port} @ {self.baudrate}bps")
            return True
        except Exception as e:
            logger.error(f"Serial connection failed: {e}")
            raise ConnectionError(f"串口连接失败: {e}")
    
    def disconnect(self) -> None:
        """断开串口连接"""
        self.running = False
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2)
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        logger.info("串口连接已断开")
    
    def _receive_data(self) -> None:
        """接收数据线程"""
        while self.running and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data:
                        text = data.decode('utf-8', errors='replace')
                        with self.lock:
                            self.buffer += text
                else:
                    time.sleep(0.01)
            except Exception as e:
                if self.running:
                    logger.error(f"接收数据错误: {e}")
                time.sleep(0.1)
    
    def send_command(self, command: str, wait_time: float = 1) -> bool:
        """发送命令"""
        if not self.is_connected():
            return False
        
        try:
            with self.lock:
                self.buffer = ""
            
            self.serial_port.write(f"{command}\n".encode())
            logger.debug(f"发送命令: {command}")
            self.log_console("SEND", command)
            time.sleep(wait_time)
            return True
        except Exception as e:
            logger.error(f"发送命令失败: {e}")
            return False
    
    def read_output(self, timeout: float = 2) -> str:
        """读取输出"""
        time.sleep(timeout)
        with self.lock:
            output = self.buffer
            self.buffer = ""
        if output:
            self.log_console("RECV", output)
        return output
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return bool(self.serial_port and self.serial_port.is_open)


class SSHConnection(BaseConnection):
    """SSH连接类 - 优化实现"""
    
    def __init__(self, hostname: str, username: str, password: Optional[str] = None,
                 port: int = 22, key_file: Optional[str] = None):
        super().__init__()
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.key_file = key_file
        self.client: Optional[paramiko.SSHClient] = None
        self.shell: Optional[paramiko.Channel] = None
        
    def connect(self) -> bool:
        """建立SSH连接"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_params = {
                'hostname': self.hostname,
                'port': self.port,
                'username': self.username,
                'timeout': 10
            }
            
            if self.key_file and Path(self.key_file).exists():
                connect_params['key_filename'] = self.key_file
            elif self.password:
                connect_params['password'] = self.password
            else:
                raise ConnectionError("需要提供密码或密钥文件")
            
            self.client.connect(**connect_params)
            self.shell = self.client.invoke_shell()
            self.shell.setblocking(0)
            
            # 清空初始输出
            time.sleep(1)
            self._clear_buffer()
            
            logger.info(f"SSH connection successful: {self.username}@{self.hostname}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"SSH connection failed: {e}")
            raise ConnectionError(f"SSH connection failed: {e}")
    
    def disconnect(self) -> None:
        """断开SSH连接"""
        if self.shell:
            self.shell.close()
        if self.client:
            self.client.close()
        logger.info("SSH连接已断开")
    
    def send_command(self, command: str, wait_time: float = 1) -> bool:
        """发送命令"""
        if not self.shell:
            return False
        
        try:
            self.shell.send(f"{command}\n")
            logger.debug(f"发送命令: {command}")
            self.log_console("SEND", command)
            time.sleep(wait_time)
            return True
        except Exception as e:
            logger.error(f"发送命令失败: {e}")
            return False
    
    def read_output(self, timeout: float = 2) -> str:
        """读取输出"""
        if not self.shell:
            return ""
        
        output = ""
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                if self.shell.recv_ready():
                    data = self.shell.recv(4096)
                    output += data.decode('utf-8', errors='replace')
                else:
                    time.sleep(0.1)
            except:
                time.sleep(0.1)
        
        if output:
            self.log_console("RECV", output)
        return output
    
    def _clear_buffer(self) -> None:
        """清空缓冲区"""
        while self.shell and self.shell.recv_ready():
            try:
                self.shell.recv(4096)
            except:
                break
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return bool(
            self.client and 
            self.client.get_transport() and 
            self.client.get_transport().is_active()
        )


class MultiConnection(BaseConnection):
    """多连接管理类"""
    
    def __init__(self, connections: List[BaseConnection]):
        super().__init__()
        self.connections = connections
        self.active_connections: List[BaseConnection] = []
        self.current_index = 0
        
    def connect(self) -> bool:
        """建立所有连接"""
        for i, conn in enumerate(self.connections):
            try:
                if conn.connect():
                    self.active_connections.append(conn)
                    logger.info(f"连接 {i+1}/{len(self.connections)} 成功")
            except Exception as e:
                logger.warning(f"连接 {i+1} 失败: {e}")
        
        success_count = len(self.active_connections)
        logger.info(f"成功建立 {success_count}/{len(self.connections)} 个连接")
        return success_count > 0
    
    def disconnect(self) -> None:
        """断开所有连接"""
        for conn in self.active_connections:
            try:
                conn.disconnect()
            except Exception as e:
                logger.error(f"断开连接失败: {e}")
        self.active_connections.clear()
    
    def send_command(self, command: str, wait_time: float = 1, 
                    target: Union[str, int] = 'current') -> bool:
        """发送命令到指定连接"""
        if target == 'all':
            results = [conn.send_command(command, wait_time) 
                      for conn in self.active_connections]
            return all(results)
        elif target == 'current':
            if self.active_connections:
                return self.active_connections[self.current_index].send_command(command, wait_time)
        elif isinstance(target, int) and 0 <= target < len(self.active_connections):
            return self.active_connections[target].send_command(command, wait_time)
        return False
    
    def read_output(self, timeout: float = 2, target: Union[str, int] = 'current') -> str:
        """读取指定连接的输出"""
        if target == 'all':
            outputs = []
            for i, conn in enumerate(self.active_connections):
                output = conn.read_output(timeout)
                outputs.append(f"[Connection {i}]\n{output}")
            return '\n'.join(outputs)
        elif target == 'current':
            if self.active_connections:
                return self.active_connections[self.current_index].read_output(timeout)
        elif isinstance(target, int) and 0 <= target < len(self.active_connections):
            return self.active_connections[target].read_output(timeout)
        return ""
    
    def is_connected(self) -> bool:
        """检查是否有活动连接"""
        return len(self.active_connections) > 0
    
    def switch_connection(self, index: int) -> bool:
        """切换当前连接"""
        if 0 <= index < len(self.active_connections):
            self.current_index = index
            return True
        return False
    
    def execute_on_all(self, command: str, wait_time: float = 1, 
                      read_timeout: float = 2) -> Dict[int, str]:
        """在所有连接上执行命令"""
        results = {}
        for i, conn in enumerate(self.active_connections):
            output = conn.execute_command(command, wait_time, read_timeout)
            results[i] = output
        return results


class ConnectionFactory:
    """连接工厂类"""
    
    @staticmethod
    def create_connection(connection_type: str, **kwargs) -> BaseConnection:
        """创建连接实例"""
        if connection_type == 'serial':
            return SerialConnection(**kwargs)
        elif connection_type == 'ssh':
            return SSHConnection(**kwargs)
        elif connection_type == 'multi_ssh':
            ssh_configs = kwargs.get('ssh_configs', [])
            connections = [SSHConnection(**config) for config in ssh_configs]
            return MultiConnection(connections)
        else:
            raise ValueError(f"不支持的连接类型: {connection_type}")
    
    @staticmethod
    def from_config(config: Dict[str, Any]) -> BaseConnection:
        """从配置字典创建连接"""
        connection_type = config.get('connection_type', 'serial')
        
        if connection_type == 'serial':
            return SerialConnection(
                port=config.get('port', 'COM38'),
                baudrate=config.get('baudrate', 115200),
                timeout=config.get('timeout', 1)
            )
        elif connection_type == 'ssh':
            return SSHConnection(
                hostname=config['hostname'],
                username=config['username'],
                password=config.get('password'),
                port=config.get('port', 22),
                key_file=config.get('key_file')
            )
        elif connection_type == 'multi_ssh':
            ssh_configs = config.get('ssh_configs', [])
            connections = [
                SSHConnection(
                    hostname=cfg['hostname'],
                    username=cfg['username'],
                    password=cfg.get('password'),
                    port=cfg.get('port', 22),
                    key_file=cfg.get('key_file')
                )
                for cfg in ssh_configs
            ]
            return MultiConnection(connections)
        else:
            raise ValueError(f"不支持的连接类型: {connection_type}")


@contextmanager
def create_connection(connection_type: str, **kwargs):
    """便捷的连接创建上下文管理器"""
    conn = ConnectionFactory.create_connection(connection_type, **kwargs)
    try:
        conn.connect()
        yield conn
    finally:
        conn.disconnect()