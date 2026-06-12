#!/bin/bash
# HTTPS 反代守护脚本 - 自动重启 + 日志输出
set -e

LOGFILE="/home/admin/work-tracker/backend/proxy.log"

echo "[$(date)] 启动 HTTPS 反代..." >> "$LOGFILE"

# 检查旧进程
pkill -f "https_proxy.py" 2>/dev/null || true
sleep 1

# 持续运行并自动重启
while true; do
    echo "[$(date)] 启动 https_proxy.py (PID $$)..." >> "$LOGFILE"
    # 前台运行，sudo 需要读证书
    sudo -E python3.11 /home/admin/work-tracker/backend/https_proxy.py 2>> "$LOGFILE"
    
    exit_code=$?
    echo "[$(date)] 进程退出，exit_code=$exit_code" >> "$LOGFILE"
    
    # 如果不是手动退出(143=SIGHUP)，等待后重启
    if [ $exit_code -ne 143 ] && [ $exit_code -ne 0 ]; then
        echo "[$(date)] 5秒后重启..." >> "$LOGFILE"
        sleep 5
    else
        echo "[$(date)] 正常退出，不重启" >> "$LOGFILE"
        break
    fi
done
