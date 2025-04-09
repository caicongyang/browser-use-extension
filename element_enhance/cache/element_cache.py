import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class ElementCache:
    """元素缓存类，管理URL到元素映射的存储和检索"""
    
    def __init__(self, cache_dir: str = "cache_data"):
        """
        初始化元素缓存
        
        Args:
            cache_dir: 缓存文件存储目录
        """
        self.cache_dir = cache_dir
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
        # 加载缓存元数据
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """加载缓存元数据"""
        metadata_file = os.path.join(self.cache_dir, "metadata.json")
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    self.metadata = json.load(f)
                logger.info(f"已加载缓存元数据，共 {len(self.metadata)} 个条目")
            except Exception as e:
                logger.error(f"加载缓存元数据失败: {str(e)}")
                self.metadata = {}
    
    def _save_metadata(self) -> None:
        """保存缓存元数据"""
        metadata_file = os.path.join(self.cache_dir, "metadata.json")
        try:
            with open(metadata_file, 'w') as f:
                json.dump(self.metadata, f)
        except Exception as e:
            logger.error(f"保存缓存元数据失败: {str(e)}")
    
    def _get_cache_file(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        import hashlib
        filename = hashlib.md5(cache_key.encode()).hexdigest() + ".json"
        return os.path.join(self.cache_dir, filename)
    
    def _generate_cache_key(self, url: str, params: Optional[Dict[str, str]] = None) -> str:
        """生成缓存键"""
        if not params:
            return url
        
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{url}?{param_str}"
    
    def _create_locator(self, element_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建定位器对象"""
        locator = {
            "type": "xpath",  # 默认类型
            "value": element_data.get("xpath", ""),
            "priority": 1
        }
        
        # 根据元素属性选择最佳定位器类型
        attributes = element_data.get("attributes", {})
        
        if "id" in attributes and attributes["id"]:
            return {"type": "id", "value": attributes["id"], "priority": 1}
        elif "class" in attributes and attributes["class"]:
            return {"type": "css", "value": f".{attributes['class'].split()[0]}", "priority": 2}
        elif "role" in attributes and attributes["role"]:
            return {"type": "role", "value": attributes["role"], "priority": 3}
        elif "name" in attributes and attributes["name"]:
            return {"type": "name", "value": attributes["name"], "priority": 4}
        
        return locator
    
    def _create_element_entry(self, element_data: Dict[str, Any], element_name: str) -> Dict[str, Any]:
        """创建元素条目"""
        return {
            "description": element_name,
            "locators": [self._create_locator(element_data)],
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "success_rate": 1.0
        }
    
    def _group_elements_by_domain(self, elements: Dict[str, Any], url: str) -> Dict[str, Any]:
        """按域名对元素进行分组"""
        from urllib.parse import urlparse
        
        domain = urlparse(url).netloc
        grouped_elements = {
            "common": {},  # 通用元素
            domain: {}    # 特定域名的元素
        }
        
        for index, element_data in elements.items():
            element_name = element_data.get("text", f"element_{index}")
            element_entry = self._create_element_entry(element_data, element_name)
            
            # 根据元素特征决定分组
            if self._is_common_element(element_data):
                grouped_elements["common"][element_name] = element_entry
            else:
                grouped_elements[domain][element_name] = element_entry
        
        return grouped_elements
    
    def _is_common_element(self, element_data: Dict[str, Any]) -> bool:
        """判断是否为通用元素"""
        common_attributes = {"id", "class", "name", "type", "role"}
        attributes = element_data.get("attributes", {})
        
        # 检查是否包含通用属性
        has_common_attr = any(attr in attributes for attr in common_attributes)
        
        # 检查是否为常见元素类型
        common_tags = {"button", "input", "a", "div", "span", "form"}
        tag_name = element_data.get("tag_name", "").lower()
        
        return has_common_attr or tag_name in common_tags
    
    def get_elements(self, url: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        获取URL对应的元素
        
        Args:
            url: 页面URL
            params: URL参数
            
        Returns:
            元素字典
        """
        cache_key = self._generate_cache_key(url, params)
        
        # 检查内存缓存
        if cache_key in self.cache:
            logger.debug(f"从内存缓存获取元素: {cache_key}")
            return self.cache[cache_key]
        
        # 检查文件缓存
        cache_file = self._get_cache_file(cache_key)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    elements = cache_data.get("elements", {})
                    # 更新内存缓存
                    self.cache[cache_key] = elements
                    logger.info(f"从文件缓存加载元素: {cache_key}, 共 {len(elements)} 个元素")
                    return elements
            except Exception as e:
                logger.error(f"加载缓存文件失败: {str(e)}")
        
        return {}
    
    def store_elements(self, url: str, elements: Dict[str, Any], params: Optional[Dict[str, str]] = None) -> None:
        """
        存储URL对应的元素
        
        Args:
            url: 页面URL
            elements: 元素字典
            params: URL参数
        """
        cache_key = self._generate_cache_key(url, params)
        
        # 更新内存缓存
        self.cache[cache_key] = elements
        
        # 更新元数据
        import time
        self.metadata[cache_key] = {
            "url": url,
            "timestamp": time.time(),
            "element_count": len(elements),
            "version": self.metadata.get(cache_key, {}).get("version", 0) + 1
        }
        self._save_metadata()
        
        # 创建缓存数据结构
        cache_data = {
            "metadata": {
                "url": url,
                "timestamp": time.time(),
                "element_count": len(elements)
            },
            "elements": elements
        }
        
        # 保存到文件
        cache_file = self._get_cache_file(cache_key)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info(f"已缓存 {len(elements)} 个元素到 {cache_key}")
        except Exception as e:
            logger.error(f"保存缓存文件失败: {str(e)}")
    
    def get_all_urls(self) -> list:
        """获取所有缓存的URL"""
        return [meta.get("url") for meta in self.metadata.values() if "url" in meta]
    
    def get_cache_info(self, url: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """获取缓存信息"""
        cache_key = self._generate_cache_key(url, params)
        return self.metadata.get(cache_key, {})
    
    def clear_cache(self, url: Optional[str] = None, params: Optional[Dict[str, str]] = None) -> None:
        """
        清除缓存
        
        Args:
            url: 如果指定，只清除该URL的缓存；否则清除所有缓存
            params: URL参数
        """
        if url:
            cache_key = self._generate_cache_key(url, params)
            if cache_key in self.cache:
                del self.cache[cache_key]
            
            if cache_key in self.metadata:
                del self.metadata[cache_key]
                self._save_metadata()
            
            cache_file = self._get_cache_file(cache_key)
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                    logger.info(f"已清除缓存: {cache_key}")
                except Exception as e:
                    logger.error(f"清除缓存文件失败: {str(e)}")
        else:
            # 清除所有缓存
            self.cache = {}
            self.metadata = {}
            self._save_metadata()
            
            # 删除缓存文件
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".json"):
                    try:
                        os.remove(os.path.join(self.cache_dir, filename))
                    except Exception as e:
                        logger.error(f"删除缓存文件失败: {filename}, {str(e)}")
            
            logger.info("已清除所有缓存") 