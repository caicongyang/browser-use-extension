#!/usr/bin/env python3
"""
Test script for Enhanced UI Actions

This script demonstrates how to use the LLMUITester to test enhanced UI actions
for LLM agents interacting with web interfaces.

Usage:
  python test_enhanced_actions.py
"""
import asyncio
import logging
import json
from llm_ui_tester import LLMUITester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to demonstrate LLMUITester capabilities."""
    # Initialize the tester
    tester = LLMUITester()
    await tester.setup()
    
    # Get available actions
    available_actions = tester.get_available_actions()
    logger.info(f"Available UI actions: {json.dumps(available_actions, indent=2)}")
    
    # Navigate to a test website
    result = await tester.navigate("https://google.com")
    logger.info(f"Navigation result: {result}")
    
    # Get page information
    page_info = tester.get_page_info()
    logger.info(f"Current page info: {json.dumps(page_info, indent=2)}")
    
    # Test resilient click action
    try:
        click_result = await tester.execute_action(
            "resilient_click", 
            element_description="Search textbox"
        )
        logger.info(f"Resilient click result: {json.dumps(click_result, indent=2)}")
    except Exception as e:
        logger.error(f"Error executing resilient_click: {e}")
    
    # Test element diagnostic action
    try:
        diagnostic_result = await tester.execute_action(
            "element_diagnostic", 
            element_description="Search textbox"
        )
        logger.info(f"Element diagnostic result: {json.dumps(diagnostic_result, indent=2)}")
    except Exception as e:
        logger.error(f"Error executing element_diagnostic: {e}")
    
    # Test page action
    try:
        page_action_result = await tester.execute_action(
            "page_action", 
            action_type="scroll", 
            direction="down"
        )
        logger.info(f"Page action result: {json.dumps(page_action_result, indent=2)}")
    except Exception as e:
        logger.error(f"Error executing page_action: {e}")
    
    # Navigate to another website
    await tester.navigate("https://github.com")
    logger.info(f"Current URL: {tester.get_current_url()}")
    logger.info(f"Page info: {json.dumps(tester.get_page_info(), indent=2)}")

if __name__ == "__main__":
    asyncio.run(main()) 