# 工作日志系统 (Work Tracker)

老板工作日志管理小程序 + FastAPI 后端。

## 功能

- 老板信息管理（增删改查，逻辑删除）
- 工作日志记录（按日期、老板、状态筛选）
- 统计汇总（按老板维度统计工数和金额）
- 数据导出（Excel / CSV / JSON）
- 数据备份（手动触发，压缩存储）
- 微信小程序前端

## 技术栈

- **后端:** Python FastAPI + SQLAlchemy + SQLite
- **前端:** 微信小程序
- **部署:** Docker / 直接运行

## 快速启动

```bash
# 直接运行后端
cd backend
export DATABASE_URL=sqlite:///./data/work_tracker.db
export SECRET_KEY=your-secret-key-here
export PORT=8000
PYTHONPATH=. python3.11 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Docker 启动
docker compose up -d --build
```

## API 接口

| 接口 | 说明 |
|------|------|
| `POST /api/auth/login` | 管理员登录 |
| `GET /api/bosses/` | 老板列表 |
| `POST /api/bosses/` | 创建老板 |
| `GET /api/logs/` | 日志列表 |
| `POST /api/logs/` | 创建日志 |
| `POST /api/logs/stats` | 统计汇总 |
| `POST /api/logs/export` | 导出数据 |
| `POST /api/backup/manual` | 手动备份 |
| `GET /api/health` | 健康检查 |

## 默认管理员

- 密码: `admin123`
- 登录后请立即修改密码
