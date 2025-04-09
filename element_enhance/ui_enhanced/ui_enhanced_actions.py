"""
UI增强操作模块

这个模块提供了一系列增强的UI操作实现，用于处理Web界面的各种交互场景。
主要功能包括：
1. 智能文本输入
2. 增强型元素查找
3. 智能点击操作
4. 页面操作控制
5. 元素诊断

每个操作都经过优化，能够处理各种边缘情况和异常情况。
"""
import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from browser_use.agent.views import ActionResult
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 操作参数模型定义
class InputTextParams(BaseModel):
    """
    文本输入操作参数模型
    
    属性:
        index: 目标元素的索引，可选
        text: 要输入的文本内容
        selector: CSS选择器，用于定位元素，可选
        wait_time: 输入后的等待时间（毫秒）
        clear_first: 是否在输入前清除现有内容
    """
    index: Optional[int] = Field(None, description="元素索引")
    text: str = Field("", description="要输入的文本")
    selector: Optional[str] = Field(None, description="CSS选择器（可选）")
    wait_time: int = Field(0, description="输入后等待时间（毫秒）")
    clear_first: bool = Field(False, description="是否先清除现有内容")

class FindElementParams(BaseModel):
    """
    元素查找操作参数模型
    
    属性:
        text: 要查找的文本内容
        tag: HTML标签名
        exact: 是否进行精确匹配
        selector: CSS选择器
        role: ARIA角色
        name: 元素名称或标签
        timeout: 查找超时时间（秒）
        visible_only: 是否只查找可见元素
        interactive_only: 是否只查找可交互元素
    """
    text: Optional[str] = Field(None, description="要查找的文本")
    tag: Optional[str] = Field(None, description="HTML标签")
    exact: bool = Field(False, description="是否精确匹配")
    selector: Optional[str] = Field(None, description="CSS选择器")
    role: Optional[str] = Field(None, description="ARIA角色")
    name: Optional[str] = Field(None, description="元素名称/标签")
    timeout: int = Field(5, description="超时时间(秒)")
    visible_only: bool = Field(True, description="是否只查找可见元素")
    interactive_only: bool = Field(False, description="是否只查找可交互元素")

class PageActionParams(BaseModel):
    """
    页面操作参数模型
    
    属性:
        wait_time: 等待时间（秒）
        action_type: 操作类型（wait/refresh/scroll）
        scroll_direction: 滚动方向（up/down/top/bottom）
        scroll_amount: 滚动距离（像素）
        wait_for_selector: 等待特定选择器出现
        wait_for_navigation: 是否等待页面导航完成
    """
    wait_time: int = Field(5, description="等待时间(秒)")
    action_type: str = Field("wait", description="操作类型(wait/refresh/scroll)")
    scroll_direction: Optional[str] = Field(None, description="滚动方向(up/down/top/bottom)")
    scroll_amount: int = Field(300, description="滚动量(像素)")
    wait_for_selector: Optional[str] = Field(None, description="等待特定选择器出现")
    wait_for_navigation: bool = Field(False, description="是否等待导航完成")

class ResilientClickParams(BaseModel):
    """
    增强型点击操作参数模型
    
    属性:
        index: 目标元素索引
        selector: CSS选择器
        text: 要点击的文本内容
        role: ARIA角色
        name: 元素名称
        max_attempts: 最大尝试次数
        force: 是否强制点击
        verify_navigation: 是否验证点击后的导航
        wait_for_selector: 点击后等待的选择器
    """
    index: Optional[int] = Field(None, description="元素索引")
    selector: Optional[str] = Field(None, description="CSS选择器（可选）")
    text: Optional[str] = Field(None, description="要点击的文本内容（可选）")
    role: Optional[str] = Field(None, description="ARIA角色（可选）")
    name: Optional[str] = Field(None, description="元素名称（可选）")
    max_attempts: int = Field(3, description="最大尝试次数")
    force: bool = Field(False, description="是否强制点击")
    verify_navigation: bool = Field(False, description="是否验证点击后的导航")
    wait_for_selector: Optional[str] = Field(None, description="点击后等待此选择器出现")

class ElementDiagnosticParams(BaseModel):
    """
    元素诊断操作参数模型
    
    属性:
        index: 目标元素索引
        selector: CSS选择器
        text: 元素文本内容
    """
    index: Optional[int] = Field(None, description="元素索引")
    selector: Optional[str] = Field(None, description="CSS选择器（可选）")
    text: Optional[str] = Field(None, description="元素文本（可选）")

