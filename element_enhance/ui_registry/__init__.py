"""
UI Registry Module

This module provides tools for registering and executing enhanced UI actions.
"""

from .action_registry import (
    enhanced_ui_action, 
    register_enhanced_ui_actions, 
    execute_ui_action, 
    get_available_actions
)

__all__ = [
    'enhanced_ui_action',
    'register_enhanced_ui_actions',
    'execute_ui_action',
    'get_available_actions'
] 