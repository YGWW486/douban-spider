#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣电影Top250爬虫 - 数据存储模块

该模块负责爬虫数据的持久化存储，支持CSV、JSON和MySQL三种输出格式，
提供统一的数据保存接口，并包含记录去重、数据合并等功能。

主要功能：
- 支持CSV文件存储，适用于简单数据分析
- 支持JSON文件存储，方便与其他系统集成
- 支持MySQL数据库存储，适用于大规模数据和查询需求
- 自动去重，避免重复存储相同电影数据
- 数据合并功能，可将新数据与已存储数据整合
- 支持记录数限制，防止数据过大
"""

import os
import json
import csv
import logging
from typing import List, Dict
import pymysql
from pymysql.cursors import DictCursor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class StorageUtils:
    """电影数据存储工具类
    
    提供多种格式的电影数据持久化方法，包括CSV、JSON和MySQL数据库存储，
    并实现了数据去重、合并和记录限制等功能。
    
    Attributes:
        config (Dict): 存储配置信息
        output_dir (str): 输出目录路径
        db_conn: 数据库连接对象
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化存储工具
        
        Args:
            config (Dict, optional): 配置参数，包含以下键值对：
                - output_type: 输出类型，可选值: 'csv', 'json', 'mysql'
                - output_dir: 输出目录路径
                - overwrite: 是否覆盖已存在文件
                - max_records: 最大记录数限制
                - db_host: 数据库主机地址
                - db_user: 数据库用户名
                - db_password: 数据库密码
                - db_name: 数据库名称
                - db_port: 数据库端口号
        """
        # 默认配置
        default_config = {
            'output_type': 'csv',  # 默认输出类型为CSV
            'output_dir': './output',  # 默认输出目录
            'overwrite': False,  # 默认不覆盖文件
            'max_records': None,  # 默认无记录数限制
            'db_host': 'localhost',
            'db_user': 'root',
            'db_password': '',
            'db_name': 'douban_movies',
            'db_port': 3306
        }
        
        # 合并配置
        self.config = default_config.copy()
        if config:
            self.config.update(config)
        
        self.output_dir = self.config['output_dir']
        self.db_conn = None
        
        # 创建输出目录
        self._create_output_dir()
    
    def _create_output_dir(self):
        """
        创建输出目录
        
        Returns:
            bool: 是否创建成功
        """
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                logger.info(f"创建输出目录: {self.output_dir}")
            return True
        except Exception as e:
            logger.error(f"创建输出目录失败: {e}")
            return False
    
    def get_existing_movie_links(self, output_file: str) -> set:
        """
        获取已存在的电影链接集合，用于去重
        
        Args:
            output_file (str): 输出文件路径
            
        Returns:
            set: 电影链接集合
        """
        links = set()
        
        try:
            # 根据文件类型选择不同的解析方法
            if output_file.endswith('.json'):
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        for movie in existing_data:
                            if 'link' in movie:
                                links.add(movie['link'])
            elif output_file.endswith('.csv'):
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if 'link' in row:
                                links.add(row['link'])
            
            logger.info(f"已加载 {len(links)} 个已存在的电影链接")
        except Exception as e:
            logger.error(f"获取已存在电影链接失败: {e}")
        
        return links
    
    def save_to_csv(self, movies: List[Dict]) -> bool:
        """
        保存电影数据到CSV文件
        
        Args:
            movies (List[Dict]): 电影数据列表，每个字典包含电影信息
            
        Returns:
            bool: 是否保存成功
        """
        if not movies:
            logger.warning("没有电影数据需要保存到CSV")
            return False
        
        csv_file = os.path.join(self.output_dir, 'movies.csv')
        
        try:
            # 获取已存在的链接，用于去重
            existing_links = set()
            if os.path.exists(csv_file) and not self.config['overwrite']:
                existing_links = self.get_existing_movie_links(csv_file)
            
            # 过滤重复数据
            filtered_movies = []
            for movie in movies:
                if movie.get('link') not in existing_links:
                    filtered_movies.append(movie)
                    existing_links.add(movie.get('link'))
            
            if not filtered_movies:
                logger.info("没有新的电影数据需要保存到CSV")
                return True
            
            # 获取所有可能的字段名
            fieldnames = set()
            for movie in movies:
                fieldnames.update(movie.keys())
            
            # 确保必要字段存在
            required_fields = ['title', 'original_title', 'score', 'votes', 'link']
            for field in required_fields:
                if field not in fieldnames:
                    fieldnames.add(field)
            
            # 将集合转换为列表，方便排序
            fieldnames = sorted(list(fieldnames))
            
            # 写入CSV文件
            mode = 'w' if self.config['overwrite'] or not os.path.exists(csv_file) else 'a'
            with open(csv_file, mode, newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # 如果是写入模式，写入表头
                if mode == 'w':
                    writer.writeheader()
                
                # 写入数据
                for movie in filtered_movies:
                    # 处理列表类型的字段
                    row_data = {}
                    for key, value in movie.items():
                        if isinstance(value, list):
                            row_data[key] = ', '.join(value)
                        else:
                            row_data[key] = value
                    writer.writerow(row_data)
            
            logger.info(f"成功保存 {len(filtered_movies)} 部电影到CSV文件: {csv_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")
            return False
    
    def save_to_json(self, movies: List[Dict], show_dialog: bool = False) -> bool:
        """
        保存电影数据到JSON文件
        
        Args:
            movies (List[Dict]): 电影数据列表
            show_dialog (bool, optional): 文件存在时是否显示对话框询问操作
            
        Returns:
            bool: 是否保存成功
        """
        if not movies:
            logger.warning("没有电影数据需要保存到JSON")
            return False
        
        json_file = os.path.join(self.output_dir, 'movies.json')
        
        try:
            # 检查文件是否存在
            if os.path.exists(json_file):
                if self.config['overwrite']:
                    action = 'overwrite'
                elif show_dialog:
                    # 在实际GUI环境中可以使用tkinter等库显示对话框
                    # 这里使用模拟的方式
                    user_input = input(f"文件 {json_file} 已存在，是否合并数据？(y/n): ")
                    action = 'merge' if user_input.lower() == 'y' else 'cancel'
                else:
                    action = 'merge'  # 默认合并
            else:
                action = 'new'  # 创建新文件
            
            if action == 'cancel':
                logger.info("用户取消保存操作")
                return False
            
            # 加载已存在的数据（如果需要合并）
            all_movies = []
            existing_links = set()
            
            if action == 'merge':
                with open(json_file, 'r', encoding='utf-8') as f:
                    all_movies = json.load(f)
                
                # 收集已存在的链接
                for movie in all_movies:
                    if 'link' in movie:
                        existing_links.add(movie['link'])
            
            # 添加新数据，去重
            added_count = 0
            for movie in movies:
                if movie.get('link') not in existing_links:
                    all_movies.append(movie)
                    existing_links.add(movie.get('link'))
                    added_count += 1
            
            # 检查记录数限制
            if self.config.get('max_records') and len(all_movies) > self.config['max_records']:
                all_movies = all_movies[:self.config['max_records']]
                logger.warning(f"电影数据数量超过配置的最大限制，已截断到 {self.config['max_records']} 条")
            
            # 保存到文件
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(all_movies, f, ensure_ascii=False, indent=2)
            
            if action == 'new':
                logger.info(f"成功创建JSON文件: {json_file}，保存了 {len(all_movies)} 部电影")
            else:
                logger.info(f"成功{action}JSON文件: {json_file}，新增 {added_count} 部电影，总计 {len(all_movies)} 部")
            
            return True
            
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
            return False
    
    def _connect_db(self):
        """
        连接到MySQL数据库
        
        Returns:
            bool: 是否连接成功
        """
        try:
            if self.db_conn and self.db_conn.open:
                return True
            
            self.db_conn = pymysql.connect(
                host=self.config['db_host'],
                user=self.config['db_user'],
                password=self.config['db_password'],
                database=self.config['db_name'],
                port=self.config['db_port'],
                charset='utf8mb4',
                cursorclass=DictCursor
            )
            logger.info("数据库连接成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            self.db_conn = None
            return False
    
    def _create_table(self):
        """
        创建电影数据表（如果不存在）
        
        Returns:
            bool: 是否创建成功
        """
        try:
            if not self.db_conn or not self.db_conn.open:
                if not self._connect_db():
                    return False
            
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS movies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                original_title VARCHAR(255),
                score FLOAT,
                votes INT,
                quote TEXT,
                link VARCHAR(255) NOT NULL UNIQUE,
                cover VARCHAR(255),
                info TEXT,
                duration VARCHAR(50),
                summary TEXT,
                director VARCHAR(255),
                actors VARCHAR(1000),
                genres VARCHAR(255),
                regions VARCHAR(255),
                languages VARCHAR(255),
                release_date VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            
            with self.db_conn.cursor() as cursor:
                cursor.execute(create_table_sql)
            self.db_conn.commit()
            logger.info("电影数据表检查/创建成功")
            return True
            
        except Exception as e:
            logger.error(f"创建数据表失败: {e}")
            if self.db_conn:
                self.db_conn.rollback()
            return False
    
    def save_to_mysql(self, movies: List[Dict]) -> bool:
        """
        保存电影数据到MySQL数据库
        
        Args:
            movies (List[Dict]): 电影数据列表
            
        Returns:
            bool: 是否保存成功
        """
        if not movies:
            logger.warning("没有电影数据需要保存到MySQL")
            return False
        
        try:
            # 连接数据库
            if not self.db_conn or not self.db_conn.open:
                if not self._connect_db():
                    return False
            
            # 创建表
            if not self._create_table():
                return False
            
            # 插入或更新数据
            sql = """
            INSERT INTO movies (
                title, original_title, score, votes, quote, link, cover, info,
                duration, summary, director, actors, genres, regions, languages, release_date
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                original_title = VALUES(original_title),
                score = VALUES(score),
                votes = VALUES(votes),
                quote = VALUES(quote),
                cover = VALUES(cover),
                info = VALUES(info),
                duration = VALUES(duration),
                summary = VALUES(summary),
                director = VALUES(director),
                actors = VALUES(actors),
                genres = VALUES(genres),
                regions = VALUES(regions),
                languages = VALUES(languages),
                release_date = VALUES(release_date),
                updated_at = CURRENT_TIMESTAMP
            """
            
            inserted_count = 0
            updated_count = 0
            
            with self.db_conn.cursor() as cursor:
                for movie in movies:
                    # 将列表类型的字段转换为字符串
                    actors_str = ', '.join(movie.get('actors', [])) if isinstance(movie.get('actors'), list) else movie.get('actors', '')
                    genres_str = ', '.join(movie.get('genres', [])) if isinstance(movie.get('genres', []), list) else movie.get('genres', '')
                    regions_str = ', '.join(movie.get('regions', [])) if isinstance(movie.get('regions', []), list) else movie.get('regions', '')
                    languages_str = ', '.join(movie.get('languages', [])) if isinstance(movie.get('languages', []), list) else movie.get('languages', '')
                    
                    # 执行SQL
                    params = (
                        movie.get('title', ''),        # 电影标题
                        movie.get('original_title', ''),  # 原始标题
                        movie.get('score', 0),         # 评分
                        movie.get('votes', 0),         # 投票数
                        movie.get('quote', ''),        # 经典台词
                        movie.get('link', ''),         # 电影链接
                        movie.get('cover', ''),        # 封面图片链接
                        movie.get('info', ''),         # 基本信息
                        movie.get('duration', ''),     # 片长
                        movie.get('summary', ''),      # 剧情简介
                        movie.get('director', ''),     # 导演
                        actors_str,                    # 主演（逗号分隔）
                        genres_str,                    # 类型（逗号分隔）
                        regions_str,                   # 地区（逗号分隔）
                        languages_str,                 # 语言（逗号分隔）
                        movie.get('release_date', '')  # 上映日期
                    )
                    
                    result = cursor.execute(sql, params)
                    
                    # 判断是插入还是更新
                    if result == 1:  # 插入
                        inserted_count += 1
                    elif result == 2:  # 更新
                        updated_count += 1
            
            # 提交事务
            self.db_conn.commit()
            logger.info(f"成功保存到数据库: 新增 {inserted_count} 部，更新 {updated_count} 部，总计 {len(movies)} 部")
            
            return True
            
        except Exception as e:
            logger.error(f"保存到数据库失败: {e}")
            if self.db_conn:
                self.db_conn.rollback()
            return False
    
    def save_movies(self, movies: List[Dict], output_type=None, show_dialog=False):
        """
        统一的电影数据保存入口
        
        Args:
            movies (List[Dict]): 电影数据列表，每个字典包含电影信息
            output_type (str, optional): 输出类型，支持 'csv', 'json', 'mysql'，默认为配置中的output_type
            show_dialog (bool, optional): 保存JSON时是否显示对话框
            
        Returns:
            bool: 是否保存成功
        """
        if not movies:
            logger.warning("没有电影数据需要保存")
            return False
        
        output_type = output_type or self.config['output_type']
        
        # 检查记录数限制
        if self.config.get('max_records') and len(movies) > self.config['max_records']:
            logger.warning(f"电影数据数量 {len(movies)} 超过配置的最大限制 {self.config['max_records']}")
            movies = movies[:self.config['max_records']]
        
        # 根据输出类型调用不同的保存方法
        if output_type == 'csv':
            return self.save_to_csv(movies)
        elif output_type == 'json':
            return self.save_to_json(movies, show_dialog=show_dialog)
        elif output_type == 'mysql':
            return self.save_to_mysql(movies)
        else:
            logger.error(f"不支持的输出类型: {output_type}")
            return False
    
    def close(self):
        """
        关闭资源，释放数据库连接
        
        Returns:
            None
        """
        try:
            if self.db_conn and self.db_conn.open:
                self.db_conn.close()
                logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭资源失败: {e}")


# 示例用法
if __name__ == '__main__':
    """
    示例代码：演示如何使用StorageUtils类保存电影数据
    
    该示例创建了一个StorageUtils实例，分别演示了保存到CSV和JSON的功能。
    实际使用时，可根据需要调整配置参数和输出类型。
    """
    # 示例电影数据
    sample_movies = [
        {
            'title': '肖申克的救赎',
            'original_title': 'The Shawshank Redemption',
            'score': 9.7,
            'votes': 2683999,
            'quote': '希望让人自由。',
            'link': 'https://movie.douban.com/subject/1292052/',
            'cover': 'https://img9.doubanio.com/view/photo/s_ratio_poster/public/p480747492.webp',
            'info': '导演: 弗兰克·德拉邦特 Frank Darabont\n主演: 蒂姆·罗宾斯 Tim Robbins / 摩根·弗里曼 Morgan Freeman\n类型: 剧情 / 犯罪\n制片国家/地区: 美国\n语言: 英语\n上映日期: 1994-09-23(加拿大)'
        },
        {
            'title': '霸王别姬',
            'original_title': 'Farewell My Concubine',
            'score': 9.6,
            'votes': 1928219,
            'quote': '说的是一辈子！差一年，一个月，一天，一个时辰，都不算一辈子！',
            'link': 'https://movie.douban.com/subject/1291546/',
            'cover': 'https://img2.doubanio.com/view/photo/s_ratio_poster/public/p2561716440.webp',
            'info': '导演: 陈凯歌\n主演: 张国荣 / 张丰毅 / 巩俐 / 葛优\n类型: 剧情 / 爱情 / 同性\n制片国家/地区: 中国大陆 / 香港\n语言: 汉语普通话\n上映日期: 1993-01-01(香港)'
        }
    ]
    
    # 初始化存储工具
    storage = StorageUtils({
        'output_type': 'csv',
        'output_dir': './output_test',
        'overwrite': True
    })
    
    # 保存到CSV
    success = storage.save_to_csv(sample_movies)
    print(f"保存CSV: {'成功' if success else '失败'}")
    
    # 保存到JSON
    success = storage.save_to_json(sample_movies)
    print(f"保存JSON: {'成功' if success else '失败'}")
    
    # 关闭资源
    storage.close()