@dataclass
class ActionResponse:
    """
    操作响应数据类
    
    属性:
        success: 操作是否成功
        message: 操作结果消息
        page_state_changed: 页面状态是否改变
        data: 附加数据
    """
    success: bool
    message: str
    page_state_changed: bool = False
    data: Optional[Any] = None

    @classmethod
    def from_result(cls, success: bool, message: str, data: Any = None, 
                   page_state_changed: bool = False) -> 'ActionResponse':
        """创建ActionResponse实例的工厂方法"""
        return cls(success=success, message=str(message), 
                  data=data, page_state_changed=page_state_changed)

class ElementHelper:
    """
    元素操作辅助类
    提供了一系列用于处理Web元素的实用方法
    """
    
    @staticmethod
    async def is_hidden(element) -> bool:
        """
        检查元素是否隐藏
        
        检查方式：
        1. 元素的hidden属性
        2. CSS样式（display: none, visibility: hidden）
        3. 元素的可见性标志
        """
        if hasattr(element, 'is_hidden') and element.is_hidden:
            return True
        if hasattr(element, 'attributes'):
            style = element.attributes.get('style', '').lower()
            if 'display: none' in style or 'visibility: hidden' in style:
                return True
            if element.attributes.get('hidden') is not None:
                return True
        return False

    @staticmethod
    async def get_element(context, index: int):
        """
        通过索引获取元素
        
        参数:
            context: 浏览器上下文
            index: 元素索引
        """
        try:
            dom_state = await context.get_state()
            return dom_state.selector_map.get(index)
        except Exception as e:
            logger.error(f"获取元素失败: {e}")
            return None
            
    @staticmethod
    async def find_by_text(context, text: str, exact: bool = False, tag: Optional[str] = None, 
                          timeout: int = 5) -> Optional[int]:
        """通过文本内容查找元素，支持重试和模糊匹配"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                dom_state = await context.get_state()
                for index, element in dom_state.selector_map.items():
                    if await ElementHelper.is_hidden(element):
                        continue
                    if tag and element.tag_name.lower() != tag.lower():
                        continue
                        
                    element_text = ""
                    if hasattr(element, 'get_all_text_till_next_clickable_element'):
                        element_text = element.get_all_text_till_next_clickable_element()
                    elif hasattr(element, 'text'):
                        element_text = element.text
                    elif hasattr(element, 'attributes') and 'innerText' in element.attributes:
                        element_text = element.attributes['innerText']
                    
                    if exact:
                        # 精确匹配，规范化文本
                        cleaned_element_text = ' '.join(element_text.split())
                        cleaned_search_text = ' '.join(text.split())
                        if cleaned_element_text == cleaned_search_text:
                            return index
                    else:
                        # 模糊匹配
                        if text.lower() in element_text.lower():
                            return index
            except Exception as e:
                logger.warning(f"文本查找失败: {e}")
                
            # 等待一段时间后重试    
            await asyncio.sleep(0.5)
            
        return None
    
    @staticmethod
    async def find_by_role(context, role: str, name: Optional[str] = None, timeout: int = 5) -> Optional[int]:
        """通过ARIA角色和名称查找元素"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                dom_state = await context.get_state()
                for index, element in dom_state.selector_map.items():
                    if await ElementHelper.is_hidden(element):
                        continue
                        
                    # 检查角色
                    element_role = ""
                    if hasattr(element, 'attributes'):
                        element_role = element.attributes.get('role', '')
                    
                    if element_role.lower() != role.lower():
                        continue
                        
                    # 如果指定了名称，检查名称匹配
                    if name:
                        element_name = ""
                        if hasattr(element, 'get_all_text_till_next_clickable_element'):
                            element_name = element.get_all_text_till_next_clickable_element()
                        elif hasattr(element, 'attributes') and 'aria-label' in element.attributes:
                            element_name = element.attributes['aria-label']
                            
                        if name.lower() not in element_name.lower():
                            continue
                            
                    return index
            except Exception as e:
                logger.warning(f"角色查找失败: {e}")
                
            await asyncio.sleep(0.5)
            
        return None
        
    @staticmethod
    async def find_by_selector(context, selector: str, timeout: int = 5) -> Optional[int]:
        """通过CSS选择器查找元素"""
        page = await context.get_current_page()
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 检查选择器是否匹配元素
                element_exists = await page.evaluate(f"""
                    () => {{
                        const el = document.querySelector('{selector}');
                        return el !== null;
                    }}
                """)
                
                if element_exists:
                    # 获取元素XPath
                    xpath = await page.evaluate(f"""
                        () => {{
                            const getElementXPath = function(element) {{
                                if (element.id)
                                    return `//*[@id="${{element.id}}"]`;
                                    
                                if (element === document.body)
                                    return '/html/body';

                                let ix = 0;
                                const siblings = element.parentNode.childNodes;
                                for (let i = 0; i < siblings.length; i++) {{
                                    const sibling = siblings[i];
                                    if (sibling === element)
                                        return `${{getElementXPath(element.parentNode)}}/${{element.tagName.toLowerCase()}}[${{ix+1}}]`;
                                    if (sibling.nodeType === 1 && sibling.tagName.toLowerCase() === element.tagName.toLowerCase())
                                        ix++;
                                }}
                            }};
                            
                            const el = document.querySelector('{selector}');
                            return el ? getElementXPath(el) : null;
                        }}
                    """)
                    
                    if xpath:
                        # 遍历DOM状态中的元素，查找匹配XPath的元素
                        dom_state = await context.get_state()
                        for index, element in dom_state.selector_map.items():
                            if hasattr(element, 'xpath') and element.xpath == xpath:
                                return index
                
            except Exception as e:
                logger.warning(f"选择器查找失败: {e}")
                
            await asyncio.sleep(0.5)
            
        return None
        
    @staticmethod
    async def resilient_locate(context, params: Dict[str, Any], max_attempts: int = 3) -> Optional[int]:
        """增强的元素定位方法，使用多种定位策略"""
        # 提取定位参数
        selector = params.get('selector', '')
        text = params.get('text', '')
        role = params.get('role', '')
        name = params.get('name', '')
        tag = params.get('tag', '')
        index = params.get('index', None)
        exact = params.get('exact', False)
        
        # 如果提供了索引，直接返回
        if index is not None:
            try:
                index_int = int(index)
                element = await ElementHelper.get_element(context, index_int)
                if element:
                    return index_int
            except (ValueError, TypeError):
                pass
        
        # 定义定位策略顺序
        strategies = []
        
        # 1. 选择器策略（如果提供）
        if selector:
            strategies.append(lambda: ElementHelper.find_by_selector(context, selector))
            
        # 2. 角色策略（如果提供）
        if role:
            strategies.append(lambda: ElementHelper.find_by_role(context, role, name))
            
        # 3. 文本策略（如果提供）
        if text:
            strategies.append(lambda: ElementHelper.find_by_text(context, text, exact, tag))
            
        # 如果没有定义任何策略，返回None
        if not strategies:
            return None
            
        # 执行定位策略
        for attempt in range(max_attempts):
            for strategy in strategies:
                try:
                    element_index = await strategy()
                    if element_index is not None:
                        return element_index
                except Exception as e:
                    logger.warning(f"定位策略失败: {e}")
                    
            # 等待后重试
            if attempt < max_attempts - 1:
                await asyncio.sleep(1)
                
        return None

