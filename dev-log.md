# LS Send 项目开发日志

## PCA 2-3: UDP 自发现 + WebSocket 传输服务完善

**开发工程师**: backend-dev  
**完成时间**: 2026-03-08  
**版本**: v1.0.0

---

## 任务概述

完成 Phase 2-3 开发工作，包括：

1. 补全 UDP 发现服务（`common/udp_discovery.py`）
2. 补全 WebSocket 传输服务（`common/websocket_transfer.py`）
3. 编写测试脚本（`test_udp.py` / `test_ws.py`）

---

## 1. UDP 发现服务 (`common/udp_discovery.py`)

### 1.1 功能实现

#### 设备发现机制
- ✅ **广播模式** (发送端)：
  - 定期广播探测包（默认 3 秒间隔）
  - 接收端响应发现请求
  - 支持网络广播地址（255.255.255.255）

- ✅ **监听模式** (接收端)：
  - 监听广播端口（50007）
  - 收到探测请求后立即响应
  - 支持多设备同时发现

#### 设备列表管理
- ✅ **设备信息存储**：
  - IP 地址
  - 设备名称
  - 协议版本
  - WebSocket 支持状态
  - 首次/最后活跃时间

- ✅ **超时清理**：
  - 设备超时阈值（默认 30 秒）
  - 自动清理离线设备
  - 触发离线回调

- ✅ **持久化**：
  - 缓存设备列表到 `/tmp/ls_send_devices.pkl`
  - 启动时自动加载缓存
  - 设备列表变更时保存

- ✅ **设备更新检测**：
  - 设备名称变更检测
  - 触发更新回调

#### 回调机制
```python
on_device_found(device)      # 发现新设备
on_device_lost(ip)           # 设备离线
on_device_updated(device)    # 设备信息更新
```

### 1.2 API 设计

#### 类：`UDPDiscoveryService`

**主要方法**：

| 方法 | 说明 |
|------|------|
| `start(is_receiver=False)` | 启动服务 |
| `stop()` | 停止服务 |
| `get_devices(timeout=None)` | 获取设备列表 |
| `get_device_by_ip(ip)` | 通过 IP 获取设备 |
| `is_device_online(ip)` | 检查设备是否在线 |
| `clear_devices()` | 清空设备列表 |
| `set_device_timeout(seconds)` | 设置超时时间 |

**配置参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `BROADCAST_PORT` | 50007 | 广播端口 |
| `DISCOVERY_INTERVAL` | 3.0 | 广播间隔（秒） |
| `DEVICE_TIMEOUT` | 30.0 | 设备超时（秒） |
| `DEVICE_CACHE_FILE` | `/tmp/ls_send_devices.pkl` | 缓存文件路径 |

---

## 2. WebSocket 传输服务 (`common/websocket_transfer.py`)

### 2.1 功能实现

#### 传输协议
- ✅ **初始化握手**：
  - 发送端：`INIT` → `REQUEST_SEND`
  - 接收端：`INIT` → `ACCEPT` / `REJECT`

- ✅ **分块传输**：
  - `BLOCK` 消息，Base64 编码
  - 序列号保障顺序
  - 64KB 默认块大小

- ✅ **进度反馈**：
  - 接收端推送：`PROGRESS` 每块更新
  - 发送端接收进度更新

- ✅ **完成确认**：
  - `COMPLETE` + 校验和验证
  - `FAILED` + 错误原因

- ✅ **心跳保活**：
  - `HEARTBEAT` 消息互发
  - 超时检测（30 秒）

#### 接收端服务 (`WebSocketTransferService`)

**核心功能**：
- TCP socket 监听（端口 50008）
- 多连接支持
- 文件块拼接
- 校验和验证
- 守护进程（心跳检查）

**数据流向**：
```
发送端 → 接收端
INIT(REQUEST_SEND) → 初始握手
BLOCK(seq, data) → 文件块传输
PROGRESS(percent, transferred) → 进度推送
COMPLETE(checksum) / FAILED(reason) → 结束
```

#### 发送端客户端 (`WebSocketClient`)

**核心功能**：
- 连接到接收端
- 分块读取文件
- Base64 编码发送
- 接收进度更新
- 完成确认

**数据流向**：
```
发送端 → 接收端
CONNECT → TCP 连接
INIT(REQUEST_SEND) → 文件请求
BLOCK(seq, data) → 文件块
HEARTBEAT → 心跳
PROGRESS → 接收进度
COMPLETE → 完成确认
```

