# HyperOS 外接显示功能补全 — ROM 静态分析研究任务

## 一、项目背景与目标

目标设备：小米 17 Pro Max（中国大陆版本）

操作系统：HyperOS 4，准确版本号以工作区内的 ROM 为准。
Github仓库: https://github.com/oldbkroll/hyperos-display-research.git .除Rom包外的成果产出请及时提交推送（文档创建时为空仓库）
设备状态：
- 已 Root，使用 KernelSU Official。
- 具备 USB-C 视频输出能力。
- 目前可以外接显示器，但主要表现为屏幕镜像。
- 外接显示器存在宽高比不匹配、黑边及刷新率限制问题。
- 已尝试部分 Android 桌面模式相关接口或开关，但未成功获得完整独立桌面体验。
- 过去使用 LSPosed Hook 系统桌面时，曾出现严重的桌面卡顿、动画异常及退出后的界面错位。

最终希望获得：

1. 外接显示器独立显示，而非简单镜像。
2. 正确识别并使用外接显示器分辨率、宽高比。
3. 在硬件和显示链路允许的情况下，支持高于 60Hz 的刷新率。
4. 外接显示器可以独立承载应用窗口。
5. 手机内屏能够继续正常工作。
6. 鼠标、键盘、手柄等输入设备正常使用。
7. 优先采用可逆、可关闭、尽可能不修改系统分区的实现方式。

本次任务的核心是研究和验证，不要求立即完成可用模块。

## 二、工作环境与限制

当前在 Windows 本地 Codex 工作区中开展研究。

我会在工作区放置当前手机版本的完整 ROM 压缩包。

你拥有工作区内文件的分析权限，可以根据实际需要安装和运行开源工具。

### 重要限制

- 不要求手机通过 USB 连接电脑。
- 不依赖实时 ADB 或手机调试。
- 不执行刷机或修改手机的操作。
- 不主动删除、移动或覆盖原始 ROM。
- 不直接修改系统分区镜像。
- 不上传 ROM 或小米专有系统文件到公共服务。
- 不将反编译后的专有代码提交至公共仓库。
- 不要求我在每个分析步骤手动操作。
- 如果某项研究必须真机验证，记录到待验证清单，而不是中断整个任务。

允许使用 WSL2、Python、Java、Android 逆向工具，但先检查系统是否已经具备相应环境。

安装工具时尽量隔离在项目工作区或独立环境，避免污染 Windows 全局配置。

## 三、第一阶段：ROM 识别与解包

### 1. 自动识别工作区文件

扫描工作区，定位 ROM 压缩包。

识别：

- ROM 类型：Recovery / Fastboot / OTA
- Android 版本
- HyperOS 版本
- 设备代号
- 固件构建编号
- 分区结构
- 文件系统格式
- 是否包含 payload.bin
- 是否包含 super.img
- 是否使用动态分区

优先依据 ROM 内部元数据确认，不要仅依赖压缩包文件名。

检查磁盘可用空间，合理规划解包目录。

### 2. 建立可重复执行的解包流程

根据 ROM 实际结构选择合适工具，包括但不限于：

- payload-dumper-go
- simg2img
- lpunpack
- erofs-utils
- Android SDK 工具
- jadx
- apktool
- baksmali
- dex2jar

工具选择以兼容性、稳定性为优先。

不要为安装工具而安装工具。

优先提取并分析：

- system
- system_ext
- product
- mi_ext（如果存在）
- vendor 中与显示功能相关的组件

如有必要，再分析 boot、vendor_boot、init_boot、dtbo 等镜像，但不要默认这些镜像都包含本次研究所需信息。

原始 ROM 及原始分区镜像保持只读。

设计可重复运行、支持断点续做的脚本，避免每次重新解包。

## 四、第二阶段：Android 原生多显示器机制分析

先研究 ROM 所对应 Android 版本的原生实现，明确系统原本应该具备哪些能力。

重点分析：

- DisplayManagerService
- WindowManagerService
- ActivityTaskManagerService
- DisplayContent
- DisplayPolicy
- WindowManagerShell
- Desktop Mode
- Freeform Window Management
- Secondary Display Activity Launch
- Multi-display Input Routing
- SurfaceFlinger 相关配置
- Display HAL / HWC 显示模式枚举
- EDID 与显示模式选择机制

需要区分以下能力：

1. 外接显示器正常输出视频。
2. 系统识别外接显示器为独立逻辑 Display。
3. 应用可以在次级 Display 上启动。
4. 系统能够为次级 Display 提供独立桌面。
5. 外接屏幕支持特定分辨率。
6. 外接屏幕支持高刷新率。

这些能力不是同一个概念，不能因为其中一个功能存在，就推断其他功能一定可用。

结合对应 Android 版本的 AOSP 源码研究，不要将不同 Android 版本的实现混为一谈。

## 五、第三阶段：HyperOS 定制与限制定位

这是本项目的研究重点。

### 1. Framework 层

分析 ROM 中相关 framework 和 services 组件。

寻找与以下功能有关的代码路径：

- 外接显示器连接事件
- Display ID 分配
- Display 类型及标记
- Activity 启动显示器选择
- Secondary Display 支持
- Desktop Mode 控制
- Freeform Window 支持
- 外接屏幕分辨率控制
- 外接显示刷新率策略
- 系统属性与资源 Overlay 控制

