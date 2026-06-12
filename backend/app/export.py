"""
Excel 导出模块 - 使用 openpyxl 生成标准 .xlsx 文件
支持样式、合并单元格、自适应列宽
"""
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from app.models import Log


def export_to_excel(logs: list[Log]):
    """生成带样式的 Excel 文件"""
    wb = Workbook()
    ws = wb.active
    ws.title = "工作日志"
    
    # 样式定义
    header_font = Font(name="微软雅黑", bold=True, size=12, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )
    money_font = Font(name="微软雅黑", size=11, color="C00000", bold=True)
    
    # 表头
    headers = ["序号", "日期", "老板", "工作地点", "工作内容", "工数", "金额(元)", "状态", "创建时间"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
    
    # 数据行
    status_map = {0: "待确认", 1: "已确认", 2: "已付款"}
    from app.database import SessionLocal
    from app.models import Boss
    db = SessionLocal()
    
    for row, log in enumerate(logs, 2):
        boss = db.query(Boss).filter(Boss.id == log.boss_id).first()
        values = [
            row - 1,
            log.date.strftime("%Y-%m-%d"),
            boss.name if boss else "未知",
            log.location or "",
            log.content,
            log.days,
            log.amount,
            status_map.get(log.status, "未知"),
            log.created_at.strftime("%Y-%m-%d %H:%M") if log.created_at else "",
        ]
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")
            if col == 7:  # 金额列红色加粗
                cell.font = money_font
    
    db.close()
    
    # 自适应列宽
    for col_idx, column in enumerate(ws.columns, 1):
        max_length = 0
        column_letter = get_column_letter(col_idx)
        for cell in column:
            try:
                cell_len = len(str(cell.value or ""))
                if cell_len > max_length:
                    max_length = cell_len
            except:
                pass
        adjusted_width = min(max_length + 4, 50)
        ws.column_dimensions[column_letter].width = max(adjusted_width, 10)
    
    # 冻结首行
    ws.freeze_panes = "A2"
    
    # 保存
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    from fastapi import Response
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=work_logs.xlsx"}
    )