#### 传输会话 (`TransferSession`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_id` | str | 会话唯一标识 |
| `peer_ip` | str | 对端 IP |
| `peer_port` | int | 对端端口 |
| `file_path` | str | 文件路径 |
| `file_name` | str | 文件名 |
| `file_size` | int | 文件大小 |
| `checksum` | str | MD5 校验和 |
| `state` | TransferState | 传输状态 |
| `transferred` | int | 已传输字节数 |
| `blocks_sent` | int | 发送块数 |
| `blocks_acknowledged` | int | 已确认块数 |
| `progress` | float | 进度百分比 |
| `speed` | float | 传输速度 (B/s) |

#### 传输状态机

```
INITIALIZING → CONNECTING → AWAITING_CONFIRMATION → TRANSFERRING → COMPLETED
                                                                 ↓
                                                              FAILED
                                                                 ↓
                                                             CANCELLED
```

#### 守护进程

**心跳检查线程**：
- 每 10 秒检查一次
- 超时阈值：30 秒
- 超时触发：传输失败回调

### 2.2 API 设计

#### 类：`WebSocketTransferService`

**主要方法**：

| 方法 | 说明 |
|------|------|
| `start(port=50008)` | 启动服务 |
| `stop()` | 停止服务 |
| `get_session(session_id)` | 获取会话 |
| `get_all_sessions()` | 获取所有会话 |

**回调**：

| 回调 | 参数 |
|------|------|
| `on_transfer_start(session)` | 传输开始 |
| `on_transfer_progress(session)` | 进度更新 |
| `on_transfer_complete(session)` | 传输完成 |
| `on_transfer_failed(session, reason)` | 传输失败 |
| `on_connection_established(ip)` | 连接建立 |
| `on_connection_closed(ip)` | 连接关闭 |

#### 类：`WebSocketClient`

**主要方法**：

| 方法 | 说明 |
|------|------|
| `connect()` | 连接到对端 |
| `disconnect()` | 断开连接 |
| `send_file(file_path)` | 发送文件 |

**回调**：

| 回调 | 参数 |
|------|------|
| `on_connected(ip)` | 连接成功 |
| `on_disconnected(ip)` | 连接断开 |
| `on_transfer_complete(session)` | 传输完成 |
| `on_transfer_failed(session, reason)` | 传输失败 |
| `on_transfer_progress(session)` | 进度更新 |

---

## 3. 测试脚本

### 3.1 UDP 测试 (`test_udp.py`)

**运行方式**：

```bash
# 发送端（广播发现）
python test_udp.py --mode sender --device-name "My-PC"

# 接收端（监听响应）
python test_udp.py --mode receiver --device-name "My-Phone"

# 10 秒后自动退出
python test_udp.py --timeout 10
```

**功能特性**：
- ✅ 设备列表显示
- ✅ 新设备发现通知
- ✅ 设备离线提示
- ✅ 信号处理（Ctrl+C）
- ✅ 自动超时退出

### 3.2 WebSocket 测试 (`test_ws.py`)

**运行方式**：

```bash
# 接收端
python test_ws.py --mode receiver --port 50008
python test_ws.py -r

# 发送端
python test_ws.py --mode sender --peer-ip 192.168.1.100 --file test.pdf
python test_ws.py -s 192.168.1.100 test.pdf
```

**功能特性**：
- ✅ 进度条显示
- ✅ 传输速度计算
- ✅ 文件校验和验证
- ✅ 错误处理
- ✅ 信号处理

**界面示例**：

```
[2026-03-08 11:30:00] 🚀 Transfer started:
    Session: a1b2c3d4
    File: test.pdf
    Size: 12.5 MB
    Peer: 192.168.1.101

[2026-03-08 11:30:00] 🔁 64.23% [████████████░░░░░░░░░░░░░░░░░░░░] 8.0 MB/12.5 MB (2.3 MB/s)
[2026-03-08 11:30:01] 🔁 100.00% [████████████████████████████████] 12.5 MB/12.5 MB (2.1 MB/s)

[2026-03-08 11:30:01] ✅ Transfer completed!
    Session: a1b2c3d4
    File: test.pdf
    Size: 12.5 MB
    Checksum: 5d41402abc4b2a76b9719d911017c592
```

---

## 4. 开发进展

