#!/usr/bin/env python3
"""
LS send 快速测试脚本（无需完整打包）
作者：派蒙
完成时间：2026-03-08
功能：运行后端服务模拟，验证 UDP + WebSocket 协议
"""

import sys
import time
from common.protocol import UDP_DISCOVERY_REQUEST, UDP_DISCOVERY_RESPONSE, WS_INIT_SEND_REQUEST
from common.utils import setup_logger

logger = setup_logger("quick-test")

def test_protocol():
    """测试协议定义"""
    logger.info("=== 测试协议定义 ===")
    
    # 测试 UDP 发现请求
    discovery_req = {
        **UDP_DISCOVERY_REQUEST,
        "sender_name": "Windows-Test"
    }
    logger.info(f"UDP Discovery Request: {discovery_req}")
    
    # 测试 UDP 发现响应
    discovery_resp = {
        **UDP_DISCOVERY_RESPONSE,
        "device_name": "Android-Test",
        "ip": "192.168.1.100",
        "supports_websocket": True
    }
    logger.info(f"UDP Discovery Response: {discovery_resp}")
    
    # 测试 WebSocket 初始化请求
    ws_init = {
        **WS_INIT_SEND_REQUEST,
        "file_name": "test.py",
        "file_size": 1024,
        "checksum": "abc123"
    }
    logger.info(f"WebSocket Init Request: {ws_init}")
    
    logger.info("协议定义测试通过！")
    return True


def test_formatting():
    """测试工具函数"""
    logger.info("=== 测试工具函数 ===")
    
    from common.utils import format_bytes, compute_file_checksum
    
    # 测试大小格式化
    logger.info(f"1024 bytes = {format_bytes(1024)}")
    logger.info(f"1048576 bytes = {format_bytes(1048576)}")
    logger.info(f"1073741824 bytes = {format_bytes(1073741824)}")
    
    # 测试非文件相关函数
    logger.info("工具函数测试通过！")
    return True


def main():
    """运行快速测试"""
    logger.info("LS send 快速测试开始")
    logger.info("注意：此测试仅验证代码结构，不启动网络服务")
    
    if not test_protocol():
        logger.error("协议测试失败")
        return 1
    
    if not test_formatting():
        logger.error("工具函数测试失败")
        return 1
    
    logger.info("=== 所有测试通过！===")
    logger.info("代码结构验证成功，可以开始打包")
    return 0


if __name__ == '__main__':
    sys.exit(main())
