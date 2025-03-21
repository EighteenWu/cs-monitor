import requests
import json
import logging
import os
import time
from datetime import datetime
from xml.etree import ElementTree as ET

from requests_toolbelt import MultipartEncoder

from MsgPush.wx_bot_push import WxComBot
from openai import OpenAI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("cs_monitor.log"), logging.StreamHandler()],
)
logger = logging.getLogger("cs-monitor")


# 加载配置
def load_config():
    config_path = "config.json"
    if not os.path.exists(config_path):
        # 默认配置
        default_config = {
            "proxy": {
                "enabled": False,
                "http": "http://127.0.0.1:7897",
                "https": "http://127.0.0.1:7897",
            },
            "openai": {
                "api_key": "",
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-reasoner",
            },
            "wx_push": {
                "corp_id": "",
                "corp_secret": "",
                "agent_id": "1000002",
                "to_party": "2",
            },
            "rss": {
                "url": "https://store.steampowered.com/feeds/news/app/730/?cc=HK&l=schinese",
                "check_interval": 300,  # 5分钟检查一次
            },
            "data": {"json_file_path": "news.json"},
            "spug": {"enabled": True, "url": ""},
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        logger.info(f"创建默认配置文件: {config_path}")
        return default_config

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info("配置加载成功")
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        raise


# 全局配置
CONFIG = load_config()

# 设置代理
proxies = None
if CONFIG["proxy"]["enabled"]:
    proxies = {
        "http": CONFIG["proxy"]["http"],
        "https": CONFIG["proxy"]["https"],
    }

# 初始化OpenAI客户端
try:
    client = OpenAI(
        api_key=CONFIG["openai"]["api_key"], base_url=CONFIG["openai"]["base_url"]
    )
    logger.info("OpenAI客户端初始化成功")
except Exception as e:
    logger.error(f"OpenAI客户端初始化失败: {e}")
    client = None


def get_wx_media_id(file_name, file_path, access_token, file_type):
    """

    :param file_name:
    :param file_path:
    :param access_token:
    :param file_type:
    :return: media_id
    """
    url = f'https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type={file_type}'
    try:
        m = MultipartEncoder(
            fields={file_name: ('file', open(file_path, 'rb'), 'image/jpeg')},
        )
        r = requests.post(url=url, data=m, headers={'Content-Type': m.content_type})
        return r.json()['media_id']
    except Exception as e:
        logger.error(f'获取media_id错误{e}')


# 获取RSS订阅内容
def fetch_rss_feed(url):
    try:
        logger.info(f"开始获取RSS: {url}")
        response = requests.get(url, proxies=proxies, timeout=30)
        response.raise_for_status()  # 如果状态码不是200，抛出异常
        logger.info("RSS获取成功")
        return response.content
    except requests.RequestException as e:
        logger.error(f"获取RSS失败: {e}")
        raise


# 解析RSS内容
def parse_rss_feed(xml_content):
    try:
        logger.info("开始解析RSS内容")
        root = ET.fromstring(xml_content)
        news_items = []
        for item in root.findall(".//item"):
            news_item = {
                "title": item.find("title").text,
                "link": item.find("link").text,
                "pubDate": item.find("pubDate").text,
                "description": item.find("description").text,
            }
            news_items.append(news_item)
        logger.info(f"解析RSS成功，获取到{len(news_items)}条新闻")
        return news_items
    except Exception as e:
        logger.error(f"解析RSS内容失败: {e}")
        raise


# 加载已有的新闻数据
def load_existing_news(file_path):
    try:
        logger.info(f"加载已有新闻数据: {file_path}")
        if not os.path.exists(file_path):
            logger.info(f"文件不存在，返回空列表: {file_path}")
            return []

        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            if not content.strip():
                logger.info("文件为空，返回空列表")
                return []
            data = json.loads(content)
            logger.info(f"加载了{len(data)}条已有新闻")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {e}")
        return []
    except Exception as e:
        logger.error(f"加载新闻数据失败: {e}")
        return []


# 保存新的新闻数据
def save_news_to_file(file_path, news_items):
    try:
        logger.info(f"保存新闻数据到: {file_path}")
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(news_items, file, ensure_ascii=False, indent=4)
        logger.info(f"保存了{len(news_items)}条新闻")
    except Exception as e:
        logger.error(f"保存新闻数据失败: {e}")
        raise


# 检查是否有新的新闻
def check_for_new_news(existing_news, new_news):
    existing_dates = {news["pubDate"] for news in existing_news}
    new_news_items = [
        news for news in new_news if news["pubDate"] not in existing_dates
    ]
    logger.info(f"检查到{len(new_news_items)}条新闻")
    return new_news_items


# ds分析
def ds_analysis(messages):
    if client is None:
        logger.error("OpenAI客户端未初始化，无法进行分析")
        return "分析服务暂时不可用，请稍后再试"

    try:
        logger.info("开始AI分析")
        response = client.chat.completions.create(
            model=CONFIG["openai"]["model"], messages=messages, stream=True
        )

        reasoning_content = ""
        content = ""

        logger.info("开始接收AI分析结果")
        for chunk in response:
            if chunk.choices[0].delta.reasoning_content:
                reasoning_chunk = chunk.choices[0].delta.reasoning_content
                reasoning_content += reasoning_chunk
            elif chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                content += content_chunk

        logger.info("AI分析完成")
        return content
    except Exception as e:
        logger.error(f"AI分析失败: {e}")
        return f"分析过程中出现错误: {str(e)}"


# 聚合消息推送
def msg_push(wx_push=False, spug=False, media_id=None, messages=None, news_url=None):
    """
    聚合消息推送
    :param wx_push: 是否推送微信,默认否
    :param spug: 推送spug平台，默认否
    :param messages: 消息内容
    :param news_url: 新闻链接
    :return: 是否推送成功
    """
    success = True

    if spug and CONFIG["spug"]["enabled"]:
        try:
            logger.info("开始推送到Spug")
            push_result = requests.get(
                f'{CONFIG["spug"]["url"]}?content=CS2已发布更新,请查看微信分析消息',
                timeout=10,
            )
            push_result.raise_for_status()
            logger.info("Spug推送成功")
        except Exception as e:
            logger.error(f"Spug推送失败: {e}")
            success = False

    if wx_push:
        try:
            logger.info("开始推送到企业微信")
            wx_com_bot = WxComBot(
                CONFIG["wx_push"]["corp_id"], CONFIG["wx_push"]["corp_secret"]
            )
            wx_com_bot.send_mpnews_msg(
                agentid=CONFIG["wx_push"]["agent_id"],
                toparty=CONFIG["wx_push"]["to_party"],
                articles=[
                    {
                        "title": "CS2更新发布",
                        "thumb_media_id": media_id,
                        "author": "cs2bot",
                        "content_source_url": news_url,
                        "content": messages,
                        "digest": "",
                    }
                ],
            )
            logger.info("企业微信推送成功")
        except Exception as e:
            logger.error(f"企业微信推送失败: {e}")
            success = False

    return success


# 主函数
def main():
    try:
        logger.info("开始执行主程序")

        # 获取RSS订阅内容
        xml_content = fetch_rss_feed(CONFIG["rss"]["url"])

        # 解析RSS内容
        new_news = parse_rss_feed(xml_content)

        # 加载已有的新闻数据
        existing_news = load_existing_news(CONFIG["data"]["json_file_path"])

        # 检查是否有新的新闻
        new_news_items = check_for_new_news(existing_news, new_news)

        if new_news_items:
            logger.info(f"发现{len(new_news_items)}条新闻")
            for news in new_news_items:
                logger.info(f"标题: {news['title']}")
                logger.info(f"链接: {news['link']}")
                logger.info(f"发布日期: {news['pubDate']}")

            # 发现新的新闻推送到spug
            # msg_push(spug=True)

            # 获取微信素材id
            access_token = WxComBot(
                CONFIG["wx_push"]["corp_id"], CONFIG["wx_push"]["corp_secret"]
            ).get_token()
            logger.info(f'微信token:{access_token}')
            media_id = get_wx_media_id(file_name='media.jpg', file_path='media.jpg', access_token=access_token,
                                       file_type='image')
            logger.info(f'media_id:{media_id}')

            # 推送新闻到deepseek做饰品数据市场分析
            messages = [
                {
                    "role": "system",
                    "content": f"你是一个精通CS2饰品市场经济的专家,根据用户提供的内容更新日志或者新闻内容,参考受更新影响饰品以往形势来给出受影响的饰品道具,简单明确;【给我答案是图文消息的内容，支持html标签,去除开头的html，需要简单美化页面，不超过666 K个字节（支持id转译）】"
                               f"返回的答案请给我格式化的文本格式,答案格式如标题:CSGO更新,日期:20xx/x/x,"
                               f"更新新闻链接:(我发给您的link放到这里就行)"
                               f"受本次影响的武器类型:"
                               f"您的分析内容:",
                },
                {"role": "user", "content": f"{new_news_items}"},
            ]
            analysis_answer = ds_analysis(messages)

            # 获取最终结果推送到微信机器人
            push_success = msg_push(
                wx_push=True,
                messages=analysis_answer,
                news_url=new_news_items[0]["link"],
                media_id=media_id
            )

            if push_success:
                # 将新的新闻添加到已有的新闻数据中
                existing_news.extend(new_news_items)

                # 保存更新后的新闻数据到JSON文件
                save_news_to_file(CONFIG["data"]["json_file_path"], existing_news)
                logger.info("新闻数据已更新")
            else:
                logger.warning("由于推送失败，新闻数据未更新")
        else:
            logger.info("没有发现新的新闻")

    except Exception as e:
        logger.error(f"主程序执行出错: {e}", exc_info=True)


# 定时执行任务
def run_scheduler():
    logger.info("启动定时任务")
    check_interval = CONFIG["rss"]["check_interval"]

    while True:
        try:
            main()
            logger.info(f"等待{check_interval}秒后再次检查")
            time.sleep(check_interval)
        except KeyboardInterrupt:
            logger.info("程序被用户中断")
            break
        except Exception as e:
            logger.error(f"定时任务出错: {e}", exc_info=True)
            logger.info(f"等待{check_interval}秒后重试")
            time.sleep(check_interval)


if __name__ == "__main__":
    try:
        # 如果需要定时执行，取消下面的注释
        # run_scheduler()

        # 单次执行
        main()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行出错: {e}", exc_info=True)
