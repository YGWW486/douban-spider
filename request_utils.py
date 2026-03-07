# -*- coding: utf-8 -*-
"""
豆瓣电影Top250爬虫网络请求模块
功能：处理HTTP请求，支持同步/异步请求、Cookie管理、代理池和请求延时控制
作者：
版本：1.0
"""

import os
import time
import random
import logging
import requests
import aiohttp
import asyncio  # 添加asyncio导入
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RequestUtils:
    """
    网络请求工具类
    提供同步和异步HTTP请求方法，支持Cookie管理、代理池和请求延时控制
    功能：
    - 从文件加载和保存Cookie
    - 提供随机请求头
    - 代理管理和有效性检查
    - 请求频率控制
    - 同步和异步页面获取
    - 错误处理和状态码分析
    """
    
    def __init__(self, config, custom_cookie=None):
        """
        初始化请求工具
        
        Args:
            config (dict): 配置字典，包含headers_pool、timeout、proxies_pool等配置
            custom_cookie (str, optional): 自定义Cookie值，优先级高于配置文件中的Cookie
        """
        self.config = config
        self.headers_pool = config.get('headers_pool', [])
        self.timeout = config.get('timeout', 10)  # 请求超时时间
        self.proxies_pool = config.get('proxies_pool', [])  # 代理池
        self.delay_range = config.get('delay_range', [2, 5])  # 请求延迟范围
        self.cookie_file = config.get('cookie_file', 'cookies.txt')  # Cookie文件路径
        self.custom_cookie = custom_cookie  # 自定义Cookie
        
        # 加载Cookie
        self.cookies = self.load_cookies()
        
        # 最后请求时间，用于控制请求频率
        self.last_request_time = 0
        
        # 代理有效性缓存，避免重复检查
        self.proxy_valid_cache = {}
    
    def load_cookies(self):
        """
        从文件加载Cookie
        
        Returns:
            dict: Cookie字典，如果加载失败返回空字典
        """
        try:
            if os.path.exists(self.cookie_file):
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    cookie_content = f.read().strip()
                    if cookie_content:
                        # 将Cookie字符串转换为字典
                        cookies = {}
                        for cookie in cookie_content.split(';'):
                            if '=' in cookie:
                                name, value = cookie.split('=', 1)
                                cookies[name.strip()] = value.strip()
                        logger.info(f"成功从文件加载Cookie: {self.cookie_file}")
                        return cookies
        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")
        return {}
    
    def save_cookies(self, cookies):
        """
        保存Cookie到文件
        
        Args:
            cookies (dict): 要保存的Cookie字典
        """
        try:
            # 将Cookie字典转换为字符串
            cookie_str = '; '.join([f'{k}={v}' for k, v in cookies.items()])
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                f.write(cookie_str)
            logger.info(f"成功保存Cookie到文件: {self.cookie_file}")
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
    
    def get_random_header(self):
        """
        获取随机请求头
        优先从请求头池中选择，如果为空则使用默认请求头
        会自动添加Cookie信息
        
        Returns:
            dict: 随机选择的请求头
        """
        if self.headers_pool:
            header = random.choice(self.headers_pool).copy()
            
            # 如果有自定义Cookie，添加到请求头
            if self.custom_cookie:
                header['Cookie'] = self.custom_cookie
            elif self.cookies:
                # 使用加载的Cookie
                header['Cookie'] = '; '.join([f'{k}={v}' for k, v in self.cookies.items()])
            
            return header
        
        # 默认请求头
        default_header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        if self.custom_cookie:
            default_header['Cookie'] = self.custom_cookie
        elif self.cookies:
            default_header['Cookie'] = '; '.join([f'{k}={v}' for k, v in self.cookies.items()])
        
        return default_header
    
    def get_proxy(self):
        """
        获取一个有效的代理
        从代理池中随机选择一个有效代理
        
        Returns:
            dict or None: 代理字典，如果没有有效代理则返回None
        """
        if not self.proxies_pool:
            logger.warning("代理池为空，无法提供代理")
            return None
        
        # 过滤出有效的代理
        valid_proxies = [p for p in self.proxies_pool if self.is_proxy_valid(p)]
        
        if valid_proxies:
            proxy = random.choice(valid_proxies)
            logger.info(f"使用代理: {proxy.get('http') or proxy.get('https')}")
            return proxy
        else:
            logger.warning("没有可用的有效代理")
            return None
    
    def is_proxy_valid(self, proxy):
        """
        检查代理是否有效
        使用百度首页测试代理连接性
        结果会缓存5分钟，避免频繁检查
        
        Args:
            proxy (dict): 代理字典
            
        Returns:
            bool: 代理是否有效
        """
        proxy_key = proxy.get('http') or proxy.get('https')
        
        # 检查缓存
        if proxy_key in self.proxy_valid_cache:
            cached_time, is_valid = self.proxy_valid_cache[proxy_key]
            # 缓存有效期为5分钟
            if time.time() - cached_time < 300:
                return is_valid
        
        # 测试代理有效性
        try:
            test_url = 'https://www.baidu.com'
            response = requests.get(test_url, proxies=proxy, timeout=5)
            is_valid = response.status_code == 200
            self.proxy_valid_cache[proxy_key] = (time.time(), is_valid)
            return is_valid
        except:
            self.proxy_valid_cache[proxy_key] = (time.time(), False)
            return False
    
    def control_request_rate(self):
        """
        控制请求频率，避免请求过快被封
        根据配置的延迟范围，确保两次请求间隔足够
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # 计算需要等待的时间
        min_delay, max_delay = self.delay_range
        required_delay = random.uniform(min_delay, max_delay)
        
        if time_since_last < required_delay:
            wait_time = required_delay - time_since_last
            logger.info(f"控制请求频率，等待 {wait_time:.2f} 秒")
            time.sleep(wait_time)
        
        # 更新最后请求时间
        self.last_request_time = time.time()
    
    def fetch_page(self, url, use_proxy=False):
        """
        同步获取页面内容
        
        Args:
            url (str): 要获取的URL
            use_proxy (bool): 是否使用代理
            
        Returns:
            str or None: 页面HTML内容，如果获取失败返回None
        """
        # 控制请求频率
        self.control_request_rate()
        
        headers = self.get_random_header()
        proxies = self.get_proxy() if use_proxy else None
        
        logger.info(f"开始同步请求: {url}")
        
        try:
            response = requests.get(
                url,
                headers=headers,
                proxies=proxies,
                timeout=self.timeout,
                allow_redirects=True
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 检查内容长度，避免获取到空内容
            content_len = len(response.text)
            if content_len < 1000:
                logger.warning(f"页面内容过短 ({content_len} 字节)，可能被反爬拦截: {url}")
                return None
            
            logger.info(f"成功获取页面，状态码: {response.status_code}, 内容长度: {content_len} 字节")
            
            # 保存Cookie（如果有）
            if response.cookies:
                self.cookies.update(response.cookies.get_dict())
                self.save_cookies(self.cookies)
            
            # 尝试检测编码并解码
            response.encoding = response.apparent_encoding
            return response.text
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 'Unknown'
            logger.error(f"HTTP错误: {status_code} - {e} - URL: {url}")
            
            # 处理特定状态码
            if status_code == 403:
                logger.error("403错误，可能被IP封禁或需要登录")
                # 可以尝试切换代理或更新Cookie
            elif status_code == 302:
                logger.error("302重定向，可能需要登录")
                # 可能需要更新Cookie
                
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e} - URL: {url}")
            return None
    
    async def fetch_page_async(self, session, url, use_proxy=False):
        """
        异步获取页面内容
        
        Args:
            session (aiohttp.ClientSession): 异步会话
            url (str): 要获取的URL
            use_proxy (bool): 是否使用代理
            
        Returns:
            str or None: 页面HTML内容，如果获取失败返回None
        """
        # 控制请求频率
        self.control_request_rate()
        
        headers = self.get_random_header()
        proxy_url = None
        
        if use_proxy and self.proxies_pool:
            proxy = self.get_proxy()
            if proxy:
                # 选择合适的代理URL
                if url.startswith('https'):
                    proxy_url = proxy.get('https')
                else:
                    proxy_url = proxy.get('http')
        
        logger.info(f"开始异步请求: {url}")
        
        try:
            async with session.get(
                url,
                headers=headers,
                proxy=proxy_url,
                timeout=self.timeout,
                allow_redirects=True
            ) as response:
                # 检查响应状态
                response.raise_for_status()
                
                # 获取内容
                text = await response.text()
                content_len = len(text)
                
                if content_len < 1000:
                    logger.warning(f"页面内容过短 ({content_len} 字节)，可能被反爬拦截: {url}")
                    return None
                
                logger.info(f"成功获取页面，状态码: {response.status}, 内容长度: {content_len} 字节")
                
                # 保存Cookie（如果有）
                if response.cookies:
                    cookie_dict = {k: v.value for k, v in response.cookies.items()}
                    self.cookies.update(cookie_dict)
                    self.save_cookies(self.cookies)
                
                return text
                
        except aiohttp.ClientResponseError as e:
            logger.error(f"HTTP错误: {e.status} - {e} - URL: {url}")
            
            # 处理特定状态码
            if e.status == 403:
                logger.error("403错误，可能被IP封禁或需要登录")
                # 可以尝试切换代理或更新Cookie
            elif e.status == 302:
                logger.error("302重定向，可能需要登录")
                # 可能需要更新Cookie
                
            return None
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"请求异常: {e} - URL: {url}")
            return None

# 示例用法
if __name__ == '__main__':
    """
    示例代码，展示RequestUtils类的使用方法
    包含同步和异步请求示例
    """
    # 创建默认配置
    default_config = {
        'headers_pool': [
            {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        ],
        'timeout': 10,
        'delay_range': [1, 2]
    }
    
    # 初始化请求工具
    request_utils = RequestUtils(default_config)
    
    # 测试同步请求
    print("测试同步请求:")
    html = request_utils.fetch_page('https://movie.douban.com/top250?start=0')
    if html:
        print(f"成功获取页面，长度: {len(html)} 字符")
    else:
        print("获取页面失败")
    
    # 测试异步请求
    print("\n测试异步请求:")
    
    async def test_async():
        async with aiohttp.ClientSession() as session:
            html = await request_utils.fetch_page_async(session, 'https://movie.douban.com/top250?start=0')
            if html:
                print(f"成功获取页面，长度: {len(html)} 字符")
            else:
                print("获取页面失败")
    
    try:
        asyncio.run(test_async())
    except Exception as e:
        print(f"异步请求测试失败: {e}")