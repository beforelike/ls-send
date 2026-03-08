"""
LS Send - Protocol Definitions

Common protocol constants and message structures for cross-platform compatibility.
"""

import json
from dataclasses import dataclass, asdict
from typing import List, Optional
from enum import Enum

# Protocol Constants
DISCOVERY_PORT = 53530
TRANSFER_PORT = 53531
DISCOVERY_INTERVAL = 5.0  # seconds
DISCOVERY_TIMEOUT = 15.0  # seconds without response before considering device offline
BROADCAST_ADDRESS = "255.255.255.255"
MULTICAST_GROUP = "224.0.0.1"

# Message Types
class MessageType(Enum):
    DISCOVERY = "discovery"
    DISCOVERY_RESPONSE = "discovery_response"
    TRANSFER_REQUEST = "transfer_request"
    TRANSFER_RESPONSE = "transfer_response"
    TRANSFER_PROGRESS = "transfer_progress"
    TRANSFER_COMPLETE = "transfer_complete"
    TRANSFER_CANCEL = "transfer_cancel"


@dataclass
class FileInfo:
    """Information about a file to transfer"""
    name: str
    size: int
    hash: str  # MD5 hash for verification
    path: Optional[str] = None  # Local path (not transmitted)


@dataclass
class DeviceInfo:
    """Information about a discovered device"""
    device_id: str
    device_name: str
    platform: str  # "windows" or "android"
    ip: str
    port: int = TRANSFER_PORT
    last_seen: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DeviceInfo':
        return cls(**data)


@dataclass
class DiscoveryMessage:
    """UDP discovery broadcast message"""
    type: str = MessageType.DISCOVERY.value
    device_id: str = ""
    device_name: str = ""
    platform: str = ""
    port: int = TRANSFER_PORT
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DiscoveryMessage':
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class DiscoveryResponseMessage:
    """UDP discovery response message"""
    type: str = MessageType.DISCOVERY_RESPONSE.value
    device_id: str = ""
    device_name: str = ""
    platform: str = ""
    port: int = TRANSFER_PORT
    ip: str = ""
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DiscoveryResponseMessage':
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class TransferRequest:
    """HTTP transfer request"""
    type: str = MessageType.TRANSFER_REQUEST.value
    sender_id: str = ""
    sender_name: str = ""
    files: List[dict] = None  # List of FileInfo as dicts
    session_id: str = ""
    
    def __post_init__(self):
        if self.files is None:
            self.files = []
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TransferRequest':
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class TransferResponse:
    """HTTP transfer response"""
    type: str = MessageType.TRANSFER_RESPONSE.value
    accepted: bool = False
    session_id: str = ""
    message: str = ""
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TransferResponse':
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class ProgressMessage:
    """Progress update message"""
    type: str = MessageType.TRANSFER_PROGRESS.value
    session_id: str = ""
    file_name: str = ""
    bytes_sent: int = 0
    total_bytes: int = 0
    current_file: int = 0
    total_files: int = 0
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ProgressMessage':
        data = json.loads(json_str)
        return cls(**data)


def generate_device_id() -> str:
    """Generate a unique device ID"""
    import uuid
    return str(uuid.uuid4())[:8]


def calculate_file_hash(filepath: str) -> str:
    """Calculate MD5 hash of a file"""
    import hashlib
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
