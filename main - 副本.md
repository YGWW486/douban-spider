# -*- coding: utf-8 -*-
"""
豆瓣电影Top250爬虫（参考python-douban-view项目）
功能：抓取豆瓣电影Top250的电影信息并保存到CSV文件
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import random
import logging
from urllib.parse import urljoin

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 设置请求头（更简单但更实用的配置）
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Connection': 'keep-alive',
    # 注意：使用时请替换为从浏览器复制的真实Cookie
    # 'Cookie': 'your_actual_cookie_from_browser'
}

def fetch_page(url):
    """
    获取页面内容的通用函数
    """
    try:
        # 随机延时，避免过快请求
        delay = random.uniform(2, 5)
        logger.info(f"请求前延时 {delay:.2f} 秒")
        time.sleep(delay)
        
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        response.encoding = 'utf-8'  # 确保编码正确
        
        # 检查响应内容
        if len(response.text) < 1000:
            logger.warning(f"返回内容异常，可能被反爬拦截，长度: {len(response.text)}")
            return None
        
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"网络请求失败: {e}")
        return None

def parse_movie_item(item):
    """
    解析单个电影项
    """
    try:
        # 提取电影名称（确保找到）
        title_elem = item.select_one('.title:nth-of-type(1)')
        title = title_elem.text if title_elem else '未知电影'
        
        # 提取评分
        rating_elem = item.select_one('.rating_num')
        rating = rating_elem.text if rating_elem else '0.0'
        
        # 提取评论数
        comment_elem = item.select_one('.star span:last-of-type')
        comment_num = comment_elem.text.replace('人评价', '') if comment_elem else '0'
        
        # 提取短评
        quote_elem = item.select_one('.inq')
        quote = quote_elem.text if quote_elem else '暂无短评'
        
        # 提取电影链接
        link_elem = item.select_one('a')
        link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else '#'
        
        # 提取基本信息（导演、演员、年份等）
        info_elem = item.select_one('.bd p')
        if info_elem:
            info_text = info_elem.text.strip()
            # 分割导演演员和年份信息
            info_lines = [line.strip() for line in info_text.split('\n') if line.strip()]
            director_actors = info_lines[0] if info_lines else '未知'
            year_country_genre = info_lines[1].strip() if len(info_lines) > 1 else '未知'
        else:
            director_actors = '未知'
            year_country_genre = '未知'
        
        return {
            'title': title,
            'rating': rating,
            'comment_num': comment_num,
            'quote': quote,
            'link': link,
            'director_actors': director_actors,
            'year_country_genre': year_country_genre
        }
    except Exception as e:
        logger.error(f"解析单部电影失败: {e}")
        return None

def scrape_page(page_start):
    """
    爬取指定起始位置的页面
    """
    base_url = 'https://movie.douban.com/top250'
    url = f'{base_url}?start={page_start}&filter='
    logger.info(f"开始爬取: {url}")
    
    html = fetch_page(url)
    if not html:
        return []
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # 使用CSS选择器查找所有电影项
        movie_items = soup.select('.grid_view li')
        if not movie_items:
            logger.warning("未找到电影项，可能页面结构变化或被反爬")
            return []
        
        logger.info(f"找到 {len(movie_items)} 个电影项")
        
        # 解析每个电影项
        movies = []
        for item in movie_items:
            movie_data = parse_movie_item(item)
            if movie_data:
                movies.append(movie_data)
        
        logger.info(f"成功解析 {len(movies)} 部电影")
        return movies
    except Exception as e:
        logger.error(f"解析页面失败: {e}")
        return []

def save_to_csv(movies):
    """
    将电影数据保存到CSV文件
    """
    if not movies:
        logger.warning("没有数据可保存")
        return False
    
    try:
        csv_file = 'douban_top250.csv'
        # 使用utf-8-sig确保中文在Excel中正确显示
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            # 使用字典写入器，更方便处理字段
            fieldnames = ['电影名称', '评分', '评论数', '短评', '导演和演员', '年份国家类型', '链接']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            # 写入表头
            writer.writeheader()
            
            # 写入数据
            for movie in movies:
                writer.writerow({
                    '电影名称': movie['title'],
                    '评分': movie['rating'],
                    '评论数': movie['comment_num'],
                    '短评': movie['quote'],
                    '导演和演员': movie['director_actors'],
                    '年份国家类型': movie['year_country_genre'],
                    '链接': movie['link']
                })
        
        logger.info(f"成功保存 {len(movies)} 部电影数据到 {csv_file}")
        return True
    except Exception as e:
        logger.error(f"保存CSV文件失败: {e}")
        return False

def main():
    """
    主函数
    """
    logger.info("开始爬取豆瓣电影Top250")
    logger.info("注意：豆瓣有严格的反爬机制，请确保代码中的Cookie已替换为真实值")
    
    all_movies = []
    total_movies = 250  # 总共250部电影
    batch_size = 25     # 每页25部
    test_mode = True    # 测试模式，只爬取第一页
    max_retries = 3     # 每页最大重试次数
    
    # 计算要爬取的页数
    if test_mode:
        total_pages = 1  # 测试模式只爬1页
    else:
        total_pages = total_movies // batch_size
    
    # 逐个页面爬取
    for page in range(total_pages):
        page_start = page * batch_size
        logger.info(f"===== 开始爬取第 {page+1}/{total_pages} 页 (start={page_start}) =====")
        
        # 重试机制
        page_movies = []
        for retry in range(max_retries):
            logger.info(f"  尝试第 {retry+1}/{max_retries} 次")
            
            # 爬取当前页
            current_movies = scrape_page(page_start)
            if current_movies:
                page_movies = current_movies
                logger.info(f"  爬取成功，获取到 {len(page_movies)} 部电影")
                break
            else:
                logger.warning(f"  爬取失败，{retry+1}秒后重试")
                time.sleep(retry + 1)  # 递增的重试间隔
        
        # 添加到总列表
        all_movies.extend(page_movies)
        
        # 页面间的间隔
        if page < total_pages - 1:
            delay = random.uniform(3, 6)
            logger.info(f"  页面间隔，等待 {delay:.2f} 秒")
            time.sleep(delay)
    
    # 保存结果
    if all_movies:
        success = save_to_csv(all_movies)
        if success:
            logger.info(f"爬取完成！总共获取到 {len(all_movies)} 部电影")
        else:
            logger.error("保存数据失败")
    else:
        logger.error("爬取失败，没有获取到任何电影数据")
        logger.error("请尝试以下解决方案：")
        logger.error("1. 从浏览器复制真实Cookie替换代码中的Cookie值")
        logger.error("2. 调整爬取间隔时间")
        logger.error("3. 检查网络连接状态")
        logger.error("4. 考虑使用代理IP")
    
    logger.info("程序结束")

if __name__ == '__main__':
    main()