# LS send 项目规格说明书

> **版本：** v0.1-alpha  
> **最后更新：** 2026-03-08  
> **作者：** 派蒙（AI 项目管理助手）  
> **确认来源：** Matrix 原文 + admin 口头补充

---

## 1. 项目概况

| 项目 | 说明 |
|------|------|
| **名称** | LS send |
| **目标** | 跨平台局域网文件传输工具（Windows + Android） |
| **开发语言** | Python |
| **GUI 框架** | Windows: PySide6<br>Android: Kivy |
| **网络协议** | WebSocket（主传输） + UDP（自发现） |
| **语言支持** | 中文、英文（界面自动适配） |
| **文件大小限制** | 支持大文件传输（需分块处理） |
| **打包方式** | Windows: `.exe` / Android: `.apk` |

---

## 2. 核心功能需求

### 2.1 设备自发现（UDP 广播）
- 发送端：定期广播 UDP 探测包（`LS_SEND_DISCOVERY`）
- 接收端：监听广播并响应（返回设备名、IP、支持的协议版本）
- 网络范围：局域网内（同一子网）

### 2.2 文件传输（WebSocket）
- 连接建立：发送端与接收端 WebSocket 通信
- 文件发送：支持多个接收端同时连接
- 传输协议：分块传输（每块 64KB，可配置）
- 进度同步：实时推送传输进度（百分比 + 已传大小）

### 2.3 接收确认机制
- 接收端收到文件请求后：
  1. 弹出通知（Windows: 桌面通知 / Android: 通知栏）
  2. 用户点击“接收”或“拒绝”
  3. 仅“接收”确认后才开始传输

### 2.4 通知系统（Android）
- 通知类型：`Service + Native Notification`（plyer 或原生 API）
- 触发条件：设备空闲 + 收到文件请求
- 显示内容：文件名、大小、发送方 IP

### 2.5 多语言支持
- 资源文件：JSON 格式（`locale/zh.json`, `locale/en.json`）
- 语言切换：自动检测系统语言（或手动选择）

### 2.6 打包分发
- Windows：PyInstaller + PySide6（生成单文件 `.exe`）
- Android：Buildozer + Kivy（生成 `.apk`，需配置权限）

---

## 3. 技术实现规划

### 3.1 目录结构（Phase 1）
```
ls-send/
├── common/                 # 共享模块（协议、工具函数）
│   ├── protocol.py         # WebSocket/UDP 协议定义
│   └── utils.py            # 工具函数（进度计算、日志）
├── windows/                # Windows GUI
│   ├── main.py             # 主界面（PySide6）
│   └── views/
│       ├── discovery.py    # 设备发现 UI
│       └── transfer.py     # 传输进度 UI
├── android/                # Android GUI
│   ├── main.py             # 主界面（Kivy）
│   └── services/           # 后台服务（plyer）
│       └── notification.py # 通知栏管理
├── locale/                 # 多语言资源
│   ├── zh.json
│   └── en.json
├── spec.md                 # 本文件
└── README.md               # 项目说明
```

### 3.2 网络协议设计

#### 3.2.1 UDP 自发现
```
广播包（发送端 → 接收端）：
{
  "type": "DISCOVERY",
  "version": "1.0",
  "sender_name": "Windows-PC-01"
}

响应包（接收端 → 发送端）：
{
  "type": "RESPONSE",
  "version": "1.0",
  "device_name": "Android-Phone-01",
  "ip": "192.168.1.100",
  "supports_websocket": true
}
```

#### 3.2.2 WebSocket 传输协议
```
连接建立：
{
  "type": "INIT",
  "action": "REQUEST_SEND",
  "file_name": "example.pdf",
  "file_size": 1024000,
  "checksum": "md5_hash"
}

确认响应：
{
  "type": "INIT",
  "action": "ACCEPT" / "REJECT",
  "reason": "storage_full" / "user_declined"
}

分块传输：
{
  "type": "BLOCK",
  "sequence": 0,
  "data": "base64_encoded_chunk"
}

进度推送：
{
  "type": "PROGRESS",
  "percent": 45,
  "transferred": 460800
}
```

### 3.3 打包配置（Phase 5）
| 平台 | 工具 | 权限配置 |
|------|------|---------|
| Windows | PyInstaller | 无特殊权限 |
| Android | Buildozer | `INTERNET`, `WRITE_EXTERNAL_STORAGE` |

---

## 4. 开发优先级

- **Phase 1（当前）：** 项目结构 + 规格说明  
- **Phase 2：** 共享模块（协议 + 工具函数）  
- **Phase 3：** Windows GUI（PySide6）  
- **Phase 4：** Android GUI（Kivy）  
- **Phase 5：** 打包分发（`.exe` + `.apk`）  

---

## 5. 风险与待确认事项

| 风险项 | 应对方案 |
|--------|---------|
| Win10/11 PySide6 兼容性 | 优先支持 Win10，Win11 测试验证 |
| Android 通知栏权限变更 | 使用 `plyer/notification` + 手动权限请求 |
| Buildozer 权限配置缺失 | 预先测试 `android.permissions` 列表 |
| 大文件传输内存溢出 | 分块传输 + 临时文件缓存 |

---

> *本规格说明书已通过双重确认（Matrix 原文 + admin 口头补充）*
