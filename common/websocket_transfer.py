"""
LS send WebSocket 传输服务

功能：
- 发送端：连接多个接收端，分块发送文件，接收确认
- 接收端：监听 WebSocket 连接，接收文件并推送进度
- 完整的握手 + 传输流
- 守护进程支持
"""

import asyncio
import json
import os
import hashlib
import base64
from typing import Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time
from datetime import datetime
import threading
import signal
import sys

from .protocol import (
    WS_INIT_SEND_REQUEST,
    WS_INIT_RESPONSE,
    WS_BLOCK传输,
    WS_PROGRESS_UPDATE,
    WS_TRANSFER_COMPLETE,
    WS_TRANSFER_FAILED,
    WS_HEARTBEAT
)
from .utils import setup_logger, encode_chunk, calculate_progress, chunk_file, format_bytes
from .exceptions import FileError, TransferError

logger = setup_logger(__name__)


class TransferState(Enum):
    """传输状态"""
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TransferSession:
    """传输会话信息"""
    session_id: str
    peer_ip: str
    peer_port: int = 50008
    file_path: str = ""
    file_name: str = ""
    file_size: int = 0
    checksum: str = ""
    state: TransferState = TransferState.INITIALIZING
    transferred: int = 0
    blocks_sent: int = 0
    blocks_acknowledged: int = 0
    chunk_size: int = 65536  # 64KB
    last_heartbeat: float = 0.0
    last_block_time: float = 0.0
    message_queue: list = field(default_factory=list)
    file_handle = None  # 文件句柄（读取/写入）
    
    @property
    def progress(self) -> float:
        if self.file_size == 0:
            return 100.0
        return round((self.transferred / self.file_size) * 100, 2)
    
    @property
    def remaining_size(self) -> int:
        return self.file_size - self.transferred
    
    @property
    def speed(self) -> float:
        """计算传输速度（字节/秒）"""
        if self.last_block_time == 0:
            return 0.0
        elapsed = time.time() - self.last_block_time
        if elapsed <= 0:
            return 0.0
        return self.chunk_size / elapsed
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "peer_ip": self.peer_ip,
            "peer_port": self.peer_port,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "transferred": self.transferred,
            "progress": self.progress,
            "state": self.state.value,
            "blocks_sent": self.blocks_sent,
            "blocks_acknowledged": self.blocks_acknowledged
        }


