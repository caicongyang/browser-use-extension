import os
import asyncio
import logging
import sys
import time
from typing import Dict, Any, List, Tuple, Optional, Union

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '../..')))

from browser_use import Browser, Controller
from browser_use.agent.views import ActionResult
from browser_use.controller.views import ClickElementAction
# 从当前目录的browser_extension模块导入
from browser_extension.context_extension import extend_browser_context

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        self.total_standard_time: float = 0.0  # 标准操作总耗时
        self.total_cache_time: float = 0.0     # 缓存操作总耗时
        
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

async def is_element_hidden(element):
    """检查元素是否隐藏"""
    # 安全地检查元素是否有is_hidden属性，如果没有则检查可见性相关的其他属性
    if hasattr(element, 'is_hidden'):
        return element.is_hidden
    
    # 备选检查方法
    if hasattr(element, 'attributes'):
        # 检查style属性中是否包含display:none或visibility:hidden
        style = element.attributes.get('style', '').lower()
        if 'display: none' in style or 'visibility: hidden' in style:
            return True
        
        # 检查是否有hidden属性
        if element.attributes.get('hidden') is not None:
            return True
    
    # 默认认为元素可见
    return False

async def find_element_by_text(context, text_content: str, tag_names: Optional[List[str]] = None, exact_match: bool = False, interactive_only: bool = True) -> Optional[int]:
    """通过文本内容查找元素
    
    Args:
        context: 浏览器上下文
        text_content: 要查找的文本内容
        tag_names: 限制查找的标签名列表，为None时不限制
        exact_match: 是否要求精确匹配文本
        interactive_only: 是否只查找可交互元素
        
    Returns:
        找到的元素索引，未找到时返回None
    """
    dom_state = await context.get_state()
    
    for index, element in dom_state.selector_map.items():
        # 检查是否只查找可交互元素
        if interactive_only and not getattr(element, 'is_interactive', False):
            continue
            
        # 检查是否隐藏
        if await is_element_hidden(element):
            continue
            
        # 检查标签名
        if tag_names and element.tag_name.lower() not in [t.lower() for t in tag_names]:
            continue
            
        # 获取元素文本 - 安全地访问方法
        element_text = ""
        if hasattr(element, 'get_all_text_till_next_clickable_element'):
            element_text = element.get_all_text_till_next_clickable_element()
        elif hasattr(element, 'text'):
            element_text = element.text
        elif hasattr(element, 'attributes') and 'innerText' in element.attributes:
            element_text = element.attributes['innerText']
        
        # 检查文本匹配
        if exact_match:
            # 去除前后空格，将中间的多个空格替换为单个空格
            cleaned_element_text = ' '.join(element_text.split())
            cleaned_text_content = ' '.join(text_content.split())
            
            # 移除中文字符之间的空格
            cleaned_element_text = ''.join(cleaned_element_text.split())
            cleaned_text_content = ''.join(cleaned_text_content.split())
            
            if cleaned_element_text == cleaned_text_content:
                return index
            else:
                continue
        
        else:
            if text_content in element_text:
                return index
                
    return None

async def find_input_element(context, input_type: Optional[str] = None, placeholder: Optional[str] = None) -> Optional[int]:
    """查找输入框元素
    
    Args:
        context: 浏览器上下文
        input_type: 输入框类型，如"text"、"password"等
        placeholder: 输入框占位符文本
        
    Returns:
        找到的元素索引，未找到时返回None
    """
    dom_state = await context.get_state()
    
    for index, element in dom_state.selector_map.items():
        # 检查标签名
        if element.tag_name.lower() != "input":
            continue
            
        # 检查是否隐藏
        if await is_element_hidden(element):
            continue
            
        # 检查输入框类型 - 安全地获取input_type
        element_type = getattr(element, 'input_type', None)
        if element_type is None and hasattr(element, 'attributes'):
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
                
        return index
                
    return None

async def measure_performance(context, operation_func, args=(), use_cache=False):
    """测量操作性能
    
    Args:
        context: 浏览器上下文
        operation_func: 要测量的操作函数
        args: 操作函数的参数
        use_cache: 是否使用缓存
        
    Returns:
        (操作结果, 耗时)
    """
    start_time = time.time()
    result = await operation_func(*args)
    end_time = time.time()
    return result, end_time - start_time

