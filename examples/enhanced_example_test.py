"""
增强UI操作系统的使用示例

本示例展示如何将增强UI操作系统集成到现有的Browser-use项目中。
有两种主要的集成方式：
1. 直接向现有Controller注册增强操作
2. 使用专用的EnhancedUIRegistry创建增强控制器

本示例包含可运行的代码，使用真实浏览器上下文来演示增强UI操作的工作方式。
"""
import asyncio
import logging
import os
import sys
from typing import Optional, Type, Dict, Any, Union
import inspect

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)  # browser-use-extension目录
sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.dirname(root_dir))  # 项目根目录

from browser_use.controller.service import Controller
from browser_use.browser.context import BrowserContext
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.agent.views import ActionResult
from pydantic import BaseModel, Field

# 使用正确的导入路径
from element_enhance.ui_registry.action_registry import EnhancedUIRegistry, create_enhanced_ui_registry
from element_enhance.ui_enhanced.ui_enhanced_actions import (
    EnhancedUIActionProvider, 
    ResilientClickParams,
    PageActionParams,
    InputTextParams,
    ElementDiagnosticParams
)

# 从browser extension导入扩展函数
from element_enhance.browser_extension.context_extension import extend_browser_context

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 检查Pydantic版本并创建兼容包装器
class ActionWrapper:
    """
    将字典包装为类似Pydantic模型的对象，兼容Controller使用
    """
    def __init__(self, data: Dict):
        self._data = data if data is not None else {}
    
    def model_dump(self, **kwargs):
        """兼容Pydantic V2的方法"""
        return self._data
    
    def dict(self, **kwargs):
        """兼容Pydantic V1的方法"""
        return self._data
    
    def __getattr__(self, name):
        """允许像访问属性一样访问字典值"""
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

def create_action_wrapper(params):
    """创建操作包装器"""
    # 如果是None，返回空包装器
    if params is None:
        return ActionWrapper({})
    
    # 如果已经是Pydantic模型，不需要包装
    if hasattr(params, 'model_dump') or hasattr(params, 'dict'):
        return params
    
    # 如果是字典，包装它
    if isinstance(params, dict):
        return ActionWrapper(params)
    
    # 其他情况，尝试转换为字典
    try:
        return ActionWrapper(dict(params))
    except (TypeError, ValueError):
        logger.warning(f"无法将类型 {type(params)} 转换为字典")
        return ActionWrapper({})

# 原始Controller.act方法
original_controller_act = Controller.act

async def patched_controller_act(self, action, browser_context):
    """
    对Controller.act方法的补丁，添加Pydantic兼容性
    """
    # 包装整个action参数
    wrapped_action = create_action_wrapper(action)
    
    # 调用原始方法
    return await original_controller_act(self, wrapped_action, browser_context)

# 应用猴子补丁
Controller.act = patched_controller_act

# 猴子补丁EnhancedUIRegistry的execute_action方法
if hasattr(EnhancedUIRegistry, 'execute_action'):
    original_registry_execute = EnhancedUIRegistry.execute_action
    
    async def patched_registry_execute(self, action_name, action_params, **kwargs):
        """对EnhancedUIRegistry.execute_action方法的补丁，添加Pydantic兼容性"""
        # 不使用ActionWrapper包装，直接使用字典
        if isinstance(action_params, ActionWrapper):
            # 如果是ActionWrapper，提取其中的字典数据
            if hasattr(action_params, 'model_dump'):
                wrapped_params = action_params.model_dump()
            elif hasattr(action_params, 'dict'):
                wrapped_params = action_params.dict()
            elif hasattr(action_params, '_data'):
                wrapped_params = action_params._data
            else:
                wrapped_params = action_params
        else:
            # 如果不是ActionWrapper，按原样传递
            wrapped_params = action_params
        
        return await original_registry_execute(self, action_name, wrapped_params, **kwargs)
    
    EnhancedUIRegistry.execute_action = patched_registry_execute

# 定义真实任务
REAL_TASK = '访问https://hy-sit.1233s2b.com,等待页面加载完成,输入用户名13600805241，输入密码Aa123456，点击登录按钮，登录成功等待页面加载完成后,点击辽阳市兴宇纸业有限公司-管理端，等待跳转的页面加载完成,验证页面包含文本首页'

