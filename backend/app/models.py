"""
数据模型定义 - 老板表 & 工作日志表
遵循数据库第三范式 (3NF)
"""
from sqlalchemy import Column, Integer, String, Text, Date, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, date
from app.database import Base


class Boss(Base):
    """老板信息表"""
    __tablename__ = "bosses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)  # 姓名
    phone = Column(String(20), nullable=False, unique=True, index=True)  # 手机号
    remark = Column(Text, default="")  # 备注
    unit_price = Column(Float, default=0)  # 默认日薪
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Integer, default=1)  # 逻辑删除标记
    
    # 关联的工作日志
    logs = relationship("Log", back_populates="boss", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Boss(id={self.id}, name='{self.name}', phone='{self.phone}')>"


class Log(Base):
    """工作日志表"""
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, index=True)
    boss_id = Column(Integer, ForeignKey("bosses.id"), nullable=False, index=True)  # 外键
    date = Column(Date, nullable=False, index=True)  # 工作日期
    location = Column(String(255), default="")  # 工作地点
    content = Column(Text, nullable=False)  # 工作内容
    days = Column(Float, default=0.5, nullable=False)  # 工数（0.5, 1, 1.5...）
    amount = Column(Float, default=0)  # 金额
    status = Column(Integer, default=0)  # 0=待确认, 1=已确认, 2=已付款
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联的老板
    boss = relationship("Boss", back_populates="logs")
    
    __table_args__ = (
        CheckConstraint("days >= 0", name="check_days_positive"),
        CheckConstraint("amount >= 0", name="check_amount_positive"),
    )
    
    def __repr__(self):
        return f"<Log(id={self.id}, date={self.date}, boss_id={self.boss_id}, days={self.days})>"
