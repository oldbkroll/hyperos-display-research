# 证据与复现

公共仓库仅放原创报告、脚本、哈希、符号定位和必要配置元数据。ROM 派生代码、完整资源、ELF 指令、APK 和日志均在 `local/`，禁止提交。

原生计划阶段 2 复用 `SelectiveJadx.java` 和 JADX 1.5.6，按 [新增证据](evidence/native-desktop-stage2.json) 的 `input`、类路径与输出分组定位；`dialog-fallback`、`shell-fallback` 分组使用 `fallback`。工具日志 `local/stage2-jadx-*.log` 保留常规重组失败及补查。类名分派用 NDK LLVM 在 `0x94e41c–0x94e469` 做定向反汇编，UI 名称用 `llvm-readelf -r -W` 核对 `0xe7e178` 重定位，应用入口用 `llvm-objdump -d --disassemble-symbols=app_entry_point`。完整日志和反汇编不入 Git。

`python scripts/verify_native_desktop.py --local` 校验输入 SHA-256、私有方法锚点、AOT 成员、迷你符号、ELF 分支、字符串和重定位。有归档 D10 时加 `--d10` 校验日志、快照和截图哈希及文本锚点。无本地输入时可只校验公开索引。复查方法见[报告 19](../reports/19-secondary-home-render-host.md)与[报告 20](../reports/20-secondary-home-aot-entry.md)。

## 证据入口

| 文件 | 范围 |
|---|---|
| evidence/rom-inventory.json | ZIP 身份、内部 OTA 元数据、58 分区的预期大小/哈希 |
| evidence/extraction.json | 七个 EROFS 镜像匹配及解包完成状态 |
| evidence/components.json | 选定 JAR/APK 的哈希、DEX 定义数量；零 DEX 不等于没有实现 |
| evidence/input-copies.json | 原分区路径到本地目标副本的映射与哈希 |
| evidence/aosp-sources.json | 固定 Android 17 提交和每文件哈希 |
| evidence/overlays.json | 97 个 packaged RRO 的哈希、manifest 条件、相关资源；无运行时状态 |
| evidence/findings.json | F01–F24 方法定位、本地反编译文件哈希、数值资源和关键属性 |
| evidence/native-first-frame.json | 主次屏渲染调用和超时闭包的 ELF 锚点，D10 归档哈希及 token / layer 锚点 |
| evidence/native-secondary-aot.json | Flutter AOT 成员、迷你符号、Dart 入口、Rust 窗口桥、scene 及其生命周期的分支与重定位锚点 |
| evidence/vendor-binaries.json | 显示 ELF 的哈希和字符串偏移；字符串本身不证明控制流 |
| evidence/tools.json | 工具来源/版本/校验边界 |

## 续做顺序

```powershell
python scripts/setup_tools.py
wsl -d Ubuntu-24.04 -- bash scripts/setup_erofs.sh
python scripts/rom_inventory.py <ROM.zip>
python scripts/extract_partitions.py <ROM.zip>
wsl -d Ubuntu-24.04 -- python3 scripts/extract_native.py
wsl -d Ubuntu-24.04 -- python3 scripts/scan_rom.py
python scripts/collect_inputs.py
python scripts/inspect_overlays.py
python scripts/fetch_aosp.py
wsl -d Ubuntu-24.04 -- python3 scripts/probe_vendor.py
```

已完成镜像按哈希跳过；文件系统完成标记位于 native root。`extracted/native-files.json` 给出 WSL 与 Windows UNC 路径。再次运行 inventory 会更新磁盘空闲量，属于环境快照变化。

## Java 目标分析

已运行的 full services 命令：

```powershell
.\tools\bin\jadx\bin\jadx.bat -j 6 -r -d analysis/local/jadx/services extracted/files/system/system/framework/services.jar
.\tools\bin\jadx\bin\jadx.bat -j 4 -s -d analysis/local/jadx/framework-res extracted/files/system/system/framework/framework-res.apk
```

全量 services 的 73 个错误已记录，不据错误方法下结论。后续使用原创 `SelectiveJadx.java`，一次加载仅保存目标类及相关依赖；禁用常量替换，防止 OEM 数值资源被自带 SDK 的 android.R 误命名。模板：

```powershell
java -Xmx6g -cp tools/bin/jadx/lib/jadx-1.5.6-all.jar scripts/SelectiveJadx.java INPUT OUTPUT 'REGEX'
```

