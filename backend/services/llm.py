"""大模型接入（OpenAI 兼容接口）+ 多场景模型管理。

配置优先级（每个 AI 场景可单独配置）：
1. 运行期配置（银行端「模型管理」保存到 runtime.json 的 model_config.scenes[scene]）
2. 环境变量 DASHSCOPE_API_KEY → 阿里云通义千问（compatible-mode），模型 qwen3.8-max
3. 环境变量 DEEPSEEK_API_KEY  → DeepSeek，模型 deepseek-flash
4. 都没有                    → 抛出 NoLLMConfigured，由上层降级为离线模板/知识库答复

「AI 文创生图（image）」场景单独走文生图接口：
- qwen   → 阿里云通义万相（异步任务 + 轮询）
- custom → OpenAI 兼容 /images/generations 接口
- offline→ 第三方免费文生图链接兜底

HTTP 客户端优先使用 httpx（异步），未安装时回退到标准库 urllib（在线程池中执行）。
调用失败时会翻译为用户可读的中文原因并记录到 _last_error，供「模型管理」页面展示，
避免出现「配置看起来生效、实际静默降级」的错觉。
"""
import asyncio
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from . import store

# ------------------------------------------------------------------ 常量
# 阿里云百炼（Model Studio / DashScope）：官方 OpenAI 兼容地址
# https://docs.bailian.console.aliyun.com/zh/model-studio/get-api-key
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DASHSCOPE_MODELS_URLS = [
    # 官方模型列表接口（原生），支持按能力筛选；不同地域 Endpoint 不同，逐个尝试
    "https://dashscope.aliyuncs.com/api/v1/models",
    "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
]
DASHSCOPE_MODEL = "qwen3.8-max"

# DeepSeek：官方文档 base_url 为 https://api.deepseek.com，
# 对话补全地址为 https://api.deepseek.com/chat/completions（不带 /v1）
# https://api-docs.deepseek.com/zh-cn/
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODELS_URLS = ["https://api.deepseek.com/models"]
DEEPSEEK_MODEL = "deepseek-flash"

# 通义万相文生图（异步任务接口）
WANX_CREATE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
WANX_MODEL = "wanx2.1-t2i-turbo"

# AI 场景定义（模型管理页面按场景配置）
SCENES = [
    {"key": "chat", "name": "AI 经营助手对话", "desc": "老板端 RAG 问答、经营建议", "type": "text"},
    {"key": "report", "name": "AI 巡检报告", "desc": "贷后风险巡检报告撰写", "type": "text"},
    {"key": "warning", "name": "AI 预警生成", "desc": "依据评分/评论/对话自动生成预警", "type": "text"},
    {"key": "copywriting", "name": "AI 宣传文案", "desc": "根据民宿信息生成推广文案", "type": "text"},
    {"key": "image", "name": "AI 文创生图", "desc": "老板端文创图片生成（文生图）", "type": "image"},
]

# 文本场景可用提供方（前端下拉选项）
# model 仅为「切到该提供方时的初始占位值」，实际可用模型请用「获取可用模型」按官方接口拉取，
# 因为官方模型名会随版本迭代变化（如 DeepSeek 已改为 deepseek-flash / deepseek-v4-pro）。
PROVIDER_PRESETS = {
    "qwen": {
        "label": "通义千问（阿里云百炼 Model Studio）",
        "base_url": DASHSCOPE_URL,
        "model": DASHSCOPE_MODEL,
        "models_urls": DASHSCOPE_MODELS_URLS,
        "models_hint": "如 qwen3.8-max / qwen3.7-plus / qwen3.6-flash",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": DEEPSEEK_URL,
        "model": DEEPSEEK_MODEL,
        "models_urls": DEEPSEEK_MODELS_URLS,
        "models_hint": "如 deepseek-flash / deepseek-v4-pro（注意：deepseek-v4.1-flash 是阿里云百炼侧的模型名，DeepSeek 官方平台不提供）",
    },
    "custom": {
        "label": "OpenAI 兼容接口（自定义）",
        "base_url": "",
        "model": "",
        "models_urls": [],
        "models_hint": "填写服务商文档中的真实模型名",
    },
    "offline": {"label": "离线兜底（不调用大模型）", "base_url": "", "model": "", "models_urls": [], "models_hint": ""},
}

