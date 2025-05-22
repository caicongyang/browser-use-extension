import argparse
import asyncio
import logging
import os
import sys
import time
import traceback
from typing import List, Optional, Dict, Any
from pathlib import Path

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
# 添加项目根目录到Python路径
parent_dir = os.path.dirname(current_dir)  # browser-use-extension目录
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '../..')))

from dotenv import load_dotenv
from browser_use import Browser, Controller, Agent
from browser_use.browser.browser import BrowserConfig
from browser_use.agent.views import ActionResult

# 从element_enhance包中导入
from element_enhance.browser_extension.context_extension import extend_browser_context


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


# 将任务解析为步骤
def parse_task(task: str) -> List[str]:
    """将任务字符串分解为步骤列表"""
    steps = []
    
    # 分解任务描述
    if ',' in task or '，' in task or ';' in task or '；' in task:
        # 替换中文标点为英文标点
        task = task.replace('，', ',').replace('；', ';')
        # 按逗号或分号分割
        parts = task.replace(';', ',').split(',')
        steps = [p.strip() for p in parts if p.strip()]
    else:
        # 如果没有明确的分隔符，整体作为一个步骤
        steps = [task]
    
    logger.info(f"任务已分解为 {len(steps)} 个步骤")
    for i, step in enumerate(steps, 1):
        logger.info(f"  步骤{i}: {step}")
        
    return steps


