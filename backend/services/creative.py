"""AI 文创生图 + 图片矢量化。

生图策略（离线优先）：
1. 银行端「模型管理 → AI 文创生图」配置了运行期提供方：
   - 通义万相（qwen）：阿里云 DashScope 文生图异步任务 + 轮询；
   - OpenAI 兼容（custom）：POST Base URL 的 /images/generations，支持 url / b64_json 返回。
2. 未配置运行期提供方时，回退环境变量 DASHSCOPE_API_KEY（同样走通义万相）；
3. 都没有（或调用失败）→ 返回可直接在浏览器打开的第三方文生图 URL（无需 Key，保证演示可用）。

调用失败时把中文可读原因回填到返回体的 degrade_reason 字段，前端可提示老板
「为什么用的是兜底图」，而不是静默降级。

合规：所有生成图片均需显式标识「AI生成」（《人工智能生成合成内容标识办法》要求）。
"""
import os
import urllib.parse
from datetime import datetime

from . import llm, store

# 生图服务地址模板（离线兜底，prompt 需 URL 编码）
TEXT_TO_IMAGE_URL = "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt={prompt}&image_size=square_hd"

# 固定风格提示词模板（与项目策划书一致）
STYLE_TEMPLATE = (
    "Q版新中式 × 文创徽章插画 × 贴纸风格原创Q版扁平矢量风，"
    "抽象几何风格的景物解构，纯白背景，圆润饱满的胶囊状建筑，"
    "粗细均匀的圆角单线轮廓，扁平糖果色块拼接，细腻的孔版印刷颗粒质感，"
    "带单线飞行轨迹的胶囊状云朵，树干呈细棍状，悬浮岛屿底座，"
    "徽章美学，丝网印刷风格插画，无3D阴影，无写实感，现代kawaii风格，"
    "主题：{theme}"
)

WATERMARK_TEXT = "AI生成"


def build_prompt(theme: str, homestay: dict = None) -> str:
    """拼接生图提示词：固定风格模板 + 民宿文化标签 + 用户主题。"""
    theme = (theme or "").strip()
    tags = []
    if homestay:
        tags = list(homestay.get("cultural_tags", []) or [])
    if tags:
        theme = f"{theme}（{'、'.join(tags[:3])}）" if theme else "、".join(tags[:3])
    if not theme:
        theme = "古都民宿文化"
    return STYLE_TEMPLATE.format(theme=theme)


def fallback_image_url(prompt: str) -> str:
    """离线兜底：拼装文生图 URL。"""
    return TEXT_TO_IMAGE_URL.format(prompt=urllib.parse.quote(prompt, safe=""))


async def _wanx_generate(prompt: str, count: int, url: str, model: str, api_key: str, size: str = "1024*1024") -> list:
    """调用通义万相文生图（异步任务 + 轮询）。失败时抛异常，由上层回退。"""
    import asyncio

    import httpx  # 可选依赖，缺失时抛 ImportError → 回退

    # 用户可能误填了图生图（image2image）接口地址，调用前自动纠正为文生图（text2image）
    if "image2image" in url and "text2image" not in url:
        url = url.replace("image2image/image-synthesis", "text2image/image-synthesis")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    payload = {
        "model": model or llm.WANX_MODEL,
        "input": {"prompt": prompt},
        "parameters": {"n": count, "size": size},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        task_id = ((resp.json().get("output") or {}).get("task_id"))
        if not task_id:
            raise RuntimeError("通义万相未返回 task_id")

        # 任务查询地址：由创建地址推导（.../services/aigc/text2image/image-synthesis → /api/v1/tasks/{id}）
        prefix = url.split("/api/v1/")[0] if "/api/v1/" in url else "https://dashscope.aliyuncs.com"
        task_url = f"{prefix}/api/v1/tasks/{task_id}"
        # 轮询任务结果，最多等待约 60 秒
        for _ in range(20):
            await asyncio.sleep(3)
            r = await client.get(task_url, headers={"Authorization": f"Bearer {api_key}"})
            data = r.json()
            status = (data.get("output") or {}).get("task_status")
            if status == "SUCCEEDED":
                results = (data.get("output") or {}).get("results") or []
                urls = [x.get("url") for x in results if x.get("url")]
                if urls:
                    return urls
                raise RuntimeError("通义万相任务成功但无图片")
            if status in ("FAILED", "CANCELED", "UNKNOWN"):
                # 透传任务失败的真实原因（如：图生图模型要求 input.image_url / source_lang / target_lang）
                msg = ((data.get("output") or {}).get("message")) or ""
                raise RuntimeError(
                    f"通义万相任务{status}：" + (msg[:300] if msg else "请检查模型是否支持文生图（text2image）")
                )
    raise RuntimeError("通义万相任务超时")


async def _openai_image_generate(prompt: str, count: int, url: str, model: str, api_key: str) -> list:
    """调用 OpenAI 兼容的 /images/generations 接口（支持 url 或 b64_json 返回）。"""
    import httpx

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "prompt": prompt, "n": count}
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json().get("data") or []
    urls = []
    for item in data:
        if item.get("url"):
            urls.append(item["url"])
        elif item.get("b64_json"):
            urls.append("data:image/png;base64," + item["b64_json"])
    if not urls:
        raise RuntimeError("生图接口未返回图片数据")
    return urls


