# 15 真机续测：桌面资格、任务承载和外屏黑屏

2026-11-11（北京时间）。小米 17 Pro Max `popsicle`，HyperOS `OS4.0.6.0.XPBCNXM`。继[报告 14](14-device-mirror-policy-and-mode-routing.md)确认系统会强制恢复镜像，本轮验证单一桌面资格资源的映射条件。

## D3：候选 Overlay 的映射条件

- 真机有效值仍为 `config_isDesktopModeSupported=false`、`config_isDesktopModeDevOptionSupported=false` 和 `config_canInternalDisplayHostDesktops=false`。`aflags` 确认显示内容管理、桌面窗口、投射桌面和两种开发选项标志为启用。ROM 的 `DesktopModeFlags` 优先走新版开发选项，新版在内容管理开启时仍要求开发选项资源为真。`DesktopStateImpl` 还在构造时缓存资格。旧全局开发开关无法替代这个单资源对照。[资格和缓存](09-native-desktop-minimal-design.md)
- 编译了只含 `config_isDesktopModeSupported=true` 的候选 APK，随后构建并验证静态签名版。手机的 `framework-res.apk` SHA-256 与本地 ROM 一致。用真机 `idmap2 create` 对临时文件分别声明 `public` 和 `public + product`，两个策略均保留 overlayable 检查。普通 `public` 返回 `no resources were overlaid`，`product` 精确生成一条 `0x011101f7` 映射。指定 `product` 是离线策略对照，真正的分区归属须由启动时的包扫描确认。
- 真机 `/product/overlay` 没有 `config/config.xml`。已有静态 MiuiHome 产品 Overlay 无 `targetName` 且已启用，提供了同一分区的实际先例。已核对当前 LKM KernelSU `3.3.1` / `32680`、`late_load=false`，以及已启用的 `hybrid_mount` 挂载器。候选模块只含一个 APK、模块信息和安装时版本门控，未包含开机脚本。候选 APK SHA-256 为 `ce4ff8793da5cc8b41468f12562e68b0f7ab01c02ba2cd9cff545c17bc868866`。
- `idmap2` 校验用的 APK 和 idmap 已从手机临时目录清理。映射校验结束时，活动 Overlay 列表、三项资源、镜像设置和物理输出均与基线一致。

## 启动回退演练

切换到有线 ADB，保存 8 个原有模块的启用状态。用户在开机阶段点按音量键。KernelSU 内核的音量计数为 0，实际由设备已有的 RescueBrick 触发回退，它停用另外 7 个模块并自动重启。重启后有线 ADB 和 root 均可用。按原清单恢复 7 个模块并正常重启，随后在开机动画已经停止时，用该模块的正常分支清除本轮恢复标记。该机已验证的是 RescueBrick 在此次启动阶段的回退和有线 ADB，KernelSU 内置安全模式未验证。RescueBrick 的重复触发分支会改动应用限制和无障碍设置，本轮仅触发一次。[KernelSU 3.3.1 官方恢复文档](https://github.com/tiann/KernelSU/blob/v3.3.1/website/docs/guide/rescue-from-bootloop.md)

## D3/D1：资格和独立任务通过，实际画面黑屏

用 KernelSU 安装单资源模块并重启。包从 `/product/overlay/D3DesktopQualificationOverlay.apk` 扫描，状态 `STATE_ENABLED`。`config_isDesktopModeSupported=true`，另外两个资格值仍为 `false`。WM Shell 出现 `DesktopTasksController`，其服务已注册。外屏连接后，镜像设置为 `0`，逻辑 Display 2 `canHostTasks=true`，MiuiHome 的 `SecondaryDisplayLauncher` 在该屏的 HOME task 上进入 resumed。

显示器有信号，用户现场看到黑屏。通过正常 shell 命令启动系统计算器，返回 `Status: ok`，其 fullscreen task 实际处于 Display 2。HOME 和计算器两次分别从同一外屏物理 ID 抓取 2560×1440 PNG，RGB 三通道全部为 0。两次 `dumpsys SurfaceFlinger` 的外屏 composition 都是 `isEnabled=false`、`layerStack=4294967295`，HWC layer 表为空。当前有证据的阻断点是物理外屏没有合成输出，需追踪关闭镜像后逻辑 Display 2 的 layer stack 如何交给该物理显示器。桌面资格、HOME 创建和外屏任务承载通过，独立画面和窗口操作未通过验收。

进一步对照同一采样的 DMS dump，逻辑 Display 2 属于显示组 1，`mHasContent=true`、逻辑 layer stack 为 2。对应的 DisplayPowerController 收到 `policy=DOZE`、`dozeScreenState=OFF`，物理设备的 `mState` 和 `mCommittedState` 均为 `OFF`，`mCurrentLayerStack=-1`。ROM 的 `DisplayManagerService.configureDisplayLocked()` 把物理 OFF 传给 `LogicalDisplay.configureDisplayLocked()` 作为 blank 参数，后者在 blank 时写入 layer stack `-1`。下一步先查外屏电源请求为何落入 DOZE/OFF，以及它与显示组唤醒策略的关系。当前记录未定位该请求的来源。[静态调用链](08-native-desktop-call-chain.md)

短对照后停止计算器，将 `mirror_built_in_display` 恢复到 `1`。有线 ADB 下卸载测试模块并重启，确认测试 APK 和模块目录均已移除，原有 8 个模块的状态、活动 Overlay 列表和三个资格资源均恢复。用户重新接外屏后确认镜像画面恢复，OSD 为 2560×1440 @ 60 Hz。

## SF：定位外屏模式拒绝

真机正在加载的 `/system_ext/lib64/libsurfaceflinger.so` 与 ROM 提取文件 SHA-256 一致，为 `43598f06ca2c3c96b9eb243e4acb177a5ee77c01794d1cbac92c3934ae32c40e`。限定在同一哈希的二进制中定位两条运行时警告。

| 入口 | 定位与观察 |
| --- | --- |
| `setDesiredDisplayModeSpecs` | 入口 `0x529c18`。`0x529e50` 引用警告字符串 `0x19581a`。条件分支进入日志和错误状态 `-38` 路径，跳过该请求的常规策略构建。另一条同形路径在 `0x56d578` 引用相同字符串。 |
| `setDesiredMode` | 入口 `0x4fec68`。`0x4fedc0` 引用警告字符串 `0x130a5e`。该路径输出带物理 ID 的告警后进入清理，不继续该次模式切换。 |

这些是与上轮日志对应的 SF 分支。精确 120 Hz 仍需要单独定位 DMS 目标筛选。未修改 SF、HWC 或刷新率设置。完整指令留在本地。[上轮真机日志](14-device-mirror-policy-and-mode-routing.md)

原始证据和候选产物在 Git 忽略的 `analysis/local/device-validation/` 下，按 `D3-overlay-idmap` 后缀定位。主要文件为 `idmap-*.txt`、`static-*.txt`、`recovery-*.txt`、`active-overlay.txt`、`desktop-*.txt`、`d1-*.txt`、`sf-*.txt` 和两张外屏截图。
