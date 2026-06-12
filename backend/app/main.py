"""
FastAPI 入口文件 - 路由注册、启动配置、登录接口
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.config import settings
from app.database import init_db
from app.middleware import add_middleware
from app.routers import bosses, logs, backup
from app.auth import create_access_token, verify_password, hash_password, DEFAULT_ADMIN_HASH


# ============ 生命周期 ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库，关闭时清理资源"""
    # 初始化数据库表
    init_db()
    
    # 检查管理员首次登录
    from app.database import SessionLocal
    from app.models import Boss
    db = SessionLocal()
    try:
        admin_hint = os.path.join(os.path.dirname(__file__), ".admin_initialized")
        if not os.path.exists(admin_hint):
            print("=" * 50)
            print("首次启动：默认管理员密码为 admin123")
            print("请及时修改！登录后访问 /api/auth/change-password 修改密码。")
            print("=" * 50)
    finally:
        db.close()
    
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


# ============ 认证接口 ============
@app.post("/api/auth/login")
def login(password: str):
    """
    管理员登录，返回 JWT Token
    
    - **password**: 管理员密码
    - 默认密码: admin123
    """
    if verify_password(password, DEFAULT_ADMIN_HASH):
        token = create_access_token("admin")
        return {"token": token, "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}
    raise HTTPException(status_code=401, detail="密码错误")


@app.post("/api/auth/change-password")
def change_password(
    old_password: str,
    new_password: str,
    _user: dict = Depends(lambda: {"username": "admin"}),
):
    """
    修改管理员密码
    
    - **old_password**: 旧密码
    - **new_password**: 新密码（>=6位）
    """
    global DEFAULT_ADMIN_HASH
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")
    
    if not verify_password(old_password, DEFAULT_ADMIN_HASH):
        raise HTTPException(status_code=401, detail="旧密码错误")
    
    DEFAULT_ADMIN_HASH = hash_password(new_password)
    
    # 标记已初始化（不再提示默认密码）
    hint_path = os.path.join(os.path.dirname(__file__), ".admin_initialized")
    with open(hint_path, "w") as f:
        f.write("initialized")
    
    return {"message": "密码修改成功"}


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
            "auth": "/api/auth/login",
            "docs": "/docs",
        }
    }