class WebSocketTransferService:
    """WebSocket 传输服务"""
    
    # WebSocket 配置
    DEFAULT_PORT = 50008
    HEARTBEAT_INTERVAL = 10.0  # 秒
    HEARTBEAT_TIMEOUT = 30.0   # 秒
    
    def __init__(
        self,
        device_name: str = "LS_SEND_DEVICE",
        on_transfer_start: Optional[Callable[[TransferSession], None]] = None,
        on_transfer_progress: Optional[Callable[[TransferSession], None]] = None,
        on_transfer_complete: Optional[Callable[[TransferSession], None]] = None,
        on_transfer_failed: Optional[Callable[[TransferSession, str], None]] = None,
        on_connection_established: Optional[Callable[[str], None]] = None,
        on_connection_closed: Optional[Callable[[str], None]] = None
    ):
        """
        初始化 WebSocket 传输服务
        
        Args:
            device_name: 设备名称
            on_transfer_start: 传输开始回调 (session)
            on_transfer_progress: 进度更新回调 (session)
            on_transfer_complete: 传输完成回调 (session)
            on_transfer_failed: 传输失败回调 (session, reason)
            on_connection_established: 连接建立回调 (peer_ip)
            on_connection_closed: 连接关闭回调 (peer_ip)
        """
        self.device_name = device_name
        self.on_transfer_start = on_transfer_start
        self.on_transfer_progress = on_transfer_progress
        self.on_transfer_complete = on_transfer_complete
        self.on_transfer_failed = on_transfer_failed
        self.on_connection_established = on_connection_established
        self.on_connection_closed = on_connection_closed
        
        self._sessions: dict[str, TransferSession] = {}
        self._sessions_by_ip: dict[str, str] = {}  # IP -> session_id 映射
        self._server: Optional[asyncio.Server] = None
        self._running = False
        self._port = self.DEFAULT_PORT
        
        self._server_reader: Optional[asyncio.StreamReader] = None
        self._server_writer: Optional[asyncio.StreamWriter] = None
        
        # 守护进程相关
        self._heartbeat_thread: Optional[threading.Thread] = None
        
        logger.info(f"WebSocketTransferService initialized (device_name={device_name})")
    
    async def start(self, port: Optional[int] = None):
        """
        启动 WebSocket 服务（接收端模式）
        
        Args:
            port: WebSocket 端口（默认 50008）
        """
        if self._running:
            logger.warning("WebSocketTransferService is already running")
            return
        
        self._running = True
        self._port = port or self.DEFAULT_PORT
        
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                host="0.0.0.0",
                port=self._port
            )
            
            # 启动守护进程（心跳检查）
            self._start_heartbeat_checker()
            
            logger.info(f"WebSocket server started on port {self._port}")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise
    
    async def stop(self):
        """停止服务"""
        if not self._running:
            return
        
        self._running = False
        
        # 关闭所有传输会话
        for session_id in list(self._sessions.keys()):
            session = self._sessions[session_id]
            session.state = TransferState.CANCELLED
            if session.file_handle:
                try:
                    session.file_handle.close()
                except:
                    pass
                session.file_handle = None
        
        # 停止守护进程
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2.0)
            self._heartbeat_thread = None
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        
        logger.info("WebSocketTransferService stopped")
    
    def _start_heartbeat_checker(self):
        """启动心跳检查线程"""
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
    
    def _heartbeat_loop(self):
        """心跳检查循环"""
        while self._running:
            try:
                time.sleep(self.HEARTBEAT_INTERVAL)
                self._check_heartbeat_timeout()
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    def _check_heartbeat_timeout(self):
        """检查心跳超时"""
        current_time = time.time()
        
        for session_id, session in list(self._sessions.items()):
            # 只检查处于传输状态的会话
            if session.state not in [TransferState.TRANSFERRING, TransferState.AWAITING_CONFIRMATION]:
                continue
            
            if current_time - session.last_heartbeat > self.HEARTBEAT_TIMEOUT:
                logger.warning(f"Heartbeat timeout for session {session_id}")
                
                if session.state != TransferState.COMPLETED:
                    session.state = TransferState.FAILED
                    if self.on_transfer_failed:
                        asyncio.run_coroutine_threadsafe(
                            self.on_transfer_failed(session, "Heartbeat timeout"),
                            asyncio.get_event_loop()
                        )
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """处理 WebSocket 客户端连接"""
        peer_ip = writer.get_extra_info('peername')[0]
        peer_port = writer.get_extra_info('peername')[1]
        
        logger.info(f"New connection from {peer_ip}:{peer_port}")
        
        # 创建会话
        session = TransferSession(
            session_id=str(uuid.uuid4())[:8],
            peer_ip=peer_ip,
            peer_port=peer_port,
            state=TransferState.CONNECTING,
            last_heartbeat=time.time()
        )
        self._sessions[session.session_id] = session
        self._sessions_by_ip[peer_ip] = session.session_id
        
        # 连接建立回调
        if self.on_connection_established:
            asyncio.create_task(self._safe_callback(self.on_connection_established, peer_ip))
        
        try:
            while self._running and not reader.at_eof():
                data = await reader.readline()
                if not data:
                    break
                
                message = json.loads(data.decode('utf-8'))
                await self._process_message(message, writer, session)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON from {peer_ip}: {e}")
        except ConnectionResetError:
            logger.info(f"Connection reset by {peer_ip}")
        except Exception as e:
            logger.error(f"Error handling client {peer_ip}: {e}")
        finally:
            # 清理会话
            if session.session_id in self._sessions:
                del self._sessions[session.session_id]
            if peer_ip in self._sessions_by_ip:
                del self._sessions_by_ip[peer_ip]
            
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass
            
            logger.info(f"Connection closed: {peer_ip}")
            
            # 连接关闭回调
            if self.on_connection_closed:
                asyncio.create_task(self._safe_callback(self.on_connection_closed, peer_ip))
    
    async def _safe_callback(self, callback: Callable, *args):
        """安全执行异步回调"""
        try:
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args)
                else:
                    callback(*args)
        except Exception as e:
            logger.error(f"Error in callback: {e}")
    
    async def _process_message(self, message: dict, writer: asyncio.StreamWriter, session: TransferSession):
        """处理收到的消息"""
        msg_type = message.get("type")
        action = message.get("action")
        
        # 更新最后心跳时间
        session.last_heartbeat = time.time()
        
        logger.debug(f"Received message: {msg_type}, action={action}")
        
        if msg_type == "INIT":
            await self._handle_init(message, writer, session)
        elif msg_type == "BLOCK":
            await self._handle_block(message, writer, session)
        elif msg_type == "PROGRESS":
            await self._handle_progress(message, writer, session)
        elif msg_type == "COMPLETE":
            await self._handle_complete(message, writer, session)
        elif msg_type == "FAILED":
            await self._handle_failed(message, writer, session)
        elif msg_type == "HEARTBEAT":
            await self._handle_heartbeat(message, writer)
        else:
            logger.warning(f"Unknown message type: {msg_type}")
    
    async def _handle_init(self, message: dict, writer: asyncio.StreamWriter, session: TransferSession):
        """处理初始化请求"""
        action = message.get("action")
        
        if action == "REQUEST_SEND":
            # 接收端：处理发送请求
            file_name = message.get("file_name")
            file_size = message.get("file_size")
            checksum = message.get("checksum")
            
            logger.info(f"File transfer request from {session.peer_ip}: {file_name} ({format_bytes(file_size)})")
            
            # 保存会话信息
            session.file_name = file_name
            session.file_size = file_size
            session.checksum = checksum
            session.file_path = f"/tmp/ls_send_{file_name}"
            session.state = TransferState.AWAITING_CONFIRMATION
            
            # 模拟用户确认（实际应用中应提示用户）
            # 这里默认接受
            await self._send_response(
                writer,
                {
                    **WS_INIT_RESPONSE,
                    "action": "ACCEPT",
                    "reason": None
                }
            )
            
            session.state = TransferState.TRANSFERRING
            session.last_block_time = time.time()
            
            # 传输开始回调
            if self.on_transfer_start:
                await self._safe_callback(self.on_transfer_start, session)
                
        elif action == "ACCEPT":
            # 发送端：接收确认
            session.state = TransferState.TRANSFERRING
            session.last_block_time = time.time()
            
            # 开始发送文件
            if session.file_path:
                asyncio.create_task(self._send_file_blocks(writer, session))
                
        elif action == "REJECT":
            # 发送端：接收拒绝
            reason = message.get("reason", "Unknown")
            session.state = TransferState.FAILED
            
            logger.warning(f"Transfer rejected by {session.peer_ip}: {reason}")
            
            if self.on_transfer_failed:
                await self._safe_callback(self.on_transfer_failed, session, reason)
    
    async def _handle_block(self, message: dict, writer: asyncio.StreamWriter, session: TransferSession):
        """处理分块传输（接收端）"""
        seq = message.get("sequence")
        data_b64 = message.get("data")
        
        if seq is None or data_b64 is None:
            logger.warning(f"Invalid block message from {session.peer_ip}")
            return
        
        try:
            # 解码数据
            data = decode_chunk(data_b64)
            
            # 如果是第一次接收，创建文件
            if session.file_handle is None:
                # 创建临时文件
                os.makedirs(os.path.dirname(session.file_path), exist_ok=True)
                session.file_handle = open(session.file_path, 'wb')
            
            # 追加写入文件
            session.file_handle.write(data)
            session.file_handle.flush()
            
            session.transferred += len(data)
            session.blocks_sent += 1
            session.last_block_time = time.time()
            
            # 推送进度
            progress = calculate_progress(session.transferred, session.file_size)
            logger.debug(f"Block {seq} received ({len(data)} bytes), progress: {progress}%")
            
            # 推送进度给发送端
            await self._send_response(
                writer,
                {
                    **WS_PROGRESS_UPDATE,
                    "percent": progress,
                    "transferred": session.transferred
                }
            )
            
            # 进度回调
            if self.on_transfer_progress:
                await self._safe_callback(self.on_transfer_progress, session)
            
            # 检查传输完成
            if session.transferred >= session.file_size:
                await self._finalize_transfer(session, writer)
                
        except Exception as e:
            logger.error(f"Error handling block from {session.peer_ip}: {e}")
            await self._send_response(
                writer,
                {
                    **WS_TRANSFER_FAILED,
                    "reason": str(e)
                }
            )
    
    async def _handle_progress(self, message: dict, writer: asyncio.StreamWriter, session: TransferSession):
        """处理进度更新（发送端）"""
        percent = message.get("percent", 0)
        transferred = message.get("transferred", 0)
        
        session.transferred = transferred
        session.blocks_acknowledged = message.get("blocks_acknowledged", session.blocks_sent)
        
        logger.debug(f"Progress update from {session.peer_ip}: {percent}%")
        
        # 进度回调
        if self.on_transfer_progress:
            await self._safe_callback(self.on_transfer_progress, session)
    
    async def _handle_complete(self, message: dict, writer: asyncio.StreamWriter, session: TransferSession):
        """处理传输完成"""
        checksum = message.get("checksum")
        
        logger.info(f"Transfer complete from {session.peer_ip}, checksum: {checksum}")
        
        # 验证校验和
        if checksum != session.checksum:
            logger.error(f"Checksum mismatch! Expected: {session.checksum}, Got: {checksum}")
            session.state = TransferState.FAILED
            
            if self.on_transfer_failed:
                await self._safe_callback(self.on_transfer_failed, session, "Checksum mismatch")
            return
        
        session.state = TransferState.COMPLETED
        
        # 传输完成回调
        if self.on_transfer_complete:
            await self._safe_callback(self.on_transfer_complete, session)
        
        # 关闭文件句柄
        if session.file_handle:
            session.file_handle.close()
            session.file_handle = None
    
    async def _handle_failed(self, message: dict, writer: asyncio.StreamWriter, session: TransferSession):
        """处理传输失败"""
        reason = message.get("reason", "Unknown")
        
        logger.error(f"Transfer failed from {session.peer_ip}: {reason}")
        
        session.state = TransferState.FAILED
        
        if self.on_transfer_failed:
            await self._safe_callback(self.on_transfer_failed, session, reason)
    
    async def _handle_heartbeat(self, message: dict, writer: asyncio.StreamWriter):
        """处理心跳包"""
        await self._send_response(
            writer,
            WS_HEARTBEAT
        )
    
    async def _send_file_blocks(self, writer: asyncio.StreamWriter, session: TransferSession):
        """分块发送文件"""
        try:
            if not session.file_path or not os.path.exists(session.file_path):
                raise FileError(f"File not found: {session.file_path}")
            
            chunk_size = session.chunk_size
            
            with open(session.file_path, 'rb') as f:
                seq = 0
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    
                    # 编码为 Base64
                    data_b64 = encode_chunk(data)
                    
                    # 发送块
                    block_msg = {
                        **WS_BLOCK传输,
                        "sequence": seq,
                        "data": data_b64
                    }
                    
                    writer.write(json.dumps(block_msg).encode('utf-8') + b'\n')
                    await writer.drain()
                    
                    session.transferred += len(data)
                    session.blocks_sent += 1
                    session.last_block_time = time.time()
                    
                    logger.debug(f"Sent block {seq} ({len(data)} bytes)")
                    
                    seq += 1
            
            # 发送完成
            complete_msg = {
                **WS_TRANSFER_COMPLETE,
                "checksum": session.checksum
            }
            
            writer.write(json.dumps(complete_msg).encode('utf-8') + b'\n')
            await writer.drain()
            
            logger.info(f"File transfer completed: {session.file_name} ({format_bytes(session.file_size)})")
            
        except Exception as e:
            logger.error(f"Error sending file blocks: {e}")
            session.state = TransferState.FAILED
            
            # 发送失败消息
            failed_msg = {
                **WS_TRANSFER_FAILED,
                "reason": str(e)
            }
            
            try:
                writer.write(json.dumps(failed_msg).encode('utf-8') + b'\n')
                await writer.drain()
            except:
                pass
            
            if self.on_transfer_failed:
                await self._safe_callback(self.on_transfer_failed, session, str(e))
    
    async def _finalize_transfer(self, session: TransferSession, writer: asyncio.StreamWriter):
        """完成传输并验证校验和"""
        try:
            # 关闭文件句柄
            if session.file_handle:
                session.file_handle.close()
                session.file_handle = None
            
            # 计算接收文件的校验和
            received_checksum = compute_file_checksum(session.file_path)
            
            if received_checksum != session.checksum:
                logger.error(f"Checksum mismatch! Expected: {session.checksum}, Got: {received_checksum}")
                
                # 删除损坏的文件
                try:
                    if os.path.exists(session.file_path):
                        os.remove(session.file_path)
                except:
                    pass
                
                await self._send_response(
                    writer,
                    {
                        **WS_TRANSFER_FAILED,
                        "reason": "Checksum mismatch"
                    }
                )
                
                session.state = TransferState.FAILED
                if self.on_transfer_failed:
                    await self._safe_callback(self.on_transfer_failed, session, "Checksum mismatch")
                return
            
            # 传输完成
            complete_msg = {
                **WS_TRANSFER_COMPLETE,
                "checksum": received_checksum
            }
            
            await self._send_response(writer, complete_msg)
            
            logger.info(f"Transfer completed: {session.file_name} ({format_bytes(session.file_size)})")
            
            session.state = TransferState.COMPLETED
            if self.on_transfer_complete:
                await self._safe_callback(self.on_transfer_complete, session)
                
        except Exception as e:
            logger.error(f"Error finalizing transfer: {e}")
            session.state = TransferState.FAILED
            
            await self._send_response(
                writer,
                {
                    **WS_TRANSFER_FAILED,
                    "reason": str(e)
                }
            )
            
            if self.on_transfer_failed:
                await self._safe_callback(self.on_transfer_failed, session, str(e))
    
    async def _send_response(self, writer: asyncio.StreamWriter, payload: dict):
        """发送响应消息"""
        try:
            writer.write(json.dumps(payload).encode('utf-8') + b'\n')
            await writer.drain()
        except Exception as e:
            logger.error(f"Failed to send response: {e}")
    
    def _find_session_by_ip(self, peer_ip: str) -> Optional[TransferSession]:
        """通过 IP 查找会话"""
        session_id = self._sessions_by_ip.get(peer_ip)
        if session_id:
            return self._sessions.get(session_id)
        return None
    
    def get_session(self, session_id: str) -> Optional[TransferSession]:
        """获取会话"""
        return self._sessions.get(session_id)
    
    def get_all_sessions(self) -> list[TransferSession]:
        """获取所有会话"""
        return list(self._sessions.values())


