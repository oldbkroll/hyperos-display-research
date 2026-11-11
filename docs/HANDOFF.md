# 交接入口

先读 `docs/maintask.md`、`docs/PROGRESS.md`，再读各阶段报告。不要从压缩包文件名推断版本；以 `analysis/evidence/rom-inventory.json` 为准。

## 已接受的后续方向

计划 `5cc4c75`、阶段 1 `2971527`、阶段 2 首次检查点 `340875d`、阶段 3 条件设计 `95a3972`、次屏回调检查点 `fcbbd7c`。阶段 2/3 仍为 `PARTIAL`。[原生计划](NATIVE_EXTERNAL_DESKTOP_PLAN.md) · [证据矩阵](../reports/07-native-desktop-evidence-matrix.md) · [调用图](../reports/08-native-desktop-call-chain.md) · [条件设计](../reports/09-native-desktop-minimal-design.md)

## 当前下一步

1. 离线接续从 `0x77a130` 的间接调用追查窗口回调实参，再定位次屏应用启动与目标显示传递。现有证据用 `python scripts/verify_native_desktop.py --local` 复核。[次屏 HOME 生命周期](../reports/10-native-secondary-home-lifecycle.md)
2. 阶段 4 先采断开及镜像的只读基线，确认真实 EXTERNAL、有效资格、HOME 解析、共享装饰绑定和恢复条件。按 task 和 transition 关联实际写入的实验留待基线之后。[外屏窗口归属](../reports/11-native-desktop-window-ownership.md)

## 首轮研究交接

1. 七个优先分区已完整提取，**不要重新从头解包**。完整根目录由 `extracted/native-files.json` 定位；NTFS system_ext 为中止输出，不是权威目录。
2. 已有本地 Java 分析输出在 `analysis/local/jadx/`；组件原文件哈希见 `analysis/evidence/components.json` 和 `input-copies.json`。
3. AOSP 已固定 `94b4c163b7dfe5ce3607f7bb8456f9573f7de57d`；reports/03、04 已完成初步研究并推送（1932655），后续补充 VoteSummary 下游筛选，共 24 组方法证据。
4. JADX 在没有本 ROM framework-res 时会把 android.R 常量误标，必须用数值 ID 和 aapt2 输出核对。SelectiveJadx 默认禁用常量替换。
5. MiuiHome 没有 DEX，SECONDARY_HOME 仅证明声明存在；原生行为未恢复，后续结论保持边界。
6. 方案比较见 reports/05：优先验证次屏 Activity，再做最小配置对照。不要直接制作高刷/桌面“全开”模块。

## 本轮已交付与下一轮边界

- 六份报告、可续做脚本、24 组方法定位、97 个 Overlay 清单、工具和哈希均已保存；按阶段推送到 origin/main。
- 阶段提交：初始化 6bb3a6f；阶段 1 50d6bbb；阶段 2 3459949；阶段 3 1932655；阶段 4 75f7ea7。阶段 5 以当前 Git HEAD 为准，避免交接文档引用自身提交形成循环。
- 先运行 `python scripts/verify_research.py --local` 核对本地证据；没有必要重下工具或重解 ROM。
- 默认仍只允许静态研究。`scripts/collect_readonly.ps1` 是未来计划，**未运行，后续未获得新的设备操作授权前也不得运行**。本轮仅用 -WhatIf 和 AST 检查验证。
- 无手机时仍可继续：恢复 MiuiHome 的 libapp_launcher.so 中 SECONDARY_HOME 控制流；跟进 ExternalScreenCompatPolicy/controller 配置；定位 vendor 模式选择与 hdmi_cfg_idx 解析。不要把未完成的原生逆向写成已经确认的行为。
- 需要设备的未知项集中在 reports/06：运行时 Overlay/资格/模式投票、外屏 Activity/桌面、输入、EDID/HWC/OSD、恢复。全部 NOT_RUN。
- 只读核验记录见 analysis/evidence/verification.json；源码、指令及完整日志位于 analysis/local，不能提交公共仓库。

## 关键结论与避免误用

- 基础 desktop 资格资源 false；原生 desktop/projected/content-mode flags true；helper 与 Shell 两侧均有资格门控。
- DMS 的 SecondaryDisplayPolicy 可恢复 mirror_built_in_display，旧 force desktop 路径在新内容模式管理下不适用。
- 厂商 DisplayAdapter 写连接设置，DisplayModeDirectorImpl 在外屏实际 enabled 且 BSP 属性为 0 时提交 priority 24 全局 **RenderVote 0–60**；不是直接证明 HWC 物理 60 Hz。
- isDisplayReadyForMirroring 的实际方法只看 boot/type/enabled，不检查当前内容模式；不能凭方法名推断只影响镜像。
- ID 1 的背屏限制必须保留，EXTERNAL 要从实际显示表识别。
- ExternalScreenCompatManager 涉及 Activity/Insets 缩放，默认门控 false；它不等于镜像黑边或输出分辨率修复。

## 约束

- 不使用 ADB，不安装模块，不修改设备；必须真机的项目加入验证计划。
- 关键结论区分 ROM 静态证据、AOSP、推测、待真机。
- 不上传私有 ROM 或反编译代码；提交前检查暂存文件。
- 每个阶段保存运行参数、工具版本、失败与替代方案，再提交推送。
