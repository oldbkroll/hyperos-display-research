# 06 未来真机验证计划

状态：**所有真机项目均 NOT_RUN**。本轮未调用 ADB、未接入设备、未改设置、未安装模块或 Hook。以下是未来可执行的计划，不是已获得的结果。

## 0：先建立不改动设备的基线

分别在“未接外屏”“外屏连接并有画面”“外屏保持连接且内屏正常操作”三个状态采集。同一组对照保持线缆、转接器、显示器输入口及模式一致，记录显示器型号/OSD 输入时序、供电和手机温度/亮度。

预备 [collect_readonly.ps1](../scripts/collect_readonly.ps1) 可按指定 serial 批量保存日志；本轮仅做 AST 与 `-WhatIf` 验证，不实际执行采集。以后手动使用：

```powershell
.\scripts\collect_readonly.ps1 -Serial <确认过的设备序列号> -Label disconnected
.\scripts\collect_readonly.ps1 -Serial <同一序列号> -Label connected
```

脚本没有 root、写设置、重启、安装或服务调用；失败命令单独记录 exit code 后继续。原始运行日志仅保存在 Git 忽略的 `analysis/local/device-validation/`。

## 1：只读 ADB 信息（无需重启，低风险）

| 命令 | 需要判定的内容 |
|---|---|
| `adb -s SERIAL shell getprop` | 指纹是否等于研究 ROM；桌面限制、MIUI optimization、厂商显示属性、背屏 ID |
| `adb -s SERIAL shell dumpsys display` | 外屏 type/ID/uniqueId、enabled、content mode、supportedModes、active mode、DisplayModeDirector 投票 |
| `adb -s SERIAL shell dumpsys SurfaceFlinger` | 物理显示标识、活动 mode、desired physical/render ranges、连接/合成策略 |
| `adb -s SERIAL shell dumpsys window displays` | DisplayContent、TaskDisplayArea、windowing mode、HOME/system decors、焦点 |
| `adb -s SERIAL shell dumpsys activity activities` | Activity/task 实际归属 Display；内屏是否被迁移 |
| `adb -s SERIAL shell dumpsys input` | 鼠标/键盘/触摸设备、显示关联、焦点与 viewport |
| `adb -s SERIAL shell dumpsys thermalservice` | 采样热状态；不能把热降频误归因桌面 |
| `adb -s SERIAL shell logcat -d -t 2000` | DMS、WMS、DisplayModeDirector、composer 的近期拒绝/模式错误 |

不硬编码 Display ID。设备的 ID 1 很可能是背屏，必须结合 type=EXTERNAL、物理 uniqueId/address 和插拔差分识别目标。软件虚拟 Display 不当作 USB-C 物理输出。

## 2：资源、配置与入口核实（无需重启，低风险）

先获取 `cmd overlay help`、`cmd display help`、`cmd package help`、`wm help`、`am help`，以设备实际命令实现为准。只读查询示例：

```text
adb -s SERIAL shell cmd overlay list --user 0
adb -s SERIAL shell cmd overlay lookup --user 0 --verbose android android:bool/config_isDesktopModeSupported
adb -s SERIAL shell cmd overlay lookup --user 0 --verbose android android:bool/config_isDesktopModeDevOptionSupported
adb -s SERIAL shell cmd overlay lookup --user 0 --verbose android android:bool/config_canInternalDisplayHostDesktops
adb -s SERIAL shell cmd overlay lookup --user 0 --verbose android android:string/config_secondaryHomePackage
adb -s SERIAL shell cmd package resolve-activity --brief --user 0 -a android.intent.action.MAIN -c android.intent.category.SECONDARY_HOME
adb -s SERIAL shell pm list features
adb -s SERIAL shell dumpsys package com.miui.home
adb -s SERIAL shell dumpsys activity service com.android.systemui/.SystemUIService
adb -s SERIAL shell settings --user 0 get secure mirror_built_in_display
adb -s SERIAL shell settings --user 0 get system external_display_connected
adb -s SERIAL shell settings get global force_desktop_mode_on_external_displays
adb -s SERIAL shell settings get global enable_freeform_support
adb -s SERIAL shell settings get global development_override_desktop_mode_features
```

