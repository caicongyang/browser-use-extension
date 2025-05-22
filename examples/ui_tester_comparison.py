import os
import asyncio
import logging
import time
import sys
from typing import Dict, List, Tuple

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入标准版和缓存版测试器
from ui_tester_standard import StandardUITester
from ui_tester_cached import CachedUITester

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceComparison:
    """性能比较类"""
    
    def __init__(self):
        self.standard_results = []  # 标准方式测试结果
        self.cached_results = []    # 缓存方式测试结果
        
    async def run_comparison(self, runs: int = 3):
        """运行性能比较测试
        
        Args:
            runs: 每种方式运行的次数
        """
        logger.info(f"开始UI测试性能比较 (每种方式运行{runs}次)...")
        
        # 创建缓存目录
        os.makedirs("ui_test_cache", exist_ok=True)
        
        # 运行标准版测试器
        logger.info("\n" + "=" * 50)
        logger.info("运行标准版测试器...")
        logger.info("=" * 50)
        
        standard_tester = StandardUITester()
        
        for i in range(runs):
            logger.info(f"\n运行标准测试 #{i+1}/{runs}")
            start_time = time.time()
            success = await standard_tester.run_ui_test()
            end_time = time.time()
            
            self.standard_results.append({
                "run": i+1,
                "success": success,
                "total_time": end_time - start_time,
                "operation_time": standard_tester.report.total_time if hasattr(standard_tester, 'report') else 0
            })
        
        # 运行缓存版测试器
        logger.info("\n" + "=" * 50)
        logger.info("运行缓存版测试器...")
        logger.info("=" * 50)
        
        cached_tester = CachedUITester()
        
        for i in range(runs):
            logger.info(f"\n运行缓存测试 #{i+1}/{runs}")
            start_time = time.time()
            success = await cached_tester.run_ui_test()
            end_time = time.time()
            
            self.cached_results.append({
                "run": i+1,
                "success": success,
                "total_time": end_time - start_time,
                "operation_time": cached_tester.report.total_time if hasattr(cached_tester, 'report') else 0
            })
        
        # 生成比较报告
        self.generate_report()
    
    def generate_report(self):
        """生成性能比较报告"""
        logger.info("\n" + "=" * 50)
        logger.info("UI测试性能比较报告")
        logger.info("=" * 50)
        
        # 计算标准版统计数据
        standard_success_count = sum(1 for result in self.standard_results if result["success"])
        standard_success_rate = (standard_success_count / len(self.standard_results)) * 100 if self.standard_results else 0
        
        standard_total_times = [result["total_time"] for result in self.standard_results]
        standard_avg_total_time = sum(standard_total_times) / len(standard_total_times) if standard_total_times else 0
        
        standard_operation_times = [result["operation_time"] for result in self.standard_results]
        standard_avg_operation_time = sum(standard_operation_times) / len(standard_operation_times) if standard_operation_times else 0
        
        # 计算缓存版统计数据
        cached_success_count = sum(1 for result in self.cached_results if result["success"])
        cached_success_rate = (cached_success_count / len(self.cached_results)) * 100 if self.cached_results else 0
        
        cached_total_times = [result["total_time"] for result in self.cached_results]
        cached_avg_total_time = sum(cached_total_times) / len(cached_total_times) if cached_total_times else 0
        
        cached_operation_times = [result["operation_time"] for result in self.cached_results]
        cached_avg_operation_time = sum(cached_operation_times) / len(cached_operation_times) if cached_operation_times else 0
        
        # 计算性能提升百分比
        total_time_improvement = ((standard_avg_total_time - cached_avg_total_time) / standard_avg_total_time) * 100 if standard_avg_total_time > 0 else 0
        operation_time_improvement = ((standard_avg_operation_time - cached_avg_operation_time) / standard_avg_operation_time) * 100 if standard_avg_operation_time > 0 else 0
        
        # 输出报告
        logger.info(f"\n标准版测试结果:")
        logger.info(f"  成功率: {standard_success_rate:.2f}% ({standard_success_count}/{len(self.standard_results)})")
        logger.info(f"  平均总耗时: {standard_avg_total_time:.4f}秒")
        logger.info(f"  平均操作耗时: {standard_avg_operation_time:.4f}秒")
        
        logger.info(f"\n缓存版测试结果:")
        logger.info(f"  成功率: {cached_success_rate:.2f}% ({cached_success_count}/{len(self.cached_results)})")
        logger.info(f"  平均总耗时: {cached_avg_total_time:.4f}秒")
        logger.info(f"  平均操作耗时: {cached_avg_operation_time:.4f}秒")
        
        logger.info(f"\n性能比较:")
        logger.info(f"  总耗时提升: {total_time_improvement:.2f}%")
        logger.info(f"  操作耗时提升: {operation_time_improvement:.2f}%")
        
        logger.info(f"\n详细测试数据:")
        logger.info(f"  标准版测试: {self.standard_results}")
        logger.info(f"  缓存版测试: {self.cached_results}")
        
        logger.info("=" * 50)

async def main():
    """主函数"""
    comparison = PerformanceComparison()
    await comparison.run_comparison(runs=1)  # 默认每种方式运行1次，可以增加次数以获取更稳定的数据

if __name__ == "__main__":
    asyncio.run(main()) 