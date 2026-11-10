# 01 ROM 识别与解包

研究日期：2026-11-10。研究对象固定为工作区现有 ZIP，不操作手机。

## 身份与范围

**[ROM]** ZIP 内 `META-INF/com/android/metadata` 给出：

| 项 | 内部证据 |
|---|---|
| 类型 | `ota-type=AB`，payload major 2 / minor 0（完整 OTA payload） |
| 设备代号 | `pre-device=popsicle` |
| Android / SDK | 指纹为 Android `17`，`post-sdk-level=37` |
| 构建 | `17OS4.0.261026.213536012.QCPECN.S` |
| 指纹 | `Xiaomi/popsicle/popsicle:17/CP2A.260605.016/17OS4.0.261026.213536012.QCPECN.S:user/release-keys` |
| 安全补丁 | `2026-10-01` |
| ZIP 大小 | 9,195,708,631 字节 |
| ZIP SHA-256 | `3afe5d75428d6159a3ead77ad8ccc7ebb11910fd288a4fac6d40ffbf47a6655f` |

**[ROM]** 解出的 `mi_ext/etc/build.prop` 进一步确认 `ro.mi.os.version.incremental=OS4.0.6.0.XPBCNXM`、版本名 `OS4.0`、code `4`；现在已由内部属性核实，而非仅依据文件名。

## 分区结构

**[ROM]** ZIP 有 7 项，包括 `payload.bin`（9,195,699,760 字节）、OTA metadata、payload properties、apex/care map 和证书；没有独立 `super.img`。payload manifest 有 58 个分区，无旧分区信息，操作只包含 REPLACE、REPLACE_BZ、REPLACE_XZ，符合完整 payload。

动态组 `qti_dynamic_partitions` 上限 13,411,287,040 字节，成员为 odm、product、system、system_dlkm、system_ext、vendor、vendor_dlkm、mi_product、mi_ext。`snapshot_enabled=true`、`vabc_enabled=true`，压缩为 `lz4`。因此没有 super.img 并不意味着没有动态分区。

| 优先提取分区 | manifest 镜像大小（字节） | 用途 |
|---|---:|---|
| system | 977,289,216 | framework、services、基础资源、SurfaceFlinger |
| system_ext | 816,467,968 | SystemUI、厂商 framework 扩展 |
| product | 4,742,344,704 | Launcher、资源 Overlay、系统应用 |
| mi_ext | 171,528,192 | 小米扩展、版本信息 |
| vendor | 589,344,768 | HAL、显示配置、属性 |
| odm | 3,892,228,096 | 设备定制及可能迁入的显示组件 |
| mi_product | 348,160 | 小型小米产品配置 |

不默认解包 boot、init_boot、vendor_boot、dtbo；静态 Java/资源研究并不首先需要这些分区。若底层链路线索要求，另立检查点。

## 可重复流程

```powershell
python scripts/rom_inventory.py <ROM.zip>
python scripts/extract_partitions.py <ROM.zip>
python scripts/extract_filesystems.py
python scripts/fetch_aosp.py
```

`rom_inventory.py` 只读 ZIP，计算整体 SHA-256 并解析 protobuf 元数据，不重写 ROM。`extract_partitions.py` 使用 payload-dumper-go 2.1.0 直接读取 ZIP，4 个 worker，逐分区提取到 `.partial` 目录；工具正常退出且结果大小/哈希等于 manifest 才改为最终文件并设置只读属性。续做时重新校验已完成文件，异常文件不覆盖。

七个目标镜像全部匹配 manifest SHA-256，文件系统均为 EROFS，已成功解出 15,061 个普通文件（不计符号链接），见 [extraction.json](../analysis/evidence/extraction.json)。

`extract_filesystems.py` 是可用的 NTFS 输出路径，但跨 WSL/NTFS 小文件 I/O 很慢，已切换到：

```powershell
wsl -d Ubuntu-24.04 -- python3 scripts/extract_native.py
wsl -d Ubuntu-24.04 -- python3 scripts/scan_rom.py
python scripts/collect_inputs.py
```

`extract_native.py` 在 WSL `~/.local/share/hyperos-display-research/<ROM哈希前16位>/` 保存副本及解出的文件。复制镜像后再次匹配 manifest SHA-256，设置副本只读，再使用用户态 `fsck.erofs --extract`。它不挂载、不修改源镜像，成功才保存完成标记。Windows 访问路径记录在本地 `extracted/native-files.json`；后续分析以这些完整输出为准，先前 NTFS 的不完整 system_ext 输出保留但不用。

Windows C: 初查可用约 809 GB，目标镜像总计约 11.19 GB；预留文件解包、反编译和分析缓存空间，不复制整个 payload。工具安装在 `tools/`，Python 不安装全局依赖，WSL 的 erofs-utils 使用下载 deb 后解到工作区的方式，不执行系统安装。

## 校验边界

完整分区清单、manifest 哈希及各镜像预期 SHA-256 见 [rom-inventory.json](../analysis/evidence/rom-inventory.json)。实际完成状态见 [extraction.json](../analysis/evidence/extraction.json)，工具版本见 [tools.json](../analysis/evidence/tools.json)。已有 Android SDK build-tools 37.0.0 的 aapt2，故没有另装 SDK。仅按需对目标 JAR/APK 反编译，失败方法另行标注，未把全量反编译成功作为解包验收条件。

**没有执行 OTA 签名链认证。** manifest 哈希匹配证明提取结果与本 ZIP 一致，不能证明 ROM 来源可信或等于当前设备运行内容。也不证明完整 ZIP 的所有压缩项已做 CRC 测试。

原始 ROM、镜像、APK、DEX、反编译代码均被 Git 排除；公开文件仅为原创脚本、描述、符号定位和必要元数据。
