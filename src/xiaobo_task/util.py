# -*- coding: utf-8 -*-
"""
通用工具模块
"""
import asyncio
import threading
from typing import List, Optional

from curl_cffi import BrowserTypeLiteral, Session, AsyncSession
from curl_cffi.requests.impersonate import DEFAULT_CHROME

# 使用线程本地存储为每个线程维护一个独立的事件循环
_thread_local = threading.local()


def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """获取或创建当前线程的事件循环。"""
    if not hasattr(_thread_local, "loop"):
        _thread_local.loop = asyncio.new_event_loop()
    return _thread_local.loop


def read_txt_file_lines(filename: str) -> List[str]:
    """
    读取txt文件内容并按行返回一个列表。

    功能:
    - 如果文件名没有 .txt 后缀(不区分大小写)，会自动补全。
    - 按行读取文件，并去除每行两侧的空白字符（包括换行符）。
    - 返回一个包含文件中所有非空行的字符串列表。

    :param filename: 要读取的txt文件名。
    :return: 包含文件所有行的字符串列表。
    :raises FileNotFoundError: 如果文件未找到。
    :raises IOError: 如果发生其他读取错误。
    """
    if not filename.lower().endswith('.txt'):
        filename += '.txt'

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            # 使用列表推导式高效读取，并只保留非空行
            lines = [line.strip() for line in f if line.strip()]
        return lines
    except FileNotFoundError:
        raise FileNotFoundError(f"错误：文件 '{filename}' 未找到。")
    except Exception as e:
        raise IOError(f"读取文件 '{filename}' 时发生错误: {e}")


def get_session(proxy: str = None, timeout: int = 30, impersonate: Optional[BrowserTypeLiteral] = DEFAULT_CHROME):
    return Session(proxy=proxy, timeout=timeout, impersonate=impersonate)


def get_async_session(proxy: str = None, timeout: int = 30, impersonate: Optional[BrowserTypeLiteral] = DEFAULT_CHROME):
    return AsyncSession(proxy=proxy, timeout=timeout, impersonate=impersonate)