定位可能由 HyperOS 修改、屏蔽或替换的逻辑。

不要只通过字符串搜索下结论。

对于关键方法，应追踪调用关系，并记录类名、方法名、调用位置以及相关证据。

### 2. SystemUI 与 Launcher

分析：

- SystemUI
- HyperOS Launcher
- 其他与桌面、窗口管理相关的系统 APK
- 与外接显示相关的系统应用或服务

重点判断：

- 是否存在针对外接显示器的专门 UI。
- 是否具备任务栏或桌面容器实现。
- 是否阻止应用运行于 Secondary Display。
- 是否由 Launcher 或 SystemUI 限制桌面模式。
- 是否存在厂商自定义多窗口逻辑。
- 是否能够不修改主桌面的情况下提供独立外接桌面。

特别注意过去 LSPosed Hook 主桌面后出现的性能和动画问题。

优先寻找不侵入 Launcher 主渲染路径的方案。

### 3. Vendor 与底层显示链路

检查 vendor 中与显示相关的：

- 配置文件
- HAL 接口定义
- 服务组件
- 显示模式配置
- 刷新率策略
- USB-C / DP 输出相关线索

判断外接屏幕的 60Hz 限制可能出现在哪一层。

需要明确区分：

- GPU 渲染帧率
- Android 逻辑显示刷新率
- SurfaceFlinger 合成策略
- HWC 输出模式
- USB-C DisplayPort 链路能力
- 转接器、线缆和显示器能力

不能仅依据系统属性推断物理输出支持 120Hz 或 180Hz。

## 六、第四阶段：寻找功能补全路径

根据证据评估以下方案。

### 方案 A：利用已有原生功能

研究是否只需要修改：

- 系统属性
- DeviceConfig
- Overlay 资源
- Feature Flag
- 系统配置文件

优先考虑配置层解决方式。

### 方案 B：非侵入式模块

研究 KernelSU 模块或其他可逆配置方案。

尽量避免直接修改系统分区。

### 方案 C：Framework Hook

如果确实需要 Hook，分析：

- 具体 Hook 位置
- 目标进程
- Android 版本兼容性
- 对系统稳定性的影响
- 对 Launcher 和 SystemUI 的影响
- 失败后的恢复方法

禁止使用未经分析的大范围 Hook。

优先研究低频事件处理路径，避免介入动画、绘制和高频窗口布局过程。

### 方案 D：独立桌面应用

评估是否可以：

- 利用 Secondary Display API
- 利用 Android 原生多窗口机制
- 在外接屏幕创建独立桌面容器
- 通过具有适当权限的系统组件实现应用窗口管理

需要明确普通应用、Root 应用和特权系统应用分别能够实现哪些功能。

### 方案 E：底层修改

如果限制位于显示 HAL、HWC 或内核驱动：

- 评估可行性。
- 标注需要的内核源码或设备树。
- 分析潜在风险。
- 不立即制作底层补丁。

## 七、第五阶段：形成可实施的研究结果

请建立清晰的项目目录：

```text
hyperos-display-research/
├── tools/
├── scripts/
├── extracted/
├── analysis/
├── reports/
│   ├── 01-rom-information.md
│   ├── 02-android-display-architecture.md
│   ├── 03-hyperos-restrictions.md
│   ├── 04-display-refresh-rate.md
│   ├── 05-implementation-options.md
│   └── 06-device-validation-plan.md
├── README.md
└── .gitignore
```

允许根据实际需要调整结构。

特别要求：

- ROM、分区镜像、大型反编译输出应排除 Git 跟踪。
- 不要复制大量反编译代码到报告。
- 每个重要发现提供可复查证据。
- 对推测、静态证据和实际验证结果采用不同标记。
- 记录使用工具的版本和运行参数。
- 尽量保存分析脚本，保证过程可重现。

## 八、真机验证计划

最终整理一份无需立即连接手机的验证计划。

按风险从低到高排列：

1. 只读 ADB 信息采集。
2. 系统配置与 Display 信息检查。
3. 运行时功能开关验证。
4. 可逆模块测试。
5. Framework Hook 验证。
6. 必要时再研究底层修改。

给出未来需要采集的 ADB 输出与对应命令。

明确哪些操作无需重启，哪些需要重启，哪些存在启动失败或系统不稳定风险。

不要执行真机操作。

## 九、执行要求

这是一项允许较长时间探索的研究任务。

请自主完成环境检测、ROM 识别、合理解包、目标组件定位及初步静态分析。

不要在每个普通步骤都停下来向我提问。

如果遇到工具不兼容、文件系统无法挂载、反编译失败等情况，尝试其他可行方案，并记录失败原因。

如果 ROM 无法解包，提供具体错误证据，不要编造分析结果。

如果发现研究路线需要调整，根据实际证据调整，不必机械执行全部步骤。

### 最重要的原则

**先验证现有能力，再定位限制，最后设计补全方案。**

不要以“HyperOS 一定屏蔽了完整桌面模式”为预设结论。

不要因为 AOSP 中存在某个接口，就认为当前设备的 Framework、HAL 和硬件一定支持。

不要为了尽快得到结果而编造不存在的类、方法、系统属性或补丁。

本轮任务以完成具有证据支持的静态研究报告为优先目标，不急于生成安装包。