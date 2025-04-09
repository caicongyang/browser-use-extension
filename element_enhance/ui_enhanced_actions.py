"""
Enhanced UI Actions Registration System

This module provides a decorator-based system for registering enhanced UI actions
that can be used by LLM agents to interact with web interfaces more effectively.
"""
import logging
import asyncio
import functools
import inspect
from typing import Callable, Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Global registry for enhanced UI actions
_ENHANCED_UI_ACTIONS: Dict[str, Callable] = {}

def enhanced_ui_action(name: str, description: str):
    """
    Decorator to register an enhanced UI action.
    
    Args:
        name: Unique name of the action
        description: Description of what the action does, used by LLM to understand capabilities
    
    Returns:
        Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(f"Executing enhanced UI action: {name}")
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in enhanced UI action '{name}': {str(e)}")
                return {"success": False, "error": str(e)}
                
        # Add metadata to the function
        wrapper.action_name = name
        wrapper.description = description
        wrapper.signature = inspect.signature(func)
        
        # Register the action
        _ENHANCED_UI_ACTIONS[name] = wrapper
        logger.debug(f"Registered enhanced UI action: {name}")
        return wrapper
    
    return decorator

def register_enhanced_ui_actions(browser_controller):
    """
    Register all enhanced UI actions with a browser controller.
    
    Args:
        browser_controller: The browser controller to register actions with
    
    Returns:
        List of registered action names
    """
    # Register basic enhanced actions
    
    @enhanced_ui_action(
        name="resilient_click",
        description="Smart click that attempts multiple strategies to click an element, "
                   "including waiting for it to be visible and clickable, scrolling to it, "
                   "and using different locator strategies."
    )
    async def resilient_click(element_description: str, timeout: int = 10):
        """Resilient click implementation"""
        logger.info(f"Attempting resilient click on: {element_description}")
        try:
            # Simulate a successful click for this example
            await asyncio.sleep(1)  # Simulate waiting for element
            return {
                "success": True,
                "message": f"Successfully clicked on '{element_description}' using resilient strategy",
                "element_found": True,
                "attempts": 1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to click on '{element_description}'",
                "element_found": False
            }
    
    @enhanced_ui_action(
        name="element_diagnostic",
        description="Performs detailed diagnostics on a web element, checking visibility, "
                   "clickability, attributes, and providing comprehensive information to help "
                   "understand why interactions might be failing."
    )
    async def element_diagnostic(element_description: str):
        """Element diagnostic implementation"""
        logger.info(f"Running diagnostics on element: {element_description}")
        # Simulate diagnostics
        await asyncio.sleep(1.5)
        
        return {
            "success": True,
            "element_found": True,
            "is_visible": True,
            "is_clickable": True,
            "accessibility_info": {
                "role": "button",
                "name": element_description,
                "state": "enabled"
            },
            "computed_styles": {
                "position": "absolute",
                "z-index": "1",
                "visibility": "visible",
                "display": "block"
            },
            "recommendations": [
                "Element appears to be interactive and accessible",
                "Recommend using standard click operation"
            ]
        }
    
    @enhanced_ui_action(
        name="page_action",
        description="Performs page-level actions like scrolling, waiting, refreshing, " 
                   "taking screenshots, and other operations not tied to specific elements."
    )
    async def page_action(action_type: str, params: Optional[Dict[str, Any]] = None):
        """Page action implementation"""
        params = params or {}
        logger.info(f"Executing page action: {action_type} with params: {params}")
        
        supported_actions = {
            "scroll_to_bottom": "Scrolled to bottom of page",
            "scroll_to_top": "Scrolled to top of page",
            "wait": f"Waited for {params.get('seconds', 1)} seconds",
            "refresh": "Refreshed the page",
            "take_screenshot": "Took a screenshot"
        }
        
        if action_type not in supported_actions:
            return {
                "success": False,
                "error": f"Unsupported page action: {action_type}",
                "supported_actions": list(supported_actions.keys())
            }
        
        # Simulate action
        await asyncio.sleep(0.5)
        
        return {
            "success": True,
            "action_type": action_type,
            "message": supported_actions[action_type],
            "params_used": params
        }
    
    # Add browser_controller to each function if it expects it
    for name, func in list(_ENHANCED_UI_ACTIONS.items()):
        sig = inspect.signature(func)
        if "browser_controller" in sig.parameters:
            # Create a new function with browser_controller bound
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(browser_controller=browser_controller, *args, **kwargs)
            
            # Copy metadata from original function
            wrapper.action_name = func.action_name
            wrapper.description = func.description
            wrapper.signature = sig
            
            # Replace the original function in registry
            _ENHANCED_UI_ACTIONS[name] = wrapper
    
    logger.info(f"Registered {len(_ENHANCED_UI_ACTIONS)} enhanced UI actions")
    return list(_ENHANCED_UI_ACTIONS.keys())

def get_available_actions() -> List[Dict[str, str]]:
    """
    Get information about all available enhanced UI actions.
    
    Returns:
        List of dictionaries with action information
    """
    return [
        {
            "name": func.action_name,
            "description": func.description,
            "parameters": str(func.signature)
        }
        for func in _ENHANCED_UI_ACTIONS.values()
    ]

async def execute_ui_action(action_name: str, **kwargs) -> Dict[str, Any]:
    """
    Execute a registered UI action by name.
    
    Args:
        action_name: Name of the action to execute
        **kwargs: Arguments to pass to the action
    
    Returns:
        Result of the action execution
    """
    if action_name not in _ENHANCED_UI_ACTIONS:
        available_actions = list(_ENHANCED_UI_ACTIONS.keys())
        return {
            "success": False,
            "error": f"Unknown UI action: {action_name}",
            "available_actions": available_actions
        }
    
    action = _ENHANCED_UI_ACTIONS[action_name]
    try:
        return await action(**kwargs)
    except Exception as e:
        logger.exception(f"Error executing UI action '{action_name}'")
        return {
            "success": False,
            "error": str(e),
            "action": action_name
        } 