# 生图场景可用提供方（Base URL 为生图接口地址，与文本接口不同）
IMAGE_PRESETS = {
    "qwen": {
        "label": "通义万相（阿里云百炼文生图）",
        "base_url": WANX_CREATE_URL,
        "model": WANX_MODEL,
        "models_urls": DASHSCOPE_MODELS_URLS,
        "models_hint": "如 wanx2.1-t2i-turbo / wan2.2-t2i-flash / qwen-image-max",
    },
    "custom": {
        "label": "OpenAI 兼容生图接口（/images/generations）",
        "base_url": "",
        "model": "",
        "models_urls": [],
        "models_hint": "如 dall-e-3 / flux-schnell",
    },
    "offline": {"label": "离线兜底（第三方免费文生图链接）", "base_url": "", "model": "", "models_urls": [], "models_hint": ""},
}

# 每个场景可选的提供方（顺序即前端下拉顺序）
SCENE_PROVIDERS = {
    "text": ["qwen", "deepseek", "custom", "offline"],
    "image": ["qwen", "custom", "offline"],
}


class NoLLMConfigured(Exception):
    """未配置任何大模型 API Key。"""


class LLMError(Exception):
    """大模型调用失败，message 为已翻译的中文可读原因。"""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.message = message
        self.status = status


# 最近一次调用失败原因（内存态，不落盘）：scene -> {message, status, at}
_last_error: dict = {}


def _upstream_message(resp) -> str:
    """从上游错误响应里取出最有信息量的一句话。"""
    try:
        data = json.loads(resp.text or "")
    except Exception:
        return (resp.text or "")[:200]
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict):
            for k in ("message", "code"):
                if isinstance(err.get(k), str) and err[k]:
                    return err[k]
        for k in ("message", "msg", "detail"):
            if isinstance(data.get(k), str) and data[k]:
                return data[k]
    return (resp.text or "")[:200]


def _friendly_error(exc: Exception) -> tuple:
    """把底层异常翻译为 (中文原因, HTTP 状态码)。"""
    # 已经翻译过的异常直接透传，避免二次包装
    if isinstance(exc, LLMError):
        return exc.message, exc.status
    if isinstance(exc, NoLLMConfigured):
        return str(exc), None

    status = getattr(getattr(exc, "response", None), "status_code", None)
    text = ""
    resp = getattr(exc, "response", None)
    if resp is not None:
        try:
            text = _upstream_message(resp)
        except Exception:
            text = ""

    if status == 401 or status == 403:
        base = (
            f"鉴权失败（HTTP {status}）：API Key 无效、已过期、被平台停用，或与所选提供方不匹配。"
            "请确认 Key 已完整复制，且确实属于当前选择的提供方平台"
            "（例如通义千问的 Key 只能用于 dashscope.aliyuncs.com，不能用于 DeepSeek）。"
        )
        # 官方文档对这两类原文有明确解释，直接给出可执行的修复方向
        low = (text or "").lower()
        if "incorrect api key" in low:
            base += (
                " 官方文档说明：返回「Incorrect API key provided」多表示 Key 与接口地域不匹配"
                "（百炼 API Key 按地域绑定，北京 / 新加坡 / 弗吉尼亚的 Key 互不通用），"
                "或该 Key 并非此平台签发。"
            )
        if "blocked" in low:
            base += " 上游提示该 Key 已被停用（blocked），请到控制台重新生成。"
        # 上游原文往往直接点明是「Key 错误」还是「Key 被停用」，附上便于精准定位
        return (f"{base} 上游返回：{text}" if text else base, status)
    if status == 404:
        return (
            "接口地址或模型不存在（HTTP 404）：请检查 Base URL 是否与服务商官方文档一致"
            "（通义千问为 https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions，"
            "DeepSeek 为 https://api.deepseek.com/chat/completions），"
            f"并确认模型名称为官方真实支持的名称（可用「获取可用模型」自动拉取）。{text}",
            status,
        )
    if status == 400:
        return (
            f"请求被拒绝（HTTP 400）：多为模型名称不存在或参数不被支持。{text}",
            status,
        )
    if status == 429:
        return (f"触发限流或余额不足（HTTP 429）：请稍后重试或检查账户额度。{text}", status)
    if isinstance(status, int) and status >= 500:
        return (f"服务端异常（HTTP {status}）：模型服务暂时不可用，请稍后重试。{text}", status)

    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return ("连接超时：无法在限定时间内访问模型服务，请检查网络或代理设置。", status)
    if isinstance(exc, urllib.error.URLError):
        return (f"网络不可达：{exc.reason}", status)

    name = exc.__class__.__name__
    if name in ("ConnectError", "ConnectTimeout", "ReadTimeout", "PoolTimeout"):
        return ("连接失败：无法访问模型服务，请检查网络、Base URL 或代理设置。", status)
    return (f"调用失败（{name}）：{str(exc)[:200]}", status)