# 定义模型转字典函数，简化代码
def to_dict(model):
    """将Pydantic模型转换为字典"""
    if model is None:
        return {}
    if isinstance(model, dict):
        return model
    if hasattr(model, "model_dump"):
        return model.model_dump()
    elif hasattr(model, "dict"):
        return model.dict()
    return model

# 示例1: 向现有Controller注册增强操作
async def example_with_existing_controller():
    """使用现有Controller注册增强操作执行真实任务的示例"""
    logger.info("示例1: 向现有Controller注册增强操作")
    
    # 创建标准控制器
    controller = Controller()
    
    # 注册增强UI操作
    EnhancedUIActionProvider.register_to_controller(controller)
    
    # 创建真实浏览器和上下文
    browser = Browser(config=BrowserConfig())
    browser_context = await browser.new_context()
    
    # 扩展浏览器上下文以支持缓存
    browser_context = extend_browser_context(browser_context, cache_dir="ui_cache")
    
    logger.info(f"执行任务: {REAL_TASK}")
    
    try:
        # 1. 访问网站
        logger.info("步骤1: 访问网站")
        goto_params = {"url": "https://hy-sit.1233s2b.com"}
        await controller.act({"go_to_url": goto_params}, browser_context)
        
        # 2. 等待页面加载
        logger.info("步骤2: 等待页面加载")
        wait_params = PageActionParams(
            action_type="wait",
            wait_time=5
        )
        await controller.act({"enhanced_page_action": to_dict(wait_params)}, browser_context)
        
        # 3. 输入用户名
        logger.info("步骤3: 输入用户名")
        username_params = InputTextParams(
            selector="input[placeholder='请输入用户名']", 
            text="13600805241",
            clear_first=True
        )
        await controller.act({"enhanced_input_text": to_dict(username_params)}, browser_context)
        
        # 4. 输入密码
        logger.info("步骤4: 输入密码")
        password_params = InputTextParams(
            selector="input[placeholder='请输入密码']",
            text="Aa123456",
            clear_first=True
        )
        await controller.act({"enhanced_input_text": to_dict(password_params)}, browser_context)
        
        # 5. 点击登录按钮
        logger.info("步骤5: 点击登录按钮")
        login_params = ResilientClickParams(
            text="登录",
            max_attempts=3,
            verify_navigation=True
        )
        await controller.act({"enhanced_resilient_click": to_dict(login_params)}, browser_context)
        
        # 6. 等待登录成功
        logger.info("步骤6: 等待登录成功")
        wait_login_params = PageActionParams(
            action_type="wait",
            wait_time=5
        )
        await controller.act({"enhanced_page_action": to_dict(wait_login_params)}, browser_context)
        
        # 7. 点击指定公司
        logger.info("步骤7: 点击辽阳市兴宇纸业有限公司-管理端")
        company_params = ResilientClickParams(
            text="辽阳市兴宇纸业有限公司-管理端",
            max_attempts=3,
            verify_navigation=True
        )
        await controller.act({"enhanced_resilient_click": to_dict(company_params)}, browser_context)
        
        # 8. 等待页面加载
        logger.info("步骤8: 等待页面加载")
        wait_page_params = PageActionParams(
            action_type="wait",
            wait_time=5
        )
        await controller.act({"enhanced_page_action": to_dict(wait_page_params)}, browser_context)
        
        # 9. 验证页面包含"首页"文本
        logger.info("步骤9: 验证页面包含'首页'文本")
        page = await browser_context.get_current_page()
        content = await page.content()
        if "首页" in content:
            logger.info("✅ 验证成功: 页面包含'首页'文本")
        else:
            logger.info("❌ 验证失败: 页面不包含'首页'文本")
            
        logger.info("任务执行成功")
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭浏览器
        await browser.close()
    
    logger.info("示例1完成")
    return controller

