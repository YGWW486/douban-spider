#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆瓣电影Top250爬虫 - 图形界面版本

功能：提供简单易用的图形界面，支持爬虫控制、结果查看和数据可视化
包含爬虫启动/停止控制、参数设置、结果预览、数据导出与图表生成等功能

依赖项：
- tkinter: 创建图形用户界面
- pandas: 数据处理和CSV文件操作
- subprocess, threading: 后台运行爬虫进程
- json, os, sys: 文件和系统操作
- webbrowser: 打开文件和文件夹
- datetime: 记录日志时间戳
- PIL (可选): 显示图表预览
"""

# 导入必要的库
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import subprocess
import os
import sys
import time
import threading
import webbrowser
from datetime import datetime
import pandas as pd
import json

# 尝试导入PIL库用于图表预览，但不强制要求
try:
    from PIL import Image, ImageTk
except ImportError:
    pass  # 如果没有安装PIL库，将在运行时处理

class DoubanSpiderGUI:
    """
    豆瓣电影Top250爬虫图形界面类
    
    提供完整的爬虫控制、结果管理和数据可视化功能，包括：
    - 爬虫启动、停止和重置
    - 爬取参数设置（模式、输出格式等）
    - 实时日志显示
    - 结果预览和导出
    - 数据可视化和图表生成
    """
    
    def __init__(self, root):
        """初始化GUI界面
        
        Args:
            root: Tkinter根窗口对象
        """
        self.root = root
        self.root.title("豆瓣电影Top250爬虫")
        self.root.geometry("1000x600")  # 增大窗口尺寸以容纳右侧结果区域
        self.root.resizable(True, True)
        
        # 设置中文字体支持
        self.style = ttk.Style()
        
        # 爬虫进程控制变量
        self.spider_process = None  # 爬虫子进程对象
        self.spider_thread = None   # 运行爬虫的线程对象
        self.is_spider_running = False  # 爬虫运行状态标志
        self.log_text = None        # 日志文本框引用
        self.result_text = None     # 结果显示文本框引用
        self.current_results = None  # 存储当前爬取结果
        self.current_output_format = None  # 当前爬取的输出格式
        self.temp_chart_folder = None  # 临时图表文件夹路径
        
        # 创建界面组件
        self._create_widgets()
        
        # 初始状态检查（断点、已有结果等）
        self._check_spider_status()
    
    def _create_widgets(self):
        """创建界面组件
        
        设计并布局GUI所有组件，包括控制按钮、选项、日志区域和结果显示区域
        界面采用左右分栏设计，左侧包含控制和操作区域，右侧显示爬取结果预览
        """
        # 创建主框架作为所有组件的容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建左右分栏布局
        left_frame = ttk.Frame(main_frame)  # 左侧：控制、日志和操作区域
        right_frame = ttk.Frame(main_frame)  # 右侧：结果预览区域
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 左侧 - 顶部控制区域
        control_frame = ttk.LabelFrame(left_frame, text="爬虫控制", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 控制按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        self.start_button = ttk.Button(button_frame, text="开始爬取", command=self.start_spider)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="停止爬取", command=self.stop_spider, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.reset_button = ttk.Button(button_frame, text="重置状态", command=self.reset_spider)
        self.reset_button.pack(side=tk.LEFT, padx=5)
        
        # 爬取选项
        options_frame = ttk.LabelFrame(control_frame, text="爬取选项", padding="5")
        options_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(options_frame, text="爬取模式: ").pack(side=tk.LEFT, padx=5)
        self.mode_var = tk.StringVar(value="full")
        mode_frame = ttk.Frame(options_frame)
        mode_frame.pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="全量爬取", variable=self.mode_var, value="full").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="测试模式", variable=self.mode_var, value="test").pack(side=tk.LEFT, padx=5)
        
        ttk.Label(options_frame, text="输出格式: ").pack(side=tk.LEFT, padx=5)
        self.output_var = tk.StringVar(value="csv")
        output_frame = ttk.Frame(options_frame)
        output_frame.pack(side=tk.LEFT)
        ttk.Radiobutton(output_frame, text="CSV", variable=self.output_var, value="csv").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(output_frame, text="JSON", variable=self.output_var, value="json").pack(side=tk.LEFT, padx=5)
        
        # 左侧 - 日志显示区域
        log_frame = ttk.LabelFrame(left_frame, text="运行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 左侧 - 结果和可视化操作区域
        result_frame = ttk.LabelFrame(left_frame, text="结果与可视化操作", padding="10")
        result_frame.pack(fill=tk.X)
        
        # 结果操作按钮
        result_button_frame = ttk.Frame(result_frame)
        result_button_frame.pack(fill=tk.X)
        
        self.save_result_button = ttk.Button(result_button_frame, text="保存当前结果", command=self.save_current_results, state=tk.DISABLED)
        self.save_result_button.pack(side=tk.LEFT, padx=5)
        
        self.save_with_viz_button = ttk.Button(result_button_frame, text="保存结果和图表", command=self.save_with_visualizations, state=tk.DISABLED)
        self.save_with_viz_button.pack(side=tk.LEFT, padx=5)
        
        self.generate_charts_button = ttk.Button(result_button_frame, text="生成当前结果图表", command=self.generate_current_charts, state=tk.DISABLED)
        self.generate_charts_button.pack(side=tk.LEFT, padx=5)
        
        self.view_saved_results_button = ttk.Button(result_button_frame, text="查看已保存结果", command=self.view_saved_results)
        self.view_saved_results_button.pack(side=tk.LEFT, padx=5)
        
        # 右侧 - 结果显示区域
        result_display_frame = ttk.LabelFrame(right_frame, text="爬取结果预览", padding="10")
        result_display_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = scrolledtext.ScrolledText(result_display_frame, wrap=tk.WORD, height=20)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        self.result_text.config(state=tk.DISABLED)
        
        # 底部状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _check_spider_status(self):
        """检查爬虫状态并更新界面"""
        # 检查是否有断点文件
        if os.path.exists("breakpoint.txt"):
            try:
                with open("breakpoint.txt", "r", encoding='utf-8') as f:
                    page = int(f.read().strip())
                if page > 0:
                    self._log("检测到未完成的爬取任务，可以继续或重置。")
            except:
                pass
        
        # 检查是否有爬取结果
        if os.path.exists("douban_top250.csv") or os.path.exists("douban_top250.json"):
            self._log("检测到已存在的爬取结果文件。")
        
        # 检查是否有可视化结果
        if os.path.exists("visualizations"):
            self._log("检测到已存在的可视化结果文件夹。")
    
    def _log(self, message):
        """向日志区域添加消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        self.status_var.set(message)
    
    def start_spider(self):
        """开始爬取豆瓣电影Top250"""
        if self.is_spider_running:
            messagebox.showwarning("警告", "爬虫已经在运行中")
            return
        
        # 更新按钮状态
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.reset_button.config(state=tk.DISABLED)
        
        # 获取爬取参数
        mode = self.mode_var.get()
        output = self.output_var.get()
        
        self._log(f"开始{"全量" if mode == "full" else "测试"}爬取，输出格式：{output.upper()}...")
        
        # 在新线程中启动爬虫
        self.spider_thread = threading.Thread(target=self._run_spider, args=(mode, output))
        self.spider_thread.daemon = True
        self.spider_thread.start()
    
    def _run_spider(self, mode, output):
        """在后台线程中运行爬虫"""
        self.is_spider_running = True
        self.current_output_format = output
        
        try:
            # 创建临时文件路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_file = f"temp_result_{timestamp}.{output}"
            
            # 构建命令
            cmd = [sys.executable, "main.py", f"--mode", mode, f"--output", output]
            
            # 启动进程并捕获输出
            self.spider_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )
            # 设置控制台编码为UTF-8，确保中文显示正常
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            
            # 实时读取和显示输出
            for line in iter(self.spider_process.stdout.readline, ''):
                if not self.is_spider_running:
                    break
                self._log(line.strip())
            
            # 等待进程结束
            self.spider_process.wait()
            
            if self.is_spider_running:
                if self.spider_process.returncode == 0:
                    self._log("爬取完成！")
                    
                    # 读取爬取结果到内存
                    self._load_spider_results(output)
                    
                    # 启用保存和生成图表按钮
                    self.root.after(0, lambda: self.save_result_button.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.save_with_viz_button.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.generate_charts_button.config(state=tk.NORMAL))
                else:
                    self._log(f"爬取过程中发生错误，返回代码：{self.spider_process.returncode}")
        
        except Exception as e:
            self._log(f"启动爬虫时出错：{str(e)}")
        
        finally:
            self.is_spider_running = False
            self.spider_process = None
            
            # 恢复按钮状态
            self.root.after(0, self._reset_button_states)
    
    def stop_spider(self):
        """停止爬取"""
        if not self.is_spider_running:
            messagebox.showinfo("提示", "爬虫未在运行")
            return
        
        if messagebox.askyesno("确认", "确定要停止爬取吗？"):
            self._log("正在停止爬虫...")
            self.is_spider_running = False
            
            if self.spider_process:
                try:
                    # 尝试优雅终止进程
                    self.spider_process.terminate()
                    # 等待进程结束，最多等待3秒
                    for _ in range(30):
                        if self.spider_process.poll() is not None:
                            break
                        time.sleep(0.1)
                    else:
                        # 如果超时，强制终止
                        self.spider_process.kill()
                except Exception as e:
                    self._log(f"停止爬虫时出错：{str(e)}")
            
            self._log("爬虫已停止")
            self._reset_button_states()
    
    def reset_spider(self):
        """重置爬虫状态"""
        if self.is_spider_running:
            messagebox.showwarning("警告", "请先停止爬虫再重置")
            return
        
        if messagebox.askyesno("确认重置", "确定要重置爬虫状态吗？这将删除断点文件并清空当前结果。"):
            try:
                # 删除断点文件
                if os.path.exists("breakpoint.txt"):
                    os.remove("breakpoint.txt")
                    with open("breakpoint.txt", "w", encoding='utf-8') as f:
                        f.write("0")
                
                # 清空当前结果
                self.current_results = None
                self.current_output_format = None
                
                # 删除临时图表文件夹
                if self.temp_chart_folder and os.path.exists(self.temp_chart_folder):
                    try:
                        import shutil
                        shutil.rmtree(self.temp_chart_folder)
                        self._log(f"已删除临时图表文件夹：{self.temp_chart_folder}")
                    except Exception as e:
                        self._log(f"删除临时图表文件夹时出错：{str(e)}")
                self.temp_chart_folder = None
                
                # 清空结果显示区域
                self.result_text.config(state=tk.NORMAL)
                self.result_text.delete("1.0", tk.END)
                self.result_text.config(state=tk.DISABLED)
                
                # 禁用按钮
                self.save_result_button.config(state=tk.DISABLED)
                self.save_with_viz_button.config(state=tk.DISABLED)
                self.generate_charts_button.config(state=tk.DISABLED)
                
                self._log("爬虫状态已重置，可以重新开始爬取。")
            except Exception as e:
                self._log(f"重置状态时出错：{str(e)}")
    
    def _reset_button_states(self):
        """重置按钮状态"""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.reset_button.config(state=tk.NORMAL)
        
        # 根据数据状态设置保存相关按钮
        if self.current_results is not None:
            self.save_result_button.config(state=tk.NORMAL)
            self.generate_charts_button.config(state=tk.NORMAL)
            # 只有生成了临时图表才启用保存结果和图表按钮
            if self.temp_chart_folder and os.path.exists(self.temp_chart_folder):
                self.save_with_viz_button.config(state=tk.NORMAL)
            else:
                self.save_with_viz_button.config(state=tk.DISABLED)
        else:
            self.save_result_button.config(state=tk.DISABLED)
            self.generate_charts_button.config(state=tk.DISABLED)
            self.save_with_viz_button.config(state=tk.DISABLED)
    
    def _load_spider_results(self, output_format):
        """加载爬虫结果到内存并显示在右侧结果区域"""
        try:
            # 确定要读取的文件
            file_to_read = f"douban_top250.{output_format}"
            
            if os.path.exists(file_to_read):
                # 清空结果显示区域
                self.result_text.config(state=tk.NORMAL)
                self.result_text.delete("1.0", tk.END)
                
                # 设置等宽字体以提高表格可读性
                self.result_text.config(font=('Consolas', 10))
                
                if output_format == "csv":
                    # 读取CSV文件，指定UTF-8编码以避免中文编码问题
                    self.current_results = pd.read_csv(file_to_read, encoding='utf-8-sig')
                    
                    # 显示基本统计信息
                    preview_text = f"共发现 {len(self.current_results)} 条记录\n\n"
                    
                    # 选择要显示的重要列
                    important_columns = ['title', 'rating', 'comments', 'year']
                    display_columns = [col for col in important_columns if col in self.current_results.columns]
                    
                    # 如果没有找到重要列，则使用前几列
                    if not display_columns:
                        display_columns = self.current_results.columns[:min(4, len(self.current_results.columns))]
                    
                    # 确定要显示的记录数量
                    is_test_mode = self.mode_var.get() == "test"
                    display_limit = len(self.current_results) if is_test_mode else 50
                    
                    # 截取要显示的数据
                    display_data = self.current_results[display_columns].head(display_limit)
                    
                    # 生成格式化的表格
                    # 定义列宽（可根据需要调整）
                    column_widths = {}
                    for col in display_columns:
                        # 标题长度
                        title_len = len(str(col))
                        # 数据最大长度
                        data_len = display_data[col].astype(str).str.len().max()
                        # 取最大值，但限制在合理范围内
                        column_widths[col] = min(max(title_len, data_len) + 2, 20)
                    
                    # 生成表头
                    header = ""
                    for col in display_columns:
                        header += str(col).ljust(column_widths[col])
                    preview_text += header + "\n"
                    
                    # 生成分隔线
                    separator = ""
                    for col in display_columns:
                        separator += "-" * column_widths[col]
                    preview_text += separator + "\n"
                    
                    # 生成数据行
                    for _, row in display_data.iterrows():
                        row_text = ""
                        for col in display_columns:
                            # 截断过长的文本
                            cell_text = str(row[col])[:column_widths[col]-2]
                            row_text += cell_text.ljust(column_widths[col])
                        preview_text += row_text + "\n"
                    
                    if not is_test_mode and len(self.current_results) > 50:
                        preview_text += "\n... 仅显示前50条记录 ..."
                else:  # json
                    # 读取JSON文件
                    with open(file_to_read, 'r', encoding='utf-8') as f:
                        self.current_results = json.load(f)
                    
                    # 确定要显示的记录数量
                    is_test_mode = self.mode_var.get() == "test"
                    display_limit = len(self.current_results) if is_test_mode else 50
                    
                    # 显示记录作为预览
                    preview_text = f"共发现 {len(self.current_results)} 条记录\n\n"
                    for i, item in enumerate(self.current_results[:display_limit]):
                        preview_text += f"{'='*40}\n"
                        preview_text += f"电影 {i+1}:\n"
                        # 只显示重要字段
                        important_fields = ['title', 'rating', 'year', 'director', 'actors', 'genre']
                        for field in important_fields:
                            if field in item and item[field]:
                                # 截断过长的值
                                value = str(item[field])[:50]
                                if len(str(item[field])) > 50:
                                    value += "..."
                                preview_text += f"  {field}: {value}\n"
                        preview_text += "\n"
                    
                    if not is_test_mode and len(self.current_results) > 50:
                        preview_text += "... 仅显示前50条记录 ..."
                
                # 显示预览
                self.result_text.insert(tk.END, preview_text)
                self.result_text.config(state=tk.DISABLED)
                
                # 设置当前输出格式
                self.current_output_format = output_format
                
                # 启用相应的按钮
                self._reset_button_states()
                
                self._log(f"已加载爬取结果，共 {len(self.current_results)} 条记录")
            else:
                self._log(f"未找到结果文件：{file_to_read}")
                messagebox.showinfo("提示", f"未找到结果文件：{file_to_read}")
        
        except Exception as e:
            self._log(f"加载结果时出错：{str(e)}")
            messagebox.showerror("错误", f"加载结果时出错：{str(e)}")
    
    def save_current_results(self):
        """
        保存当前爬取结果到用户命名的文件夹中
        
        将当前加载的爬取结果以CSV格式保存到用户指定的文件夹中，
        支持检查文件是否已存在、确认覆盖操作，以及保存后打开文件夹查看。
        如果当前结果是JSON格式，会自动转换为DataFrame后再保存。
        """
        if self.current_results is None:
            messagebox.showinfo("提示", "没有可保存的结果")
            return
        
        # 生成默认文件夹名称 - 使用时间戳确保唯一性
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_folder = f"result_{timestamp}"
        
        # 创建一个对话框让用户输入文件夹名称
        dialog = tk.Toplevel(self.root)
        dialog.title("输入保存文件夹名称")
        dialog.geometry("300x150")
        dialog.transient(self.root)  # 设置为父窗口的子窗口
        dialog.grab_set()  # 模态对话框，阻止用户操作其他窗口
        dialog.resizable(False, False)  # 固定对话框大小
        
        # 居中显示对话框 - 提升用户体验
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
        y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # 添加标签和输入框
        ttk.Label(dialog, text="请输入保存文件夹名称：").pack(pady=(15, 5))
        
        folder_var = tk.StringVar(value=default_folder)
        entry = ttk.Entry(dialog, textvariable=folder_var, width=30)
        entry.pack(pady=5)
        entry.select_range(0, tk.END)  # 选中默认文本
        entry.focus_set()  # 设置焦点到输入框
        
        def on_confirm():
            """处理确认保存操作
            
            验证文件夹名称，创建文件夹，检查文件是否已存在，
            保存结果数据，并处理各种异常情况。
            """
            folder_name = folder_var.get().strip()
            if not folder_name:
                messagebox.showwarning("警告", "文件夹名称不能为空")
                return
            
            dialog.destroy()  # 关闭对话框
            
            try:
                # 创建用户命名的文件夹
                if not os.path.exists(folder_name):
                    os.makedirs(folder_name)
                
                # 保存CSV文件到该文件夹
                csv_file = os.path.join(folder_name, "douban_movies.csv")
                
                # 检查文件是否已存在或文件夹中是否有图表文件夹，如果存在则询问用户
                charts_folder = os.path.join(folder_name, "图表")
                has_existing_data = os.path.exists(csv_file) or (os.path.exists(charts_folder) and os.listdir(charts_folder))
                
                if has_existing_data:
                    # 文件或文件夹已存在，询问是否覆盖
                    response = messagebox.askyesnocancel(
                        "文件/文件夹已存在", 
                        f"目标位置已存在CSV文件或图表文件夹，是否覆盖？",
                        default=messagebox.NO
                    )
                    if response is None:  # 用户取消操作
                        self._log("用户取消了保存操作")
                        return
                    elif not response:  # 用户选择不覆盖，退出
                        self._log("用户选择不覆盖现有内容，保存操作已取消")
                        return
                    # 如果用户选择覆盖，检查并清理图表文件夹
                    self._log(f"用户选择覆盖现有内容：{folder_name}")
                    if os.path.exists(charts_folder):
                        self._log(f"检测到现有图表文件夹：{charts_folder}，正在清理...")
                        try:
                            import shutil
                            shutil.rmtree(charts_folder)  # 清空现有图表文件夹
                            self._log("图表文件夹已清理")
                        except Exception as e:
                            self._log(f"清理图表文件夹时出错：{str(e)}")
                
                # 保存CSV文件
                self._log(f"正在保存CSV结果到：{csv_file}")
                if self.current_output_format == "json":
                    # 如果当前数据是JSON格式，先转换为DataFrame
                    df = pd.DataFrame(self.current_results)
                    df.to_csv(csv_file, index=False, encoding='utf-8')
                else:
                    # 如果是DataFrame格式，直接保存
                    self.current_results.to_csv(csv_file, index=False, encoding='utf-8')
                
                # 记录保存成功日志
                self._log(f"结果已保存到：{csv_file}")
                # 显示成功提示消息，告知用户文件保存位置
                messagebox.showinfo("成功", f"结果已成功保存到：\n{folder_name}/douban_movies.csv")
                
                # 询问用户是否需要立即打开保存文件夹
                if messagebox.askyesno("提示", f"是否打开{folder_name}文件夹查看？"):
                    # 根据操作系统选择合适的方式打开文件夹
                    if os.name == 'nt':  # Windows系统
                        os.startfile(folder_name)
                    else:  # macOS/Linux系统
                        webbrowser.open(folder_name)
                
            # 捕获所有异常，确保程序稳定运行
            except Exception as e:
                # 记录错误日志
                self._log(f"保存结果时出错：{str(e)}")
                # 显示错误消息给用户
                messagebox.showerror("错误", f"保存结果时出错：{str(e)}")
        
        # 创建按钮框架并添加确定和取消按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)  # 添加垂直边距
        
        # 添加确定和取消按钮，设置合适的水平间距
        ttk.Button(button_frame, text="确定", command=on_confirm).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=10)
        
        # 添加键盘快捷键支持 - 按Enter键也可以确认
        dialog.bind('<Return>', lambda event: on_confirm())
    
    def save_with_visualizations(self):
        """保存结果和可视化图表
        
        该方法将爬虫结果数据和生成的可视化图表一起保存到用户指定的文件夹中。
        使用前必须先有爬虫结果数据，并且已经成功生成可视化图表。
        
        实现流程：
        1. 验证是否存在可保存的结果数据
        2. 验证是否已生成可视化图表
        3. 弹出对话框让用户指定保存文件夹名称
        4. 创建文件夹并进行覆盖确认
        5. 保存CSV数据文件
        6. 复制图表文件到目标位置
        7. 提供打开文件夹的选项
        """
        # 验证是否有可保存的结果数据
        if self.current_results is None:
            messagebox.showinfo("提示", "没有可保存的结果")
            return
        
        # 验证是否已生成可视化图表
        if self.temp_chart_folder is None or not os.path.exists(self.temp_chart_folder):
            messagebox.showinfo("提示", "请先生成图表，然后再保存结果和图表")
            return
        
        # 生成默认文件夹名称 - 使用时间戳确保唯一性
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_folder = f"result_with_charts_{timestamp}"
        
        # 创建文件夹命名对话框 - 模态对话框设计
        dialog = tk.Toplevel(self.root)
        dialog.title("输入保存文件夹名称")
        dialog.geometry("300x150")
        dialog.transient(self.root)  # 设置为主窗口的子窗口
        dialog.grab_set()  # 模态对话框，阻止用户操作主窗口
        dialog.resizable(False, False)  # 固定对话框大小
        
        # 居中显示对话框 - 提升用户体验
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
        y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # 添加标签和输入框
        ttk.Label(dialog, text="请输入保存文件夹名称：").pack(pady=(15, 5))
        
        # 预设默认文件夹名称并自动选中
        folder_var = tk.StringVar(value=default_folder)
        entry = ttk.Entry(dialog, textvariable=folder_var, width=30)
        entry.pack(pady=5)
        entry.select_range(0, tk.END)  # 选中默认文本
        entry.focus_set()  # 设置输入焦点
        
        def on_confirm():
            """处理保存确认操作
            
            验证文件夹名称，创建或清理目标文件夹，保存CSV数据
            并复制可视化图表到指定位置，同时提供错误处理机制。
            """
            # 验证文件夹名称
            folder_name = folder_var.get().strip()
            if not folder_name:
                messagebox.showwarning("警告", "文件夹名称不能为空")
                return
            
            # 关闭对话框
            dialog.destroy()
            
            try:
                # 创建用户命名的文件夹或检查现有文件夹
                folder_exists = os.path.exists(folder_name)
                if not folder_exists:
                    # 创建新文件夹
                    os.makedirs(folder_name)
                else:
                    # 检查是否有文件会被覆盖
                    csv_file = os.path.join(folder_name, "douban_movies.csv")
                    charts_folder = os.path.join(folder_name, "图表")
                    
                    # 如果目标文件夹已存在CSV文件或图表文件夹，询问用户是否覆盖
                    if os.path.exists(csv_file) or (os.path.exists(charts_folder) and os.listdir(charts_folder)):
                        response = messagebox.askyesnocancel(
                            "文件夹已存在", 
                            f"文件夹 {folder_name} 已存在且可能包含文件，是否继续并覆盖现有文件？",
                            default=messagebox.NO  # 默认选择为不覆盖
                        )
                        if response is None:  # 用户取消操作
                            self._log("用户取消了保存操作")
                            return
                        elif not response:  # 用户选择不覆盖，退出
                            self._log("用户选择不覆盖现有文件，保存操作已取消")
                            return
                        # 如果用户选择覆盖，继续执行后续操作
                        self._log(f"用户选择覆盖现有文件夹内容：{folder_name}")
                
                # 创建图表子文件夹（如果不存在或需要覆盖）
                charts_folder = os.path.join(folder_name, "图表")
                # 无论用户选择覆盖还是文件夹为空，都重新创建图表文件夹，确保内容完全更新
                if os.path.exists(charts_folder):
                    self._log(f"检测到现有图表文件夹：{charts_folder}，正在清空...")
                    try:
                        import shutil
                        shutil.rmtree(charts_folder)  # 清空现有图表文件夹，删除所有内容
                        self._log("图表文件夹已清空")
                    except Exception as e:
                        self._log(f"清空图表文件夹时出错：{str(e)}")
                
                # 重新创建图表文件夹
                try:
                    os.makedirs(charts_folder)
                    self._log(f"图表文件夹已重新创建：{charts_folder}")
                except Exception as e:
                    self._log(f"创建图表文件夹时出错：{str(e)}")
                
                # 保存CSV文件到主文件夹
                csv_file = os.path.join(folder_name, "douban_movies.csv")
                self._log(f"正在保存CSV结果到：{csv_file}")
                # 根据当前数据格式进行适当转换后保存
                if self.current_output_format == "json":
                    # JSON格式需要先转换为DataFrame
                    df = pd.DataFrame(self.current_results)
                    df.to_csv(csv_file, index=False, encoding='utf-8')
                else:
                    # DataFrame格式直接保存
                    self.current_results.to_csv(csv_file, index=False, encoding='utf-8')
                
                # 复制图表到图表文件夹 - 确保只复制PNG图像文件
                import shutil
                chart_files = os.listdir(self.temp_chart_folder)
                for chart_file in chart_files:
                    # 只复制PNG格式的图表文件
                    if chart_file.endswith('.png'):
                        src = os.path.join(self.temp_chart_folder, chart_file)  # 源文件路径
                        dst = os.path.join(charts_folder, chart_file)          # 目标文件路径
                        shutil.copy2(src, dst)  # 复制文件，保留元数据
                
                # 记录保存成功日志
                self._log(f"结果和图表已保存到：{folder_name}")
                # 显示保存成功提示
                messagebox.showinfo("成功", f"结果和图表已成功保存到：\n{folder_name}")
                
                # 询问用户是否需要立即打开保存文件夹查看
                if messagebox.askyesno("提示", f"是否打开{folder_name}文件夹查看？"):
                    # 根据操作系统使用适当的方式打开文件夹
                    if os.name == 'nt':  # Windows系统
                        os.startfile(folder_name)  # 使用Windows默认程序打开
                    else:  # macOS/Linux系统
                        webbrowser.open(folder_name)  # 使用浏览器打开
                
            # 全局异常处理，确保程序稳定性
            except Exception as e:
                # 记录错误日志
                self._log(f"保存结果和图表时出错：{str(e)}")
                # 显示错误消息给用户
                messagebox.showerror("错误", f"保存结果和图表时出错：{str(e)}")
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="确定", command=on_confirm).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=10)
        
        # 按Enter键确认
        dialog.bind('<Return>', lambda event: on_confirm())
    
    def view_saved_results(self):
        """查看已保存的爬取结果
        
        该方法提供了一个文件选择对话框，让用户选择并使用系统默认程序打开已保存的
        CSV或JSON格式的爬取结果文件。支持CSV和JSON两种格式的文件预览。
        """
        # 打开文件选择对话框，限制只显示CSV和JSON文件
        filetypes = [("所有支持的文件", "*.csv;*.json"), ("CSV文件", "*.csv"), ("JSON文件", "*.json")]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        
        # 检查用户是否选择了文件
        if filename:
            try:
                # 根据操作系统使用合适的方式打开文件
                if os.name == 'nt':  # Windows系统
                    os.startfile(filename)  # 使用Windows默认程序打开
                else:  # macOS/Linux系统
                    webbrowser.open(filename)  # 使用浏览器打开
                # 记录日志
                self._log(f"正在打开结果文件：{filename}")
            # 异常处理，确保程序稳定性
            except Exception as e:
                self._log(f"无法打开结果文件：{str(e)}")
                messagebox.showerror("错误", f"无法打开结果文件：{str(e)}")
    
    def generate_current_charts(self):
        """生成当前结果的临时可视化图表用于预览
        
        该方法为当前爬取的电影数据生成可视化图表，并保存到临时文件夹中。
        图表生成完成后可用于预览或保存。使用了Python内置的subprocess模块
        调用外部的visualization.py脚本生成图表。
        """
        # 验证是否有数据可供生成图表
        if self.current_results is None:
            messagebox.showinfo("提示", "没有可生成图表的数据")
            return
        
        # 生成临时文件夹名称，使用时间戳确保唯一性（精确到微秒）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_folder = f"temp_charts_{timestamp}"
        
        # 删除之前的临时文件夹（如果存在），避免旧数据干扰
        if self.temp_chart_folder and os.path.exists(self.temp_chart_folder):
            try:
                import shutil
                shutil.rmtree(self.temp_chart_folder)
                self._log(f"已删除之前的临时图表文件夹：{self.temp_chart_folder}")
            except Exception as e:
                self._log(f"删除临时图表文件夹时出错：{str(e)}")
        
        # 设置新的临时图表文件夹路径
        self.temp_chart_folder = temp_folder
        
        # 调用_process_chart_generation处理图表生成
        self._process_chart_generation(temp_folder)
        
        # 启用保存结果和图表按钮
        if self.save_with_viz_button:
            self.save_with_viz_button.config(state=tk.NORMAL)
    
    def _process_chart_generation(self, charts_folder):
        """处理图表生成逻辑
        
        该方法是图表生成的核心实现，负责：
        1. 临时保存当前爬取结果为CSV格式
        2. 在单独线程中调用visualization.py脚本生成图表
        3. 实时显示图表生成日志
        4. 创建图表预览窗口展示生成结果
        5. 处理图表生成成功或失败的各种情况
        
        Args:
            charts_folder (str): 图表保存的目标文件夹路径
        """
        # 临时保存当前结果用于生成图表
        temp_file = "temp_for_charts.csv"
        try:
            # 保存为临时CSV文件，供visualization.py使用
            if self.current_output_format == "json":
                # 如果是JSON数据，转换为DataFrame再保存
                df = pd.DataFrame(self.current_results)
                df.to_csv(temp_file, index=False, encoding='utf-8')
            else:
                # 如果是DataFrame数据，直接保存
                self.current_results.to_csv(temp_file, index=False, encoding='utf-8')
            
            # 更新生成图表按钮状态为禁用，防止重复点击
            self.generate_charts_button.config(state=tk.DISABLED)
            
            # 记录开始生成图表的日志
            self._log(f"开始为当前结果生成可视化图表，图表将保存到：{charts_folder}")
            
            # 在新线程中运行可视化脚本，避免阻塞UI
            def run_visualization():
                """在单独线程中运行可视化脚本
                
                该函数负责：
                1. 创建输出文件夹
                2. 调用visualization.py脚本处理数据并生成图表
                3. 实时捕获和显示脚本输出日志
                4. 检查图表生成结果
                5. 创建图表预览窗口
                6. 处理各种异常情况
                """
                try:
                    # 确保输出文件夹存在
                    if not os.path.exists(charts_folder):
                        os.makedirs(charts_folder)
                    
                    # 运行visualization.py脚本，传入临时文件和输出文件夹
                    # 使用subprocess.Popen非阻塞方式启动进程
                    process = subprocess.Popen(
                        [sys.executable, "visualization.py", "--input", temp_file, "--output_folder", charts_folder],
                        stdout=subprocess.PIPE,        # 捕获标准输出
                        stderr=subprocess.STDOUT,      # 合并标准错误到标准输出
                        text=True,                     # 以文本模式处理输出
                        bufsize=1,                     # 行缓冲，实时显示输出
                        encoding='utf-8',              # 使用UTF-8编码
                        errors='replace'               # 替换无法解码的字符
                    )
                    
                    # 实时读取和显示输出，避免程序卡顿
                    for line in iter(process.stdout.readline, ''):
                        self._log(line.strip())  # 移除换行符并记录日志
                    
                    # 等待进程结束并获取返回码
                    process.wait()
                    
                    # 检查图表文件是否成功生成
                    chart_files_generated = False
                    chart_files = []  # 存储生成的图表文件列表
                    if os.path.exists(charts_folder):
                        # 过滤出所有PNG格式的图表文件
                        chart_files = [f for f in os.listdir(charts_folder) if f.endswith('.png')]
                        chart_files_generated = len(chart_files) > 0
                    
                    if process.returncode == 0 and chart_files_generated:
                        # 记录图表生成成功日志
                        self._log(f"可视化图表生成完成！图表保存在 {charts_folder} 文件夹中。")
                        
                        # 创建图表预览窗口
                        preview_window = tk.Toplevel(self.root)
                        preview_window.title("图表预览")
                        preview_window.geometry("800x600")
                        preview_window.transient(self.root)  # 设置为临时窗口，与主窗口关联
                        
                        # 实现可滚动界面
                        # 创建画布作为滚动区域
                        canvas = tk.Canvas(preview_window)
                        # 添加垂直滚动条
                        scrollbar = ttk.Scrollbar(preview_window, orient="vertical", command=canvas.yview)
                        # 创建可滚动的框架
                        scrollable_frame = ttk.Frame(canvas)
                        
                        # 当滚动框架内容改变时，更新画布的滚动区域
                        scrollable_frame.bind(
                            "<Configure>",
                            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
                        )
                        
                        # 将滚动框架添加到画布中
                        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
                        # 连接滚动条和画布
                        canvas.configure(yscrollcommand=scrollbar.set)
                        
                        # 放置画布和滚动条
                        canvas.pack(side="left", fill="both", expand=True)
                        scrollbar.pack(side="right", fill="y")
                        
                        # 显示图表列表和基本信息
                        ttk.Label(scrollable_frame, text=f"已生成 {len(chart_files)} 张图表", font=("SimHei", 12, "bold")).pack(pady=10)
                        
                        # 图表预览部分
                        ttk.Label(scrollable_frame, text="图表预览:", font=("SimHei", 10)).pack(anchor="w", padx=20, pady=(10, 5))
                        
                        # 尝试导入PIL库来显示图像
                        try:
                            from PIL import Image, ImageTk
                            has_pil = True
                        except ImportError:
                            has_pil = False
                            ttk.Label(scrollable_frame, text="提示: 未安装PIL库，无法显示图表预览图像。请安装Pillow库以启用图像预览功能。", 
                                     font=("SimHei", 10), foreground="red").pack(anchor="w", padx=20, pady=5)
                        
                        # 图表文件列表（始终显示）
                        ttk.Label(scrollable_frame, text="图表文件列表:", font=("SimHei", 10)).pack(anchor="w", padx=20, pady=(10, 5))
                        chart_listbox = tk.Text(scrollable_frame, height=6, width=50, font=("Consolas", 10))
                        for i, chart_file in enumerate(chart_files, 1):
                            chart_listbox.insert(tk.END, f"{i}. {chart_file}\n")
                        chart_listbox.config(state=tk.DISABLED)
                        chart_listbox.pack(anchor="w", padx=20)
                        
                        # 如果有PIL库，显示图表图像
                        if has_pil and chart_files:
                            # 创建一个框架来放置图像
                            image_frame = ttk.Frame(scrollable_frame)
                            image_frame.pack(fill="x", padx=20, pady=10)
                            
                            # 显示前3张图表作为预览
                            for i, chart_file in enumerate(chart_files[:3]):
                                chart_path = os.path.join(charts_folder, chart_file)
                                if os.path.exists(chart_path):
                                    try:
                                        # 创建图像容器
                                        img_container = ttk.Frame(image_frame)
                                        img_container.pack(side="top", fill="x", pady=5)
                                        
                                        # 显示图表名称
                                        ttk.Label(img_container, text=f"{i+1}. {chart_file}", font=("SimHei", 9)).pack(anchor="w", pady=(0, 3))
                                        
                                        # 打开图像并调整大小以适应预览
                                        image = Image.open(chart_path)
                                        # 调整图像大小，保持宽高比
                                        image.thumbnail((700, 300))
                                        
                                        # 转换为Tkinter可用的格式
                                        photo = ImageTk.PhotoImage(image)
                                        
                                        # 创建标签显示图像
                                        img_label = ttk.Label(img_container, image=photo)
                                        img_label.image = photo  # 保持引用，防止被垃圾回收
                                        img_label.pack(anchor="center")
                                    except Exception as e:
                                        ttk.Label(img_container, text=f"无法加载图表 {chart_file}: {str(e)}", 
                                                 font=("SimHei", 9), foreground="red").pack(anchor="w")
                        
                        # 如果没有PIL库或没有图表，显示提示
                        if not has_pil and chart_files:
                            ttk.Label(scrollable_frame, text="请点击'打开图表文件夹'按钮查看实际图表文件。", 
                                     font=("SimHei", 9), foreground="blue").pack(anchor="w", padx=20, pady=5)
                        
                        # 添加操作按钮
                        button_frame = ttk.Frame(scrollable_frame)
                        button_frame.pack(pady=15)
                        
                        # 打开文件夹按钮
                        ttk.Button(
                            button_frame, 
                            text="打开图表文件夹", 
                            command=lambda: (
                                preview_window.destroy(),
                                os.startfile(charts_folder) if os.name == 'nt' else webbrowser.open(charts_folder)
                            )
                        ).pack(side=tk.LEFT, padx=10)
                        
                        # 关闭按钮
                        ttk.Button(button_frame, text="关闭", command=preview_window.destroy).pack(side=tk.LEFT, padx=10)
                        
                        messagebox.showinfo("成功", "可视化图表已生成完成！请查看预览窗口查看图表文件列表和图像预览。")
                    else:
                        error_msg = "生成图表时发生错误"
                        if not chart_files_generated:
                            error_msg += "：未生成任何图表文件"
                        else:
                            error_msg += f"，返回代码：{process.returncode}"
                        
                        self._log(error_msg)
                        messagebox.showerror("错误", error_msg + "，请查看日志。")
                    
                except Exception as e:
                    self._log(f"运行可视化脚本时出错：{str(e)}")
                    messagebox.showerror("错误", f"运行可视化脚本时出错：{str(e)}")
                
                finally:
                    # 删除临时文件
                    if os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                    
                    # 恢复按钮状态
                    self.root.after(0, lambda: self.generate_charts_button.config(state=tk.NORMAL))
            
            # 启动可视化线程
            viz_thread = threading.Thread(target=run_visualization)
            viz_thread.daemon = True
            viz_thread.start()
        
        except Exception as e:
            self._log(f"准备生成图表时出错：{str(e)}")
            messagebox.showerror("错误", f"准备生成图表时出错：{str(e)}")
            
            # 清理临时文件
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
    
    def view_charts_folder(self):
        """浏览所有图表文件夹"""
        # 获取当前目录下所有以visualizations_开头的文件夹
        chart_folders = []
        for item in os.listdir('.'):
            if os.path.isdir(item) and item.startswith('visualizations_'):
                chart_folders.append((item, os.path.getmtime(item)))
        
        # 如果也有原始的visualizations文件夹，也加入列表
        if os.path.exists('visualizations'):
            chart_folders.append(('visualizations', os.path.getmtime('visualizations')))
        
        # 按修改时间排序（最新的在前）
        chart_folders.sort(key=lambda x: x[1], reverse=True)
        
        if chart_folders:
            # 创建选择对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("选择图表文件夹")
            dialog.geometry("400x300")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # 添加滚动列表
            listbox = tk.Listbox(dialog)
            listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            scrollbar = ttk.Scrollbar(listbox, orient="vertical", command=listbox.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            listbox.config(yscrollcommand=scrollbar.set)
            
            # 填充列表
            for folder, _ in chart_folders:
                listbox.insert(tk.END, folder)
            
            # 选择按钮
            def open_selected():
                if listbox.curselection():
                    selected_folder = listbox.get(listbox.curselection()[0])
                    try:
                        if os.name == 'nt':  # Windows
                            os.startfile(selected_folder)
                        else:  # macOS/Linux
                            webbrowser.open(selected_folder)
                        self._log(f"正在打开图表文件夹：{selected_folder}")
                        dialog.destroy()
                    except Exception as e:
                        self._log(f"无法打开图表文件夹：{str(e)}")
                        messagebox.showerror("错误", f"无法打开图表文件夹：{str(e)}")
            
            # 按钮框
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            ttk.Button(button_frame, text="打开选中的文件夹", command=open_selected).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        else:
            messagebox.showinfo("提示", "未找到任何图表文件夹，请先生成可视化图表。")
    
    def on_closing(self):
        """窗口关闭时的处理"""
        if self.is_spider_running:
            if messagebox.askyesno("确认关闭", "爬虫正在运行中，确定要关闭程序吗？"):
                self.stop_spider()
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    """主函数"""
    root = tk.Tk()
    app = DoubanSpiderGUI(root)
    
    # 设置窗口关闭处理
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # 运行主循环
    root.mainloop()

if __name__ == "__main__":
    main()