async def _generate_with_config(prompt: str, count: int) -> tuple:
    """按运行期「AI 文创生图」配置生成图片。

    返回 (图片URL列表, provider, 降级原因或 None)。
    """
    url, model, api_key, prov = llm._resolve("image")

    if not url or not api_key:
        return [], "fallback_url", "未配置生图模型（模型管理 → AI 文创生图），已使用免费兜底图。"

    try:
        if prov == "qwen" or "dashscope" in (url or ""):
            return await _wanx_generate(prompt, count, url, model, api_key), "dashscope-wanx", None
        return await _openai_image_generate(prompt, count, url, model, api_key), "openai-images", None
    except Exception as exc:
        msg, status = llm._friendly_error(exc)
        reason = f"生图模型调用失败，已回退兜底图。原因：{msg}"
        try:
            llm._record_error("image", msg, status)
        except Exception:
            pass
        return [], "fallback_url", reason


async def generate_images(homestay_id: str, theme: str, count: int = 1) -> dict:
    """生成文创图片。返回图片 URL 列表与使用的提示词。"""
    h = store.get_homestay(homestay_id)
    prompt = build_prompt(theme, h)
    count = max(1, min(int(count or 1), 4))

    urls, provider_used, degrade_reason = await _generate_with_config(prompt, count)

    if not urls:
        base = fallback_image_url(prompt)
        # 同 prompt 生成多张时附加序号，避免前端缓存导致看起来重复
        urls = [base if i == 0 else f"{base}&seed={i}" for i in range(count)]

    return {
        "homestay_id": homestay_id,
        "theme": theme,
        "prompt_used": prompt,
        "image_urls": urls,
        "count": len(urls),
        "provider": provider_used,
        "degrade_reason": degrade_reason,
        "watermarked": True,
        "watermark_text": WATERMARK_TEXT,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "compliance_note": "依据《人工智能生成合成内容标识办法》，AI 生成图片已在右下角添加显式标识「AI生成」。",
    }


# ---------------------------------------------------------------- 生图样式库
# 每个样式包含「标题 + 隐藏提示词」：老板端只看到标题与样式封面，
# 点击后按该样式（提示词不对老板展示）生成图片。
IMAGE_STYLES = [
    {
        "key": "q_newchin",
        "title": "Q版新中式徽章",
        "prompt": "Q版新中式徽章插画，圆润胶囊状古建，扁平糖果色块，孔版印刷颗粒质感，纯白背景，徽章美学，主题：{theme}",
    },
    {
        "key": "peony",
        "title": "洛阳牡丹伴手礼",
        "prompt": "洛阳牡丹主题伴手礼插画，盛放牡丹与古典窗棂，粉金配色，烫金质感，扁平矢量，纯色背景，主题：{theme}",
    },
    {
        "key": "water_banquet",
        "title": "洛阳水席美食贴纸",
        "prompt": "洛阳水席美食贴纸插画，汤碗与二十四道菜小巧排布，暖橙色调，圆润描边，贴纸风格，主题：{theme}",
    },
    {
        "key": "longmen",
        "title": "龙门石窟佛龛剪影",
        "prompt": "龙门石窟佛龛剪影插画，石窟造像与山峦线条，砂岩暖褐色系，现代扁平解构，留白构图，主题：{theme}",
    },
    {
        "key": "opera",
        "title": "豫剧脸谱潮流徽章",
        "prompt": "豫剧脸谱潮流徽章插画，戏曲脸谱几何解构，红金蓝撞色，圆角单线轮廓，徽章美学，主题：{theme}",
    },
    {
        "key": "guodu_night",
        "title": "古都夜游灯会",
        "prompt": "古都夜游灯会插画，古城楼与灯笼，靛蓝夜色配暖金光晕，扁平渐变，光斑点点，主题：{theme}",
    },
]