# 示例2: 使用EnhancedUIRegistry创建增强控制器
async def example_with_enhanced_registry():
    """使用EnhancedUIRegistry创建增强控制器执行真实任务的示例"""
    logger.info("示例2: 使用EnhancedUIRegistry创建增强控制器")
    
    # 创建增强UI注册表
    enhanced_registry = create_enhanced_ui_registry()
    
    # 注册自定义增强操作到增强UI注册表
    @enhanced_registry.register_enhanced_ui_action(
        name="custom_action",
        description="自定义增强操作示例"
    )
    async def custom_action(message: str = "默认消息", browser=None):
        """自定义增强操作示例"""
        logger.info(f"执行自定义操作: {message}")
        return ActionResult(
            success=True,
            extracted_content=f"自定义操作执行成功: {message}"
        )
    
    # 注册所有标准增强UI操作
    EnhancedUIActionProvider.register_to_registry(enhanced_registry)
    
    # 创建真实浏览器和上下文
    browser = Browser(config=BrowserConfig())
    browser_context = await browser.new_context()
    
    # 扩展浏览器上下文以支持缓存
    browser_context = extend_browser_context(browser_context, cache_dir="ui_cache")
    
    logger.info(f"执行任务: {REAL_TASK}")
    
    try:
        # 1. 访问网站
        logger.info("步骤1: 访问网站 (使用自定义操作)")
        result = await enhanced_registry.execute_action(
            "custom_action", 
            {"message": "访问https://hy-sit.1233s2b.com"}, 
            browser=browser_context
        )
        logger.info(f"结果: {result.extracted_content}")
        
        # 执行真正的访问操作
        goto_params = {"url": "https://hy-sit.1233s2b.com"}
        await enhanced_registry.execute_action(
            "go_to_url", 
            goto_params, 
            browser=browser_context
        )
        
        # 2. 等待页面加载
        logger.info("步骤2: 等待页面加载")
        wait_params = PageActionParams(
            action_type="wait",
            wait_time=5
        )
        await enhanced_registry.execute_action(
            "enhanced_page_action", 
            to_dict(wait_params), 
            browser=browser_context
        )
        
        # 3. 输入用户名
        logger.info("步骤3: 输入用户名")
        username_params = InputTextParams(
            selector="input[placeholder='请输入用户名']", 
            text="13600805241",
            clear_first=True
        )
        await enhanced_registry.execute_action(
            "enhanced_input_text", 
            to_dict(username_params), 
            browser=browser_context
        )
        
        # 4. 输入密码
        logger.info("步骤4: 输入密码")
        password_params = InputTextParams(
            selector="input[placeholder='请输入密码']",
            text="Aa123456",
            clear_first=True
        )
        await enhanced_registry.execute_action(
            "enhanced_input_text", 
            to_dict(password_params), 
            browser=browser_context
        )
        
        # 5. 点击登录按钮
        logger.info("步骤5: 点击登录按钮")
        login_params = ResilientClickParams(
            text="登录",
            max_attempts=3,
            verify_navigation=True
        )
        await enhanced_registry.execute_action(
            "enhanced_resilient_click", 
            to_dict(login_params), 
            browser=browser_context
        )
        
        # 6. 等待登录成功
        logger.info("步骤6: 等待登录成功")
        wait_login_params = PageActionParams(
            action_type="wait",
            wait_time=5
        )
        await enhanced_registry.execute_action(
            "enhanced_page_action", 
            to_dict(wait_login_params), 
            browser=browser_context
        )
        
        # 7. 点击指定公司
        logger.info("步骤7: 点击辽阳市兴宇纸业有限公司-管理端")
        company_params = ResilientClickParams(
            text="辽阳市兴宇纸业有限公司-管理端",
            max_attempts=3,
            verify_navigation=True
        )
        await enhanced_registry.execute_action(
            "enhanced_resilient_click", 
            to_dict(company_params), 
            browser=browser_context
        )
        
        # 8. 等待页面加载
        logger.info("步骤8: 等待页面加载")
        wait_page_params = PageActionParams(
            action_type="wait",
            wait_time=5
        )
        await enhanced_registry.execute_action(
            "enhanced_page_action", 
            to_dict(wait_page_params), 
            browser=browser_context
        )
        
        # 9. 验证页面包含"首页"文本
        logger.info("步骤9: 验证页面包含'首页'文本")
        page = await browser_context.get_current_page()
        content = await page.content()
        if "首页" in content:
            logger.info("✅ 验证成功: 页面包含'首页'文本")
        else:
            logger.info("❌ 验证失败: 页面不包含'首页'文本")
            
        logger.info("任务执行成功")
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭浏览器
        await browser.close()
    
    logger.info("示例2完成")
    return enhanced_registry

# 示例3: 最佳实践 - 使用工厂函数创建增强控制器
def create_enhanced_controller(exclude_actions: list[str] = []) -> Controller:
    """
    创建一个带有增强UI操作的控制器
    
    参数:
        exclude_actions: 要排除的操作列表
        
    返回:
        配置好的Controller实例
    """
    # 创建标准控制器
    controller = Controller(exclude_actions=exclude_actions)
    
    # 注册增强UI操作
    EnhancedUIActionProvider.register_to_controller(controller)
    
    return controller

