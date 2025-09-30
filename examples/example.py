# -*- coding: utf-8 -*-

import time
import random
import sys
import os
from typing import Any

# 将项目根目录添加到 sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from loguru import logger

from xiaobo_task import XiaoboTask, Target

# 建议在项目根目录创建 .env 文件并添加以下内容，以便此示例能正确运行：
# MAX_WORKERS=5
# SHUFFLE=true
# PROXY=http://user:pass@host:port
#
# --- 新增的重试配置 ---
# RETRIES=2           # 默认重试次数
# RETRY_DELAY=3       # 默认重试延迟（秒）

# 1. 加载环境变量 (通常在项目入口处执行一次)
load_dotenv()


def my_task_processor(target: Target, custom_arg: str):
    """
    这是我们要并发执行的主任务函数。
    """
    target.logger.info(f"开始处理任务，数据: {target.data}，自定义参数: {custom_arg}")
    target.logger.info(f"任务分配到的代理是: {target.proxy}")

    try:
        sleep_time = random.uniform(0.5, 1.0)
        time.sleep(sleep_time)

        # 为了演示重试，我们让 'data-3' 和 'data-7' 任务总是失败
        if target.data in ["data-3", "data-7"]:
            # target.index 是从0开始的，所以这里可以用来区分不同任务的失败场景
            if target.index % 2 == 0:
                # 偶数索引的任务模拟一个网络错误
                raise ConnectionError("模拟一个网络连接错误")
            else:
                # 奇数索引的任务模拟一个值错误
                raise ValueError("模拟一个无效值错误")

        result = f"'{target.data}' 处理完毕，耗时 {sleep_time:.2f} 秒"
        return result
    except Exception as e:
        # 任务函数内部不需要自己实现重试逻辑，只需要在发生无法恢复的错误时抛出异常即可
        # 框架会自动根据配置进行重试
        raise e


def on_task_success(target: Target, result: Any):
    """任务成功完成时的回调函数。"""
    target.logger.info(f"✅ 成功回调 [数据: {target.data}] -> 结果: {result}")


def on_task_error(target: Target, error: Exception):
    """任务失败时的回调函数（所有重试都用完后才会调用）。"""
    target.logger.error(f"❌ 失败回调 [数据: {target.data}] -> 最终异常: {error.__class__.__name__}: {error}")


if __name__ == "__main__":
    logger.info("--- 开始批量提交任务 ---")

    task_data_list = [f"data-{i}" for i in range(10)]

    # 使用 pydantic-settings 后，可以在初始化时通过关键字参数覆盖任何配置
    # 例如，这里我们将 .env 文件中的 MAX_WORKERS (如果存在) 覆盖为 3
    # XiaoboTask 初始化时会自动以中文打印所有加载的配置
    with XiaoboTask(name="MyExampleTask", max_workers=3) as task_manager:

        # 批量提交任务
        # 也可以在提交时覆盖重试策略
        task_manager.submit_tasks(
            source=task_data_list,
            task_func=my_task_processor,
            args=("这是一个自定义参数",),
            on_success=on_task_success,
            on_error=on_task_error,
            retries=1  # 将这批任务的重试次数覆盖为1
        )

        # 预期行为:
        # - 任务将以3个并发工作线程执行。
        # - 'data-3' 和 'data-7' 会失败。
        # - 框架会为它们分别重试1次（因为 submit_tasks 中 retries=1 覆盖了全局设置）。
        # - 最终，'data-3' 和 'data-7' 的 on_task_error 回调会被触发。
        # - 其他任务的 on_task_success 回调会被触发。

    logger.info("--- 所有任务已提交，主线程等待任务完成 ---")
    logger.info("--- 所有任务已执行完毕 ---")