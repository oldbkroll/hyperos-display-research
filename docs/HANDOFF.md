# 交接入口

先读 `docs/maintask.md`、`docs/PROGRESS.md`，再读各阶段报告。不要从压缩包文件名推断版本；以 `analysis/evidence/rom-inventory.json` 为准。

## 当前下一步

1. 七个优先分区已完整提取，**不要重新从头解包**。完整根目录由 `extracted/native-files.json` 定位；NTFS system_ext 为中止输出，不是权威目录。
2. 已有本地 Java 分析输出在 `analysis/local/jadx/`；组件原文件哈希见 `analysis/evidence/components.json` 和 `input-copies.json`。
3. AOSP 已固定 `94b4c163b7dfe5ce3607f7bb8456f9573f7de57d`；原生架构报告已写，继续厂商限制与高刷分析。
4. JADX 在没有本 ROM framework-res 时会把 android.R 常量误标，必须用数值 ID 和 aapt2 输出核对。SelectiveJadx 默认禁用常量替换。
5. MiuiHome 没有 DEX，SECONDARY_HOME 仅证明声明存在；原生行为未恢复，后续结论保持边界。

## 约束

- 不使用 ADB，不安装模块，不修改设备；必须真机的项目加入验证计划。
- 关键结论区分 ROM 静态证据、AOSP、推测、待真机。
- 不上传私有 ROM 或反编译代码；提交前检查暂存文件。
- 每个阶段保存运行参数、工具版本、失败与替代方案，再提交推送。
