import argparse
import asyncio
import logging
import os
import sys
import time
from typing import List, Optional, Dict, Any
from pathlib import Path

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '../..')))

from dotenv import load_dotenv
from browser_use import Browser, Controller, Agent
from browser_use.browser.browser import BrowserConfig

# 从当前目录的browser_extension模块导入
from browser_extension.context_extension import extend_browser_context
from examples.element_enhance.ui_enhanced.ui_enhanced_actions import UIEnhancedActions

# 导入增强UI操作注册函数
from ui_enhanced.ui_enhanced_actions import register_enhanced_ui_actions, execute_ui_action, get_available_actions

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# UI测试相关类和辅助函数
class UITestStep:
    """UI测试步骤类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.start_time = 0
        self.end_time = 0
        self.success = False
        self.error_message = ""

    def start(self):
        """开始执行步骤"""
        logger.info(f"执行步骤: {self.name} - {self.description}")
        self.start_time = time.time()

    def complete(self, success: bool, error_message: str = ""):
        """完成步骤"""
        self.end_time = time.time()
        self.success = success
        self.error_message = error_message

        duration = self.end_time - self.start_time
        if success:
            logger.info(f"步骤 '{self.name}' 成功完成，耗时: {duration:.2f}秒")
        else:
            logger.error(f"步骤 '{self.name}' 失败，耗时: {duration:.2f}秒, 错误: {error_message}")

    @property
    def duration(self) -> float:
        """获取步骤执行时长"""
        if self.end_time > 0:
            return self.end_time - self.start_time
        return 0


class UITestReport:
    """UI测试报告类"""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.steps: List[UITestStep] = []
        self.start_time = 0
        self.end_time = 0
        self.total_standard_time: float = 0.0
        self.total_cache_time: float = 0.0

    def add_step(self, step: UITestStep):
        """添加测试步骤"""
        self.steps.append(step)

    def start_test(self):
        """开始测试"""
        logger.info(f"开始UI测试: {self.test_name}")
        self.start_time = time.time()

    def complete_test(self):
        """完成测试"""
        self.end_time = time.time()
        duration = self.end_time - self.start_time

        # 计算测试结果
        total_steps = len(self.steps)
        successful_steps = sum(1 for step in self.steps if step.success)

        logger.info(f"\n{'=' * 50}")
        logger.info(f"UI测试报告: {self.test_name}")
        logger.info(f"{'=' * 50}")
        logger.info(f"总耗时: {duration:.2f}秒")
        logger.info(f"步骤总数: {total_steps}")
        logger.info(f"成功步骤: {successful_steps}")
        logger.info(f"失败步骤: {total_steps - successful_steps}")

        if self.total_standard_time > 0 and self.total_cache_time > 0:
            improvement = (self.total_standard_time - self.total_cache_time) / self.total_standard_time * 100
            logger.info(f"\n性能比较:")
            logger.info(f"  标准操作总耗时: {self.total_standard_time:.4f}秒")
            logger.info(f"  缓存操作总耗时: {self.total_cache_time:.4f}秒")
            logger.info(f"  性能提升: {improvement:.2f}%")

        logger.info(f"\n步骤详情:")
        for i, step in enumerate(self.steps, 1):
            status = "✅ 成功" if step.success else "❌ 失败"
            logger.info(f"  {i}. {step.name}: {status} ({step.duration:.2f}秒)")
            if not step.success:
                logger.info(f"     错误: {step.error_message}")

        logger.info(f"{'=' * 50}")

        # 返回测试是否全部成功
        return successful_steps == total_steps


async def measure_performance(context, operation_func, args=(), use_cache=False):
    """测量操作性能"""
    start_time = time.time()
    result = await operation_func(*args)
    end_time = time.time()
    return result, end_time - start_time


# LLM集成部分
def get_llm(provider: str):
    """获取指定的LLM模型"""
    if provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Error: ANTHROPIC_API_KEY is not set. Please provide a valid API key.")

        return ChatAnthropic(
            model_name='claude-3-5-sonnet-20240620', timeout=25, stop=None, temperature=0.0
        )
    elif provider == 'openai':
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Error: OPENAI_API_KEY is not set. Please provide a valid API key.")

        return ChatOpenAI(model='gpt-4o', temperature=0.0)
    elif provider == 'deepseek':
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL")

        logger.info(f"DEEPSEEK_API_KEY: {api_key}")
        logger.info(f"DEEPSEEK_BASE_URL: {base_url}")
        if not api_key:
            raise ValueError("Error: DEEPSEEK_API_KEY is not set. Please provide a valid API key.")

        return ChatOpenAI(model='deepseek-chat', temperature=1, base_url=base_url, api_key=api_key)
    else:
        raise ValueError(f'Unsupported provider: {provider}')


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="使用LLM增强的UI自动化测试工具")
    parser.add_argument(
        '--task',
        type=str,
        help='要执行的测试任务描述',
        default='访问https://hy-sit.1233s2b.com,等待页面加载完成,输入用户名13600805241，输入密码Aa123456，点击登录按钮，登录成功等待页面加载完成后,点击辽阳市兴宇纸业有限公司-管理端，等待跳转的页面加载完成,验证页面包含文本首页'
    )
    parser.add_argument(
        '--provider',
        type=str,
        choices=['openai', 'anthropic', 'deepseek'],
        default='deepseek',
        help='要使用的LLM提供商 (默认: deepseek)',
    )
    parser.add_argument(
        '--use_cache',
        action='store_true',
        help='是否使用元素缓存来提高性能'
    )
    parser.add_argument(
        '--max_steps',
        type=int,
        default=10,
        help='最大执行步骤数'
    )
    parser.add_argument(
        '--cache_dir',
        type=str,
        default='ui_test_cache',
        help='缓存目录路径'
    )
    return parser.parse_args()


# 自定义Controller扩展类
class EnhancedController(Controller):
    """增强的控制器，包含更多UI操作方法"""

    def __init__(self):
        super().__init__()
        self._context = None
        self._enhanced_actions_registered = False

    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, value):
        self._context = value
        if not hasattr(value, 'get_controller'):
            def get_controller():
                return self

            value.get_controller = get_controller

    async def register_enhanced_actions(self):
        """注册所有增强的操作"""
        if self._enhanced_actions_registered:
            return

        # 使用UIEnhancedActions的注册方法
        await UIEnhancedActions.register_actions(self)
        self._enhanced_actions_registered = True


# 更新EnhancedUITestAgent类
class EnhancedUITestAgent:
    """增强的UI测试代理，结合LLM能力和增强的UI测试方法"""

    def __init__(self, task: str, llm_provider: str, use_cache: bool = True, cache_dir: str = "ui_test_cache"):
        self.task = task
        self.llm_provider = llm_provider
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        self.report = UITestReport(f"LLM驱动的UI测试: {task[:30]}...")

        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)

        # 初始化组件 - 使用增强的控制器
        self.llm = get_llm(llm_provider)
        self.controller = EnhancedController()  # 使用增强的控制器
        self.browser = Browser(config=BrowserConfig())

        # 注册增强的操作
        asyncio.create_task(self.controller.register_enhanced_actions())

        # 初始化代理
        self.agent = Agent(
            task=task,
            llm=self.llm,
            controller=self.controller,
            browser=self.browser,
            use_vision=True,
            max_actions_per_step=1,
        )

    async def setup(self):
        """设置浏览器上下文并添加增强功能"""
        try:
            # 创建浏览器上下文
            context = await self.browser.new_context()

            # 如果启用缓存，扩展上下文以支持元素缓存
            if self.use_cache:
                logger.info(f"启用元素缓存，缓存目录: {self.cache_dir}")
                context = extend_browser_context(context, cache_dir=self.cache_dir)

            # 将上下文添加到控制器
            self.controller.context = context

            # 创建新页面 - 修改这部分
            try:
                # 首先尝试获取当前页面
                self.page = await context.get_current_page()
                if not self.page:
                    # 如果没有当前页面，则从浏览器创建新页面
                    browser_instance = await self.browser.get_browser()
                    self.page = await browser_instance.new_page()
                    # 将新页面添加到上下文
                    await context.set_current_page(self.page)
            except Exception as e:
                logger.warning(f"页面创建过程中出错: {str(e)}")
                # 如果上述方法都失败，尝试直接从浏览器创建
                browser_instance = await self.browser.get_browser()
                self.page = await browser_instance.new_page()
                await context.set_current_page(self.page)

            if not self.page:
                raise ValueError("无法创建新页面")

            logger.info("浏览器设置完成")

        except Exception as e:
            logger.error(f"浏览器设置失败: {e}")
            raise

    async def run(self, max_steps: int = 25):
        """运行LLM驱动的UI测试"""
        self.report.start_test()

        try:
            # 设置浏览器和上下文
            await self.setup()

            # 运行代理执行任务
            logger.info(f"开始执行任务: {self.task}")

            # 添加任务描述前缀，帮助LLM理解可用的增强功能
            task_with_context = f"""
            你现在可以使用以下增强的操作方法来完成UI测试任务:
            
            1. click_element - 点击元素
            2. input_text - 输入文本
            3. go_to_url - 导航到URL
            
            这些操作提供了基本的UI交互能力。
            请使用这些功能来完成以下任务:
            
            {self.task}
            """

            # 更新代理的任务
            self.agent.task = task_with_context

            # 运行代理
            await self.agent.run(max_steps=max_steps)

            # 完成测试
            success = self.report.complete_test()
            return success

        except Exception as e:
            logger.error(f"执行测试时发生错误: {str(e)}")
            self.report.complete_test()
            return False

        finally:
            # 提示用户
            input("测试完成，按Enter键关闭浏览器...")
            # 关闭浏览器
            await self.browser.close()
            logger.info("测试浏览器已关闭")

    async def execute_step(self, step_name: str, step_description: str, step_func, *args, **kwargs):
        """执行测试步骤并记录结果"""
        step = UITestStep(step_name, step_description)
        step.start()

        try:
            result = await step_func(*args, **kwargs)
            step.complete(True)
            return result
        except Exception as e:
            step.complete(False, str(e))
            raise e  # 重新抛出异常以便上层处理
        finally:
            self.report.add_step(step)


class BrowserController:
    """Simple simulation of a browser controller for testing purposes."""
    
    def __init__(self):
        self.current_url = None
        self.page_content = {}
        self.page_history = []
        
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL."""
        logger.info(f"Navigating to: {url}")
        self.page_history.append(self.current_url) if self.current_url else None
        self.current_url = url
        
        # Simulate page loading
        await asyncio.sleep(1)
        
        # Store mock page content for various sites
        if "google.com" in url:
            self.page_content = {
                "title": "Google",
                "elements": [
                    {"role": "textbox", "name": "Search", "is_visible": True}
                ]
            }
        elif "github.com" in url:
            self.page_content = {
                "title": "GitHub: Let's build from here",
                "elements": [
                    {"role": "link", "name": "Sign in", "is_visible": True},
                    {"role": "textbox", "name": "Username", "is_visible": False}
                ]
            }
        else:
            self.page_content = {
                "title": "Unknown Page",
                "elements": []
            }
        
        return {
            "success": True,
            "url": url,
            "title": self.page_content["title"]
        }
    
    def get_current_url(self) -> str:
        """Get the current URL."""
        return self.current_url
    
    def get_page_content(self) -> Dict[str, Any]:
        """Get the current page content."""
        return self.page_content


