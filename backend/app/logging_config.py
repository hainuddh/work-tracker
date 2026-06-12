"""
日志配置 - 按天分割，可配置等级
格式参考: 000019|D|2121682|mysqlGlb*|118| : Success xx
"""
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime


def _get_log_level(level_str: str) -> int:
    """字符串转日志等级"""
    level_str = level_str.upper().strip()
    mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
    }
    return mapping.get(level_str, logging.INFO)


def setup_logging():
    """初始化全局日志配置"""
    log_level = _get_log_level(
        os.getenv('LOG_LEVEL', 'INFO')
    )
    log_dir = os.getenv('LOG_DIR', '/home/admin/work-tracker/backend/logs')
    os.makedirs(log_dir, exist_ok=True)

    class CustomFormatter(logging.Formatter):
        _seq = 0

        def format(self, record):
            CustomFormatter._seq += 1
            seq = f"{CustomFormatter._seq:06d}"

            level_map = {
                logging.DEBUG: 'D',
                logging.INFO: 'I',
                logging.WARNING: 'W',
                logging.ERROR: 'E',
                logging.CRITICAL: 'C',
            }
            level = level_map.get(record.levelno, '?')

            timestamp = int(record.created)

            module = record.name.split('.')[-1] if record.name else ''
            module = module[:8] if module else 'MAIN'

            file_info = f"{record.filename}:{record.lineno}" if hasattr(record, 'lineno') else ''

            msg = record.getMessage()

            return f"{seq}|{level}|{timestamp}|{module}|{file_info}| : {msg}"

    # 控制台
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(CustomFormatter())

    # 文件 - 按天分割
    log_file = os.path.join(log_dir, 'app.log')
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',
        interval=1,
        backupCount=90,
        encoding='utf-8',
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(CustomFormatter())

    # 根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # 降低第三方库日志级别
    for lib in ['uvicorn', 'starlette', 'sqlalchemy', 'fastapi']:
        logging.getLogger(lib).setLevel(logging.WARNING)

    logging.getLogger(__name__).info("日志系统初始化: level=%s, dir=%s",
                                     logging.getLevelName(log_level), log_dir)


def get_logger(name: str) -> logging.Logger:
    """获取命名logger"""
    return logging.getLogger(name)
