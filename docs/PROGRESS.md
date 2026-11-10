# 分阶段进度

最后更新：2026-11-10（北京时间）。本轮严格离线分析设备 ROM，不执行真机操作。

| 阶段 | 状态 | 产物 / 验收条件 |
|---|---|---|
| 1 ROM 识别与合理解包 | 完成 | 七个目标分区通过 manifest SHA256，全部 EROFS，解出 15,061 个普通文件 |
| 2 Android 原生机制 | 报告已完成，待阶段提交 | 固定 android17-release 提交，已分离六项能力 |
| 3 HyperOS 限制定位 | 进行中 | 已确认桌面资格门控、镜像恢复调用链、SECONDARY_HOME；继续 vendor/Overlay/本地代码 |
| 4 补全路径评估 | 待开始 | A–E 方案、权限与风险、优先顺序 |
| 5 报告与验证计划 | 待开始 | 六份报告、待验证事项、可交接状态 |

## 已确认

- 原始文件约 9.20 GB，为 A/B OTA，内部 `post-sdk-level=37`、Android 17、设备 popsicle。
- 没有独立 super.img；需要继续读 payload 动态分区元数据，不能据此否定动态分区。
- Windows C: 可用约 809 GB；已有 Python 3.14、Java 17、WSL Ubuntu 24.04。
- 目标远程仓库初查无 refs，工作区现已初始化 main。

## 检查点

- 建立 Git 排除规则，所有 ROM/镜像/APK/反编译输出与工具二进制保留本地。
- `6bb3a6f` 项目初始化已推送 main。
- 阶段 1：七个分区镜像和 EROFS 提取完成；成果保存于 reports/01 和 analysis/evidence/。
- 原始 ROM 未改动；首次 NTFS 提取慢，改为隔离 WSL ext4，不删除已有输出。
- 97 个 packaged Overlay 的 aapt2 资源与 manifest 均成功扫描；运行时启用情况未测。
- MiuiHome 没有 DEX，APK 包含原生 libapp_launcher.so，并依赖 hyperos.rustruntime.v5；不能仅据 manifest 宣称次屏桌面可用。
