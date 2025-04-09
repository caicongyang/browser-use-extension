# Browser-Use-Extension

[Browser-Use](https://github.com/caicongyang/browser-use) 库的高级扩展，提供增强的UI交互能力、元素缓存以及为AI代理提供可靠的浏览器自动化功能。

## 🌟 特性

- **增强的UI操作**：能够处理常见Web自动化挑战的弹性元素交互
- **元素缓存**：缓存DOM元素以提高性能和可靠性
- **诊断工具**：先进的元素诊断工具，帮助排查浏览器自动化问题
- **LLM集成**：与多种LLM提供商无缝集成（OpenAI、Anthropic、DeepSeek）
- **性能测量**：用于对比标准操作与增强操作性能的工具

## 📋 系统要求

- Python 3.11+
- Playwright
- 至少一个LLM提供商的访问权限（OpenAI、Anthropic或DeepSeek）

## 🚀 安装

```bash
# 安装包
pip install browser-use

# 安装playwright浏览器
playwright install
```

## 🔧 配置

在项目根目录创建一个`.env`文件，内含您的LLM API密钥：

```
# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Anthropic (可选)
ANTHROPIC_API_KEY=your-anthropic-api-key

# DeepSeek (可选)
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=your-deepseek-base-url
```

## 💻 使用方法

### 基本示例

```python
from element_enhance.llm_ui_tester import LLMUITester
import asyncio
from dotenv import load_dotenv
load_dotenv()

async def main():
    # 初始化UI测试器
    tester = LLMUITester()
    await tester.setup()
    
    # 导航到网站
    await tester.navigate("https://example.com")
    
    # 使用增强的UI操作
    result = await tester.execute_action(
        "resilient_click", 
        element_description="注册按钮"
    )
    
    print(f"操作结果: {result}")

asyncio.run(main())
```

### 运行自动化UI测试

```python
from element_enhance.llm_ui_tester import get_llm, EnhancedUITestAgent
import asyncio
from dotenv import load_dotenv
load_dotenv()

async def main():
    # 定义要执行的任务
    task = "访问example.com，填写联系表单并提交"
    
    # 创建并运行代理
    agent = EnhancedUITestAgent(
        task=task,
        llm_provider="openai",  # 或 "anthropic" 或 "deepseek"
        use_cache=True
    )
    
    await agent.setup()
    test_success = await agent.run(max_steps=10)
    
    print(f"测试成功完成: {test_success}")

asyncio.run(main())
```

## 🧩 项目结构

```
browser-use-extension/
├── element_enhance/                # 主要扩展代码
│   ├── browser_extension/          # 浏览器扩展功能
│   │   └── context_extension.py    # 带缓存的扩展浏览器上下文
│   ├── cache/                      # 元素缓存系统
│   ├── ui_enhanced/                # 增强的UI操作
│   │   └── ui_enhanced_actions.py  # 核心增强操作
│   ├── llm_ui_tester.py            # LLM驱动的UI测试框架
│   ├── ui_enhanced_actions.py      # 增强操作的注册系统
│   └── test_*.py                   # 测试文件
└── docs_local/                     # 原项目browser-use的解析文档
```

## 🔍 核心组件

### 增强的UI操作

该扩展提供强大的弹性UI操作：

- **resilient_click**：智能点击操作，可尝试多种备选策略
- **element_diagnostic**：Web元素的详细诊断
- **page_action**：各种页面级操作（滚动、等待等）

### 浏览器上下文扩展

扩展基础的Browser-Use上下文，增加：

- 元素缓存以提高性能
- 先进的元素定位策略
- 增强的诊断能力

### UI测试框架

完整的浏览器自动化框架，包含：

- 测试步骤跟踪和报告
- 性能比较（缓存操作与标准操作）
- 与多个LLM提供商的集成

## 🤝 贡献

欢迎贡献！请随时提交Pull Request。

## 📄 许可证

本项目采用MIT许可证 - 详情请参阅LICENSE文件。

## 🔗 链接

- [Browser-Use 仓库](https://github.com/browser-use/browser-use)
- [Browser-Use 文档](https://browser-use.github.io/)
