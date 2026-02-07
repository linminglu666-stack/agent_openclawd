# Plan17 详情（与主计划对齐）

- 对应主计划：Training_Manual/Plan17
- 主计划标题：OpenClawd 稳健 Cron 调度器（WSL 部署）需求与方案说明

## 核心要点索引（来自主计划）
2:1. 背景
6:2. 目标
7:2.1 功能目标
27:2.2 运维目标（WSL 重点）

## 计划原文摘录
OpenClawd 稳健 Cron 调度器（WSL 部署）需求与方案说明
1. 背景

OpenClawd 现有自带 Cron 调度器在稳定性、可观测、宕机恢复与系统级守护方面存在不足。目标是在 WSL 环境中，用一个更稳健、更全面的调度器替代现有 Cron，并实现系统服务级常驻与持久化（跨 WSL 关闭/Windows 重启可自动恢复）。

2. 目标
2.1 功能目标

替代 OpenClawd 内置 Cron 调度器，提供：

Cron 表达式触发

misfire（宕机错过触发）策略

并发/互斥策略

超时、重试、退避

运行记录（run）持久化审计

与 OpenClawd 汇报机制对齐：

任务进行中按周期汇报进度

任务完成后立即输出总结

2.2 运维目标（WSL 重点）

在 WSL 内具备“系统服务级”常驻能力

跨 Windows 重启/WSL 停止后可自动启动恢复

权限最小化：安装期可使用管理员权限，运行期降权到专用用户

3. 非目标

不依赖系统 cron 守护进程（不使用 crond）。

不要求任务本身具备 SDK 进度上报能力（可先用 executor 统一心跳与日志截断作为进度）。

4. 约束与现实边界（WSL 特性导致必须写清楚）

WSL 实例生命周期：当 WSL 内无前台/后台进程时，实例会停止；因此“永久常驻”需要：

WSL 内有长期运行的服务进程 且

Windows 侧在开机/登录时触发启动 WSL（否则 WSL 不会自行启动）

systemd 可用性不保证：部分 WSL 发行版/配置默认未启用 systemd，需要显式启用；若无法启用，需走“无 systemd 的替代路径”。

5. 总体方案概述（推荐：双层持久化）
5.1 核心设计

在 WSL 内提供一个常驻服务：openclawd-scheduler

采用 SQLite/WAL 持久化 jobs/runs，实现断电/退出后恢复

运行期通过 executor 执行任务并进行 OpenClawd 进度与总结汇报

5.2 WSL 场景“持久化”拆解为两层

层 A：WSL 内服务守护（Linux 维度）

优先：systemd service

备选：supervisor（runit/s6）或 nohup 守护（不推荐但可用）

层 B：Windows 侧拉起 WSL（Windows 维度）

使用 Windows Task Scheduler 在开机/登录时执行 wsl.exe -d <Distro> --exec ...

解决“Windows 重启后 WSL 不会自动运行”的问题

结论：仅做层 A 不足以覆盖“Windows 重启后自动恢复”；要满足“系统服务级持久化”，建议 A + B 同时落地。

6. 权限与安全方案（你提出的“需要写清楚权限”）
6.1 权限分层原则

安装/配置期：需要 root（或 sudo）权限，用于：

创建专用用户/组：openclawd

写入系统级服务定义（systemd unit 或替代守护配置）

创建持久化目录：/var/lib/openclawd/...、/etc/openclawd/... 并赋权

运行期：服务以低权限用户运行（User=openclawd），仅拥有必要目录读写权限。

6.2 目录与权限约束（强烈建议）

配置目录（只读为主）

/etc/openclawd/scheduler.d/：root 拥有；openclawd 只读

数据目录（持久化、可写）

/var/lib/openclawd/scheduler/：openclawd 拥有可写（SQLite/WAL 在这里）

运行时目录（socket/lock）

/run/openclawd/：由服务启动时创建，权限给 openclawd

6.3 WSL 特有安全注意

避免把数据库/锁文件放在 /mnt/c 这类 Windows 挂载盘上（权限/锁语义/性能可能不稳定）；建议使用 WSL 的 Linux 文件系统（发行版虚拟磁盘）路径，如 /var/lib/...。

7. 部署路径 A（首选）：WSL 启用 systemd + systemd service
7.1 适用条件

WSL 发行版允许启用 systemd（常见发行版可行，但不做绝对保证）。

7.2 配置要点

在 WSL 内启用 systemd（示例配置结构）

/etc/wsl.conf 关键项（示意）：

[boot]

systemd=true

在 Windows 执行 wsl.exe --shutdown 后重新进入 WSL，使配置生效。

7.3 systemd 单元（运行期降权）

/etc/systemd/system/openclawd-scheduler.service（示意）

User=openclawd

Restart=always

ReadWritePaths=/var/lib/openclawd /run/openclawd

其他 hardening 选项按需要启用

7.4 启用与验收

systemctl enable --now openclawd-scheduler

验收点：

WSL 内重启后服务自动启动

服务崩溃会自动拉起

运行记录落入 SQLite，重启后状态可追溯

8. 部署路径 B（必须项，用于跨 Windows 重启自动恢复）：Windows 任务计划拉起 WSL
8.1 适用条件

无论是否启用 systemd，都建议配置此项，以满足“Windows 重启自动恢复”。

8.2 方案描述

在 Windows Task Scheduler 创建任务：

触发器：

“At startup”（开机）或 “At log on”（登录）

操作（核心）：

执行：wsl.exe

参数（示例）：

-d <DistroName> --exec /usr/local/bin/openclawd-bootstrap

openclawd-bootstrap 职责：

如果 systemd 可用：systemctl start openclawd-scheduler

否则：以守护方式启动 openclawd-scheduler（并做 pidfile/重复启动保护）

8.3 权限说明（Windows 侧）

任务计划本身通常需要管理员创建（一次性）。

运行时可选择“使用最高权限运行”（避免因策略限制导致拉起失败）。

