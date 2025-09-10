#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志管理模块
分离控制台输出、程序日志和SSH交互日志
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

class LoggerManager:
    """统一的日志管理器"""
    
    def __init__(self, output_dir: Path):
        """
        初始化日志管理器
        output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件路径
        self.program_log = self.output_dir / "program.log"  # 程序运行日志
        self.console_log = self.output_dir / "console.log"  # SSH控制台交互日志
        self.debug_log = self.output_dir / "debug.log"     # 调试日志
        
        # 清理已存在的处理器
        self._clear_handlers()
        
        # 设置日志格式
        self.setup_loggers()
    
    def _clear_handlers(self):
        """清理所有现有的日志处理器"""
        for logger_name in ['', 'stress_monitor', 'temperature_monitor', 
                           'connection_manager', 'config_loader']:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.setLevel(logging.DEBUG)
    
    def setup_loggers(self):
        """配置各个日志器"""
        # 1. 程序日志 - 只记录INFO及以上级别
        program_handler = logging.FileHandler(
            self.program_log, encoding='utf-8', mode='w'
        )
        program_handler.setLevel(logging.INFO)
        program_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        program_handler.setFormatter(program_formatter)
        
        # 2. 调试日志 - 记录所有级别
        debug_handler = logging.FileHandler(
            self.debug_log, encoding='utf-8', mode='w'
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        debug_handler.setFormatter(debug_formatter)
        
        # 3. 控制台输出 - 只显示重要信息
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        
        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(program_handler)
        root_logger.addHandler(debug_handler)
        root_logger.addHandler(console_handler)
        
        # 配置各个模块的日志器
        for module_name in ['stress_monitor', 'temperature_monitor', 
                           'connection_manager', 'config_loader']:
            module_logger = logging.getLogger(module_name)
            module_logger.setLevel(logging.DEBUG)
            # 不再添加处理器，使用根日志器的处理器
            module_logger.propagate = True
    
    def get_console_logger(self) -> logging.Logger:
        """获取SSH控制台日志器"""
        console_logger = logging.getLogger('ssh_console')
        console_logger.setLevel(logging.DEBUG)
        console_logger.propagate = False  # 不传播到根日志器
        
        # 清除已有处理器
        console_logger.handlers.clear()
        
        # 添加文件处理器
        handler = logging.FileHandler(
            self.console_log, encoding='utf-8', mode='w'
        )
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(message)s', 
                                    datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        console_logger.addHandler(handler)
        
        return console_logger
    
    def log_summary(self):
        """记录日志文件位置摘要"""
        logger = logging.getLogger(__name__)
        logger.info(f"日志文件已创建:")
        logger.info(f"  程序日志: {self.program_log}")
        logger.info(f"  控制台日志: {self.console_log}")
        logger.info(f"  调试日志: {self.debug_log}")

def setup_logging(output_dir: Optional[Path] = None) -> LoggerManager:
    """
    便捷函数：设置日志系统
    output_dir: 输出目录，默认为 results/当前时间
    """
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("results") / f"result_{timestamp}"
    
    manager = LoggerManager(output_dir)
    return manager