# 转换ActionResponse为ActionResult
def action_response_to_result(response: ActionResponse) -> ActionResult:
    """将ActionResponse转换为ActionResult"""
    return ActionResult(
        success=response.success,
        error_message="" if response.success else response.message,
        extracted_content=response.message if response.success else "",
        metadata=response.data
    )

# UIEnhancedActions 包含注册所有增强操作的方法
class EnhancedUIActionImplementations:
    """UI增强操作实现类"""
    
    @staticmethod
    def register_actions(controller) -> None:
        """注册所有增强的UI操作"""
        logger.info("开始注册UI增强操作")
        
        # 这里将改为使用装饰器模式，但实际的装饰器调用将在实际应用时进行
        
        # 定义并返回所有要注册的操作方法
        actions = {
            "input_text": {"func": input_text_action, "params": InputTextParams},
            "find_element": {"func": find_element_action, "params": FindElementParams},
            "page_action": {"func": page_action, "params": PageActionParams},
            "resilient_click": {"func": resilient_click_action, "params": ResilientClickParams},
            "element_diagnostic": {"func": element_diagnostic_action, "params": ElementDiagnosticParams},
        }
        
        # 返回所有注册的操作
        return actions

# 下面是各个独立的操作函数，不再嵌套在类中

async def input_text_action(params: InputTextParams, browser) -> ActionResult:
    """文本输入操作"""
    try:
        context = browser.context
        # 获取元素索引
        index = params.index
        text = params.text
        
        if not text:
            return ActionResult(success=False, error_message="未指定文本")
        
        # 使用增强的定位方法查找元素
        if index is None:
            index = await ElementHelper.resilient_locate(context, params.dict(exclude_unset=True))
            if index is None:
                return ActionResult(success=False, error_message="使用所有定位方法均未找到元素")
        
        element = await ElementHelper.get_element(context, index)
        if not element:
            return ActionResult(success=False, error_message="未找到元素")

        page = await context.get_current_page()
        
        # 检查是否需要先清除内容
        if params.clear_first:
            try:
                await page.evaluate("""
                    selector => {
                        const el = document.querySelector(selector);
                        if (el) {
                            el.value = '';
                            el.dispatchEvent(new Event('input', {bubbles:true}));
                        }
                    }
                """, element.selector)
            except Exception as e:
                logger.warning(f"清除内容失败: {e}")

        # 尝试不同的输入方法
        if await _try_input_methods(page, element, text, context, params.dict()):
            if params.wait_time > 0:
                await asyncio.sleep(params.wait_time / 1000.0)  # 转换为秒
            
            return ActionResult(
                success=True,
                extracted_content=f"输入成功: {text}",
                metadata={"element_index": index}
            )
        
        return ActionResult(success=False, error_message="所有输入方法都失败")
    except Exception as e:
        logger.error(f"输入操作失败: {e}", exc_info=True)
        return ActionResult(success=False, error_message=f"输入失败: {str(e)}")

