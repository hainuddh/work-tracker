"""
Boss API Router - 老板管理接口
遵循 CMMI 数据完整性、可追溯性要求
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Boss, Log
from app.schemas import BossCreate, BossUpdate, BossResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/bosses", tags=["老板管理"])


@router.post("/", response_model=BossResponse, status_code=201)
def create_boss(
    boss_data: BossCreate,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """
    创建老板
    
    - **name**: 姓名（必填，1-100字）
    - **phone**: 手机号（必填，唯一）
    - **remark**: 备注（选填，最多500字）
    - **unit_price**: 默认日薪（选填，>=0）
    """
    # 检查手机号是否重复
    existing = db.query(Boss).filter(
        Boss.phone == boss_data.phone,
        Boss.is_active == 1
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"手机号 {boss_data.phone} 已存在"
        )
    
    boss = Boss(
        name=boss_data.name,
        phone=boss_data.phone,
        remark=boss_data.remark or "",
        unit_price=boss_data.unit_price or 0,
    )
    db.add(boss)
    db.commit()
    db.refresh(boss)
    return boss


@router.get("/", response_model=list[BossResponse])
def list_bosses(
    skip: int = 0,
    limit: int = 100,
    search: str = "",
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """
    查询老板列表
    
    - **search**: 按姓名或手机号模糊搜索
    """
    query = db.query(Boss).filter(Boss.is_active == 1)
    if search:
        query = query.filter(
            (Boss.name.contains(search)) | (Boss.phone.contains(search))
        )
    query = query.order_by(Boss.created_at.desc())
    return query.offset(skip).limit(limit).all()


@router.get("/{boss_id}", response_model=BossResponse)
def get_boss(
    boss_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """获取单个老板详情"""
    boss = db.query(Boss).filter(
        Boss.id == boss_id,
        Boss.is_active == 1
    ).first()
    if not boss:
        raise HTTPException(status_code=404, detail="老板不存在")
    return boss


@router.put("/{boss_id}", response_model=BossResponse)
def update_boss(
    boss_id: int,
    boss_data: BossUpdate,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """
    更新老板信息
    
    支持部分更新（只传需要改的字段）
    """
    boss = db.query(Boss).filter(
        Boss.id == boss_id,
        Boss.is_active == 1
    ).first()
    if not boss:
        raise HTTPException(status_code=404, detail="老板不存在")
    
    # 检查手机号是否被其他老板占用
    if boss_data.phone:
        duplicate = db.query(Boss).filter(
            Boss.phone == boss_data.phone,
            Boss.id != boss_id,
            Boss.is_active == 1
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail=f"手机号 {boss_data.phone} 已被其他老板使用"
            )
    
    update_data = boss_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(boss, field, value)
    
    db.commit()
    db.refresh(boss)
    return boss


@router.delete("/{boss_id}")
def delete_boss(
    boss_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """
    逻辑删除老板
    
    软删除：is_active=0，保留历史记录
    注意：如果有未结清的日志，禁止删除
    """
    boss = db.query(Boss).filter(
        Boss.id == boss_id,
        Boss.is_active == 1
    ).first()
    if not boss:
        raise HTTPException(status_code=404, detail="老板不存在")
    
    # 检查是否有未结清的日志
    unsettled = db.query(Log).filter(
        Log.boss_id == boss_id,
        Log.status < 2  # 未付款
    ).count()
    if unsettled > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该老板还有 {unsettled} 条未结清日志，无法删除"
        )
    
    boss.is_active = 0
    db.commit()
    return {"message": "老板已删除"}


@router.get("/{boss_id}/stats")
def get_boss_stats(
    boss_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user)
):
    """获取老板统计汇总"""
    boss = db.query(Boss).filter(
        Boss.id == boss_id,
        Boss.is_active == 1
    ).first()
    if not boss:
        raise HTTPException(status_code=404, detail="老板不存在")
    
    logs = db.query(Log).filter(Log.boss_id == boss_id).all()
    total_days = sum(log.days for log in logs)
    total_amount = sum(log.amount for log in logs)
    
    return {
        "boss_id": boss.id,
        "boss_name": boss.name,
        "total_days": round(total_days, 2),
        "total_amount": round(total_amount, 2),
        "log_count": len(logs),
    }
