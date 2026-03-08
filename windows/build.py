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
    ls_dir = Path(__file__).resolve().parent.parent
    
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
    
    # 构建资源文件路径（使用 Windows 风格分隔符）
    def normalize_path(p: Path) -> str:
        """将路径转换为 Windows 风格（分号分隔）"""
        return str(p).replace('\\', '/')
    
    # 运行 PyInstaller 构建
    try:
        # 清理旧的构建文件
        build_dir = ls_dir / 'dist'
        if build_dir.exists():
            import shutil
            shutil.rmtree(build_dir)
        
        # 确保 dist 和 build 目录存在
        dist_dir = ls_dir / 'dist'
        build_dir_inner = ls_dir / 'build'
        dist_dir.mkdir(exist_ok=True)
        build_dir_inner.mkdir(exist_ok=True)
        
        # 资源文件路径
        locale_src = normalize_path(ls_dir / 'locale')
        common_src = normalize_path(ls_dir / 'common')
        
        print(f"[INFO] 项目根目录: {normalize_path(ls_dir)}")
        print(f"[INFO] 主文件: {normalize_path(main_file)}")
        print(f"[INFO] locale 路径: {locale_src}")
        print(f"[INFO] common 路径: {common_src}")
        
        # 运行打包（使用双引号包装路径）
        cmd = [
            "pyinstaller",
            "--onefile",
            "--windowed",  # 无控制台窗口
            "--name", "LS_send",
            "--add-data", f"{locale_src};locale",
            "--add-data", f"{common_src};common",
            "--hidden-import", "PySide6.QtWidgets",
            "--hidden-import", "PySide6.QtCore",
            "--hidden-import", "PySide6.QtGui",
            "--clean",
            str(main_file)
        ]
        
        print(f"[INFO] 执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, cwd=str(ls_dir), check=True)
        
        exe_path = dist_dir / 'LS_send.exe'
        if exe_path.exists():
            print(f"[SUCCESS] EXE built at: {normalize_path(exe_path)}")
            return True
        else:
            print(f"[ERROR] EXE 文件未找到: {normalize_path(exe_path)}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Build failed with exit code {e.returncode}")
        print(f"[ERROR] Error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False


if __name__ == '__main__':
    success = build_exe()
    sys.exit(0 if success else 1)
