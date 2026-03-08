"""
LS send 共享协议定义

作者：LS send Team
完成时间：2026-03-08
"""

# ========== UDP 自发现协议 ==========

# 发送端广播包
UDP_DISCOVERY_REQUEST = {
    "type": "DISCOVERY",
    "version": "1.0",
    "sender_name": str  # e.g., "Windows-PC-01"
}

# 接收端响应包
UDP_DISCOVERY_RESPONSE = {
    "type": "RESPONSE",
    "version": "1.0",
    "device_name": str,  # e.g., "Android-Phone-01"
    "ip": str,           # e.g., "192.168.1.100"
    "supports_websocket": bool
}

# ========== WebSocket 传输协议 ==========

# 初始化请求（发送端 → 接收端）
WS_INIT_SEND_REQUEST = {
    "type": "INIT",
    "action": "REQUEST_SEND",
    "file_name": str,      # 文件名
    "file_size": int,      # 文件大小（字节）
    "checksum": str        # 文件校验和（MD5）
}

# 初始化确认（接收端 → 发送端）
WS_INIT_RESPONSE = {
    "type": "INIT",
    "action": str,         # "ACCEPT" or "REJECT"
    "reason": str | None   # 拒绝原因（可选）
}

# 分块传输
WS_BLOCK传输 = {
    "type": "BLOCK",
    "sequence": int,      # 块序号（从 0 开始）
    "data": str           # Base64 编码的二进制数据
}

# 进度推送（接收端 → 发送端）
WS_PROGRESS_UPDATE = {
    "type": "PROGRESS",
    "percent": float,     # 0-100
    "transferred": int    # 已传输字节数
}

# 传输完成
WS_TRANSFER_COMPLETE = {
    "type": "COMPLETE",
    "checksum": str       # 最终校验和（再次验证）
}

# 传输失败
WS_TRANSFER_FAILED = {
    "type": "FAILED",
    "reason": str         # 失败原因
}

# 心跳包（保持连接）
WS_HEARTBEAT = {
    "type": "HEARTBEAT",
    "timestamp": int      # Unix 时间戳（毫秒）
}
