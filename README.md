# douban-top250-crawler
豆瓣电影Top250爬虫（优化版）- 高稳定性、可配置、支持断点续爬与数据可视化

## 项目简介
一个基于Python开发的豆瓣电影Top250爬虫工具，支持：
- 异步/同步爬取双模式
- 断点续爬（避免重复爬取）
- Cookie持久化（解决反爬限制）
- 多格式数据导出（CSV/JSON）
- 电影评分分布可视化
- 完善的日志记录与异常处理

## 🛠 技术栈
- 核心语言：Python 3.8+
- 爬虫核心：requests / aiohttp（异步）
- 数据解析：BeautifulSoup4
- 配置管理：PyYAML
- 数据存储：CSV/JSON / MySQL（可选）
- 可视化：matplotlib
- 辅助工具：python-dotenv（敏感配置隔离）

## 项目结构
douban-top250-crawler/
├── README.md               # 项目说明文档
├── requirements.txt        # 依赖清单
├── .gitignore              # Git忽略规则
├── .env.example            # 环境变量示例（敏感配置）
├── start.bat               # Windows一键启动脚本
├── config.yaml             # 核心配置文件
├── config.py               # 配置加载模块
├── main.py                 # 爬虫主程序
├── crawler.py              # 爬虫核心逻辑
├── parser.py               # 数据解析模块
├── storage.py              # 数据存储模块
├── visualization.py        # 数据可视化模块
├── utils/                  # 工具函数目录
│   ├── log_utils.py        # 日志工具
│   ├── exception_utils.py  # 异常处理工具
│   └── cookie_utils.py     # Cookie管理工具
├── data/                   # 爬取数据存储目录（运行后生成）
│   ├── douban_top250.csv   # CSV格式数据
│   └── douban_top250.json  # JSON格式数据
├── logs/                   # 日志目录（运行后生成）
└── cache/                  # 缓存目录（运行后生成）
    ├── douban_cookie.json  # Cookie缓存文件
    └── breakpoint.json     # 断点续爬缓存文件

## ⚙️ 环境准备
### 1. 安装依赖
pip install -r requirements.txt

### 2. 配置文件
- 复制 .env.example 为 .env，填写MySQL密码（若使用MySQL存储）：
MYSQL_PASSWORD=your_mysql_password

- 修改 config.yaml 配置项（按需调整）：
# 爬虫配置
crawler:
  mode: "async"          # 爬取模式：async(异步)/sync(同步)
  delay: 1               # 请求延迟（秒），避免反爬
  retry_times: 3         # 失败重试次数
# 存储配置
storage:
  format: ["csv", "json"] # 导出格式
  mysql: False           # 是否启用MySQL存储
# 缓存配置
cache:
  cookie_file: "cache/douban_cookie.json"
  breakpoint_file: "cache/breakpoint.json"

## 快速启动
### Windows
# 双击启动（推荐）
start.bat

# 或命令行启动
python main.py

### Linux/Mac
python main.py

## 📊 输出结果
运行完成后，可在 data/ 目录下查看：
- douban_top250.csv：结构化电影数据（包含排名、标题、评分、导演、演员、简介等）
- douban_top250.json：JSON格式数据，便于后续接口调用
- ratings_distribution.png：评分分布可视化图表（生成在data/目录）

##  核心功能说明
### 1. 断点续爬
爬虫会记录已爬取的电影ID到 cache/breakpoint.json，若中途中断，重新运行会自动从断点处继续爬取。

### 2. 反爬策略
- Cookie持久化：自动保存/加载豆瓣Cookie，避免频繁登录
- 随机请求延迟：避免请求频率过高触发反爬
- 失败重试：请求失败自动重试，提升稳定性

### 3. 数据可视化
运行完成后自动生成评分分布柱状图，直观展示Top250电影的评分分布规律。

##  注意事项
1. 请勿频繁爬取，遵守豆瓣网站的robots协议
2. 若出现爬取失败，可更新 cache/douban_cookie.json 中的Cookie
3. 敏感配置（如MySQL密码）请写在 .env 文件，不要直接提交到代码仓库
