# ArXiv Academic Paper Crawler

一个功能完善的 ArXiv 学术论文爬虫系统，支持论文搜索、下载、管理和数据分析。

## 功能特性

### 🔍 强大的搜索功能
- 支持关键词、作者、标题、摘要搜索
- 按学科分类搜索（如 cs.AI, physics.gen-ph 等）
- 时间范围筛选
- 高级查询语法支持（AND, OR, NOT）
- 分页查询，支持大量结果处理

### 📥 智能下载管理
- 多线程并发下载，可配置线程数
- 断点续传支持
- 进度条显示（整体和单文件进度）
- 失败自动重试机制
- 交互式选择下载
- 智能文件命名和分类存储

### 💾 数据存储与管理
- SQLite 数据库存储论文元数据
- JSON/CSV 格式导出
- 数据去重机制
- 增量更新功能
- 本地搜索支持
- 统计信息分析

### 🖥️ 用户界面
- 丰富的命令行界面（使用 Rich 库美化）
- 交互式菜单模式
- 详细的帮助信息
- 配置文件管理

## 安装要求

### 系统要求
- Python 3.7 或更高版本
- Windows 10+, macOS 10.14+, 或 Linux

### 依赖库
```bash
pip install -r requirements.txt
```

主要依赖：
- `requests` - HTTP 请求
- `feedparser` - ArXiv API 响应解析
- `pandas` - 数据处理
- `tqdm` - 进度条
- `rich` - 终端美化
- `click` - 命令行界面
- `pyyaml` - 配置文件处理

## 快速开始

### 1. 安装依赖
```bash
# 克隆或下载项目
# 安装依赖
pip install -r requirements.txt
```

### 2. 基本使用

#### 搜索论文
```bash
# 关键词搜索
python main.py search --query "machine learning" --max-results 10

# 作者搜索
python main.py search --author "Yann LeCun" --category "cs.AI"

# 分类搜索
python main.py search --category "cs.CV" --date-from "2023-01-01"

# 高级搜索
python main.py search --title "neural networks" --abstract "deep learning" --max-results 50
```

#### 下载论文
```bash
# 搜索并下载
python main.py download --query "deep learning" --max-results 20 --interactive

# 从 JSON 文件下载
python main.py download --input results.json --threads 8

# 指定输出目录
python main.py download --query "computer vision" --output-dir ./cv_papers
```

#### 数据库管理
```bash
# 查看统计信息
python main.py stats

# 搜索本地数据库
python main.py search-local --query "transformer" --fields "title,abstract"

# 更新数据库（获取最近 7 天的论文）
python main.py update --category "cs.AI" --days 7

# 数据库清理
python main.py cleanup --backup
```

#### 其他功能
```bash
# 查看可用分类
python main.py categories

# 交互式模式
python main.py --interactive

# 查看帮助
python main.py --help
python main.py COMMAND --help
```

## 配置文件

配置文件 `config.yaml` 包含所有可配置选项：

```yaml
api:
  base_url: "http://export.arxiv.org/api/query"
  max_results_per_query: 100
  request_delay: 3.0
  user_agent: "ArxivCrawler/1.0"
  timeout: 30

download:
  output_directory: "./downloaded_papers"
  max_concurrent_downloads: 5
  retry_attempts: 3
  timeout: 60
  filename_pattern: "{year}_{first_author}_{title}"
  create_category_folders: true

storage:
  database_path: "./arxiv_papers.db"
  export_formats: ["json", "csv"]
  auto_backup: true

logging:
  level: "INFO"
  log_file: "arxiv_crawler.log"
  max_file_size: "10MB"
  backup_count: 3
```

## 环境变量

可以使用环境变量覆盖配置文件设置：

```bash
export ARXIV_DOWNLOAD_DIR="/path/to/papers"
export ARXIV_DOWNLOAD_THREADS=10
export ARXIV_API_DELAY=5
export ARXIV_LOG_LEVEL=DEBUG
```

## 高级功能

### 文件命名模式
支持自定义文件命名，可用变量：
- `{year}` - 发表年份
- `{first_author}` - 第一作者
- `{title}` - 论文标题
- `{arxiv_id}` - ArXiv ID

### 数据导出
```bash
# 导出搜索结果
python main.py search --query "quantum computing" --export results.json
python main.py search --query "quantum computing" --export results.csv

# 导出统计信息
python main.py stats --export statistics.json
```

### 批量操作
```python
# 使用 Python API
from arxiv_api import ArxivAPI
from data_processor import DataProcessor
from downloader import DownloadManager

# 初始化
api = ArxivAPI(config)
processor = DataProcessor(config)
downloader = DownloadManager(config)

# 搜索
results = api.search(query="machine learning", max_results=100)

# 处理数据
processor.add_papers(results['papers'])

# 下载
download_results = downloader.download_papers(results['papers'])
```

## 常见问题

### Q: 下载失败怎么办？
A: 系统提供自动重试机制。你也可以使用 `--retry` 选项手动重试失败的下载。

### Q: 如何避免被 ArXiv 封禁？
A: 默认配置遵守 ArXiv API 使用规范（3秒请求间隔）。请勿修改 `request_delay` 为小于 3 秒的值。

### Q: 支持哪些论文分类？
A: 使用 `python main.py categories` 查看所有可用的 ArXiv 分类。

### Q: 如何处理网络代理？
A: 可以设置环境变量：
```bash
export HTTP_PROXY=http://proxy:8080
export HTTPS_PROXY=http://proxy:8080
```

### Q: 数据库文件在哪里？
A: 默认在当前目录的 `arxiv_papers.db`，可在配置文件中修改。

## 项目结构

```
paper_spider/
├── main.py              # 主程序入口
├── cli.py               # 命令行接口
├── arxiv_api.py         # ArXiv API 封装
├── data_processor.py    # 数据处理模块
├── downloader.py        # 下载管理器
├── config.py            # 配置管理
├── requirements.txt     # 依赖列表
├── config.yaml          # 配置文件
├── setup.py            # 安装脚本
└── README.md           # 说明文档
```

## 开发说明

### 运行测试
```bash
python -m pytest tests/
```

### 代码格式化
```bash
black *.py
flake8 *.py
```

### 构建分发包
```bash
python setup.py sdist bdist_wheel
```

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎贡献代码！请：

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 联系方式

- 项目主页：https://github.com/Nathanielneil/paper_spider
- 问题反馈：https://github.com/Nathanielneil/paper_spider/issues

## 更新日志

### v1.0.0 (2025-09-11)
- 初始版本发布
- 完整的搜索和下载功能
- 数据库存储和管理
- 丰富的命令行界面
- 跨平台支持（Windows/macOS/Linux）

---

**注意：本工具仅供学术研究使用，请遵守 ArXiv 的使用条款和版权声明。**
