# 13 外接显示真机基线与无重启验证

2026-11-11（北京时间）。小米 17 Pro Max `popsicle`，HyperOS `OS4.0.6.0.XPBCNXM`，Android 17 / SDK 37。经用户授权通过无线 ADB 测试。两条 ADB transport 对应同一设备，本轮 boot ID 始终一致，重启 0 次。`ro.system.build.version.incremental` 与 OTA 清单的内部增量号一致。设备的 `services.jar`、`framework-res.apk`、`miui-services.jar`、WM Shell JAR、SystemUI 和 MiuiHome 共六个文件 SHA-256 均与研究输入匹配。[ROM 清单](../analysis/evidence/rom-inventory.json)

## D0：连接、断开、重新镜像

通过逻辑 Display 2、物理端口 21、SurfaceFlinger 物理 ID 和 HWC display 1 关联 F27G51Q Pro。内屏和背屏分别为逻辑 Display 0 和 1，均为 INTERNAL。热插拔后重新核对身份，脚本复跑时按当前连接发现 ID。

| 状态 | 外屏连接 / 已启用 | 全局 MIUI RenderVote | 实际输出 |
| --- | --- | --- | --- |
| 初始镜像 | `true / true` | 0–60 fps | SF/HWC 2560×1440 @ 60 Hz，用户 OSD 一致 |
| 拔线 | `false / false` | 0–120 fps | 外屏从物理及逻辑显示表消失，DRM `disconnected` |
| 插线待选 | `true / false` | 0–120 fps | SF 已枚举外屏，SystemUI 等待用户选择 |
| 选择镜像 | `true / true` | 0–60 fps | SF/HWC 与用户 OSD 回到 2560×1440 @ 60 Hz |

运行时 `vendor.display.support_builtin_high_fps_when_pluggable_connected=0`。待选和镜像两组的差异支持「外屏实际启用」才触发 0–60 渲染投票。物理模式的选定还经过 SF/HWC。已读取 KernelSU `3.3.1` / `32680`、现有模块目录和启用标记，并用已授权的 root shell 读取 DRM connector 和 EDID。尚未验证模块救援或恢复启动。

## D1、D2：原生任务与连接入口

- 外屏在镜像下 `canHostTasks=false`、`mShouldShowSystemDecors=false`，窗口与 Activity dump 未见外屏 HOME 或普通任务。尝试 `am start -W --user 0 --display 2 -f 0x18800000 -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n com.miui.calculator/.cal.CalculatorActivity`，系统在 `SafeActivityOptions.checkPermissions` 拒绝，日志明确为 `activity launch is not allowed on a display that cannot host tasks`。检查前后任务列表，没有创建计算器任务。
- 有效的 `config_isDesktopModeSupported`、`config_isDesktopModeDevOptionSupported`、`config_canInternalDisplayHostDesktops` 均为 `false`。镜像键为 `1`，旧强制桌面开关为 `0`，开发桌面覆盖键未设置。
- `config_secondaryHomePackage` 的有效值为 `com.miui.home`。未限定包的 `SECONDARY_HOME` 查询有 MiuiHome 和背屏启动器两个候选，普通 resolve 返回 ResolverActivity。限定 `com.miui.home` 后解析到 `.launcher.SecondaryDisplayLauncher`。实际创建与点击启动仍待验证。
- 插线弹窗由 SystemUI 获得焦点，用户确认只有「镜像」「取消」。点击「镜像」后恢复画面。已观测到镜像挡住任务承载，桌面资格资源关闭。外屏装饰 provider 的实际调用、任务归属和窗口功能需在外屏能承载任务后采集。

## D6：黑边、模式清单与 120 Hz 对照

- 直立内屏镜像的 HWC `sourceCrop=[0,0,1200,2608]`，输出矩形 `displayFrame=[948,0,1611,1440]`。原画面等比缩到约 663 像素宽并居中，两侧留空由这次投影产生。外屏物理输出和逻辑尺寸均为 2560×1440。
- DRM `card0-DP-1` 为 `connected / enabled`。EDID 384 字节，三个块校验通过。Framework 的 2560×1440 模式清单包括 50、60、100、120、144、165、180 Hz。基线 SF 为 `hwcId=0`，HWC 活动配置索引为 `0`，`cur:60`，与 OSD 一致。
- 使用设备支持的 `cmd display set-user-preferred-display-mode 2560 1440 120 2 false`，`false` 表示不持久化。两次请求均被接受。首轮 DMS 一度报活动模式 17（SF mode 4，120 Hz），同期 SF 和 HWC 的采样仍是配置 0、60 Hz。重新插线后持续约 45 秒复测，2、12、27、44 秒四次采样中 DMS、SF 与 HWC 都维持 60 Hz。试验窗口内未取得 OSD 读数，连接基线和重新镜像后的 60 Hz 有用户 OSD 读数。120 Hz 物理输出在这条请求路径上未验证通过。
- 两次均用 `cmd display reset-user-preferred-display-mode 2` 恢复。复核偏好回到 `-1 -1 0.0`，外屏仍为 1440p60 镜像，内屏和背屏仍可枚举。原有设置、属性、Overlay 和模块保持原状。

## 验收和续做

| 项目 | 本轮结论 |
| --- | --- |
| 阶段 4 真机基线 | `PARTIAL`。三种连接状态、有效资格、HOME 解析、DRM 和模式投票有对照。共享装饰调用与模块恢复能力未验证。 |
| 阶段 5 原生桌面 | `PARTIAL`。系统应用的镜像落屏实验 `FAIL`，原生次屏 HOME 已解析，创建、操作和窗口管理待测。 |
| 阶段 6 尺寸与高刷 | `PARTIAL`。已定位直立镜像黑边。1440p60 基线 `PASS`，120 Hz 临时偏好路径 `FAIL`。 |
| 阶段 7 回归 | 镜像插拔恢复一轮 `PASS`。独立桌面下的输入、熄屏唤醒、背屏功能、持续性能、重启和模块恢复 `NOT_RUN`。 |

优先定位桌面资格、连接入口和 `canHostTasks` 的联动，完成最小改动与恢复设计后再选下一次设备对照。物理高刷可独立追踪用户偏好、DMS 活动模式记录与 HWC 实际配置之间的差异。

原始文件在 Git 忽略的 `analysis/local/device-validation/` 下。按 `D0-connected`、`D1-stock-activity`、`D0-disconnected`、`D2-reconnect-dialog`、`D0-mirror-restored`、`D6-mode120` 和 `D6-mode120-OSD` 后缀定位。D0/D2 用 `scripts/collect_readonly.ps1` 采集，`display.txt`、`surfaceflinger.txt`、`window-displays.txt`、`activities.txt` 是主要证据。D1 拒绝见 `wm-start-events.txt`，D6 前后状态见各次 `*-sf.txt`、`*-dms.txt` 或 `sf-*.txt`、`dms-*.txt`。OSD 与弹窗文字为用户现场回报。
