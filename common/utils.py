"""
LS send 工具函数
"""

import logging
import hashlib
import base64
from pathlib import Path

# ========== 日志配置 ==========

def setup_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    设置日志器，输出到控制台和文件
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 清除已有 handler（避免重复）
    if logger.handlers:
        logger.handlers.clear()
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    logger.addHandler(console_handler)
    
    return logger


# ========== 文件校验和 ==========

def compute_file_checksum(filepath: str | Path, block_size: int = 65536) -> str:
    """
    计算文件的 MD5 校验和
    """
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(block_size), b''):
            md5.update(chunk)
    return md5.hexdigest()


# ========== Base64 编码/解码 ==========

def encode_chunk(data: bytes) -> str:
    """Base64 编码二进制数据"""
    return base64.b64encode(data).decode('ascii')


def decode_chunk(data: str) -> bytes:
    """Base64 解码字符串为二进制"""
    return base64.b64decode(data.encode('ascii'))


# ========== 进度计算 ==========

def calculate_progress(transferred: int, total: int) -> float:
    """
    计算进度百分比（0-100）
    """
    if total == 0:
        return 100.0
    return round((transferred / total) * 100, 2)


# ========== 分块处理 ==========

def chunk_file(filepath: str | Path, chunk_size: int = 65536):
    """
    生成器：分块读取文件
    """
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


# ========== 大小格式化 ==========

def format_bytes(size: int) -> str:
    """
    格式化字节数为可读字符串（KB/MB/GB）
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"
