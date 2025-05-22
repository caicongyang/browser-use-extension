"""
增强型UI注册系统

这个包提供了用于注册增强型UI操作的功能。
"""

from .action_registry import (
    EnhancedUIRegistry,
    create_enhanced_ui_registry
)

__all__ = [
    'EnhancedUIRegistry',
    'create_enhanced_ui_registry'
] 