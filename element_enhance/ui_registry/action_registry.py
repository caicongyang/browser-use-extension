"""
UI Actions Registry System - UI动作注册系统

这个模块提供了一个基于Registry的系统，用于注册增强型UI动作。
这些动作可以被LLM代理（AI模型）用来更有效地与Web界面进行交互。

主要功能：
1. 扩展了核心Registry类
2. 提供注册增强型UI动作的方法
3. 支持与Controller系统的集成
"""
import logging
from typing import Dict, Any, List, Optional, Type, TypeVar, Generic, Callable

from browser_use.controller.registry.service import Registry
from browser_use.agent.views import ActionResult
from pydantic import BaseModel
from browser_use.controller.views import (
    GoToUrlAction,
    ClickElementAction,
    InputTextAction,
    ScrollAction,
    SendKeysAction,
    NoParamsAction,
)

logger = logging.getLogger(__name__)

Context = TypeVar('Context')

class EnhancedUIRegistry(Generic[Context], Registry[Context]):
    """
    扩展核心Registry类，提供增强的UI操作注册功能
    """
    
    def __init__(self, exclude_actions: list[str] | None = None):
        """
        初始化增强UI注册表
        
        参数:
            exclude_actions: 要排除的动作列表
        """
        # 确保exclude_actions始终是列表而不是None
        super().__init__(exclude_actions if exclude_actions is not None else [])
        logger.info("增强UI注册表初始化完成")
        
    def register_enhanced_ui_action(self, name: str, description: str, param_model: Optional[Type[BaseModel]] = None):
        """
        注册增强型UI动作的装饰器
        
        参数:
            name: 动作的唯一标识名称
            description: 动作的描述信息
            param_model: 参数模型类
            
        返回:
            装饰器函数
        
        示例:
            @registry.register_enhanced_ui_action(
                name="resilient_click",
                description="智能点击功能"
            )
            async def resilient_click(element_description: str, timeout: int = 10, browser=None):
                # 实现点击逻辑
                pass
        """
        # 修改为直接装饰函数
        def decorator(func: Callable):
            # 保存原始函数名
            original_name = func.__name__
            
            # 修改函数名为指定的名称
            func.__name__ = name
            
            # 使用核心Registry的action装饰器（不带name参数）
            result = self.action(description, param_model=param_model)(func)
            
            # 恢复原始函数名，避免影响后续使用
            func.__name__ = original_name
            
            return result
            
        return decorator
        
    def register_basic_enhanced_actions(self, browser_controller=None):
        """
        注册基本的增强型UI动作
        
        参数:
            browser_controller: 浏览器控制器实例（可选）
        
        注意:
            此方法已被清空，不再预定义任何操作。
            您可以在此添加自己的自定义操作。
        """
        logger.info("基本增强UI动作注册（当前无预定义操作）")
        return list(self.registry.actions.keys())
        
    def get_available_actions(self) -> List[Dict[str, str]]:
        """
        获取所有可用的增强型UI动作的信息
        
        返回:
            包含动作信息的字典列表
        """
        return [
            {
                "name": name,
                "description": action.description,
                "parameters": str(action.param_model)
            }
            for name, action in self.registry.actions.items()
        ]
        
    def register_standard_actions(self):
        """注册标准的浏览器操作"""
        logger.info("注册标准浏览器操作")
        
        @self.action("导航到指定URL", GoToUrlAction)
        async def go_to_url(url: str, browser=None):
            """导航到指定URL"""
            if browser:
                page = await browser.get_current_page()
                await page.goto(url)
                return ActionResult(
                    success=True,
                    extracted_content=f"已导航到 {url}",
                    metadata={"url": url}
                )
            return ActionResult(success=False, error_message="未提供浏览器实例")
            
        @self.action("点击元素", ClickElementAction)
        async def click_element(index: int, browser=None):
            """点击元素"""
            if browser:
                page = await browser.get_current_page()
                dom_state = await browser.get_state()
                element = dom_state.selector_map.get(index)
                if element and hasattr(element, 'selector'):
                    await page.click(element.selector)
                    return ActionResult(
                        success=True,
                        extracted_content=f"已点击元素 {index}",
                        metadata={"element_index": index}
                    )
                return ActionResult(success=False, error_message=f"未找到元素 {index}")
            return ActionResult(success=False, error_message="未提供浏览器实例")
            
        @self.action("通过CSS选择器点击元素", param_model=None)
        async def click_by_selector(selector: str, browser=None):
            """通过CSS选择器点击元素"""
            if browser:
                page = await browser.get_current_page()
                try:
                    await page.click(selector)
                    return ActionResult(
                        success=True,
                        extracted_content=f"已通过选择器 {selector} 点击元素",
                        metadata={"selector": selector}
                    )
                except Exception as e:
                    return ActionResult(success=False, error_message=f"点击失败: {str(e)}")
            return ActionResult(success=False, error_message="未提供浏览器实例")
            
        @self.action("输入文本", InputTextAction)
        async def input_text(index: int, text: str, browser=None):
            """输入文本"""
            if browser:
                page = await browser.get_current_page()
                dom_state = await browser.get_state()
                element = dom_state.selector_map.get(index)
                if element and hasattr(element, 'selector'):
                    await page.fill(element.selector, text)
                    return ActionResult(
                        success=True,
                        extracted_content=f"已输入文本: {text}",
                        metadata={"element_index": index, "text": text}
                    )
                return ActionResult(success=False, error_message=f"未找到元素 {index}")
            return ActionResult(success=False, error_message="未提供浏览器实例")
            
        return ["go_to_url", "click_element", "click_by_selector", "input_text"]

# 创建增强型UI注册表的工厂函数
def create_enhanced_ui_registry(exclude_actions: list[str] | None = None) -> EnhancedUIRegistry:
    """
    创建并返回一个增强型UI注册表实例
    
    参数:
        exclude_actions: 要排除的动作列表
        
    返回:
        配置好的EnhancedUIRegistry实例
    """
    # 确保exclude_actions始终是列表而不是None
    registry = EnhancedUIRegistry(exclude_actions if exclude_actions is not None else [])
    
    # 注册标准浏览器操作
    registry.register_standard_actions()
    
    return registry 