async def _try_input_methods(page, element, text: str, context, params: Dict[str, Any]) -> bool:
    """尝试多种输入方法"""
    # 添加更多输入方法
    methods = [
        _try_fill,
        _try_click_type,
        _try_js_input,
        _try_click_select_type,
        _try_direct_input,
        _try_focused_input
    ]
    
    # 尝试每种方法
    for method in methods:
        try:
            logger.debug(f"尝试输入方法: {method.__name__}")
            if await method(page, element, text, context, params):
                logger.info(f"输入方法 {method.__name__} 成功")
                return True
        except Exception as e:
            logger.warning(f"{method.__name__} 失败: {e}")
            
        # 每次尝试后等待一小段时间
        await asyncio.sleep(0.1)
        
    return False

async def _try_click_type(page, element, text: str, context, params) -> bool:
    """点击并输入"""
    try:
        # 确保元素在视图中并且可交互
        await _ensure_visible(page, element)
        
        # 尝试点击元素
        await page.click(element.selector, timeout=3000)
        # 延迟确保点击事件已处理
        await asyncio.sleep(0.2)
        # 输入文本
        await page.keyboard.type(text)
        return True
    except Exception as e:
        logger.debug(f"点击输入失败: {e}")
        return False

async def _try_fill(page, element, text: str, context, params) -> bool:
    """使用fill方法"""
    try:
        # 确保元素在视图中
        await _ensure_visible(page, element)
        
        # 尝试填充
        await page.fill(element.selector, text, timeout=3000)
        return True
    except Exception as e:
        logger.debug(f"fill方法失败: {e}")
        return False

async def _try_js_input(page, element, text: str, context, params) -> bool:
    """使用JavaScript输入"""
    try:
        # 使用JavaScript设置值并触发事件
        text_escaped = text.replace("'", "\\'")
        await page.evaluate(f"""
            selector => {{
                const el = document.querySelector(selector);
                if (el) {{
                    el.value = '{text_escaped}';
                    el.dispatchEvent(new Event('input', {{bubbles:true}}));
                    el.dispatchEvent(new Event('change', {{bubbles:true}}));
                    return true;
                }}
                return false;
            }}
        """, element.selector)
        return True
    except Exception as e:
        logger.debug(f"JavaScript输入失败: {e}")
        return False
            
async def _try_click_select_type(page, element, text: str, context, params) -> bool:
    """点击全选再输入"""
    try:
        # 确保元素在视图中
        await _ensure_visible(page, element)
        
        # 点击元素
        await page.click(element.selector, timeout=3000)
        await asyncio.sleep(0.1)
        
        # 全选当前内容
        if hasattr(context, 'platform') and context.platform == 'darwin':
            await page.keyboard.press('Meta+A')  # macOS
        else:
            await page.keyboard.press('Control+A')  # Windows/Linux
            
        await asyncio.sleep(0.1)
        
        # 输入新内容
        await page.keyboard.type(text)
        return True
    except Exception as e:
        logger.debug(f"点击全选输入失败: {e}")
        return False
            
async def _try_direct_input(page, element, text: str, context, params) -> bool:
    """直接输入不点击"""
    try:
        # 使用type方法直接输入
        await page.type(element.selector, text, timeout=3000)
        return True
    except Exception as e:
        logger.debug(f"直接输入失败: {e}")
        return False
            
