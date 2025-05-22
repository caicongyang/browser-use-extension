#!/usr/bin/env python3
"""
Test script for demonstrating enhanced UI actions using our custom implementation with LLM integration
"""
import asyncio
import logging
from pathlib import Path
import sys
import os
import json
import argparse
import traceback
import time
from typing import Dict, Any, List, Optional, Tuple
import subprocess

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径
current_dir = Path(__file__).resolve().parent  # examples目录
parent_dir = current_dir.parent  # browser-use-extension目录
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))
sys.path.insert(0, os.path.dirname(parent_dir))  # 项目根目录

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 导入我们自己的增强UI操作系统
from browser_use.controller.service import Controller
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.agent.views import ActionResult

# 导入增强UI模块
from element_enhance.ui_registry.action_registry import EnhancedUIRegistry, create_enhanced_ui_registry
from element_enhance.ui_enhanced.ui_enhanced_actions import (
    EnhancedUIActionProvider,
    ResilientClickParams,
    PageActionParams,
    InputTextParams,
    ElementDiagnosticParams,
    FindElementParams
)

# 导入浏览器上下文扩展
from element_enhance.browser_extension.context_extension import extend_browser_context

# 从enhanced_example_test.py导入辅助函数
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

# LLM集成
def get_llm(provider: str = 'deepseek'):
    """获取指定的LLM模型"""
    if provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Error: ANTHROPIC_API_KEY is not set. Please provide a valid API key.")

        return ChatAnthropic(
            model="claude-3-5-sonnet-20240620", 
            temperature=0.0,
            max_tokens=4000
        )
    elif provider == 'openai':
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Error: OPENAI_API_KEY is not set. Please provide a valid API key.")

        return ChatOpenAI(
            model='gpt-4o', 
            temperature=0.0,
            max_tokens=4000
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
        if not base_url:
            raise ValueError("Error: DEEPSEEK_BASE_URL is not set. Please provide a valid base URL.")

        return ChatOpenAI(
            base_url=base_url,
            model='deepseek-chat', 
            api_key=SecretStr(api_key),
            temperature=0.0
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
        default='点击Google搜索框，输入Python automation，然后按回车键。'
    )
    parser.add_argument(
        '--provider',
        type=str,
        choices=['openai', 'anthropic', 'deepseek'],
        default='deepseek',
        help='要使用的LLM提供商 (默认: deepseek)',
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='是否使用无头模式运行浏览器'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=60,
        help='操作超时时间（秒）'
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
        default='ui_cache',
        help='缓存目录路径'
    )
    return parser.parse_args()

class EnhancedUITester:
    """
    增强的UI测试器，使用LLM和增强UI操作来执行浏览器自动化
    """
    def __init__(self, task: str, headless=False, timeout=60, llm_provider='deepseek', cache_dir='ui_cache'):
        """
        初始化测试器
        
        参数:
            task: 要执行的任务描述
            headless: 是否使用无头模式
            timeout: 超时时间（秒）
            llm_provider: LLM提供商
            cache_dir: 缓存目录
        """
        self.task = task
        self.headless = headless
        self.timeout = timeout
        self.cache_dir = cache_dir
        self.llm_provider = llm_provider
        self.browser = None
        self.browser_context = None
        self.enhanced_registry = None
        self.llm = None
        
    async def setup(self):
        """设置浏览器环境和增强UI操作"""
        # 创建浏览器实例
        browser_config = BrowserConfig(headless=self.headless)
        self.browser = Browser(config=browser_config)
        self.browser_context = await self.browser.new_context()
        
        # 扩展浏览器上下文以支持缓存
        self.browser_context = extend_browser_context(self.browser_context, cache_dir=self.cache_dir)
        
        # 创建增强UI注册表
        self.enhanced_registry = create_enhanced_ui_registry()
        
        # 注册所有增强UI操作
        EnhancedUIActionProvider.register_to_registry(self.enhanced_registry)
        
        # 初始化LLM
        try:
            self.llm = get_llm(self.llm_provider)
            logger.info(f"LLM模型 ({self.llm_provider}) 初始化成功")
        except Exception as e:
            logger.error(f"LLM初始化失败: {e}")
            self.llm = None
            
        logger.info("浏览器环境和增强UI操作已设置")
        
    async def navigate_to(self, url):
        """导航到指定URL"""
        goto_params = {"url": url}
        await self.enhanced_registry.execute_action(
            "go_to_url", 
            goto_params, 
            browser=self.browser_context
        )
        
        # 等待页面加载
        wait_params = PageActionParams(
            action_type="wait",
            wait_time=3
        )
        await self.enhanced_registry.execute_action(
            "enhanced_page_action", 
            to_dict(wait_params), 
            browser=self.browser_context
        )
        logger.info(f"已导航到 {url}")
        
    async def prompt(self, instructions):
        """
        使用LLM分析指令并执行UI自动化操作
        
        参数:
            instructions: 自然语言指令
            
        返回:
            执行结果
        """
        logger.info(f"执行指令: {instructions}")
        
        # 如果没有LLM，回退到简单的关键词匹配
        if not self.llm:
            logger.warning("LLM不可用，使用简单关键词匹配")
            return await self._execute_with_keyword_matching(instructions)
        
        # 使用LLM分析指令
        try:
            instruction_analysis = await self._analyze_instruction(instructions)
            if not instruction_analysis:
                logger.warning("LLM分析失败，回退到关键词匹配")
                return await self._execute_with_keyword_matching(instructions)
                
            # 执行LLM分析的操作
            result = await self._execute_llm_actions(instruction_analysis)
            return result
        except Exception as e:
            logger.error(f"LLM指令执行失败: {e}")
            logger.info("回退到关键词匹配")
            traceback.print_exc()
            return await self._execute_with_keyword_matching(instructions)
    
    async def _analyze_instruction(self, instruction):
        """使用LLM分析指令"""
        from langchain_core.messages import HumanMessage, SystemMessage
        
        system_prompt = """
你是一个专业的浏览器自动化助手，你的任务是分析用户的指令并将其转换为具体的浏览器操作步骤。

可用的浏览器操作有：
1. enhanced_resilient_click - 智能点击操作，能处理各种复杂情况
2. enhanced_input_text - 增强的文本输入操作
3. enhanced_page_action - 页面操作（滚动、等待、刷新等）
4. enhanced_find_element - 智能元素查找
5. enhanced_element_diagnostic - 元素诊断工具

你需要提供以下JSON格式的操作序列：
```json
{
  "actions": [
    {
      "action": "操作名称",
      "params": {
        "参数1": "值1",
        "参数2": "值2"
      },
      "description": "这个操作的目的描述"
    }
  ]
}
```

每个操作的参数说明：

1. enhanced_resilient_click:
   - selector: CSS选择器（可选）
   - text: 要点击的文本内容（可选） 
   - index: 元素索引（可选）
   - max_attempts: 最大尝试次数
   - verify_navigation: 是否验证点击后的导航

2. enhanced_input_text:
   - selector: CSS选择器（可选）
   - text: 要输入的文本
   - clear_first: 是否先清除现有内容

3. enhanced_page_action:
   - action_type: 操作类型(wait/refresh/scroll)
   - wait_time: 等待时间(秒)
   - scroll_direction: 滚动方向(up/down/top/bottom)
   - scroll_amount: 滚动量(像素)

4. enhanced_find_element:
   - text: 要查找的文本（可选）
   - tag: HTML标签（可选）
   - selector: CSS选择器（可选）
   - visible_only: 是否只查找可见元素

5. enhanced_element_diagnostic:
   - selector: CSS选择器（可选）
   - text: 元素文本（可选）
   - index: 元素索引（可选）

仅输出JSON格式的结果，不要包含其他解释。确保生成的JSON是有效的，且每个操作的参数与上述说明一致。
        """
        
        try:
            # 发送消息到LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=instruction)
            ]
            
            response = await self.llm.ainvoke(messages)
            response_text = response.content
            
            # 提取JSON内容
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_text = response_text.split("```")[1].strip()
            else:
                json_text = response_text.strip()
                
            # 解析JSON
            try:
                instruction_data = json.loads(json_text)
                logger.info(f"LLM分析成功: {len(instruction_data.get('actions', []))}个操作")
                return instruction_data
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                logger.debug(f"JSON文本: {json_text}")
                return None
                
        except Exception as e:
            logger.error(f"LLM分析指令失败: {e}")
            return None
    
    async def _execute_llm_actions(self, instruction_data):
        """执行LLM分析的操作"""
        if not instruction_data or "actions" not in instruction_data:
            return "LLM分析结果格式不正确"
            
        actions = instruction_data["actions"]
        results = []
        
        for idx, action_data in enumerate(actions):
            action_name = action_data.get("action")
            params = action_data.get("params", {})
            description = action_data.get("description", "")
            
            logger.info(f"执行操作 {idx+1}/{len(actions)}: {action_name} - {description}")
            
            try:
                # 映射操作名称到实际的注册名称
                registry_action_name = action_name
                if not action_name.startswith("enhanced_") and action_name not in ["go_to_url"]:
                    registry_action_name = f"enhanced_{action_name}"
                
                # 执行操作
                result = await self.enhanced_registry.execute_action(
                    registry_action_name,
                    params,
                    browser=self.browser_context
                )
                
                # 记录结果
                success = getattr(result, "success", True)
                message = getattr(result, "extracted_content", str(result))
                
                results.append({
                    "action": action_name,
                    "success": success,
                    "message": message
                })
                
                logger.info(f"操作结果: {'成功' if success else '失败'} - {message}")
                
                # 如果操作失败，记录错误并继续
                if not success:
                    error_message = getattr(result, "error_message", "未知错误")
                    logger.error(f"操作失败: {error_message}")
                    
            except Exception as e:
                logger.error(f"执行操作 {action_name} 时发生错误: {e}")
                results.append({
                    "action": action_name,
                    "success": False,
                    "message": str(e)
                })
        
        # 返回操作结果摘要
        success_count = sum(1 for r in results if r.get("success", False))
        return f"执行了 {len(results)} 个操作，成功 {success_count} 个，失败 {len(results) - success_count} 个"
    
    async def _execute_with_keyword_matching(self, instructions):
        """使用关键词匹配执行指令"""
        logger.info("使用关键词匹配解析指令")
        
        # 解析指令中的关键词，执行基本操作
        if "点击" in instructions or "click" in instructions.lower():
            # 尝试点击搜索框（对于Google）
            if "搜索框" in instructions or "search" in instructions.lower():
                try:
                    click_params = ResilientClickParams(
                        selector="input[name='q']",
                        max_attempts=3
                    )
                    result = await self.enhanced_registry.execute_action(
                        "enhanced_resilient_click", 
                        to_dict(click_params), 
                        browser=self.browser_context
                    )
                    logger.info("已尝试点击搜索框")
                    
                    # 如果需要输入文本
                    if "输入" in instructions or "input" in instructions.lower() or "type" in instructions.lower():
                        # 从指令中提取要输入的文本
                        search_text = "Python automation"  # 默认文本
                        input_params = InputTextParams(
                            selector="input[name='q']",
                            text=search_text,
                            clear_first=True
                        )
                        await self.enhanced_registry.execute_action(
                            "enhanced_input_text", 
                            to_dict(input_params), 
                            browser=self.browser_context
                        )
                        logger.info(f"已输入文本: {search_text}")
                        
                        # 如果需要按回车键
                        if "回车" in instructions or "enter" in instructions.lower():
                            page = await self.browser_context.get_current_page()
                            await page.keyboard.press("Enter")
                            logger.info("已按回车键")
                except Exception as e:
                    logger.error(f"点击搜索框失败: {e}")
            
            # 尝试点击Sign in按钮（对于GitHub）
            elif "sign in" in instructions.lower():
                try:
                    click_params = ResilientClickParams(
                        text="Sign in",
                        max_attempts=3
                    )
                    result = await self.enhanced_registry.execute_action(
                        "enhanced_resilient_click", 
                        to_dict(click_params), 
                        browser=self.browser_context
                    )
                    logger.info("已尝试点击Sign in按钮")
                except Exception as e:
                    logger.error(f"点击Sign in按钮失败: {e}")
        
        # 处理滚动操作
        elif "滚动" in instructions or "scroll" in instructions.lower():
            scroll_direction = "down"
            if "顶部" in instructions or "top" in instructions.lower():
                scroll_direction = "top"
            elif "底部" in instructions or "bottom" in instructions.lower():
                scroll_direction = "bottom"
            elif "上" in instructions or "up" in instructions.lower():
                scroll_direction = "up"
            
            try:
                scroll_params = PageActionParams(
                    action_type="scroll",
                    scroll_direction=scroll_direction,
                    scroll_amount=500
                )
                await self.enhanced_registry.execute_action(
                    "enhanced_page_action", 
                    to_dict(scroll_params), 
                    browser=self.browser_context
                )
                logger.info(f"已滚动页面: {scroll_direction}")
                
                # 如果需要等待
                if "等待" in instructions or "wait" in instructions.lower():
                    wait_time = 2  # 默认等待2秒
                    wait_params = PageActionParams(
                        action_type="wait",
                        wait_time=wait_time
                    )
                    await self.enhanced_registry.execute_action(
                        "enhanced_page_action", 
                        to_dict(wait_params), 
                        browser=self.browser_context
                    )
                    logger.info(f"已等待 {wait_time} 秒")
            except Exception as e:
                logger.error(f"滚动页面失败: {e}")
        
        # 处理诊断操作
        elif "诊断" in instructions or "diagnostic" in instructions.lower():
            try:
                # 尝试获取当前页面的第一个可见链接
                page = await self.browser_context.get_current_page()
                first_link = await page.query_selector("a:visible")
                if first_link:
                    # 获取DOM元素状态
                    dom_state = await self.browser_context.get_state()
                    if dom_state and dom_state.selector_map:
                        # 假设第一个元素是我们想要的
                        element_index = list(dom_state.selector_map.keys())[0]
                        diagnostic_params = ElementDiagnosticParams(
                            index=element_index
                        )
                        result = await self.enhanced_registry.execute_action(
                            "enhanced_element_diagnostic", 
                            to_dict(diagnostic_params), 
                            browser=self.browser_context
                        )
                        logger.info("已执行元素诊断")
                        return f"元素诊断结果: {result.extracted_content if hasattr(result, 'extracted_content') else str(result)}"
                    else:
                        logger.warning("未获取到DOM状态")
                else:
                    logger.warning("未找到可诊断的元素")
            except Exception as e:
                logger.error(f"元素诊断失败: {e}")
                import traceback
                traceback.print_exc()
                
        # 处理等待操作        
        elif "等待" in instructions or "wait" in instructions.lower():
            try:
                wait_time = 2  # 默认等待2秒
                wait_params = PageActionParams(
                    action_type="wait",
                    wait_time=wait_time
                )
                await self.enhanced_registry.execute_action(
                    "enhanced_page_action", 
                    to_dict(wait_params), 
                    browser=self.browser_context
                )
                logger.info(f"已等待 {wait_time} 秒")
            except Exception as e:
                logger.error(f"等待操作失败: {e}")
        
        return "操作已执行完成"
        
    async def execute_action(self, action_name, params):
        """
        直接执行特定的增强UI操作
        
        参数:
            action_name: 操作名称
            params: 操作参数
        """
        result = await self.enhanced_registry.execute_action(
            action_name, 
            params, 
            browser=self.browser_context
        )
        return result
        
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")

