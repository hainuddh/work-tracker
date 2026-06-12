"""
API 认证模块 - 微信登录 + JWT Token 鉴权
"""
import os
import json
import time
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db, SessionLocal
from app.models import User

security = HTTPBearer()


# ============ 微信登录 ============
WECHAT_CODE2SESSION = "https://api.weixin.qq.com/sns/jscode2session"


async def wechat_code2session(code: str, appid: str, secret: str) -> dict:
    """
    微信 code 换 session
    返回: {openid, unionid(可选), session_key}
    """
    params = {
        "appid": appid,
        "secret": secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(WECHAT_CODE2SESSION, params=params)
        data = resp.json()
    if "errcode" in data:
        raise HTTPException(
            status_code=400,
            detail=f"微信登录失败: {data.get('errmsg', '未知错误')}"
        )
    return data


# ============ JWT ============
def verify_token(token: str) -> dict:
    """验证 JWT Token"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        exp: datetime = datetime.fromtimestamp(payload.get("exp"))
        if exp < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Token已过期")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的Token")


def create_access_token(user_id: int, openid: str, nickname: str) -> str:
    """创建 JWT Token"""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "openid": openid,
        "nickname": nickname,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ============ 依赖注入 ============
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: SessionLocal = Depends(get_db)
) -> dict:
    """依赖注入：获取当前认证用户（从 JWT 中解析）"""
    return verify_token(credentials.credentials)


# ============ 配置 ============
def get_wechat_config():
    """从环境变量获取微信配置"""
    appid = os.getenv("WECHAT_APPID")
    secret = os.getenv("WECHAT_SECRET")
    if not appid or not secret:
        raise HTTPException(
            status_code=500,
            detail="服务器未配置微信登录参数（WECHAT_APPID / WECHAT_SECRET）"
        )
    return appid, secret