# 示例4: 使用工厂函数创建的控制器执行真实任务
async def example_login_flow():
    """使用工厂函数创建的增强控制器执行真实任务的示例"""
    logger.info("示例4: 使用工厂函数创建的增强控制器")
    
    # 创建增强控制器
    controller = create_enhanced_controller()
    
    # 创建真实浏览器和上下文
    browser = Browser(config=BrowserConfig())
    browser_context = await browser.new_context()
    
    # 扩展浏览器上下文以支持缓存
    browser_context = extend_browser_context(browser_context, cache_dir="ui_cache")
    
    logger.info(f"执行任务: {REAL_TASK}")
    
    try:
        # 1. 访问网站
        logger.info("步骤1: 访问网站")
        goto_params = {"url": "https://hy-sit.1233s2b.com"}
        await controller.act({"go_to_url": goto_params}, browser_context)
        
        # 2. 等待页面加载
        logger.info("步骤2: 等待页面加载")
        wait_params = PageActionParams(
            action_type="wait",
            wait_time=5
        )
        await controller.act({"enhanced_page_action": to_dict(wait_params)}, browser_context)
        
        # 3. 输入用户名
        logger.info("步骤3: 输入用户名")
        username_params = InputTextParams(
            selector="input[placeholder='手机号码']", 
            text="13600805241",
            clear_first=True
        )
        await controller.act({"enhanced_input_text": to_dict(username_params)}, browser_context)
        
        # 4. 输入密码
        logger.info("步骤4: 输入密码")
        password_params = InputTextParams(
            selector="input[placeholder='请输入密码']",
            text="Aa123456",
            clear_first=True
        )
        await controller.act({"enhanced_input_text": to_dict(password_params)}, browser_context)
        
        # 5. 点击登录按钮
        logger.info("步骤5: 点击登录按钮")
        login_params = ResilientClickParams(
            text="登录",
            max_attempts=3,
            verify_navigation=True
        )
        await controller.act({"enhanced_resilient_click": to_dict(login_params)}, browser_context)
        
        # 6. 等待登录成功
        logger.info("步骤6: 等待登录成功")
        wait_login_params = PageActionParams(
            action_type="wait",
            wait_time=5
        )
        await controller.act({"enhanced_page_action": to_dict(wait_login_params)}, browser_context)
        
        # 7. 点击指定公司
        logger.info("步骤7: 点击辽阳市兴宇纸业有限公司-管理端")
        company_params = ResilientClickParams(
            text="辽阳市兴宇纸业有限公司-管理端",
            max_attempts=3,
            verify_navigation=True
        )
        await controller.act({"enhanced_resilient_click": to_dict(company_params)}, browser_context)
        
        # 8. 等待页面加载
        logger.info("步骤8: 等待页面加载")
        wait_page_params = PageActionParams(
            action_type="wait",
            wait_time=5
        )
        await controller.act({"enhanced_page_action": to_dict(wait_page_params)}, browser_context)
        
        # 9. 验证页面包含"首页"文本
        logger.info("步骤9: 验证页面包含'首页'文本")
        page = await browser_context.get_current_page()
        content = await page.content()
        if "首页" in content:
            logger.info("✅ 验证成功: 页面包含'首页'文本")
        else:
            logger.info("❌ 验证失败: 页面不包含'首页'文本")
        
        logger.info("任务执行成功")
    except Exception as e:
        logger.error(f"任务执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭浏览器
        await browser.close()
    
    logger.info("示例4完成")
    return controller

async def main():
    """运行所有示例"""
    logger.info("===== 启动增强UI操作系统示例 =====")
    
    # 使用硬编码变量选择要运行的示例
    # 可选值: 1, 2, 3 或 0（运行所有示例）
    example_to_run = 2  # 修改此值来运行不同的示例
    
    try:
        if example_to_run == 0:
            # 运行所有示例
            logger.info("运行所有示例")
            await example_with_existing_controller()
            await example_with_enhanced_registry()
            await example_login_flow()
        elif example_to_run == 1:
            await example_with_existing_controller()
        elif example_to_run == 2:
            await example_with_enhanced_registry()
        elif example_to_run == 3:
            await example_login_flow()
        
        logger.info("===== 增强UI操作系统示例完成 =====")
    except Exception as e:
        logger.error(f"示例运行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 