async def test_resilient_click():
    """测试增强的点击功能"""
    args = parse_arguments()
    tester = EnhancedUITester(
        task=args.task,
        headless=args.headless, 
        timeout=args.timeout,
        llm_provider=args.provider,
        cache_dir=args.cache_dir
    )
    try:
        await tester.setup()
        
        # 导航到测试页面
        logger.info("导航到测试页面...")
        await tester.navigate_to("https://www.google.com")
        
        # 使用智能点击尝试点击搜索框
        logger.info("执行增强点击操作...")
        results = await tester.prompt(
            "使用增强的resilient_click操作点击搜索框，然后输入'Python automation'，"
            "然后按回车键。分析点击是否成功，如果遇到问题，请使用element_diagnostic帮助诊断。"
        )
        logger.info(f"执行结果: {results}")
        
        # 尝试页面操作
        logger.info("执行页面操作...")
        await tester.prompt(
            "使用enhanced_page_action滚动到页面底部，等待2秒，然后再滚动回页面顶部。"
        )
        
        # 元素诊断
        logger.info("执行元素诊断...")
        await tester.prompt(
            "对搜索结果页的第一个链接元素执行enhanced_element_diagnostic诊断，"
            "并分析元素是否可点击，如果遇到任何问题，提供详细的诊断信息。"
        )
        
    finally:
        logger.info("测试完成，关闭浏览器...")
        await tester.close()

