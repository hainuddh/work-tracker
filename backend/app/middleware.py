"""
中间件 - 请求日志、CORS、限流
"""
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from collections import defaultdict
from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单限流中间件"""
    def __init__(self, app, limit: int = 60, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        # 清理过期记录
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if now - t < self.window
        ]
        if len(self.requests[client_ip]) >= self.limit:
            return Response(
                "请求过于频繁，请稍后再试",
                status_code=429
            )
        self.requests[client_ip].append(now)
        return await call_next(request)


def add_middleware(app):
    """注册中间件"""
    # CORS - 允许小程序和任意来源（小程序直连服务器IP）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        print(f"[{request.method}] {request.url.path} -> {response.status_code} ({duration:.3f}s)")
        return response
    
    # 限流
    try:
        app.add_middleware(RateLimitMiddleware, limit=settings.RATE_LIMIT_PER_MINUTE)
    except Exception:
        pass  # 限流非核心功能，失败不影响主流程
