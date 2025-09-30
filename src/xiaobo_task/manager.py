import asyncio
import inspect
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Optional, Tuple, Dict

from xiaobo_task.domain import Target


class TaskManager:
    """通用多线程任务管理器（简化版）。

    该类仅封装 ThreadPoolExecutor，提供一个提交任务和附加回调的接口。
    所有复杂的执行逻辑（如重试、异步处理）都由调用方处理。
    """

    def __init__(self, max_workers: Optional[int] = None):
        """初始化 TaskManager。"""
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit_task(
            self,
            task_func: Callable[..., Any],
            args: Tuple = (),
            kwargs: Optional[Dict[str, Any]] = None,
            on_success: Optional[Callable[[Target, Any], None]] = None,
            on_error: Optional[Callable[[Target, Exception], None]] = None,
    ) -> Future:
        """提交一个新任务到线程池执行。

        参数:
            task_func (Callable): 要在工作线程中执行的、已被完全包装好的目标函数。
            args (Tuple): 传递给目标函数的位置参数。
            kwargs (Optional[Dict]): 传递给目标函数的关键字参数。
            on_success (Optional[Callable]): 任务成功完成时调用的回调函数。
            on_error (Optional[Callable]): 任务执行过程中发生异常时调用的回调函数。
        """
        # 从参数中提取 Target，用于回调
        target = args[0] if args and isinstance(args[0], Target) else None

        # 直接提交调用方传入的函数，不再关心其内部逻辑
        future = self.executor.submit(task_func, *args, **kwargs)

        future.add_done_callback(
            lambda f: self._task_done_callback(f, target, on_success, on_error)
        )
        return future

    def _task_done_callback(
            self,
            future: Future,
            target: Optional[Target],
            on_success: Optional[Callable[[Target, Any], None]],
            on_error: Optional[Callable[[Target, Exception], None]],
    ):
        """Future 完成时的内部回调方法。"""
        try:
            result = future.result()
            if on_success:
                on_success(target, result)
        except Exception as e:
            if on_error:
                on_error(target, e)

    def shutdown(self, wait: bool = True):
        """关闭线程池"""
        self.executor.shutdown(wait=wait)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

