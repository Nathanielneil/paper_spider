# ArXiv Paper Crawler 使用指南

本文档详细介绍如何使用 ArXiv 学术论文爬虫系统的各种功能。

## 目录

1. [快速开始](#快速开始)
2. [命令详细说明](#命令详细说明)
3. [配置文件详解](#配置文件详解)
4. [高级用法](#高级用法)
5. [故障排除](#故障排除)
6. [API 使用](#API-使用)

## 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 首次运行

```bash
# 直接运行会创建默认配置文件
python main.py

# 或者查看帮助
python main.py --help
```

### 3. 基本搜索

```bash
# 搜索机器学习相关论文
python main.py search --query "machine learning" --max-results 10

# 搜索特定作者的论文
python main.py search --author "Geoffrey Hinton" --max-results 20

# 搜索特定分类的论文
python main.py search --category "cs.AI" --max-results 15
```

### 4. 下载论文

```bash
# 搜索并交互式选择下载
python main.py download --query "deep learning" --interactive

# 直接下载搜索结果
python main.py download --query "neural networks" --max-results 10
```

## 命令详细说明

### search - 搜索论文

搜索 ArXiv 论文并将结果保存到数据库。

```bash
python main.py search [OPTIONS]
```

**选项：**
- `--query, -q TEXT`: 通用搜索查询
- `--author, -a TEXT`: 按作者搜索
- `--title, -t TEXT`: 按标题关键词搜索
- `--abstract TEXT`: 按摘要关键词搜索
- `--category, -c TEXT`: 按 ArXiv 分类搜索
- `--date-from TEXT`: 开始日期 (YYYY-MM-DD)
- `--date-to TEXT`: 结束日期 (YYYY-MM-DD)
- `--max-results, -n INTEGER`: 最大结果数 (默认: 50)
- `--sort-by [relevance|lastUpdatedDate|submittedDate]`: 排序标准
- `--sort-order [ascending|descending]`: 排序顺序
- `--export, -e TEXT`: 导出结果到文件 (JSON/CSV)
- `--show-details`: 显示详细论文信息

**示例：**

```bash
# 基础搜索
python main.py search --query "transformer neural network"

# 组合搜索条件
python main.py search --author "Yoshua Bengio" --category "cs.LG" --date-from "2020-01-01"

# 导出搜索结果
python main.py search --query "computer vision" --export results.json --max-results 100

# 按最新更新排序
python main.py search --query "GPT" --sort-by "lastUpdatedDate" --sort-order "descending"
```

### download - 下载论文

下载论文的 PDF 文件。

```bash
python main.py download [OPTIONS]
```

**选项：**
- `--input, -i TEXT`: 从 JSON 文件加载论文列表
- `--query, -q TEXT`: 搜索查询（用于下载）
- `--category, -c TEXT`: 下载特定分类的论文
- `--max-results, -n INTEGER`: 最大下载数量
- `--threads, -t INTEGER`: 下载线程数 (默认: 5)
- `--interactive`: 交互式选择要下载的论文
- `--output-dir, -o TEXT`: 输出目录

**示例：**

```bash
# 交互式下载
python main.py download --query "machine learning" --interactive

# 批量下载
python main.py download --query "deep learning" --max-results 20 --threads 8

# 从 JSON 文件下载
python main.py download --input search_results.json --interactive

# 指定输出目录
python main.py download --query "robotics" --output-dir /path/to/papers
```

### update - 更新数据库

从 ArXiv 获取新论文更新数据库。

```bash
python main.py update [OPTIONS]
```

**选项：**
- `--category, -c TEXT`: 更新特定分类
- `--days, -d INTEGER`: 获取最近 N 天的论文 (默认: 7)
- `--max-results, -n INTEGER`: 最大更新数量

**示例：**

```bash
# 更新最近 7 天的所有论文
python main.py update

# 更新特定分类的论文
python main.py update --category "cs.AI" --days 14

# 限制更新数量
python main.py update --max-results 500
```

### stats - 数据库统计

显示数据库统计信息。

```bash
python main.py stats [OPTIONS]
```

**选项：**
- `--category, -c TEXT`: 显示特定分类的统计
- `--export, -e TEXT`: 导出统计信息到文件

**示例：**

```bash
# 显示总体统计
python main.py stats

# 导出统计信息
python main.py stats --export statistics.json
```

### search-local - 本地搜索

在本地数据库中搜索论文。

```bash
python main.py search-local [OPTIONS]
```

**选项：**
- `--query, -q TEXT`: 搜索查询 (必需)
- `--fields TEXT`: 搜索字段 (默认: title,abstract,authors)
- `--limit, -l INTEGER`: 最大结果数 (默认: 50)

**示例：**

```bash
# 在标题和摘要中搜索
python main.py search-local --query "neural network"

# 只在标题中搜索
python main.py search-local --query "transformer" --fields "title"

# 限制结果数量
python main.py search-local --query "deep learning" --limit 20
```

### categories - 查看分类

显示可用的 ArXiv 分类。

```bash
python main.py categories
```

### cleanup - 清理数据

清理数据库和下载文件。

```bash
python main.py cleanup [OPTIONS]
```

**选项：**
- `--backup`: 清理前创建备份

**示例：**

```bash
# 清理并备份
python main.py cleanup --backup
```

## 配置文件详解

配置文件 `config.yaml` 包含所有系统设置：

### API 配置

```yaml
api:
  base_url: "http://export.arxiv.org/api/query"  # ArXiv API 地址
  max_results_per_query: 100                     # 单次查询最大结果数
  request_delay: 3.0                             # 请求间隔（秒）
  user_agent: "ArxivCrawler/1.0"                 # 用户代理
  timeout: 30                                    # 请求超时（秒）
```

### 下载配置

```yaml
download:
  output_directory: "./downloaded_papers"        # 下载目录
  max_concurrent_downloads: 5                    # 最大并发下载数
  retry_attempts: 3                              # 重试次数
  timeout: 60                                    # 下载超时（秒）
  filename_pattern: "{year}_{first_author}_{title}"  # 文件名模式
  create_category_folders: true                  # 是否创建分类文件夹
```

### 存储配置

```yaml
storage:
  database_path: "./arxiv_papers.db"             # 数据库路径
  export_formats: ["json", "csv"]                # 支持的导出格式
  auto_backup: true                              # 自动备份
```

### 日志配置

```yaml
logging:
  level: "INFO"                                  # 日志级别
  log_file: "arxiv_crawler.log"                 # 日志文件
  max_file_size: "10MB"                          # 最大文件大小
  backup_count: 3                                # 备份文件数量
```

## 高级用法

### 1. 环境变量覆盖

可以使用环境变量覆盖配置文件设置：

```bash
export ARXIV_DOWNLOAD_DIR="/path/to/papers"
export ARXIV_DOWNLOAD_THREADS=10
export ARXIV_LOG_LEVEL=DEBUG

python main.py search --query "quantum computing"
```

### 2. 批处理脚本

Linux/macOS:
```bash
./run.sh
```

Windows:
```cmd
run.bat
```

### 3. 交互式模式

```bash
python main.py --interactive
```

### 4. 高级查询语法

```bash
# 布尔查询
python main.py search --query "machine learning AND neural networks"

# 排除关键词
python main.py search --query "deep learning NOT computer vision"

# 多字段组合
python main.py search --title "transformer" --abstract "attention mechanism"
```

### 5. 自定义文件命名

配置文件中的 `filename_pattern` 支持以下变量：
- `{year}`: 发表年份
- `{first_author}`: 第一作者
- `{title}`: 论文标题
- `{arxiv_id}`: ArXiv ID

示例模式：
- `"{arxiv_id}_{title}"`: "2301.12345_Attention_Is_All_You_Need"
- `"{year}/{category}/{first_author}_{title}"`: "2023/cs.AI/Vaswani_Attention_Is_All_You_Need"

## 故障排除

### 1. 常见错误

**网络连接问题：**
```
解决方案：
- 检查网络连接
- 检查防火墙设置
- 增加超时时间
- 使用代理（设置 HTTP_PROXY 环境变量）
```

**API 限流：**
```
错误：HTTP 503 Service Unavailable
解决方案：
- 检查 request_delay 设置（应 >= 3 秒）
- 减少并发请求
- 稍后重试
```

**磁盘空间不足：**
```
解决方案：
- 清理下载目录
- 更改 output_directory 到有足够空间的位置
- 使用 cleanup 命令清理无效文件
```

### 2. 调试模式

启用详细日志：

```bash
export ARXIV_LOG_LEVEL=DEBUG
python main.py search --query "test"
```

### 3. 重置配置

删除配置文件以重置为默认设置：

```bash
rm config.yaml
python main.py  # 将创建新的默认配置
```

## API 使用

可以在 Python 程序中直接使用爬虫组件：

```python
from arxiv_api import ArxivAPI
from data_processor import DataProcessor  
from downloader import DownloadManager
from config import ConfigManager

# 加载配置
config_manager = ConfigManager()
config = config_manager.get_all()

# 初始化组件
api = ArxivAPI(config['api'])
processor = DataProcessor(config['storage'])
downloader = DownloadManager(config['download'])

# 搜索论文
results = api.search(query="machine learning", max_results=10)
papers = results['papers']

# 保存到数据库
processor.add_papers(papers)

# 下载 PDF
download_results = downloader.download_papers(papers)

# 获取统计信息
stats = processor.get_statistics()
print(f"总计论文数: {stats['total_papers']}")
```

更多示例请参考各模块的文档字符串和 `examples/` 目录。