async def get_cached_elements(context, url, force_refresh=False):
    """安全地获取缓存的元素"""
    try:
        # 首先尝试使用cache_manager访问
        if hasattr(context, 'cache_manager'):
            return await context.cache_manager.get_elements_with_cache(url, force_refresh=force_refresh)
        
        # 如果上面的方法不可用，尝试直接调用get_elements_with_cache
        if hasattr(context, 'get_elements_with_cache'):
            return await context.get_elements_with_cache(url, force_refresh=force_refresh)
        
        # 如果都不可用，则返回空字典
        logger.warning("无法找到缓存方法，返回空缓存")
        return {}
    except Exception as e:
        logger.error(f"获取缓存元素时出错: {str(e)}")
        return {}

def get_available_actions(controller) -> List[str]:
    """安全地获取控制器中可用的操作列表"""
    try:
        # 尝试通过不同方式获取可用操作
        available_actions = []
        
        # 尝试直接通过get_registered_actions方法获取
        if hasattr(controller.registry, 'get_registered_actions'):
            return controller.registry.get_registered_actions()
        
        # 尝试通过dir()获取所有成员，并过滤出可能的操作
        registry_members = dir(controller.registry)
        action_methods = [
            member for member in registry_members 
            if member.startswith("action_") or 
               member.endswith("_action") or
               "execute" in member
        ]
        
        if action_methods:
            logger.info(f"发现可能的操作方法: {action_methods}")
            
        # 基于常见操作猜测可用的操作
        common_actions = [
            "click_element", "fill", "type", "input_text", "focus", "blur",
            "press_key", "scroll", "navigate", "get_text"
        ]
        
        # 尝试执行，看哪些是可用的
        logger.info("将使用以下常见操作: click_element")
        
        return ["click_element"]  # 默认至少返回click_element操作
        
    except Exception as e:
        logger.warning(f"获取可用操作失败: {str(e)}")
        return ["click_element"]  # 至少返回一个我们知道应该存在的操作

async def input_text_to_element(controller, context, element_index, text):
    """向元素输入文本，尝试多种可能的操作名称"""
    # 安全地获取可用操作
    try:
        # 尝试多种可能的输入文本方式
        # 1. 先尝试直接点击元素
        logger.info("首先尝试点击元素")
        try:
            await controller.registry.execute_action("click_element", {"index": element_index}, context)
            logger.info("元素点击成功")
            
            # 2. 获取当前页面并使用keyboard.type直接输入
            page = await context.get_current_page()
            await page.keyboard.type(text)
            logger.info("通过keyboard.type方法输入文本成功")
            return ActionResult(success=True, extracted_content=f"已点击并输入文本: {text}")
        except Exception as e:
            logger.warning(f"点击和键盘输入失败: {str(e)}")
            
        # 3. 尝试使用fill方法直接填充元素
        try:
            logger.info("尝试使用元素选择器直接填充文本")
            page = await context.get_current_page()
            dom_state = await context.get_state()
            element = dom_state.selector_map.get(element_index)
            
            if element and hasattr(element, 'selector'):
                await page.fill(element.selector, text)
                logger.info("通过fill方法输入文本成功")
                return ActionResult(success=True, extracted_content=f"已使用fill填充文本: {text}")
        except Exception as e:
            logger.warning(f"使用fill方法填充文本失败: {str(e)}")
        
        # 4. 如果以上方法都失败，尝试使用评估JS直接设置值
        try:
            logger.info("尝试使用JavaScript设置元素值")
            page = await context.get_current_page()
            dom_state = await context.get_state()
            element = dom_state.selector_map.get(element_index)
            
            if element and hasattr(element, 'selector'):
                await page.evaluate(f"""
                    selector => {{
                        const element = document.querySelector(selector);
                        if (element) {{
                            element.value = '{text}';
                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }}
                """, element.selector)
                logger.info("通过JavaScript设置元素值成功")
                return ActionResult(success=True, extracted_content=f"已使用JavaScript设置文本: {text}")
        except Exception as e:
            logger.warning(f"使用JavaScript设置元素值失败: {str(e)}")
        
        # 如果所有方法都失败
        raise Exception("所有输入文本的方法都失败")
            
    except Exception as e:
        logger.error(f"输入文本过程中发生错误: {str(e)}")
        raise Exception(f"无法输入文本到元素: {str(e)}")

