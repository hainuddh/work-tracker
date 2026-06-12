"""
Pydantic 请求/响应模型 - 输入校验
所有外部输入必须经过此层校验，遵循 CMMI 数据完整性要求
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import date as DateType, datetime
from decimal import Decimal


# ============ 老板相关 ============

class BossCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=5, max_length=20)
    remark: str = Field(default="")
    unit_price: float = Field(default=0, ge=0)
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re
        if not re.match(r'^1[3-9]\d{9}$|^0\d{2,3}-?\d{7,8}$', v):
            raise ValueError("手机号格式不正确")
        return v


class BossUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, min_length=5, max_length=20)
    remark: Optional[str] = Field(default=None, max_length=500)
    unit_price: Optional[float] = Field(default=None, ge=0)
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re
        if not re.match(r'^1[3-9]\d{9}$|^0\d{2,3}-?\d{7,8}$', v):
            raise ValueError("手机号格式不正确")
        return v


class BossResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")}
    )
    
    id: int
    name: str
    phone: str
    remark: str
    unit_price: float
    is_active: int
    created_at: datetime
    updated_at: datetime


# ============ 日志相关 ============

class LogCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    
    boss_id: int = Field(gt=0)
    date: DateType
    location: str = Field(default="")
    content: str = Field(min_length=1)
    days: float = Field(default=0.5, ge=0.5, le=3)
    amount: float | None = Field(default=None, ge=0)
    
    @field_validator("content")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        import re
        v = re.sub(r'<[^>]+>', '', v)
        return v.strip()


class LogUpdate(BaseModel):
    date: Optional[DateType] = None
    location: Optional[str] = Field(default=None, max_length=255)
    content: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    days: Optional[float] = Field(default=None, ge=0.5, le=3)
    amount: Optional[float] = Field(default=None, ge=0)
    status: Optional[int] = Field(default=None, ge=0, le=2)


class LogResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")}
    )
    
    id: int
    boss_id: int
    boss_name: str
    date: DateType
    location: str
    content: str
    days: float
    amount: float
    status: int
    created_at: datetime
    updated_at: datetime


# ============ 统计相关 ============

class StatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    boss_id: int
    boss_name: str
    total_days: float
    total_amount: float
    log_count: int
    logs: list[LogResponse]


class ExportParams(BaseModel):
    boss_id: int | None = None
    start_date: DateType | None = None
    end_date: DateType | None = None
