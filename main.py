# -*- coding: utf-8 -*-
"""
豆瓣电影Top250爬虫主程序

本模块是豆瓣电影Top250爬虫的核心实现，提供了完整的电影信息爬取、解析和存储功能。

主要功能：
- 支持同步和异步两种爬取模式
- 实现断点续爬机制，支持程序中断后恢复爬取
- 包含错误重试、异常处理和日志记录
- 支持爬取电影列表和详情页信息
- 可将数据保存为JSON或CSV格式
- 提供命令行参数配置

使用方法：
- 同步模式：python main.py
- 异步模式：python main.py --async
- 自定义页码范围：python main.py --start-page 0 --end-page 10
- 自定义输出格式：python main.py --output-format csv
"""

import asyncio
import aiohttp
import requests
import json
import csv
import time
import random
import os
import logging
import re  # 添加正则表达式模块导入
from bs4 import BeautifulSoup
from functools import wraps
import argparse
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("spider.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 断点文件，用于存储爬取进度
BREAKPOINT_FILE = "breakpoint.json"

def load_breakpoint():
    """
    加载断点信息，用于断点续爬
    
    Returns:
        dict: 包含当前爬取进度的断点信息字典
            - current_page: 当前页码
            - total_movies: 已爬取电影总数
            - movies: 已爬取的电影列表
            若没有断点文件或加载失败则返回默认值
    """
    if os.path.exists(BREAKPOINT_FILE):
        try:
            with open(BREAKPOINT_FILE, 'r', encoding='utf-8') as f:
                breakpoint_info = json.load(f)
                logger.info(f"已加载断点信息，从页码 {breakpoint_info.get('current_page', 0)} 继续")
                return breakpoint_info
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"加载断点信息失败: {e}")
    return {"current_page": 0, "total_movies": 0, "movies": []}

def save_breakpoint(breakpoint_info):
    """
    保存断点信息到文件
    
    Args:
        breakpoint_info (dict): 包含当前爬取进度的断点信息字典
    """
    try:
        with open(BREAKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(breakpoint_info, f, ensure_ascii=False, indent=2)
        logger.info(f"断点已保存，当前页码: {breakpoint_info.get('current_page', 0)}")
    except IOError as e:
        logger.error(f"保存断点信息失败: {e}")

def retry(func):
    """
    重试装饰器，用于捕获请求异常并重试
    
    实现指数退避策略，每次重试的间隔时间递增
    
    Args:
        func (callable): 需要添加重试机制的函数
        
    Returns:
        callable: 包装后的函数，具有重试功能
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = kwargs.get('max_retries', 3)  # 最大重试次数
        retry_delay = kwargs.get('retry_delay', 5)  # 初始重试延迟时间（秒）
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    # 指数退避 + 随机延迟，避免请求风暴
                    delay = retry_delay * (2 ** (retry_count - 1)) + random.uniform(0, 2)
                    logger.warning(f"请求失败: {e}，{delay:.2f}秒后重试第 {retry_count} 次")
                    time.sleep(delay)
                else:
                    logger.error(f"达到最大重试次数 {max_retries}，请求失败: {e}")
                    raise
    return wrapper

def async_retry(func):
    """
    异步重试装饰器，用于捕获异步请求异常并重试
    
    实现指数退避策略，适用于async/await函数
    
    Args:
        func (callable): 需要添加重试机制的异步函数
        
    Returns:
        callable: 包装后的异步函数，具有重试功能
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        max_retries = kwargs.get('max_retries', 3)  # 最大重试次数
        retry_delay = kwargs.get('retry_delay', 5)  # 初始重试延迟时间（秒）
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    # 异步版本的指数退避策略
                    delay = retry_delay * (2 ** (retry_count - 1)) + random.uniform(0, 2)
                    logger.warning(f"异步请求失败: {e}，{delay:.2f}秒后重试第 {retry_count} 次")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"达到最大重试次数 {max_retries}，异步请求失败: {e}")
                    raise
    return wrapper

