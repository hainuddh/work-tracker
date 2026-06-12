#!/bin/bash
set -e

LOGFILE="/home/admin/work-tracker/backend/proxy.log"
echo "[$(date)] ==================== 启动 HTTPS 反代 ====================" >> "$LOGFILE"

# 确保 443 端口空闲
for i in 1 2 3 4 5; do
    if ss -tlnp | grep -q ':443 '; then
        echo "[$(date)] 端口 443 仍被占用，等待... (尝试 $i/5)" >> "$LOGFILE"
        for pid in $(ss -tlnp | grep ':443 ' | grep -oP 'pid=\K[0-9]+' 2>/dev/null); do
            echo "[$(date)] 占用进程 PID=$pid" >> "$LOGFILE"
            sudo kill -9 "$pid" 2>/dev/null || true
        done
        sleep 2
    else
        echo "[$(date)] 端口 443 空闲" >> "$LOGFILE"
        break
    fi
done

# 启动反代（sudo 才能读证书目录）
cd /home/admin/work-tracker/backend
exec sudo -E python3.11 https_proxy.py >> "$LOGFILE" 2>&1
