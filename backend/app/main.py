"""
FastAPI 入口文件 - 路由注册、启动配置、微信登录接口
"""
from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
import httpx
from datetime import datetime

from app.config import settings
from app.database import init_db, SessionLocal
from app.middleware import add_middleware
from app.logging_config import setup_logging
from app.routers import bosses, logs, backup
from app.auth import (
    create_access_token, verify_token, get_current_user,
    get_wechat_config, wechat_code2session
)
from app.models import User


# ============ 生命周期 ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化日志、数据库，关闭时清理资源"""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("应用启动")
    
    # 初始化数据库表
    init_db()
    
    # 初始化第一个微信管理员
    from app.auth import get_wechat_config
    try:
        appid, secret = get_wechat_config()
        # 检查是否已有用户
        db = SessionLocal()
        try:
            user_count = db.query(User).count()
            if user_count == 0:
                logger.info("首次启动：请先用微信登录创建管理员账号")
                logger.info("小程序扫码授权后会自动创建第一个用户")
        finally:
            db.close()
    except HTTPException:
        # 未配置微信参数，跳过
        pass
    
    yield
    
    print("工作日志系统已关闭")


# ============ 应用实例 ============
app = FastAPI(
    title="工作日志系统",
    description="老板工作日志管理 - 记录、统计、导出",
    version="1.0.0",
    lifespan=lifespan,
)

# 注册中间件
add_middleware(app)

# 注册路由
app.include_router(bosses.router)
app.include_router(logs.router)
app.include_router(backup.router)


# ============ 微信登录接口 ============
@app.post("/api/auth/wechat-login")
async def wechat_login(code: str = Body(..., embed=True)):
    """
    微信登录：小程序 code 换取 JWT Token
    
    - **code**: 小程序 wx.login() 返回的临时授权码
    
    流程：
    1. 后端用 code 向微信换取 openid
    2. 查找或创建用户记录
    3. 返回 JWT Token + 用户信息
    
    注意：前端需要先通过 wx.getUserProfile 获取 nickname/avatar，
    然后在登录成功后调用 /api/auth/update-profile 更新
    """
    appid, secret = get_wechat_config()
    
    # 微信 code 换 openid
    session_data = await wechat_code2session(code, appid, secret)
    openid = session_data["openid"]
    unionid = session_data.get("unionid")
    
    # 查找或创建用户
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.openid == openid).first()
        if not user:
            user = User(openid=openid, unionid=unionid, nickname="微信用户")
            db.add(user)
            db.commit()
            db.refresh(user)
            logging.getLogger("auth").info("新用户注册: openid=%s", openid)
        
        # 创建 JWT
        token = create_access_token(user.id, user.openid, user.nickname)
        
        return {
            "token": token,
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "openid": user.openid,
                "nickname": user.nickname,
                "avatar_url": user.avatar_url,
            }
        }
    finally:
        db.close()


# ============ 更新用户资料 ============
@app.post("/api/auth/update-profile")
async def update_profile(
    nickname: str = "",
    avatar_url: str = "",
    _user: dict = Depends(get_current_user)
):
    """
    更新当前登录用户的昵称和头像
    """
    db = SessionLocal()
    try:
        # 从 JWT 中获取用户 ID
        user_id = int(_user.get("sub", 0))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        if nickname:
            user.nickname = nickname
        if avatar_url:
            user.avatar_url = avatar_url
        
        user.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "message": "更新成功",
            "user": {
                "nickname": user.nickname,
                "avatar_url": user.avatar_url,
            }
        }
    finally:
        db.close()


# ============ 获取当前用户信息 ============
@app.get("/api/auth/me")
async def get_me(
    user: dict = Depends(get_current_user)
):
    """获取当前登录用户信息"""
    db = SessionLocal()
    try:
        user_id = int(user.get("sub", 0))
        u = db.query(User).filter(User.id == user_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="用户不存在")
        return {
            "id": u.id,
            "openid": u.openid,
            "nickname": u.nickname,
            "avatar_url": u.avatar_url,
        }
    finally:
        db.close()


# ============ 健康检查 ============
@app.get("/api/health")
def health_check():
    """系统健康检查"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "endpoints": {
            "bosses": "/api/bosses/",
            "logs": "/api/logs/",
            "backup": "/api/backup/",
            "auth": "/api/auth/wechat-login",
            "docs": "/docs",
        }
    }
