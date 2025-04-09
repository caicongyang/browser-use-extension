import os
import asyncio
import logging
import sys
from typing import Dict, Any

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

async def run_demo():
    """运行演示"""
    logger.info("启动演示...")
    
    # 创建浏览器和控制器
    browser = Browser()  # 使用默认配置
    controller = Controller()
    
    # 创建浏览器上下文
    context = await browser.new_context()
    
    # 扩展浏览器上下文，添加缓存功能
    context = extend_browser_context(context, cache_dir="demo_cache_001")
    
    try:
        # 测试场景1: 初始缓存构建
        await test_initial_caching(context)
        
        # 测试场景2: 使用缓存定位元素
        await test_cached_element_location(context, controller)
        
        # 测试场景3: 缓存验证和更新
        await test_cache_validation(context)
        
        # 测试场景4: 性能比较
        await test_performance_comparison(context)
        
    finally:
        # 关闭浏览器
        await browser.close()
        logger.info("演示完成")

async def test_initial_caching(context):
    """测试初始缓存构建"""
    logger.info("\n=== 测试场景1: 初始缓存构建 ===")
    
    # 导航到测试页面
    page = await context.get_current_page()
    await page.goto("https://www.python.org/")
    await page.wait_for_load_state()
    
    # 获取当前URL
    current_url = await context._get_current_url()
    logger.info(f"当前页面: {current_url}")
    
    # 获取DOM状态以确保包含xpath信息
    dom_state = await context.get_state()
    
    # 构建并存储缓存，确保包含xpath信息
    logger.info("构建元素缓存...")
    cached_elements = {}
    for index, element in dom_state.selector_map.items():
        element_data = {
            'tag_name': element.tag_name,
            'text': element.get_all_text_till_next_clickable_element(),
            'attributes': element.attributes,
            'xpath': element.xpath,
            'is_interactive': element.is_interactive,
            'is_visible': element.is_visible,
            'is_in_viewport': element.is_in_viewport
        }
        cached_elements[index] = element_data
    
    # 使用cache_manager的store_elements方法
    params = context.cache_manager._extract_url_params(current_url)
    context.element_cache.store_elements(current_url, cached_elements, params)
    logger.info(f"缓存了 {len(cached_elements)} 个元素")
    
    # 显示部分缓存内容
    display_sample_cache(cached_elements)

async def test_cached_element_location(context, controller):
    """测试使用缓存定位元素"""
    logger.info("\n=== 测试场景2: 使用缓存定位元素 ===")
    
    # 导航到测试页面
    page = await context.get_current_page()
    await page.goto("https://www.python.org/")
    await page.wait_for_load_state()
    
    # 获取当前URL
    current_url = await context._get_current_url()
    
    # 使用缓存获取元素
    logger.info("使用缓存获取元素...")
    
    # 获取DOM状态
    dom_state = await context.get_state()
    
    # 找到一个可点击的元素
    target_index = None
    for index, element in dom_state.selector_map.items():
        if element.is_interactive and "Download" in element.get_all_text_till_next_clickable_element():
            target_index = index
            break
    
    if target_index is not None:
        logger.info(f"找到目标元素: index={target_index}")
        
        # 使用标准方法获取元素
        logger.info("使用标准方法获取元素...")
        standard_start = asyncio.get_event_loop().time()
        element_standard = await context.get_dom_element_by_index(target_index)
        standard_end = asyncio.get_event_loop().time()
        standard_time = standard_end - standard_start
        
        # 使用缓存方法获取元素
        logger.info("使用缓存方法获取元素...")
        cache_start = asyncio.get_event_loop().time()
        element_cached = await context.get_dom_element_by_index_with_cache(target_index)
        cache_end = asyncio.get_event_loop().time()
        cache_time = cache_end - cache_start
        
        logger.info(f"标准方法耗时: {standard_time:.4f}秒")
        logger.info(f"缓存方法耗时: {cache_time:.4f}秒")
        logger.info(f"性能提升: {(standard_time - cache_time) / standard_time * 100:.2f}%")
        
        # 点击元素
        logger.info("点击缓存获取的元素...")
        try:
            # 创建点击操作
            click_action = ClickElementAction(index=target_index)
            
            # 执行点击操作
            result = await controller.registry.execute_action("click_element", click_action, context)
            
            logger.info(f"点击结果: {result.extracted_content}")
        except Exception as e:
            logger.error(f"点击元素失败: {str(e)}")
    else:
        logger.warning("未找到合适的目标元素")