async def _try_focused_input(page, element, text: str, context, params) -> bool:
    """强制聚焦后输入"""
    try:
        # 使用JavaScript强制聚焦
        await page.evaluate(f"""
            selector => {{
                const el = document.querySelector(selector);
                if (el) {{
                    el.focus();
                    return true;
                }}
                return false;
            }}
        """, element.selector)
        
        await asyncio.sleep(0.1)
        
        # 直接键入
        await page.keyboard.type(text)
        return True
    except Exception as e:
        logger.debug(f"强制聚焦输入失败: {e}")
        return False
            
async def _ensure_visible(page, element) -> None:
    """确保元素在视图中"""
    try:
        # 检查元素是否在视图中，如果不在则滚动到元素
        await page.evaluate(f"""
            selector => {{
                const el = document.querySelector(selector);
                if (el) {{
                    // 获取元素的位置信息
                    const rect = el.getBoundingClientRect();
                    
                    // 检查元素是否在视图中
                    const isInViewport = 
                        rect.top >= 0 &&
                        rect.left >= 0 &&
                        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                        rect.right <= (window.innerWidth || document.documentElement.clientWidth);
                    
                    // 如果不在视图中，滚动到元素
                    if (!isInViewport) {{
                        el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        return false;
                    }}
                    return true;
                }}
                return false;
            }}
        """, element.selector)
        
        # 给滚动一点时间完成
        await asyncio.sleep(0.3)
    except Exception as e:
        logger.warning(f"确保元素可见失败: {e}")

async def find_element_action(params: FindElementParams, browser) -> ActionResult:
    """元素查找操作"""
    try:
        context = browser.context
        # 使用增强的定位方法
        element_index = await ElementHelper.resilient_locate(context, params.dict(exclude_unset=True))
        
        if element_index is not None:
            element = await ElementHelper.get_element(context, element_index)
            
            # 检查元素可见性（如果需要）
            if params.visible_only and await ElementHelper.is_hidden(element):
                return ActionResult(success=False, error_message="找到的元素不可见")
                
            # 检查元素可交互性（如果需要）
            if params.interactive_only and not getattr(element, 'is_interactive', False):
                return ActionResult(success=False, error_message="找到的元素不可交互")
            
            # 构建结果数据
            element_data = {
                "index": element_index,
                "tag_name": getattr(element, 'tag_name', ''),
                "text": getattr(element, 'text', ''),
                "xpath": getattr(element, 'xpath', ''),
                "selector": getattr(element, 'selector', ''),
                "is_interactive": getattr(element, 'is_interactive', False),
                "attributes": getattr(element, 'attributes', {})
            }
            
            return ActionResult(
                success=True,
                extracted_content="找到元素",
                metadata=element_data
            )
        
        # 如果常规方法失败，尝试高级查找策略
        element_index = await _advanced_find(context, params.dict(exclude_unset=True))
        if element_index is not None:
            element = await ElementHelper.get_element(context, element_index)
            element_data = {
                "index": element_index,
                "tag_name": getattr(element, 'tag_name', ''),
                "text": getattr(element, 'text', ''),
                "xpath": getattr(element, 'xpath', ''),
                "selector": getattr(element, 'selector', ''),
                "is_interactive": getattr(element, 'is_interactive', False),
                "attributes": getattr(element, 'attributes', {})
            }
            return ActionResult(
                success=True, 
                extracted_content="使用高级策略找到元素",
                metadata=element_data
            )
        
        return ActionResult(success=False, error_message="未找到元素")
    except Exception as e:
        logger.error(f"查找元素失败: {e}", exc_info=True)
        return ActionResult(success=False, error_message=f"查找失败: {str(e)}")