def parse_movie_info(html_content):
    """
    解析电影列表页面，提取电影基本信息
    
    Args:
        html_content (str): 网页HTML内容
        
    Returns:
        list: 电影信息列表，每个元素是包含电影详细信息的字典
    """
    movies = []
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 提取电影列表
    movie_list = soup.select('div.article > ol.grid_view > li')
    
    for item in movie_list:
        try:
            # 排名
            rank = int(item.select_one('em').text.strip())
            
            # 电影名称（主要名称）
            title_element = item.select_one('span.title:nth-of-type(1)')
            title = title_element.text.strip() if title_element else "未知"
            
            # 其他名称（如有）
            other_titles = [span.text.strip().replace('/', '').strip() 
                           for span in item.select('span.title:nth-of-type(n+2)')]
            other_title = '/'.join(other_titles) if other_titles else ""
            
            # 评分
            rating_element = item.select_one('span.rating_num')
            rating = float(rating_element.text.strip()) if rating_element else 0.0
            
            # 评论数
            comment_element = item.select_one('span.inq')
            comment_count_text = item.select_one('div.star > span:nth-of-type(4)')
            comment_count = int(''.join(filter(str.isdigit, comment_count_text.text))) if comment_count_text else 0
            
            # 评价语
            quote = comment_element.text.strip() if comment_element else ""
            
            # 导演、演员和其他信息
            info_element = item.select_one('div.info > div.bd > p:nth-of-type(1)')
            info_text = info_element.text.strip() if info_element else ""
            
            # 提取年份和国家/地区信息
            year_region_genre = None
            for line in info_text.split('\n'):
                stripped_line = line.strip()
                if stripped_line and '导演' not in stripped_line and '主演' not in stripped_line:
                    year_region_genre = stripped_line
                    break
            
            year = None
            region = None
            genre = None
            if year_region_genre:
                # 提取年份
                year_match = re.search(r'(\d{4})', year_region_genre)
                if year_match:
                    year = int(year_match.group(1))
                
                # 提取国家/地区和类型信息
                parts = year_region_genre.split('/')
                if len(parts) > 1:
                    region = parts[1].strip() if len(parts) > 1 else None
                    genre = parts[2].strip() if len(parts) > 2 else None
            
            # 图片链接
            img_element = item.select_one('div.pic > a > img')
            img_url = img_element.get('src', '') if img_element else ""
            
            # 电影链接
            link_element = item.select_one('div.pic > a')
            movie_url = link_element.get('href', '') if link_element else ""
            
            # 构建电影信息字典
            movie_info = {
                "排名": rank,
                "电影名称": title,
                "其他名称": other_title,
                "评分": rating,
                "评论数": comment_count,
                "评价语": quote,
                "年份": year,
                "地区": region,
                "类型": genre,
                "图片链接": img_url,
                "电影链接": movie_url
            }
            
            movies.append(movie_info)
            
        except Exception as e:
            logger.error(f"解析电影信息失败: {e}")
            continue
    
    return movies

@retry
def scrape_page_sync(url, headers=None):
    """
    同步爬取页面内容
    
    Args:
        url (str): 页面URL
        headers (dict, optional): 请求头，用于模拟浏览器行为
        
    Returns:
        str: 页面HTML内容
    """
    # 随机延时，避免被反爬
    time.sleep(random.uniform(1, 3))
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()  # 检查响应状态码
    response.encoding = 'utf-8'  # 设置编码为UTF-8
    
    return response.text

@async_retry
async def scrape_page_async(session, url, headers=None):
    """
    异步爬取页面内容
    
    Args:
        session (aiohttp.ClientSession): 异步会话对象
        url (str): 页面URL
        headers (dict, optional): 请求头，用于模拟浏览器行为
        
    Returns:
        str: 页面HTML内容
    """
    # 随机延时，避免被反爬
    await asyncio.sleep(random.uniform(0.5, 2))
    
    async with session.get(url, headers=headers, timeout=10) as response:
        response.raise_for_status()  # 检查响应状态码
        return await response.text()