def list_styles(homestay_id: str = None) -> list:
    """返回生图样式库（含封面图），用于老板端样式展示墙。"""
    h = store.get_homestay(homestay_id) if homestay_id else None
    out = []
    for s in IMAGE_STYLES:
        theme = "、".join((h.get("cultural_tags", []) or ["古都民宿"])[:2]) if h else "古都民宿"
        prompt = s["prompt"].format(theme=theme)
        out.append({
            "key": s["key"],
            "title": s["title"],
            "cover": fallback_image_url(prompt),
        })
    return out


def _style_prompt(style_key: str, homestay: dict) -> str:
    style = next((s for s in IMAGE_STYLES if s["key"] == style_key), None)
    tags = list((homestay or {}).get("cultural_tags", []) or [])
    theme = (homestay or {}).get("name") or "古都民宿"
    if tags:
        theme = f"{theme}（{'、'.join(tags[:2])}）"
    if style:
        return style["prompt"].format(theme=theme)
    return STYLE_TEMPLATE.format(theme=theme)


async def generate_by_style(homestay_id: str, style_key: str, count: int = 1, image_url: str = "") -> dict:
    """按样式生成文创图片（样式提示词由后端持有，不对老板展示）。"""
    h = store.get_homestay(homestay_id)
    prompt = _style_prompt(style_key, h)
    count = max(1, min(int(count or 1), 4))

    urls, provider_used, degrade_reason = await _generate_with_config(prompt, count)

    if not urls:
        base = fallback_image_url(prompt)
        urls = [base if i == 0 else f"{base}&seed={i}" for i in range(count)]

    style = next((s for s in IMAGE_STYLES if s["key"] == style_key), None)
    return {
        "homestay_id": homestay_id,
        "style_key": style_key,
        "style_title": (style or {}).get("title", "文创风格"),
        "source_image": image_url,
        "image_urls": urls,
        "count": len(urls),
        "provider": provider_used,
        "degrade_reason": degrade_reason,
        "watermarked": True,
        "watermark_text": WATERMARK_TEXT,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "compliance_note": "依据《人工智能生成合成内容标识办法》，AI 生成图片已添加显式标识「AI生成」。",
    }


# ---------------------------------------------------------------- 宣传文案生成
COPY_STYLES = [
    {"key": "xiaohongshu", "name": "小红书种草风", "desc": "口语化、带话题标签、突出氛围感"},
    {"key": "ota", "name": "OTA详情页风", "desc": "卖点清晰、适合携程/美团房源介绍"},
    {"key": "cultural", "name": "古都文化风", "desc": "典雅书面语、融入历史人文底蕴"},
    {"key": "promo", "name": "节日促销风", "desc": "强调优惠力度与行动号召"},
]

_COPY_FALLBACK = (
    "【{name} · 古都栖居】\n"
    "在{city}的烟火与古迹之间，{name}为你留一盏灯。\n"
    "📍 位置：{address}\n"
    "🌿 特色：{tags}\n"
    "🛏 入住体验：闹中取静，推窗即见古都风貌，客房洁净舒适，布草一客一换。\n"
    "💡 适合人群：亲子出游、文化旅行、周末微度假。\n"
    "✨ {requirement}\n"
    "预订请私信，我们为你与古都留一段温柔的记忆。\n"
    "#古都民宿 #{city}旅行 #民宿推荐 #{tag0}"
)


