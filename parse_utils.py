# -*- coding: utf-8 -*-
"""
豆瓣电影Top250爬虫HTML解析模块
功能：解析电影列表页面和详情页面，提取电影相关信息
作者：
版本：1.0
"""

import re
import logging
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ParseUtils:
    """
    HTML解析工具类
    负责解析豆瓣电影页面，提取电影信息
    包含电影列表解析、电影详情解析和数据验证功能
    """
    
    def __init__(self):
        """
        初始化解析工具
        设置用于信息提取的正则表达式
        """
        # 定义正则表达式用于提取信息
        self.score_pattern = re.compile(r'\d+\.\d+')  # 匹配评分 (如 9.7)
        self.votes_pattern = re.compile(r'(\d+)人评价')  # 匹配评价人数
        self.year_pattern = re.compile(r'(\d{4})')  # 匹配年份
        self.duration_pattern = re.compile(r'(\d+)分钟')  # 匹配电影时长
    
    def parse_movie_item(self, item_soup):
        """
        解析单个电影项
        
        Args:
            item_soup (bs4.element.Tag): 包含单个电影信息的BeautifulSoup对象
            
        Returns:
            dict: 电影信息字典，包含标题、评分、评论数等信息
        """
        movie = {
            'title': '',  # 电影标题
            'original_title': '',  # 英文名/原名
            'score': 0.0,  # 评分
            'votes': 0,  # 评论数
            'quote': '',  # 短评
            'link': '',  # 电影详情页链接
            'cover': '',  # 封面图片链接
            'info': ''  # 基本信息（导演、演员、类型等）
        }
        
        try:
            # 提取标题
            title_elem = item_soup.select_one('.title:nth-child(1)')
            if title_elem:
                movie['title'] = title_elem.text.strip()
            
            # 提取英文名/原名
            original_title_elem = item_soup.select_one('.title:nth-child(2)')
            if original_title_elem:
                # 移除多余的空格和斜杠
                movie['original_title'] = original_title_elem.text.strip().lstrip('/').strip()
            
            # 提取评分
            score_elem = item_soup.select_one('.rating_num')
            if score_elem:
                score_text = score_elem.text.strip()
                if score_text and score_text.replace('.', '', 1).isdigit():
                    movie['score'] = float(score_text)
            
            # 提取评论数
            # 策略1: 直接查找评分旁边的span元素
            rating_people_elem = item_soup.select_one('.rating_people')
            if rating_people_elem:
                # 查找评分人数的标签
                votes_text = rating_people_elem.text.strip()
                match = self.votes_pattern.search(votes_text)
                if match:
                    movie['votes'] = int(match.group(1))
            
            # 策略2: 如果策略1失败，尝试查找包含"人评价"的span标签
            if movie['votes'] == 0:
                span_elements = item_soup.find_all('span')
                for span in span_elements:
                    if span.text and '人评价' in span.text:
                        match = self.votes_pattern.search(span.text)
                        if match:
                            movie['votes'] = int(match.group(1))
                            break
            
            # 提取短评
            quote_elem = item_soup.select_one('.inq')
            if quote_elem:
                movie['quote'] = quote_elem.text.strip()
            
            # 提取链接
            link_elem = item_soup.select_one('.hd > a')
            if link_elem and link_elem.get('href'):
                movie['link'] = link_elem.get('href').strip()
            
            # 提取封面图片
            cover_elem = item_soup.select_one('.pic img')
            if cover_elem and cover_elem.get('src'):
                movie['cover'] = cover_elem.get('src').strip()
            
            # 提取基本信息（导演、演员、年份、类型等）
            info_elem = item_soup.select_one('.bd p:nth-of-type(1)')
            if info_elem:
                movie['info'] = info_elem.text.strip()
            
            # 日志记录
            logger.info(f"解析电影: {movie['title']}, 评分: {movie['score']}, 评价数: {movie['votes']}")
            
        except Exception as e:
            logger.error(f"解析电影项失败: {e}")
        
        return movie
    
    def validate_movie_data(self, movie):
        """
        验证电影数据的有效性
        
        Args:
            movie (dict): 电影信息字典
            
        Returns:
            bool: 电影数据是否有效
        """
        # 检查评分是否合理
        if movie['score'] < 7.0:
            logger.warning(f"电影评分过低: {movie['title']} - {movie['score']}")
            return False
        
        # 检查评论数是否合理
        if movie['votes'] < 100:
            logger.warning(f"电影评论数过少: {movie['title']} - {movie['votes']}")
            return False
        
        # 检查标题和链接是否存在
        if not movie['title'] or not movie['link']:
            logger.warning(f"电影标题或链接缺失: {movie}")
            return False
        
        return True
    
    def parse_movie_detail(self, html, movie=None):
        """
        解析电影详情页
        
        Args:
            html (str): 详情页HTML内容
            movie (dict, optional): 已有的电影信息字典
            
        Returns:
            dict: 包含详细信息的电影字典
        """
        # 如果没有提供电影字典，创建一个新的
        if not movie:
            movie = {}
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取电影时长
            duration = self._extract_duration(soup)
            if duration:
                movie['duration'] = duration
            
            # 提取剧情简介
            summary = self._extract_summary(soup)
            if summary:
                movie['summary'] = summary
            
            # 提取导演信息
            director = self._extract_director(soup)
            if director:
                movie['director'] = director
            
            # 提取主演信息
            actors = self._extract_actors(soup)
            if actors:
                movie['actors'] = actors
            
            # 提取类型信息
            genres = self._extract_genres(soup)
            if genres:
                movie['genres'] = genres
            
            # 提取地区信息
            regions = self._extract_regions(soup)
            if regions:
                movie['regions'] = regions
            
            # 提取语言信息
            languages = self._extract_languages(soup)
            if languages:
                movie['languages'] = languages
                
            # 提取上映日期
            release_date = self._extract_release_date(soup)
            if release_date:
                movie['release_date'] = release_date
            
            logger.info(f"成功解析详情: {movie.get('title', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"解析详情页失败: {e}")
        
        return movie
    
    def _extract_duration(self, soup):
        """
        从详情页提取电影时长
        
        Args:
            soup (BeautifulSoup): BeautifulSoup对象
            
        Returns:
            str or None: 电影时长
        """
        try:
            # 查找包含时长的标签
            info_elems = soup.find_all('span', class_='pl')
            for elem in info_elems:
                if '片长' in elem.text:
                    next_sibling = elem.next_sibling
                    if next_sibling:
                        duration_text = str(next_sibling).strip()
                        # 使用正则提取分钟数
                        match = self.duration_pattern.search(duration_text)
                        if match:
                            return match.group(1) + '分钟'
                        return duration_text
            return None
        except Exception:
            return None
    
    def _extract_summary(self, soup):
        """
        从详情页提取剧情简介
        
        Args:
            soup (BeautifulSoup): BeautifulSoup对象
            
        Returns:
            str or None: 剧情简介
        """
        try:
            # 查找剧情简介标签
            summary_elem = soup.find('span', class_='all hidden')
            if not summary_elem:
                # 如果没有展开的简介，查找默认简介
                summary_elem = soup.find('span', property='v:summary')
            
            if summary_elem:
                return summary_elem.text.strip()
            return None
        except Exception:
            return None
    
    def _extract_director(self, soup):
        """
        从详情页提取导演信息
        
        Args:
            soup (BeautifulSoup): BeautifulSoup对象
            
        Returns:
            str or None: 导演姓名
        """
        try:
            # 查找导演标签
            director_elem = soup.find('span', class_='attrs').find('a')
            if director_elem:
                return director_elem.text.strip()
            return None
        except Exception:
            return None
    
    def _extract_actors(self, soup):
        """
        从详情页提取主演信息
        
        Args:
            soup (BeautifulSoup): BeautifulSoup对象
            
        Returns:
            list or None: 主演列表
        """
        try:
            # 找到"主演"标签后面的演员列表
            pl_elems = soup.find_all('span', class_='pl')
            for elem in pl_elems:
                if '主演' in elem.text:
                    actors_container = elem.find_next('span', class_='attrs')
                    if actors_container:
                        actors = [a.text.strip() for a in actors_container.find_all('a')]
                        return actors[:5]  # 只返回前5个主演
            return None
        except Exception:
            return None
    
    def _extract_genres(self, soup):
        """
        从详情页提取类型信息
        
        Args:
            soup (BeautifulSoup): BeautifulSoup对象
            
        Returns:
            list or None: 类型列表
        """
        try:
            genres = [g.text.strip() for g in soup.find_all('span', property='v:genre')]
            return genres if genres else None
        except Exception:
            return None
    
    def _extract_regions(self, soup):
        """
        从详情页提取地区信息
        
        Args:
            soup (BeautifulSoup): BeautifulSoup对象
            
        Returns:
            list or None: 地区列表
        """
        try:
            info_elems = soup.find_all('span', class_='pl')
            for elem in info_elems:
                if '制片国家/地区' in elem.text:
                    next_sibling = elem.next_sibling
                    if next_sibling:
                        regions = [r.strip() for r in str(next_sibling).strip().split('/')]
                        return regions
            return None
        except Exception:
            return None
    
    def _extract_languages(self, soup):
        """
        从详情页提取语言信息
        
        Args:
            soup (BeautifulSoup): BeautifulSoup对象
            
        Returns:
            list or None: 语言列表
        """
        try:
            info_elems = soup.find_all('span', class_='pl')
            for elem in info_elems:
                if '语言' in elem.text:
                    next_sibling = elem.next_sibling
                    if next_sibling:
                        languages = [l.strip() for l in str(next_sibling).strip().split('/')]
                        return languages
            return None
        except Exception:
            return None
    
    def _extract_release_date(self, soup):
        """
        从详情页提取上映日期
        
        Args:
            soup (BeautifulSoup): BeautifulSoup对象
            
        Returns:
            str or None: 上映日期
        """
        try:
            release_date_elem = soup.find('span', property='v:initialReleaseDate')
            if release_date_elem:
                return release_date_elem.text.strip()
            return None
        except Exception:
            return None
    
    def parse_movie_list(self, html):
        """
        解析电影列表页面
        
        Args:
            html (str): 列表页HTML内容
            
        Returns:
            list: 电影信息列表
        """
        movies = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 查找所有电影项
            movie_items = soup.select('.grid_view li')
            logger.info(f"找到 {len(movie_items)} 个电影项")
            
            # 逐个解析电影项
            for item in movie_items:
                movie = self.parse_movie_item(item)
                
                # 验证电影数据
                if self.validate_movie_data(movie):
                    movies.append(movie)
                else:
                    logger.warning(f"跳过无效电影数据: {movie['title']}")
            
            logger.info(f"成功解析 {len(movies)} 部有效电影")
            
        except Exception as e:
            logger.error(f"解析电影列表失败: {e}")
        
        return movies

# 示例用法
if __name__ == '__main__':
    """
    示例代码，展示ParseUtils类的使用方法
    实际使用时，HTML内容会从网络获取
    """
    # 示例HTML（实际使用时会从网络获取）
    sample_html = """
    <ol class="grid_view">
        <li>
            <div class="item">
                <div class="pic">
                    <em class="">1</em>
                    <a href="https://movie.douban.com/subject/1292052/">
                        <img width="100" alt="肖申克的救赎" src="https://img9.doubanio.com/view/photo/s_ratio_poster/public/p480747492.webp" class="">
                    </a>
                </div>
                <div class="info">
                    <div class="hd">
                        <a href="https://movie.douban.com/subject/1292052/" class="">
                            <span class="title">肖申克的救赎</span>
                            <span class="title">/ The Shawshank Redemption</span>
                            <span class="other">/ 月黑高飞(港) / 刺激1995(台)</span>
                        </a>
                    </div>
                    <div class="bd">
                        <p class="">导演: 弗兰克·德拉邦特 Frank Darabont<br>
                        主演: 蒂姆·罗宾斯 Tim Robbins / 摩根·弗里曼 Morgan Freeman<br>
                        类型: 剧情 / 犯罪<br>
                        制片国家/地区: 美国<br>
                        语言: 英语<br>
                        上映日期: 1994-09-23(加拿大)</p>
                        <div class="star">
                            <span class="rating5-t"></span>
                            <span class="rating_num" property="v:average">9.7</span>
                            <span property="v:best" content="10.0"></span>
                            <span class="rating_people">
                                <span property="v:votes">2683999</span>人评价
                            </span>
                        </div>
                        <p class="quote">
                            <span class="inq">希望让人自由。</span>
                        </p>
                    </div>
                </div>
            </div>
        </li>
    </ol>
    """
    
    # 初始化解析工具
    parse_utils = ParseUtils()
    
    # 解析电影列表
    movies = parse_utils.parse_movie_list(sample_html)
    
    # 打印结果
    print(f"解析到 {len(movies)} 部电影")
    for movie in movies:
        print(f"电影: {movie['title']}")
        print(f"评分: {movie['score']}")
        print(f"评价数: {movie['votes']}")
        print(f"短评: {movie['quote']}")
        print(f"链接: {movie['link']}")
        print("---")