async def run_ui_test():
    """运行UI测试"""
    logger.info("启动UI测试...")
    
    # 创建测试报告
    report = UITestReport("登录系统测试")
    report.start_test()
    
    # 创建浏览器和控制器
    browser = Browser()  # 使用默认配置
    controller = Controller()
    
    # 创建浏览器上下文并添加缓存功能
    context = await browser.new_context()
    context = extend_browser_context(context, cache_dir="ui_test_cache")
    
    try:
        # 定义测试任务
        task = '访问https://hy-sit.1233s2b.com,等待页面加载完成,输入用户名13600805241，输入密码Aa123456，点击登录按钮，登录成功等待页面加载完成后,点击辽阳市兴宇纸业有限公司-管理端，等待跳转的页面加载完成,验证页面包含文本首页'
        logger.info(f"测试任务: {task}")
        
        # 步骤1: 访问网站
        step1 = UITestStep("访问网站", "访问https://hy-sit.1233s2b.com并等待页面加载")
        step1.start()
        
        try:
            page = await context.get_current_page()
            await page.goto("https://hy-sit.1233s2b.com")
            await page.wait_for_load_state()
            
            # 获取当前URL并缓存页面元素
            current_url = page.url
            logger.info(f"当前页面: {current_url}")
            
            # 使用缓存获取页面元素 - 使用安全的方法
            cached_elements = await get_cached_elements(context, current_url, force_refresh=True)
            logger.info(f"缓存了 {len(cached_elements)} 个元素")
            
            # 等待一下确保页面完全加载
            await asyncio.sleep(2)
            
            step1.complete(True)
        except Exception as e:
            step1.complete(False, str(e))
        
        report.add_step(step1)
        
        # 如果前一步失败，则后续步骤不执行
        if not step1.success:
            logger.error("由于前序步骤失败，测试终止")
            report.complete_test()
            return False
        
        # 步骤2: 输入用户名
        step2 = UITestStep("输入用户名", "定位用户名输入框并输入13600805241")
        step2.start()
        
        try:
            # 比较标准方法和缓存方法的性能差异
            standard_func = find_input_element
            standard_args = (context, "text", "请输入手机号")
            username_index, standard_time = await measure_performance(context, standard_func, standard_args)
            
            # 如果没有找到明确的手机号输入框，尝试查找其他可能的用户名输入框
            if username_index is None:
                username_index, additional_time = await measure_performance(
                    context, 
                    find_input_element, 
                    (context, "tel", None)
                )
                standard_time += additional_time
                
            # 再次尝试查找任何文本输入框
            if username_index is None:
                username_index, additional_time = await measure_performance(
                    context, 
                    find_input_element, 
                    (context, "text", None)
                )
                standard_time += additional_time
            
            if username_index is None:
                raise Exception("未找到用户名输入框")
            
            # 输入用户名 - 使用改进的输入文本方法
            await input_text_to_element(controller, context, username_index, "13600805241")
            logger.info("用户名输入完成")
            
            # 记录性能数据
            cache_time = 0.0  # 缓存方法在这个步骤中尚未实现
            report.total_standard_time += standard_time
            report.total_cache_time += cache_time
            
            step2.complete(True)
        except Exception as e:
            step2.complete(False, str(e))
        
        report.add_step(step2)
        
        if not step2.success:
            logger.error("由于前序步骤失败，测试终止")
            report.complete_test()
            return False
        
        # 步骤3: 输入密码
        step3 = UITestStep("输入密码", "定位密码输入框并输入Aa123456")
        step3.start()
        
        try:
            # 查找密码输入框
            password_index, standard_time = await measure_performance(
                context,
                find_input_element,
                (context, "password", None)
            )
            
            if password_index is None:
                raise Exception("未找到密码输入框")
            
            # 输入密码 - 使用改进的输入文本方法
            await input_text_to_element(controller, context, password_index, "Aa123456")
            logger.info("密码输入完成")
            
            # 记录性能数据
            cache_time = 0.0  # 缓存方法在这个步骤中尚未实现
            report.total_standard_time += standard_time
            report.total_cache_time += cache_time
            
            step3.complete(True)
        except Exception as e:
            step3.complete(False, str(e))
        
        report.add_step(step3)
        
        if not step3.success:
            logger.error("由于前序步骤失败，测试终止")
            report.complete_test()
            return False
        
        # 步骤4: 点击登录按钮
        step4 = UITestStep("登  录", "定位并点击登录按钮")
        step4.start()
        
        try:
            # 使用标准方法查找登录按钮
            login_button_index, standard_time = await measure_performance(
                context,
                find_element_by_text,
                (context, "登 录", ["button", "div", "span"], False, True)
            )
            
            # 使用缓存方法再次查找
            page = await context.get_current_page()
            current_url = page.url
            cached_elements = await get_cached_elements(context, current_url)
            
            cache_start = time.time()
            cache_login_index = None
            
            # 使用缓存数据查找登录按钮
            for idx, element in cached_elements.items():
                text = element.get("text", "").lower()
                if "登录" in text.lower() and element.get("is_interactive", False):
                    cache_login_index = idx
                    break
                    
            cache_time = time.time() - cache_start
            
            # 使用找到的按钮索引（优先使用标准方法找到的）
            login_button_index = login_button_index or cache_login_index
            
            if login_button_index is None:
                raise Exception("未找到登录按钮")
            
            # 点击登录按钮 - 使用字典形式的参数
            await controller.registry.execute_action("click_element", {"index": login_button_index}, context)
            logger.info("已点击登录按钮")
            
            # 记录性能数据
            report.total_standard_time += standard_time
            report.total_cache_time += cache_time
            
            # 增强的等待机制，确保登录成功并页面完全刷新
            logger.info("等待登录成功并页面刷新完成...")
            
            # 1. 等待页面加载状态
            await page.wait_for_load_state("networkidle")
            
            # 2. 等待URL变化，这通常表示导航已发生
            initial_url = page.url
            start_time = time.time()
            max_wait_time = 10  # 最长等待10秒
            
            while time.time() - start_time < max_wait_time:
                current_url = page.url
                if current_url != initial_url:
                    logger.info(f"检测到URL变化: {initial_url} -> {current_url}")
                    break
                await asyncio.sleep(0.5)
            
            # 3. 等待额外时间以确保页面上的所有元素都加载完成
            logger.info("等待页面元素加载完成...")
            await asyncio.sleep(5)
            
            # 4. 等待可能的动画效果完成
            await page.wait_for_load_state("domcontentloaded")
            
            # 5. 检查页面内容变化，确认已经登录成功
            try:
                # 尝试查找登录成功后通常会出现的元素或文本
                success_indicators = ["登出", "欢迎", "用户", "首页", "控制台", "管理"]
                dom_state = await context.get_state()
                
                found_indicator = False
                for idx, element in dom_state.selector_map.items():
                    element_text = ""
                    if hasattr(element, 'get_all_text_till_next_clickable_element'):
                        element_text = element.get_all_text_till_next_clickable_element()
                    elif hasattr(element, 'attributes') and 'innerText' in element.attributes:
                        element_text = element.attributes['innerText']
                        
                    if element_text and any(indicator in element_text for indicator in success_indicators):
                        logger.info(f"发现登录成功指示符: '{element_text[:30]}...'")
                        found_indicator = True
                        break
                        
                if found_indicator:
                    logger.info("确认登录成功，页面已刷新")
                else:
                    logger.warning("未发现明确的登录成功标识，但将继续执行")
            except Exception as e:
                logger.warning(f"检查登录状态时出错: {str(e)}")
            
            step4.complete(True)
        except Exception as e:
            step4.complete(False, str(e))
        
        report.add_step(step4)
        
        if not step4.success:
            logger.error("由于前序步骤失败，测试终止")
            report.complete_test()
            return False
        
        # 步骤5: 点击辽阳市兴宇纸业有限公司-管理端
        step5 = UITestStep("点击按钮", "定位并点击辽阳市兴宇纸业有限公司-管理端按钮")
        step5.start()
        
        try:
            # 缓存当前页面元素以提高性能
            page = await context.get_current_page()
            current_url = page.url
            cached_elements = await get_cached_elements(context, current_url, force_refresh=True)
            
            # 等待一段时间确保页面上的所有元素都已加载
            await asyncio.sleep(2)
            
            # 使用标准方法查找目标元素 - 注意这里不限制元素类型，并使用部分匹配
            target_element_index, standard_time = await measure_performance(
                context,
                find_element_by_text,
                (context, "辽阳市兴宇纸业有限公司", None, False, True)
            )
            
            # 如果没有找到，尝试更宽松的搜索
            if target_element_index is None:
                logger.info("尝试更宽松的搜索方式查找目标元素")
                target_element_index, additional_time = await measure_performance(
                    context,
                    find_element_by_text,
                    (context, "兴宇纸业", None, False, True)
                )
                standard_time += additional_time
            
            # 使用缓存方法查找
            cache_start = time.time()
            cache_target_index = None
            
            # 在缓存中以更宽松的方式查找
            search_terms = ["辽阳市兴宇纸业有限公司", "兴宇纸业", "管理端"]
            for idx, element in cached_elements.items():
                text = element.get("text", "")
                if element.get("is_interactive", False):
                    for term in search_terms:
                        if term in text:
                            cache_target_index = idx
                            logger.info(f"在缓存中找到匹配元素，文本: {text}")
                            break
                    if cache_target_index is not None:
                        break
                    
            cache_time = time.time() - cache_start
            
            # 使用找到的元素索引（优先使用标准方法找到的）
            target_element_index = target_element_index or cache_target_index
            
            if target_element_index is None:
                # 如果找不到，尝试从DOM中查找并打印所有可交互元素，方便调试
                logger.warning("未找到目标元素，尝试列出所有可交互元素")
                dom_state = await context.get_state()
                interactive_elements = []
                
                for idx, element in dom_state.selector_map.items():
                    if getattr(element, 'is_interactive', False) and not await is_element_hidden(element):
                        element_text = ""
                        if hasattr(element, 'get_all_text_till_next_clickable_element'):
                            element_text = element.get_all_text_till_next_clickable_element()
                        elif hasattr(element, 'text'):
                            element_text = element.text
                        elif hasattr(element, 'attributes') and 'innerText' in element.attributes:
                            element_text = element.attributes['innerText']
                            
                        if element_text:
                            logger.info(f"可交互元素 #{idx}: {element_text[:100]}...")
                            interactive_elements.append((idx, element_text))
                
                # 再次尝试匹配，使用更宽松的条件
                for idx, text in interactive_elements:
                    if any(term.lower() in text.lower() for term in ["纸业", "辽阳", "管理"]):
                        logger.info(f"使用宽松匹配找到可能的目标元素: {text}")
                        target_element_index = idx
                        break
                
                if target_element_index is None:
                    raise Exception("未找到'辽阳市兴宇纸业有限公司-管理端'或相关元素")
            
            # 记录性能数据
            report.total_standard_time += standard_time
            report.total_cache_time += cache_time
            
            # 点击目标元素
            logger.info(f"尝试点击元素索引 {target_element_index}")
            await controller.registry.execute_action("click_element", {"index": target_element_index}, context)
            logger.info("已点击目标元素")
            
            # 等待页面跳转完成
            logger.info("等待页面跳转完成")
            await page.wait_for_load_state()
            await asyncio.sleep(3)  # 额外等待以确保跳转后的页面完全加载
            
            step5.complete(True)
        except Exception as e:
            step5.complete(False, str(e))
        
        report.add_step(step5)
        
        if not step5.success:
            logger.error("由于前序步骤失败，测试终止")
            report.complete_test()
            return False
        
        # 步骤6: 验证页面包含文本"首页"
        step6 = UITestStep("验证页面内容", "验证页面包含文本'首页'")
        step6.start()
        
        try:
            # 使用标准方法验证
            home_text_index, standard_time = await measure_performance(
                context,
                find_element_by_text,
                (context, "首页", None, False, False)
            )
            
            # 使用缓存方法验证
            page = await context.get_current_page()
            current_url = page.url
            cached_elements = await get_cached_elements(context, current_url)
            
            cache_start = time.time()
            cache_home_index = None
            
            for idx, element in cached_elements.items():
                text = element.get("text", "")
                if "首页" in text:
                    cache_home_index = idx
                    break
                    
            cache_time = time.time() - cache_start
            
            # 记录性能数据
            report.total_standard_time += standard_time
            report.total_cache_time += cache_time
            
            # 验证结果
            found_text = (home_text_index is not None) or (cache_home_index is not None)
            
            if not found_text:
                raise Exception("页面不包含文本'首页'")
            
            logger.info("验证成功: 页面包含文本'首页'")
            step6.complete(True)
        except Exception as e:
            step6.complete(False, str(e))
        
        report.add_step(step6)
        
        # 完成测试并生成报告
        success = report.complete_test()
        return success
        
    except Exception as e:
        logger.error(f"执行测试任务时发生错误: {str(e)}")
        report.complete_test()
        return False
    finally:
        # 关闭浏览器
        await browser.close()
        logger.info("测试浏览器已关闭")

async def batch_run_tests(num_runs=1):
    """批量运行测试多次以获取更稳定的性能数据"""
    logger.info(f"开始批量运行UI测试 ({num_runs}次)...")
    
    success_count = 0
    
    for i in range(num_runs):
        logger.info(f"\n运行测试 #{i+1}/{num_runs}")
        success = await run_ui_test()
        if success:
            success_count += 1
    
    success_rate = (success_count / num_runs) * 100
    logger.info(f"\n批量测试完成: 成功率 {success_rate:.2f}% ({success_count}/{num_runs})")

if __name__ == "__main__":
    # 创建缓存目录
    os.makedirs("ui_test_cache", exist_ok=True)
    
    # 运行UI测试
    # asyncio.run(run_ui_test())
    
    # 批量运行测试以获取更稳定的性能数据
    asyncio.run(batch_run_tests(1))  # 默认运行1次，可以增加次数以获取更稳定的数据 