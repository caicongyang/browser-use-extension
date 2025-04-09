#!/usr/bin/env python3
"""
Test script for demonstrating enhanced UI actions
"""
import asyncio
import logging
from pathlib import Path
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from examples.element_enhance.llm_ui_tester import LLMUITester

async def test_resilient_click():
    """测试增强的点击功能"""
    tester = LLMUITester(headless=False, timeout=60)
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
            "使用page_action滚动到页面底部，等待2秒，然后再滚动回页面顶部。"
        )
        
        # 元素诊断
        logger.info("执行元素诊断...")
        await tester.prompt(
            "对搜索结果页的第一个链接元素执行element_diagnostic诊断，"
            "并分析元素是否可点击，如果遇到任何问题，提供详细的诊断信息。"
        )
        
    finally:
        logger.info("测试完成，关闭浏览器...")
        await tester.close()

async def test_complex_interaction():
    """测试复杂的交互场景"""
    tester = LLMUITester(headless=False, timeout=60)
    try:
        await tester.setup()
        
        # 导航到GitHub
        logger.info("导航到GitHub...")
        await tester.navigate_to("https://github.com")
        
        # 执行复杂操作序列
        logger.info("执行复杂交互...")
        instructions = """
        请执行以下任务:
        1. 使用resilient_click找到并点击"Sign in"按钮
        2. 在登录页面，使用element_diagnostic诊断用户名输入框的状态
        3. 使用page_action返回首页
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
    await test_resilient_click()
    # 等待一会儿再运行下一个测试
    await asyncio.sleep(2)
    await test_complex_interaction()

if __name__ == "__main__":
    asyncio.run(main()) 