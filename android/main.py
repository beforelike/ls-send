"""
LS Send - Android Implementation

Kivy UI with Android notification integration.
"""

import sys
import os
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.listview import ListView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivy.metrics import dp

from shared.discovery import DeviceDiscovery
from shared.transfer import TransferServer, FileSender
from shared import TRANSFER_PORT, DeviceInfo, generate_device_id


class DeviceItem(BoxLayout):
    """Widget for displaying a device in the list"""
    
    device_id = StringProperty('')
    device_name = StringProperty('')
    device_ip = StringProperty('')
    device_platform = StringProperty('')
    
    def __init__(self, device=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.padding = dp(10)
        self.spacing = dp(10)
        
        if device:
            self.device_id = device.device_id
            self.device_name = device.device_name
            self.device_ip = device.ip
            self.device_platform = device.platform
        
        # Icon based on platform
        icon = '📱' if self.device_platform == 'android' else '💻'
        
        self.add_widget(Label(
            text=f"{icon} {self.device_name}",
            halign='left',
            size_hint_x=0.6
        ))
        self.add_widget(Label(
            text=self.device_ip,
            halign='right',
            size_hint_x=0.4
        ))


class MainScreen(Screen):
    """Main screen with device list and file selection"""
    
    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app_instance = app_instance
        
        layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # Title
        title = Label(
            text='LS Send',
            size_hint_y=None,
            height=dp(50),
            font_size=dp(24)
        )
        layout.add_widget(title)
        
        # Device list section
        device_label = Label(
            text='Devices on Network',
            size_hint_y=None,
            height=dp(30),
            halign='left'
        )
        layout.add_widget(device_label)
        
        self.device_list = ListView()
        self.device_list.adapter = None
        layout.add_widget(self.device_list)
        
        # Buttons
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        
        refresh_btn = Button(text='🔄 Refresh')
        refresh_btn.bind(on_press=lambda x: self.app_instance.refresh_devices())
        btn_layout.add_widget(refresh_btn)
        
        layout.add_widget(btn_layout)
        
        # File section
        file_label = Label(
            text='Selected Files',
            size_hint_y=None,
            height=dp(30),
            halign='left'
        )
        layout.add_widget(file_label)
        
        self.file_list = ListView()
        self.file_list.adapter = None
        layout.add_widget(self.file_list)
        
        # File buttons
        file_btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        
        add_file_btn = Button(text='📁 Add Files')
        add_file_btn.bind(on_press=lambda x: self.app_instance.show_file_picker())
        file_btn_layout.add_widget(add_file_btn)
        
        layout.add_widget(file_btn_layout)
        
        # Send button
        self.send_btn = Button(
            text='📤 Send to Selected',
            size_hint_y=None,
            height=dp(50),
            disabled=True
        )
        self.send_btn.bind(on_press=lambda x: self.app_instance.send_files())
        layout.add_widget(self.send_btn)
        
        # Progress
        self.progress_label = Label(
            text='Ready',
            size_hint_y=None,
            height=dp(30)
        )
        layout.add_widget(self.progress_label)
        
        self.progress_bar = ProgressBar(max=100, size_hint_y=None, height=dp(30))
        layout.add_widget(self.progress_bar)
        
        self.add_widget(layout)
    
    def update_device_list(self, devices):
        """Update the device list display"""
        from kivy.adapters.listadapter import ListAdapter
        from kivy.uix.listitem import ListItemButton
        
        items = []
        for device in devices:
            icon = '📱' if device.platform == 'android' else '💻'
            items.append(f"{icon} {device.device_name} ({device.ip})")
        
        self.device_list.adapter = ListAdapter(
            data=items,
            cls=ListItemButton
        )
        
        # Store devices for selection
        self.app_instance.available_devices = devices
    
    def update_file_list(self, files):
        """Update the file list display"""
        from kivy.adapters.listadapter import ListAdapter
        from kivy.uix.listitem import ListItemButton
        
        items = [os.path.basename(f) for f in files]
        
        self.file_list.adapter = ListAdapter(
            data=items,
            cls=ListItemButton
        )
    
    def update_progress(self, label, value):
        """Update progress display"""
        self.progress_label.text = label
        self.progress_bar.value = value


class LSSendApp(App):
    """Main Android application"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.device_id = generate_device_id()
        self.device_name = f"Android-{self.device_id}"
        
        self.available_devices = []
        self.selected_files = []
        self.selected_device = None
        
        self.discovery = None
        self.transfer_server = None
        self.transfer_sender = None
    
    def build(self):
        """Build the UI"""
        self.icon = 'assets/icons/icon.png'
        self.title = 'LS Send'
        
        # Create screen manager
        sm = ScreenManager()
        
        # Create main screen
        self.main_screen = MainScreen(self)
        sm.add_widget(self.main_screen)
        
        # Start services
        Clock.schedule_once(self.start_services, 0.5)
        
        return sm
    
    def start_services(self, dt):
        """Start discovery and transfer services"""
        # Start discovery
        self.discovery = DeviceDiscovery(
            self.device_id,
            self.device_name,
            "android"
        )
        self.discovery.set_callbacks(
            on_device_found=self.on_device_found,
            on_device_lost=self.on_device_lost
        )
        self.discovery.start()
        
        # Start transfer server
        from android.storage import primary_external_storage_path
        save_dir = os.path.join(primary_external_storage_path(), 'LS_Send_Received')
        
        self.transfer_server = TransferServer(
            device_id=self.device_id,
            save_dir=save_dir
        )
        self.transfer_server.set_callbacks(
            on_transfer_request=self.handle_transfer_request,
            on_progress=self.handle_transfer_progress,
            on_complete=self.handle_transfer_complete,
            on_cancel=self.handle_transfer_cancel
        )
        self.transfer_server.start()
        
        # Initial refresh
        self.refresh_devices()
    
    def refresh_devices(self):
        """Refresh device list"""
        if self.discovery:
            self.discovery.refresh()
    
    def on_device_found(self, device: DeviceInfo):
        """Handle device discovered"""
        Clock.schedule_once(lambda dt: self.main_screen.update_device_list(
            self.discovery.get_devices()
        ))
        
        # Show notification
        self.show_notification(
            "Device Discovered",
            f"{device.device_name} is on the network"
        )
    
    def on_device_lost(self, device_id: str):
        """Handle device lost"""
        Clock.schedule_once(lambda dt: self.main_screen.update_device_list(
            self.discovery.get_devices()
        ))
    
    def show_file_picker(self):
        """Show file picker dialog"""
        from kivy.uix.popup import Popup
        from kivy.uix.filechooser import FileChooserListView
        
        content = BoxLayout(orientation='vertical')
        
        file_chooser = FileChooserListView(
            path=os.path.expanduser('~'),
            filters=['*']
        )
        content.add_widget(file_chooser)
        
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50))
        
        select_btn = Button(text='Select')
        cancel_btn = Button(text='Cancel')
        
        def select_files(instance):
            self.selected_files.extend(file_chooser.selection)
            self.main_screen.update_file_list(self.selected_files)
            if self.selected_files:
                self.main_screen.send_btn.disabled = False
            popup.dismiss()
        
        def cancel(instance):
            popup.dismiss()
        
        select_btn.bind(on_press=select_files)
        cancel_btn.bind(on_press=cancel)
        
        btn_layout.add_widget(select_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)
        
        popup = Popup(
            title='Select Files',
            content=content,
            size_hint=(0.9, 0.9)
        )
        popup.open()
    
    def send_files(self):
        """Send selected files"""
        if not self.selected_files or not self.available_devices:
            return
        
        # For simplicity, send to first device (could add device selection)
        target = self.available_devices[0]
        
        self.main_screen.send_btn.disabled = True
        self.main_screen.update_progress("Starting transfer...", 0)
        
        # Start transfer in background
        import threading
        
        def do_transfer():
            sender = FileSender(target.ip, TRANSFER_PORT)
            sender.set_progress_callback(self.on_transfer_progress)
            success, message = sender.send_files(
                self.selected_files,
                self.device_id,
                self.device_name
            )
            
            Clock.schedule_once(lambda dt: self.on_transfer_complete(success, message))
        
        threading.Thread(target=do_transfer, daemon=True).start()
    
    def on_transfer_progress(self, filename, sent, total):
        """Handle transfer progress"""
        percent = int((sent / total) * 100) if total > 0 else 0
        
        def update(label, value):
            self.main_screen.update_progress(
                f"Sending {filename}: {percent}%",
                value
            )
        
        Clock.schedule_once(lambda dt: update(filename, percent))
    
    def on_transfer_complete(self, success, message):
        """Handle transfer complete"""
        if success:
            self.main_screen.update_progress("Transfer complete!", 100)
            self.show_notification("Success", message)
        else:
            self.main_screen.update_progress("Transfer failed", 0)
            self.show_notification("Error", message)
        
        self.main_screen.send_btn.disabled = False
    
    def handle_transfer_request(self, request):
        """Handle incoming transfer request"""
        self.show_notification(
            "File Transfer Request",
            f"{request.sender_name} wants to send {len(request.files)} file(s)"
        )
        
        session_id = self.transfer_server.create_session(request)
        return True, session_id, "Accepted"
    
    def handle_transfer_progress(self, session_id, bytes_received, total_bytes, filename):
        """Handle incoming transfer progress"""
        percent = int((bytes_received / total_bytes) * 100) if total_bytes > 0 else 0
        
        def update(label, value):
            self.main_screen.update_progress(
                f"Receiving {filename}: {percent}%",
                value
            )
        
        Clock.schedule_once(lambda dt: update(filename, percent))
    
    def handle_transfer_complete(self, session_id):
        """Handle incoming transfer complete"""
        self.main_screen.update_progress("Received files complete!", 100)
        self.show_notification("Transfer Complete", "Files received successfully")
    
    def handle_transfer_cancel(self, session_id):
        """Handle transfer cancellation"""
        self.main_screen.update_progress("Transfer cancelled", 0)
    
    def show_notification(self, title, message):
        """Show Android notification"""
        try:
            from android import python_act
            from android.jnius import autoclass
            
            NotificationManager = autoclass('android.app.NotificationManager')
            NotificationCompat = autoclass('androidx.core.app.NotificationCompat')
            PendingIntent = autoclass('android.app.PendingIntent')
            Intent = autoclass('android.content.Intent')
            
            nm = python_act.getSystemService(python_act.NOTIFICATION_SERVICE)
            
            intent = Intent(python_act, python_act.getClass())
            pending_intent = PendingIntent.getActivity(
                python_act, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            )
            
            builder = NotificationCompat.Builder(python_act, 'ls_send_channel')
            builder.setContentTitle(title)
            builder.setContentText(message)
            builder.setSmallIcon(python_act.getApplicationInfo().icon)
            builder.setContentIntent(pending_intent)
            builder.setAutoCancel(True)
            
            nm.notify(1, builder.build())
        
        except Exception as e:
            print(f"Notification error: {e}")
    
    def on_pause(self):
        """Handle app pause (keep running in background)"""
        return True
    
    def on_stop(self):
        """Handle app stop"""
        if self.discovery:
            self.discovery.stop()
        if self.transfer_server:
            self.transfer_server.stop()


def main():
    """Main entry point"""
    LSSendApp().run()


if __name__ == "__main__":
    main()