| INPUT | OUTPUT（analysis/local/jadx/ 下） | REGEX 主目标 |
|---|---|---|
| system/framework/services.jar | services-numeric | `com\.android\.server\.(wm\.(DesktopModeHelper\|ActivityTaskSupervisor\|DisplayWindowSettings\|RootWindowContainer)\|display\.(DisplayManagerService\|SecondaryDisplayPolicy))$` |
| 同上 | services-fallback | `com\.android\.server\.(wm\.DesktopModeHelper\|display\.SecondaryDisplayPolicy)$`，最后加 `fallback` 参数 |
| 同上 | services-atms-numeric | `com\.android\.server\.wm\.ActivityTaskManagerService$` |
| system/framework/framework.jar | framework-hidden-flags | `com\.android\.internal\.hidden_from_bootclasspath\.com\.android\.(window\|server\.display\.feature)\.flags\.Flags$` |
| 同上 | framework-selected | `android\.window\.(DesktopExperienceFlags\|DesktopModeFlags)$` |
| miui-services.jar | miui-services | `com\.android\.server\.(display\.DisplayManagerServiceImpl\|wm\.(ActivityStarterImpl\|DisplayContentStubImpl))$` |
| miui-services.jar | miui-display-mode | `com\.android\.server\.display\.mode\.DisplayModeDirectorImpl$` |
| Miui-WindowManager-Shell.jar | miui-shell | DesktopStateImpl / WMShellModule / WMShellBaseModule / DesktopTasksController / DesktopDisplayEventHandler / DesktopModeWindowDecorViewModel |
| 同上 | miui-shell-extra | MiuiWMShellModule / MiuiDesktopModeStatus / ProjectedModeState |
| MiuiSystemUI.apk | systemui | ConnectingDisplayViewModel / WMShell / DesktopModule |
| miui-services.jar | miui-registrations / miui-wm-registrations | display mode 与 wm 包的 GeneratedMiuiImplManifest；核实 provider 注册 |
| miui-services.jar | miui-external | ExternalScreenCompatManagerImpl / LocalDisplayAdapterImpl / DisplayAdapterImpl |

表格内 `\|` 为 Markdown 表格转义；传入正则时使用普通 `|`。system JAR 在 native 根内多一层 system/。目标副本优先使用 `analysis/local/inputs/`；system JAR 也可从已完成 NTFS system 输出读取。

用已有 SDK aapt2 `dump resources` 产生 `analysis/local/framework-res-aapt2.txt`，`dump xmltree APK --file AndroidManifest.xml` 得到 manifest。重新生成代码/资源后运行 `python scripts/build_evidence.py`，缺失锚点会失败；代码变化后要重新人工审核，不能只更新哈希。

## 外屏电源组

复用上面的 full services 输出。按下列命令补查 Mapper 的分组参数和 MIUI 的电源组 provider。JADX 1.5.6 两次定向运行均报告 0 个错误。Mapper 的普通 Java 输出有重组不清的分支，组号条件及实参以 fallback 为准。

```powershell
$jadxJar = 'tools/bin/jadx/lib/jadx-1.5.6-all.jar'
$servicesJar = 'extracted/files/system/system/framework/services.jar'
java -Xmx5g -cp $jadxJar scripts/SelectiveJadx.java $servicesJar analysis/local/jadx/desktop-power-fallback 'com\.android\.server\.display\.LogicalDisplayMapper$' fallback
java -Xmx5g -cp $jadxJar scripts/SelectiveJadx.java analysis/local/inputs/miui-services.jar analysis/local/jadx/desktop-power-miui 'com\.android\.server\.(power\.(PowerManagerServiceImpl|GeneratedMiuiImplManifest)|display\.(DisplayManagerServiceImpl|LogicalDisplayMapperImpl|LocalDisplayAdapterImpl|GeneratedMiuiImplManifest))$'
```

对照 D3 的 `desktop-dms.txt`、`d1-restored-dms.txt` 与 D7 的 `00-dms.txt`、`00-power.txt`。从 Display Groups 小节核实成员，从对应 DPC 核实 `mPowerRequest`，再用同一物理设备的状态和 layer stack 核实输出。报告列出精确行锚点和待采时间线。[报告 16](../reports/16-external-desktop-power-group.md)

## ELF 分析

`probe_vendor.py` 保存 readelf/c++filt 和有界字符串输出。已有 NDK llvm-objdump 参数示例：

```powershell
llvm-objdump -d --demangle --start-address=0x16e938 --stop-address=0x16eb94 analysis/local/inputs/libsdmcore.so
llvm-objdump -d --demangle --start-address=0x172754 --stop-address=0x1728bc analysis/local/inputs/libsdmcore.so
llvm-objdump -d --demangle --start-address=0x18640 --stop-address=0x18648 analysis/local/inputs/libsdmutils.so
llvm-objdump -d --demangle --start-address=0xc840 --stop-address=0xc8b8 analysis/local/inputs/libsdmutils.so
```

地址只适用于清单内哈希对应的库；换 ROM 必须重新定位。完整输出留在 `analysis/local/vendor-probe/`，不公开指令片段。
