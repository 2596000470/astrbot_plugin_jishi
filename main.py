from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import httpx
import re
import json
import urllib.parse

# ==================== 配置项 ====================
DISCUZ_API_URL = "http://172.18.0.1/api_qqbot.php"
# 发帖页面链接（固定）
POST_URL = "https://www.sss526.top/forum.php?mod=misc&action=nav&mobile=2"
# ================================================

def get_qrcode_url(link):
    """将链接转为在线二维码图片地址"""
    enc = urllib.parse.quote(link)
    return f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={enc}"

@register("astrbot_plugin_jishi", "闻翊羲", "校园论坛机器人", "v0.0.8")
class DiscuzQQ(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.client = None

    async def initialize(self):
        self.client = httpx.AsyncClient(timeout=10)
        logger.info("[论坛插件] 初始化完成（含发帖指令）")

    async def call_api(self, action: str, tid: int = None) -> dict:
        """调用论坛API，返回解析后的JSON数据"""
        params = {"action": action}
        if tid:
            params["tid"] = tid
        
        default_error = {"code": -1, "msg": "API访问失败"}
        
        try:
            response = await self.client.get(DISCUZ_API_URL, params=params)
            if response.status_code != 200:
                logger.error(f"API状态码错误：{response.status_code}")
                return {"code": response.status_code, "msg": f"HTTP错误：{response.status_code}"}
            
            raw_text = response.text.strip()
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if not json_match:
                logger.error(f"API返回无有效JSON：{raw_text}")
                return {"code": -2, "msg": "API返回格式错误"}
            
            clean_json = json_match.group()
            data = json.loads(clean_json)
            return data
            
        except Exception as e:
            logger.error(f"API请求异常：{str(e)}")
            return default_error

    @filter.command("论坛帮助", aliases=["!论坛帮助", "！论坛帮助"])
    async def help(self, e: AstrMessageEvent):
        """展示所有指令菜单"""
        api_data = await self.call_api("menu")
        if api_data.get("code") != 0 or "data" not in api_data:
            yield e.plain_result(f"❌ {api_data.get('msg', '获取菜单失败')}")
            return
        
        # 补充新增的发帖指令到菜单
        txt = "📋 论坛机器人指令菜单\n"
        for k, v in api_data["data"].items():
            txt += f"{k}：{v}\n"
        txt += "!我要发帖：获取发帖入口（需先注册）\n"
        
        yield e.plain_result(txt.strip())

    @filter.command("最新帖子", aliases=["!最新帖子"])
    async def latest(self, e: AstrMessageEvent):
        """查询最新帖子"""
        api_data = await self.call_api("latest")
        if api_data.get("code") != 0 or "data" not in api_data:
            yield e.plain_result(f"❌ {api_data.get('msg', '获取失败')}")
            return
        
        posts = api_data["data"]
        if not posts:
            yield e.plain_result("📭 暂无帖子")
            return

        txt = "🔍 论坛最新帖子\n"
        for i, item in enumerate(posts[:5], 1):
            txt += f"{i}. {item['title']}\n   作者：{item['author']}｜浏览：{item['views']}\n"
        
        yield e.plain_result(txt.strip())

    @filter.command("热门帖子", aliases=["!热门帖子"])
    async def hot(self, e: AstrMessageEvent):
        """查询热门帖子"""
        api_data = await self.call_api("hot")
        if api_data.get("code") != 0 or "data" not in api_data:
            yield e.plain_result(f"❌ {api_data.get('msg', '获取失败')}")
            return
        
        posts = api_data["data"]
        if not posts:
            yield e.plain_result("📭 暂无帖子")
            return

        txt = "🔥 论坛热门帖子\n"
        for i, item in enumerate(posts[:5], 1):
            txt += f"{i}. {item['title']}\n   作者：{item['author']}｜浏览：{item['views']}\n"
        
        yield e.plain_result(txt.strip())

    @filter.command("帖子详情", aliases=["!帖子详情"])
    async def detail(self, e: AstrMessageEvent):
        """查询帖子详情（文字+二维码）"""
        parts = e.message_str.strip().split()
        if len(parts) != 2 or not parts[1].isdigit():
            yield e.plain_result("❌ 格式：!帖子详情 帖子ID\n例：!帖子详情 1")
            return
        
        tid = int(parts[1])
        api_data = await self.call_api("detail", tid)
        if api_data.get("code") != 0 or "data" not in api_data:
            yield e.plain_result(f"❌ {api_data.get('msg', '获取失败')}")
            return
        
        dt = api_data["data"]
        txt = (
            f"📄 帖子详情（ID：{dt['tid']}）\n"
            f"标题：{dt['title']}\n"
            f"作者：{dt['author']}\n"
            f"浏览：{dt['views']}｜回复：{dt['replies']}\n"
            f"内容：{dt['content']}\n\n"
            f"📱 扫码打开帖子"
        )
        qr = get_qrcode_url(dt['url'])
        
        yield e.plain_result(txt)
        yield e.image_result(qr)

    @filter.command("我要发帖", aliases=["!我要发帖", "！我要发帖"])
    async def post(self, e: AstrMessageEvent):
        """新增：我要发帖指令"""
        # 构造提示文本
        txt = (
            "✍️ 论坛发帖入口\n"
            "⚠️ 提示：发帖前需先注册论坛账号哦！\n\n"
            "📱 扫码进入发帖页面"
        )
        # 生成发帖链接的二维码
        qr = get_qrcode_url(POST_URL)
        
        # 发送文字提示 + 二维码图片
        yield e.plain_result(txt)
        yield e.image_result(qr)

    async def terminate(self):
        """关闭HTTP客户端"""
        if self.client:
            await self.client.aclose()
            logger.info("[论坛插件] 已关闭HTTP客户端")