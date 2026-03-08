# LS Send - Quick Start Guide

Get up and running in 5 minutes!

## Windows (3 minutes)

```bash
# 1. Navigate to ls-send folder
cd ls-send

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install PySide6 pystray Pillow

# 4. Run!
python -m windows.main
```

That's it! The app will:
- Start automatically discovering devices on your network
- Listen for incoming file transfers
- Show an icon in your system tray

## Android (using pre-built or build yourself)

### Option A: Quick Test with Termux
```bash
# Install Termux from F-Droid
pkg install python
pip install kivy
cd ls-send
python android/main.py
```

### Option B: Build APK (requires Linux/macOS)
```bash
pip install buildozer
cd ls-send
buildozer -v android debug
# APK in bin/ folder
```

## Test It Out

1. **Open on two devices** (or two Windows instances)
2. **Wait for discovery** (devices appear in list automatically)
3. **Select files** to send
4. **Choose device** from the list
5. **Click Send!**

## Default Ports

- **Discovery:** UDP 53530
- **Transfer:** TCP 53531

If you get firewall prompts, allow access for private networks.

## Received Files Location

- **Windows:** `C:\Users\You\LS_Send_Received\`
- **Android:** `/storage/emulated/0/LS_Send_Received/`

## Troubleshooting

**Devices not showing up?**
- Make sure both on same WiFi
- Click "Refresh" button
- Check firewall settings

**Transfer fails?**
- Verify device still in list
- Check available storage space
- Try smaller file first

## Next Steps

- Read `README.md` for full documentation
- Check `SETUP.md` for detailed installation
- See `ARCHITECTURE.md` for how it works

Enjoy! 🚀
