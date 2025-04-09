# Enhanced UI Actions for LLM Agents

This directory contains a framework for enhancing UI actions for LLM agents interacting with web interfaces. The framework provides a way to test and implement resilient UI actions that can handle common challenges in web automation.

## Components

- `llm_ui_tester.py`: Contains the `LLMUITester` class that simulates a browser and provides methods for executing enhanced UI actions.
- `test_enhanced_actions.py`: A demonstration script showing how to use the `LLMUITester` class.

## Enhanced UI Actions

The framework supports several enhanced UI actions:

1. **Resilient Click**: A click action that can handle element movement, visibility changes, and other common issues.
2. **Element Diagnostic**: Provides diagnostic information about an element, helping to debug UI automation issues.
3. **Page Action**: General page actions like scrolling, zooming, or waiting for elements to load.

## Usage

To use the framework, import the `LLMUITester` class and create an instance:

```python
from llm_ui_tester import LLMUITester

tester = LLMUITester()
await tester.setup()
```

You can then navigate to a URL and execute actions:

```python
# Navigate to a website
await tester.navigate("https://example.com")

# Execute a resilient click
result = await tester.execute_action(
    "resilient_click", 
    element_description="Submit button"
)

# Get information about the current page
page_info = tester.get_page_info()
```

## Running the Test Script

To run the test script and see the framework in action:

```bash
python test_enhanced_actions.py
```

## Extending the Framework

You can extend the framework by adding new actions to the `LLMUITester` class. Simply implement a new method for your action and register it in the `setup()` method. 