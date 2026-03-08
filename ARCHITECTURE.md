# LS Send - Architecture Documentation

## Overview

LS Send is a cross-platform LAN file transfer application built with Python. It uses a shared networking core with platform-specific UI implementations.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
├──────────────────────────┬──────────────────────────────────┤
│    Windows (PySide6)     │      Android (Kivy)              │
│  ┌────────────────────┐  │  ┌────────────────────┐          │
│  │  MainWindow        │  │  │  MainScreen        │          │
│  │  SystemTray        │  │  │  DeviceItem        │          │
│  │  DiscoveryWorker   │  │  │  Notification      │          │
│  └─────────┬──────────┘  │  └─────────┬──────────┘          │
└────────────┼─────────────┴────────────┼─────────────────────┘
             │                          │
             └──────────┬───────────────┘
                        │
             ┌──────────▼───────────┐
             │   Shared Core Layer   │
             ├───────────────────────┤
             │  DeviceDiscovery      │◄── UDP Broadcast (53530)
             │  TransferServer       │◄── HTTP Server (53531)
             │  FileSender           │──► HTTP Client
             │  Protocol Definitions │
             └───────────────────────┘
```

## Core Components

### 1. Protocol Layer (`shared/__init__.py`)

Defines the communication protocol:

- **Message Types:** Discovery, Transfer Request/Response, Progress, Complete
- **Data Classes:** DeviceInfo, FileInfo, TransferRequest, etc.
- **Constants:** Ports, timeouts, addresses
- **Utilities:** Device ID generation, file hashing

### 2. Discovery Module (`shared/discovery.py`)

**Purpose:** Find devices on the local network

**Implementation:**
- UDP broadcast on port 53530
- Broadcasts every 5 seconds
- Listens for responses from other devices
- Maintains device list with automatic timeout (15 seconds)

**Key Features:**
- Thread-safe device list
- Callbacks for device found/lost events
- Automatic cleanup of stale devices

**Message Format:**
```json
{
  "type": "discovery",
  "device_id": "abc123",
  "device_name": "My-Device",
  "platform": "windows",
  "port": 53531
}
```

### 3. Transfer Module (`shared/transfer.py`)

**Purpose:** Handle file transfers over HTTP

**Components:**

#### TransferServer
- HTTP server on port 53531
- Handles incoming transfer requests
- Manages transfer sessions
- Saves files to disk with progress tracking

#### FileSender
- HTTP client for sending files
- Multipart file upload
- Progress callbacks
- Transfer cancellation support

**Endpoints:**
- `POST /transfer` - Initiate transfer
- `POST /file/{session_id}` - Upload file
- `POST /cancel/{session_id}` - Cancel transfer
- `GET /progress/{session_id}` - Get progress

## Platform Implementations

### Windows (`windows/main.py`)

**UI Framework:** PySide6 (Qt for Python)

**Features:**
- Main window with device list, file selection, progress
- System tray integration (minimize to tray)
- Background threads for discovery and transfer
- Native notifications

**Key Classes:**
- `MainWindow` - Main application window
- `DiscoveryWorker` - Background discovery thread
- `TransferWorker` - Background transfer thread
- `SystemTray` - System tray icon and menu

### Android (`android/main.py`)

**UI Framework:** Kivy

**Features:**
- Touch-optimized interface
- Android notifications
- File picker integration
- Background execution support

**Key Classes:**
- `LSSendApp` - Main application
- `MainScreen` - Primary UI screen
- `DeviceItem` - Device list item widget

**Build System:** Buildozer (creates APK from Python code)

## Communication Flow

### Device Discovery

```
Device A                          Device B
    |                                 |
    |---[UDP Broadcast]------------->|
    |    "I'm Device A"              |
    |                                 |
    |<--[UDP Response]--------------|
    |    "I'm Device B @ 192.168.1.5" |
    |                                 |
    |---[UDP Broadcast]------------->|
    |    "I'm Device A"              |
    |                                 |
    |<--[UDP Response]--------------|
    |    "I'm Device B @ 192.168.1.5" |
