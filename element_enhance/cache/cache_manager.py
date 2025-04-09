import time
import logging
import asyncio
from typing import Dict, Any, List, Tuple, Set, Optional

from browser_use.browser.context import BrowserContext
from browser_use.dom.views import DOMElementNode
from .element_cache import ElementCache

logger = logging.getLogger(__name__)

class CacheManager:
    """缓存管理器，处理缓存的更新策略和验证"""
    
    def __init__(self, element_cache: ElementCache, browser_context: BrowserContext):
        """
        初始化缓存管理器
        
        Args:
            element_cache: 元素缓存实例
            browser_context: 浏览器上下文实例
        """
        self.cache = element_cache
        self.browser_context = browser_context
        self.cache_ttl = 24 * 60 * 60  # 缓存有效期（秒）
        self.validation_sample_size = 3  # 验证时抽样的元素数量
    
    async def get_elements_with_cache(self, url: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取元素，优先使用缓存
        
        Args:
            url: 页面URL
            force_refresh: 是否强制刷新缓存
            
        Returns:
            元素字典
        """
        current_url = await self._get_current_url()
        params = self._extract_url_params(current_url)
        
        # 检查是否需要刷新缓存
        if force_refresh or self._should_refresh_cache(url, params):
            logger.info(f"刷新缓存: {url}")
            # 获取新的元素数据
            elements = await self._fetch_fresh_elements()
            # 存储到缓存
            self.cache.store_elements(url, elements, params)
            return elements
        
        # 获取缓存
        cached_elements = self.cache.get_elements(url, params)
        
        # 如果缓存为空，获取新数据
        if not cached_elements:
            logger.info(f"缓存为空，获取新数据: {url}")
            elements = await self._fetch_fresh_elements()
            self.cache.store_elements(url, elements, params)
            return elements
        
        # 验证缓存
        is_valid = await self.validate_cache(url, cached_elements)
        if not is_valid:
            logger.info(f"缓存验证失败，更新缓存: {url}")
            # 差异化更新缓存
            updated_elements = await self.update_cache_with_diff(url, cached_elements)
            return updated_elements
        
        logger.info(f"使用缓存: {url}, 共 {len(cached_elements)} 个元素")
        return cached_elements
    
    def _should_refresh_cache(self, url: str, params: Optional[Dict[str, str]] = None) -> bool:
        """
        判断是否应该刷新缓存
        
        Args:
            url: 页面URL
            params: URL参数
            
        Returns:
            如果应该刷新缓存则返回True
        """
        # 获取缓存信息
        cache_info = self.cache.get_cache_info(url, params)
        
        # 如果没有缓存信息，需要刷新
        if not cache_info:
            return True
        
        # 检查缓存是否过期
        timestamp = cache_info.get("timestamp", 0)
        current_time = time.time()
        return (current_time - timestamp) > self.cache_ttl
    
    async def _get_current_url(self) -> str:
        """获取当前URL"""
        page = await self.browser_context.get_current_page()
        return page.url
    
    def _extract_url_params(self, url: str) -> Dict[str, str]:
        """
        提取URL参数
        
        Args:
            url: 完整URL
            
        Returns:
            参数字典
        """
        if '?' not in url:
            return {}
        
        query_string = url.split('?', 1)[1]
        params = {}
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
        
        return params
    
    async def _fetch_fresh_elements(self) -> Dict[str, Any]:
        """
        获取新的元素数据
        
        Returns:
            元素字典
        """
        # 使用DOM服务获取元素
        dom_state = await self.browser_context.get_state()
        
        # 转换为可序列化格式
        elements = {}
        
        # 转换选择器映射
        for index, element in dom_state.selector_map.items():
            # 创建定位器
            locators = {}
            
            # XPath定位器
            if element.xpath:
                locators['xpath'] = element.xpath
            
            # ID定位器
            if element.attributes and 'id' in element.attributes:
                locators['id'] = element.attributes['id']
            
            # CSS选择器
            if element.attributes and 'class' in element.attributes:
                class_selector = f"{element.tag_name}.{element.attributes['class'].replace(' ', '.')}"
                locators['css'] = class_selector
            
            # 创建元素条目
            elements[str(index)] = {
                "locators": locators,
                "attributes": element.attributes,
                "tag_name": element.tag_name,
                "text": element.get_all_text_till_next_clickable_element(),
                "is_visible": element.is_visible,
                "is_clickable": element.is_interactive
            }
        
        return elements
    
    async def validate_cache(self, url: str, cached_elements: Dict[str, Any]) -> bool:
        """
        验证缓存是否仍然有效
        
        Args:
            url: 页面URL
            cached_elements: 缓存的元素
            
        Returns:
            如果缓存有效则返回True
        """
        page = await self.browser_context.get_current_page()
        
        # 选择几个关键元素进行验证
        sample_indices = self._select_validation_samples(cached_elements)
        
        valid_count = 0
        for index in sample_indices:
            element_data = cached_elements[index]
            
            # 尝试定位元素
            try:
                selector = self._create_selector_from_cache(element_data)
                element = await page.query_selector(selector)
                
                if element:
                    valid_count += 1
                else:
                    logger.debug(f"验证失败: 找不到元素 {index}, 选择器: {selector}")
            except Exception as e:
                logger.debug(f"验证异常: {str(e)}")
        
        # 如果大部分样本都有效，则认为缓存有效
        validity_ratio = valid_count / len(sample_indices) if sample_indices else 0
        logger.info(f"缓存验证结果: {valid_count}/{len(sample_indices)} 有效, 比例: {validity_ratio:.2f}")
        
        return validity_ratio >= 0.7  # 70% 的样本有效则认为缓存有效
    
    def _select_validation_samples(self, cached_elements: Dict[str, Any]) -> List[str]:
        """
        选择用于验证的样本元素
        
        Args:
            cached_elements: 缓存的元素
            
        Returns:
            样本元素索引列表
        """
        indices = list(cached_elements.keys())
        
        # 如果元素数量少于样本大小，返回所有元素
        if len(indices) <= self.validation_sample_size:
            return indices
        
        # 优先选择可能是关键元素的索引
        # 这里简单实现为选择前几个元素，实际应用中可以使用更智能的选择策略
        return indices[:self.validation_sample_size]
    
    def _create_selector_from_cache(self, element_data: Dict[str, Any]) -> str:
        """
        从缓存数据创建选择器
        
        Args:
            element_data: 元素数据
            
        Returns:
            CSS选择器
        """
        # 尝试使用ID
        attributes = element_data.get('attributes', {})
        if 'id' in attributes and attributes['id']:
            return f"#{attributes['id']}"
        
        # 使用标签名和其他属性
        tag_name = element_data.get('tag_name', '*')
        selector = tag_name
        
        # 添加关键属性
        for attr in ['name', 'type', 'role', 'aria-label']:
            if attr in attributes and attributes[attr]:
                value = attributes[attr].replace('"', '\\"')
                selector += f'[{attr}="{value}"]'
        
        # 如果有class，添加第一个class
        if 'class' in attributes and attributes['class']:
            classes = attributes['class'].split()
            if classes:
                selector += f'.{classes[0]}'
        
        return selector
    
    async def update_cache_with_diff(self, url: str, cached_elements: Dict[str, Any]) -> Dict[str, Any]:
        """
        差异化更新缓存
        
        Args:
            url: 页面URL
            cached_elements: 缓存的元素
            
        Returns:
            更新后的元素字典
        """
        # 获取当前页面元素
        current_elements = await self._fetch_fresh_elements()
        
        # 计算差异
        added, modified, removed = self._compute_diff(cached_elements, current_elements)
        
        # 更新缓存
        updated_cache = cached_elements.copy()
        
        # 添加新元素
        for index in added:
            updated_cache[index] = current_elements[index]
        
        # 更新修改的元素
        for index in modified:
            updated_cache[index] = current_elements[index]
        
        # 移除不存在的元素
        for index in removed:
            del updated_cache[index]
        
        # 存储更新后的缓存
        params = self._extract_url_params(url)
        self.cache.store_elements(url, updated_cache, params)
        
        logger.info(f"缓存差异更新: 添加 {len(added)}, 修改 {len(modified)}, 删除 {len(removed)}")
        
        return updated_cache
    
    def _compute_diff(self, old_elements: Dict[str, Any], new_elements: Dict[str, Any]) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        计算两个元素集合的差异
        
        Args:
            old_elements: 旧元素集合
            new_elements: 新元素集合
            
        Returns:
            (添加的元素索引, 修改的元素索引, 删除的元素索引)
        """
        old_keys = set(old_elements.keys())
        new_keys = set(new_elements.keys())
        
        added = new_keys - old_keys
        removed = old_keys - new_keys
        
        # 检查修改的元素
        modified = set()
        for key in old_keys.intersection(new_keys):
            if self._is_element_modified(old_elements[key], new_elements[key]):
                modified.add(key)
        
        return added, modified, removed
    
    def _is_element_modified(self, old_element: Dict[str, Any], new_element: Dict[str, Any]) -> bool:
        """
        判断元素是否被修改
        
        Args:
            old_element: 旧元素
            new_element: 新元素
            
        Returns:
            如果元素被修改则返回True
        """
        # 比较关键属性
        key_attrs = ['xpath', 'tag_name', 'is_interactive']
        
        for attr in key_attrs:
            if old_element.get(attr) != new_element.get(attr):
                return True
        
        # 比较HTML属性
        old_attrs = old_element.get('attributes', {})
        new_attrs = new_element.get('attributes', {})
        
        # 检查关键属性是否变化
        important_attrs = ['id', 'class', 'name', 'type']
        for attr in important_attrs:
            if old_attrs.get(attr) != new_attrs.get(attr):
                return True
        
        return False 