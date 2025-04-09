"""
UI Actions Registry System - UI动作注册系统

这个模块提供了一个基于装饰器的系统，用于注册增强型UI动作。
这些动作可以被LLM代理（AI模型）用来更有效地与Web界面进行交互。

主要功能：
1. 提供动作注册装饰器
2. 管理UI动作的全局注册表
3. 支持动作的异步执行
4. 提供错误处理和日志记录
"""
import logging
import asyncio
import functools
import inspect
from typing import Callable, Dict, Any, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# 全局注册表，用于存储所有已注册的增强型UI动作
# 键：动作名称
# 值：对应的处理函数
_ENHANCED_UI_ACTIONS: Dict[str, Callable] = {}

def enhanced_ui_action(name: str, description: str):
    """
    用于注册增强型UI动作的装饰器
    
    参数:
        name: 动作的唯一标识名称
        description: 动作的描述信息，用于帮助LLM理解该动作的功能和用途
    
    返回:
        装饰器函数
    
    使用示例:
        @enhanced_ui_action(
            name="click_button",
            description="点击指定的按钮元素"
        )
        async def click_button(element_id: str):
            # 实现点击逻辑
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(f"正在执行增强型UI动作: {name}")
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"执行增强型UI动作 '{name}' 时发生错误: {str(e)}")
                return {"success": False, "error": str(e)}
                
        # 为函数添加元数据，便于后续查询和管理
        wrapper.action_name = name
        wrapper.description = description
        wrapper.signature = inspect.signature(func)
        
        # 将动作注册到全局注册表
        _ENHANCED_UI_ACTIONS[name] = wrapper
        logger.debug(f"成功注册增强型UI动作: {name}")
        return wrapper
    
    return decorator

def register_enhanced_ui_actions(browser_controller):
    """
    注册所有基础的增强型UI动作到浏览器控制器
    
    参数:
        browser_controller: 浏览器控制器实例，用于执行具体的浏览器操作
    
    返回:
        已注册动作名称的列表
    """
    # 注册基础增强动作
    
    @enhanced_ui_action(
        name="resilient_click",
        description="智能点击功能，会尝试多种策略来点击元素，"
                   "包括等待元素可见和可点击、滚动到元素位置、"
                   "使用不同的定位策略等。"
    )
    async def resilient_click(element_description: str, timeout: int = 10):
        """智能点击的具体实现"""
        logger.info(f"尝试智能点击元素: {element_description}")
        try:
            # 模拟成功的点击操作
            await asyncio.sleep(1)  # 模拟等待元素
            return {
                "success": True,
                "message": f"成功使用智能策略点击元素 '{element_description}'",
                "element_found": True,
                "attempts": 1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"点击元素 '{element_description}' 失败",
                "element_found": False
            }
    
    @enhanced_ui_action(
        name="element_diagnostic",
        description="执行详细的Web元素诊断，检查元素的可见性、"
                   "可点击性、属性等，并提供全面的信息以帮助"
                   "理解交互失败的原因。"
    )
    async def element_diagnostic(element_description: str):
        """元素诊断的具体实现"""
        logger.info(f"正在对元素进行诊断: {element_description}")
        # 模拟诊断过程
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
                "元素看起来是可交互的且可访问",
                "建议使用标准点击操作"
            ]
        }
    
    @enhanced_ui_action(
        name="page_action",
        description="执行页面级别的操作，如滚动、等待、刷新、"
                   "截图等不依赖于特定元素的操作。"
    )
    async def page_action(action_type: str, params: Optional[Dict[str, Any]] = None):
        """页面动作的具体实现"""
        params = params or {}
        logger.info(f"执行页面动作: {action_type}，参数: {params}")
        
        supported_actions = {
            "scroll_to_bottom": "已滚动到页面底部",
            "scroll_to_top": "已滚动到页面顶部",
            "wait": f"已等待 {params.get('seconds', 1)} 秒",
            "refresh": "已刷新页面",
            "take_screenshot": "已完成截图"
        }
        
        if action_type not in supported_actions:
            return {
                "success": False,
                "error": f"不支持的页面动作: {action_type}",
                "supported_actions": list(supported_actions.keys())
            }
        
        # 模拟动作执行
        await asyncio.sleep(0.5)
        
        return {
            "success": True,
            "action_type": action_type,
            "message": supported_actions[action_type],
            "params_used": params
        }
    
    # 为需要browser_controller的函数添加browser_controller参数
    for name, func in list(_ENHANCED_UI_ACTIONS.items()):
        sig = inspect.signature(func)
        if "browser_controller" in sig.parameters:
            # 创建一个新的函数，将browser_controller绑定到函数中
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(browser_controller=browser_controller, *args, **kwargs)
            
            # 复制原函数的元数据
            wrapper.action_name = func.action_name
            wrapper.description = func.description
            wrapper.signature = sig
            
            # 用新函数替换注册表中的原函数
            _ENHANCED_UI_ACTIONS[name] = wrapper
    
    logger.info(f"共注册了 {len(_ENHANCED_UI_ACTIONS)} 个增强型UI动作")
    return list(_ENHANCED_UI_ACTIONS.keys())

def get_available_actions() -> List[Dict[str, str]]:
    """
    获取所有可用的增强型UI动作的信息
    
    返回:
        包含动作信息的字典列表，每个字典包含：
        - name: 动作名称
        - description: 动作描述
        - parameters: 参数签名
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
    通过名称执行已注册的UI动作
    
    参数:
        action_name: 要执行的动作名称
        **kwargs: 传递给动作的参数
    
    返回:
        动作执行的结果，包含：
        - success: 是否成功
        - error: 如果失败，错误信息
        - 其他动作特定的返回值
    """
    if action_name not in _ENHANCED_UI_ACTIONS:
        available_actions = list(_ENHANCED_UI_ACTIONS.keys())
        return {
            "success": False,
            "error": f"未知的UI动作: {action_name}",
            "available_actions": available_actions
        }
    
    action = _ENHANCED_UI_ACTIONS[action_name]
    try:
        return await action(**kwargs)
    except Exception as e:
        logger.exception(f"执行UI动作 '{action_name}' 时发生异常")
        return {
            "success": False,
            "error": str(e),
            "action": action_name
        } 