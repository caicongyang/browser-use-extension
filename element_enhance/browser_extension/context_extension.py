"""
浏览器上下文扩展模块

这个模块扩展了基础的BrowserContext类，添加了元素缓存功能，
用于提高页面元素访问性能和可靠性。主要功能包括：
1. 元素缓存管理
2. DOM元素状态维护
3. 页面导航跟踪
"""
import logging
import os
import sys
from typing import Dict, Any, Optional

# 添加当前目录的父目录到Python路径，确保能够正确导入相关模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from browser_use.browser.context import BrowserContext
from browser_use.dom.views import DOMElementNode
from cache.element_cache import ElementCache
from cache.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class ExtendedBrowserContext(BrowserContext):
    """
    扩展的浏览器上下文类
    
    这个类扩展了基础的BrowserContext，添加了元素缓存和管理功能，
    用于优化页面元素的访问性能和可靠性。
    
    主要功能：
    1. 元素缓存管理
    2. 智能元素查找
    3. 缓存状态维护
    """
    
    def __init__(self, original_context: BrowserContext, cache_dir: str):
        """
        初始化扩展的浏览器上下文
        
        参数:
            original_context: 原始的浏览器上下文实例
            cache_dir: 缓存目录路径
        """
        # 继承原始context的所有属性
        self.__dict__.update(original_context.__dict__)
        
        # 初始化缓存相关组件
        self.element_cache = ElementCache(cache_dir=cache_dir)
        self.cache_manager = CacheManager(self.element_cache, self)
        
        # 保存原始的元素获取方法，用于回退
        self._original_get_dom_element_by_index = self.get_dom_element_by_index
    
    async def get_dom_element_by_index_with_cache(self, index: int) -> Optional[DOMElementNode]:
        """
        使用缓存机制获取DOM元素
        
        参数:
            index: 元素索引
            
        返回:
            DOMElementNode: DOM元素节点对象
            None: 如果元素不存在或获取失败
            
        工作流程：
        1. 获取当前页面URL
        2. 尝试从缓存获取元素
        3. 如果缓存命中，构建并返回DOM元素节点
        4. 如果缓存未命中，使用原始方法获取
        """
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
            # 设置文本内容
            if hasattr(element_node, 'set_text'):
                element_node.set_text(element_data.get('text', ''))
            elif hasattr(element_node, '_text'):
                element_node._text = element_data.get('text', '')
            
            logger.info(f"从缓存获取元素: index={index}")
            return element_node
        
        # 缓存未命中，使用原始方法
        logger.info(f"缓存中未找到元素 index={index}，使用标准方法")
        return await self._original_get_dom_element_by_index(index)
    
    async def _get_current_url(self) -> str:
        """
        获取当前页面的URL
        
        返回:
            str: 当前页面的URL
        """
        page = await self.get_current_page()
        return page.url
    
    async def initialize_cache(self, urls: list) -> None:
        """
        初始化元素缓存
        
        为指定的URL列表预先建立元素缓存，提高后续访问性能。
        
        参数:
            urls: 要缓存的URL列表
            
        工作流程：
        1. 遍历URL列表
        2. 访问每个URL
        3. 等待页面加载
        4. 获取并缓存页面元素
        """
        for url in urls:
            logger.info(f"初始化缓存: {url}")
            # 导航到URL
            page = await self.get_current_page()
            await page.goto(url)
            # 等待页面加载完成
            await page.wait_for_load_state()
            # 获取并缓存元素
            await self.cache_manager.get_elements_with_cache(url, force_refresh=True)

def extend_browser_context(browser_context: BrowserContext, cache_dir: str = "cache_data") -> BrowserContext:
    """
    创建扩展的浏览器上下文实例
    
    这是一个工厂函数，用于创建ExtendedBrowserContext实例。
    
    参数:
        browser_context: 原始的浏览器上下文实例
        cache_dir: 缓存目录路径，默认为"cache_data"
        
    返回:
        ExtendedBrowserContext: 扩展后的浏览器上下文实例
    """
    return ExtendedBrowserContext(browser_context, cache_dir) 