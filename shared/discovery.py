"""
LS Send - Device Discovery Module

UDP broadcast/multicast based device discovery for LAN.
"""

import socket
import threading
import time
import json
from typing import Dict, Callable, Optional, List
from . import (
    DISCOVERY_PORT, DISCOVERY_INTERVAL, DISCOVERY_TIMEOUT,
    BROADCAST_ADDRESS, DeviceInfo, DiscoveryMessage, DiscoveryResponseMessage,
    generate_device_id
)


class DeviceDiscovery:
    """
    Handles LAN device discovery using UDP broadcast.
    
    Broadcasts discovery messages periodically and listens for responses.
    Maintains a list of discovered devices with automatic timeout.
    """
    
    def __init__(self, device_id: str = None, device_name: str = "", platform: str = ""):
        self.device_id = device_id or generate_device_id()
        self.device_name = device_name or f"Device-{self.device_id}"
        self.platform = platform
        
        self.devices: Dict[str, DeviceInfo] = {}
        self.devices_lock = threading.Lock()
        
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._broadcast_thread: Optional[threading.Thread] = None
        self._listen_thread: Optional[threading.Thread] = None
        
        self._on_device_found: Optional[Callable[[DeviceInfo], None]] = None
        self._on_device_lost: Optional[Callable[[str], None]] = None
    
    def set_callbacks(self, 
                     on_device_found: Callable[[DeviceInfo], None] = None,
                     on_device_lost: Callable[[str], None] = None):
        """Set callback functions for device events"""
        self._on_device_found = on_device_found
        self._on_device_lost = on_device_lost
    
    def start(self):
        """Start discovery service"""
        if self._running:
            return
        
        self._running = True
        
        # Create UDP socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to port for receiving
        try:
            self._socket.bind(('', DISCOVERY_PORT))
        except OSError as e:
            # Port might be in use, try with SO_REUSEPORT on Windows
            if hasattr(socket, 'SO_REUSEPORT'):
                self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                self._socket.bind(('', DISCOVERY_PORT))
        
        self._socket.settimeout(1.0)  # Timeout for recv
        
        # Start threads
        self._broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        
        self._broadcast_thread.start()
        self._listen_thread.start()
        
        # Send initial discovery
        self._send_discovery()
    
    def stop(self):
        """Stop discovery service"""
        self._running = False
        
        if self._socket:
            self._socket.close()
            self._socket = None
        
        if self._broadcast_thread:
            self._broadcast_thread.join(timeout=2.0)
        if self._listen_thread:
            self._listen_thread.join(timeout=2.0)
    
    def _send_discovery(self):
        """Broadcast discovery message"""
        if not self._socket or not self._running:
            return
        
        msg = DiscoveryMessage(
            device_id=self.device_id,
            device_name=self.device_name,
            platform=self.platform,
            port=DISCOVERY_PORT
        )
        
        try:
            data = msg.to_json().encode('utf-8')
            self._socket.sendto(data, (BROADCAST_ADDRESS, DISCOVERY_PORT))
        except Exception as e:
            print(f"Discovery broadcast error: {e}")
    
    def _broadcast_loop(self):
        """Periodically broadcast discovery messages"""
        while self._running:
            self._send_discovery()
            
            # Clean up old devices
            self._cleanup_devices()
            
            time.sleep(DISCOVERY_INTERVAL)
    
    def _listen_loop(self):
        """Listen for discovery messages and responses"""
        while self._running:
            try:
                data, addr = self._socket.recvfrom(4096)
                self._handle_message(data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    print(f"Discovery listen error: {e}")
                break
    
    def _handle_message(self, data: bytes, addr: tuple):
        """Handle incoming discovery message"""
        try:
            json_str = data.decode('utf-8')
            
            # Try parsing as discovery message
            if json_str.startswith('{"type": "discovery"'):
                msg = DiscoveryMessage.from_json(json_str)
                
                # Don't respond to our own messages
                if msg.device_id == self.device_id:
                    return
                
                # Send response
                self._send_discovery_response(addr[0])
                
                # Add/update device
                self._add_device(DeviceInfo(
                    device_id=msg.device_id,
                    device_name=msg.device_name,
                    platform=msg.platform,
                    ip=addr[0],
                    port=msg.port,
                    last_seen=time.time()
                ))
            
            # Try parsing as discovery response
            elif json_str.startswith('{"type": "discovery_response"'):
                msg = DiscoveryResponseMessage.from_json(json_str)
                
                # Don't add ourselves
                if msg.device_id == self.device_id:
                    return
                
                self._add_device(DeviceInfo(
                    device_id=msg.device_id,
                    device_name=msg.device_name,
                    platform=msg.platform,
                    ip=msg.ip or addr[0],
                    port=msg.port,
                    last_seen=time.time()
                ))
        
        except Exception as e:
            print(f"Error handling discovery message: {e}")
    
    def _send_discovery_response(self, target_ip: str):
        """Send discovery response to specific IP"""
        if not self._socket or not self._running:
            return
        
        msg = DiscoveryResponseMessage(
            device_id=self.device_id,
            device_name=self.device_name,
            platform=self.platform,
            port=DISCOVERY_PORT,
            ip=target_ip  # Will be replaced by receiver
        )
        
        try:
            data = msg.to_json().encode('utf-8')
            self._socket.sendto(data, (target_ip, DISCOVERY_PORT))
        except Exception as e:
            print(f"Discovery response error: {e}")
    
    def _add_device(self, device: DeviceInfo):
        """Add or update a discovered device"""
        with self.devices_lock:
            is_new = device.device_id not in self.devices
            self.devices[device.device_id] = device
        
        if is_new and self._on_device_found:
            self._on_device_found(device)
    
    def _cleanup_devices(self):
        """Remove devices that haven't been seen recently"""
        current_time = time.time()
        lost_devices = []
        
        with self.devices_lock:
            for device_id, device in list(self.devices.items()):
                if current_time - device.last_seen > DISCOVERY_TIMEOUT:
                    lost_devices.append(device_id)
                    del self.devices[device_id]
        
        for device_id in lost_devices:
            if self._on_device_lost:
                self._on_device_lost(device_id)
    
    def get_devices(self) -> List[DeviceInfo]:
        """Get list of currently discovered devices"""
        with self.devices_lock:
            return list(self.devices.values())
    
    def refresh(self):
        """Force immediate discovery broadcast"""
        self._send_discovery()
