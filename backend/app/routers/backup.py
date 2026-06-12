"""
数据备份模块 - 定时备份 + 手动触发
遵循 CMMI 数据安全管理要求
"""
import os
import shutil
import gzip
import glob
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from app.config import settings
from app.auth import get_current_user

router = APIRouter(prefix="/api/backup", tags=["数据备份"])


@router.post("/manual")
def manual_backup(
    _user: dict = Depends(get_current_user)
):
    """手动触发数据库备份"""
    backup_dir = settings.BACKUP_DIR
    os.makedirs(backup_dir, exist_ok=True)
    
    # 确定数据库文件路径
    db_url = settings.DATABASE_URL
    if "sqlite" in db_url:
        # 提取数据库文件路径
        db_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
    else:
        raise HTTPException(status_code=500, detail="仅支持SQLite数据库备份")
    
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="数据库文件不存在")
    
    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"work_tracker_backup_{timestamp}.db.gz"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    # 压缩备份
    with open(db_path, "rb") as f_in:
        with gzip.open(backup_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    return {
        "message": "备份成功",
        "backup_file": backup_filename,
        "backup_path": backup_path,
        "size": os.path.getsize(backup_path),
        "created_at": datetime.now().isoformat(),
    }


@router.get("/list")
def list_backups(
    _user: dict = Depends(get_current_user)
):
    """列出所有备份文件"""
    backup_dir = settings.BACKUP_DIR
    if not os.path.exists(backup_dir):
        return {"backups": []}
    
    backup_files = glob.glob(os.path.join(backup_dir, "*.db.gz"))
    backups = []
    for f in backup_files:
        backups.append({
            "filename": os.path.basename(f),
            "size": os.path.getsize(f),
            "created": datetime.fromtimestamp(os.path.getctime(f)).isoformat(),
        })
    backups.sort(key=lambda x: x["created"], reverse=True)
    return {"backups": backups}


@router.delete("/cleanup")
def cleanup_old_backups(
    _user: dict = Depends(get_current_user)
):
    """清理过期备份（保留最近 N 天）"""
    retention = settings.BACKUP_RETENTION_DAYS
    backup_dir = settings.BACKUP_DIR
    now = datetime.now()
    removed = 0
    
    for f in glob.glob(os.path.join(backup_dir, "*.db.gz")):
        file_date = datetime.fromtimestamp(os.path.getctime(f))
        if (now - file_date).days > retention:
            os.remove(f)
            removed += 1
    
    return {
        "message": f"已清理 {removed} 个过期备份",
        "retention_days": retention,
    }
