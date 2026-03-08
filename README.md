# LS Send - LAN File Transfer

Cross-platform LAN file transfer application for Windows and Android.

## Features

- **LAN Device Discovery**: Automatically find all devices running LS Send on the same network
- **One-to-Many File Sending**: Select files and send to multiple devices simultaneously
- **Receive Notifications**: System tray (Windows) or notification bar (Android) alerts for incoming transfers
- **Real-time Progress**: Live progress display for both sender and receiver

## Technical Overview

- **Device Discovery**: UDP broadcast/multicast on port 53530
- **File Transfer**: HTTP server on port 53531
- **Protocol**: Custom JSON-based protocol over UDP/TCP

## Project Structure

```
ls-send/
├── shared/              # Common code (discovery, transfer, protocol)
├── windows/             # Windows-specific (PySide6 UI)
├── android/             # Android-specific (Kivy UI)
├── assets/              # Icons and resources
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Installation

### Windows

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m windows.main
```

### Android (using Buildozer)

```bash
# Install buildozer
pip install buildozer

# Initialize buildozer
buildozer init

# Edit buildozer.spec (requirements already configured)

# Build APK
buildozer -v android debug

# APK will be in bin/ directory
```

## Usage

### Sending Files

1. Launch LS Send on your device
2. The app will automatically discover other devices on the network
3. Select files you want to send
4. Choose one or more recipient devices
5. Click "Send" and monitor progress

### Receiving Files

1. Launch LS Send (runs in background)
2. When a transfer request arrives, you'll receive a notification
3. Click the notification to accept/reject
4. Monitor download progress

## Protocol Specification

### Device Discovery (UDP Broadcast)

**Discovery Request** (broadcast every 5 seconds):
```json
{
  "type": "discovery",
  "device_id": "unique-device-id",
  "device_name": "Human-readable name",
  "platform": "windows|android",
  "port": 53531
}
```

**Discovery Response** (unicast back to sender):
```json
{
  "type": "discovery_response",
  "device_id": "unique-device-id",
  "device_name": "Human-readable name",
  "platform": "windows|android",
  "port": 53531,
  "ip": "192.168.1.100"
}
```

### File Transfer (HTTP)

**Transfer Request** (POST /transfer):
```json
{
  "type": "transfer_request",
  "sender_id": "device-id",
  "files": [
    {"name": "file.txt", "size": 1024, "hash": "md5hash"},
    {"name": "image.jpg", "size": 2048, "hash": "md5hash"}
  ]
}
```

**Transfer Response**:
```json
{
  "type": "transfer_response",
  "accepted": true,
  "session_id": "unique-session-id"
}
```

**File Upload** (POST /file/{session_id}):
- Multipart form data with file content

## Configuration

### Ports

- Discovery (UDP): 53530
- Transfer (HTTP): 53531

### Firewall

Ensure these ports are allowed through your firewall for LAN communication.

## License

MIT License
