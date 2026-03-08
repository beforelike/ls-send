#!/usr/bin/env python3
"""
LS send Windows 构建脚本
作者：windows-ui-dev
完成时间：2026-03-08
功能：使用 PyInstaller 打包 Windows EXE
"""

import os
import subprocess
import sys
from pathlib import Path


def build_exe():
    """使用 PyInstaller 构建 EXE"""
    ls_dir = Path(__file__).parent.parent
    
    # 检查 PyInstaller 是否安装
    try:
        subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: PyInstaller 未安装，请运行 'pip install pyinstaller' 安装")
        return False
    
    # 准备构建参数
    windows_dir = ls_dir / 'windows'
    main_file = windows_dir / 'main.py'
    
    if not main_file.exists():
        print(f"错误: 主文件不存在 {main_file}")
        return False
    
    # 运行 PyInstaller 构建
    try:
        # 清理旧的构建文件
        build_dir = ls_dir / 'dist'
        if build_dir.exists():
            import shutil
            shutil.rmtree(build_dir)
        
        # 运行打包
        subprocess.run([
            "pyinstaller",
            "--onefile",
            "--windowed",  # 无控制台窗口
            "--name", "LS_send",
            "--add-data", f"{ls_dir}/locale;locale",
            "--add-data", f"{ls_dir}/common/common;common",
            "--hidden-import", "PySide6.QtWidgets",
            "--hidden-import", "PySide6.QtCore",
            "--hidden-import", "PySide6.QtGui",
            str(main_file)
        ], check=True)
        
        print(f"✓ EXE 构建成功！位置: {ls_dir / 'dist' / 'LS_send.exe'}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 构建失败: {e}")
        return False


if __name__ == '__main__':
    success = build_exe()
    sys.exit(0 if success else 1)
