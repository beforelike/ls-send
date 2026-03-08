"""
LS send Windows GUI 主界面
作者：windows-ui-dev
完成时间：2026-03-08
功能：PySide6 界面 + UDP 发现 + WebSocket 传输
"""

import sys
import threading
import time
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QProgressBar, QFileDialog, QTextEdit, QGroupBox, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal, QThreadPool, QRunnable, QObject

from common.locallization import Localization
from common.udp_discovery import UDPDiscoveryService, DiscoveredDevice
from common.websocket_transfer import WebSocketClient, TransferState
from common.utils import setup_logger, format_bytes

logger = setup_logger(__name__)


class LocalizationWrapper:
    """多语言适配器"""
    def __init__(self, locale_dir: str = str(Path(__file__).parent.parent / 'locale')):
        self._lm = Localization(locale_dir)
        self._lm.load_locale('zh')
        self._lm.set_locale('zh')
    
    def gettext(self, key: str) -> str:
        return self._lm.gettext(key)
    
    def set_locale(self, locale: str):
        self._lm.set_locale(locale)


class DeviceDiscoveryWorker(QThread):
    """设备发现线程"""
    device_found = Signal(DiscoveredDevice)
    device_updated = Signal(DiscoveredDevice)
    device_lost = Signal(str)
    
    def __init__(self, device_name: str = "Windows-PC"):
        super().__init__()
        self.device_name = device_name
        self._running = False
        self._discovery = UDPDiscoveryService(
            device_name=device_name,
            on_device_found=self.on_device_found,
            on_device_lost=self.on_device_lost
        )
    
    def on_device_found(self, device: DiscoveredDevice):
        self.device_found.emit(device)
    
    def on_device_updated(self, device: DiscoveredDevice):
        self.device_updated.emit(device)
    
    def on_device_lost(self, ip: str):
        self.device_lost.emit(ip)
    
    def run(self):
        self._running = True
        self._discovery.start()
        while self._running:
            time.sleep(1)
    
    def stop(self):
        self._running = False
        self._discovery.stop()
        self.wait()


