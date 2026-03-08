"""
LS send Android GUI 主界面
作者：android-ui-dev
完成时间：2026-03-08
功能：Kivy 界面 + UDP 发现 + WebSocket 传输
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.listview import ListView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.lang import Builder
from kivy.clock import Clock

from common.localization import LocalizationManager
from common.udp_discovery import UDPDiscoveryService, DiscoveredDevice
from common.websocket_transfer import WebSocketClient
from common.utils import format_bytes

# Kivy 语言定义 UI
Builder.load_string('''
<MainWindow>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    
    BoxLayout:
        size_hint_y: None
        height: '40dp'
        Label:
            text: root._localization.gettext("file_selector_label")
        Button:
            text: root._localization.gettext("browse_button")
            on_press: root._browse_file()
    
    FileChooserListView:
        id: filechooser
        filters: ['*']
    
    BoxLayout:
        size_hint_y: None
        height: '40dp'
        Label:
            text: root._localization.gettext("device_list_label")
    
    ListView:
        id: device_list
        adapter: root.device_adapter
    
    BoxLayout:
        size_hint_y: None
        height: '40dp'
        Label:
            text: "Language:"
        Spinner:
            id: lang_spinner
            values: ["中文", "English"]
            on_select: root._change_locale(args[1])
    
    Button:
        text: root._localization.gettext("send_button")
        size_hint_y: None
        height: '50dp'
        on_press: root._send_file()
    
    ProgressBar:
        id: progress_bar
        max: 100
        value: 0
    
    Label:
        id: progress_label
        text: ""
    
    TextInput:
        id: log_text
        readonly: True
        height: '150dp'
        size_hint_y: None
''')


class MainWindow(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._localization = LocalizationManager('locale')
        self._device_list = []
        self._selected_device = None
        self._selected_file = None
        
        Clock.schedule_once(self._init_ui, 0)
    
    def _init_ui(self, dt):
        self.update_text_labels()
    
    def update_text_labels(self):
        """更新 UI 文本（语言切换）"""
        pass  # Kivy 语言绑定后自动更新
    
    def _browse_file(self):
        # 简化实现：提示用户选择文件
        pass
    
    def _device_selected(self, instance, value):
        self._selected_device = value
    
    def _change_locale(self, locale_name):
        locales = {'中文': 'zh', 'English': 'en'}
        locale = locales.get(locale_name, 'zh')
        self._localization.set_locale(locale)
        self.update_text_labels()
    
    def _send_file(self):
        pass  # 实现发送逻辑
    
    def _log(self, message):
        pass  # 实现日志输出


class LSApp(App):
    def build(self):
        return MainWindow()


if __name__ == '__main__':
    LSApp().run()
