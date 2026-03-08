# LS send 安装包打包指南

> **最后更新：** 2026-03-08  
> **状态：** 代码已全部完成，等待打包环境配置完成

---

## 📦 已完成工作

### ✅ 项目结构
```
ls-send/
├── common/             # 共享模块
│   ├── protocol.py     # 协议定义
│   ├── utils.py        # 工具函数
│   ├── exceptions.py   # 异常类
│   ├── localization.py # 多语言管理
│   ├── udp_discovery.py   # UDP 自发现服务
│   └── websocket_transfer.py # WebSocket 传输服务
├── windows/            # Windows GUI
│   └── main.py         # PySide6 主界面
│   └── build.py        # PyInstaller 打包脚本
├── android/            # Android GUI
│   └── main.py         # Kivy 主界面
│   └── services/notification.py # 通知服务
│   └── buildozer.spec  # Buildozer 配置
│   └── build.py        # Buildozer 打包脚本
├── locale/             # 多语言资源
│   ├── zh.json
│   └── en.json
├── spec.md             # 需求规格说明
├── README.md           # 项目说明
└── requirements.txt    # 依赖清单
```

---

## 🛠️ 打包步骤（等待依赖安装完成）

### Windows EXE 打包

#### 1. 安装依赖
```bash
pip install pyinstaller pyside6
```

#### 2. 构建 EXE
```bash
cd /root/manager-workspace/ls-send/windows
python build.py
```

或手动运行：
```bash
pyinstaller --onefile --windowed \
  --name "LS_send" \
  --add-data "/root/manager-workspace/ls-send/locale;locale" \
  --hidden-import PySide6.QtWidgets \
  --hidden-import PySide6.QtCore \
  --hidden-import PySide6.QtGui \
  /root/manager-workspace/ls-send/windows/main.py
```

#### 3. 输出位置
- EXE 文件：`/root/manager-workspace/ls-send/dist/LS_send.exe`

---

### Android APK 打包

#### 1. 安装 Buildozer + Android SDK/NDK
```bash
pip install buildozer plyer

# 下载 Android SDK：
# https://developer.android.com/studio#command-tools

# 下载 Android NDK：
# https://developer.android.com/ndk/downloads

# 设置环境变量：
export ANDROID_SDK_ROOT=/path/to/android-sdk
export ANDROID_NDK_ROOT=/path/to/android-ndk
```

#### 2. 构建 APK
```bash
cd /root/manager-workspace/ls-send/android
buildozer android debug
```

或使用自动构建脚本：
```bash
python build.py
```

#### 3. 输出位置
- APK 文件：`/root/manager-workspace/ls-send/bin/lssend-0.1-armeabi-v7a-debug.apk`

---

## 🔧 当前问题（等待解决）

| 问题 | 状态 |
|------|------|
| Python pip 未安装 | ✅ 已修复（apt-get install python3-pip） |
| PySide6 未安装 | ⏳ 等待 pip install pyside6 |
| PyInstaller 未安装 | ⏳ 等待 pip install pyinstaller |
| Android SDK/NDK | ⏳ 需要手动下载配置 |

---

## 📬 下一步

请执行以下命令完成打包：

```bash
# 安装缺失的依赖
python3 -m pip install pyinstaller pyside6 kivy plyer buildozer

# Windows 打包
cd /root/manager-workspace/ls-send/windows
python3 build.py

# Android 打包（需要配置 SDK/NDK 后）
cd /root/manager-workspace/ls-send/android
buildozer android debug
```

打包完成后，安装包位置：
- **Windows**：`ls-send/dist/LS_send.exe`
- **Android**：`ls-send/bin/lssend-*.apk`

派蒙会等待你的确认，或在依赖安装完成后自动启动打包流程。
