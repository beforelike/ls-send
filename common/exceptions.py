"""
LS send 通用异常定义
"""

class LSsendError(Exception):
    """LS send 基础异常"""
    pass


class NetworkError(LSsendError):
    """网络相关异常"""
    pass


class ProtocolError(LSsendError):
    """协议解析异常"""
    pass


class FileError(LSsendError):
    """文件操作异常"""
    pass


class TransferError(LSsendError):
    """传输异常"""
    pass
