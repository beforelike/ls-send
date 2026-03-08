"""
LS send WebSocket 传输服务测试脚本

运行方式：
    # 接收端
    python test_ws.py --mode receiver --port 50008
    
    # 发送端
    python test_ws.py --mode sender --peer-ip 192.168.1.100 --file /path/to/file
    
    # 或使用简写形式
    python test_ws.py -r (receiver)
    python test_ws.py -s 192.168.1.100 /path/to/file (sender)
"""

import asyncio
import signal
import sys
import os
from datetime import datetime
from pathlib import Path
import argparse

# 导入本地模块
sys.path.insert(0, str(Path(__file__).parent))

from common.websocket_transfer import (
    WebSocketTransferService,
    WebSocketClient,
    TransferSession,
    TransferState,
    compute_file_checksum
)
from common.utils import format_bytes


class WebSocketTestApp:
    """WebSocket 传输测试应用"""
    
    def __init__(self, mode: str, peer_ip: str = "", file_path: str = "", port: int = 50008):
        self.mode = mode
        self.peer_ip = peer_ip
        self.file_path = file_path
        self.port = port
        
        self.service = None
        self.client = None
        self.running = True
        self.transfer_session = None
        
        print(f"[{datetime.now()}] Starting WebSocket test app (mode={mode})")
        if mode == "sender":
            print(f"[{datetime.now()}] Target: {peer_ip}:{port}")
            print(f"[{datetime.now()}] File: {file_path}")
        elif mode == "receiver":
            print(f"[{datetime.now()}] Listening on port {port}")
    
    async def on_transfer_start(self, session: TransferSession):
        """传输开始回调"""
        print(f"\n[{datetime.now()}] 🚀 Transfer started:")
        print(f"    Session: {session.session_id}")
        print(f"    File: {session.file_name}")
        print(f"    Size: {format_bytes(session.file_size)}")
        print(f"    Peer: {session.peer_ip}")
    
    async def on_transfer_progress(self, session: TransferSession):
        """进度更新回调"""
        if session.file_size > 0:
            progress = session.progress
            speed = session.speed
            
            # 进度条
            bar_length = 40
            filled = int(bar_length * progress / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            sys.stdout.write(
                f"\r[{datetime.now()}] 🔁 {progress:6.2f}% [{bar}] "
                f"{format_bytes(session.transferred)}/{format_bytes(session.file_size)} "
                f"({format_bytes(speed)}/s)      "
            )
            sys.stdout.flush()
    
    async def on_transfer_complete(self, session: TransferSession):
        """传输完成回调"""
        print(f"\n\n[{datetime.now()}] ✅ Transfer completed!")
        print(f"    Session: {session.session_id}")
        print(f"    File: {session.file_name}")
        print(f"    Size: {format_bytes(session.file_size)}")
        print(f"    Checksum: {session.checksum}")
        
        if self.mode == "receiver":
            print(f"    Saved to: {session.file_path}")
        
        # 保存结果
        self.transfer_session = session
    
    async def on_transfer_failed(self, session: TransferSession, reason: str):
        """传输失败回调"""
        print(f"\n\n[{datetime.now()}] ❌ Transfer failed!")
        print(f"    Session: {session.session_id}")
        print(f"    Reason: {reason}")
        
        self.transfer_session = session
    
    async def on_connection_established(self, peer_ip: str):
        """连接建立回调"""
        print(f"\n[{datetime.now()}] ✅ Connected to {peer_ip}")
    
    async def on_connection_closed(self, peer_ip: str):
        """连接关闭回调"""
        print(f"\n[{datetime.now()}] 🔌 Disconnected from {peer_ip}")
        if self.running:
            print(f"[{datetime.now()}] Reconnecting in 3 seconds...")
            await asyncio.sleep(3)
            if self.mode == "receiver" and self.service:
                print(f"[{datetime.now()}}] Service is running, continuing to listen...")
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        sig_name = signal.Signals(signum).name
        print(f"\n\n[{datetime.now()}] Received signal {sig_name}")
        self.running = False
    
    async def start_as_receiver(self):
        """启动为接收端"""
        self.setup_signal_handlers()
        
        self.service = WebSocketTransferService(
            device_name="LS_RECEIVER",
            on_transfer_start=self.on_transfer_start,
            on_transfer_progress=self.on_transfer_progress,
            on_transfer_complete=self.on_transfer_complete,
            on_transfer_failed=self.on_transfer_failed,
            on_connection_established=self.on_connection_established,
            on_connection_closed=self.on_connection_closed
        )
        
        try:
            await self.service.start(port=self.port)
            print(f"[{datetime.now()}] 📡 WebSocket server started on port {self.port}")
            print(f"[{datetime.now()}] Waiting for incoming connections...")
            
            while self.running:
                await asyncio.sleep(1)
                
                # 打印会话状态
                sessions = self.service.get_all_sessions()
                if sessions:
                    print(f"\n[{datetime.now()}] 📊 Active sessions ({len(sessions)}):")
                    for session in sessions:
                        print(f"    {session.session_id}: {session.file_name} "
                              f"({session.progress:.1f}%, {session.state.value})")
                
        except Exception as e:
            print(f"[{datetime.now()}] Error: {e}")
        finally:
            await self.service.stop()
            print(f"[{datetime.now()}] Service stopped")
    
    async def start_as_sender(self):
        """启动为发送端"""
        if not os.path.exists(self.file_path):
            print(f"[{datetime.now()}] Error: File not found: {self.file_path}")
            return
        
        self.setup_signal_handlers()
        
        # 创建 WebSocket 客户端
        self.client = WebSocketClient(
            peer_ip=self.peer_ip,
            peer_port=self.port,
            on_connected=self.on_connection_established,
            on_disconnected=self.on_connection_closed,
            on_transfer_complete=self.on_transfer_complete,
            on_transfer_failed=self.on_transfer_failed,
            on_transfer_progress=self.on_transfer_progress
        )
        
        try:
            # 连接到接收端
            print(f"[{datetime.now()}] Connecting to {self.peer_ip}:{self.port}...")
            connected = await self.client.connect()
            
            if not connected:
                print(f"[{datetime.now()}] Failed to connect")
                return
            
            print(f"[{datetime.now()}] Connected!")
            
            # 发送文件
            file_size = os.path.getsize(self.file_path)
            print(f"[{datetime.now()}] Sending {format_bytes(file_size)} file...")
            
            self.transfer_session = await self.client.send_file(self.file_path)
            
            if self.transfer_session is None:
                print(f"[{datetime.now()}] Failed to send file")
                return
            
            # 等待传输完成或失败
            while self.transfer_session.state not in [TransferState.COMPLETED, TransferState.FAILED, TransferState.CANCELLED]:
                await asyncio.sleep(1)
            
            # 显示最终结果
            if self.transfer_session.state == TransferState.COMPLETED:
                print(f"\n\n[{datetime.now()}] ✅ File sent successfully!")
                print(f"    Session: {self.transfer_session.session_id}")
                print(f"    File: {self.transfer_session.file_name}")
                print(f"    Size: {format_bytes(self.transfer_session.file_size)}")
            else:
                print(f"\n\n[{datetime.now()}] ❌ File transfer failed")
                
        except Exception as e:
            print(f"[{datetime.now()}] Error: {e}")
        finally:
            await self.client.disconnect()
            print(f"[{datetime.now()}] Disconnected")
    
    async def run(self):
        """运行测试"""
        if self.mode == "receiver":
            await self.start_as_receiver()
        else:
            await self.start_as_sender()


async def async_main(args):
    """异步主函数"""
    app = WebSocketTestApp(
        mode=args.mode,
        peer_ip=args.peer_ip,
        file_path=args.file,
        port=args.port
    )
    await app.run()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="WebSocket transfer service test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Receiver mode
    python test_ws.py --mode receiver --port 50008
    python test_ws.py -r

    # Sender mode
    python test_ws.py --mode sender --peer-ip 192.168.1.100 --file /path/to/file
    python test_ws.py -s 192.168.1.100 /path/to/file
        """
    )
    
    parser.add_argument(
        "--mode", "-m",
        choices=["sender", "receiver", "s", "r"],
        required=True,
        help="Run mode: sender or receiver"
    )
    
    parser.add_argument(
        "--peer-ip",
        default="127.0.0.1",
        help="Target IP address (sender mode only)"
    )
    
    parser.add_argument(
        "--file", "-f",
        help="File to send (sender mode only)"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=50008,
        help="WebSocket port (default: 50008)"
    )
    
    args = parser.parse_args()
    
    # 处理简写模式
    if args.mode == "r":
        args.mode = "receiver"
    elif args.mode == "s":
        args.mode = "sender"
    
    # 验证参数
    if args.mode == "sender":
        if not args.file:
            parser.error("Sender mode requires --file / -f")
        if not os.path.exists(args.file):
            parser.error(f"File not found: {args.file}")
    
    # 运行测试
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