def _record_error(scene: str, message: str, status=None):
    _last_error[scene] = {
        "message": message,
        "status": status,
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _clear_error(scene: str):
    _last_error.pop(scene, None)


# ------------------------------------------------------------------ 配置解析
def _scene_cfg(scene: str) -> dict:
    """取某场景的运行期配置。"""
    scenes = (store.get_model_config() or {}).get("scenes", {}) or {}
    return dict(scenes.get(scene) or {})


def _presets(scene: str) -> dict:
    """返回该场景可用的提供方预设表。"""
    return IMAGE_PRESETS if scene == "image" else PROVIDER_PRESETS


def _normalize_base(provider: str, base_url: str) -> str:
    """把历史遗留/写法不规范的服务地址纠正为官方文档地址。

    早期版本 DeepSeek 用了 https://api.deepseek.com/v1/chat/completions，
    官方文档给出的对话补全地址是 https://api.deepseek.com/chat/completions。
    """
    url = (base_url or "").strip().rstrip("/")
    if provider == "deepseek":
        if url in ("https://api.deepseek.com/v1", "https://api.deepseek.com/v1/chat/completions",
                   "https://api.deepseek.com", ""):
            return DEEPSEEK_URL
    if provider == "qwen":
        if url in ("https://dashscope.aliyuncs.com/compatible-mode/v1", ""):
            return DASHSCOPE_URL
        # 用户可能误填了「图生图」接口地址（image2image），而本系统按「文生图」（text2image）调用，
        # 统一纠正为目标路径，避免生图任务 100% 失败。
        if "image2image" in url and "text2image" not in url:
            return url.replace("image2image/image-synthesis", "text2image/image-synthesis")
    return base_url


def _infer_provider(scene: str) -> str:
    """未显式选择提供方时，按场景与环境变量推断一个合理默认。"""
    if scene == "image":
        # 文生图只有百炼通义万相或自定义 OpenAI 兼容接口
        return "qwen" if os.environ.get("DASHSCOPE_API_KEY") else "custom"
    if os.environ.get("DASHSCOPE_API_KEY"):
        return "qwen"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    return "custom"


def _resolve(scene: str = "chat"):
    """返回 (url, model, api_key, provider)；全部缺失时返回 (None, None, None, 'offline')。"""
    presets = _presets(scene)
    cfg = _scene_cfg(scene)
    provider = (cfg.get("provider") or "").strip()

    # 1) 运行期显式配置（含自定义 base_url / 模型名 / Key）
    if provider and provider != "offline" and provider in presets:
        api_key = (cfg.get("api_key") or "").strip()
        model = (cfg.get("model") or "").strip() or presets.get(provider, {}).get("model", "")
        base_url = _normalize_base(provider, cfg.get("base_url") or "") or presets.get(provider, {}).get("base_url", "")
        if api_key and base_url and model:
            return base_url, model, api_key, provider

    if provider == "offline":
        return None, None, None, "offline"

    # 2) 环境变量兜底
    if os.environ.get("DASHSCOPE_API_KEY"):
        key = os.environ["DASHSCOPE_API_KEY"]
        if scene == "image":
            return WANX_CREATE_URL, WANX_MODEL, key, "qwen"
        return DASHSCOPE_URL, DASHSCOPE_MODEL, key, "qwen"
    if os.environ.get("DEEPSEEK_API_KEY") and scene != "image":
        return DEEPSEEK_URL, DEEPSEEK_MODEL, os.environ["DEEPSEEK_API_KEY"], "deepseek"

    # 3) 无可用配置
    return None, None, None, "offline"


def provider(scene: str = "chat") -> str:
    """返回某场景当前可用的大模型提供方：qwen / deepseek / custom / offline。"""
    return _resolve(scene)[3]


def _endpoint(scene: str = "chat") -> tuple:
    """返回 (url, model, api_key)，未配置抛 NoLLMConfigured。"""
    url, model, api_key, _ = _resolve(scene)
    if not url or not api_key:
        raise NoLLMConfigured("未配置可用的大模型 API Key，已降级为离线答复")
    return url, model, api_key


def _mask(key: str) -> str:
    """API Key 脱敏展示。"""
    key = key or ""
    if len(key) <= 8:
        return "****" if key else ""
    return f"{key[:4]}****{key[-4:]}"


def describe() -> dict:
    """模型管理页面所需的全景信息：场景列表 + 当前配置 + 可用提供方。"""
    scenes = []
    for meta in SCENES:
        cfg = _scene_cfg(meta["key"])
        url, model, api_key, prov = _resolve(meta["key"])
        presets = _presets(meta["key"])
        scenes.append({
            **meta,
            "provider": (cfg.get("provider") or ("auto" if prov != "offline" else "offline")),
            "active_provider": prov,
            "model": cfg.get("model") or (model or ""),
            # 展示「实际生效」的地址：历史配置里的 /v1/... 会被 _normalize_base 纠正为官方地址
            "base_url": url or cfg.get("base_url") or "",
            "api_key_masked": _mask(api_key or ""),
            "has_key": bool(api_key),
            "key_length": len(api_key or ""),
            # 已保存但调用失败 → 前端按「配置有误」高亮
            "last_error": _last_error.get(meta["key"]),
            "providers": [
                {
                    "key": k,
                    "label": presets[k]["label"],
                    "base_url": presets[k]["base_url"],
                    "model": presets[k]["model"],
                    "models_hint": presets[k].get("models_hint", ""),
                    "can_list_models": bool(presets[k].get("models_urls")),
                }
                for k in SCENE_PROVIDERS.get(meta.get("type", "text"), [])
            ],
            "configured": bool(url and api_key),
        })
    return {
        "scenes": scenes,
        "providers": [
            {"key": k, "label": v["label"], "base_url": v["base_url"], "model": v["model"]}
            for k, v in PROVIDER_PRESETS.items()
        ],
        "env": {
            "dashscope": bool(os.environ.get("DASHSCOPE_API_KEY")),
            "deepseek": bool(os.environ.get("DEEPSEEK_API_KEY")),
        },
    }


def save_scenes(payload: dict) -> dict:
    """保存多场景模型配置（api_key 为空表示保持原值不变）。"""
    existing = (store.get_model_config() or {}).get("scenes", {}) or {}
    scenes = dict(existing)
    for key, val in (payload or {}).items():
        val = dict(val or {})
        api_key = (val.get("api_key") or "").strip()
        if not api_key and key in scenes:
            # 未重新填写 Key → 沿用旧值
            api_key = (scenes[key] or {}).get("api_key", "")
        scenes[key] = {
            "provider": val.get("provider", "offline"),
            "model": val.get("model", ""),
            # 落盘前按官方文档归一化，避免把历史遗留的 .../v1/chat/completions 再存回去
            "base_url": _normalize_base(val.get("provider", ""), val.get("base_url", "")),
            "api_key": api_key,
        }
        # 配置已变更，旧的失败记录不再适用
        _clear_error(key)
    store.save_model_config({"scenes": scenes})
    return describe()


async def test_connection(scene: str = "chat") -> dict:
    """对某场景发起一次最小真实请求，返回可读的连通性结论。

    这是「模型管理」页面验证配置是否真正生效的关键：直接暴露上游的真实报错
    （如 401 鉴权失败 / 404 模型不存在），而不是让调用方静默降级。
    """
    try:
        url, model, api_key, prov = _resolve(scene)
    except Exception as exc:  # 配置读取异常
        return {"ok": False, "scene": scene, "provider": "offline", "message": f"配置读取失败：{exc}"}

    if not url or not api_key:
        return {
            "ok": False, "scene": scene, "provider": prov, "model": model or "", "base_url": url or "",
            "message": "该场景当前为「离线兜底」：未填写 API Key，或提供方选择了 offline。",
            "hint": "请选择提供方、填写模型名称与 API Key 后保存，再点击测试。",
        }

    try:
        if scene == "image":
            await _test_image(url, model, api_key, prov)
        else:
            await chat([{"role": "user", "content": "ping"}], temperature=0, timeout=25.0, scene=scene)
        _clear_error(scene)
        return {
            "ok": True, "scene": scene, "provider": prov, "model": model,
            "base_url": url, "key_masked": _mask(api_key),
            "message": f"连接成功：{prov} / {model} 已可正常调用。",
        }
    except NoLLMConfigured:
        return {"ok": False, "scene": scene, "provider": prov, "message": "未配置可用的 API Key。"}
    except Exception as exc:
        msg, status = _friendly_error(exc)
        _record_error(scene, msg, status)
        return {
            "ok": False, "scene": scene, "provider": prov, "model": model, "base_url": url,
            "status": status, "message": msg,
        }


async def list_models(scene: str = "chat", keyword: str = "") -> dict:
    """按官方「模型列表」接口拉取该场景当前真正可用的模型名。

    为什么要这样做：各平台的模型名会随版本迭代变化（例如 DeepSeek 官方现在
    提供 deepseek-flash / deepseek-v4-pro，通义千问侧有 qwen-max-latest / qwen3-max 等），
    手写模型名极易过期导致 404。这里直接调用官方接口，保证拿到的是当下真实可用的名字。

    对应官方接口：
    - DeepSeek（OpenAI 兼容）：GET https://api.deepseek.com/models
    - 阿里云百炼（原生）：      GET https://dashscope.aliyuncs.com/api/v1/models
    """
    cfg = _scene_cfg(scene)
    presets = _presets(scene)
    provider = (cfg.get("provider") or "").strip()
    # 未显式选择提供方（或在「自动」模式）时，按场景与环境变量推断
    if provider in ("", "auto"):
        provider = _infer_provider(scene)
    preset = presets.get(provider) or {}

    api_key = (cfg.get("api_key") or "").strip()
    if not api_key:
        # 未单独填写 Key 时，允许复用环境变量兜底
        api_key = (os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or "").strip()

    if not api_key:
        return {
            "ok": False, "scene": scene, "models": [],
            "message": "请先填写并保存 API Key，再获取可用模型。",
        }

    # 候选列表接口：官方预设优先，其次由 Base URL 推导（/chat/completions → /models）
    urls = list(preset.get("models_urls") or [])
    base = _normalize_base(provider, cfg.get("base_url") or "") or preset.get("base_url", "")
    # 业务空间专属域名（https://ws-xxx.cn-beijing.maas.aliyuncs.com/...）：
    # 列表接口为同域名下的 /api/v1/models，且该 Key 只对该域名有效
    api_prefix = (base or "").split("/api/")[0]
    if api_prefix.endswith("maas.aliyuncs.com"):
        workspace_models = f"{api_prefix}/api/v1/models"
        if workspace_models not in urls:
            urls.insert(0, workspace_models)
    for suffix in ("/chat/completions", "/images/generations"):
        if (base or "").endswith(suffix):
            derived = base[: -len(suffix)] + "/models"
            if derived not in urls:
                urls.append(derived)
            break
    if not urls:
        return {
            "ok": False, "scene": scene, "models": [],
            "message": "当前提供方未提供模型列表接口，请在官方文档中查到模型名后手动填写。",
        }

    params = {"page_size": "200"}
    if keyword:
        params["name"] = keyword
    # 生图场景只要图片生成类模型（官方 capabilities=IG）
    if scene == "image":
        params["capabilities"] = "IG"

    errors = []
    for url in urls:
        try:
            payload = await _get_json(url, api_key, params)
            models = _extract_models(payload)
            if models:
                return {
                    "ok": True, "scene": scene, "provider": provider,
                    "models": models, "count": len(models),
                    "message": f"已从官方接口获取到 {len(models)} 个可用模型。",
                }
            errors.append(f"{url} 返回内容中未找到模型列表")
        except Exception as exc:
            msg, status = _friendly_error(exc)
            errors.append(f"{url} → {msg}")

    return {
        "ok": False, "scene": scene, "models": [],
        "message": "获取模型列表失败：" + "；".join(errors[:2]),
    }


async def _get_json(url: str, api_key: str, params: dict):
    """GET 一个 JSON 接口（httpx 缺失时回退 urllib）。"""
    try:
        import httpx
    except ImportError:
        return await asyncio.to_thread(_sync_get_json, url, api_key, params)

    async with httpx.AsyncClient(timeout=25) as client:
        resp = await client.get(url, params=params, headers={"Authorization": f"Bearer {api_key}"})
        resp.raise_for_status()
        return resp.json()


def _sync_get_json(url: str, api_key: str, params: dict):
    """标准库 GET JSON 回退实现。"""
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_models(payload: dict) -> list:
    """从各家返回结构中抽取模型名（兼容 OpenAI 与百炼两种形态）。"""
    if not isinstance(payload, dict):
        return []
    items = payload.get("data") or payload.get("models") or payload.get("result") or []
    if isinstance(items, dict):
        items = items.get("models") or items.get("data") or []
    ids = []
    for it in items or []:
        if isinstance(it, str):
            ids.append(it)
            continue
        if not isinstance(it, dict):
            continue
        for k in ("id", "model", "model_name", "name"):
            v = it.get(k)
            if isinstance(v, str) and v.strip():
                ids.append(v.strip())
                break
    # 去重并保持稳定排序
    return sorted(set(ids))


async def _test_image(url: str, model: str, api_key: str, prov: str):
    """生图场景的连通性测试：提交任务并轮询到真实状态，杜绝「假成功」。

    上一版只提交不轮询，导致用户配置了 image2image 接口 + qwen-mt-image-* 这类
    图生图/翻译模型时，「测试连接」显示成功、实际生成却 100% 失败。
    """
    import asyncio

    import httpx

    if prov == "qwen" or "dashscope" in (url or ""):
        # 用户可能误填了图生图（image2image）接口地址，调用前自动纠正为文生图（text2image）
        if "image2image" in url and "text2image" not in url:
            url = url.replace("image2image/image-synthesis", "text2image/image-synthesis")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        payload = {"model": model, "input": {"prompt": "ping"}, "parameters": {"n": 1, "size": "1024*1024"}}
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            task_id = (data.get("output") or {}).get("task_id")
            if not task_id:
                raise RuntimeError("通义万相未返回 task_id，接口可能不支持该模型做文生图")
            prefix = url.split("/api/v1/")[0] if "/api/v1/" in url else "https://dashscope.aliyuncs.com"
            task_url = f"{prefix}/api/v1/tasks/{task_id}"
            # 轮询真实任务状态（最多约 16 秒）
            for _ in range(8):
                await asyncio.sleep(2)
                tr = await client.get(task_url, headers={"Authorization": f"Bearer {api_key}"})  # noqa: E501
                td = tr.json()
                status = (td.get("output") or {}).get("task_status")
                if status == "SUCCEEDED":
                    return
                if status in ("FAILED", "CANCELED", "UNKNOWN"):
                    msg = ((td.get("output") or {}).get("message")) or ""
                    raise RuntimeError(
                        f"生图任务{status}：" + (msg[:300] if msg else "请检查模型是否支持文生图（text2image）")
                    )
            raise RuntimeError(
                "生图测试超时：若为 qwen-mt-image-* 等图生图/翻译类模型，请改选文生图模型（如 wanx2.1-t2i-turbo）"
            )
        return
    # OpenAI 兼容 /images/generations
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=25) as client:
        resp = await client.post(url, json={"model": model, "prompt": "ping", "n": 1}, headers=headers)
        resp.raise_for_status()