@async_retry
async def fetch_movie_detail_async(session, url, headers=None):
    """
    异步爬取电影详情页，提取更多详细信息
    
    Args:
        session (aiohttp.ClientSession): 异步会话对象
        url (str): 电影详情页URL
        headers (dict, optional): 请求头
        
    Returns:
        dict: 电影详细信息字典
            - 导演: 电影导演
            - 编剧: 电影编剧
            - 主演: 电影主演
            - 片长: 电影时长
            - 简介: 电影剧情简介
    """
    try:
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        async with session.get(url, headers=headers, timeout=10) as response:
            response.raise_for_status()
            html = await response.text()
        
        soup = BeautifulSoup(html, 'lxml')
        
        # 提取导演、编剧、主演等详细信息
        info_section = soup.select_one('div#info')
        details = {}
        
        if info_section:
            info_text = info_section.text.strip()
            
            # 使用正则表达式提取导演信息
            director_match = re.search(r'导演[:：]\s*([^\n]+)', info_text)
            if director_match:
                details['导演'] = director_match.group(1).strip()
            
            # 提取编剧信息
            writer_match = re.search(r'编剧[:：]\s*([^\n]+)', info_text)
            if writer_match:
                details['编剧'] = writer_match.group(1).strip()
            
            # 提取主演信息
            actor_match = re.search(r'主演[:：]\s*([^\n]+)', info_text)
            if actor_match:
                details['主演'] = actor_match.group(1).strip()
            
            # 提取片长信息
            duration_match = re.search(r'片长[:：]\s*([^\n]+)', info_text)
            if duration_match:
                details['片长'] = duration_match.group(1).strip()
        
        # 提取剧情简介
        summary_section = soup.select_one('div#link-report span.short')
        if summary_section:
            details['简介'] = summary_section.text.strip()
        
        return details
    
    except Exception as e:
        logger.error(f"获取电影详情失败 ({url}): {e}")
        return {}

