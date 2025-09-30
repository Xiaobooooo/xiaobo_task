import asyncio
import inspect
import os
import random
import traceback
from typing import Optional, Callable, Any, Dict, Tuple, List, Union, TYPE_CHECKING

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from xiaobo_task.manager import TaskManager
from xiaobo_task import util
from xiaobo_task.domain import Target
from xiaobo_task.settings import Settings

if TYPE_CHECKING:
    from loguru import Logger


class XiaoboTask:
    """任务框架的高级封装 (Facade)。

    该类旨在提供一个更简洁的API，并自动处理配置加载。
    它封装了底层的 TaskManager，处理.env配置文件的读取，
    并为用户提供一个即开即用的任务提交接口。
    """

    def __init__(self, name: str = "XiaoboTask", **kwargs):
        """初始化 XiaoboTask 实例。

        配置会自动从 .env 文件、环境变量或默认值加载。
        也可以通过在构造函数中传递关键字参数来直接覆盖任何配置项。

        参数:
            name (str): 任务实例的名称。
            **kwargs: 任何配置参数，将覆盖 .env 文件或默认值。
                      例如: max_workers=10, retries=5
        """
        self.logger = logger.bind(name=name)

        # 过滤掉值为 None 的 kwargs，这样 pydantic 才会继续查找 env/default
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}

        # 使用 pydantic-settings 加载配置，并允许通过参数覆盖
        self.settings = Settings(**filtered_kwargs)

        # 初始化简化的 TaskManager
        self._manager = TaskManager(max_workers=self.settings.max_workers)

        # 记录加载的配置信息
        self._log_settings()

    def _log_settings(self):
        """以中文格式，逐行记录加载的配置信息，并处理中文字符对齐。"""

        self.logger.info("--- 任务配置加载开始 ---")

        # 遍历 pydantic 模型的字段以获取描述和值
        for field_name, field_info in self.settings.model_fields.items():
            description = field_info.description or field_name
            value = getattr(self.settings, field_name)

            # 对特殊值进行友好显示
            if value is None:
                value_str = "未设置"
            elif isinstance(value, bool):
                value_str = "是" if value else "否"
            else:
                value_str = str(value)

            self.logger.info(f"{description}: {value_str}")

        self.logger.info("--- 配置加载完毕 ---")


    def submit_task(
            self,
            task_logger: "Logger",
            task_func: Callable[..., Any],
            args: Tuple = (),
            kwargs: Optional[Dict[str, Any]] = None,
            on_success: Optional[Callable[[Target, Any], None]] = None,
            on_error: Optional[Callable[[Target, Exception], None]] = None,
            retries: Optional[int] = None,
            retry_delay: Optional[float] = None,
    ):
        """提交一个新任务。

        此方法现在负责包装任务函数，为其添加重试和异步处理逻辑，
        然后将包装好的函数提交给底层的 TaskManager。
        """
        target = args[0] if args and isinstance(args[0], Target) else None

        def on_task_success(t: Target, result: Any):
            task_logger.success(f"✅ 任务执行成功")
            if on_success:
                on_success(t, result)

        def on_task_error(t: Target, error: Exception):
            try:
                tb = error.__traceback__
                last_frame = traceback.extract_tb(tb)[-1]
                filename = os.path.basename(last_frame.filename)
                lineno = last_frame.lineno
                error_type = error.__class__.__name__
                log_message = f"❌ 任务执行失败 -> [{filename}:{lineno}] {error_type}: {error}"
                task_logger.error(log_message)
            except Exception:
                task_logger.error(f"❌ 任务执行失败 -> {error.__class__.__name__}: {error}")

            if on_error:
                on_error(t, error)

        effective_retries = retries if retries is not None else self.settings.retries
        effective_retry_delay = retry_delay if retry_delay is not None else self.settings.retry_delay

        # --- 将所有执行逻辑包装到一个函数中 ---
        def _wrapped_task_executor():
            
            def log_before_retry(retry_state):
                if target and target.logger:
                    exc = retry_state.outcome.exception()
                    target.logger.warning(
                        f"🔄 任务失败，将在 {retry_state.next_action.sleep:.2f} 秒后进行第 {retry_state.attempt_number} 次重试... "
                        f"异常: {repr(exc)}"
                    )

            @retry(
                stop=stop_after_attempt(effective_retries + 1),
                wait=wait_fixed(effective_retry_delay) if effective_retry_delay > 0 else None,
                before_sleep=log_before_retry,
                reraise=True
            )
            def task_to_run():
                if inspect.iscoroutinefunction(task_func):
                    loop = util.get_or_create_event_loop()
                    return loop.run_until_complete(task_func(*args, **(kwargs or {})))
                else:
                    return task_func(*args, **(kwargs or {}))

            return task_to_run()
        # --- 包装结束 ---

        return self._manager.submit_task(
            task_func=_wrapped_task_executor,
            args=args,  # 传递原始 args 以便 manager 能提取 target 用于回调
            kwargs=kwargs,
            on_success=on_task_success,
            on_error=on_task_error,
        )

    def submit_tasks(
            self,
            source: Union[int, List[Any]],
            task_func: Callable[..., Any],
            args: Tuple = (),
            kwargs: Optional[Dict[str, Any]] = None,
            on_success: Optional[Callable[[Target, Any], None]] = None,
            on_error: Optional[Callable[[Target, Exception], None]] = None,
            retries: Optional[int] = None,
            retry_delay: Optional[float] = None,
    ):
        """
        根据指定的源批量提交任务。

        源可以是整数（提交指定数量的任务）或列表（为每个元素提交一个任务）。

        参数:
            source (Union[int, List[Any]]): 任务源。
            task_func (Callable): 要执行的任务函数。
            ... (其他参数)
        """
        if isinstance(source, int):
            items = range(source)
        elif isinstance(source, list):
            items = source[:]
            if self.settings.shuffle:
                random.shuffle(items)
        else:
            raise TypeError("'source' 必须是 int 或 list 类型。")

        if not items:
            self.logger.warning("任务数量必须大于 0。")
            return

        for index, item in enumerate(items):
            task_name = f"{index + 1:05d}"
            task_logger = self.logger.bind(name=task_name)

            proxy = None
            if not self.settings.disable_proxy:
                p = self.settings.proxy_ipv6 if self.settings.use_ipv6 and self.settings.proxy_ipv6 else self.settings.proxy
                if p:
                    proxy = p.replace('*****', str(item))

            source_obj = Target(index=index, data=item, proxy=proxy, logger=task_logger)
            task_args = (source_obj,) + args

            self.submit_task(
                task_logger=task_logger,
                task_func=task_func,
                args=task_args,
                kwargs=kwargs,
                on_success=on_success,
                on_error=on_error,
                retries=retries,
                retry_delay=retry_delay,
            )

    def submit_tasks_from_file(
            self,
            filename: str,
            task_func: Callable[..., Any],
            separator: str = '----',
            args: Tuple = (),
            kwargs: Optional[Dict[str, Any]] = None,
            on_success: Optional[Callable[[Target, Any], None]] = None,
            on_error: Optional[Callable[[Target, Exception], None]] = None,
            retries: Optional[int] = None,
            retry_delay: Optional[float] = None,
    ):
        """
        从文件中读取数据并批量提交任务。
        ... (其他文档)
        """
        try:
            lines = util.read_txt_file_lines(filename)
            source_list = [line.split(separator) for line in lines]
        except (FileNotFoundError, IOError) as e:
            self.logger.error(f"文件 '{filename}' 解析失败: {e}")
            return

        self.submit_tasks(
            source=source_list,
            task_func=task_func,
            args=args,
            kwargs=kwargs,
            on_success=on_success,
            on_error=on_error,
            retries=retries,
            retry_delay=retry_delay,
        )

    def __enter__(self):
        """实现上下文管理器协议，在 'with' 语句开始时返回自身。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """在 'with' 语句结束时，安全关闭底层的 TaskManager。"""
        self._manager.shutdown()