# ------------------------------------------------------------------ 请求实现
def _payload(messages: list, temperature: float, scene: str) -> bytes:
    url, model, _ = _endpoint(scene)
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


def _parse_response(raw: str) -> str:
    data = json.loads(raw)
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"大模型返回异常：{raw[:200]}")
    return (choices[0].get("message") or {}).get("content", "").strip()


def _sync_request(messages: list, temperature: float, timeout: float, scene: str) -> str:
    """标准库 urllib 同步请求（httpx 缺失时的兜底）。"""
    url, _, api_key = _endpoint(scene)
    req = urllib.request.Request(
        url,
        data=_payload(messages, temperature, scene),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return _parse_response(resp.read().decode("utf-8"))


async def chat(messages: list, temperature: float = 0.3, timeout: float = 60.0, scene: str = "chat") -> str:
    """异步调用大模型，返回回复文本。

    参数：
        messages: OpenAI 格式的消息列表 [{"role": "system"|"user"|"assistant", "content": "..."}]
        temperature: 采样温度
        scene: AI 场景（chat / report / warning / copywriting），决定使用哪套模型配置
    异常：
        NoLLMConfigured —— 未配置 API Key（上层需降级）
        LLMError        —— 上游返回错误（含中文可读原因与 HTTP 状态码，上层可决定是否降级）
    """
    url, model, api_key = _endpoint(scene)

    try:
        import httpx  # 可选依赖，缺失时回退标准库
    except ImportError:
        try:
            text = await asyncio.to_thread(_sync_request, messages, temperature, timeout, scene)
        except NoLLMConfigured:
            raise
        except Exception as exc:
            msg, status = _friendly_error(exc)
            _record_error(scene, msg, status)
            raise LLMError(msg, status) from exc
        _clear_error(scene)
        return text

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False,
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
            )
            resp.raise_for_status()
            text = _parse_response(resp.text)
    except NoLLMConfigured:
        raise
    except Exception as exc:
        msg, status = _friendly_error(exc)
        _record_error(scene, msg, status)
        raise LLMError(msg, status) from exc

    _clear_error(scene)
    return text


def get_last_error(scene: str):
    """返回某场景最近一次调用失败原因（供前端提示）。"""
    return _last_error.get(scene)
