# 豆瓣电影Top250爬虫 - 优化版

基于Python开发的豆瓣电影Top250数据爬取工具，具备完善的反爬策略、高稳定性和灵活的存储选项。

## 优化特性

### 1. 反爬策略优化
- **Cookie动态化处理**：支持从文件加载Cookie，避免手动复制
- **请求头多样化**：内置多种浏览器User-Agent，随机切换
- **代理IP池集成**：支持配置代理IP池，自动检测有效性
- **自适应延时**：根据响应时间动态调整请求间隔，避免被封

### 2. 数据解析与完整性优化
- **字段细分**：将原有的合并字段拆分为独立字段（年份、国家、类型）
- **数据校验**：自动过滤异常数据（评分过低、评论数过少等）
- **详情页支持**：可选爬取电影详情页，获取更多信息

### 3. 稳定性与容错优化
- **重试机制升级**：对关键字段解析失败时自动重试
- **断点续爬**：程序中断后可从上次位置继续，无需重新开始
- **完善的日志**：详细记录爬取过程，便于问题排查

### 4. 性能与效率优化
- **异步请求支持**：使用aiohttp实现异步爬取，提升效率
- **多种存储选项**：支持CSV、JSON、MySQL三种存储方式
- **数据去重**：自动检测重复数据，避免重复存储

### 5. 易用性与扩展性优化
- **命令行参数**：支持通过命令行调整运行参数，无需修改代码
- **配置文件分离**：核心参数集中在config.yaml，易于维护
- **模块化架构**：代码按功能拆分为多个模块，耦合度低

## 快速开始

### 安装依赖

```bash
pip install requests beautifulsoup4 pyyaml pymysql aiohttp
```

### 基本使用

#### 测试模式（只爬取第一页）

```bash
python main.py
```

#### 全量爬取（250部电影）

```bash
python main.py --mode full
```

#### 指定输出格式

```bash
# 保存为JSON格式
python main.py --output json

# 保存到MySQL数据库
python main.py --output mysql
```

#### 使用异步模式

```bash
python main.py --async
```

#### 手动指定Cookie

```bash
python main.py --cookie "your_cookie_here"
```

## 配置文件说明

项目使用`config.yaml`作为配置文件，包含以下主要配置项：

- **headers_pool**：请求头池，用于随机切换User-Agent
- **delay_range**：延时范围配置，根据响应时间自动调整
- **mysql_config**：MySQL数据库连接配置
- **proxies**：代理IP列表（需取消注释并填写实际代理）
- **cookie_file**：Cookie文件路径
- **breakpoint_file**：断点文件路径

## 项目结构

```
douban_spider/
├── main.py              # 主程序入口
├── config.py            # 配置管理模块
├── request_utils.py     # 请求工具模块
├── parse_utils.py       # 解析工具模块
├── storage_utils.py     # 存储工具模块
├── config.yaml          # 配置文件
├── douban_top250.csv    # CSV输出文件
├── douban_top250.json   # JSON输出文件
├── douban_cookie.json   # Cookie存储文件
└── breakpoint.txt       # 断点记录文件
```

## 注意事项

1. **反爬提示**：豆瓣有严格的反爬机制，建议合理设置爬取间隔
2. **Cookie使用**：长期运行建议通过浏览器手动登录后导出Cookie
3. **代理配置**：如需使用代理，请在config.yaml中配置有效的代理IP
4. **MySQL存储**：使用前需确保MySQL服务已启动，并创建相应的数据库

## 扩展建议

1. 实现定时任务，定期更新电影数据
2. 添加邮件告警功能，当爬虫遇到严重问题时及时通知
3. 开发Web界面，可视化展示爬取结果和状态
4. 扩展支持更多电影榜单，如热门电影、新片榜等