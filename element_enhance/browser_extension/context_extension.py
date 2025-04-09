import logging
import os
import sys
from typing import Dict, Any, Optional

# 添加当前目录的父目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from browser_use.browser.context import BrowserContext
from browser_use.dom.views import DOMElementNode
from cache.element_cache import ElementCache
from cache.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class ExtendedBrowserContext(BrowserContext):
    """扩展的BrowserContext类，添加缓存功能"""
    
    def __init__(self, original_context: BrowserContext, cache_dir: str):
        # 继承原始context的所有属性
        self.__dict__.update(original_context.__dict__)
        
        # 添加缓存相关属性
        self.element_cache = ElementCache(cache_dir=cache_dir)
        self.cache_manager = CacheManager(self.element_cache, self)
        
        # 保存原始方法
        self._original_get_dom_element_by_index = self.get_dom_element_by_index
    
    async def get_dom_element_by_index_with_cache(self, index: int) -> Optional[DOMElementNode]:
        """使用缓存获取DOM元素"""
        current_url = await self._get_current_url()
        
        # 尝试从缓存获取元素
        cached_elements = await self.cache_manager.get_elements_with_cache(current_url)
        
        if str(index) in cached_elements:
            # 使用缓存的元素信息创建DOM元素节点
            element_data = cached_elements[str(index)]
            # 创建基本的DOM元素节点
            element_node = DOMElementNode(
                tag_name=element_data.get('tag_name', 'div'),
                xpath=element_data.get('xpath', ''),
                attributes=element_data.get('attributes', {}),
                children=[],  # 简化处理，不包含子元素
                is_visible=element_data.get('is_visible', True),
                is_interactive=element_data.get('is_interactive', True),
                is_in_viewport=element_data.get('is_in_viewport', True),
                highlight_index=element_data.get('highlight_index', index),
                parent=None
            )
            # 设置文本内容（如果DOMElementNode有相应的方法）
            if hasattr(element_node, 'set_text'):
                element_node.set_text(element_data.get('text', ''))
            elif hasattr(element_node, '_text'):
                element_node._text = element_data.get('text', '')
            
            logger.info(f"从缓存获取元素: index={index}")
            return element_node
        
        # 缓存中没有找到，回退到标准方法
        logger.info(f"缓存中未找到元素 index={index}，使用标准方法")
        return await self._original_get_dom_element_by_index(index)
    
    async def _get_current_url(self) -> str:
        """获取当前URL"""
        page = await self.get_current_page()
        return page.url
    
    async def initialize_cache(self, urls: list) -> None:
        """
        初始化元素缓存
        
        Args:
            urls: 要缓存的URL列表
        """
        for url in urls:
            logger.info(f"初始化缓存: {url}")
            # 导航到URL
            page = await self.get_current_page()
            await page.goto(url)
            # 等待页面加载
            await page.wait_for_load_state()
            # 获取并缓存元素
            await self.cache_manager.get_elements_with_cache(url, force_refresh=True)

def extend_browser_context(browser_context: BrowserContext, cache_dir: str = "cache_data") -> BrowserContext:
    """
    扩展BrowserContext，添加缓存功能
    
    Args:
        browser_context: 原始BrowserContext实例
        cache_dir: 缓存目录
        
    Returns:
        扩展后的BrowserContext实例
    """
    return ExtendedBrowserContext(browser_context, cache_dir) 