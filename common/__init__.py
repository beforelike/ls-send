"""
LS send 公共模块
"""

from .protocol import (
    UDP_DISCOVERY_REQUEST,
    UDP_DISCOVERY_RESPONSE,
    WS_INIT_SEND_REQUEST,
    WS_INIT_RESPONSE,
    WS_BLOCK传输,
    WS_PROGRESS_UPDATE,
    WS_TRANSFER_COMPLETE,
    WS_TRANSFER_FAILED,
    WS_HEARTBEAT
)

from .utils import (
    setup_logger,
    compute_file_checksum,
    encode_chunk,
    decode_chunk,
    calculate_progress,
    chunk_file,
    format_bytes
)

from .exceptions import (
    LSsendError,
    NetworkError,
    ProtocolError,
    FileError,
    TransferError
)

from .localization import Localization

from .udp_discovery import (
    UDPDiscoveryService,
    DiscoveredDevice
)

from .websocket_transfer import (
    WebSocketTransferService,
    WebSocketClient,
    TransferSession,
    TransferState,
    compute_file_checksum,
    decode_chunk
)

__all__ = [
    # Protocol
    'UDP_DISCOVERY_REQUEST',
    'UDP_DISCOVERY_RESPONSE',
    'WS_INIT_SEND_REQUEST',
    'WS_INIT_RESPONSE',
    'WS_BLOCK传输',
    'WS_PROGRESS_UPDATE',
    'WS_TRANSFER_COMPLETE',
    'WS_TRANSFER_FAILED',
    'WS_HEARTBEAT',
    
    # Utils
    'setup_logger',
    'compute_file_checksum',
    'encode_chunk',
    'decode_chunk',
    'calculate_progress',
    'chunk_file',
    'format_bytes',
    
    # Exceptions
    'LSsendError',
    'NetworkError',
    'ProtocolError',
    'FileError',
    'TransferError',
    
    # Localization
    'Localization',
    
    # UDP Discovery
    'UDPDiscoveryService',
    'DiscoveredDevice',
    
    # WebSocket Transfer
    'WebSocketTransferService',
    'WebSocketClient',
    'TransferSession',
    'TransferState',
]
