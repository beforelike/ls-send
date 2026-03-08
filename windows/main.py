"""
LS Send - Windows Implementation

PySide6 UI with system tray integration.
"""

import sys
import os
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QProgressBar,
    QFileDialog, QMessageBox, QSystemTrayIcon, QMenu, QAction,
    QGroupBox, QSplitter, QTextEdit, QFrame
)
from PySide6.QtCore import Qt, Signal, QObject, QThread, QTimer
from PySide6.QtGui import QIcon, QAction

from shared.discovery import DeviceDiscovery
from shared.transfer import TransferServer, FileSender
from shared import TRANSFER_PORT, DeviceInfo, TransferRequest, generate_device_id


class DiscoveryWorker(QThread):
    """Background thread for device discovery"""
    device_found = Signal(object)
    device_lost = Signal(str)
    
    def __init__(self, device_id, device_name, platform):
        super().__init__()
        self.discovery = DeviceDiscovery(device_id, device_name, platform)
    
    def run(self):
        self.discovery.set_callbacks(
            on_device_found=lambda d: self.device_found.emit(d),
            on_device_lost=lambda id: self.device_lost.emit(id)
        )
        self.discovery.start()
        
        # Keep running
        while True:
            self.msleep(1000)
    
    def stop(self):
        self.discovery.stop()
        self.terminate()
    
    def get_devices(self):
        return self.discovery.get_devices()
    
    def refresh(self):
        self.discovery.refresh()


class TransferWorker(QThread):
    """Background thread for file transfer"""
    progress = Signal(str, int, int)
    complete = Signal(bool, str)
    
    def __init__(self, files, target_ip, sender_id, sender_name):
        super().__init__()
        self.files = files
        self.target_ip = target_ip
        self.sender_id = sender_id
        self.sender_name = sender_name
        self.sender = None
    
    def run(self):
        try:
            self.sender = FileSender(self.target_ip, TRANSFER_PORT)
            self.sender.set_progress_callback(
                lambda name, sent, total: self.progress.emit(name, sent, total)
            )
            
            success, message = self.sender.send_files(
                self.files, self.sender_id, self.sender_name
            )
            self.complete.emit(success, message)
        
        except Exception as e:
            self.complete.emit(False, str(e))
    
    def cancel(self):
        if self.sender:
            self.sender.cancel()


