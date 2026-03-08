"""
LS send 多语言管理器

作者：LS send Team
完成时间：2026-03-08
"""

import json
from pathlib import Path
from typing import Optional


class Localization:
    """多语言管理器（简化版）"""
    
    def __init__(self, locale_dir: str | Path = "locale", locale: str = "zh"):
        self.locale_dir = Path(locale_dir)
        self._translations = {}
        self._current_locale = locale  # 默认中文
    
        # 加载语言文件
        self.load_locale(locale)
    
    def load_locale(self, locale: str = "zh") -> bool:
        """
        加载指定语言的翻译文件
        """
        locale_file = self.locale_dir / f"{locale}.json"
        if not locale_file.exists():
            # 尝试加载英文
            locale_file = self.locale_dir / "en.json"
            if not locale_file.exists():
                return False
        
        try:
            with open(locale_file, 'r', encoding='utf-8') as f:
                self._translations = json.load(f)
            
            # 获取对应语言的翻译
            locale_data = self._translations.get(locale, self._translations.get("zh", {}))
            self._current_locale = locale_data
            return True
        except (json.JSONDecodeError, IOError):
            return False
    
    def get(self, key: str) -> str:
        """
        获取翻译字符串
        """
        # 直接从当前语言中查找
        value = self._current_locale.get(key, key)
        return value if isinstance(value, str) else key
    
    # 便捷方法
    def __call__(self, key: str) -> str:
        """允许直接调用 get"""
        return self.get(key)
