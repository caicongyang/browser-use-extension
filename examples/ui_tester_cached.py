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
parent_dir = os.path.dirname(current_dir)  # browser-use-extension目录
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '../..')))

from browser_use import Browser, Controller
from browser_use.agent.views import ActionResult
# 从element_enhance包中导入
from element_enhance.browser_extension.context_extension import extend_browser_context

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
        self.total_time: float = 0.0  # 缓存操作总耗时
        
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
        
        if self.total_time > 0:
            logger.info(f"\n性能数据:")
            logger.info(f"  缓存操作总耗时: {self.total_time:.4f}秒")
        
        logger.info(f"\n步骤详情:")
        for i, step in enumerate(self.steps, 1):
            status = "✅ 成功" if step.success else "❌ 失败"
            logger.info(f"  {i}. {step.name}: {status} ({step.duration:.2f}秒)")
            if not step.success:
                logger.info(f"     错误: {step.error_message}")
                
        logger.info(f"{'=' * 50}")
        
        # 返回测试是否全部成功
        return successful_steps == total_steps

class CachedUITester:
    """使用缓存的UI测试器"""
    
    def __init__(self):
        self.report = None  # 存储测试报告
    
    async def is_element_hidden(self, element):
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

    async def get_cached_elements(self, context, url, force_refresh=False):
        """安全地获取缓存的元素"""
        try:
            # 直接使用cache_manager访问，与test_cache.py一致
            return await context.cache_manager.get_elements_with_cache(url, force_refresh=force_refresh)
        except Exception as e:
            logger.error(f"获取缓存元素时出错: {str(e)}")
            return {}

    async def find_element_by_text_cached(self, context, text_content: str, tag_names: Optional[List[str]] = None, exact_match: bool = False, interactive_only: bool = True) -> Optional[int]:
        """通过文本内容查找元素（使用缓存）"""
        # 获取当前页面URL
        page = await context.get_current_page()
        current_url = page.url
        
        # 从缓存中获取元素
        cached_elements = await self.get_cached_elements(context, current_url)
        
        # 在缓存中查找元素
        for idx, element in cached_elements.items():
            # # 检查是否只查找可交互元素
            # if interactive_only and not element.get('is_interactive', False):
            #     continue
                
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
                # 简化的精确匹配逻辑
                if element_text and ''.join(element_text.split()) == ''.join(text_content.split()):
                    return int(idx)  # 确保返回整数索引
            else:
                if text_content in element_text:
                    return int(idx)  # 确保返回整数索引
                    
        return None

    async def find_input_element_cached(self, context, input_type: Optional[str] = None, placeholder: Optional[str] = None) -> Optional[int]:
        """查找输入框元素（使用缓存）"""
        # 获取当前页面URL
        page = await context.get_current_page()
        current_url = page.url
        
        # 从缓存中获取元素
        cached_elements = await self.get_cached_elements(context, current_url)
        
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
                    
            return int(idx)  # 确保返回整数索引
                    
        return None

    async def measure_performance(self, context, operation_func, args=()):
        """测量操作性能
        
        Args:
            context: 浏览器上下文
            operation_func: 要测量的操作函数
            args: 操作函数的参数
            
        Returns:
            (操作结果, 耗时)
        """
        start_time = time.time()
        result = await operation_func(*args)
        end_time = time.time()
        return result, end_time - start_time

    async def input_text_to_element(self, controller, context, element_index, text):
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

    async def run_ui_test(self):
        """运行UI测试"""
        logger.info("启动缓存UI测试（使用缓存）...")
        
        # 创建测试报告
        self.report = UITestReport("登录系统缓存测试")
        self.report.start_test()
        
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
                
                # 使用缓存获取页面元素 - 直接使用cache_manager，与test_cache.py一致
                cached_elements = await context.cache_manager.get_elements_with_cache(current_url, force_refresh=True)
                logger.info(f"缓存了 {len(cached_elements)} 个元素")
                
                # 等待一下确保页面完全加载
                await asyncio.sleep(2)
                
                step1.complete(True)
            except Exception as e:
                step1.complete(False, str(e))
            
            self.report.add_step(step1)
            
            # 如果前一步失败，则后续步骤不执行
            if not step1.success:
                logger.error("由于前序步骤失败，测试终止")
                self.report.complete_test()
                return False
            
            # 步骤2: 输入用户名
            step2 = UITestStep("输入用户名", "定位用户名输入框并输入13600805241")
            step2.start()
            
            try:
                # 使用缓存方法查找用户名输入框
                username_index, cache_time = await self.measure_performance(
                    context, 
                    self.find_input_element_cached, 
                    (context, "text", "请输入手机号")
                )
                
                # 如果没有找到明确的手机号输入框，尝试查找其他可能的用户名输入框
                if username_index is None:
                    username_index, additional_time = await self.measure_performance(
                        context, 
                        self.find_input_element_cached, 
                        (context, "tel", None)
                    )
                    cache_time += additional_time
                    
                # 再次尝试查找任何文本输入框
                if username_index is None:
                    username_index, additional_time = await self.measure_performance(
                        context, 
                        self.find_input_element_cached, 
                        (context, "text", None)
                    )
                    cache_time += additional_time
                
                if username_index is None:
                    raise Exception("未找到用户名输入框")
                
                # 输入用户名
                await self.input_text_to_element(controller, context, username_index, "13600805241")
                logger.info("用户名输入完成")
                
                # 记录性能数据
                self.report.total_time += cache_time
                
                step2.complete(True)
            except Exception as e:
                step2.complete(False, str(e))
            
            self.report.add_step(step2)
            
            if not step2.success:
                logger.error("由于前序步骤失败，测试终止")
                self.report.complete_test()
                return False
            
            # 步骤3: 输入密码
            step3 = UITestStep("输入密码", "定位密码输入框并输入Aa123456")
            step3.start()
            
            try:
                # 查找密码输入框
                password_index, cache_time = await self.measure_performance(
                    context,
                    self.find_input_element_cached,
                    (context, "password", None)
                )
                
                if password_index is None:
                    raise Exception("未找到密码输入框")
                
                # 输入密码
                await self.input_text_to_element(controller, context, password_index, "Aa123456")
                logger.info("密码输入完成")
                
                # 记录性能数据
                self.report.total_time += cache_time
                
                step3.complete(True)
            except Exception as e:
                step3.complete(False, str(e))
            
            self.report.add_step(step3)
            
            if not step3.success:
                logger.error("由于前序步骤失败，测试终止")
                self.report.complete_test()
                return False
            
            # 步骤4: 点击登录按钮
            step4 = UITestStep("登  录", "定位并点击登录按钮")
            step4.start()
            
            try:
                # 使用缓存方法查找登录按钮
                login_button_index, cache_time = await self.measure_performance(
                    context,
                    self.find_element_by_text_cached,
                    (context, "登 录", ["button", "div", "span"], False, True)
                )
                
                if login_button_index is None:
                    raise Exception("未找到登录按钮")
                
                # 点击登录按钮
                await controller.registry.execute_action("click_element", {"index": login_button_index}, context)
                logger.info("已点击登录按钮")
                
                # 记录性能数据
                self.report.total_time += cache_time
                
                # 增强的等待机制，确保登录成功并页面完全刷新
                logger.info("等待登录成功并页面刷新完成...")
                
                # 1. 等待页面加载状态
                page = await context.get_current_page()
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
                
                # 5. 刷新缓存获取新页面元素
                current_url = page.url
                await context.cache_manager.get_elements_with_cache(current_url, force_refresh=True)
                
                step4.complete(True)
            except Exception as e:
                step4.complete(False, str(e))
            
            self.report.add_step(step4)
            
            if not step4.success:
                logger.error("由于前序步骤失败，测试终止")
                self.report.complete_test()
                return False
            
            # 步骤5: 点击辽阳市兴宇纸业有限公司-管理端
            step5 = UITestStep("点击按钮", "定位并点击辽阳市兴宇纸业有限公司-管理端按钮")
            step5.start()
            
            try:
                # 等待一段时间确保页面上的所有元素都已加载
                await asyncio.sleep(2)
                
                # 使用缓存方法查找目标元素
                target_element_index, cache_time = await self.measure_performance(
                    context,
                    self.find_element_by_text_cached,
                    (context, "辽阳市兴宇纸业有限公司", None, False, True)
                )
                
                # 如果没有找到，尝试更宽松的搜索
                if target_element_index is None:
                    logger.info("尝试更宽松的搜索方式查找目标元素")
                    target_element_index, additional_time = await self.measure_performance(
                        context,
                        self.find_element_by_text_cached,
                        (context, "兴宇纸业", None, False, True)
                    )
                    cache_time += additional_time
                
                # 如果找不到，尝试在缓存中查找含有相关关键词的元素
                if target_element_index is None:
                    logger.warning("未找到目标元素，尝试在缓存中查找相关元素")
                    
                    page = await context.get_current_page()
                    current_url = page.url
                    cached_elements = await self.get_cached_elements(context, current_url)
                    
                    # 在缓存中查找相关元素
                    search_terms = ["纸业", "辽阳", "管理"]
                    for idx, element in cached_elements.items():
                        text = element.get('text', '')
                        if element.get('is_interactive', False):
                            if any(term.lower() in text.lower() for term in search_terms):
                                logger.info(f"使用宽松匹配找到可能的目标元素: {text}")
                                target_element_index = idx
                                break
                
                if target_element_index is None:
                    raise Exception("未找到'辽阳市兴宇纸业有限公司-管理端'或相关元素")
                
                # 记录性能数据
                self.report.total_time += cache_time
                
                # 点击目标元素
                logger.info(f"尝试点击元素索引 {target_element_index}")
                await controller.registry.execute_action("click_element", {"index": target_element_index}, context)
                logger.info("已点击目标元素")
                
                # 等待页面跳转完成
                logger.info("等待页面跳转完成")
                page = await context.get_current_page()
                await page.wait_for_load_state()
                await asyncio.sleep(3)  # 额外等待以确保跳转后的页面完全加载
                
                # 刷新缓存获取新页面元素
                current_url = page.url
                await context.cache_manager.get_elements_with_cache(current_url, force_refresh=True)
                
                step5.complete(True)
            except Exception as e:
                step5.complete(False, str(e))
            
            self.report.add_step(step5)
            
            if not step5.success:
                logger.error("由于前序步骤失败，测试终止")
                self.report.complete_test()
                return False
            
            # 步骤6: 验证页面包含文本"首页"
            step6 = UITestStep("验证页面内容", "验证页面包含文本'首页'")
            step6.start()
            
            try:
                # 使用缓存方法验证
                home_text_index, cache_time = await self.measure_performance(
                    context,
                    self.find_element_by_text_cached,
                    (context, "首页", None, False, False)
                )
                
                # 记录性能数据
                self.report.total_time += cache_time
                
                # 验证结果
                if home_text_index is None:
                    raise Exception("页面不包含文本'首页'")
                
                logger.info("验证成功: 页面包含文本'首页'")
                step6.complete(True)
            except Exception as e:
                step6.complete(False, str(e))
            
            self.report.add_step(step6)
            
            # 完成测试并生成报告
            success = self.report.complete_test()
            return success
            
        except Exception as e:
            logger.error(f"执行测试任务时发生错误: {str(e)}")
            self.report.complete_test()
            return False
        finally:
            # 关闭浏览器
            await browser.close()
            logger.info("测试浏览器已关闭")

async def batch_run_tests(num_runs=1):
    """批量运行测试多次以获取更稳定的性能数据"""
    logger.info(f"开始批量运行缓存UI测试 ({num_runs}次)...")
    
    success_count = 0
    tester = CachedUITester()
    
    for i in range(num_runs):
        logger.info(f"\n运行测试 #{i+1}/{num_runs}")
        success = await tester.run_ui_test()
        if success:
            success_count += 1
    
    success_rate = (success_count / num_runs) * 100
    logger.info(f"\n批量测试完成: 成功率 {success_rate:.2f}% ({success_count}/{num_runs})")

if __name__ == "__main__":
    # 创建缓存目录
    os.makedirs("ui_test_cache", exist_ok=True)
    
    # 运行UI测试
    tester = CachedUITester()
    asyncio.run(tester.run_ui_test())
    
    # 批量运行测试以获取更稳定的性能数据
    # asyncio.run(batch_run_tests(1))  # 默认运行1次，可以增加次数以获取更稳定的数据 