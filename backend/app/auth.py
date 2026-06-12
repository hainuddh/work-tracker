"""
API 认证模块 - JWT Token 鉴权
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.database import get_db, SessionLocal
from sqlalchemy import text

security = HTTPBearer()


def _hash_password(password: str) -> str:
    """用 bcrypt 哈希密码，返回 $2b$ 开头的字符串"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# 内置管理员密码哈希（首次登录修改）
DEFAULT_ADMIN_HASH = _hash_password("admin123")


def verify_token(token: str) -> dict:
    """验证 JWT Token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        exp: datetime = datetime.fromtimestamp(payload.get("exp"))
        if exp < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Token已过期")
        return {"username": username, "exp": exp}
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的Token")


def create_access_token(username: str) -> str:
    """创建 JWT Token"""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def hash_password(password: str) -> str:
    return _hash_password(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _verify_password(plain, hashed)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: SessionLocal = Depends(get_db)
) -> dict:
    """依赖注入：获取当前认证用户"""
    return verify_token(credentials.credentials)
