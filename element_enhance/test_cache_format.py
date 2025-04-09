import os
import logging
from typing import Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 导入Browser类和缓存管理相关类
from browser_use.browser.browser import Browser
from cache.element_cache import ElementCache
from cache.cache_manager import CacheManager

class RealPageCacheDemo:
    """实际页面缓存演示类"""

    def __init__(self, target_url: str = "https://hy-sit.1233s2b.com", cache_dir: str = "cache_data_0317_004"):
        """
        初始化实际页面缓存演示
        :param target_url: 目标网页URL
        :param cache_dir: 缓存目录
        """
        self.target_url = target_url
        self.cache_dir = cache_dir
        self.browser = None
        self.context = None
        
        # 初始化缓存相关组件
        self.element_cache = ElementCache(cache_dir)
        
        # 确保缓存目录存在
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    async def setup_browser(self):
        """设置浏览器"""
        logger.info("启动浏览器...")
        self.browser = Browser()
        self.context = await self.browser.new_context()
        
        # 初始化缓存管理器
        self.cache_manager = CacheManager(self.element_cache, self.context)
            
    async def close_browser(self):
        """关闭浏览器"""
        logger.info("关闭浏览器...")
        if self.browser:
            await self.browser.close()
            
    async def fetch_and_cache_elements(self) -> Dict[str, Any]:
        """
        获取并缓存页面元素
        :return: 页面元素
        """
        logger.info(f"打开页面并获取元素: {self.target_url}")
        
        # 获取当前页面
        page = await self.context.get_current_page()
        if not page:
            logger.error("无法获取页面")
            return {}
            
        await page.goto(self.target_url)
        await page.wait_for_load_state()
        
        # 使用缓存管理器获取元素（会自动处理缓存逻辑）
        elements = await self.cache_manager.get_elements_with_cache(self.target_url)
        
        return elements
                
    def print_cache_content(self):
        """打印缓存内容"""
        # 获取缓存信息
        cache_info = self.element_cache.get_cache_info(self.target_url)
        
        if cache_info:
            logger.info(f"缓存元数据:")
            logger.info(f"  URL: {cache_info.get('url')}")
            logger.info(f"  元素数量: {cache_info.get('element_count')}")
            logger.info(f"  版本: {cache_info.get('version')}")
            
            # 获取元素数据
            elements = self.element_cache.get_elements(self.target_url)
            
            # 打印样例元素
            logger.info(f"样例元素:")
            for element_id, element_data in list(elements.items())[:3]:  # 只打印前3个元素作为样例
                logger.info(f"  元素 {element_id}:")
                logger.info(f"    定位器: {element_data.get('locators')}")
                logger.info(f"    标签: {element_data.get('tag_name')}")
                
                # 文本内容
                text = element_data.get('text', '')
                if text:
                    # 截断长文本，确保中文显示正常
                    display_text = text[:30] + "..." if len(text) > 30 else text
                    logger.info(f"    文本: {display_text}")
                else:
                    logger.info(f"    文本: ")
        else:
            logger.info(f"未找到缓存信息")
                
    async def run_demo(self):
        """运行演示"""
        logger.info("开始实际页面缓存演示...")
        
        try:
            # 设置浏览器
            await self.setup_browser()
            
            # 获取并缓存页面元素
            elements = await self.fetch_and_cache_elements()
            
            # 打印缓存内容
            self.print_cache_content()
            
            logger.info(f"演示完成，共处理 {len(elements)} 个元素")
            
        except Exception as e:
            logger.error(f"演示运行失败: {str(e)}")
            # 打印异常详细信息
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # 关闭浏览器
            await self.close_browser()

# 运行演示
if __name__ == "__main__":
    import sys
    import asyncio
    
    # 获取命令行参数中的URL（如果提供）
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://hy-sit.1233s2b.com"
    
    # 创建演示实例，传入目标URL
    demo = RealPageCacheDemo(target_url=target_url)
    asyncio.run(demo.run_demo()) 