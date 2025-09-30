# xiaobo-task

一个轻量、优雅且易于使用的 Python 多线程任务框架，内置了对异步函数、自动重试和灵活配置的支持。

旨在将开发者从繁琐的任务调度、并发控制和错误处理中解放出来，只需专注于核心业务逻辑的实现。

## ✨ 核心功能

- **简洁的 API**: 通过 `XiaoboTask` 类提供统一、易用的接口，使用 `with` 语句自动管理资源。
- **多线程执行**: 基于 `concurrent.futures.ThreadPoolExecutor` 实现真正的多线程并发。
- **`asyncio` 兼容**: 无缝支持 `async def` 形式的异步任务函数，并在线程中高效执行。
- **自动重试**: 内置基于 `tenacity` 的强大重试机制，可自定义重试次数和延迟。
- **灵活配置**: 通过 `.env` 文件或在初始化时传入参数来配置框架，由 `pydantic-settings` 驱动，健壮且易于扩展。
- **丰富的回调**: 支持为任务的成功和最终失败分别指定回调函数。
- **批量提交**: 可从列表或文件中轻松批量提交任务。
- **详细日志**: 集成 `loguru`，提供结构化、色彩丰富的日志输出，便于调试。

## 🚀 安装指南

1.  **克隆项目**
    ```bash
    git clone <your-repo-url>
    cd xiaobo-task
    ```

2.  **安装依赖**
    项目使用 `pyproject.toml` 管理依赖。推荐使用 `uv` 或 `pip` 进行安装。
    ```bash
    # 使用 uv (推荐)
    uv pip install -e .

    # 或使用 pip
    pip install -e .
    ```
    `-e` 表示以可编辑模式安装，方便你进行代码修改。

3.  **创建配置文件**
    在项目根目录创建一个 `.env` 文件。你可以从 `.env.example` 复制一份作为模板。
    ```bash
    cp .env.example .env
    ```
    然后根据需要修改 `.env` 文件中的配置。

## 💡 快速开始

使用 `xiaobo-task` 只需简单几步。下面是一个完整示例：

### 1. 定义任务函数

创建一个函数，它的**唯一参数**是 `Target` 对象。你可以通过 `target` 对象访问任务所需的所有上下文信息。

```python
# example.py
import time
import random
from xiaobo_task import Target

def my_task_processor(target: Target):
    """
    这是我们要并发执行的主任务函数。
    """
    target.logger.info(f"开始处理任务，数据: {target.data}")
    
    # 模拟任务执行
    time.sleep(random.uniform(0.5, 1.0))

    # 模拟失败，用于演示重试
    if target.data == "data-3":
        raise ConnectionError("模拟网络错误")

    return f"'{target.data}' 处理完毕"
```

### 2. (可选) 定义回调函数

你可以定义在任务成功或最终失败时执行的函数。

```python
# example.py
from typing import Any

def on_task_success(target: Target, result: Any):
    """任务成功完成时的回调函数。"""
    target.logger.info(f"✅ 成功回调 [数据: {target.data}] -> 结果: {result}")

def on_task_error(target: Target, error: Exception):
    """任务失败时的回调函数（所有重试都用完后才会调用）。"""
    target.logger.error(f"❌ 失败回调 [数据: {target.data}] -> 最终异常: {error}")
```

### 3. 启动任务

使用 `with` 语句创建 `XiaoboTask` 实例，并调用 `submit_tasks` 方法。

```python
# example.py
from xiaobo_task import XiaoboTask
from dotenv import load_dotenv

if __name__ == "__main__":
    # 加载 .env 文件中的配置
    load_dotenv()

    # 准备任务数据
    task_data_list = [f"data-{i}" for i in range(10)]

    # max_workers=3 会覆盖 .env 文件中的设置
    with XiaoboTask(name="MyExampleTask", max_workers=3) as task_manager:
        
        # 批量提交任务
        task_manager.submit_tasks(
            source=task_data_list,
            task_func=my_task_processor,
            on_success=on_task_success,
            on_error=on_task_error,
            retries=1  # 覆盖全局重试次数
        )

    print("--- 所有任务已执行完毕 ---")
```

## ⚙️ 配置详解

框架可以通过在项目根目录下的 `.env` 文件进行配置。所有配置项均不区分大小写。

| 变量名          | 类型    | 描述                                           | 默认值   |
| --------------- | ------- | ---------------------------------------------- | -------- |
| `MAX_WORKERS`   | `int`   | 线程池的最大工作线程数。                       | `5`      |
| `SHUFFLE`       | `bool`  | 是否在提交前打乱任务列表的顺序。               | `False`  |
| `RETRIES`       | `int`   | 任务失败后的全局默认重试次数。                 | `2`      |
| `RETRY_DELAY`   | `float` | 每次重试之间的全局默认延迟时间（秒）。         | `0.0`    |
| `PROXY`         | `str`   | 默认代理地址。                                 | `None`   |
| `PROXY_IPV6`    | `str`   | IPv6 代理地址。                                | `None`   |
| `USE_IPV6`      | `bool`  | 是否优先使用 `PROXY_IPV6`。                    | `False`  |
| `DISABLE_PROXY` | `bool`  | 是否完全禁用代理功能。                         | `False`  |

**注意**:
- 所有配置都可以在 `XiaoboTask(...)` 初始化时作为关键字参数传入，以覆盖 `.env` 文件中的值。
- `retries` 和 `retry_delay` 可以在 `submit_tasks()` 调用时传入，为该批次任务指定独立的重试策略。

## 📄 API 概览

### `XiaoboTask`
这是框架的主入口点。
```python
with XiaoboTask(name: str = "XiaoboTask", **kwargs) as manager:
    ...
```
- `name`: 任务实例的名称，会显示在日志中。
- `**kwargs`: 任何配置项的名称（不区分大小写），用于覆盖全局配置。

### `manager.submit_tasks()`
用于批量提交任务。
```python
manager.submit_tasks(
    source: Union[int, List[Any]],
    task_func: Callable[[Target], Any],
    on_success: Optional[Callable[[Target, Any], None]] = None,
    on_error: Optional[Callable[[Target, Exception], None]] = None,
    retries: Optional[int] = None,
    retry_delay: Optional[float] = None,
)
```
- `source`: 任务源，可以是一个整数（任务数量）或一个列表（任务数据）。
- `task_func`: 你定义的任务处理函数，它必须只接收一个 `Target` 参数。
- `on_success` / `on_error`: 成功/失败回调。
- `retries` / `retry_delay`: 针对此批次任务的临时重试策略。

### `Target` 对象
`Target` 对象会作为唯一参数传递给你的 `task_func` 和回调函数。
- `target.index`: `int`, 任务在批次中的索引。
- `target.data`: `Any`, 任务关联的数据。
- `target.proxy`: `Optional[str]`, 分配给此任务的代理。
- `target.logger`: `loguru.Logger`, 为此任务绑定的专属 logger 实例，会自动包含任务编号。
