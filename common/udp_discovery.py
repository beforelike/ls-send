"""
LS send UDP 广播服务（设备自发现）

功能：
- 发送端：广播探测包，接收响应包，构建设备列表
- 接收端：监听广播，响应探测请求
- 设备列表管理：超时清理、持久化、设备更新
"""

import socket
import threading
import json
import time
import os
import pickle
from typing import Callable, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from .protocol import UDP_DISCOVERY_REQUEST, UDP_DISCOVERY_RESPONSE
from .utils import setup_logger

logger = setup_logger(__name__)


@dataclass
class DiscoveredDevice:
    """发现的设备信息"""
    ip: str
    device_name: str
    version: str
    supports_websocket: bool
    last_seen: float = 0.0
    first_seen: float = 0.0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "ip": self.ip,
            "device_name": self.device_name,
            "version": self.version,
            "supports_websocket": self.supports_websocket,
            "last_seen": self.last_seen,
            "first_seen": self.first_seen
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DiscoveredDevice':
        """从字典创建实例"""
        return cls(
            ip=data.get("ip", ""),
            device_name=data.get("device_name", "Unknown"),
            version=data.get("version", "1.0"),
            supports_websocket=data.get("supports_websocket", False),
            last_seen=data.get("last_seen", 0.0),
            first_seen=data.get("first_seen", 0.0)
        )


