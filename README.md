# CS-Monitor

CS2游戏更新监控与饰品市场分析工具

## 项目介绍

CS-Monitor是一个自动化工具，用于监控CS2游戏的更新动态，并提供相关的饰品市场分析。主要功能包括：

1. 定期检查CS2官方RSS订阅源，获取最新游戏更新信息
2. 使用AI分析更新内容对游戏饰品市场的潜在影响
3. 通过多种渠道（企业微信、Spug等）推送分析结果

## 功能特点

- **自动监控**: 定期检查CS2官方RSS订阅源，自动识别新的更新内容
- **AI分析**: 利用DeepSeek AI模型分析更新内容对饰品市场的影响
- **多渠道推送**: 支持企业微信和Spug等多种消息推送渠道
- **可配置**: 通过config.json文件灵活配置所有参数
- **日志记录**: 详细的日志记录，方便问题排查

## 安装与配置

### 环境要求

- Python 3.7+
- 依赖包：requests, openai

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/yourusername/cs-monitor.git
cd cs-monitor
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置config.json
```json
{
    "proxy": {
        "enabled": false,
        "http": "http://127.0.0.1:7897",
        "https": "http://127.0.0.1:7897"
    },
    "openai": {
        "api_key": "your-api-key",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-reasoner"
    },
    "wx_push": {
        "corp_id": "your-corp-id",
        "corp_secret": "your-corp-secret",
        "agent_id": "your-agent-id",
        "to_party": "your-to-party"
    },
    "rss": {
        "url": "https://store.steampowered.com/feeds/news/app/730/?cc=HK&l=schinese",
        "check_interval": 300
    },
    "data": {
        "json_file_path": "news.json"
    },
    "spug": {
        "enabled": true,
        "url": "your-spug-url"
    }
}
```

## 使用方法

### 单次运行

```bash
python main.py
```

### 定时任务模式

修改main.py中的`if __name__ == "__main__":`部分，取消`run_scheduler()`的注释：

```python
if __name__ == "__main__":
    try:
        # 定时执行
        run_scheduler()
        
        # 单次执行
        # main()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行出错: {e}", exc_info=True)
```

然后运行：

```bash
python main.py
```

## 配置说明

### proxy
- `enabled`: 是否启用代理
- `http`/`https`: 代理服务器地址

### openai
- `api_key`: DeepSeek API密钥
- `base_url`: DeepSeek API基础URL
- `model`: 使用的AI模型

### wx_push
- `corp_id`: 企业微信企业ID
- `corp_secret`: 企业微信应用密钥
- `agent_id`: 企业微信应用ID
- `to_party`: 接收消息的部门ID

### rss
- `url`: CS2 RSS订阅源URL
- `check_interval`: 检查间隔（秒）

### data
- `json_file_path`: 存储新闻数据的JSON文件路径

### spug
- `enabled`: 是否启用Spug推送
- `url`: Spug推送URL

## 贡献

欢迎提交问题和功能请求！如果您想贡献代码，请提交拉取请求。

## 许可证

本项目采用MIT许可证 - 详情请参阅LICENSE文件。