async def generate_copywriting(homestay_id: str, requirement: str = "", style: str = "xiaohongshu") -> dict:
    """根据民宿信息 + 老板要求生成宣传文案（未配置大模型时使用模板兜底）。"""
    h = store.get_homestay(homestay_id)
    if h is None:
        raise ValueError(f"民宿不存在：{homestay_id}")

    style_meta = next((s for s in COPY_STYLES if s["key"] == style), COPY_STYLES[0])
    tags = "、".join(h.get("cultural_tags", []) or ["古都文化"])
    mode = "offline"
    content = ""
    degrade_reason = None

    if llm.provider("copywriting") != "offline":
        try:
            system = (
                "你是民宿品牌文案策划师，服务于工行「豫宿巡」系统的民宿经营者。"
                f"请以「{style_meta['name']}」风格撰写一段 200~320 字的民宿宣传文案，"
                "要求真实、有画面感、突出本店特色，结尾附 3~5 个话题标签。"
                "不得编造不存在的设施或数据，直接输出文案正文。"
            )
            user = (
                f"民宿名称：{h.get('name')}\n城市：{h.get('city')}\n地址：{h.get('address')}\n"
                f"文化标签：{tags}\nOTA 评分：{h.get('ota_score')}\n"
                f"老板的具体要求：{requirement or '突出古都文化氛围，吸引文化旅行客群'}"
            )
            content = await llm.chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.7, scene="copywriting",
            )
            if content:
                mode = "llm"
        except llm.NoLLMConfigured:
            content = ""
            degrade_reason = "未配置「AI 宣传文案」模型，已使用离线模板文案。"
        except Exception as exc:
            content = ""
            detail = getattr(exc, "message", None) or str(exc)
            degrade_reason = f"大模型调用失败，已使用离线模板文案。原因：{detail}"

    if not content:
        content = _COPY_FALLBACK.format(
            name=h.get("name"), city=h.get("city"), address=h.get("address"),
            tags=tags, requirement=requirement or "限时预订可享古都伴手礼一份～",
            tag0=(h.get("cultural_tags") or ["古都文化"])[0],
        )
        mode = "offline"

    return {
        "homestay_id": h.get("id"),
        "homestay_name": h.get("name"),
        "style": style,
        "style_name": style_meta["name"],
        "requirement": requirement,
        "content": content,
        "mode": mode,
        "degrade_reason": degrade_reason,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------- 矢量化
def _placeholder_svg(text: str = "豫宿巡·AI文创") -> str:
    """生成一个内联示例 SVG（data-uri），用于矢量化不可用时兜底展示。"""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320">'
        '<rect width="320" height="320" rx="24" fill="#F7F8FA"/>'
        '<circle cx="160" cy="140" r="74" fill="#165DFF" opacity="0.12"/>'
        '<circle cx="160" cy="140" r="52" fill="none" stroke="#165DFF" stroke-width="3"/>'
        '<path d="M108 160 L160 118 L212 160" fill="none" stroke="#FFB800" stroke-width="4" stroke-linecap="round"/>'
        '<text x="160" y="238" text-anchor="middle" font-size="18" fill="#0A192F" font-family="sans-serif">'
        f'{text}</text>'
        '<text x="308" y="308" text-anchor="end" font-size="12" fill="#86909C" font-family="sans-serif">AI生成</text>'
        '</svg>'
    )
    return "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(svg, safe="")


def vectorize(image_url: str) -> dict:
    """图片矢量化：优先 vtracer，未安装则返回 placeholder + 内联示例 SVG（不报错）。"""
    if not image_url:
        raise ValueError("缺少 image_url 参数")

    try:
        import vtracer  # 可选依赖
    except Exception:
        return {
            "svg_url": _placeholder_svg(),
            "method": "placeholder",
            "source_image": image_url,
            "note": (
                "未安装 vtracer，已返回内联示例 SVG。"
                "安装方式：pip install vtracer，安装后将自动对图片执行真实矢量化并输出可下载的 SVG。"
            ),
        }

    try:
        import io
        import tempfile
        import urllib.request

        with urllib.request.urlopen(image_url, timeout=20) as resp:
            raw = resp.read()
        in_path = os.path.join(tempfile.gettempdir(), "yusuxun_in.png")
        out_path = os.path.join(tempfile.gettempdir(), "yusuxun_out.svg")
        with open(in_path, "wb") as f:
            f.write(raw)
        vtracer.convert_image_to_svg_py(in_path, out_path, colormode="color")
        with open(out_path, "r", encoding="utf-8") as f:
            svg_text = f.read()
        return {
            "svg_url": "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(svg_text, safe=""),
            "method": "vtracer",
            "source_image": image_url,
            "note": "已使用 vtracer 完成图片矢量化，输出为内联 SVG（data-uri）。",
        }
    except Exception as exc:
        return {
            "svg_url": _placeholder_svg(),
            "method": "placeholder",
            "source_image": image_url,
            "note": f"vtracer 处理失败（{exc.__class__.__name__}），已返回内联示例 SVG。",
        }