class LLMUITester:
    """
    A class for testing enhanced UI actions using a simulated browser.
    
    This class provides an interface for LLM-based UI testing, allowing registration
    and execution of enhanced UI actions.
    """
    
    def __init__(self):
        self.browser = BrowserController()
        self.actions = []
        
    async def setup(self):
        """Set up the tester by registering enhanced UI actions."""
        self.actions = register_enhanced_ui_actions(self.browser)
        logger.info(f"Registered {len(self.actions)} enhanced UI actions")
        
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL."""
        return await self.browser.navigate(url)
    
    async def execute_action(self, action_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a registered UI action by name."""
        return await execute_ui_action(action_name, **kwargs)
    
    def get_available_actions(self) -> List[Dict[str, str]]:
        """Get information about all available enhanced UI actions."""
        return get_available_actions()
    
    def get_current_url(self) -> str:
        """Get the current URL."""
        return self.browser.get_current_url()
    
    def get_page_info(self) -> Dict[str, Any]:
        """Get information about the current page."""
        content = self.browser.get_page_content()
        return {
            "url": self.get_current_url(),
            "title": content.get("title", "Unknown"),
            "element_count": len(content.get("elements", [])),
            "visible_elements": [
                e for e in content.get("elements", []) 
                if e.get("is_visible", False)
            ]
        }


async def main():
    """主函数"""
    args = parse_arguments()

    # 创建并运行增强的UI测试代理
    agent = EnhancedUITestAgent(
        task=args.task,
        llm_provider=args.provider,
        use_cache=args.use_cache,
        cache_dir=args.cache_dir
    )

    success = await agent.run(max_steps=args.max_steps)

    # 退出码：0表示成功，1表示失败
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