| 阶段 | 任务 | 状态 |
|------|------|------|
| Phase 1 | 协议定义 | ✅ 完成 |
| Phase 1 | 工具函数 | ✅ 完成 |
| Phase 1 | 异常类 | ✅ 完成 |
| Phase 1 | 多语言管理 | ✅ 完成 |
| Phase 2 | UDP 基础框架 | ✅ 完成 |
| Phase 2 ** | UDP 发现服务 | ✅ 完成 |
| Phase 3 | WebSocket 基础框架 | ✅ 完成 |
| Phase 3 ** | WebSocket 传输服务 | ✅ 完成 |
| Test | UDP 测试脚本 | ✅ 完成 |
| Test | WebSocket 测试脚本 | ✅ 完成 |

**‘** 表示本次完成的工作

---

## 5. 文件清单

### 核心代码

| 文件 | 行数 | 说明 |
|------|------|------|
| `common/protocol.py` | 80 | 协议定义 |
| `common/utils.py` | 95 | 工具函数 |
| `common/exceptions.py` | 25 | 异常类 |
| `common/localization.py` | - | 多语言管理 |
| `common/udp_discovery.py` | 13436 字节 | **UDP 发现服务** |
| `common/websocket_transfer.py` | 34448 字节 | **WebSocket 传输** |

### 测试代码

| 文件 | 行数 | 说明 |
|------|------|------|
| `test_udp.py` | 4938 字节 | UDP 测试 |
| `test_ws.py` | 10134 字节 | WebSocket 测试 |

---

## 6. 技术难点与解决方案

### 6.1 UDP 广播
**问题**：广播地址需要特殊 socket 选项

**解决**：
```python
self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
```

### 6.2 文件分块传输
**问题**：大文件内存占用

**解决**：分块读取 + 流式传输
```python
with open(filepath, 'rb') as f:
    while True:
        data = f.read(chunk_size)
        if not data:
            break
        # 发送 data
```

### 6.3 进度实时更新
**问题**：异步回调机制

**解决**：同时支持同步和异步回调
```python
if asyncio.iscoroutinefunction(callback):
    await callback(*args)
else:
    callback(*args)
```

### 6.4 网络异常处理
**问题**：断线重连、超时

**解决**：
- TCP 连接异常捕获
- Heartbeat 超时检测
- 自动清理失效会话

---

## 7. 后续优化方向

### 传输优化
- [ ] 多线程/异步文件 I/O
- [ ] 动态块大小调整（根据网络状况）
- [ ] 传输限速（避免占满带宽）
- [ ] 断点续传（支持续传未完成的文件）

### 安全增强
- [ ] TLS 加密传输
- [ ] 身份认证
- [ ] 访问控制列表

### 用户体验
- [ ] 文件预览（小文件）
- [ ] 批量传输
- [ ] 传输队列
- [ ] 历史记录

### Web 管理界面
- [ ] 设备列表展示
- [ ] 传输历史
- [ ] 实时进度监控

---

## 8. 测试验证

### UDP 发现测试
```bash
# Terminal 1: Receiver
python test_udp.py --mode receiver --device-name "Android-Phone"

# Terminal 2: Sender
python test_udp.py --mode sender --device-name "Windows-PC"
```

**预期结果**：
- Receiver 显示 "Listening for discovery requests..."
- Sender 广播并显示发现的设备
- 设备列表实时更新

### WebSocket 传输测试
```bash
# Terminal 1: Receiver
python test_ws.py --mode receiver --port 50008

# Terminal 2: Sender
echo "test content" > /tmp/test.txt
python test_ws.py --mode sender --peer-ip 127.0.0.1 --file /tmp/test.txt
```

**预期结果**：
- Receiver 显示 "Waiting for incoming connections..."
- Sender 连接并开始传输
- 实时进度条显示
- 传输完成后验证文件一致性

---

## 9. 总结

本次开发完成了：

✅ UDP 自发现服务（接收端 + 发送端 + 设备管理 + 持久化）  
✅ WebSocket 传输服务（接收端 + 发送端 + 完整传输流）  
✅ 测试脚本（UDP + WebSocket）  

**代码质量**：
- 符合 PEP 8 规范
- 完整的文档注释
- 异常处理完善
- 回调机制灵活

**下一步**：
- 集成测试（端到端）
- 性能测试（大文件传输）
- 实际场景验证
