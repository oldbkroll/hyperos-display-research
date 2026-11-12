# 分阶段进度

最后更新：2026-11-12（北京时间）。离线已核对 Dart 启动与多视图窗口的落屏链。已查的次屏 HOME 回调没有把自己的窗口接到 Flutter scene。D10 测试模块已停用，设备恢复 1440p60 镜像。[AOT 入口与窗口归属](../reports/20-secondary-home-aot-entry.md)

## 已接受的后续计划

[原生外接桌面接通与兼容性修复计划](NATIVE_EXTERNAL_DESKTOP_PLAN.md) 已推送（`5cc4c75`）。目标为复用系统自带桌面与窗口组件，不依赖第三方桌面。真机原始数据保留本地，公开结论见[报告 13](../reports/13-device-display-baseline.md)。

| 原生计划阶段 | 状态 | 交付 / 下一步 |
|---|---|---|
| 1 统一证据 | 分析完成 | [N1–N6 证据矩阵、对照与缺项](../reports/07-native-desktop-evidence-matrix.md) |
| 2 追踪原生调用链 | `PARTIAL` | 已定位主屏 Flutter 宿主、Surface 绑定、Dart 启动和多视图桥。已查次屏回调没有接入。独立次屏内容入口、点击启动与任务归属仍待查。[AOT 入口](../reports/20-secondary-home-aot-entry.md) · [应用落屏](../reports/12-native-secondary-home-display-routing.md) |
| 3 设计最小改动 | `PARTIAL`，条件设计已交付 | A 优先评估、B 保留。两条路线都需要次屏 HOME 的窗口到内容 scene 的绑定，下一步离线评估可复用的 scene 工厂与窗口生命周期。[路线准入、单变量实验和恢复](../reports/09-native-desktop-minimal-design.md) |
| 4 真机基线 | `PARTIAL` | 已采镜像、断开和插线待选，核对 ROM、资格、HOME、EDID 和模式。有线 ADB 和一次 RescueBrick 回退已实测。外屏窗口写入归属仍待验。 |
| 5 原生桌面 | `PARTIAL` | D9 确认外屏可复用背屏组的 `DOZE/OFF`。D10 在组 0、外屏 ON 时确认计算器出帧，次屏 HOME 初建及重建后均无可绘制内容。静态确认超时后的空事务完成路径，次屏首个 buffer 的入队和 latch 待验证。[电源对照](../reports/17-external-desktop-power-and-composition-control.md) · [首帧对照](../reports/19-secondary-home-render-host.md) |
| 6 尺寸和高刷 | `PARTIAL` | 1440p60 与 OSD 一致。精确 120 Hz 偏好已匹配但 DMS 目标维持 60。1440p50 和精确 1080p60 请求到达 SF 后触发外屏警告，HWC 维持 1440p60。 |
| 7 回归与恢复 | `PARTIAL` | 镜像拔插、锁屏唤醒、测试 Overlay 卸载和停用恢复均通过。独立桌面的输入、背屏功能仍待验。 |

阶段 2 首次检查点为 `340875d`，阶段 3 条件设计为 `95a3972`，次屏回调和窗口归属检查点为 `fcbbd7c`、`f0efdd5`。静态检查点校验了 31 条方法证据、九个回调槽位、启动分支及指标向量析构重定位。

下表保留首轮研究阶段状态，不表示后续原生桌面实施与功能验收已经完成。

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
