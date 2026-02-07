# 代码搬运一致性报告（Plan595~620 -> src）

- 时间：2026-02-08 01:38:51
- 校验范围：`Training_Manual/Dev_Plans/Plan595~620.md` 中标注 `src/...` 的代码段
- 比对对象：对应 `src/...` 实际文件
- 比对方式：`SHA256 精确哈希` + `规范化哈希（去行尾空白/统一结尾换行）`

## 汇总
- checked：15
- exact_match：15
- normalized_match：15
- skipped_non_src：12
- missing_target：0
- missing_plan：0
- no_code_block：0

## 逐条结果（src）
### Plan597.md -> `src/shared/config.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `2dc4a8d4436e132a24329e2d1f1a6f3b22446b6dec46ec236606377303c32d68`
- file_hash: `2dc4a8d4436e132a24329e2d1f1a6f3b22446b6dec46ec236606377303c32d68`
- plan_norm_hash: `2dc4a8d4436e132a24329e2d1f1a6f3b22446b6dec46ec236606377303c32d68`
- file_norm_hash: `2dc4a8d4436e132a24329e2d1f1a6f3b22446b6dec46ec236606377303c32d68`

### Plan598.md -> `src/shared/models.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `61df257ee639daec3cc34f46d005b9d627c23be0c0167071c3c05264a6396f25`
- file_hash: `61df257ee639daec3cc34f46d005b9d627c23be0c0167071c3c05264a6396f25`
- plan_norm_hash: `61df257ee639daec3cc34f46d005b9d627c23be0c0167071c3c05264a6396f25`
- file_norm_hash: `61df257ee639daec3cc34f46d005b9d627c23be0c0167071c3c05264a6396f25`

### Plan599.md -> `src/shared/store.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `26c738aa352d979e324d970a39f60474cabc1c3c36306f58952fe1906ccbde12`
- file_hash: `26c738aa352d979e324d970a39f60474cabc1c3c36306f58952fe1906ccbde12`
- plan_norm_hash: `26c738aa352d979e324d970a39f60474cabc1c3c36306f58952fe1906ccbde12`
- file_norm_hash: `26c738aa352d979e324d970a39f60474cabc1c3c36306f58952fe1906ccbde12`

### Plan600.md -> `src/scheduler/service.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `80b0fe379cb240a11849b43a8f33643abd01a39688ea85d5a6ce31ac561925c0`
- file_hash: `80b0fe379cb240a11849b43a8f33643abd01a39688ea85d5a6ce31ac561925c0`
- plan_norm_hash: `80b0fe379cb240a11849b43a8f33643abd01a39688ea85d5a6ce31ac561925c0`
- file_norm_hash: `80b0fe379cb240a11849b43a8f33643abd01a39688ea85d5a6ce31ac561925c0`

### Plan601.md -> `src/orchestrator/service.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `a2dec034520f335ba5a980c003de69ca6b553de919ada7ec486ceb693cdef500`
- file_hash: `a2dec034520f335ba5a980c003de69ca6b553de919ada7ec486ceb693cdef500`
- plan_norm_hash: `a2dec034520f335ba5a980c003de69ca6b553de919ada7ec486ceb693cdef500`
- file_norm_hash: `a2dec034520f335ba5a980c003de69ca6b553de919ada7ec486ceb693cdef500`

### Plan602.md -> `src/workers/base.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `242b02f251fbc8c9f7cee5f2e8629a0910718326dfa5579bc85de420c498d038`
- file_hash: `242b02f251fbc8c9f7cee5f2e8629a0910718326dfa5579bc85de420c498d038`
- plan_norm_hash: `242b02f251fbc8c9f7cee5f2e8629a0910718326dfa5579bc85de420c498d038`
- file_norm_hash: `242b02f251fbc8c9f7cee5f2e8629a0910718326dfa5579bc85de420c498d038`

### Plan603.md -> `src/memory/service.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `d915f8716d4ea76ed87b57e15d9c406b1dd2a70cb425ae9f747e6e3815890b93`
- file_hash: `d915f8716d4ea76ed87b57e15d9c406b1dd2a70cb425ae9f747e6e3815890b93`
- plan_norm_hash: `d915f8716d4ea76ed87b57e15d9c406b1dd2a70cb425ae9f747e6e3815890b93`
- file_norm_hash: `d915f8716d4ea76ed87b57e15d9c406b1dd2a70cb425ae9f747e6e3815890b93`

### Plan604.md -> `src/kg/service.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `5fa95bfafc49d360b18addd4bd93ee7972fc1f940ad75d2f7cbb30c9585b5801`
- file_hash: `5fa95bfafc49d360b18addd4bd93ee7972fc1f940ad75d2f7cbb30c9585b5801`
- plan_norm_hash: `5fa95bfafc49d360b18addd4bd93ee7972fc1f940ad75d2f7cbb30c9585b5801`
- file_norm_hash: `5fa95bfafc49d360b18addd4bd93ee7972fc1f940ad75d2f7cbb30c9585b5801`

