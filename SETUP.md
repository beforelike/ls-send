# LS Send - Setup and Installation Guide

Complete setup instructions for Windows and Android platforms.

## Quick Start

### Windows Setup

1. **Install Python 3.8+**
   - Download from https://www.python.org/downloads/
   - During installation, check "Add Python to PATH"

2. **Clone or Download LS Send**
   ```bash
   cd ls-send
   ```

3. **Create Virtual Environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the Application**
   ```bash
   python -m windows.main
   ```

6. **Firewall Configuration** (if prompted)
   - Allow Python through Windows Firewall for private networks
   - Or manually allow ports 53530 (UDP) and 53531 (TCP)

### Android Setup

#### Option 1: Build with Buildozer (Linux/macOS)

1. **Install Buildozer Dependencies** (Ubuntu/Debian)
   ```bash
   sudo apt-get update
   sudo apt-get install -y \
       git zip unzip openjdk-17-jdk \
       python3-pip autoconf libtool pkg-config \
       zlib1g-dev libncurses5-dev libncursesw5-dev \
       libtinfo5 cmake libffi-dev libssl-dev
   ```

2. **Install Buildozer**
   ```bash
   pip3 install buildozer
   ```

3. **Initialize Buildozer**
   ```bash
   cd ls-send
   buildozer init
   ```
   (This creates buildozer.spec, which is already provided)

4. **Build APK**
   ```bash
   buildozer -v android debug
   ```

5. **Find APK**
   - APK will be in `bin/` directory
   - Install on Android device via USB or transfer file

#### Option 2: Pre-built APK

Download pre-built APK from releases (when available).

#### Option 3: Python for Android (Termux)

1. **Install Termux** from F-Droid (not Play Store)

2. **Setup Termux**
   ```bash
   pkg update && pkg upgrade
   pkg install python clang
   pip install kivy
   ```

3. **Run LS Send**
   ```bash
   cd ls-send
   python android/main.py
   ```

## Network Configuration

### Firewall Rules

For proper LAN communication, ensure these ports are open:

**Windows Firewall:**
```powershell
# Allow UDP discovery port
New-NetFirewallRule -DisplayName "LS Send Discovery" -Direction Inbound -LocalPort 53530 -Protocol UDP -Action Allow

# Allow TCP transfer port
New-NetFirewallRule -DisplayName "LS Send Transfer" -Direction Inbound -LocalPort 53531 -Protocol TCP -Action Allow
```

**Linux (ufw):**
```bash
sudo ufw allow 53530/udp
sudo ufw allow 53531/tcp
```

### Network Requirements

- All devices must be on the same local network (same subnet)
- Router should allow UDP broadcast (usually enabled by default)
- Guest networks or AP isolation will prevent device discovery

## Usage Guide

### Sending Files

1. Launch LS Send on sender device
2. Wait for recipient devices to appear in the device list
3. Click "Add Files" and select files to send
4. Select target device from the list
5. Click "Send to Selected Device"
6. Monitor progress in the progress bar

### Receiving Files

1. Launch LS Send on recipient device
2. App runs in background (system tray on Windows, notification on Android)
3. When transfer request arrives, notification appears
4. Tap/click notification to view progress
5. Files are saved to:
   - **Windows:** `~/LS_Send_Received/`
   - **Android:** `/storage/emulated/0/LS_Send_Received/`

### Tips

- **Multiple Files:** Select multiple files before sending
- **Large Files:** Progress is shown in real-time
- **Network Changes:** If devices disappear, click "Refresh"
- **Background Mode:** On Windows, close button minimizes to tray

## Troubleshooting

### Devices Not Appearing

1. **Check Network:** Ensure both devices are on same WiFi network
2. **Firewall:** Verify firewall allows ports 53530/53531
3. **Refresh:** Click the refresh button
4. **Restart:** Restart both applications

### Transfer Fails

1. **Check Connection:** Verify target device is still visible
2. **Storage Space:** Ensure recipient has enough storage
3. **File Permissions:** Check file isn't locked by another app
4. **Network Stability:** Weak WiFi can cause timeouts

### Android-Specific Issues

1. **Permissions:** Grant storage permissions when prompted
2. **Battery Optimization:** Disable for LS Send to run in background
3. **Android 11+:** May need to grant "All files access" permission

### Windows-Specific Issues

1. **System Tray:** If icon doesn't appear, check hidden icons
2. **Firewall:** Windows may block on first run - allow access
3. **Antivirus:** Some AV software may block - add exception

## Development

### Running from Source

**Windows:**
```bash
python -m windows.main
```

**Android (testing):**
```bash
buildozer android debug deploy run
```

### Project Structure

```
ls-send/
├── shared/           # Common networking code
│   ├── __init__.py   # Protocol definitions
│   ├── discovery.py  # UDP device discovery
│   └── transfer.py   # HTTP file transfer
├── windows/          # Windows PySide6 UI
│   └── main.py
├── android/          # Android Kivy UI
│   └── main.py
├── assets/           # Icons and resources
├── requirements.txt
├── buildozer.spec
└── README.md
```

### Adding Features

1. **New Protocol Messages:** Edit `shared/__init__.py`
2. **Discovery Changes:** Modify `shared/discovery.py`
3. **Transfer Logic:** Update `shared/transfer.py`
4. **UI Changes:** Edit platform-specific `main.py`

## Security Notes

- **LAN Only:** App only works on local network (no internet)
- **No Encryption:** Transfers are unencrypted (trusted networks only)
- **Auto-Accept:** Currently accepts all transfers (can be modified)
- **Device ID:** Random ID generated per installation

## Performance Tips

- **Large Files:** Use wired Ethernet for faster transfers
- **Multiple Recipients:** Send sequentially (one-to-many in future)
- **Background:** App uses minimal resources when idle

## Support

For issues or feature requests, check the project repository or documentation.