async def _advanced_find(context, params: Dict[str, Any]) -> Optional[int]:
    """高级元素查找策略"""
    page = await context.get_current_page()
    text = params.get("text", "")
    tag = params.get("tag", "")
    
    try:
        # 使用深度搜索JavaScript来查找匹配元素
        if text:
            text_escaped = text.replace("'", "\\'")
            js_result = await page.evaluate(f"""
                () => {{
                    // 深度优先搜索函数
                    function deepSearch(root, predicate) {{
                        const matches = [];
                        function traverse(node) {{
                            if (predicate(node)) matches.push(node);
                            for (const child of node.children) traverse(child);
                        }}
                        traverse(root);
                        return matches;
                    }}
                    
                    // 检查元素是否可见
                    function isVisible(el) {{
                        if (!el) return false;
                        
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0')
                            return false;
                            
                        const rect = el.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0)
                            return false;
                            
                        return true;
                    }}
                    
                    // 构建搜索条件
                    const searchText = '{text_escaped}';
                    const searchTag = '{tag.lower() if tag else ""}';
                    
                    // 搜索谓词
                    const predicate = node => {{
                        // 检查文本内容
                        const nodeText = node.innerText || node.textContent || '';
                        const hasText = searchText ? nodeText.toLowerCase().includes(searchText.toLowerCase()) : true;
                        
                        // 检查标签
                        const hasTag = searchTag ? node.tagName.toLowerCase() === searchTag : true;
                        
                        // 检查可见性
                        const isNodeVisible = isVisible(node);
                        
                        return hasText && hasTag && isNodeVisible;
                    }};
                    
                    // 执行搜索
                    const matches = deepSearch(document.body, predicate);
                    
                    // 如果找到匹配元素，返回XPath
                    if (matches.length > 0) {{
                        // 获取元素XPath
                        const getElementXPath = function(element) {{
                            if (element.id !== '')
                                return `//*[@id="${{element.id}}"]`;
                                
                            if (element === document.body)
                                return '/html/body';

                            let ix = 0;
                            const siblings = element.parentNode.childNodes;
                            for (let i = 0; i < siblings.length; i++) {{
                                const sibling = siblings[i];
                                if (sibling === element)
                                    return `${{getElementXPath(element.parentNode)}}/${{element.tagName.toLowerCase()}}[${{ix+1}}]`;
                                if (sibling.nodeType === 1 && sibling.tagName.toLowerCase() === element.tagName.toLowerCase())
                                    ix++;
                            }}
                        }};
                        
                        return getElementXPath(matches[0]);
                    }}
                    
                    return null;
                }}
            """)
            
            if js_result:
                # 通过XPath找到对应的元素索引
                dom_state = await context.get_state()
                for index, element in dom_state.selector_map.items():
                    if hasattr(element, 'xpath') and element.xpath == js_result:
                        return index
    except Exception as e:
        logger.warning(f"高级查找失败: {e}")
        
    return None

async def page_action(params: PageActionParams, browser) -> ActionResult:
    """页面操作"""
    try:
        context = browser.context
        page = await context.get_current_page()
        action_type = params.action_type.lower()
        
        if action_type == "wait":
            # 等待操作
            wait_time = params.wait_time
            wait_selector = params.wait_for_selector
            
            if wait_selector:
                try:
                    # 等待特定选择器出现
                    await page.wait_for_selector(wait_selector, timeout=wait_time * 1000)
                    return ActionResult(
                        success=True, 
                        extracted_content=f"已等待选择器 {wait_selector} 出现"
                    )
                except Exception as e:
                    return ActionResult(success=False, error_message=f"等待选择器超时: {str(e)}")
            else:
                # 通用等待
                try:
                    # 等待网络空闲
                    await page.wait_for_load_state("networkidle", timeout=wait_time * 1000)
                except Exception:
                    logger.warning("等待网络空闲超时")
                
                # 增加小延迟确保DOM更新
                await asyncio.sleep(min(1, wait_time))
                
                try:
                    # 等待DOM内容加载
                    await page.wait_for_load_state("domcontentloaded", timeout=wait_time * 1000)
                except Exception:
                    logger.warning("等待DOM加载超时")
                
                return ActionResult(success=True, extracted_content="页面等待完成")
        
        elif action_type == "refresh":
            # 刷新页面
            await page.reload()
            # 等待加载完成
            await page.wait_for_load_state("domcontentloaded")
            return ActionResult(success=True, extracted_content="页面已刷新")
        
        elif action_type == "scroll":
            # 滚动操作
            direction = params.scroll_direction
            if not direction:
                direction = "down"
            direction = direction.lower()
            
            amount = params.scroll_amount
            
            if direction == "up":
                amount = -amount
            elif direction == "top":
                # 滚动到顶部
                await page.evaluate("window.scrollTo(0, 0);")
                return ActionResult(success=True, extracted_content="已滚动到页面顶部")
            elif direction == "bottom":
                # 滚动到底部
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                return ActionResult(success=True, extracted_content="已滚动到页面底部")
            
            # 执行滚动
            await page.evaluate(f"window.scrollBy(0, {amount});")
            return ActionResult(success=True, extracted_content=f"已滚动 {amount} 像素")
        
        # 如果操作类型无效，返回错误
        return ActionResult(success=False, error_message=f"无效的操作类型: {action_type}")
    except Exception as e:
        logger.error(f"页面操作失败: {e}", exc_info=True)
        return ActionResult(success=False, error_message=f"页面操作失败: {str(e)}")