class UDPDiscoveryService:
    """UDP 广播自发现服务"""
    
    # 广播配置
    BROADCAST_IP = "255.255.255.255"
    BROADCAST_PORT = 50007
    DISCOVERY_INTERVAL = 3.0  # 秒
    DEVICE_TIMEOUT = 30.0  # 设备超时时间（秒）
    
    # 文件持久化配置
    DEVICE_CACHE_FILE = "/tmp/ls_send_devices.pkl"
    
    def __init__(
        self,
        device_name: str = "LS_SEND_DEVICE",
        on_device_found: Optional[Callable[[DiscoveredDevice], None]] = None,
        on_device_lost: Optional[Callable[[str], None]] = None,
        on_device_updated: Optional[Callable[[DiscoveredDevice], None]] = None,
        cache_dir: str = "/tmp"
    ):
        """
        初始化 UDP 发现服务
        
        Args:
            device_name: 设备名称（用于广播）
            on_device_found: 发现新设备时的回调
            on_device_lost: 设备离线时的回调
            on_device_updated: 设备信息更新时的回调
            cache_dir: 缓存目录
        """
        self.device_name = device_name
        self.on_device_found = on_device_found
        self.on_device_lost = on_device_lost
        self.on_device_updated = on_device_updated
        self.cache_dir = cache_dir
        self.DEVICE_CACHE_FILE = os.path.join(cache_dir, "ls_send_devices.pkl")
        
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._devices: dict[str, DiscoveredDevice] = {}
        self._sock_lock = threading.Lock()
        self._cleanup_lock = threading.Lock()
        
        # 探测线程
        self._broadcast_thread: Optional[threading.Thread] = None
        self._cleanup_thread: Optional[threading.Thread] = None
        self._listener_thread: Optional[threading.Thread] = None
        
        # 是否是接收端模式
        self._is_receiver = False
        
        # 加载缓存的设备列表
        self._load_devices()
        
        logger.info(f"UDPDiscoveryService initialized (device_name={device_name})")
    
    def start(self, is_receiver: bool = False):
        """
        启动服务
        
        Args:
            is_receiver: 是否作为接收端（只监听不广播）
        """
        if self._running:
            logger.warning("UDPDiscoveryService is already running")
            return
        
        self._running = True
        self._is_receiver = is_receiver
        self._create_socket()
        
        # 启动接收线程（接收端和发送端都需要接收）
        self._listener_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._listener_thread.start()
        
        # 如果不是接收端，启动广播线程
        if not is_receiver:
            self._broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
            self._broadcast_thread.start()
            
            # 启动设备清理线程
            self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self._cleanup_thread.start()
        
        logger.info(f"UDPDiscoveryService started (is_receiver={is_receiver})")
    
    def stop(self):
        """停止服务"""
        if not self._running:
            return
        
        self._running = False
        
        # 等待线程结束
        if self._broadcast_thread:
            self._broadcast_thread.join(timeout=2.0)
        
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=2.0)
        
        if self._listener_thread:
            self._listener_thread.join(timeout=2.0)
        
        if self._socket:
            try:
                self._socket.close()
            except Exception as e:
                logger.warning(f"Error closing socket: {e}")
            self._socket = None
        
        # 保存设备列表到缓存
        self._save_devices()
        
        logger.info("UDPDiscoveryService stopped")
    
    def _create_socket(self):
        """创建 UDP socket"""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.settimeout(1.0)  # 非阻塞超时
            
            # 接收端绑定到指定端口
            # 发送端也绑定端口以便接收响应
            self._socket.bind(("", self.BROADCAST_PORT))
            
            logger.info(f"UDP socket created and bound to port {self.BROADCAST_PORT}")
        except Exception as e:
            logger.error(f"Failed to create UDP socket: {e}")
            raise
    
    def _broadcast_loop(self):
        """广播探测包循环"""
        while self._running:
            self._send_discovery_request()
            time.sleep(self.DISCOVERY_INTERVAL)
    
    def _send_discovery_request(self):
        """发送探测包"""
        if not self._socket:
            logger.warning("Socket not initialized")
            return
        
        payload = {
            **UDP_DISCOVERY_REQUEST,
            "sender_name": self.device_name
        }
        
        try:
            self._socket.sendto(
                json.dumps(payload).encode('utf-8'),
                (self.BROADCAST_IP, self.BROADCAST_PORT)
            )
            logger.debug(f"Sent discovery request from {self.device_name}")
        except Exception as e:
            logger.error(f"Failed to send discovery request: {e}")
    
    def _receive_loop(self):
        """接收响应包循环"""
        while self._running:
            try:
                data, addr = self._socket.recvfrom(4096)
                self._handle_response(data, addr[0], addr[1])
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
    
    def _handle_response(self, data: bytes, ip: str, port: int):
        """处理响应包"""
        try:
            payload = json.loads(data.decode('utf-8'))
            
            msg_type = payload.get("type")
            
            # 处理广播请求（接收端响应）
            if msg_type == "DISCOVERY":
                self._handle_discovery_request(payload, ip, port)
                return
            
            # 处理响应包（发送端）
            if msg_type != "RESPONSE":
                return
            
            # 验证协议版本
            if payload.get("version") != "1.0":
                logger.warning(f"Unsupported protocol version: {payload.get('version')}")
                return
            
            device = DiscoveredDevice(
                ip=ip,
                device_name=payload.get("device_name", "Unknown"),
                version=payload.get("version", "1.0"),
                supports_websocket=payload.get("supports_websocket", False),
                last_seen=time.time(),
                first_seen=self._devices.get(ip, DiscoveredDevice(ip=ip, device_name="")).first_seen or time.time()
            )
            
            with self._sock_lock:
                # 设备已存在，更新信息
                if device.ip in self._devices:
                    old_device = self._devices[device.ip]
                    self._devices[device.ip] = device
                    
                    # 检查设备信息是否变化
                    if old_device.device_name != device.device_name:
                        logger.info(f"Device updated: {old_device.device_name} → {device.device_name} ({device.ip})")
                        if self.on_device_updated:
                            threading.Thread(target=self.on_device_updated, args=(device,), daemon=True).start()
                # 新设备
                else:
                    self._devices[device.ip] = device
                    logger.info(f"New device discovered: {device.device_name} ({device.ip})")
                    if self.on_device_found:
                        threading.Thread(
                            target=self.on_device_found,
                            args=(device,),
                            daemon=True
                        ).start()
            
            # 保存设备列表
            self._save_devices()
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid UDP packet: {e}")
        except Exception as e:
            logger.error(f"Error handling response: {e}")
    
    def _handle_discovery_request(self, payload: dict, ip: str, port: int):
        """处理广播请求（接收端响应）"""
        sender_name = payload.get("sender_name", "Unknown")
        
        logger.debug(f"Received discovery request from {sender_name} ({ip})")
        
        # 构建响应包
        response = {
            **UDP_DISCOVERY_RESPONSE,
            "device_name": self.device_name,
            "ip": ip,
            "supports_websocket": True
        }
        
        try:
            self._socket.sendto(
                json.dumps(response).encode('utf-8'),
                (ip, port)
            )
            logger.info(f"Sent response to {sender_name} ({ip})")
        except Exception as e:
            logger.error(f"Failed to send response to {ip}: {e}")
    
    def _cleanup_loop(self):
        """清理超时设备循环"""
        while self._running:
            time.sleep(self.DEVICE_TIMEOUT / 2)
            self._cleanup_timeout_devices()
    
    def _cleanup_timeout_devices(self):
        """清理超时设备"""
        current_time = time.time()
        devices_to_remove = []
        
        with self._sock_lock:
            for ip, device in self._devices.items():
                if current_time - device.last_seen > self.DEVICE_TIMEOUT:
                    devices_to_remove.append(ip)
            
            for ip in devices_to_remove:
                device = self._devices[ip]
                del self._devices[ip]
                logger.info(f"Device removed (timeout): {device.device_name} ({ip})")
                
                if self.on_device_lost:
                    threading.Thread(target=self.on_device_lost, args=(ip,), daemon=True).start()
        
        # 保存设备列表
        if devices_to_remove:
            self._save_devices()
    
    def _load_devices(self):
        """从缓存加载设备列表"""
        try:
            if os.path.exists(self.DEVICE_CACHE_FILE):
                with open(self.DEVICE_CACHE_FILE, 'rb') as f:
                    self._devices = pickle.load(f)
                logger.info(f"Loaded {len(self._devices)} devices from cache")
        except Exception as e:
            logger.error(f"Failed to load devices from cache: {e}")
            self._devices = {}
    
    def _save_devices(self):
        """保存设备列表到缓存"""
        try:
            with open(self.DEVICE_CACHE_FILE, 'wb') as f:
                pickle.dump(self._devices, f)
        except Exception as e:
            logger.error(f"Failed to save devices to cache: {e}")
    
    def get_devices(self, timeout_seconds: Optional[float] = None) -> list[DiscoveredDevice]:
        """
        获取已发现的设备列表
        
        Args:
            timeout_seconds: 只返回最近 timeout_seconds 秒内活跃的设备
        """
        with self._sock_lock:
            if timeout_seconds is None:
                return list(self._devices.values())
            
            current_time = time.time()
            return [
                device for device in self._devices.values()
                if current_time - device.last_seen <= timeout_seconds
            ]
    
    def get_device_by_ip(self, ip: str) -> Optional[DiscoveredDevice]:
        """通过 IP 获取设备"""
        with self._sock_lock:
            return self._devices.get(ip)
    
    def clear_devices(self):
        """清空设备列表"""
        with self._sock_lock:
            self._devices.clear()
            try:
                if os.path.exists(self.DEVICE_CACHE_FILE):
                    os.remove(self.DEVICE_CACHE_FILE)
            except Exception as e:
                logger.warning(f"Failed to clear device cache: {e}")
            logger.info("Device list cleared")
    
    def set_device_timeout(self, timeout_seconds: float):
        """设置设备超时时间"""
        self.DEVICE_TIMEOUT = timeout_seconds
        logger.info(f"Device timeout set to {timeout_seconds} seconds")
    
    def is_device_online(self, ip: str) -> bool:
        """检查设备是否在线"""
        device = self.get_device_by_ip(ip)
        if device is None:
            return False
        
        return time.time() - device.last_seen <= self.DEVICE_TIMEOUT
