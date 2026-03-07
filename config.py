#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
豆瓣电影Top250爬虫配置模块

该模块负责管理爬虫的配置参数，提供配置文件加载、配置合并和命令行参数解析功能。
主要功能包括：
- 定义默认配置参数（请求头、爬虫参数、数据库配置等）
- 从YAML文件加载用户自定义配置
- 递归合并默认配置和用户配置
- 解析和处理命令行参数
- 确保输出目录存在
- 配置日志记录器
"""

import os
import yaml
import argparse
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    # 请求头配置
    'headers_pool': [
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    ],
    
    # 爬虫配置
    'delay_range': [2, 5],  # 请求延迟范围（秒）
    'max_retries': 3,       # 最大重试次数
    'timeout': 10,          # 请求超时时间（秒）
    'breakpoint_file': 'breakpoint.txt',  # 断点文件路径
    
    # MySQL数据库配置
    'mysql': {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '',
        'database': 'douban',
        'charset': 'utf8mb4'
    },
    
    # 代理配置（可在运行时通过命令行参数启用）
    'proxies_pool': [
        # 示例代理，使用时需要替换为有效的代理
        # {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'},
    ],
    
    # Cookie配置
    'cookie_file': 'cookies.txt',
    
    # 输出配置
    'output_dir': 'output',
    'default_output_file': 'douban_top250'
}

def load_config(config_file='config.yaml'):
    """
    加载配置文件并与默认配置合并
    
    该函数从指定的YAML文件中加载用户配置，然后将其与默认配置递归合并，
    同时确保输出目录存在。如果配置文件不存在或加载失败，将继续使用默认配置。
    
    Args:
        config_file (str): 配置文件路径，默认为'config.yaml'
        
    Returns:
        dict: 合并后的配置字典，包含默认配置和用户配置的合并结果
    """
    # 创建默认配置的副本，避免修改原始默认配置
    config = DEFAULT_CONFIG.copy()
    
    # 如果配置文件存在，则加载并合并
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                
                # 递归合并配置，而不是直接替换
                if user_config:
                    config = merge_configs(config, user_config)
                    logger.info(f"成功加载配置文件: {config_file}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            # 继续使用默认配置
    else:
        logger.info(f"配置文件不存在: {config_file}，使用默认配置")
    
    # 确保输出目录存在
    output_dir = config.get('output_dir', 'output')
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            logger.info(f"创建输出目录: {output_dir}")
        except Exception as e:
            logger.error(f"创建输出目录失败: {e}")
    
    return config

def merge_configs(default, user):
    """
    递归合并两个配置字典
    
    该函数将用户配置与默认配置递归合并，保留默认配置中未被用户配置覆盖的部分。
    当两个配置都包含相同键且值都是字典时，会递归合并这两个字典，
    否则直接用用户配置的值替换默认配置的值。
    
    Args:
        default (dict): 默认配置字典，作为基础配置
        user (dict): 用户配置字典，用于覆盖默认配置
        
    Returns:
        dict: 合并后的配置字典，保留默认配置中未被用户配置覆盖的部分
    """
    # 创建默认配置的副本，避免修改原始默认配置
    result = default.copy()
    
    for key, value in user.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # 如果两者都是字典，递归合并
            result[key] = merge_configs(result[key], value)
        else:
            # 否则直接替换
            result[key] = value
    
    return result

def parse_args():
    """
    解析命令行参数
    
    该函数定义并解析爬虫支持的命令行参数，包括运行模式、输出格式、
    异步模式、代理设置等，使用户能够灵活控制爬虫的运行行为。
    
    Returns:
        argparse.Namespace: 解析后的命令行参数命名空间，包含所有用户指定的运行参数
    """
    parser = argparse.ArgumentParser(description='豆瓣电影Top250爬虫 - 支持异步、代理、断点续爬等功能')
    
    # 运行模式参数
    parser.add_argument('--mode', choices=['full', 'test'], default='full', 
                        help='运行模式: full(全量爬取) 或 test(仅爬取第一页)')
    
    # 输出格式参数
    parser.add_argument('--output', choices=['csv', 'json', 'mysql'], default='csv',
                        help='输出格式: csv, json 或 mysql')
    
    # 输出文件参数
    parser.add_argument('--output_file', type=str, default=None,
                        help='输出文件名（不含扩展名），默认使用配置中的default_output_file')
    
    # 异步模式参数
    parser.add_argument('--async', dest='use_async', action='store_true',
                        help='使用异步请求模式（默认使用同步模式）')
    
    # 代理参数
    parser.add_argument('--proxy', action='store_true',
                        help='使用代理IP（需要在配置中设置有效的代理）')
    
    # 重试次数参数
    parser.add_argument('--retry', type=int, default=3,
                        help='请求失败时的最大重试次数')
    
    # Cookie参数
    parser.add_argument('--cookie', type=str, default=None,
                        help='自定义Cookie值，用于绕过登录限制')
    
    # 调试模式参数
    parser.add_argument('--debug', action='store_true',
                        help='启用调试模式，显示更详细的日志信息')
    
    # 解析参数
    args = parser.parse_args()
    
    # 如果启用调试模式，修改日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    return args

# 如果直接运行此文件，显示配置示例
if __name__ == '__main__':
    """
    当直接运行此模块时，显示配置模块的使用方法和默认配置示例。
    这有助于开发者了解如何正确使用该模块。
    """
    print("豆瓣电影Top250爬虫配置模块")
    print("使用方法：")
    print("  1. 导入此模块：from config import load_config, parse_args")
    print("  2. 加载配置：config = load_config()")
    print("  3. 解析命令行参数：args = parse_args()")
    
    # 显示默认配置示例
    print("\n默认配置示例：")
    print(yaml.dump(DEFAULT_CONFIG, allow_unicode=True, default_flow_style=False))