async def async_main(config):
    """
    异步爬取主函数，协调整个异步爬取流程
    
    Args:
        config (dict): 配置字典，包含爬取参数
    """
    # 从配置中提取参数
    start_page = config.get('start_page', 0)  # 起始页码
    end_page = config.get('end_page', 10)  # 结束页码
    concurrency = config.get('concurrency', 3)  # 并发数
    headers_pool = config.get('headers_pool', [])  # 请求头池
    output_format = config.get('output_format', 'json')  # 输出格式
    
    # 加载断点
    breakpoint_info = load_breakpoint()
    current_page = max(start_page, breakpoint_info.get('current_page', 0))
    all_movies = breakpoint_info.get('movies', [])
    
    # 如果从头开始爬取，清空断点
    if current_page == start_page and current_page == 0:
        all_movies = []
        breakpoint_info = {"current_page": 0, "total_movies": 0, "movies": []}
    
    base_url = "https://movie.douban.com/top250"  # 基础URL
    
    # 连续失败计数，用于终止爬取
    consecutive_failures = 0
    max_consecutive_failures = 3  # 最大连续失败次数
    
    try:
        # 创建异步会话，设置并发限制
        connector = aiohttp.TCPConnector(limit=concurrency)
        async with aiohttp.ClientSession(connector=connector) as session:
            logger.info(f"开始异步爬取豆瓣电影Top250，从第 {current_page+1} 页到第 {end_page+1} 页")
            
            # 逐页爬取
            while current_page <= end_page:
                # 检查连续失败次数
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"连续 {consecutive_failures} 页爬取失败，终止爬取")
                    break
                
                start = current_page * 25  # 计算起始索引（每页25部电影）
                url = f"{base_url}?start={start}&filter="
                logger.info(f"爬取页面 {current_page+1}/{end_page+1}: {url}")
                
                try:
                    # 随机选择请求头，增加请求多样性
                    headers = random.choice(headers_pool) if headers_pool else {}
                    
                    # 爬取页面
                    html_content = await scrape_page_async(session, url, headers=headers)
                    
                    # 解析电影信息
                    movies = parse_movie_info(html_content)
                    
                    if movies:
                        logger.info(f"成功解析 {len(movies)} 部电影信息")
                        all_movies.extend(movies)
                        consecutive_failures = 0  # 重置失败计数
                        
                        # 保存断点
                        current_page += 1
                        breakpoint_info["current_page"] = current_page
                        breakpoint_info["total_movies"] = len(all_movies)
                        breakpoint_info["movies"] = all_movies
                        save_breakpoint(breakpoint_info)
                        
                        # 检查是否爬够了电影数量（Top250）
                        if len(all_movies) >= 250:
                            logger.info("已爬取全部250部电影")
                            break
                    else:
                        consecutive_failures += 1
                        logger.warning(f"未能解析电影信息，连续失败 {consecutive_failures} 次")
                        # 短暂等待后重试当前页
                        await asyncio.sleep(5)
                        
                except Exception as e:
                    consecutive_failures += 1
                    logger.error(f"爬取页面失败: {e}，连续失败 {consecutive_failures} 次")
                    await asyncio.sleep(5)
            
            # 检查是否有电影数据
            if not all_movies:
                logger.error("未能获取任何电影数据")
                return
            
            # 保存数据
            logger.info(f"爬取完成，共获取 {len(all_movies)} 部电影信息")
            save_movies(all_movies, output_format)
            
            # 爬取完成后删除断点文件
            if os.path.exists(BREAKPOINT_FILE):
                os.remove(BREAKPOINT_FILE)
                logger.info("断点文件已删除")
                
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        # 保存断点
        breakpoint_info["current_page"] = current_page
        breakpoint_info["total_movies"] = len(all_movies)
        breakpoint_info["movies"] = all_movies
        save_breakpoint(breakpoint_info)
    except Exception as e:
        logger.error(f"异步爬取过程中发生错误: {e}")
        # 保存断点
        breakpoint_info["current_page"] = current_page
        breakpoint_info["total_movies"] = len(all_movies)
        breakpoint_info["movies"] = all_movies
        save_breakpoint(breakpoint_info)

def sync_main(config):
    """
    同步爬取主函数，协调整个同步爬取流程
    
    Args:
        config (dict): 配置字典，包含爬取参数
    """
    # 从配置中提取参数
    start_page = config.get('start_page', 0)
    end_page = config.get('end_page', 10)
    headers_pool = config.get('headers_pool', [])
    output_format = config.get('output_format', 'json')
    
    # 加载断点
    breakpoint_info = load_breakpoint()
    current_page = max(start_page, breakpoint_info.get('current_page', 0))
    all_movies = breakpoint_info.get('movies', [])
    
    # 如果从头开始爬取，清空断点
    if current_page == start_page and current_page == 0:
        all_movies = []
        breakpoint_info = {"current_page": 0, "total_movies": 0, "movies": []}
    
    base_url = "https://movie.douban.com/top250"
    
    # 连续失败计数，用于终止爬取
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    try:
        logger.info(f"开始同步爬取豆瓣电影Top250，从第 {current_page+1} 页到第 {end_page+1} 页")
        
        # 逐页爬取
        while current_page <= end_page:
            # 检查连续失败次数
            if consecutive_failures >= max_consecutive_failures:
                logger.error(f"连续 {consecutive_failures} 页爬取失败，终止爬取")
                break
            
            start = current_page * 25
            url = f"{base_url}?start={start}&filter="
            logger.info(f"爬取页面 {current_page+1}/{end_page+1}: {url}")
            
            try:
                # 随机选择请求头
                headers = random.choice(headers_pool) if headers_pool else {}
                
                # 爬取页面
                html_content = scrape_page_sync(url, headers=headers)
                
                # 解析电影信息
                movies = parse_movie_info(html_content)
                
                if movies:
                    logger.info(f"成功解析 {len(movies)} 部电影信息")
                    all_movies.extend(movies)
                    consecutive_failures = 0  # 重置失败计数
                    
                    # 保存断点
                    current_page += 1
                    breakpoint_info["current_page"] = current_page
                    breakpoint_info["total_movies"] = len(all_movies)
                    breakpoint_info["movies"] = all_movies
                    save_breakpoint(breakpoint_info)
                    
                    # 检查是否爬够了电影数量
                    if len(all_movies) >= 250:
                        logger.info("已爬取全部250部电影")
                        break
                else:
                    consecutive_failures += 1
                    logger.warning(f"未能解析电影信息，连续失败 {consecutive_failures} 次")
                    # 短暂等待后重试当前页
                    time.sleep(5)
                    
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"爬取页面失败: {e}，连续失败 {consecutive_failures} 次")
                time.sleep(5)
        
        # 检查是否有电影数据
        if not all_movies:
            logger.error("未能获取任何电影数据")
            return
        
        # 保存数据
        logger.info(f"爬取完成，共获取 {len(all_movies)} 部电影信息")
        save_movies(all_movies, output_format)
        
        # 爬取完成后删除断点文件
        if os.path.exists(BREAKPOINT_FILE):
            os.remove(BREAKPOINT_FILE)
            logger.info("断点文件已删除")
            
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        # 保存断点
        breakpoint_info["current_page"] = current_page
        breakpoint_info["total_movies"] = len(all_movies)
        breakpoint_info["movies"] = all_movies
        save_breakpoint(breakpoint_info)
    except Exception as e:
        logger.error(f"同步爬取过程中发生错误: {e}")
        # 保存断点
        breakpoint_info["current_page"] = current_page
        breakpoint_info["total_movies"] = len(all_movies)
        breakpoint_info["movies"] = all_movies
        save_breakpoint(breakpoint_info)

