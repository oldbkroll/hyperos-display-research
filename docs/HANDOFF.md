# 交接入口

先读 `docs/maintask.md`、`docs/PROGRESS.md`，再读各阶段报告。不要从压缩包文件名推断版本；以 `analysis/evidence/rom-inventory.json` 为准。

## 当前下一步

1. 运行 `python scripts/rom_inventory.py <ROM.zip>`。
2. 获取并校验 payload-dumper-go，在本地提取 system/system_ext/product/mi_ext/vendor 等目标分区。
3. 探测文件系统并只读提取，不修改原始镜像。
4. 固定 Android 17 的 AOSP 源码版本，再做 Framework 与 UI 方法追踪。

## 约束

- 不使用 ADB，不安装模块，不修改设备；必须真机的项目加入验证计划。
- 关键结论区分 ROM 静态证据、AOSP、推测、待真机。
- 不上传私有 ROM 或反编译代码；提交前检查暂存文件。
- 每个阶段保存运行参数、工具版本、失败与替代方案，再提交推送。
