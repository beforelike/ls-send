#!/usr/bin/env python3
"""
LS send 主入口（Phase 2-3）

功能：
- UDP + WebSocket 服务整合
- 命令行接口（测试用）
- 简单的设备列表 UI（text-based）

作者：BW-001
完成时间：2026-03-08
"""

import asyncio
import sys
import threading
import time
from typing import Optional

from common.udp_discovery import UDPDiscoveryService, DiscoveredDevice
from common.websocket_transfer import WebSocketTransferService, WebSocketClient
from common.utils import format_bytes, setup_logger
from common.localization import Localization

logger = setup_logger(__name__)

# 初始化国际化
localization = Localization('zh')


class LSSendApp:
    """LS send 主应用"""
    
    def __init__(self):
        self.device_name = localization.get("app_title") + "-PC"
        self.udp_service: Optional[UDPDiscoveryService] = None
        self.ws_service: Optional[WebSocketTransferService] = None
        self.running = False
        
        # 设备列表
        self.discovered_devices: dict[str, DiscoveredDevice] = {}
        
        logger.info(f"LSSendApp initialized (device_name={self.device_name})")
    
    def start(self):
        """启动应用"""
        self.running = True
        print(f"[{localization.get('app_title')}] Starting...")
        
        # 启动 UDP 服务
        self.udp_service = UDPDiscoveryService(
            device_name=self.device_name,
            on_device_found=self._on_device_found,
            on_device_lost=self._on_device_lost
        )
        self.udp_service.start()
        
        # 启动 WebSocket 服务
        self.ws_service = WebSocketTransferService(
            device_name=self.device_name,
            on_transfer_start=self._on_transfer_start,
            on_transfer_progress=self._on_transfer_progress,
            on_transfer_complete=self._on_transfer_complete,
            on_transfer_failed=self._on_transfer_failed
        )
        
        # 运行事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.create_task(self.ws_service.start())
        
        # 启动命令行 UI
        self._start_cli(loop)
    
    def stop(self):
        """停止应用"""
        self.running = False
        
        if self.udp_service:
            self.udp_service.stop()
        
        if self.ws_service:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.ws_service.stop())
        
        print(f"[{localization.get('app_title')}] Stopped")
    
    def _on_device_found(self, device: DiscoveredDevice):
        """发现新设备回调"""
        self.discovered_devices[device.ip] = device
        print(f"\n[{localization.get('app_title')}] {localization.get('transferring').format(filename=device.device_name)} ({device.ip})")
    
    def _on_device_lost(self, ip: str):
        """设备离线回调"""
        if ip in self.discovered_devices:
            del self.discovered_devices[ip]
            print(f"\n[{localization.get('app_title')}] {ip} offline")
    
    def _on_transfer_start(self, session_id: str):
        """传输开始"""
        print(f"\n[{localization.get('app_title')}] [{session_id}] {localization.get('transferring').format(filename='')}")
    
    def _on_transfer_progress(self, session_id: str, progress: float):
        """传输进度"""
        print(f"\r[{localization.get('app_title')}] [{session_id}] {progress:.1f}%", end='', flush=True)
    
    def _on_transfer_complete(self, session_id: str, checksum: str):
        """传输完成"""
        print(f"\n[{localization.get('app_title')}] [{session_id}] {localization.get('complete')}, checksum={checksum}")
    
    def _on_transfer_failed(self, session_id: str, reason: str):
        """传输失败"""
        print(f"\n[{localization.get('app_title')}] [{session_id}] {localization.get('failed')}: {reason}")
    
    def _start_cli(self, loop):
        """启动命令行 UI"""
        print(f"\n{'='*50}")
        print(f"  {localization.get('app_title')} - Command Line Interface")
        print(f"{'='*50}")
        print(f"\n{localization.get('device_list_label')}")
        
        while self.running:
            devices = self.udp_service.get_devices()
            
            print(f"\n[{localization.get('app_title')}] 设备列表 ({len(devices)} 台):")
            for i, device in enumerate(devices, 1):
                print(f"  {i}. {device.device_name} ({device.ip})")
            
            print(f"\n命令: ls - 刷新设备列表")
            print(f"      send <id> <filepath> - 发送文件")
            print(f"      quit - 退出程序")
            
            try:
                cmd = input(f"\n[{localization.get('app_title')}]> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            
            if cmd == "ls":
                continue
            elif cmd == "quit":
                break
            elif cmd.startswith("send "):
                parts = cmd.split()
                if len(parts) >= 3:
                    device_id = int(parts[1])
                    filepath = parts[2]
                    
                    if device_id <= len(devices):
                        target = devices[device_id - 1]
                        print(f"\n[{localization.get('app_title')}] 发送到 {target.device_name} ({target.ip})")
                        
                        # 启动发送
                        asyncio.run_coroutine_threadsafe(
                            self._send_file(target.ip, filepath),
                            loop
                        )
                    else:
                        print(f"[{localization.get('app_title')}] 设备 ID 无效")
                else:
                    print(f"[{localization.get('app_title')}] 用法: send <id> <filepath>")
            elif cmd == "":
                continue
            else:
                print(f"[{localization.get('app_title')}] 未知命令: {cmd}")
        
        self.stop()
    
    async def _send_file(self, peer_ip: str, filepath: str):
        """发送文件到指定 IP"""
        client = WebSocketClient(peer_ip)
        
        if await client.connect():
            success = await client.send_file(filepath)
            
            if success:
                print(f"[{localization.get('app_title')}] 传输过程中... (按 Ctrl+C 停止)")
                while True:
                    try:
                        await asyncio.sleep(1)
                    except KeyboardInterrupt:
                        break
            
            await client.disconnect()


def main():
    """主入口"""
    print(f"\n{'='*50}")
    print(f"  {localization.get('app_title')} - Phase 2-3")
    print(f"{'='*50}")
    
    app = LSSendApp()
    
    try:
        app.start()
    except KeyboardInterrupt:
        print("\n\n[INFO] Received keyboard interrupt")
    finally:
        app.stop()


if __name__ == "__main__":
    main()
