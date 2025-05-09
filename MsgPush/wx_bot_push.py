# -*- coding: utf-8 -*-
import json
import logging

from .exceptions import SendError, WxComError
from datetime import datetime, timedelta
import requests


class WxComBot(object):
    """
    企业微信消息通知机器人（利用应用）
    目前支持消息类型：
        1. 文本
    """
    # 企业 id
    corp_id: str
    # 应用的凭证密钥
    corp_secret: str
    # 企业微信应用 access_token
    token: str
    # access_token 过期时间，默认为 2 小时过期
    expires_at: datetime

    def __init__(self, corp_id: str, corp_secret: str):
        self.corp_id = corp_id
        self.corp_secret = corp_secret
        self.expires_at = datetime.now()
        logging.basicConfig(format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
                            level=logging.INFO, datefmt='%Y-%m-%d %H:%M:%S')
        self.logger = logging.getLogger(__name__)

    def get_token(self, **kwargs):
        self.logger.info('开始获取 token')
        now = datetime.now()
        url = f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={self.corp_id}&corpsecret={self.corp_secret}'
        r = requests.get(url, **kwargs)
        data = json.loads(r.text)
        if data['errcode'] != 0:
            self.logger.error('获取 token 失败！请检查！')
        self.expires_at = now + timedelta(seconds=data['expires_in'])
        self.token = data['access_token']
        self.logger.info('获取 token 成功')
        return self.token

    def _send_msg(self, form_data: dict, **kwargs):
        if not form_data.get('touser') and not form_data.get('toparty') and not form_data.get('totag'):
            raise ValueError('[to_user,to_party,to_tag] 不能同时为空')
        if len(form_data.get('content', '').encode()) > 2048:
            self.logger.warning(f'消息长度超出 2048 字节 ，消息将被企业微信截断')
        now = datetime.now()
        if now >= self.expires_at:
            self.get_token()

        url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={self.token}&debug=1'
        try:
            r = requests.post(url, data=json.dumps(form_data), **kwargs)
        except Exception as e:
            raise SendError(f'发送 post 请求失败，详情如下：\n{e}')
        response = json.loads(r.content.decode('utf-8'))
        if response.get('errcode') != 0:
            raise WxComError(
                f'{response}\n请查阅企业微信错误码 [ https://work.weixin.qq.com/api/doc/90000/90139/90313 ]')

        return response

    def send_msg_text(self, agent_id: int, content: str, to_user: str = None, to_party: str = None, safe: int = 0,
                      to_tag: str = None, enable_id_trans: int = 0, enable_duplicate_check: int = 0,
                      duplicate_check_interval: int = 1800, **kwargs):
        """
        发送文本类型消息
        :param agent_id: 企业应用的id，整型。企业内部开发，可在应用的设置页面查看
        :param content: 消息内容，最长不超过2048个字节，超过将截断（支持id转译）
                        content 参数支持换行（\n）、以及 a 标签（打开自定义的网页）
        :param to_user: 指定接收消息的成员，成员ID列表（多个接收者用 | 分隔，最多支持1000个）。
                        特殊情况：指定为 @all ，则向该企业应用的全部成员发送
        :param to_party: 指定接收消息的部门，部门ID列表，多个接收者用 | 分隔，最多支持100个。
                         当 to_user 为 @all 时忽略本参数
        :param to_tag: 指定接收消息的标签，标签ID列表，多个接收者用 | 分隔，最多支持100个。
                       当 to_user 为 @all 时忽略本参数
        :param safe: 表示是否是保密消息，0表示可对外分享，1表示不能分享且内容显示水印，默认为0
        :param enable_id_trans: 表示是否开启id转译，0表示否，1表示是，默认0。仅第三方应用需要用到，企业自建应用可以忽略。
        :param enable_duplicate_check: 表示是否开启重复消息检查，0表示否，1表示是，默认0
        :param duplicate_check_interval: 表示是否重复消息检查的时间间隔，默认1800s，最大不超过4小时
        :param kwargs: requests 相关参数，如超时时间
        :return:
        """
        form_data = {
            "touser": to_user,
            "toparty": to_party,
            "totag": to_tag,
            "msgtype": 'text',
            "agentid": agent_id,
            "text": {
                "content": content
            },
            "safe": safe,
            "enable_id_trans": enable_id_trans,
            "enable_duplicate_check": enable_duplicate_check,
            "duplicate_check_interval": duplicate_check_interval
        }
        return self._send_msg(form_data=form_data, **kwargs)

    def send_msg_md(self, agent_id: int, content: str, to_user: str = None, to_party: str = None, safe: int = 0,
                    to_tag: str = None, enable_id_trans: int = 0, enable_duplicate_check: int = 0,
                    duplicate_check_interval: int = 1800, **kwargs):
        """
        发送 markdown 类型消息
        :param agent_id: 企业应用的id，整型。企业内部开发，可在应用的设置页面查看
        :param content: 消息内容，最长不超过2048个字节，超过将截断（支持id转译）
                        content 参数支持换行（\n）、以及 a 标签（打开自定义的网页）
        :param to_user: 指定接收消息的成员，成员ID列表（多个接收者用 | 分隔，最多支持1000个）。
                        特殊情况：指定为 @all ，则向该企业应用的全部成员发送
        :param to_party: 指定接收消息的部门，部门ID列表，多个接收者用 | 分隔，最多支持100个。
                         当 to_user 为 @all 时忽略本参数
        :param to_tag: 指定接收消息的标签，标签ID列表，多个接收者用 | 分隔，最多支持100个。
                       当 to_user 为 @all 时忽略本参数
        :param safe: 表示是否是保密消息，0表示可对外分享，1表示不能分享且内容显示水印，默认为0
        :param enable_id_trans: 表示是否开启id转译，0表示否，1表示是，默认0。仅第三方应用需要用到，企业自建应用可以忽略。
        :param enable_duplicate_check: 表示是否开启重复消息检查，0表示否，1表示是，默认0
        :param duplicate_check_interval: 表示是否重复消息检查的时间间隔，默认1800s，最大不超过4小时
        :param kwargs: requests 相关参数，如超时时间
        :return:
        """
        form_data = {
            "touser": to_user,
            "toparty": to_party,
            "totag": to_tag,
            "msgtype": 'markdown',
            "agentid": agent_id,
            "markdown": {
                "content": content
            },
            "safe": safe,
            "enable_id_trans": enable_id_trans,
            "enable_duplicate_check": enable_duplicate_check,
            "duplicate_check_interval": duplicate_check_interval
        }
        return self._send_msg(form_data=form_data, **kwargs)

    def send_msg_card(self, agentid: int, title: str, description: str, url: str = None, ouser: str = None,
                      toparty: str = None, totag: str = None, enable_id_trans: int = 0, enable_duplicate_check: int = 0,
                      duplicate_check_interval: int = 1800, btntxt: str = "详情", **kwargs):
        """
        发送卡片消息
        :param agentid: 企业应用的id，整型。企业内部开发，可在应用的设置页面查看；第三方服务商，可通过接口 获取企业授权信息 获取该参数值
        :param title: 标题，不超过128个字符，超过会自动截断（支持id转译）
        :param description: 描述，不超过512个字符，超过会自动截断（支持id转译）
        :param url: 点击后跳转的链接。最长2048字节，请确保包含了协议头(http/https)
        :param ouser: 成员ID列表（消息接收者，多个接收者用‘|’分隔，最多支持1000个）。特殊情况：指定为@all，则向关注该企业应用的全部成员发送
        :param toparty: 部门ID列表，多个接收者用‘|’分隔，最多支持100个。当touser为@all时忽略本参数
        :param totag: 标签ID列表，多个接收者用‘|’分隔，最多支持100个。当touser为@all时忽略本参数
        :param enable_id_trans: 表示是否开启id转译，0表示否，1表示是，默认0
        :param enable_duplicate_check: 表示是否开启重复消息检查，0表示否，1表示是，默认0
        :param duplicate_check_interval: 表示是否重复消息检查的时间间隔，默认1800s，最大不超过4小时
        :param btntxt: 按钮文字。 默认为“详情”， 不超过4个文字，超过自动截断。
        :param kwargs: requests 相关参数，如超时时间
        :return:
        """
        form_data = {
            "touser": ouser,
            "toparty": toparty,
            "totag": totag,
            "msgtype": 'textcard',
            "agentid": agentid,
            "textcard": {
                "title": title,
                "description": description,
                "url": url,
                "btntxt": btntxt
            },
            "enable_id_trans": enable_id_trans,
            "enable_duplicate_check": enable_duplicate_check,
            "duplicate_check_interval": duplicate_check_interval
        }
        return self._send_msg(form_data=form_data, **kwargs)

    def send_mpnews_msg(self, agentid: int, articles: list, ouser: str = None, toparty: str = None, totag: str = None,
                        safe: int = 0, enable_id_trans: int = 0, enable_duplicate_check: int = 0,
                        duplicate_check_interval: int = 1800, **kwargs):
        """
        发送图文消息
        :param agentid: 企业应用的id，整型。企业内部开发，可在应用的设置页面查看；第三方服务商，可通过接口 获取企业授权信息 获取该参数值
        :param articles: 图文消息列表，每个元素为一个字典，包含以下字段：
            - title: 标题，不超过128个字节，超过会自动截断（支持id转译）
            - thumb_media_id: 图文消息缩略图的media_id, 可以通过素材管理接口获得
            - author: 图文消息的作者，不超过64个字节（可选）
            - content_source_url: 图文消息点击“阅读原文”之后的页面链接（可选）
            - content: 图文消息的内容，支持html标签，不超过666 K个字节（支持id转译）
            - digest: 图文消息的描述，不超过512个字节，超过会自动截断（支持id转译）（可选）
        :param ouser: 成员ID列表（消息接收者，多个接收者用‘|’分隔，最多支持1000个）。特殊情况：指定为@all，则向关注该企业应用的全部成员发送
        :param toparty: 部门ID列表，多个接收者用‘|’分隔，最多支持100个。当touser为@all时忽略本参数
        :param totag: 标签ID列表，多个接收者用‘|’分隔，最多支持100个。当touser为@all时忽略本参数
        :param safe: 表示是否是保密消息，0表示可对外分享，1表示不能分享且内容显示水印，2表示仅限在企业内分享，默认为0
        :param enable_id_trans: 表示是否开启id转译，0表示否，1表示是，默认0
        :param enable_duplicate_check: 表示是否开启重复消息检查，0表示否，1表示是，默认0
        :param duplicate_check_interval: 表示是否重复消息检查的时间间隔，默认1800s，最大不超过4小时
        :param kwargs: requests 相关参数，如超时时间
        :return:
        """
        form_data = {
            "touser": ouser,
            "toparty": toparty,
            "totag": totag,
            "msgtype": 'mpnews',
            "agentid": agentid,
            "mpnews": {
                "articles": articles
            },
            "safe": safe,
            "enable_id_trans": enable_id_trans,
            "enable_duplicate_check": enable_duplicate_check,
            "duplicate_check_interval": duplicate_check_interval
        }
        return self._send_msg(form_data=form_data, **kwargs)
