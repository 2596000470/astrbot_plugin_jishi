from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import httpx

@register("astrbot_plugin_discuz", "闻翊羲", "Discuz论坛机器人", "v1.0.0")
class DiscuzQQ(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.client = None

    async def initialize(self):
        self.client = httpx.AsyncClient(timeout=5)
        logger.info("[Discuz插件] 已启动")

    async def api(self, action, tid=None):
        url = "http://172.17.0.1/api_qqbot.php"
        params = {"action": action}
        if tid: params["tid"] = tid
        try:
            r = await self.client.get(url, params=params)
            return r.json()
        except:
            return {"code":-1}

    @filter.command("论坛帮助", aliases=["!论坛帮助"])
    async def help(self, e: AstrMessageEvent):
        d = await self.api("menu")
        txt = "📋 论坛指令\n"
        for k,v in d["data"].items(): txt += f"{k}：{v}\n"
        yield e.plain_result(txt.strip())

    @filter.command("最新帖子", aliases=["!最新帖子"])
    async def latest(self, e: AstrMessageEvent):
        d = await self.api("latest")
        txt = "🔍 最新帖子\n"
        for i,item in enumerate(d["data"][:10],1):
            txt += f"{i}.{item['title']}\n  浏览:{item['views']} {item['url']}\n\n"
        yield e.plain_result(txt.strip()[:1800])

    @filter.command("热门帖子", aliases=["!热门帖子"])
    async def hot(self, e: AstrMessageEvent):
        d = await self.api("hot")
        txt = "🔥 热门帖子\n"
        for i,item in enumerate(d["data"][:10],1):
            txt += f"{i}.{item['title']}\n  浏览:{item['views']} {item['url']}\n\n"
        yield e.plain_result(txt.strip()[:1800])

    @filter.command("帖子详情", aliases=["!帖子详情"])
    async def detail(self, e: AstrMessageEvent):
        parts = e.message_str.strip().split()
        if len(parts)!=2 or not parts[1].isdigit():
            yield e.plain_result("格式：!帖子详情 123")
            return
        d = await self.api("detail", parts[1])
        dt = d["data"]
        txt = f"📄 {dt['title']}\n作者：{dt['author']}\n内容：{dt['content']}\n{dt['url']}"
        yield e.plain_result(txt)

    async def terminate(self):
        await self.client.aclose()