async def test_cache_validation(context):
    """测试缓存验证和更新"""
    logger.info("\n=== 测试场景3: 缓存验证和更新 ===")
    
    # 导航到测试页面
    page = await context.get_current_page()
    await page.goto("https://www.python.org/")
    await page.wait_for_load_state()
    
    # 获取当前URL
    current_url = await context._get_current_url()
    
    # 获取初始缓存
    initial_cache = await context.cache_manager.get_elements_with_cache(current_url)
    logger.info(f"初始缓存包含 {len(initial_cache)} 个元素")
    
    # 修改页面内容（模拟页面变化）
    logger.info("模拟页面变化...")
    await page.evaluate("""
    () => {
        // 添加一个新按钮
        const newButton = document.createElement('button');
        newButton.textContent = 'New Test Button';
        newButton.style.position = 'fixed';
        newButton.style.top = '100px';
        newButton.style.right = '20px';
        newButton.style.zIndex = '9999';
        document.body.appendChild(newButton);
        
        // 修改一些现有元素
        const links = document.querySelectorAll('a');
        if (links.length > 5) {
            links[5].textContent = 'Modified Link';
            links[5].style.color = 'red';
        }
    }
    """)
    
    # 验证缓存
    logger.info("验证缓存...")
    is_valid = await context.cache_manager.validate_cache(current_url, initial_cache)
    logger.info(f"缓存验证结果: {'有效' if is_valid else '无效'}")
    
    # 更新缓存
    logger.info("更新缓存...")
    updated_cache = await context.cache_manager.update_cache_with_diff(current_url, initial_cache)
    logger.info(f"更新后的缓存包含 {len(updated_cache)} 个元素")
    
    # 比较缓存差异
    added = set(updated_cache.keys()) - set(initial_cache.keys())
    removed = set(initial_cache.keys()) - set(updated_cache.keys())
    
    logger.info(f"添加了 {len(added)} 个元素")
    logger.info(f"删除了 {len(removed)} 个元素")
    
    # 显示部分更新后的缓存
    display_sample_cache(updated_cache)

async def test_performance_comparison(context):
    """测试性能比较"""
    logger.info("\n=== 测试场景4: 性能比较 ===")
    
    # 测试页面列表
    test_pages = [
        "https://www.python.org/",
        "https://www.python.org/about/",
        "https://www.python.org/downloads/"
    ]
    
    # 初始化缓存
    logger.info("初始化测试页面缓存...")
    await context.initialize_cache(test_pages)
    
    # 性能测试结果
    results = []
    
    for url in test_pages:
        logger.info(f"\n测试页面: {url}")
        
        # 导航到页面
        page = await context.get_current_page()
        await page.goto(url)
        await page.wait_for_load_state()
        
        # 测试标准方法性能
        logger.info("测试标准方法性能...")
        standard_start = asyncio.get_event_loop().time()
        
        # 获取DOM状态 - 标准方法
        dom_state = await context.get_state()
        element_count = len(dom_state.selector_map)
        
        standard_end = asyncio.get_event_loop().time()
        standard_time = standard_end - standard_start
        
        # 测试缓存方法性能
        logger.info("测试缓存方法性能...")
        cache_start = asyncio.get_event_loop().time()
        
        # 获取缓存元素
        cached_elements = await context.cache_manager.get_elements_with_cache(url)
        
        cache_end = asyncio.get_event_loop().time()
        cache_time = cache_end - cache_start
        
        # 记录结果
        results.append({
            'url': url,
            'element_count': element_count,
            'standard_time': standard_time,
            'cache_time': cache_time,
            'improvement': (standard_time - cache_time) / standard_time * 100
        })
        
        logger.info(f"标准方法耗时: {standard_time:.4f}秒")
        logger.info(f"缓存方法耗时: {cache_time:.4f}秒")
        logger.info(f"性能提升: {(standard_time - cache_time) / standard_time * 100:.2f}%")
    
    # 显示汇总结果
    logger.info("\n=== 性能测试汇总 ===")
    for result in results:
        logger.info(f"页面: {result['url']}")
        logger.info(f"  元素数量: {result['element_count']}")
        logger.info(f"  标准方法耗时: {result['standard_time']:.4f}秒")
        logger.info(f"  缓存方法耗时: {result['cache_time']:.4f}秒")
        logger.info(f"  性能提升: {result['improvement']:.2f}%")

def display_sample_cache(cached_elements, sample_size=3):
    """显示部分缓存内容"""
    logger.info("缓存样本:")
    
    # 获取最多sample_size个元素
    sample_keys = list(cached_elements.keys())[:sample_size]
    
    for key in sample_keys:
        element = cached_elements[key]
        tag_name = element.get('tag_name', 'unknown')
        text = element.get('text', '')[:50]  # 限制文本长度
        xpath = element.get('xpath', 'N/A')  # 添加xpath信息显示
        
        if len(text) >= 50:
            text += "..."
        
        attributes = element.get('attributes', {})
        attr_str = ", ".join(f"{k}='{v}'" for k, v in list(attributes.items())[:3])
        
        logger.info(f"  元素 {key}: <{tag_name} {attr_str}> xpath: {xpath} text: {text}")

if __name__ == "__main__":
    # 创建缓存目录
    os.makedirs("demo_cache", exist_ok=True)
    
    # 运行演示
    asyncio.run(run_demo()) 