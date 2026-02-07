# Plan613 WSL/systemd/Windows 启动链

## 目标
跨重启自动恢复。

## 代码（`scripts/openclawd.service`）
```ini
[Unit]
Description=OpenClawd Scheduler
After=network.target

[Service]
User=openclawd
ExecStart=/usr/bin/python -m src.scheduler.service
Restart=always

[Install]
WantedBy=multi-user.target
```

## 代码（Windows Task 示例命令）
```powershell
wsl.exe -d <DistroName> --exec /usr/bin/systemctl start openclawd.service
```

## 验收
- Windows 重启后服务可拉起