# LLM集成部分
def get_llm(provider: str):
    """获取指定的LLM模型"""
    if provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Error: ANTHROPIC_API_KEY is not set. Please provide a valid API key.")

        return ChatAnthropic(
            model_name='claude-3-5-sonnet-20240620', 
            timeout=25, 
            stop=None, 
            temperature=0.0,
            max_tokens=4000  # 限制token数量，避免过长消息
        )
    elif provider == 'openai':
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Error: OPENAI_API_KEY is not set. Please provide a valid API key.")

        return ChatOpenAI(
            model='gpt-4o', 
            temperature=0.0,
            max_tokens=4000  # 限制token数量
        )
    elif provider == 'deepseek':
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL")

        logger.info(f"DEEPSEEK_API_KEY: {api_key != None}")
        logger.info(f"DEEPSEEK_BASE_URL: {base_url}")
        if not api_key:
            raise ValueError("Error: DEEPSEEK_API_KEY is not set. Please provide a valid API key.")

        # 按照deepseek.py示例的方式简化配置
        return ChatOpenAI(
            base_url=base_url,
            model='deepseek-chat', 
            api_key=SecretStr(api_key),
            # 不添加额外参数，避免不兼容问题
        )
    else:
        raise ValueError(f'Unsupported provider: {provider}')


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="使用LLM增强的UI自动化测试工具")
    parser.add_argument(
        '--task',
        type=str,
        help='要执行的测试任务描述',
        default='访问https://hy-sit.1233s2b.com,等待页面加载完成,输入用户名13600805241，输入密码Aa123456，点击登录按钮，登录成功等待页面加载完成后,点击辽阳市兴宇纸业有限公司-管理端，等待跳转的页面加载完成,验证页面包含文本首页'  # 只执行第一步，成功后再执行后续步骤
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
        # 注册自定义操作，使其对LLM可用
        self._register_custom_actions()

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
        
    def get_action_logs(self):
        """获取操作日志 (此版本中将为空，因为拦截器已移除)"""
        logger.warning("Action interceptor has been removed, action_logs will be empty.")
        return [] # 返回空列表，因为action_logs将不再被填充
        
    def print_action_summary(self):
        """打印操作摘要 (此版本中将简化，因为拦截器已移除)"""
        logger.info(f"\n{'=' * 50}")
        logger.info(f"操作摘要 (拦截器已移除):")
        # 由于拦截器移除，无法准确统计缓存和标准操作
        # 可以考虑在自定义action内部进行日志记录和统计，如果需要
        logger.info(f"  注意: 详细的操作日志需要通过其他方式查看 (例如自定义action内部的logger)。")
        logger.info(f"{'=' * 50}")

    def _register_custom_actions(self):
        """注册自定义操作到registry，使其对LLM可用"""
        from browser_use.agent.views import ActionResult

        # 注册点击文本元素的操作 - 标准方式
        @self.registry.action("根据文本内容查找并点击元素")
        async def click_text(text: str, exact_match: bool = False):
            """通过文本内容查找并点击元素的操作，支持缓存查找以提高性能"""
            logger.info(f"LLM正在调用click_text操作，文本: '{text}', 精确匹配: {exact_match}")
            
            if not text:
                return ActionResult(success=False, extracted_content="必须提供要查找的文本内容")
            
            try:
                if not self.context:
                    return ActionResult(success=False, extracted_content="浏览器上下文未初始化")
                
                # 使用find_element_by_text查找元素
                element_index = await self._find_element_by_text(text, exact_match=exact_match)
                
                if element_index is None:
                    return ActionResult(success=False, extracted_content=f"未找到文本为 '{text}' 的元素")
                
                # 使用标准click_element执行点击
                # 注意：这里传递 self.context 作为 context 参数
                result = await self.registry.execute_action("click_element", {"index": element_index}, context=self.context)
                
                if result and hasattr(result, 'success') and result.success:
                    return ActionResult(success=True, extracted_content=f"成功点击文本为 '{text}' 的元素")
                else:
                    return ActionResult(success=False, extracted_content=f"点击文本为 '{text}' 的元素失败")
            
            except Exception as e:
                logger.error(f"click_text操作失败: {str(e)}")
                traceback.print_exc() # 打印完整的堆栈跟踪
                return ActionResult(success=False, extracted_content=f"操作失败: {str(e)}")

        # 注册输入文本的操作 - 标准方式
        @self.registry.action("在指定元素中输入文本")
        async def input_text_in_element(text: str, placeholder: str = None, input_type: str = None):
            """在输入框中输入文本，支持缓存查找以提高性能"""
            logger.info(f"LLM正在调用input_text_in_element操作，文本: '{text}'")
            
            if not text:
                return ActionResult(success=False, extracted_content="必须提供要输入的文本")
            
            try:
                if not self.context:
                    return ActionResult(success=False, extracted_content="浏览器上下文未初始化")
                
                # 查找输入框元素
                element_index = await self._find_input_element(input_type, placeholder)
                
                if element_index is None:
                    return ActionResult(success=False, extracted_content=f"未找到匹配的输入框元素")
                
                # 先点击元素获取焦点
                # 注意：这里传递 self.context 作为 context 参数
                click_result = await self.registry.execute_action("click_element", {"index": element_index}, context=self.context)
                
                if not (click_result and hasattr(click_result, 'success') and click_result.success):
                    logger.warning("点击输入框获取焦点失败")
                
                # 使用键盘输入文本
                page = await self.context.get_current_page()
                await page.keyboard.type(text)
                
                return ActionResult(success=True, extracted_content=f"成功向输入框输入文本: {text}")
            
            except Exception as e:
                logger.error(f"input_text_in_element操作失败: {str(e)}")
                traceback.print_exc() # 打印完整的堆栈跟踪
                return ActionResult(success=False, extracted_content=f"操作失败: {str(e)}")
                
    async def _find_element_by_text(self, text_content: str, tag_names=None, exact_match=False):
        """通过文本内容查找元素(优先使用缓存)"""
        if not self.context:
            logger.warning("浏览器上下文未初始化")
            return None
            
        # 如果上下文有cache_manager，使用缓存查找
        if hasattr(self.context, 'cache_manager'):
            # 获取当前页面URL
            page = await self.context.get_current_page()
            current_url = page.url
            
            # 获取缓存元素
            cached_elements = await self._get_cached_elements(current_url)
            
            # 在缓存中查找元素
            for idx, element in cached_elements.items():
                # 检查是否可交互
                if not element.get('is_interactive', False):
                    continue
                    
                # 检查标签名
                if tag_names and element.get('tag_name', '').lower() not in [t.lower() for t in tag_names]:
                    continue
                    
                # 获取元素文本
                element_text = ""
                if 'text' in element:
                    element_text = element.get('text', '')
                elif 'innerText' in element.get('attributes', {}):
                    element_text = element.get('attributes', {}).get('innerText', '')
                
                # 检查文本匹配
                if exact_match:
                    if element_text and ''.join(element_text.split()) == ''.join(text_content.split()):
                        logger.info(f"在缓存中找到文本为 '{text_content}' 的元素，索引: {idx}")
                        return int(idx)
                else:
                    if text_content in element_text:
                        logger.info(f"在缓存中找到包含文本 '{text_content}' 的元素，索引: {idx}")
                        return int(idx)
            
            logger.info(f"在缓存中未找到文本为 '{text_content}' 的元素，将使用标准方法")
        
        # 缓存中未找到或未启用缓存，使用标准方法
        dom_state = await self.context.get_state()
        
        for index, element in dom_state.selector_map.items():
            if not getattr(element, 'is_interactive', False):
                continue
                
            if tag_names and element.tag_name.lower() not in [t.lower() for t in tag_names]:
                continue
                
            element_text = ""
            if hasattr(element, 'get_all_text_till_next_clickable_element'):
                element_text = element.get_all_text_till_next_clickable_element()
            elif hasattr(element, 'text'):
                element_text = element.text
            elif hasattr(element, 'attributes') and 'innerText' in element.attributes:
                element_text = element.attributes['innerText']
            
            if exact_match:
                if element_text and ''.join(element_text.split()) == ''.join(text_content.split()):
                    logger.info(f"使用标准方法找到文本为 '{text_content}' 的元素，索引: {index}")
                    return index
            else:
                if text_content in element_text:
                    logger.info(f"使用标准方法找到包含文本 '{text_content}' 的元素，索引: {index}")
                    return index
                    
        logger.warning(f"未找到文本为 '{text_content}' 的元素")
        return None
        
    async def _find_input_element(self, input_type=None, placeholder=None):
        """查找输入框元素(优先使用缓存)"""
        if not self.context:
            logger.warning("浏览器上下文未初始化")
            return None
            
        # 如果启用了缓存，先尝试从缓存中查找
        if hasattr(self.context, 'cache_manager'):
            # 获取当前页面URL
            page = await self.context.get_current_page()
            current_url = page.url
            
            # 获取缓存元素
            cached_elements = await self._get_cached_elements(current_url)
            
            # 在缓存中查找输入框元素
            for idx, element in cached_elements.items():
                # 检查标签名
                if element.get('tag_name', '').lower() != "input":
                    continue
                    
                # 检查输入框类型
                element_attributes = element.get('attributes', {})
                element_type = element_attributes.get('type', '')
                
                # 检查输入框类型是否匹配
                if input_type and element_type != input_type:
                    # 特殊处理：有些输入框可能没有明确设置type
                    if input_type == "text" and element_type == "":
                        pass  # 允许空type作为text类型
                    else:
                        continue
                        
                # 检查占位符文本
                if placeholder:
                    element_placeholder = element_attributes.get("placeholder", "")
                    if placeholder.lower() not in element_placeholder.lower():
                        continue
                        
                logger.info(f"在缓存中找到输入框元素，索引: {idx}")
                return int(idx)
            
            logger.info(f"在缓存中未找到匹配的输入框元素，将使用标准方法")
        
        # 缓存中未找到或未启用缓存，使用标准方法
        dom_state = await self.context.get_state()
        
        for index, element in dom_state.selector_map.items():
            # 检查标签名
            if element.tag_name.lower() != "input":
                continue
                
            # 检查输入框类型
            element_type = element.attributes.get('type', '')
            
            # 检查输入框类型是否匹配
            if input_type and element_type != input_type:
                # 特殊处理：有些输入框可能没有明确设置type
                if input_type == "text" and element_type == "":
                    pass  # 允许空type作为text类型
                else:
                    continue
                    
            # 检查占位符文本
            if placeholder and hasattr(element, 'attributes'):
                element_placeholder = element.attributes.get("placeholder", "")
                if placeholder.lower() not in element_placeholder.lower():
                    continue
                    
            logger.info(f"使用标准方法找到输入框元素，索引: {index}")
            return index
                    
        logger.warning(f"未找到匹配的输入框元素")
        return None
        
    async def _get_cached_elements(self, url=None, force_refresh=False):
        """获取缓存的元素"""
        if not self.context or not hasattr(self.context, 'cache_manager'):
            logger.warning("浏览器上下文未初始化或未启用缓存")
            return {}
            
        if url is None:
            # 获取当前URL
            page = await self.context.get_current_page()
            url = page.url
            
        try:
            # 使用cache_manager获取缓存元素
            cached_elements = await self.context.cache_manager.get_elements_with_cache(url, force_refresh=force_refresh)
            logger.info(f"已从缓存获取 {len(cached_elements)} 个元素")
            return cached_elements
        except Exception as e:
            logger.error(f"获取缓存元素时出错: {str(e)}")
            return {}


# 更新EnhancedUITestAgent类
class EnhancedUITestAgent:
    """增强的UI测试代理，结合LLM能力和增强的UI测试方法"""
    def __init__(self, task: str, llm_provider: str, use_cache: bool = True, cache_dir: str = "ui_test_cache"):
        self.task = task
        self.task_steps = parse_task(task)  # 将任务拆分为步骤
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
        self.page = None
        self.context = None  # 存储浏览器上下文

    async def setup(self):
        """设置浏览器上下文并添加增强功能"""
        try:
            # 创建浏览器上下文
            context = await self.browser.new_context()
            logger.info("浏览器上下文创建成功")

            # 如果启用缓存，扩展上下文以支持元素缓存
            if self.use_cache:
                logger.info(f"启用元素缓存，缓存目录: {self.cache_dir}")
                context = extend_browser_context(context, cache_dir=self.cache_dir)
            
            # 存储上下文供后续使用
            self.context = context

            # 将上下文添加到控制器
            self.controller.context = context
            
        
            
            # 准备代理，告知新的自定义操作
            enhanced_task = self.task
            if self.use_cache:
                enhanced_task = f"{self.task}\n\n你有两个优化的操作可以使用：\n1. click_text - 根据文本内容查找并点击元素\n2. input_text_in_element - 在输入框中输入文本\n这些操作使用元素缓存来提高性能，优先使用它们而不是标准操作。"
            
            # 创建代理
            self.agent = Agent(
                task=enhanced_task,
                llm=self.llm,
                controller=self.controller,
                browser=self.browser,
                use_vision=False,
                max_actions_per_step=1,
            )

            # 如果有解析好的任务步骤，输出更清晰的指令
            if hasattr(self, 'task_steps') and len(self.task_steps) > 1:
                logger.info(f"任务已分解为 {len(self.task_steps)} 个步骤，将按顺序执行")
                # 任务步骤可以在Agent中使用，也可以由外部流程控制执行

            logger.info("浏览器设置完成，使用LLM驱动的测试，已注册缓存优化操作")
        
        except Exception as e:
            logger.error(f"浏览器设置失败: {e}")
            traceback.print_exc()
            raise

    async def find_input_element(self, input_type=None, placeholder=None):
        """查找输入框元素(优先使用缓存)"""
        if not self.context:
            logger.warning("浏览器上下文未初始化")
            return None
            
        # 如果启用了缓存，先尝试从缓存中查找
        if self.use_cache and hasattr(self.context, 'cache_manager'):
            # 获取当前页面URL
            page = await self.context.get_current_page()
            current_url = page.url
            
            # 获取缓存元素
            cached_elements = await self.get_cached_elements(current_url)
            
            # 在缓存中查找输入框元素
            for idx, element in cached_elements.items():
                # 检查标签名
                if element.get('tag_name', '').lower() != "input":
                    continue
                    
                # 检查输入框类型
                element_attributes = element.get('attributes', {})
                element_type = element_attributes.get('type', '')
                
                # 检查输入框类型是否匹配
                if input_type and element_type != input_type:
                    # 特殊处理：有些输入框可能没有明确设置type
                    if input_type == "text" and element_type == "":
                        pass  # 允许空type作为text类型
                    else:
                        continue
                        
                # 检查占位符文本
                if placeholder:
                    element_placeholder = element_attributes.get("placeholder", "")
                    if placeholder.lower() not in element_placeholder.lower():
                        continue
                        
                logger.info(f"在缓存中找到输入框元素，索引: {idx}")
                return int(idx)
            
            logger.info(f"在缓存中未找到匹配的输入框元素，将使用标准方法")
        
        # 缓存中未找到或未启用缓存，使用标准方法
        dom_state = await self.context.get_state()
        
        for index, element in dom_state.selector_map.items():
            # 检查标签名
            if element.tag_name.lower() != "input":
                continue
                
            # 检查输入框类型
            element_type = element.attributes.get('type', '')
            
            # 检查输入框类型是否匹配
            if input_type and element_type != input_type:
                # 特殊处理：有些输入框可能没有明确设置type
                if input_type == "text" and element_type == "":
                    pass  # 允许空type作为text类型
                else:
                    continue
                    
            # 检查占位符文本
            if placeholder and hasattr(element, 'attributes'):
                element_placeholder = element.attributes.get("placeholder", "")
                if placeholder.lower() not in element_placeholder.lower():
                    continue
                    
            logger.info(f"使用标准方法找到输入框元素，索引: {index}")
            return index
                    
        logger.warning(f"未找到匹配的输入框元素")
        return None

    async def run(self, max_steps: int = 25):
        """运行LLM驱动的UI测试"""
        self.report.start_test()

        try:
            # 设置浏览器和上下文
            try:
                await self.setup()
                logger.info("浏览器和上下文设置成功")
            except Exception as setup_error:
                logger.error(f"设置过程失败: {setup_error}")
                self.report.complete_test()
                return False

            # 如果启用缓存，预加载第一个URL
            if self.use_cache and self.task_steps and len(self.task_steps) > 0:
                try:
                    # 预处理第一步的URL导航
                    if "访问" in self.task_steps[0]:
                        url = self.task_steps[0].replace("访问", "").strip()
                        logger.info(f"预加载第一步URL: {url}")
                        
                        page = await self.context.get_current_page()
                        await page.goto(url)
                        await page.wait_for_load_state("networkidle")
                        
                        # 刷新缓存
                        current_url = page.url
                        logger.info(f"刷新页面元素缓存: {current_url}")
                        # 使用EnhancedUITestAgent自己的方法
                        await self.get_cached_elements(current_url, force_refresh=True)
                except Exception as preload_error:
                    logger.error(f"预加载第一步URL失败: {preload_error}")
                    # 继续执行，不阻断主流程
            
            # 运行代理
            try:
                logger.info("开始运行Agent...")
                
                # 添加重试机制
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        # 将步骤数减半，避免过长的会话历史
                        effective_steps = min(max_steps, 12)
                        logger.info(f"尝试运行Agent (尝试 {retry+1}/{max_retries})，最大步骤数: {effective_steps}")
                        
                        # 运行Agent
                        await self.agent.run(max_steps=effective_steps)
                        logger.info("Agent运行完成")
                        break
                    except Exception as attempt_error:
                        if retry < max_retries - 1:
                            logger.warning(f"Agent运行尝试 {retry+1} 失败: {attempt_error}，准备重试...")
                            # 等待一段时间再重试
                            await asyncio.sleep(2)
                        else:
                            logger.error(f"所有Agent运行尝试都失败: {attempt_error}")
                            raise
            except Exception as agent_error:
                logger.error(f"Agent运行失败: {agent_error}")
                traceback.print_exc()
                self.report.complete_test()
                return False

            # 完成测试
            success = self.report.complete_test()
            
            # 打印操作摘要
            if hasattr(self.controller, 'print_action_summary'):
                self.controller.print_action_summary()
                
            return success

        except Exception as e:
            logger.error(f"执行测试时发生错误: {str(e)}")
            traceback.print_exc()
            self.report.complete_test()
            return False

        finally:
            # 提示用户
            try:
                input("测试完成，按Enter键关闭浏览器...")
                # 关闭浏览器
                await self.browser.close()
                logger.info("测试浏览器已关闭")
            except Exception as close_error:
                logger.error(f"关闭浏览器时出错: {close_error}")

    # 添加获取缓存元素的方法
    async def get_cached_elements(self, url=None, force_refresh=False):
        """获取缓存的元素"""
        if not self.context or not hasattr(self.context, 'cache_manager'):
            logger.warning("浏览器上下文未初始化或未启用缓存")
            return {}
            
        if url is None:
            # 获取当前URL
            page = await self.context.get_current_page()
            url = page.url
            
        try:
            # 直接使用cache_manager获取缓存元素
            cached_elements = await self.context.cache_manager.get_elements_with_cache(url, force_refresh=force_refresh)
            logger.info(f"已从缓存获取 {len(cached_elements)} 个元素")
            return cached_elements
        except Exception as e:
            logger.error(f"获取缓存元素时出错: {str(e)}")
            return {}
            
    async def find_element_by_text(self, text_content: str, tag_names=None, exact_match=False, interactive_only=True):
        """通过文本内容查找元素(优先使用缓存)"""
        if not self.context:
            logger.warning("浏览器上下文未初始化")
            return None
            
        # 如果启用了缓存，先尝试从缓存中查找
        if self.use_cache and hasattr(self.context, 'cache_manager'):
            # 获取当前页面URL
            page = await self.context.get_current_page()
            current_url = page.url
            
            # 获取缓存元素
            cached_elements = await self.get_cached_elements(current_url)
            
            # 在缓存中查找元素
            for idx, element in cached_elements.items():
                # 检查是否只查找可交互元素
                if interactive_only and not element.get('is_interactive', False):
                    continue
                    
                # 检查标签名
                if tag_names and element.get('tag_name', '').lower() not in [t.lower() for t in tag_names]:
                    continue
                    
                # 获取元素文本 - 可能存储在不同字段
                element_text = ""
                if 'text' in element:
                    element_text = element.get('text', '')
                elif 'innerText' in element.get('attributes', {}):
                    element_text = element.get('attributes', {}).get('innerText', '')
                
                # 检查文本匹配
                if exact_match:
                    # 精确匹配逻辑
                    if element_text and ''.join(element_text.split()) == ''.join(text_content.split()):
                        logger.info(f"在缓存中找到文本为 '{text_content}' 的元素，索引: {idx}")
                        return int(idx)
                else:
                    if text_content in element_text:
                        logger.info(f"在缓存中找到包含文本 '{text_content}' 的元素，索引: {idx}")
                        return int(idx)
            
            logger.info(f"在缓存中未找到文本为 '{text_content}' 的元素，将使用标准方法")
        
        # 缓存中未找到或未启用缓存，使用标准方法
        dom_state = await self.context.get_state()
        
        for index, element in dom_state.selector_map.items():
            # 检查是否只查找可交互元素
            if interactive_only and not getattr(element, 'is_interactive', False):
                continue
                
            # 检查标签名
            if tag_names and element.tag_name.lower() not in [t.lower() for t in tag_names]:
                continue
                
            # 获取元素文本
            element_text = ""
            if hasattr(element, 'get_all_text_till_next_clickable_element'):
                element_text = element.get_all_text_till_next_clickable_element()
            elif hasattr(element, 'text'):
                element_text = element.text
            elif hasattr(element, 'attributes') and 'innerText' in element.attributes:
                element_text = element.attributes['innerText']
            
            # 检查文本匹配
            if exact_match:
                # 精确匹配逻辑
                cleaned_element_text = ''.join(element_text.split())
                cleaned_text_content = ''.join(text_content.split())
                
                if cleaned_element_text == cleaned_text_content:
                    logger.info(f"使用标准方法找到文本为 '{text_content}' 的元素，索引: {index}")
                    return index
            else:
                if text_content in element_text:
                    logger.info(f"使用标准方法找到包含文本 '{text_content}' 的元素，索引: {index}")
                    return index
                    
        logger.warning(f"未找到文本为 '{text_content}' 的元素")
        return None

    async def click_element_by_text(self, text_content: str, tag_names=None, exact_match=False):
        """查找并点击包含指定文本的元素"""
        if not self.context:
            logger.warning("浏览器上下文未初始化")
            return False
            
        # 查找元素（优先使用缓存）
        element_index = await self.find_element_by_text(text_content, tag_names, exact_match, interactive_only=True)
        
        if element_index is None:
            logger.warning(f"未找到文本为 '{text_content}' 的可点击元素")
            return False
            
        try:
            # 获取控制器并执行点击操作
            controller = self.controller
            logger.info(f"点击索引为 {element_index} 的元素")
            
            # 执行点击操作
            result = await controller.registry.execute_action("click_element", {"index": element_index}, self.context)
            
            # 检查点击是否成功
            if result and hasattr(result, 'success') and result.success:
                logger.info(f"成功点击文本为 '{text_content}' 的元素")
                return True
            else:
                logger.warning(f"点击文本为 '{text_content}' 的元素失败")
                return False
        except Exception as e:
            logger.error(f"点击元素时出错: {str(e)}")
            return False
    
    async def input_text(self, input_type=None, placeholder=None, text=""):
        """查找输入框并输入文本"""
        if not self.context:
            logger.warning("浏览器上下文未初始化")
            return False
            
        # 查找输入框元素（优先使用缓存）
        element_index = await self.find_input_element(input_type, placeholder)
        
        if element_index is None:
            logger.warning(f"未找到匹配的输入框元素")
            return False
            
        try:
            # 获取控制器
            controller = self.controller
            logger.info(f"向索引为 {element_index} 的输入框输入文本: {text}")
            
            # 先点击元素获取焦点
            click_result = await controller.registry.execute_action("click_element", {"index": element_index}, self.context)
            
            if not (click_result and hasattr(click_result, 'success') and click_result.success):
                logger.warning("点击输入框获取焦点失败")
                
            # 使用键盘输入文本
            page = await self.context.get_current_page()
            await page.keyboard.type(text)
            
            logger.info(f"成功向输入框输入文本: {text}")
            return True
        except Exception as e:
            logger.error(f"输入文本时出错: {str(e)}")
            return False


async def main():
    """主函数"""
    args = parse_arguments()

    try:
        # 验证环境变量
        provider = args.provider.lower()
        if provider == 'anthropic' and not os.getenv("ANTHROPIC_API_KEY"):
            logger.error("错误: 缺少ANTHROPIC_API_KEY环境变量")
            return False
        elif provider == 'openai' and not os.getenv("OPENAI_API_KEY"):
            logger.error("错误: 缺少OPENAI_API_KEY环境变量")
            return False
        elif provider == 'deepseek' and (not os.getenv("DEEPSEEK_API_KEY") or not os.getenv("DEEPSEEK_BASE_URL")):
            logger.error("错误: 缺少DEEPSEEK_API_KEY或DEEPSEEK_BASE_URL环境变量")
            return False

        # 创建并运行增强的UI测试代理
        logger.info("使用LLM驱动的UI测试")
        agent = EnhancedUITestAgent(
            task=args.task,
            llm_provider=args.provider,
            use_cache=args.use_cache,
            cache_dir=args.cache_dir
        )

        try:
            success = await agent.run(max_steps=args.max_steps)
            # 退出码：0表示成功，1表示失败
            return success
        except Exception as e:
            logger.error(f"执行测试过程中发生错误: {str(e)}")
            traceback.print_exc()
            return False

    except Exception as e:
        logger.error(f"初始化过程中发生错误: {str(e)}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
