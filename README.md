# cs-monitor

Analysis of csgo News monitoring

1、思路
腾讯云api服务：每5分钟扫一次https://store.steampowered.com/feeds/news/app/730/?cc=HK&l=schinese rss订阅，获取最新新闻;
如何判定最新新闻？日期是否是当天；或者把文章标题存入文件内，做字典映射
2、如果是新新闻，调用ai接口分析饰品数据，再返回推给手机系统；
3、主要的是确定信息的准确性，时效性，对外提供消息推送接口，收费即可;