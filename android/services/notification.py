"""
LS send Android 通知服务
作者：android-ui-dev
完成时间：2026-03-08
功能：Service + Native Notification (plyer)
"""

from plyer import notification
from jnius import autoclass, PythonJavaClass, java_method


class NotificationManager:
    """Android 通知管理器"""
    
    def __init__(self):
        self.context = autoclass('org.kivy.android.PythonActivity').mActivity
        
    def show_notification(self, title: str, message: str):
        """
        显示原生通知栏弹窗
        """
        notification.notify(
            title=title,
            message=message,
            app_name='LS send',
            app_icon='',  # 空字符串使用默认图标
            timeout=10  # 通知持续时间（秒）
        )
    
    def show_file_transfer_notification(self, sender_ip: str, filename: str, filesize: int):
        """
        显示文件传输请求通知
        """
        title = "收到文件请求"
        message = f"来自 {sender_ip} 的 {filename} ({format_bytes(filesize)})"
        
        self.show_notification(title, message)


def format_bytes(size: int) -> str:
    """格式化字节数"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"