class WebSocketClient:
    """WebSocket 客户端（发送端使用）"""
    
    def __init__(
        self,
        peer_ip: str,
        peer_port: int = 50008,
        on_connected: Optional[Callable[[str], None]] = None,
        on_disconnected: Optional[Callable[[str], None]] = None,
        on_transfer_complete: Optional[Callable[[TransferSession], None]] = None,
        on_transfer_failed: Optional[Callable[[TransferSession, str], None]] = None,
        on_transfer_progress: Optional[Callable[[TransferSession], None]] = None,
        chunk_size: int = 65536
    ):
        """
        初始化 WebSocket 客户端
        
        Args:
            peer_ip: 对端 IP 地址
            peer_port: 对端 WebSocket 端口
            on_connected: 连接成功回调
            on_disconnected: 连接断开回调
            on_transfer_complete: 传输完成回调
            on_transfer_failed: 传输失败回调
            on_transfer_progress: 进度更新回调
            chunk_size: 块大小
        """
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self.on_transfer_complete = on_transfer_complete
        self.on_transfer_failed = on_transfer_failed
        self.on_transfer_progress = on_transfer_progress
        self.chunk_size = chunk_size
        
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._running = False
        self._session: Optional[TransferSession] = None
        self._message_task: Optional[asyncio.Task] = None
        
        logger.info(f"WebSocketClient initialized (peer={peer_ip}:{peer_port})")
    
    async def connect(self) -> bool:
        """连接到对端"""
        try:
            self._reader, self._writer = await asyncio.open_connection(
                self.peer_ip, self.peer_port
            )
            self._running = True
            
            # 创建消息接收任务
            self._message_task = asyncio.create_task(self._receive_loop())
            
            logger.info(f"Connected to {self.peer_ip}:{self.peer_port}")
            
            if self.on_connected:
                asyncio.create_task(self._safe_callback(self.on_connected, self.peer_ip))
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.peer_ip}:{self.peer_port}: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        self._running = False
        
        # 取消消息任务
        if self._message_task:
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.CancelledError:
                pass
            self._message_task = None
        
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except:
                pass
            self._writer = None
        
        logger.info(f"Disconnected from {self.peer_ip}")
        
        if self.on_disconnected:
            asyncio.create_task(self._safe_callback(self.on_disconnected, self.peer_ip))
    
    async def _safe_callback(self, callback: Callable, *args):
        """安全执行异步回调"""
        try:
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args)
                else:
                    callback(*args)
        except Exception as e:
            logger.error(f"Error in callback: {e}")
    
    async def _receive_loop(self):
        """接收端消息循环（接收响应）"""
        try:
            while self._running and self._reader:
                try:
                    data = await self._reader.readline()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error reading data: {e}")
                    break
                    
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    await self._process_server_response(message)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON: {e}")
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
    
    async def _process_server_response(self, message: dict):
        """处理服务器响应"""
        msg_type = message.get("type")
        
        if msg_type == "INIT":
            action = message.get("action")
            if action == "ACCEPT":
                logger.info("Transfer accepted by receiver")
                # 开始发送文件
                if self._session:
                    await self._send_file_blocks()
            elif action == "REJECT":
                reason = message.get("reason", "Unknown")
                logger.warning(f"Transfer rejected: {reason}")
                if self.on_transfer_failed:
                    asyncio.create_task(self._safe_callback(self.on_transfer_failed, self._session, reason))
                    
        elif msg_type == "PROGRESS":
            # 接收进度更新
            if self._session:
                self._session.transferred = message.get("transferred", self._session.transferred)
                
            if self.on_transfer_progress:
                asyncio.create_task(self._safe_callback(self.on_transfer_progress, self._session))
                
        elif msg_type == "COMPLETE":
            if self._session:
                checksum = message.get("checksum")
                logger.info(f"Transfer complete, checksum: {checksum}")
                self._session.state = TransferState.COMPLETED
                
            if self.on_transfer_complete:
                asyncio.create_task(self._safe_callback(self.on_transfer_complete, self._session))
                
        elif msg_type == "FAILED":
            reason = message.get("reason", "Unknown")
            logger.error(f"Transfer failed: {reason}")
            if self._session:
                self._session.state = TransferState.FAILED
                
            if self.on_transfer_failed:
                asyncio.create_task(self._safe_callback(self.on_transfer_failed, self._session, reason))
        
        elif msg_type == "HEARTBEAT":
            # 心跳响应
            pass
    
    async def _send_file_blocks(self):
        """分块发送文件"""
        if not self._session:
            logger.error("No session available")
            return
        
        try:
            chunk_size = self._session.chunk_size
            
            with open(self._session.file_path, 'rb') as f:
                seq = 0
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break
                    
                    # 编码为 Base64
                    data_b64 = encode_chunk(data)
                    
                    # 发送块
                    block_msg = {
                        **WS_BLOCK传输,
                        "sequence": seq,
                        "data": data_b64
                    }
                    
                    self._writer.write(json.dumps(block_msg).encode('utf-8') + b'\n')
                    await self._writer.drain()
                    
                    self._session.transferred += len(data)
                    self._session.blocks_sent += 1
                    self._session.last_block_time = time.time()
                    
                    logger.debug(f"Sent block {seq} ({len(data)} bytes)")
                    
                    seq += 1
            
            # 发送完成
            complete_msg = {
                **WS_TRANSFER_COMPLETE,
                "checksum": self._session.checksum
            }
            
            self._writer.write(json.dumps(complete_msg).encode('utf-8') + b'\n')
            await self._writer.drain()
            
            logger.info(f"File transfer completed: {self._session.file_name}")
            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error sending file blocks: {e}")
            
            # 发送失败消息
            if self._writer and not self._writer.is_closing():
                try:
                    failed_msg = {
                        **WS_TRANSFER_FAILED,
                        "reason": str(e)
                    }
                    self._writer.write(json.dumps(failed_msg).encode('utf-8') + b'\n')
                    await self._writer.drain()
                except:
                    pass
            
            if self._session:
                self._session.state = TransferState.FAILED
                
            if self.on_transfer_failed:
                asyncio.create_task(self._safe_callback(self.on_transfer_failed, self._session, str(e)))
    
    async def send_file(self, file_path: str) -> Optional[TransferSession]:
        """
        发送文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            TransferSession: 会话对象（如果发送成功）
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        file_size = os.path.getsize(file_path)
        checksum = compute_file_checksum(file_path)
        file_name = os.path.basename(file_path)
        
        # 创建会话
        self._session = TransferSession(
            session_id=str(uuid.uuid4())[:8],
            peer_ip=self.peer_ip,
            peer_port=self.peer_port,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            checksum=checksum,
            chunk_size=self.chunk_size,
            state=TransferState.INITIALIZING
        )
        
        # 构建初始化请求
        init_request = {
            **WS_INIT_SEND_REQUEST,
            "file_name": file_name,
            "file_size": file_size,
            "checksum": checksum
        }
        
        try:
            self._writer.write(json.dumps(init_request).encode('utf-8') + b'\n')
            await self._writer.drain()
            
            logger.info(f"Sent file request: {file_name} ({format_bytes(file_size)})")
            
            self._session.state = TransferState.AWAITING_CONFIRMATION
            
            return self._session
            
        except Exception as e:
            logger.error(f"Failed to send file request: {e}")
            if self._session:
                self._session.state = TransferState.FAILED
            return None


def compute_file_checksum(filepath: str, block_size: int = 65536) -> str:
    """计算文件 MD5 校验和"""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(block_size), b''):
            md5.update(chunk)
    return md5.hexdigest()


def decode_chunk(data: str) -> bytes:
    """Base64 解码字符串为二进制"""
    return base64.b64decode(data.encode('ascii'))