async def resilient_click_action(params: ResilientClickParams, browser) -> ActionResult:
    """增强型点击操作"""
    try:
        context = browser.context
        # 获取元素索引
        index = params.index
        
        # 使用增强的定位方法查找元素
        if index is None:
            index = await ElementHelper.resilient_locate(context, params.dict(exclude_unset=True))
            if index is None:
                return ActionResult(success=False, error_message="使用所有定位方法均未找到元素")
        
        element = await ElementHelper.get_element(context, index)
        if not element:
            return ActionResult(success=False, error_message="未找到元素")
        
        page = await context.get_current_page()
        max_attempts = params.max_attempts
        force = params.force
        
        # 尝试点击元素
        for attempt in range(max_attempts):
            try:
                # 确保元素在视图中
                await _ensure_visible(page, element)
                
                # 尝试不同的点击方法
                click_success = await _try_click_methods(page, element, force, context)
                
                if click_success:
                    # 如果需要验证导航
                    if params.verify_navigation:
                        try:
                            await page.wait_for_navigation(timeout=5000)
                        except Exception:
                            logger.warning("等待导航超时")
                    
                    # 如果需要等待特定选择器
                    wait_selector = params.wait_for_selector
                    if wait_selector:
                        try:
                            await page.wait_for_selector(wait_selector, timeout=5000)
                        except Exception:
                            logger.warning(f"等待选择器 {wait_selector} 出现超时")
                    
                    return ActionResult(
                        success=True, 
                        extracted_content="点击成功",
                        metadata={"element_index": index}
                    )
            except Exception as e:
                logger.warning(f"点击尝试 {attempt+1}/{max_attempts} 失败: {e}")
                
                if attempt < max_attempts - 1:
                    # 等待后重试
                    await asyncio.sleep(0.5)
        
        return ActionResult(success=False, error_message="所有点击方法都失败")
    except Exception as e:
        logger.error(f"点击操作失败: {e}", exc_info=True)
        return ActionResult(success=False, error_message=f"点击失败: {str(e)}")

async def _try_click_methods(page, element, force: bool, context) -> bool:
    """尝试多种点击方法"""
    methods = [
        _try_standard_click,
        _try_js_click,
        _try_mouse_click
    ]
    
    if force:
        # 如果指定强制点击，添加强制点击方法
        methods.append(_try_force_click)
    
    # 尝试每种方法
    for method in methods:
        try:
            if await method(page, element, context):
                return True
        except Exception as e:
            logger.warning(f"{method.__name__} 失败: {e}")
            
        # 每次尝试后等待一小段时间
        await asyncio.sleep(0.1)
        
    return False
    
async def _try_standard_click(page, element, context) -> bool:
    """标准点击方法"""
    await page.click(element.selector, timeout=3000)
    return True
    
async def _try_js_click(page, element, context) -> bool:
    """JavaScript点击方法"""
    await page.evaluate(f"""
        selector => {{
            const el = document.querySelector(selector);
            if (el) {{
                el.click();
                return true;
            }}
            return false;
        }}
    """, element.selector)
    return True
    
async def _try_mouse_click(page, element, context) -> bool:
    """鼠标点击方法"""
    # 获取元素中心位置
    bounds = await page.evaluate(f"""
        selector => {{
            const el = document.querySelector(selector);
            if (el) {{
                const rect = el.getBoundingClientRect();
                return {{
                    x: rect.left + rect.width / 2,
                    y: rect.top + rect.height / 2,
                    width: rect.width,
                    height: rect.height
                }};
            }}
            return null;
        }}
    """, element.selector)
    
    if bounds:
        # 移动鼠标到元素中心
        await page.mouse.move(bounds['x'], bounds['y'])
        # 点击
        await page.mouse.click(bounds['x'], bounds['y'])
        return True
    return False
    
async def _try_force_click(page, element, context) -> bool:
    """强制点击方法"""
    # 使用JavaScript手动触发事件
    await page.evaluate(f"""
        selector => {{
            const el = document.querySelector(selector);
            if (el) {{
                // 创建并分发鼠标事件
                const events = ['mousedown', 'mouseup', 'click'];
                for (const eventName of events) {{
                    const event = new MouseEvent(eventName, {{
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        buttons: 1
                    }});
                    el.dispatchEvent(event);
                }}
                return true;
            }}
            return false;
        }}
    """, element.selector)
    return True

