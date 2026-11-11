# 14 真机续测：镜像恢复、模式请求与锁屏回归

2026-11-11（北京时间），沿用同一台 `popsicle`、`OS4.0.6.0.XPBCNXM`、F27G51Q Pro 和无线 ADB。外屏为物理 EXTERNAL、逻辑 Display 2、端口 21。沿用[报告 13](13-device-display-baseline.md)的镜像基线。测试前后 boot ID 一致，重启 0 次。结束时镜像键为 `1`，外屏为 2560×1440 @ 60 Hz，模式偏好回到未设置。

## D4：系统恢复镜像

普通 ADB shell 写 secure 设置被 `WRITE_SECURE_SETTINGS` 权限拒绝。随后使用设备已有的 KernelSU root，通过 Settings 接口将用户 0 的 `mirror_built_in_display` 从 `1` 临时写为 `0`。执行前确认外屏启用，远端脚本退出时会在需要的情况下恢复原值。

设备时间显示，写入命令开始约 30 ms 后，`SecondaryDisplayPolicy` 记录 `Force enable mirroring`。约 77 ms 时首个读回值已经是 `1`，未触发脚本的补偿写入。后续 DMS 仍为 `mMirrorBuiltInDisplaySetting=true`，外屏保持启用且 `canHostTasks=false`。这验证了[静态研究中的镜像恢复路径](03-hyperos-restrictions.md)。D4 的策略复现 `PASS`，单独关闭镜像的路径 `FAIL`。本轮没有修改桌面资格资源或安装模块。

用 `dumpsys activity service com.android.systemui/.SystemUIService WMShell` 查到 `ShellTaskOrganizer`、`MultiTaskingStateManager`、`MultiTaskingTransitionHandler` 及内屏装饰任务。`WindowDecor size:` 与 ROM 中 `MulWinSwitchDecorViewModel.dump()` 的输出匹配，支持 MIUI 装饰已在当前 Shell 实例中工作。已记录的装饰任务均为 Display 0，外屏任务与 transition 的实际写入者仍待验证。[静态窗口归属](11-native-desktop-window-ownership.md)

## D6：模式匹配与 SurfaceFlinger 边界

每次只对物理外屏临时设置一个 `cmd display set-user-preferred-display-mode WIDTH HEIGHT FPS DISPLAY_ID false`，采集约 2 秒和 7 秒的 DMS、SF、HWC 状态，再用 `reset-user-preferred-display-mode DISPLAY_ID` 恢复并核对。显示清单的简表会四舍五入。原始模式值取自 `dumpsys display`。

| 请求 | Framework | 物理输出 |
| --- | --- | --- |
| 2560×1440 @ `50` | 匹配模式 44，DMS 目标为 50 Hz | SF 收到外屏模式 6 请求并发出外屏警告，HWC 仍为 1440p60 |
| 1920×1080 @ `60` | 读回偏好，但 `mUserPreferredModeId=-1` | 1440p60 |
| 1920×1080 @ `60.000004` | 匹配模式 48，DMS 目标为 1080p60 | SF 收到外屏模式 10 请求并发出同一警告，HWC 仍为 1440p60 |
| 2560×1440 @ `120.00001` | 匹配模式 42，出现 120 Hz 物理偏好投票，DMS 最终目标仍为模式 38、渲染上限约 60 | 1440p60 |

两次低于或等于 60 Hz 的有效目标请求都在 SF 记录 `Attempt to set desired display modes for external display`，对应的 SF 外屏策略未改变。锁屏唤醒期间，同一物理 ID 还出现 `setDesiredMode` 的外屏警告。由此确认移除 60 fps 投票不足以解释这些切换失败。精确 120 Hz 已完成模式匹配，但本轮未观测到 DMS 把 120 Hz 作为外屏目标提交给 SF。所有外屏物理模式切换请求均未通过，复测期间未采集 OSD。

[AOSP] 固定的 `android17-release` 对照提交 `ae266dcb706d083868578cfedce381ef44488a07` 在 `setDesiredDisplayModeSpecs()` 入口检查无效 token 和虚拟屏，并向内部策略传递物理显示请求。所读入口和 `setDesiredMode()` 未见本机外屏警告。下一步需在匹配 ROM 的 SF 实现中定位这两个外屏分支，以及它们与 HWC 和 DisplayModeDirector 的关系。[AOSP SurfaceFlinger.cpp](https://android.googlesource.com/platform/frameworks/native/+/ae266dcb706d083868578cfedce381ef44488a07/services/surfaceflinger/SurfaceFlinger.cpp#9109)

## D7：镜像锁屏与唤醒

用户手动锁屏、唤醒并解锁一次。采样依次看到 `Awake / unlocked`、`Dozing / keyguard showing`、`Awake / unlocked`。外屏在采样中持续被识别，SF/HWC 活动模式仍为 1440p60。用户确认解锁后画面自动恢复，镜像锁屏回归一轮 `PASS`。独立桌面下的锁屏、输入、窗口操作和背屏功能仍待验。

原始记录保留在 Git 忽略的 `analysis/local/device-validation/`，按 `D4-mirror-policy`、`D6-mode-controls`、`D6-exact-mode` 和 `D7-mirror-lock-wake` 后缀定位。关键文件为 `policy-live-root.txt`、`root-pulse.txt`、`wmshell.txt`、`mode-logcat.txt` 及各轮 `*-dms.txt`、`*-sf.txt`。
