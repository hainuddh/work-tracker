"""
Work Log API Router - 工作日志接口
支持 CRUD、按老板/日期筛选、统计汇总、导出Excel
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional
from datetime import date, datetime
from io import BytesIO
import csv
import json
from app.database import get_db
from app.models import Boss, Log
from app.schemas import LogCreate, LogUpdate, LogResponse, StatsResponse
from app.auth import get_current_user
from app.export import export_to_excel

router = APIRouter(prefix="/api/logs", tags=["工作日志"])


@router.post("/", response_model=LogResponse, status_code=201)
def create_log(
    log_data: LogCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """
    创建工作日志
    
    - **boss_id**: 老板ID（必填）
    - **date**: 工作日期（必填）
    - **location**: 工作地点（选填）
    - **content**: 工作内容（必填，1-2000字）
    - **days**: 工数（选填，默认0.5，范围0.5-3）
    - **amount**: 金额（选填，不填则按老板日薪计算）
    """
    # 验证老板存在
    boss = db.query(Boss).filter(
        Boss.id == log_data.boss_id,
        Boss.is_active == 1
    ).first()
    if not boss:
        raise HTTPException(status_code=404, detail="老板不存在或已被删除")
    
    # 自动计算金额
    amount = log_data.amount if log_data.amount is not None else boss.unit_price * log_data.days
    
    log = Log(
        boss_id=log_data.boss_id,
        date=log_data.date,
        location=log_data.location or "",
        content=log_data.content,
        days=log_data.days,
        amount=round(amount, 2),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    
    # 返回时附加老板名称
    result = log.__dict__.copy()
    result["boss_name"] = boss.name
    return LogResponse(**result)


@router.get("/", response_model=list[LogResponse])
def list_logs(
    boss_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    status: Optional[int] = None,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """
    查询工作日志列表
    
    - **boss_id**: 按老板筛选
    - **start_date**: 起始日期
    - **end_date**: 结束日期
    - **status**: 状态筛选(0=待确认,1=已确认,2=已付款)
    """
    query = db.query(Log).join(Boss).filter(
        Boss.is_active == 1
    )
    
    if boss_id:
        query = query.filter(Log.boss_id == boss_id)
    if start_date:
        query = query.filter(Log.date >= start_date)
    if end_date:
        query = query.filter(Log.date <= end_date)
    if status is not None:
        query = query.filter(Log.status == status)
    
    query = query.order_by(Log.date.desc(), Log.created_at.desc())
    return query.offset(skip).limit(limit).all()


@router.get("/{log_id}", response_model=LogResponse)
def get_log(
    log_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """获取单个日志详情"""
    log = db.query(Log).filter(Log.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    boss = db.query(Boss).filter(Boss.id == log.boss_id).first()
    result = log.__dict__.copy()
    result["boss_name"] = boss.name if boss else "未知"
    return LogResponse(**result)


@router.put("/{log_id}", response_model=LogResponse)
def update_log(
    log_id: int,
    log_data: LogUpdate,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """更新工作日志（支持部分更新）"""
    log = db.query(Log).filter(Log.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    update_data = log_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(log, field, value)
    
    # 如果修改了days或boss，重新计算金额
    if "days" in update_data or "boss_id" in update_data:
        boss = db.query(Boss).filter(Boss.id == log.boss_id).first()
        if boss and (log_data.amount is None):
            log.amount = round(boss.unit_price * log.days, 2)
    
    db.commit()
    db.refresh(log)
    
    boss = db.query(Boss).filter(Boss.id == log.boss_id).first()
    result = log.__dict__.copy()
    result["boss_name"] = boss.name if boss else "未知"
    return LogResponse(**result)


@router.delete("/{log_id}")
def delete_log(
    log_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """删除工作日志（物理删除，有提醒）"""
    log = db.query(Log).filter(Log.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    db.delete(log)
    db.commit()
    return {"message": "日志已删除"}


@router.post("/stats")
def get_stats(
    boss_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """
    按老板维度统计汇总
    
    返回每个老板的：总工数、总金额、日志条数
    """
    query = db.query(Log).join(Boss).filter(Boss.is_active == 1)
    
    if boss_id:
        query = query.filter(Log.boss_id == boss_id)
    if start_date:
        query = query.filter(Log.date >= start_date)
    if end_date:
        query = query.filter(Log.date <= end_date)
    
    logs = query.all()
    
    # 按老板分组统计
    stats = {}
    for log in logs:
        bid = log.boss_id
        if bid not in stats:
            boss = db.query(Boss).filter(Boss.id == bid).first()
            stats[bid] = {
                "boss_id": bid,
                "boss_name": boss.name if boss else "未知",
                "total_days": 0,
                "total_amount": 0,
                "log_count": 0,
            }
        stats[bid]["total_days"] += log.days
        stats[bid]["total_amount"] += log.amount
        stats[bid]["log_count"] += 1
    
    # 取每个老板的所有日志详情
    for bid, stat in stats.items():
        log_query = db.query(Log).filter(Log.boss_id == bid)
        if start_date:
            log_query = log_query.filter(Log.date >= start_date)
        if end_date:
            log_query = log_query.filter(Log.date <= end_date)
        stat["logs"] = log_query.all()
    
    return list(stats.values())


@router.post("/export")
def export_logs(
    boss_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    fmt: str = Query(default="xlsx", regex="^(xlsx|csv|json)$"),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """
    导出工作日志
    
    - **fmt**: 格式 (xlsx/csv/json)
    - 支持按老板、日期范围筛选
    """
    query = db.query(Log).join(Boss).filter(Boss.is_active == 1)
    
    if boss_id:
        query = query.filter(Log.boss_id == boss_id)
    if start_date:
        query = query.filter(Log.date >= start_date)
    if end_date:
        query = query.filter(Log.date <= end_date)
    
    query = query.order_by(Log.date.asc())
    logs = query.all()
    
    if not logs:
        raise HTTPException(status_code=404, detail="没有符合条件的日志")
    
    if fmt == "csv":
        return _export_csv(logs, db)
    elif fmt == "json":
        return _export_json(logs)
    else:
        return _export_xlsx(logs)


def _export_csv(logs, db):
    """导出为CSV（Excel可打开，中文BOM头）"""
    output = BytesIO()
    output.write(b'\xef\xbb\xbf')  # UTF-8 BOM
    writer = csv.writer(output)
    writer.writerow(["日期", "老板", "工作地点", "工作内容", "工数", "金额", "状态", "创建时间"])
    
    status_map = {0: "待确认", 1: "已确认", 2: "已付款"}
    for log in logs:
        boss = db.query(Boss).filter(Boss.id == log.boss_id).first()
        writer.writerow([
            log.date.strftime("%Y-%m-%d"),
            boss.name if boss else "未知",
            log.location or "",
            log.content,
            log.days,
            log.amount,
            status_map.get(log.status, "未知"),
            log.created_at.strftime("%Y-%m-%d %H:%M") if log.created_at else ""
        ])
    
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=work_logs.csv"}
    )


def _export_json(logs):
    """导出为JSON"""
    import json
    data = []
    for log in logs:
        data.append({
            "date": str(log.date),
            "boss": log.boss.name if log.boss else "未知",
            "location": log.location,
            "content": log.content,
            "days": log.days,
            "amount": log.amount,
            "status": log.status,
            "created_at": str(log.created_at) if log.created_at else "",
        })
    return StreamingResponse(
        json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=work_logs.json"}
    )


def _export_xlsx(logs):
    """导出为Excel（支持转发给老板/微信）"""
    return export_to_excel(logs)
