# -*- coding: utf-8 -*-
"""
豆瓣电影Top250数据可视化增强版
功能：将爬取的电影数据进行多维度可视化分析，支持CSV和JSON格式
作者：
版本：1.0
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import json
import os
import argparse
from collections import Counter
import re

# 设置matplotlib参数
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['savefig.dpi'] = 300

# 设置中文显示
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

class DoubanVisualizer:
    """
    豆瓣电影数据可视化类
    提供多种数据可视化分析功能，包括评分分布、评论数排行、年代分布等
    """
    
    def __init__(self):
        """
        初始化可视化器
        """
        pass
    
    def load_data(self, file_path=None):
        """
        加载数据，自动检测文件格式
        
        Args:
            file_path (str, optional): 数据文件路径，如果不指定则自动查找
            
        Returns:
            pandas.DataFrame or None: 加载的数据框，如果加载失败返回None
        """
        # 自动检测文件
        if file_path is None:
            if os.path.exists('douban_top250.json'):
                file_path = 'douban_top250.json'
            elif os.path.exists('douban_top250.csv'):
                file_path = 'douban_top250.csv'
            else:
                print("错误：找不到数据文件 (douban_top250.csv 或 douban_top250.json)")
                return None
        
        try:
            _, ext = os.path.splitext(file_path)
            if ext.lower() == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8-sig')
            elif ext.lower() == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    df = pd.DataFrame(data)
            else:
                print(f"错误：不支持的文件格式: {ext}")
                return None
            
            print(f"成功加载 {len(df)} 条电影数据")
            return df
        except Exception as e:
            print(f"加载数据失败：{e}")
            return None
    
    def preprocess_data(self, df):
        """
        数据预处理
        
        Args:
            df (pandas.DataFrame): 原始数据框
            
        Returns:
            pandas.DataFrame or None: 预处理后的数据框，如果输入为None则返回None
        """
        if df is None:
            return None
        
        # 确保数值列的类型正确
        numeric_columns = ['评分', '评论数', '排名', '年份']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 数据清洗：处理缺失值
        print(f"\n数据清洗：")
        print(f"- 原始记录数: {len(df)}")
        
        # 提取年份信息（如果需要）
        if '上映日期' in df.columns and '年份' not in df.columns:
            df['年份'] = pd.to_datetime(df['上映日期'], errors='coerce').dt.year
        
        # 去除重复记录
        df = df.drop_duplicates()
        print(f"- 去重后记录数: {len(df)}")
        
        return df
    
    def analyze_rating_distribution(self, df, output_dir='.'):
        """
        分析评分分布，生成直方图和箱线图
        
        Args:
            df (pandas.DataFrame): 电影数据
            output_dir (str): 输出目录路径
            
        Returns:
            bool: 生成成功返回True，失败返回False
        """
        if '评分' not in df.columns:
            print("跳过：缺少评分列")
            return False
        
        plt.figure(figsize=(10, 6))
        
        # 左侧：直方图
        plt.subplot(1, 2, 1)
        sns.histplot(df['评分'], kde=True, bins=15, color='#ff7e67', alpha=0.8)
        plt.title('评分分布直方图', fontsize=12)
        plt.xlabel('评分')
        plt.ylabel('电影数量')
        plt.grid(True, linestyle='--', alpha=0.3)
        
        # 添加统计信息
        mean_rating = df['评分'].mean()
        median_rating = df['评分'].median()
        plt.axvline(mean_rating, color='red', linestyle='--', label=f'平均分: {mean_rating:.2f}')
        plt.legend()
        
        # 右侧：箱线图
        plt.subplot(1, 2, 2)
        sns.boxplot(y=df['评分'], color='#ffa372')
        plt.title('评分分布箱线图', fontsize=12)
        plt.ylabel('评分')
        
        plt.tight_layout()
        
        output_path = os.path.join(output_dir, 'rating_distribution.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"[OK] 评分分布图已保存至: {output_path}")
        return True
    
    def analyze_comment_top10(self, df, output_dir='.'):
        """
        分析评论数Top10的电影，生成水平条形图
        
        Args:
            df (pandas.DataFrame): 电影数据
            output_dir (str): 输出目录路径
            
        Returns:
            bool: 生成成功返回True，失败返回False
        """
        if '评论数' not in df.columns:
            print("跳过：缺少评论数列")
            return False
        
        # 获取评论数最多的10部电影
        top10 = df.nlargest(10, '评论数')
        
        plt.figure(figsize=(12, 8))
        colors = plt.cm.viridis(np.linspace(0, 1, len(top10)))
        bars = plt.barh(range(len(top10)), top10['评论数'], color=colors)
        
        # 电影名称和评分标签
        for i, bar in enumerate(bars):
            width = bar.get_width()
            movie = top10.iloc[i]
            name = movie['电影名称'] if '电影名称' in movie else movie['title']
            rating = movie['评分'] if '评分' in movie else 'N/A'
            plt.text(width + 0.05 * max(top10['评论数']), bar.get_y() + bar.get_height()/2, 
                     f'{int(width)} 评 ({rating})', ha='left', va='center')
        
        # 设置y轴标签
        movie_names = [top10.iloc[i]['电影名称'] if '电影名称' in top10.columns else \
                      top10.iloc[i]['title'] for i in range(len(top10))]
        plt.yticks(range(len(top10)), movie_names, fontsize=9)
        
        plt.xlabel('评论数')
        plt.title('豆瓣Top250电影评论数Top10', fontsize=14)
        plt.grid(True, linestyle='--', alpha=0.3, axis='x')
        
        output_path = os.path.join(output_dir, 'comment_top10.png')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"[OK] 评论数Top10图表已保存至: {output_path}")
        return True
    
    def analyze_year_distribution(self, df, output_dir='.'):
        """
        按年份分析电影数量，根据数据量自动选择年份或年代分组显示
        
        Args:
            df (pandas.DataFrame): 电影数据
            output_dir (str): 输出目录路径
            
        Returns:
            bool: 生成成功返回True，失败返回False
        """
        if '年份' not in df.columns:
            print("跳过：缺少年份列")
            return False
        
        # 过滤有效年份（1900-2024）
        valid_years = df[(df['年份'] >= 1900) & (df['年份'] <= 2024)]
        if len(valid_years) == 0:
            print("跳过：无法提取有效年份")
            return False
        
        year_counts = valid_years['年份'].value_counts().sort_index()
        
        # 按年代分组统计
        if len(year_counts) > 20:
            # 按10年为一组统计，处理可能存在的NaN值
            df['年代'] = (df['年份'].fillna(0) // 10 * 10).astype(int)
            decade_counts = df[df['年代'] > 0]['年代'].value_counts().sort_index()
            
            plt.figure(figsize=(12, 6))
            bars = plt.bar(decade_counts.index.astype(str), decade_counts.values, color=plt.cm.plasma(np.linspace(0, 1, len(decade_counts))))
            plt.title('豆瓣Top250电影年代分布', fontsize=14)
            plt.xlabel('年代')
            plt.ylabel('电影数量')
            plt.grid(True, linestyle='--', alpha=0.3, axis='y')
            
            # 添加数值标签
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{int(height)}', ha='center', va='bottom')
        else:
            # 直接按年份显示
            plt.figure(figsize=(12, 6))
            bars = plt.bar(year_counts.index.astype(str), year_counts.values, color=plt.cm.plasma(np.linspace(0, 1, len(year_counts))))
            plt.title('豆瓣Top250电影年份分布', fontsize=14)
            plt.xlabel('年份')
            plt.ylabel('电影数量')
            plt.xticks(rotation=45)
            plt.grid(True, linestyle='--', alpha=0.3, axis='y')
            
            # 添加数值标签
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{int(height)}', ha='center', va='bottom')
        
        output_path = os.path.join(output_dir, 'year_distribution.png')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"[OK] 年份/年代分布图已保存至: {output_path}")
        return True
    
    def analyze_region_distribution(self, df, output_dir='.'):
        """
        分析电影产地分布，生成饼图
        
        Args:
            df (pandas.DataFrame): 电影数据
            output_dir (str): 输出目录路径
            
        Returns:
            bool: 生成成功返回True，失败返回False
        """
        # 尝试不同的列名
        region_cols = ['国家', '地区', '产地']
        region_col = None
        for col in region_cols:
            if col in df.columns:
                region_col = col
                break
        
        if region_col is None:
            print("跳过：缺少地区信息列")
            return False
        
        # 统计地区分布
        region_counter = Counter()
        for regions in df[region_col].dropna():
            # 分割多个地区（处理'美国/德国'这样的情况）
            for region in [r.strip() for r in str(regions).split('/')]:
                region_counter[region] += 1
        
        # 获取数量最多的8个地区
        top_regions = dict(region_counter.most_common(8))
        
        plt.figure(figsize=(10, 8))
        plt.pie(top_regions.values(), labels=top_regions.keys(), autopct='%1.1f%%',
                startangle=90, colors=plt.cm.tab20(np.linspace(0, 1, len(top_regions))),
                wedgeprops={'edgecolor': 'w', 'linewidth': 1})
        plt.axis('equal')
        plt.title('豆瓣Top250电影产地分布', fontsize=14)
        
        output_path = os.path.join(output_dir, 'region_distribution.png')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"[OK] 产地分布图已保存至: {output_path}")
        return True
    
    def analyze_genre_distribution(self, df, output_dir='.'):
        """
        分析电影类型分布，生成条形图
        
        Args:
            df (pandas.DataFrame): 电影数据
            output_dir (str): 输出目录路径
            
        Returns:
            bool: 生成成功返回True，失败返回False
        """
        if '类型' not in df.columns:
            print("跳过：缺少类型列")
            return False
        
        # 统计类型分布
        genre_counter = Counter()
        for genres in df['类型'].dropna():
            # 分割多个类型
            for genre in [g.strip() for g in str(genres).split('/')]:
                genre_counter[genre] += 1
        
        # 获取数量最多的10个类型
        top_genres = dict(genre_counter.most_common(10))
        
        plt.figure(figsize=(12, 6))
        colors = plt.cm.Set3(np.linspace(0, 1, len(top_genres)))
        bars = plt.bar(range(len(top_genres)), top_genres.values(), color=colors)
        
        plt.xticks(range(len(top_genres)), top_genres.keys(), rotation=45, ha='right')
        plt.xlabel('电影类型')
        plt.ylabel('数量')
        plt.title('豆瓣Top250电影类型分布', fontsize=14)
        plt.grid(True, linestyle='--', alpha=0.3, axis='y')
        
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{int(height)}', ha='center', va='bottom')
        
        output_path = os.path.join(output_dir, 'genre_distribution.png')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"[OK] 类型分布图已保存至: {output_path}")
        return True
    
    def analyze_rating_quality(self, df, output_dir='.'):
        """
        分析评分与其他因素的关系，生成散点图和趋势线
        
        Args:
            df (pandas.DataFrame): 电影数据
            output_dir (str): 输出目录路径
            
        Returns:
            bool: 生成成功返回True，失败返回False
        """
        if not all(col in df.columns for col in ['评分', '评论数']):
            print("跳过：缺少评分或评论数列")
            return False
        
        plt.figure(figsize=(10, 6))
        
        # 散点图：评分 vs 评论数
        plt.scatter(df['评分'], df['评论数'], alpha=0.6, c=df['评分'], cmap='viridis', s=50)
        plt.colorbar(label='评分')
        
        # 添加趋势线
        z = np.polyfit(df['评分'], df['评论数'], 1)
        p = np.poly1d(z)
        plt.plot(df['评分'], p(df['评分']), "r--", alpha=0.8, linewidth=2)
        
        plt.title('豆瓣Top250电影评分与评论数关系', fontsize=14)
        plt.xlabel('评分')
        plt.ylabel('评论数')
        plt.grid(True, linestyle='--', alpha=0.3)
        
        output_path = os.path.join(output_dir, 'rating_vs_comments.png')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"[OK] 评分与评论数关系图已保存至: {output_path}")
        return True
    
    def generate_summary_report(self, df, output_dir='.', prompt_user=True):
        """
        生成数据摘要报告
        
        Args:
            df (pandas.DataFrame): 电影数据
            output_dir (str): 输出目录路径
            prompt_user (bool): 是否在文件已存在时提示用户
            
        Returns:
            bool: 生成成功返回True，失败返回False
        """
        if df is None:
            return False
        
        report = """
