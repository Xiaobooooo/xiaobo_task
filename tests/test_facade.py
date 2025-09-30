# -*- coding: utf-8 -*-

import asyncio
import time
from typing import List

# Correctly import the classes we created
from xiaobo_task.facade import XiaoboTask
from xiaobo_task.domain import Target


# --- Test Task Functions ---

def sync_task(source: Target, results_list: List):
    """A universal synchronous task for testing."""
    time.sleep(0.01)
    source.logger.warning("2")
    results_list.append(source.data)


async def async_task(source: Target, results_list: List):
    """A universal asynchronous task for testing."""
    await asyncio.sleep(0.01)
    results_list.append(source.data)


# --- Pytest Test Cases ---

def test_submit_tasks_with_int_source():
    """测试使用整数作为任务源。"""
    results = []
    task_count = 5
    with XiaoboTask(max_workers=2) as runner:
        runner.submit_tasks(
            source=task_count,
            task_func=sync_task,
            kwargs={"results_list": results}
        )
    # The `data` field for an int source is the index itself
    assert len(results) == task_count
    assert sorted(results) == list(range(task_count))


def test_submit_tasks_with_list_source():
    """测试使用列表作为任务源。"""
    results = []
    items = ["apple", "banana", "cherry"]
    with XiaoboTask(max_workers=2) as runner:
        runner.submit_tasks(
            source=items,
            task_func=sync_task,
            kwargs={"results_list": results}
        )
    assert len(results) == len(items)
    assert sorted(results) == sorted(items)


def test_async_task_submission():
    """测试对异步 (async) 任务函数的支持。"""
    results = []
    items = ["async_a", "async_b"]
    with XiaoboTask(max_workers=2) as runner:
        runner.submit_tasks(
            source=items,
            task_func=async_task,
            kwargs={"results_list": results}
        )
    assert len(results) == len(items)
    assert sorted(results) == sorted(items)


def test_submit_tasks_from_file(tmp_path):
    """测试从文件读取任务源。"""
    results = []
    # Use pytest's tmp_path fixture to create a temporary test file
    file_content = "line1_data\nline2_data"
    p = tmp_path / "test_data.txt"
    p.write_text(file_content, encoding="utf-8")

    with XiaoboTask(max_workers=2) as runner:
        runner.submit_tasks_from_file(
            filename=str(p),
            task_func=sync_task,
            separator='_',  # Use a different separator for testing
            kwargs={"results_list": results}
        )

    assert len(results) == 2
    # The data passed to the task is a list of strings from the split line
    assert results[0] == ["line1", "data"]
    assert results[1] == ["line2", "data"]


def test_callbacks_on_success_and_error():
    """测试 on_success 和 on_error 回调函数。"""
    success_results = []
    error_results = []

    def handle_success(result):
        success_results.append(result)

    def handle_error(error):
        error_results.append(error)

    # A simple task that returns the data
    def simple_return_task(source: Target):
        if source.index == 1:  # Fail on the second item
            raise ValueError("Test Error")
        return source.data

    items = ["a", "b", "c"]
    with XiaoboTask(max_workers=2) as runner:
        runner.submit_tasks(
            source=items,
            task_func=simple_return_task,
            on_success=handle_success,
            on_error=handle_error
        )

    assert len(success_results) == 2
    assert len(error_results) == 1
    assert "a" in success_results
    assert "c" in success_results
    assert isinstance(error_results[0], ValueError)




test_submit_tasks_with_list_source()
