# 分阶段进度

最后更新：2026-11-10（北京时间）。本轮严格离线分析设备 ROM，不执行真机操作。

| 阶段 | 状态 | 产物 / 验收条件 |
|---|---|---|
| 1 ROM 识别与合理解包 | 完成 | 七个目标分区通过 manifest SHA256，全部 EROFS，解出 15,061 个普通文件 |
| 2 Android 原生机制 | 完成 | 固定 android17-release 提交，已分离六项能力 |
| 3 HyperOS 限制定位 | 初步静态研究完成 | 24 组方法证据、资格与镜像调用链、渲染投票及下游模式筛选、Launcher 原生边界、HWC 符号与定向指令检查 |
| 4 补全路径评估 | 完成 | A–E 方案、权限与风险；优先次屏探针 → 最小配置 → 可逆载体 |
| 5 报告与验证计划 | 完成（静态范围） | 六份报告、未来只读采集脚本、证据完整性检查与交接；真机全部 NOT_RUN |

## 已确认

- 原始文件约 9.20 GB，为 A/B OTA，内部 `post-sdk-level=37`、Android 17、设备 popsicle。
- 没有独立 super.img；需要继续读 payload 动态分区元数据，不能据此否定动态分区。
- Windows C: 可用约 809 GB；已有 Python 3.14、Java 17、WSL Ubuntu 24.04。
- 目标远程仓库初查无 refs，工作区现已初始化 main。

## 检查点

- 建立 Git 排除规则，所有 ROM/镜像/APK/反编译输出与工具二进制保留本地。
- `6bb3a6f` 项目初始化已推送 main。
- `50d6bbb` 阶段 1 已推送；`3459949` 阶段 2 已推送。
- `1932655` 阶段 3 已推送，包含 HyperOS 限制和刷新率研究。
- `75f7ea7` 阶段 4 已推送，完成 A–E 路线与权限/风险比较。
- 阶段 1：七个分区镜像和 EROFS 提取完成；成果保存于 reports/01 和 analysis/evidence/。
- 原始 ROM 未改动；首次 NTFS 提取慢，改为隔离 WSL ext4，不删除已有输出。
- 97 个 packaged Overlay 的 aapt2 资源与 manifest 均成功扫描；运行时启用情况未测。
- MiuiHome 没有 DEX，APK 包含原生 libapp_launcher.so，并依赖 hyperos.rustruntime.v5；不能仅据 manifest 宣称次屏桌面可用。
- 已追踪 DisplayAdapter 连接设置 → DisplayModeDirector 厂商 provider → 外屏实际启用检查 → priority 24 全局 RenderVote 的条件性 60 上限。物理输出模式与高刷能力仍未知。
- 背屏 ID 1 的特殊限制与 EXTERNAL 分开，不建议全局绕过。
- 关键剩余不确定性：设备运行时状态、Launcher 原生实现、模式/EDID/DP 链路。全部进入未来验证/续研究清单，本轮不执行。

## 最终核验

- 七个目标镜像均匹配 manifest，WSL 原生 EROFS 提取完成；续跑 mi_product 已验证跳过，不重复解包。
- 24 组方法锚点/本地文件哈希、目标输入副本哈希、固定 AOSP 文件哈希一致。
- 原始 ROM 结束时 SHA256 仍等于首次清单。
- 六份报告链接、JSON、Python 编译、Git diff 空白检查通过。
- 未来采集脚本通过 PowerShell AST 检查和 `-WhatIf`；没有调用 ADB。
- Git 暂存检查排除 ROM/镜像/APK/ELF/反编译代码；本地缓存和原始文件保留。

详细检查结果见 `analysis/evidence/verification.json`。本次完成研究报告，不代表桌面、高刷或输入的功能验收已通过。
