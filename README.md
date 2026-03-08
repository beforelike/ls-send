# LS send

> *跨平台局域网文件传输工具（Windows + Android）*

---

## 📦 项目特色

- **一鍵發現设备**：UDP 广播自发现同一局域网的所有 LS send 实例  
- **一对多传输**：支持从一个设备向多个接收端同时发送文件  
- **接收确认机制**：接收方必须点击“确认接收”才开始传输  
- **实时进度推送**：WebSocket 实时显示文件传输进度  
- **Android 通知栏**：空闲时收到文件请求→通知栏弹窗  
- **中英文双语**：界面语言自动适配（中文/英文）  

---

## 🛠️ 技术栈

| 模块 | 技术选型 |
|------|---------|
| **Windows GUI** | PySide6 (Qt for Python) |
| **Android GUI** | Kivy + Buildozer |
| **网络协议** | WebSocket + UDP 广播 |
| **通知机制 (Android)** | Service + plyer (native notification) |
| **打包** | Windows: PyInstaller<br>Android: Buildozer |

---

## 📁 项目结构

```
ls-send/
├── common/                 # 共享模块（协议、工具函数）
├── windows/                # Windows GUI（PySide6）
├── android/                # Android GUI（Kivy）
├── locale/                 # 多语言资源（zh.json / en.json）
├── spec.md                 # 项目规格说明书
└── README.md               # 本文件
```

---

## 🚀 快速开始（开发中）

> ⚠️ 项目当前处于开发阶段，暂未提供预编译版本

### 开发者

1. 克隆项目（后续添加）
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 运行 Windows 版本：
   ```bash
   cd windows
   python main.py
   ```
4. 运行 Android 版本：
   ```bash
   cd android
   python main.py
   ```

### 打包

- Windows：
  ```bash
  pyinstaller --onefile windows/main.py
  ```
- Android：
  ```bash
  buildozer android debug
  ```

---

## 📬 联系方式

如有问题或建议，请通过 Matrix 联系项目维护者。

---

> *最后更新：2026-03-08*
