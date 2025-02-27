import requests
import json
from xml.etree import ElementTree as ET
from MsgPush.wx_bot_push import WxComBot
from openai import OpenAI

# 本地测试使用代理
proxies = {
    'http': 'http://127.0.0.1:7897',
    'https': 'http://127.0.0.1:7897',
}

client = OpenAI(api_key='sk-b9b082a32d87491181a684b6bf68bc19', base_url='https://api.deepseek.com')
corp_id = 'ww85eb6097649bfa4d'
corp_secret = '_uQAPvqzla0FMlPx-QZS0jFFQ8AUWQ3J8H8o86ysSPQ'

# RSS订阅的URL
rss_url = "https://store.steampowered.com/feeds/news/app/730/?cc=HK&l=schinese"

# JSON文件的路径
json_file_path = "news.json"


# 获取RSS订阅内容
def fetch_rss_feed(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to fetch RSS feed. Status code: {response.status_code}")


# 解析RSS内容
def parse_rss_feed(xml_content):
    root = ET.fromstring(xml_content)
    news_items = []
    for item in root.findall(".//item"):
        news_item = {
            "title": item.find("title").text,
            "link": item.find("link").text,
            "pubDate": item.find("pubDate").text,
            "description": item.find("description").text
        }
        news_items.append(news_item)
    return news_items


# 加载已有的新闻数据
def load_existing_news(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            # 如果文件为空，返回空列表
            content = file.read()
            if not content.strip():
                return []
            return json.loads(content)
    except FileNotFoundError:
        # 如果文件不存在，返回空列表
        return []


# 保存新的新闻数据
def save_news_to_file(file_path, news_items):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(news_items, file, ensure_ascii=False, indent=4)


# 检查是否有新的新闻
def check_for_new_news(existing_news, new_news):
    existing_titles = {news["pubDate"] for news in existing_news}
    new_news_items = [news for news in new_news if news["pubDate"] not in existing_titles]
    return new_news_items


# ds分析
def ds_analysis(messages):
    import time
    response = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=messages,
        stream=True
    )
    reasoning_content = ""
    content = ""

    print("\nReasoning Process:")  # 打印推理过程标题
    print("-" * 20)  # 分隔线

    for chunk in response:
        if chunk.choices[0].delta.reasoning_content:
            reasoning_chunk = chunk.choices[0].delta.reasoning_content
            reasoning_content += reasoning_chunk
            print(reasoning_chunk, end="", flush=True)  # 打印推理过程，不换行，并立即刷新输出
            time.sleep(0.02)  # 可以添加一个小的延迟，模拟思考过程，并让输出更平缓 (可选)
        elif chunk.choices[0].delta.content:
            content_chunk = chunk.choices[0].delta.content
            content += content_chunk
            print(content_chunk, end="", flush=True)  # 打印内容，不换行，并立即刷新输出
            time.sleep(0.02)  # 同上 (可选)

    print("\n" + "-" * 20)  # 分隔线
    print("Final Answer:", content)  # 打印最终答案
    print("-" * 30 + "\n")  # 更长的分隔线，区分不同轮次
    return content


# 聚合消息推送
def msg_push(wx_push=False, spug=False, messages=None, news_url=None):
    """
    聚合消息推推送
    :param wx_push: 是否推送微信,默认否
    :param spug: 推送spug平台，默认否
    :param messages: 消息内容
    :param new_url: 新闻链接
    :return:
    """
    if spug:
        push_result = requests.get('https://push.spug.cc/send/AXprQGG2mJQ0?content=CS2已发布更新,请查看微信分析消息')
        # 判断push_result是否推送成功
        if push_result.status_code != 200:
            print('消息推送失败')
    if wx_push:
        wx_com_bot = WxComBot(corp_id, corp_secret)
        wx_com_bot.send_mpnews_msg(agentid='1000002', toparty=2, articles=[
            {
                "title": "CS2更新发布",
                "thumb_media_id": "3e0ablt19scvOxXxoOcR562tY1cRkKBSyOSIALoifd7eJ9JPOX_Wit_1Oxg-8cpBhulUzmP9mNx5zllYOUN6DfA",
                "author": "cs2bot",
                "content_source_url": news_url,
                "content": messages,
                "digest": ""
            }
        ]
                                   )


# 主函数
def main():
    # 获取RSS订阅内容
    xml_content = fetch_rss_feed(rss_url)

    # 解析RSS内容
    new_news = parse_rss_feed(xml_content)

    # 加载已有的新闻数据
    existing_news = load_existing_news(json_file_path)

    # 检查是否有新的新闻
    new_news_items = check_for_new_news(existing_news, new_news)

    if new_news_items:
        print("发现新的新闻:")
        for news in new_news_items:
            print(f"标题: {news['title']}")
            print(f"链接: {news['link']}")
            print(f"发布日期: {news['pubDate']}")
            print(f"描述: {news['description']}")
            print("-" * 40)

        # 发现新的新闻推送到spug
        msg_push(spug=True)

        # 推送新闻到deepseek做饰品数据市场分析
        messages = [{
            "role": "system",
            "content": f"你是一个精通CS2饰品市场经济的专家,根据用户提供的内容更新日志或者新闻内容,参考受更新影响饰品以往形势来给出受影响的饰品道具,简单明确;【给我答案是图文消息的内容，支持html标签,去除开头的html，需要简单美化页面，不超过666 K个字节（支持id转译）】"
                       f"返回的答案请给我格式化的文本格式,答案格式如标题:CSGO更新,日期:20xx/x/x,"
                       f"更新新闻链接:(我发给您的link放到这里就行)"
                       f"受本次影响的武器类型:"
                       f"您的分析内容:"
        },
            {
                "role": 'user',
                "content": f'{new_news_items}'
            }]
        analysis_answer = ds_analysis(messages)

        # 获取最终结果推送到微信机器人
        msg_push(wx_push=True, messages=analysis_answer, news_url=news['link'])

        # 将新的新闻添加到已有的新闻数据中
        existing_news.extend(new_news_items)

        # 保存更新后的新闻数据到JSON文件
        save_news_to_file(json_file_path, existing_news)


    else:
        print("没有发现新的新闻。")


if __name__ == "__main__":
    main()
