# 11 外屏任务的装饰、边界与动画归属

2026-11-11，`OS4.0.6.0.XPBCNXM`。继续核对 `Miui-WindowManager-Shell.jar` 的同一任务与 transition 路径。新增 N18–N29 方法锚点，设备验证 `NOT_RUN`。[证据清单](../analysis/evidence/native-desktop-stage2.json)

`WMShellModule.provideWindowDecorViewModel` 优先返回启用的 MIUI controller 所提供的 `MulWinSwitchDecorViewModel`。其次使用可用的 AOSP desktop 装饰，最后才创建普通 caption。ROM 中 `MultiTaskingControllerImpl.isMiuiShellModuleEnable()` 返回 `true`。该 provider 接受全局依赖，选择时没有显示参数。阶段 3 若评估 AOSP 路线，必须先确认真机的共享装饰绑定与外屏任务的实际装饰调用。[调用链与职责](08-native-desktop-call-chain.md)

| 操作 | 具体写入点及条件 |
|---|---|
| 创建与更新装饰（N18–N22、N29） | `FreeformTaskTransitionObserver` 将 opening task、leash、start/finish transaction 交给共享 `WindowDecorViewModel`。MIUI 实现按 `taskId` 建立或更新装饰，保留独立背屏设备的 ID 1 排除，按窗口模式和多窗切换能力判断。常规 `FreeformTaskListener.onTaskInfoChanged` 遇到 MIUI 装饰实现会跳过自己的装饰更新，MIUI listener 另有对应通知路径 |
| 任务逻辑边界（N25、N27） | `DesktopTasksController` 对启动请求检查 task 的 display 资格，最大化路径把 `setBounds` 写入 `WindowContainerTransaction`。MIUI 的 `adjustBoundsForDisplayChange` 也会按 task token 写 `setBounds`，折叠设备的部分小窗分支还附加 leash 的 position、crop 与 scale。两条路径使用各自的触发条件与任务集合 |
| 焦点动画与 surface（N23、N24） | `MultiTaskingTransitionObserver.onTransitionStarting` 遍历该 transition 的 task 变化并检查需取消的焦点动画。在有活动动画、有效 leash、全屏模式和白名单等条件同时成立时，MIUI 可提交独立的 surface scale 与 position 写入 |
| 选择动画 handler（N20、N26） | `Transitions` 先通知已注册 observer，再尝试预选 handler。回退时倒序遍历，首个接受 `startAnimation` 的 handler 取得该次分派。MIUI 的 `MultiTaskingTransitionHandler` 又按自身列表选择子 handler，首个接受后返回。observer 的写入和 handler 的选择发生在不同位置 |
| 桌面关闭与层级（N28） | `DesktopTasksTransitionObserver` 在 ready 阶段跟踪关闭任务及 remembered bounds。在特定桌面壁纸关闭路径，finished 阶段另起 transition，将该屏壁纸 task `reorder` 或 `removeTask` |

这些静态分支确认了装饰的选择顺序和几类实际写入。特定外屏任务的 provider 实例、observer 注册顺序、动画 handler 与最终 WCT/surface 提交归属仍待真机观测。当前保留 MIUI 路线优先评估，并保留 AOSP 候选。已有证据足以明确 AOSP 路线需要额外确认共享装饰绑定。[路线与准入](09-native-desktop-minimal-design.md)

下一次设备实验如获安排，应从同一 `taskId`、`displayId`、transition debug ID 关联三类事件。先核对装饰实例和 opening/infoChanged，再核对 bounds 或 leash 写入，最后核对接受动画的 handler 与结束状态。阶段 4 仍先采集断开及连接镜像的只读基线，具体窗口写入归属列入后续单变量实验。[验证预案](06-device-validation-plan.md)

复查使用 JADX 1.5.6。`ownership` 与 `ownership-follow` 保留可读分支，涉及 coroutine、动画复杂控制流或装饰调用接收者时查看 `ownership-fallback`、`ownership-decor-fallback`、`ownership-miui-handler`。常规模式在部分动画方法报类型推断错误，相关 fallback 结果保留在本地。公开清单记录文件哈希和方法锚点，`python scripts/verify_native_desktop.py --local` 可核对定位。