async def element_diagnostic_action(params: ElementDiagnosticParams, browser) -> ActionResult:
    """元素诊断操作"""
    try:
        context = browser.context
        page = await context.get_current_page()
        
        # 获取元素索引
        index = params.index
        
        # 使用增强的定位方法查找元素
        if index is None:
            index = await ElementHelper.resilient_locate(context, params.dict(exclude_unset=True))
            if index is None:
                return ActionResult(success=False, error_message="使用所有定位方法均未找到元素")
        
        element = await ElementHelper.get_element(context, index)
        if not element:
            return ActionResult(success=False, error_message="未找到元素")
        
        # 收集元素详细信息
        selector = element.selector
        element_info = await page.evaluate(f"""
            selector => {{
                const el = document.querySelector(selector);
                if (!el) return null;
                
                // 计算样式
                const style = window.getComputedStyle(el);
                
                // 位置和尺寸
                const rect = el.getBoundingClientRect();
                
                // 事件处理程序
                const events = [];
                for (const key in el) {{
                    if (key.startsWith('on') && typeof el[key] === 'function') {{
                        events.push(key.slice(2));
                    }}
                }}
                
                // 收集属性
                const attributes = {{}};
                for (const attr of el.attributes) {{
                    attributes[attr.name] = attr.value;
                }}
                
                // Z-index和定位
                const zIndex = style.zIndex !== 'auto' ? parseInt(style.zIndex) : 0;
                const position = style.position;
                
                // 可见性
                const isVisible = 
                    style.display !== 'none' && 
                    style.visibility !== 'hidden' && 
                    style.opacity !== '0' &&
                    rect.width > 0 && 
                    rect.height > 0;
                    
                // 检查元素是否被其他元素覆盖
                let isObstructed = false;
                if (isVisible) {{
                    const x = rect.left + rect.width / 2;
                    const y = rect.top + rect.height / 2;
                    const elementsAtPoint = document.elementsFromPoint(x, y);
                    
                    if (elementsAtPoint.length > 0 && elementsAtPoint[0] !== el) {{
                        isObstructed = true;
                    }}
                }}
                
                // 是否在视口内
                const isInViewport = 
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                    rect.right <= (window.innerWidth || document.documentElement.clientWidth);
                
                return {{
                    tagName: el.tagName.toLowerCase(),
                    id: el.id,
                    className: el.className,
                    innerText: el.innerText,
                    value: el.value,
                    isVisible,
                    isInViewport,
                    isObstructed,
                    position,
                    zIndex,
                    rect: {{
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        top: rect.top,
                        right: rect.right,
                        bottom: rect.bottom,
                        left: rect.left
                    }},
                    styles: {{
                        display: style.display,
                        visibility: style.visibility,
                        opacity: style.opacity,
                        pointerEvents: style.pointerEvents
                    }},
                    attributes,
                    events
                }};
            }}
        """, selector)
        
        if not element_info:
            return ActionResult(success=False, error_message="无法获取元素信息")
        
        # 添加建议
        suggestions = []
        
        if not element_info.get("isVisible", False):
            suggestions.append("元素不可见，检查CSS属性：display、visibility或opacity")
        
        if not element_info.get("isInViewport", False):
            suggestions.append("元素不在视口内，需要滚动到元素位置")
        
        if element_info.get("isObstructed", False):
            suggestions.append("元素被其他元素覆盖，可能需要先处理覆盖元素")
        
        if element_info.get("styles", {}).get("pointerEvents") == "none":
            suggestions.append("元素的pointerEvents设为none，使用JavaScript点击或先修改此属性")
        
        # 返回元素诊断信息
        diagnostic_data = {
            "element_info": element_info,
            "suggestions": suggestions,
            "index": index,
            "selector": selector
        }
        
        return ActionResult(
            success=True, 
            extracted_content="元素诊断完成", 
            metadata=diagnostic_data
        )
    except Exception as e:
        logger.error(f"元素诊断失败: {e}", exc_info=True)
        return ActionResult(success=False, error_message=f"诊断失败: {str(e)}")

# 提供一个函数来设置装饰器式的操作注册
def register_enhanced_ui_actions(controller):
    """注册所有增强的UI操作到控制器，使用装饰器模式"""
    logger.info("注册增强UI操作")
    
    # 注册输入文本操作
    controller.registry.action(
        name="input_text",
        description="输入文本到指定元素",
        param_model=InputTextParams
    )(input_text_action)
    
    # 注册查找元素操作
    controller.registry.action(
        name="find_element",
        description="查找页面元素",
        param_model=FindElementParams
    )(find_element_action)
    
    # 注册页面操作
    controller.registry.action(
        name="page_action",
        description="执行页面相关操作",
        param_model=PageActionParams
    )(page_action)
    
    # 注册增强点击操作
    controller.registry.action(
        name="resilient_click",
        description="增强型元素点击操作",
        param_model=ResilientClickParams
    )(resilient_click_action)
    
    # 注册元素诊断操作
    controller.registry.action(
        name="element_diagnostic",
        description="诊断元素状态和问题",
        param_model=ElementDiagnosticParams
    )(element_diagnostic_action)
    
    logger.info("UI增强操作注册完成")