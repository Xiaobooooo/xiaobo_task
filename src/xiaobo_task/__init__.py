"""
通用异步多线程任务框架

该模块提供了一个简单易用的异步任务管理器，允许调用者提交任务并在任务完成或失败时执行回调。
"""
import sys

from dotenv import load_dotenv
from loguru import logger

# 自动加载 .env 文件
load_dotenv()

# --- 日志配置 ---
# 移除默认的 logger，添加自定义格式的 logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <7}</level> | <cyan>[{extra[name]}]</cyan> - <level>{message}</level>",
    colorize=True,
    backtrace=False
)
logger.configure(extra={"name": "MainApp"})

# --- 公开接口 ---
# 从子模块中导入核心类和函数，以便用户直接从包顶级导入
from .domain import Target
from .manager import TaskManager
from .facade import XiaoboTask
from .util import read_txt_file_lines, to_bool

# 定义当 `from task_framework import *` 时要导入的名称
__all__ = [
    'Target',
    'TaskManager',  # 底层任务管理器
    'XiaoboTask',  # 高级封装，推荐使用
    'read_txt_file_lines',  # 工具函数：按行读取文件
    'to_bool',  # 工具函数：字符串转布尔
]