class SystemTray:
    """System tray icon and menu"""
    
    def __init__(self, app, main_window):
        self.app = app
        self.main_window = main_window
        
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon.fromTheme("network-workgroup", QIcon.fromTheme("folder-network")))
        self.tray.setToolTip("LS Send - Running")
        
        # Create menu
        menu = QMenu()
        
        show_action = QAction("Show", menu)
        show_action.triggered.connect(self.main_window.show)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.app.quit)
        menu.addAction(quit_action)
        
        self.tray.setContextMenu(menu)
        
        # Double-click to show
        self.tray.activated.connect(self.on_activated)
        
        self.tray.show()
    
    def on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.main_window.show()
            self.main_window.activateWindow()
    
    def show_notification(self, title, message):
        self.tray.showMessage(title, message, QSystemTrayIcon.Information, 5000)


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, device_id, device_name):
        super().__init__()
        
        self.device_id = device_id
        self.device_name = device_name
        
        self.discovery_worker = None
        self.transfer_worker = None
        self.transfer_server = None
        
        self.selected_files = []
        
        self.init_ui()
        self.init_server()
        self.start_discovery()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("LS Send")
        self.setMinimumSize(800, 600)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        layout = QVBoxLayout(central)
        
        # Device list section
        device_group = QGroupBox("Devices on Network")
        device_layout = QVBoxLayout(device_group)
        
        self.device_list = QListWidget()
        self.device_list.itemClicked.connect(self.on_device_selected)
        device_layout.addWidget(self.device_list)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_devices)
        device_layout.addWidget(refresh_btn)
        
        layout.addWidget(device_group)
        
        # File selection section
        file_group = QGroupBox("Files to Send")
        file_layout = QVBoxLayout(file_group)
        
        self.file_list = QListWidget()
        file_layout.addWidget(self.file_list)
        
        file_btn_layout = QHBoxLayout()
        
        add_file_btn = QPushButton("📁 Add Files")
        add_file_btn.clicked.connect(self.add_files)
        file_btn_layout.addWidget(add_file_btn)
        
        remove_file_btn = QPushButton("🗑️ Remove Selected")
        remove_file_btn.clicked.connect(self.remove_selected_files)
        file_btn_layout.addWidget(remove_file_btn)
        
        file_btn_layout.addStretch()
        file_layout.addLayout(file_btn_layout)
        
        layout.addWidget(file_group)
        
        # Progress section
        progress_group = QGroupBox("Transfer Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_label = QLabel("Ready")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_detail = QTextEdit()
        self.progress_detail.setReadOnly(True)
        self.progress_detail.setMaximumHeight(100)
        progress_layout.addWidget(self.progress_detail)
        
        layout.addWidget(progress_group)
        
        # Send button
        self.send_btn = QPushButton("📤 Send to Selected Device")
        self.send_btn.clicked.connect(self.send_files)
        self.send_btn.setEnabled(False)
        layout.addWidget(self.send_btn)
        
        # Status bar
        self.statusBar().showMessage(f"Listening on port {TRANSFER_PORT}")
        
        # Selected device
        self.selected_device = None
    
    def init_server(self):
        """Initialize the transfer server"""
        self.transfer_server = TransferServer(
            device_id=self.device_id,
            save_dir=str(Path.home() / "LS_Send_Received")
        )
        
        self.transfer_server.set_callbacks(
            on_transfer_request=self.handle_transfer_request,
            on_progress=self.handle_transfer_progress,
            on_complete=self.handle_transfer_complete,
            on_cancel=self.handle_transfer_cancel
        )
        
        self.transfer_server.start()
    
    def start_discovery(self):
        """Start device discovery"""
        self.discovery_worker = DiscoveryWorker(
            self.device_id,
            self.device_name,
            "windows"
        )
        
        self.discovery_worker.device_found.connect(self.on_device_found)
        self.discovery_worker.device_lost.connect(self.on_device_lost)
        
        self.discovery_worker.start()
    
    def refresh_devices(self):
        """Refresh device list"""
        if self.discovery_worker:
            self.discovery_worker.refresh()
    
    def on_device_found(self, device: DeviceInfo):
        """Handle device discovered"""
        # Check if already in list
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.data(Qt.UserRole) == device.device_id:
                return
        
        # Add to list
        item_text = f"{device.device_name} ({device.ip})"
        if device.platform == "android":
            item_text += " 📱"
        else:
            item_text += " 💻"
        
        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, device)
        self.device_list.addItem(item)
        
        # Show notification
        if hasattr(self, 'system_tray'):
            self.system_tray.show_notification(
                "Device Discovered",
                f"{device.device_name} is on the network"
            )
    
    def on_device_lost(self, device_id: str):
        """Handle device lost"""
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.data(Qt.UserRole).device_id == device_id:
                self.device_list.takeItem(i)
                break
        
        # Clear selection if lost device was selected
        if self.selected_device and self.selected_device.device_id == device_id:
            self.selected_device = None
            self.send_btn.setEnabled(False)
    
    def on_device_selected(self, item: QListWidgetItem):
        """Handle device selection"""
        self.selected_device = item.data(Qt.UserRole)
        self.send_btn.setEnabled(len(self.selected_files) > 0)
    
    def add_files(self):
        """Add files to send list"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "", "All Files (*)"
        )
        
        for filepath in files:
            if filepath not in self.selected_files:
                self.selected_files.append(filepath)
                filename = os.path.basename(filepath)
                size = os.path.getsize(filepath)
                size_str = self.format_size(size)
                self.file_list.addItem(f"📄 {filename} ({size_str})")
        
        if self.selected_files and self.selected_device:
            self.send_btn.setEnabled(True)
    
    def remove_selected_files(self):
        """Remove selected files from list"""
        selected = self.file_list.selectedItems()
        for item in selected:
            row = self.file_list.row(item)
            if 0 <= row < len(self.selected_files):
                self.selected_files.pop(row)
                self.file_list.takeItem(row)
        
        if not self.selected_files:
            self.send_btn.setEnabled(False)
    
    def send_files(self):
        """Send selected files to selected device"""
        if not self.selected_files or not self.selected_device:
            return
        
        # Disable UI during transfer
        self.send_btn.setEnabled(False)
        self.progress_label.setText("Starting transfer...")
        self.progress_bar.setValue(0)
        self.progress_detail.clear()
        
        # Start transfer worker
        self.transfer_worker = TransferWorker(
            self.selected_files,
            self.selected_device.ip,
            self.device_id,
            self.device_name
        )
        
        self.transfer_worker.progress.connect(self.on_transfer_progress)
        self.transfer_worker.complete.connect(self.on_transfer_complete)
        
        self.transfer_worker.start()
    
    def on_transfer_progress(self, filename, sent, total):
        """Handle transfer progress"""
        percent = int((sent / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(percent)
        self.progress_label.setText(f"Sending {filename}: {self.format_size(sent)} / {self.format_size(total)}")
        
        self.progress_detail.append(f"✓ {filename}: {percent}%")
    
    def on_transfer_complete(self, success, message):
        """Handle transfer complete"""
        if success:
            self.progress_label.setText("Transfer complete!")
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Success", message)
        else:
            self.progress_label.setText("Transfer failed")
            QMessageBox.critical(self, "Error", message)
        
        self.send_btn.setEnabled(len(self.selected_files) > 0)
    
    def handle_transfer_request(self, request: TransferRequest) -> tuple:
        """Handle incoming transfer request"""
        # Show notification
        if hasattr(self, 'system_tray'):
            self.system_tray.show_notification(
                "File Transfer Request",
                f"{request.sender_name} wants to send {len(request.files)} file(s)"
            )
        
        # Auto-accept for now (could be made interactive)
        session_id = self.transfer_server.create_session(request)
        return True, session_id, "Accepted"
    
    def handle_transfer_progress(self, session_id, bytes_received, total_bytes, filename):
        """Handle incoming transfer progress"""
        percent = int((bytes_received / total_bytes) * 100) if total_bytes > 0 else 0
        self.progress_label.setText(f"Receiving {filename}: {self.format_size(bytes_received)} / {self.format_size(total_bytes)}")
        self.progress_bar.setValue(percent)
    
    def handle_transfer_complete(self, session_id):
        """Handle incoming transfer complete"""
        self.progress_label.setText("Received files complete!")
        self.progress_bar.setValue(100)
        
        if hasattr(self, 'system_tray'):
            self.system_tray.show_notification(
                "Transfer Complete",
                "Files received successfully"
            )
    
    def handle_transfer_cancel(self, session_id):
        """Handle transfer cancellation"""
        self.progress_label.setText("Transfer cancelled")
    
    def format_size(self, size: int) -> str:
        """Format file size for display"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def closeEvent(self, event):
        """Handle window close"""
        # Minimize to tray instead of closing
        event.ignore()
        self.hide()
        if hasattr(self, 'system_tray'):
            self.system_tray.show_notification(
                "LS Send",
                "Running in system tray"
            )


def main():
    """Main entry point"""
    # Generate device ID and name
    device_id = generate_device_id()
    device_name = f"Windows-{device_id}"
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("LS Send")
    app.setQuitOnLastWindowClosed(False)
    
    # Create main window
    window = MainWindow(device_id, device_name)
    window.show()
    
    # Create system tray
    tray = SystemTray(app, window)
    window.system_tray = tray
    
    # Run
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