# 豆瓣电影Top250数据分析报告

## 数据概览
- 总电影数量: {}
- 评分范围: {} - {}
- 平均评分: {:.2f}
- 最高评分电影: {}
- 评论数最多: {}
""".format(
            len(df),
            df['评分'].min() if '评分' in df.columns else 'N/A',
            df['评分'].max() if '评分' in df.columns else 'N/A',
            df['评分'].mean() if '评分' in df.columns else 0,
            df.loc[df['评分'].idxmax()]['电影名称'] if '评分' in df.columns and '电影名称' in df.columns else 'N/A',
            df.loc[df['评论数'].idxmax()]['电影名称'] if '评论数' in df.columns and '电影名称' in df.columns else 'N/A'
        )
        
        # 添加年份信息
        if '年份' in df.columns:
            valid_years = df[(df['年份'] >= 1900) & (df['年份'] <= 2024)]['年份']
            if len(valid_years) > 0:
                report += "- 最早上映年份: {}\n".format(int(valid_years.min()))
                report += "- 最晚上映年份: {}\n".format(int(valid_years.max()))
        
        output_path = os.path.join(output_dir, 'analysis_report.txt')
        
        # 检查文件是否存在
        file_exists = os.path.exists(output_path)
        
        # 如果文件存在且需要提示用户
        if file_exists and prompt_user:
            try:
                # 尝试导入tkinter用于GUI提示
                import tkinter as tk
                from tkinter import messagebox
                import datetime
                
                # 检查是否已初始化Tk实例
                root = tk._default_root
                if root is None:
                    root = tk.Tk()
                    root.withdraw()  # 隐藏主窗口
                
                # 显示提示对话框
                response = messagebox.askyesnocancel(
                    "文件已存在",
                    f"报告文件 analysis_report.txt 已存在，是否覆盖？",
                    default=messagebox.NO
                )
                
                if response is None:  # 用户取消
                    print("用户取消了报告生成")
                    return False
                elif not response:  # 用户选择不覆盖
                    # 生成带时间戳的新文件名
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = os.path.join(output_dir, f'analysis_report_{timestamp}.txt')
            except Exception:
                # 如果tkinter不可用，生成带时间戳的新文件名
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = os.path.join(output_dir, f'analysis_report_{timestamp}.txt')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"[OK] 数据分析报告已保存至: {output_path}")
        print(report)
        return True
    
    def generate_all_charts(self, file_path=None, output_dir='visualizations', prompt_user=True):
        """
        生成所有可视化图表
        
        Args:
            file_path (str, optional): 数据文件路径，如果不指定则自动查找
            output_dir (str): 输出目录路径
            prompt_user (bool): 是否在文件已存在时提示用户
            
        Returns:
            bool: 生成成功返回True，失败返回False
        """
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        else:
            # 检查目录是否为空或有图表文件
            chart_files = [f for f in os.listdir(output_dir) if f.endswith('.png')]
            has_charts = len(chart_files) > 0
            
            # 如果有图表文件且需要提示用户
            if has_charts and prompt_user:
                try:
                    # 尝试导入tkinter用于GUI提示
                    import tkinter as tk
                    from tkinter import messagebox
                    
                    # 检查是否已初始化Tk实例
                    root = tk._default_root
                    if root is None:
                        root = tk.Tk()
                        root.withdraw()  # 隐藏主窗口
                    
                    # 显示提示对话框
                    response = messagebox.askyesnocancel(
                        "目录已存在",
                        f"输出目录 {os.path.basename(output_dir)} 中存在图表文件，是否继续生成？\n（已存在的图表文件将被覆盖）",
                        default=messagebox.NO
                    )
                    
                    if response is None or not response:  # 用户取消或选择不继续
                        print("用户取消了图表生成")
                        return False
                except Exception:
                    # 如果tkinter不可用，继续执行（覆盖现有文件）
                    pass
        
        # 加载和预处理数据
        print("=== 开始数据分析 ===")
        df = self.load_data(file_path)
        if df is None:
            return False
        
        df = self.preprocess_data(df)
        if df is None:
            return False
        
        # 显示数据信息
        print(f"\n数据列信息: {list(df.columns)}")
        
        # 生成所有图表
        print("\n=== 生成可视化图表 ===")
        charts = [
            ("评分分布分析", self.analyze_rating_distribution),
            ("评论数Top10分析", self.analyze_comment_top10),
            ("年份/年代分布分析", self.analyze_year_distribution),
            ("产地分布分析", self.analyze_region_distribution),
            ("类型分布分析", self.analyze_genre_distribution),
            ("评分质量关系分析", self.analyze_rating_quality)
        ]
        
        # 生成报告
        self.generate_summary_report(df, output_dir, prompt_user)
        
        # 生成图表
        success_count = 0
        try:
            for name, func in charts:
                print(f"\n{name}...")
                if func(df, output_dir):
                    success_count += 1
            
            print(f"\n=== 分析完成 ===")
            print(f"成功生成 {success_count}/{len(charts)} 个可视化图表")
            print(f"所有图表和报告已保存至: {os.path.abspath(output_dir)}")
            return True
        except Exception as e:
            print(f"生成图表时出错：{str(e)}")
            return False

def main():
    """
    主函数，支持命令行参数
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='豆瓣电影Top250数据可视化工具')
    
    # 添加参数
    parser.add_argument('--input', type=str, default=None,
                        help='指定输入数据文件路径 (CSV或JSON格式)')
    parser.add_argument('--output_folder', type=str, default='visualizations',
                        help='指定输出图表文件夹路径')
    parser.add_argument('--no_prompt', action='store_true',
                        help='文件已存在时不弹出提示对话框，直接覆盖或创建新文件')
    
    # 解析参数
    args = parser.parse_args()
    
    # 创建可视化器并生成图表
    visualizer = DoubanVisualizer()
    visualizer.generate_all_charts(file_path=args.input, output_dir=args.output_folder, prompt_user=not args.no_prompt)

if __name__ == '__main__':
    main()