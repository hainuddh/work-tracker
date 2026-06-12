"""
应用配置 - 从环境变量读取，遵循 12-Factor App 原则
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # 数据库
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./work_tracker.db")
    
    # 安全
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-to-a-random-string-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天
    
    # 服务器
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    # 备份
    BACKUP_DIR = os.getenv("BACKUP_DIR", "./backup")
    BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
    
    # 限流
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

settings = Settings()
