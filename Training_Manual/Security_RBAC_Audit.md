# Security / RBAC / Audit

## 1. 权限原则
- 安装期可 root。
- 运行期最小权限（`openclawd`）。
- 默认拒绝，按角色放行。

## 2. 角色
- `admin`: 全权限，含高风险操作。
- `editor`: 创建/修改 schedule、run 控制。
- `operator`: 查看运行与日志、有限控制。
- `viewer`: 只读。

## 3. 高风险操作
- `nodeRun:skip`
- `run:force_cancel`
- `policy:update`
- `path_contract:change`

以上操作需二次确认并写审计日志。

## 4. 审计要求
- 不可篡改审计链：append-only + hash 链。
- 审计字段：`who/when/ip/action/resource/result/reason`。
- 审计保留：180 天。