```

### File Transfer

```
Sender                              Receiver
    |                                 |
    |---[POST /transfer]------------>|
    |    {files: [...]}              |
    |                                 |
    |<--[200 OK]--------------------|
    |    {session_id: "abc123"}      |
    |                                 |
    |---[POST /file/abc123]--------->|
    |    [file data]                 |
    |                                 |
    |<--[200 OK]--------------------|
    |    {success: true}             |
    |                                 |
    |    (repeat for each file)      |
```

## Threading Model

```
Main Thread (UI)
    │
    ├── DiscoveryWorker (background)
    │     └── UDP socket listener
    │
    └── TransferWorker (background, per transfer)
          └── HTTP client
          
TransferServer (background)
    └── HTTP server thread
```

**Thread Safety:**
- Device list protected by `threading.Lock`
- Session management protected by `threading.Lock`
- UI updates scheduled on main thread (Kivy Clock / Qt signals)

## Data Flow

### Sending Files

1. User selects files in UI
2. User selects target device
3. UI creates `TransferWorker` thread
4. `FileSender` sends transfer request
5. Receiver accepts, returns session ID
6. `FileSender` uploads each file
7. Progress callbacks update UI
8. Transfer complete

### Receiving Files

1. `TransferServer` receives POST /transfer
2. Callback notifies UI (shows notification)
3. Server creates session, returns ID
4. Client uploads files to POST /file/{id}
5. Progress callbacks update UI
6. Files saved to disk
7. Transfer complete notification

## Error Handling

### Network Errors
- Socket timeouts handled gracefully
- Device discovery auto-retries
- Transfer failures reported to UI

### File Errors
- Hash verification on receive
- Disk space checks
- Permission error handling

### UI Errors
- Thread-safe UI updates
- Graceful degradation
- User-friendly error messages

## Performance Considerations

### Large Files
- Chunked reading/writing (8KB chunks)
- Progress callbacks during transfer
- No full file in memory

### Multiple Devices
- Sequential transfers (one at a time)
- Device list cached with timeout
- Efficient UDP broadcast

### Memory
- Streaming file I/O
- Minimal caching
- Background threads cleaned up on exit

## Security Considerations

### Current Implementation
- LAN-only (no internet exposure)
- No encryption (trusted networks assumed)
- Auto-accept transfers (configurable)
- Device ID random per install

### Future Improvements
- Optional encryption (TLS)
- Transfer approval dialog
- Device pairing/whitelisting
- Transfer history/audit log

## Extension Points

### Adding New Message Types
1. Add to `MessageType` enum in `shared/__init__.py`
2. Create dataclass for message
3. Implement handler in `TransferHandler`
4. Add UI support in platform code

### Adding Platform Support
1. Create `platform_name/` directory
2. Implement UI using preferred framework
3. Import and use shared modules
4. Handle platform-specific features (notifications, etc.)

### Custom File Handlers
1. Extend `TransferHandler` class
2. Override specific methods
3. Pass to `TransferServer`

## Testing

### Unit Tests
- Protocol serialization
- File hash calculation
- Device info management

### Integration Tests
- Discovery between instances
- End-to-end file transfer
- Progress tracking

### Manual Testing
- Cross-platform transfers
- Large file handling
- Network interruption recovery

## Build and Deployment

### Windows
- Executable via PyInstaller (future)
- Currently runs from source
- Dependencies via pip

### Android
- APK via Buildozer
- Python bundled with app
- Native notification support

## Future Roadmap

1. **Encryption:** TLS for transfers
2. **Multi-recipient:** Send to multiple devices simultaneously
3. **Transfer History:** Log of sent/received files
4. **QR Pairing:** Easy device pairing
5. **Cloud Relay:** Internet transfer option
6. **Plugin System:** Custom file handlers
7. **Desktop Apps:** macOS and Linux support