### Plan605.md -> `src/search/adapter.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `a8387ada09c729752e75b5186365f562dc2f89b152629fa3e2ed616358159f3c`
- file_hash: `a8387ada09c729752e75b5186365f562dc2f89b152629fa3e2ed616358159f3c`
- plan_norm_hash: `a8387ada09c729752e75b5186365f562dc2f89b152629fa3e2ed616358159f3c`
- file_norm_hash: `a8387ada09c729752e75b5186365f562dc2f89b152629fa3e2ed616358159f3c`

### Plan606.md -> `src/plugins/extension_manager.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `d469b624d2ddcf1c069ab74c945e60930682fe2cc9f84cfd39ee560c9e01f8ae`
- file_hash: `d469b624d2ddcf1c069ab74c945e60930682fe2cc9f84cfd39ee560c9e01f8ae`
- plan_norm_hash: `d469b624d2ddcf1c069ab74c945e60930682fe2cc9f84cfd39ee560c9e01f8ae`
- file_norm_hash: `d469b624d2ddcf1c069ab74c945e60930682fe2cc9f84cfd39ee560c9e01f8ae`

### Plan607.md -> `src/plugins/sandbox.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `17696643dfd476c28e010bc81cad2b07c3b8410048074fb9cb84aef005bf5de7`
- file_hash: `17696643dfd476c28e010bc81cad2b07c3b8410048074fb9cb84aef005bf5de7`
- plan_norm_hash: `17696643dfd476c28e010bc81cad2b07c3b8410048074fb9cb84aef005bf5de7`
- file_norm_hash: `17696643dfd476c28e010bc81cad2b07c3b8410048074fb9cb84aef005bf5de7`

### Plan608.md -> `src/bff/app.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `2789d890008020b7bf4e1d3722c18a04bbd06f9d29811956c85ec5f7e0ca3861`
- file_hash: `2789d890008020b7bf4e1d3722c18a04bbd06f9d29811956c85ec5f7e0ca3861`
- plan_norm_hash: `2789d890008020b7bf4e1d3722c18a04bbd06f9d29811956c85ec5f7e0ca3861`
- file_norm_hash: `2789d890008020b7bf4e1d3722c18a04bbd06f9d29811956c85ec5f7e0ca3861`

### Plan609.md -> `src/bff/security.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `e76f015d24e7ee6e4f6ae0479ceec815c8288d6e40fadab4e3844a6f5e18372e`
- file_hash: `e76f015d24e7ee6e4f6ae0479ceec815c8288d6e40fadab4e3844a6f5e18372e`
- plan_norm_hash: `e76f015d24e7ee6e4f6ae0479ceec815c8288d6e40fadab4e3844a6f5e18372e`
- file_norm_hash: `e76f015d24e7ee6e4f6ae0479ceec815c8288d6e40fadab4e3844a6f5e18372e`

### Plan610.md -> `src/bff/sse.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `d6a7eebb11255f4e85b1282359b0e13e57cc6f47bbd6f98a078d1618b31bfa22`
- file_hash: `d6a7eebb11255f4e85b1282359b0e13e57cc6f47bbd6f98a078d1618b31bfa22`
- plan_norm_hash: `d6a7eebb11255f4e85b1282359b0e13e57cc6f47bbd6f98a078d1618b31bfa22`
- file_norm_hash: `d6a7eebb11255f4e85b1282359b0e13e57cc6f47bbd6f98a078d1618b31bfa22`

### Plan611.md -> `src/shared/obs.py`
- exact_match: `True`
- normalized_match: `True`
- plan_hash: `41db34d230a36a7860f7a6c34535ae2110ef60c728bf7c1c69792f6342544ae7`
- file_hash: `41db34d230a36a7860f7a6c34535ae2110ef60c728bf7c1c69792f6342544ae7`
- plan_norm_hash: `41db34d230a36a7860f7a6c34535ae2110ef60c728bf7c1c69792f6342544ae7`
- file_norm_hash: `41db34d230a36a7860f7a6c34535ae2110ef60c728bf7c1c69792f6342544ae7`

## 跳过项（非 src 路径）
- Plan612.md -> `tests/test_smoke.py`
- Plan612.md -> `scripts/quality_gate.sh`
- Plan613.md -> `scripts/openclawd.service`
- Plan614.md -> `scripts/backup.sh`
- Plan614.md -> `scripts/restore.sh`
- Plan615.md -> `scripts/chaos_kill_scheduler.sh`
- Plan615.md -> `scripts/auto_rollback.sh`
- Plan616.md -> `.github/workflows/ci.yml`
- Plan617.md -> `scripts/bootstrap.sh`
- Plan618.md -> `docs/bug_triage.md`
- Plan619.md -> `docs/release_checklist.md`
- Plan620.md -> `docs/runbook.md`
