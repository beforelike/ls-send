#!/usr/bin/env python3
"""
LS send Android 构建脚本
作者：android-ui-dev
完成时间：2026-03-08
功能：使用 Buildozer 打包 Android APK
"""

import os
import subprocess
import sys
from pathlib import Path


def build_apk():
    """使用 Buildozer 构建 APK"""
    android_dir = Path(__file__).parent
    
    # 检查 Buildozer 是否安装
    try:
        subprocess.run(["buildozer", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: Buildozer 未安装，请运行 'pip install buildozer' 安装")
        return False
    
    # 检查 Android SDK/NDK
    sdk_path = os.environ.get('ANDROID_SDK_ROOT')
    ndk_path = os.environ.get('ANDROID_NDK_ROOT')
    
    if not sdk_path:
        print("警告: ANDROID_SDK_ROOT 未设置")
    
    if not ndk_path:
        print("警告: ANDROID_NDK_ROOT 未设置")
    
    # 运行 Buildozer 构建
    try:
        subprocess.run([
            "buildozer", "android", "debug", "deploy", "run"
        ], cwd=str(android_dir), check=True)
        print("✓ APK 构建成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 构建失败: {e}")
        return False


if __name__ == '__main__':
    success = build_apk()
    sys.exit(0 if success else 1)