def save_movies(movies, format="json"):
    """
    保存电影数据到文件
    
    Args:
        movies (list): 电影信息列表
        format (str): 输出格式，支持 'json' 和 'csv'
    """
    try:
        if format.lower() == "json":
            # 保存为JSON
            with open("douban_top250.json", "w", encoding="utf-8") as f:
                json.dump(movies, f, ensure_ascii=False, indent=2)
            logger.info("数据已保存到 douban_top250.json")
        else:
            # 保存为CSV
            if movies:
                with open("douban_top250.csv", "w", newline="", encoding="utf-8-sig") as f:
                    # 获取所有可能的字段名
                    fieldnames = list(movies[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(movies)
                logger.info("数据已保存到 douban_top250.csv")
    except Exception as e:
        logger.error(f"保存数据失败: {e}")

def main():
    """
    主函数，负责加载配置、解析命令行参数、启动爬虫
    
    解析命令行参数，加载配置文件，根据参数选择同步或异步模式启动爬虫
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='豆瓣电影Top250爬虫')
    parser.add_argument('--async', action='store_true', dest='use_async', help='使用异步爬取模式')
    parser.add_argument('--start-page', type=int, default=0, help='起始页码')
    parser.add_argument('--end-page', type=int, default=10, help='结束页码')
    parser.add_argument('--concurrency', type=int, default=3, help='异步模式下的并发数')
    parser.add_argument('--output-format', choices=['json', 'csv'], default='json', help='输出格式')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 导入配置模块
    from config import DEFAULT_CONFIG, load_config
    
    # 加载配置文件
    config = load_config()
    
    # 更新配置（命令行参数优先级高于配置文件）
    config['start_page'] = args.start_page
    config['end_page'] = args.end_page
    config['concurrency'] = args.concurrency
    config['output_format'] = args.output_format
    
    logger.info(f"爬虫配置: 使用{'异步' if args.use_async else '同步'}模式, 页码范围 {args.start_page+1}-{args.end_page+1}")
    
    try:
        if args.use_async:
            # 运行异步爬取模式
            asyncio.run(async_main(config))
        else:
            # 运行同步爬取模式
            sync_main(config)
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        sys.exit(1)
    
    logger.info("爬虫程序已完成")

if __name__ == "__main__":
    main()