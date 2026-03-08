"""
LS send UDP 广播服务测试脚本

运行方式：
    python test_udp.py [--mode sender|receiver] [--device-name NAME] [--timeout.SECONDS]
"""

import asyncio
import signal
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

# 导入本地模块
sys.path.insert(0, str(Path(__file__).parent))

from common.udp_discovery import UDPDiscoveryService, DiscoveredDevice


class UDPTestApp:
    """UDP 发现测试应用"""
    
    def __init__(self, mode: str = "sender", device_name: str = "TEST_DEVICE"):
        self.mode = mode
        self.device_name = device_name
        self.service = None
        self.running = True
        
        print(f"[{datetime.now()}] Starting UDP test app (mode={mode}, device_name={device_name})")
    
    def on_device_found(self, device: DiscoveredDevice):
        """发现新设备回调"""
        print(f"\n[{datetime.now()}] 📡 New device found:")
        print(f"    IP: {device.ip}")
        print(f"    Name: {device.device_name}")
        print(f"    Version: {device.version}")
        print(f"    WebSocket: {device.supports_websocket}")
        print(f"    First seen: {datetime.fromtimestamp(device.first_seen)}")
        print(f"    Last seen: {datetime.fromtimestamp(device.last_seen)}")
        print()
    
    def on_device_lost(self, ip: str):
        """设备离线回调"""
        print(f"\n[{datetime.now()}] ⚠️ Device lost: {ip}")
        print()
    
    def on_device_updated(self, device: DiscoveredDevice):
        """设备信息更新回调"""
        print(f"\n[{datetime.now()}] 🔄 Device updated: {device.ip}")
        print(f"    Name: {device.device_name}")
        print()
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        sig_name = signal.Signals(signum).name
        print(f"\n[{datetime.now()}] Received signal {sig_name}")
        self.running = False
    
    def start(self):
        """启动测试"""
        self.setup_signal_handlers()
        
        # 初始化 UDP 发现服务
        self.service = UDPDiscoveryService(
            device_name=self.device_name,
            on_device_found=self.on_device_found,
            on_device_lost=self.on_device_lost,
            on_device_updated=self.on_device_updated
        )
        
        # 启动服务
        if self.mode == "receiver":
            self.service.start(is_receiver=True)
            print(f"[{datetime.now()}] 📡 Started in RECEIVER mode")
            print(f"[{datetime.now()}] Listening for discovery requests...")
        else:
            self.service.start(is_receiver=False)
            print(f"[{datetime.now()}] 📡 Started in SENDER mode")
            print(f"[{datetime.now()}] Broadcasting discovery requests...")
        
        print(f"[{datetime.now()}] Press Ctrl+C to exit")
        
        # 主循环
        try:
            while self.running:
                if self.mode == "sender":
                    # 发送端：显示设备列表
                    devices = self.service.get_devices()
                    if devices:
                        print(f"\n[{datetime.now()}] 📋 Device list ({len(devices)} devices):")
                        for i, device in enumerate(devices, 1):
                            print(f"  {i}. {device.device_name} ({device.ip})")
                    else:
                        print(f"\n[{datetime.now()}] 🔍 Scanning for devices...")
                else:
                    # 接收端：只需保持运行
                    time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        """停止测试"""
        print(f"\n[{datetime.now()}] Stopping UDP discovery service...")
        if self.service:
            self.service.stop()
        print(f"[{datetime.now()}] Service stopped")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="UDP discovery service test")
    parser.add_argument(
        "--mode",
        choices=["sender", "receiver"],
        default="sender",
        help="Run mode: sender (broadcast) or receiver (listen)"
    )
    parser.add_argument(
        "--device-name",
        default=f"TEST_{sys.argv[0].split('/')[-1].split('.')[0].upper()}",
        help="Device name for broadcasting"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Auto-exit timeout in seconds (default: 10)"
    )
    
    args = parser.parse_args()
    
    app = UDPTestApp(
        mode=args.mode,
        device_name=args.device_name
    )
    
    # 设置自动退出
    if args.timeout > 0:
        def auto_exit():
            time.sleep(args.timeout)
            app.running = False
        
        exit_thread = threading.Thread(target=auto_exit, daemon=True)
        exit_thread.start()
    
    app.start()


if __name__ == "__main__":
    main()
