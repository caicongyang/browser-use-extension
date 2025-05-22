"""
Browser-Use 增强型UI操作系统

这个包为 Browser-Use 项目提供了增强型UI操作，使其能够更智能地与Web界面进行交互。
"""

__version__ = "0.1.0"

# 暴露核心功能
from .ui_registry.action_registry import EnhancedUIRegistry, create_enhanced_ui_registry
from .ui_enhanced.ui_enhanced_actions import EnhancedUIActionProvider

# 方便导入的便捷函数
def create_enhanced_controller(*args, **kwargs):
    """创建一个带有增强UI操作的控制器"""
    from .ui_registry.example_usage import create_enhanced_controller as _create
    return _create(*args, **kwargs) 