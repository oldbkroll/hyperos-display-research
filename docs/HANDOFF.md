# 交接入口

先读 `docs/maintask.md`、`docs/PROGRESS.md`，再读各阶段报告。不要从压缩包文件名推断版本；以 `analysis/evidence/rom-inventory.json` 为准。

## 当前下一步

1. 七个优先分区已完整提取，**不要重新从头解包**。完整根目录由 `extracted/native-files.json` 定位；NTFS system_ext 为中止输出，不是权威目录。
2. 已有本地 Java 分析输出在 `analysis/local/jadx/`；组件原文件哈希见 `analysis/evidence/components.json` 和 `input-copies.json`。
3. AOSP 已固定 `94b4c163b7dfe5ce3607f7bb8456f9573f7de57d`；23 组方法证据与 reports/03、04 已完成初步研究并推送（1932655）。
4. JADX 在没有本 ROM framework-res 时会把 android.R 常量误标，必须用数值 ID 和 aapt2 输出核对。SelectiveJadx 默认禁用常量替换。
5. MiuiHome 没有 DEX，SECONDARY_HOME 仅证明声明存在；原生行为未恢复，后续结论保持边界。
6. 方案比较见 reports/05：优先验证次屏 Activity，再做最小配置对照。不要直接制作高刷/桌面“全开”模块。

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
