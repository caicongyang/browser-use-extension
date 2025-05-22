# Browser-Use 增强型UI操作系统

这个模块为 Browser-Use 项目提供了增强型UI操作，使其能够更智能地与Web界面进行交互。

## 主要特性

- **增强型元素定位**: 使用多种定位策略智能查找元素
- **智能点击操作**: 自动尝试多种点击方法，确保点击成功
- **增强型文本输入**: 处理各种输入场景和边缘情况
- **元素诊断工具**: 提供详细的元素状态分析和问题排查
- **增强型页面操作**: 提供更灵活的页面控制能力

## 结构

- `ui_registry/`: 注册系统，负责将增强型UI操作集成到控制器中
  - `action_registry.py`: 提供 `EnhancedUIRegistry` 类，扩展核心注册表
- `ui_enhanced/`: 实现各种增强型UI操作
  - `ui_enhanced_actions.py`: 包含所有增强型UI操作的实现
  - `example_usage.py`: 展示如何使用增强型UI操作的示例
  - `run_test.py`: 用于测试增强型UI操作的工具

## 快速开始

### 1. 向现有Controller注册增强操作

最简单的使用方式是将增强操作注册到现有控制器：

```python
from browser_use.controller.service import Controller
from element_enhance.ui_enhanced.ui_enhanced_actions import EnhancedUIActionProvider

# 创建控制器
controller = Controller()

# 注册增强UI操作
EnhancedUIActionProvider.register_to_controller(controller)

# 现在控制器已经具备了增强UI操作能力
```

### 2. 使用工厂函数创建增强控制器

为了简化使用，可以使用工厂函数创建预配置的控制器：

```python
from element_enhance.ui_enhanced.example_usage import create_enhanced_controller

# 创建增强控制器
enhanced_controller = create_enhanced_controller()

# 使用控制器
result = await enhanced_controller.act(action_model, browser)
```

### 3. 使用专用的EnhancedUIRegistry

如果需要更灵活的配置，可以使用 `EnhancedUIRegistry`：

```python
from element_enhance.ui_registry.action_registry import create_enhanced_ui_registry
from element_enhance.ui_enhanced.ui_enhanced_actions import EnhancedUIActionProvider

# 创建增强UI注册表
enhanced_registry = create_enhanced_ui_registry()

# 注册自定义操作
@enhanced_registry.register_enhanced_ui_action(
    name="custom_action",
    description="自定义操作"
)
async def custom_action(message: str, browser=None):
    # 实现自定义操作
    return ActionResult(success=True, extracted_content=message)

# 注册所有标准增强UI操作
EnhancedUIActionProvider.register_to_registry(enhanced_registry)
```

## 增强型UI操作列表

### 1. 增强型点击操作 (`enhanced_resilient_click`)

智能点击功能，会尝试多种策略来点击元素。

```python
from element_enhance.ui_enhanced.ui_enhanced_actions import ResilientClickParams

params = ResilientClickParams(
    text="登录",  # 通过文本查找元素
    max_attempts=3,  # 最大尝试次数
    force=True  # 是否使用强制点击
)

result = await controller.act({"enhanced_resilient_click": params.model_dump()}, browser)
```

### 2. 增强型文本输入 (`enhanced_input_text`)

智能处理各种输入场景的文本输入操作。

```python
from element_enhance.ui_enhanced.ui_enhanced_actions import InputTextParams

params = InputTextParams(
    index=2,  # 元素索引
    text="test@example.com",  # 要输入的文本
    clear_first=True  # 是否先清除现有内容
)

result = await controller.act({"enhanced_input_text": params.model_dump()}, browser)
```

### 3. 元素查找 (`enhanced_find_element`)

使用多种策略查找元素。

```python
from element_enhance.ui_enhanced.ui_enhanced_actions import FindElementParams

params = FindElementParams(
    text="登录",  # 要查找的文本
    visible_only=True  # 是否只查找可见元素
)

result = await controller.act({"enhanced_find_element": params.model_dump()}, browser)
```

### 4. 页面操作 (`enhanced_page_action`)

执行各种页面级操作。

```python
from element_enhance.ui_enhanced.ui_enhanced_actions import PageActionParams

params = PageActionParams(
    action_type="scroll",  # 操作类型
    scroll_direction="bottom"  # 滚动方向
)

result = await controller.act({"enhanced_page_action": params.model_dump()}, browser)
```

### 5. 元素诊断 (`enhanced_element_diagnostic`)

诊断元素状态，提供详细信息。

```python
from element_enhance.ui_enhanced.ui_enhanced_actions import ElementDiagnosticParams

params = ElementDiagnosticParams(
    index=1  # 元素索引
)

result = await controller.act({"enhanced_element_diagnostic": params.model_dump()}, browser)
```

## 测试

使用提供的测试脚本测试增强UI操作：

```bash
# 测试所有操作（使用模拟浏览器）
python -m element_enhance.ui_enhanced.run_test --mock

# 测试特定操作
python -m element_enhance.ui_enhanced.run_test --action resilient_click

# 使用真实浏览器测试
python -m element_enhance.ui_enhanced.run_test
```

## 示例

查看 `ui_enhanced/example_usage.py` 获取更多使用示例，包括：

1. 如何向现有Controller注册增强操作
2. 如何使用EnhancedUIRegistry创建增强控制器
3. 如何使用工厂函数创建预配置的控制器
4. 如何在实际应用场景中使用增强UI操作（如登录流程）

## 开发扩展

要添加新的增强UI操作：

1. 在 `ui_enhanced_actions.py` 中定义新的参数模型和实现函数
2. 在 `EnhancedUIActionProvider` 类中注册新操作
3. 更新测试和文档

## 许可证

与Browser-Use项目相同 