Overlay lookup 和 package resolve 的参数已对照固定 Android 17 上游 shell command；厂商可有差异，失败应保留，不自动替换为写操作。参考：[OverlayManagerShellCommand](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/services/core/java/com/android/server/om/OverlayManagerShellCommand.java)、[PackageManagerShellCommand](https://android.googlesource.com/platform/frameworks/base/+/94b4c163b7dfe5ce3607f7bb8456f9573f7de57d/services/core/java/com/android/server/pm/PackageManagerShellCommand.java)。

重点查 F12 路径中的 mMiuiRefreshRateEnable、mExternalDisplayConnected、mExternalDisplayActuallyEnabled、mMultiDisplaysLimit、priority 24 RenderVote 和 thermal vote。不能仅凭 property=0 就判定投票已发生。

另外只读核查 `persist.wm.external_compat.enabled`、WMS 的 ExternalScreenCompatManager 状态和按 Activity 的缩放配置，区分应用兼容性缩放与镜像 viewport 黑边；本阶段不启用它。

## 3：次屏 Activity 与运行时开关（有状态变化，中风险）

只有外屏已识别、基线保存且具备退出方式后再进行。先用自有探针 Activity，必要时按 `am help` 确认后用 `am start --display EXTERNAL_ID -n 测试包/测试Activity`；每次核对 task/displayId。它无需重启，但会启动应用/改变焦点，因此不纳入只读脚本。

运行时 Settings 对照前先保存原值，包括值是否为 `null`（键不存在）。恢复时原来不存在用 `settings delete`，原来存在用 `settings put` 原值；不能一律恢复为猜测的 0。一次只改一个变量，保留前后 dump 和日志。

`mirror_built_in_display` 可被策略自动恢复；若无桌面资格或可用 HOME，强制关闭镜像可能黑屏或无任务承载。先验证 consumer 和资格，出现空白、内屏布局异常、持续 SystemUI 崩溃就恢复。旧 force desktop 开关在当前内容模式分支可能无效，不连续叠加开关“撞答案”。

持久属性、DesktopState/flag 缓存与 RRO 资格通常需重启相关进程或设备，归入下一阶段；不在此阶段用重启 system_server/HWC 来掩盖状态不一致。

## 4：可逆配置模块（需要重启，中高风险）

先只读确认 KernelSU Official 的版本、模块挂载能力及该版本支持的恢复入口。建立模块禁用/移除方式，保存原 Settings/property/Overlay 状态，再对照报告 05 的最小配置候选制作版本门控测试包。

分开测试“桌面资格”和“刷新率策略”，不同时改变两者。重启前后确认模块状态、资源实际值、内屏 HOME、背屏行为、桌面组件与输入。禁用模块后还原持久值并再次重启，验收基线恢复。可能发生 SystemUI 不稳定或启动失败；本轮未制作、安装或测试此模块。

## 5：Framework Hook（需要重启，高风险）

仅在只读/配置证据指向具体方法后进行。先观测方法参数、返回值与调用次数；限定本 ROM 指纹/哈希/签名、进程和显示类型。禁止全放行 private/rear display，禁止主 Launcher 动画/绘制路径 Hook。

一次一个 Hook，严格比较内屏动画、退出布局、AOD/解锁、外屏拔插和 task 恢复。错误时禁用模块/Hook，按已确认的本版本恢复路径启动；没有可用恢复方法前不得测试。system_server Hook 可能导致重启循环。

## 6：物理模式与链路采集（先只读，底层修改另立任务）

先只读列出 `/sys/class/drm`，根据连接状态发现真实 DP connector，不能假设 card0-DP-1。权限拒绝只记录，未来经明确安排再使用有授权的只读 root helper。按实际存在的节点采集 connector status、modes、EDID；用能保持二进制的方式保存 EDID，不在旧 PowerShell 文本管道中重定向原始字节。

将 EDID modes、DRM/HWC mode、SF 物理模式与显示器 OSD 对齐。跨转接器/线缆/显示器的对照逐项替换，保留色深、HDR、DSC、lane/link rate 等可获得信息。未暴露高刷的原因可能是链路、接收端或厂商裁剪，不能以空缺日志补结论。

若需要改 HWC/内核/DTBO，单独评审源码匹配、恢复镜像与风险，本计划不提供或执行底层补丁。

## 验收矩阵（目前全部 NOT_RUN）

| 项目 | 通过条件 |
|---|---|
| 独立输出 | 外屏持续显示自己的 Activity，内屏显示不同内容，task/displayId 可复核 |
| 正确尺寸 | 物理输入时序、外屏逻辑宽高/方向一致；分别解释镜像与应用黑边 |
| 独立桌面 | 次屏 HOME/启动器、任务切换、窗口管理正常，主屏 HOME 不被替换 |
| 高刷 | 同一外接物理显示的 mode/SF/HWC 与 OSD 交叉一致，渲染率另记 |
| 内屏与背屏 | 内屏触控/动画/锁屏/AOD、背屏原功能保持正常 |
| 输入 | 鼠标跨屏/点击、键盘焦点/IME、手柄焦点分别通过 |
| 生命周期 | 插拔、旋转、熄屏/唤醒、应用崩溃/关闭、重启及拔屏任务归位正常 |
| 性能与恢复 | 记录稳定运行和热状态；退出后无持续卡顿/错位；禁用后恢复基线 |

每项记录 ROM 指纹、测试编号、前置状态、命令/操作、原始日志路径、预期/实际与 PASS/FAIL/NOT_RUN；不得把静态存在升级为 PASS。