async def test_complex_interaction():
    """测试复杂的交互场景"""
    args = parse_arguments()
    tester = EnhancedUITester(
        task=args.task,
        headless=args.headless, 
        timeout=args.timeout,
        llm_provider=args.provider,
        cache_dir=args.cache_dir
    )
    try:
        await tester.setup()
        
        # 导航到GitHub
        logger.info("导航到GitHub...")
        await tester.navigate_to("https://github.com")
        
        # 执行复杂操作序列
        logger.info("执行复杂交互...")
        instructions = """
        请执行以下任务:
        1. 使用enhanced_resilient_click找到并点击"Sign in"按钮
        2. 在登录页面，使用enhanced_element_diagnostic诊断用户名输入框的状态
        3. 使用enhanced_page_action返回首页
        4. 在首页滚动到"The complete developer platform"部分
        5. 分析该部分是否存在动画元素，如果有，请提供诊断信息
        """
        results = await tester.prompt(instructions)
        logger.info(f"执行结果: {results}")
        
    finally:
        logger.info("测试完成，关闭浏览器...")
        await tester.close()

async def main():
    """主函数"""
    logger.info("===== 启动增强UI操作测试 =====")
    try:
        await test_resilient_click()
        # 等待一会儿再运行下一个测试
        await asyncio.sleep(2)
        await test_complex_interaction()
        logger.info("===== 增强UI操作测试完成 =====")
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 