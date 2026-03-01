from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import httpx
import re
import json  # 新增：导入内置json模块

# ==================== 配置项 ====================
DISCUZ_API_URL = "http://172.18.0.2/api_qqbot.php"
# ================================================

@register("astrbot_plugin_jishi", "闻翊羲", "对接校园论坛", "v0.0.4")
class DiscuzQQ(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.client = None

    async def initialize(self):
        self.client = httpx.AsyncClient(timeout=10)
        logger.info("[论坛插件] 初始化完成")

    async def call_api(self, action: str, tid: int = None) -> dict:
        """调用API，清理多余文本后解析JSON"""
        params = {"action": action}
        if tid:
            params["tid"] = tid
        
        default_error = {"code": -1, "msg": "API访问失败"}
        
        try:
            response = await self.client.get(DISCUZ_API_URL, params=params)
            if response.status_code != 200:
                logger.error(f"API状态码错误：{response.status_code}")
                return {"code": response.status_code, "msg": f"HTTP错误：{response.status_code}"}
            
            # 核心修复：清理返回内容，只保留JSON部分
            raw_text = response.text.strip()
            # 用正则提取JSON（去掉前面的HTML/警告文本）
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if not json_match:
                logger.error(f"API返回无有效JSON：{raw_text}")
                return {"code": -2, "msg": "API返回格式错误，无有效JSON"}
            
            clean_json = json_match.group()
            logger.info(f"清理后JSON：{clean_json}")
            
            # 修复：用Python内置json解析
            try:
                data = json.loads(clean_json)
                return data
            except Exception as e:
                logger.error(f"JSON解析失败：{str(e)}，内容：{clean_json}")
                return default_error
                
        except httpx.ConnectError:
            logger.error(f"无法连接API：{DISCUZ_API_URL}")
            return {"code": -3, "msg": "无法连接到论坛API"}
        except Exception as e:
            logger.error(f"API请求异常：{str(e)}")
            return default_error

    @filter.command("论坛帮助", aliases=["!论坛帮助", "！论坛帮助"])
    async def help(self, e: AstrMessageEvent):
        """处理!论坛帮助指令"""
        api_data = await self.call_api("menu")
        logger.info(f"API返回数据：{api_data}")  # 日志打印返回数据，方便排查
        
        # 校验data字段
        if api_data.get("code") != 0 or "data" not in api_data:
            error_msg = api_data.get("msg", "获取菜单失败")
            yield e.plain_result(f"❌ {error_msg}")
            return
        
        # 拼接菜单
        txt = "📋 论坛机器人指令菜单\n"
        for k, v in api_data["data"].items():
            txt += f"{k}：{v}\n"
        yield e.plain_result(txt.strip())

    @filter.command("最新帖子", aliases=["!最新帖子"])
    async def latest(self, e: AstrMessageEvent):
        """处理!最新帖子指令"""
        api_data = await self.call_api("latest")
        
        if api_data.get("code") != 0 or "data" not in api_data:
            error_msg = api_data.get("msg", "获取最新帖子失败")
            yield e.plain_result(f"❌ {error_msg}")
            return
        
        posts = api_data["data"]
        if not posts:
            yield e.plain_result("📭 论坛暂无公开帖子")
            return
        
        txt = "🔍 论坛最新帖子\n"
        for i, item in enumerate(posts[:10], 1):
            txt += f"{i}. {item['title']}\n  作者：{item['author']} | 浏览：{item['views']}\n  {item['url']}\n\n"
        yield e.plain_result(txt.strip()[:1800])

    @filter.command("热门帖子", aliases=["!热门帖子"])
    async def hot(self, e: AstrMessageEvent):
        """处理!热门帖子指令"""
        api_data = await self.call_api("hot")
        
        if api_data.get("code") != 0 or "data" not in api_data:
            error_msg = api_data.get("msg", "获取热门帖子失败")
            yield e.plain_result(f"❌ {error_msg}")
            return
        
        posts = api_data["data"]
        if not posts:
            yield e.plain_result("📭 论坛暂无公开帖子")
            return
        
        txt = "🔥 论坛热门帖子\n"
        for i, item in enumerate(posts[:10], 1):
            txt += f"{i}. {item['title']}\n  作者：{item['author']} | 浏览：{item['views']}\n  {item['url']}\n\n"
        yield e.plain_result(txt.strip()[:1800])

    @filter.command("帖子详情", aliases=["!帖子详情"])
    async def detail(self, e: AstrMessageEvent):
        """处理!帖子详情指令"""
        parts = e.message_str.strip().split()
        if len(parts) != 2 or not parts[1].isdigit():
            yield e.plain_result("❌ 指令格式错误！\n正确格式：!帖子详情 帖子ID（数字）\n例：!帖子详情 123")
            return
        
        tid = int(parts[1])
        api_data = await self.call_api("detail", tid)
        
        if api_data.get("code") != 0 or "data" not in api_data:
            error_msg = api_data.get("msg", f"获取ID为{tid}的帖子失败")
            yield e.plain_result(f"❌ {error_msg}")
            return
        
        dt = api_data["data"]
        txt = (
            f"📄 帖子详情（ID：{dt['tid']}）\n"
            f"标题：{dt['title']}\n"
            f"作者：{dt['author']}\n"
            f"浏览：{dt['views']} | 回复：{dt['replies']}\n"
            f"内容：{dt['content']}\n"
            f"链接：{dt['url']}"
        )
        yield e.plain_result(txt)

    async def terminate(self):
        if self.client:
            await self.client.aclose()
            logger.info("[论坛插件] 已关闭HTTP客户端")