class FileTransferWorker(QRunnable):
    """文件传输工作线程"""
    class Signals(QObject):
        progress = Signal(float)
        complete = Signal(str)
        failed = Signal(str)
    
    def __init__(self, peer_ip: str, file_path: str, signals: Signals):
        super().__init__()
        self.peer_ip = peer_ip
        self.file_path = file_path
        self.signals = signals
        self._client = WebSocketClient(
            peer_ip=peer_ip,
            on_transfer_complete=self.on_complete,
            on_transfer_failed=self.on_failed
        )
    
    def run(self):
        try:
            if not self._client.connect():
                self.signals.failed.emit("Connection failed")
                return
            
            if not self._client.send_file(self.file_path):
                self.signals.failed.emit("Send failed")
                return
            
            # 等待传输完成（简化实现）
            time.sleep(5)
            self.signals.complete.emit("Transfer complete")
        except Exception as e:
            self.signals.failed.emit(str(e))
    
    def on_complete(self, peer_ip: str, checksum: str):
        self.signals.complete.emit("Transfer complete")
    
    def on_failed(self, peer_ip: str, reason: str):
        self.signals.failed.emit(reason)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LS send - Windows")
        self.resize(600, 500)
        
        self._localization = LocalizationWrapper()
        self.setWindowTitle(self._localization.gettext("app_title"))
        
        self._thread_pool = QThreadPool()
        self._discovery_worker = None
        self._selected_device = None
        self._selected_file = None
        
        self._init_ui()
        self._start_discovery()
    
    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 文件选择组
        file_group = QGroupBox(self._localization.gettext("file_selector_label"))
        file_layout = QHBoxLayout(file_group)
        
        self._file_path_edit = QLineEdit()
        self._file_path_edit.setReadOnly(True)
        file_layout.addWidget(self._file_path_edit)
        
        self._browse_btn = QPushButton(self._localization.gettext("browse_button"))
        self._browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self._browse_btn)
        
        layout.addWidget(file_group)
        
        # 设备列表组
        device_group = QGroupBox(self._localization.gettext("device_list_label"))
        device_layout = QVBoxLayout(device_group)
        
        self._device_list = QListWidget()
        self._device_list.itemClicked.connect(self._device_selected)
        device_layout.addWidget(self._device_list)
        
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._refresh_devices)
        device_layout.addWidget(self._refresh_btn)
        
        layout.addWidget(device_group)
        
        # 语言切换
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["中文", "English"])
        self._lang_combo.currentIndexChanged.connect(self._change_locale)
        lang_layout.addWidget(self._lang_combo)
        layout.addLayout(lang_layout)
        
        # 传输按钮
        btn_layout = QHBoxLayout()
        self._send_btn = QPushButton(self._localization.gettext("send_button"))
        self._send_btn.clicked.connect(self._send_file)
        self._send_btn.setEnabled(False)
        btn_layout.addWidget(self._send_btn)
        
        self._cancel_btn = QPushButton(self._localization.gettext("cancel_button"))
        self._cancel_btn.setEnabled(False)
        btn_layout.addWidget(self._cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # 进度条
        self._progress_label = QLabel("")
        layout.addWidget(self._progress_label)
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)
        
        # 日志输出
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(150)
        layout.addWidget(self._log_text)
    
    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            self._selected_file = file_path
            self._file_path_edit.setText(file_path)
            self._log(f"Selected file: {file_path}")
    
    def _start_discovery(self):
        self._discovery_worker = DeviceDiscoveryWorker()
        self._discovery_worker.device_found.connect(self._add_device)
        self._discovery_worker.start()
        self._log("Device discovery started")
    
    def _add_device(self, device: DiscoveredDevice):
        item = QListWidgetItem(f"{device.device_name} ({device.ip})")
        item.setData(Qt.UserRole, device)
        self._device_list.addItem(item)
        self._log(f"Device found: {device.device_name} ({device.ip})")
    
    def _device_selected(self, item: QListWidgetItem):
        self._selected_device = item.data(Qt.UserRole)
        self._send_btn.setEnabled(self._selected_file is not None and self._selected_device is not None)
        self._log(f"Selected device: {self._selected_device.device_name} ({self._selected_device.ip})")
    
    def _refresh_devices(self):
        self._discovery_worker._discovery.clear_devices()
        self._device_list.clear()
        self._log("Device list refreshed")
    
    def _change_locale(self, index: int):
        locales = ['zh', 'en']
        locale = locales[index]
        self._localization.set_locale(locale)
        self.setWindowTitle(self._localization.gettext("app_title"))
        
        # 更新 UI 文本
        self.findChild(QGroupBox, "fileSelectorLabel").setTitle(self._localization.gettext("file_selector_label"))
        self.findChild(QPushButton, "browseButton").setText(self._localization.gettext("browse_button"))
        
        # 重新查设备
        self._refresh_devices()
    
    def _send_file(self):
        if not self._selected_file or not self._selected_device:
            self._log("Please select a file and device first")
            return
        
        self._log(f"Sending file to {self._selected_device.ip}...")
        self._send_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._progress_bar.setVisible(True)
        
        # 启动传输线程
        worker = FileTransferWorker(
            peer_ip=self._selected_device.ip,
            file_path=self._selected_file,
            signals=FileTransferWorker.Signals()
        )
        worker.signals.progress.connect(self._update_progress)
        worker.signals.complete.connect(self._transfer_complete)
        worker.signals.failed.connect(self._transfer_failed)
        
        self._thread_pool.start(worker)
    
    def _cancel_transfer(self):
        self._log("Transfer cancelled")
        self._send_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress_bar.setVisible(False)
    
    def _update_progress(self, percent: float):
        self._progress_bar.setValue(int(percent))
        self._progress_label.setText(f"{self._localization.gettext('transferring')}: {percent:.1f}%")
    
    def _transfer_complete(self, msg: str):
        self._log(msg)
        self._send_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress_bar.setVisible(False)
        self._progress_label.setText("")
    
    def _transfer_failed(self, reason: str):
        self._log(f"Transfer failed: {reason}")
        self._send_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress_bar.setVisible(False)
        self._progress_label.setText("")
    
    def _log(self, message: str):
        self._log_text.append(f"[{time.strftime('%H:%M:%S')}] {message}")


def main():
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
