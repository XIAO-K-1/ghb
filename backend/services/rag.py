"""RAG 检索模块（多租户 collection 隔离）。

设计目标：
1. **多租户隔离**：每家民宿一个独立 collection（homestay_<ID>）。
   collection 内 = 通用知识（SOP / OTA / 财务 / 竞品 / 本地文旅）
   + 该民宿专属的经营档案与贷款合同文档（由 mock 数据动态生成）。
   检索时只在该民宿的 collection 内查询，绝不串店。
2. **离线优先**：ChromaDB 为可选依赖，未安装或初始化失败时，
   自动降级为纯 Python 的「字符 bigram 交集 + 关键词加权」检索（仅用标准库）。
   注意：本项目不使用 jieba 等需要下载词典的依赖。
"""
import re
import zlib
from datetime import datetime

from . import store

# ---------------------------------------------------------------- 常量
CHUNK_SIZE = 300        # 分块长度（字符）
CHUNK_OVERLAP = 60      # 滑窗重叠

CHROMA_DIR = store.DATA_DIR + "/chroma_db"

# 通用知识文档：(文件名, doc_type, 展示来源)
GENERAL_DOCS = [
    ("sop.md", "sop", "您的经营SOP文档"),
    ("ota.md", "ota", "您的OTA运营指南"),
    ("finance.md", "finance", "您的财务与贷后管理文档"),
    ("competitor.md", "competitor", "同区域竞品数据"),
]

# 城市 → 本地文旅知识文档
CITY_LOCAL_DOCS = {
    "洛阳": ("local_luoyang.md", "local", "本地文旅知识"),
    "开封": ("local_kaifeng.md", "local", "本地文旅知识"),
    "安阳": ("local_anyang.md", "local", "本地文旅知识"),
}

# 领域关键词（用于加权打分，命中越多越相关）
DOMAIN_TERMS = [
    "贷款", "借款", "还款", "应还", "下期", "剩余", "额度", "授信", "利率", "逾期", "罚息", "征信",
    "资金", "流水", "营收", "收入", "财务", "现金",
    "入住率", "房价", "定价", "价格", "客流", "淡季", "旺季", "国庆", "节假日", "促销", "营销",
    "宣传", "引流", "推广", "文案", "小红书", "抖音",
    "携程", "美团", "飞猪", "OTA", "评分", "好评", "差评", "点评", "回复", "HOS", "PSI",
    "卫生", "保洁", "布草", "洗涤", "排班", "隔音", "投诉", "服务", "设施", "整改",
    "交通", "位置", "导航", "接站", "景点", "攻略", "路线", "玩法", "伴手礼", "美食", "美食攻略",
    "文创", "冰箱贴", "徽章", "图案", "海报",
    "竞品", "对标", "同区域", "标杆", "标准", "流程", "SOP", "预案", "风险", "巡检", "预警",
    "洛阳", "开封", "安阳", "栾川", "林州", "老君山", "龙门石窟", "洛邑古城", "清明上河园",
    "龙亭", "鼓楼", "包公湖", "红旗渠", "太行大峡谷", "水席", "灌汤包", "汴绣", "牡丹",
]

# ---------------------------------------------------------------- 缓存
_chunk_cache = {}        # homestay_id -> [chunk, ...]
_collections = {}        # homestay_id -> chroma collection
_client = None
_chroma_ready = None     # None=未检测, True/False


# ================================================================ 文本工具
def _clean(text: str) -> str:
    """去除多余空白，便于分块与比对。"""
    return re.sub(r"[ \t\r\f\v]+", " ", text or "").strip()


def bigrams(text: str) -> set:
    """提取字符 bigram 集合（去掉空白与标点）。"""
    t = re.sub(r"[\s，。、；：！？【】（）《》“”‘’,.;:!?()\[\]{}<>\"'|/\\~`@#$%^&*+=—…-]+", "", text or "")
    if len(t) < 2:
        return {t} if t else set()
    return {t[i:i + 2] for i in range(len(t) - 1)}


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """按段落优先、滑窗兜底的方式分块（约 300 字一块）。"""
    text = _clean(text)
    if not text:
        return []
    # 先按换行切段，累计到接近 size 再输出，尽量保持语义完整
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if p.strip()]
    pieces = []
    buf = ""
    for p in paragraphs:
        if len(p) > size:
            if buf:
                pieces.append(buf)
                buf = ""
            step = max(size - overlap, 1)
            for i in range(0, len(p), step):
                pieces.append(p[i:i + size])
                if i + size >= len(p):
                    break
            continue
        if len(buf) + len(p) + 1 <= size:
            buf = (buf + "\n" + p) if buf else p
        else:
            pieces.append(buf)
            buf = p
    if buf:
        pieces.append(buf)

    # 过滤过短碎片
    result = [x.strip() for x in pieces if len(x.strip()) >= 20]
    return result or ([text[:size]] if len(text) >= 20 else [text])


def _query_terms(question: str) -> list:
    """从问题中提取领域关键词（用于加权）。"""
    return [t for t in DOMAIN_TERMS if t.lower() in (question or "").lower()]


def score_chunk(question: str, text: str) -> float:
    """打分明细：字符 bigram 交集 + 领域关键词加权。"""
    q_bg = bigrams(question)
    d_bg = bigrams(text)
    inter = len(q_bg & d_bg)
    terms = _query_terms(question)
    # 关键词命中加权，长词更具体，权重更高
    kw_score = sum(1 + len(t) / 4.0 for t in terms if t in text)
    return float(inter) + kw_score * 6.0


# ================================================================ 文档构造
def _homestay_profile_doc(h: dict) -> str:
    """该民宿专属经营档案（含贷款与舆情关键指标）。"""
    reviews = h.get("recent_reviews", {}) or {}
    kw_text = "、".join(f"{k} {v} 次" for k, v in store.negative_keywords(h, 6))
    occ7 = h.get("occupancy_7d", []) or []
    avg7 = round(sum(float(x) for x in occ7) / len(occ7), 3) if occ7 else 0
    risk_cn = {"red": "红色高风险", "amber": "黄色中风险", "green": "绿色低风险"}.get(h.get("risk_level"), "未知")
    return (
        f"【民宿经营档案】{h.get('name')}（编号 {h.get('id')}），位于 {h.get('address')}，隶属 {h.get('city')}。\n"
        f"文化标签：{'、'.join(h.get('cultural_tags', []))}。\n"
        f"当前入住率 {float(h.get('current_occupancy', 0)) * 100:.0f}%，近 7 日平均入住率 {avg7 * 100:.0f}%。\n"
        f"平均房价 {h.get('avg_price')} 元，本月营收 {h.get('monthly_revenue')} 元。\n"
        f"OTA 综合评分 {h.get('ota_score')} 分；近 7 日新增点评 {reviews.get('total_7d')} 条，其中差评 {reviews.get('bad_7d')} 条。\n"
        f"差评关键词分布：{kw_text}。\n"
        f"当前风险等级：{risk_cn}；风险原因：{h.get('risk_reason')}。\n"
        f"近 30 天经营流水下降比例：{float(h.get('flow_drop_30d', 0)) * 100:.0f}%。上次巡检时间：{h.get('last_inspection')}。"
    )


def _loan_contract_doc(h: dict) -> str:
    """该民宿专属贷款合同与还款计划文档。"""
    amount = int(h.get("loan_amount", 0) or 0)
    used = int(h.get("loan_used", 0) or 0)
    ratio = used / amount if amount else 0
    return (
        f"【豫游民宿贷 · 贷款合同与还款计划】\n"
        f"借款人：{(h.get('owner') or {}).get('name')}；民宿名称：{h.get('name')}。\n"
        f"合同贷款金额 {amount} 元，已使用额度 {used} 元，额度使用率 {ratio * 100:.0f}%。\n"
        f"剩余未偿还本金 {h.get('loan_balance')} 元，授信额度上限 {h.get('credit_limit')} 元。\n"
        f"还款约定：{h.get('repayment_day')}，每月应还金额 {h.get('monthly_repayment')} 元；"
        f"下期还款日为 {store.next_repayment_date(h)}，下个月要还 {h.get('monthly_repayment')} 元。\n"
        f"贷后要求：贷款资金仅限用于民宿装修改造与经营性支出，严禁挪用；"
        f"若额度使用率超过 90% 且近 30 天经营流水下降超过 20%，将触发红色预警 R004。"
    )


def _build_chunks(h: dict) -> list:
    """构造某民宿 collection 的全部知识块（通用知识 + 专属数据）。"""
    chunks = []

    def _add(text: str, doc_type: str, source: str):
        for idx, piece in enumerate(chunk_text(text)):
            chunks.append({
                "id": f"{h.get('id')}::{doc_type}::{idx}",
                "text": piece,
                "doc_type": doc_type,
                "source": source,
            })

    # 1) 通用知识
    for filename, doc_type, source in GENERAL_DOCS:
        content = store.read_knowledge(filename)
        if content:
            _add(content, doc_type, source)

    # 2) 对应城市的本地文旅知识
    local = CITY_LOCAL_DOCS.get(h.get("city"))
    if local:
        content = store.read_knowledge(local[0])
        if content:
            _add(content, local[1], local[2])

    # 3) 该民宿专属经营档案与贷款合同（多租户隔离的关键：只属于本店）
    _add(_homestay_profile_doc(h), "homestay_profile", "您的民宿经营档案")
    _add(_loan_contract_doc(h), "loan_contract", "您的贷款合同")

    # 4) 老板/银行通过「RAG 系统管理」添加的自定义文档（含爬取的平台评论）
    for doc in store.list_rag_docs(h.get("id")):
        content = doc.get("content") or ""
        if content.strip():
            _add(content, doc.get("doc_type") or "custom", doc.get("title") or "自定义文档")

    # 5) 老板与本店 AI 的历史对话记录（沉淀为专属文档）
    history = store.list_chat_history(h.get("id"), limit=30)
    if history:
        lines = ["【我的 AI 咨询记录】以下为老板与本店 AI 经营助手的历史问答摘录："]
        for item in reversed(history):
            lines.append(f"问：{item.get('question', '')}")
            ans = str(item.get("answer", "")).strip()
            if ans:
                lines.append(f"答：{ans[:160]}")
        _add("\n".join(lines), "chat_history", "您的 AI 咨询记录")

    return chunks


def get_chunks(homestay_id: str) -> list:
    """获取（并缓存）某民宿的知识块。"""
    hid = str(homestay_id)
    if hid not in _chunk_cache:
        h = store.get_homestay(hid)
        if h is None:
            _chunk_cache[hid] = []
        else:
            _chunk_cache[hid] = _build_chunks(h)
    return _chunk_cache[hid]


# ================================================================ ChromaDB
class _HashEmbedding:
    """轻量确定性向量化（字符 bigram 哈希），供 ChromaDB 使用。

    目的：完全离线，不下载任何 embedding 模型。
    """
    DIM = 256

    def __init__(self, dim: int = 256):
        self.dim = dim

    def name(self) -> str:
        return "yusuxun-hash-bigram"

    @staticmethod
    def build_from_config(config):
        return _HashEmbedding(int((config or {}).get("dim", 256)))

    def get_config(self):
        return {"dim": self.dim}

    def _vec(self, text: str) -> list:
        vec = [0.0] * self.dim
        for bg in bigrams(text):
            vec[zlib.crc32(bg.encode("utf-8")) % self.dim] += 1.0
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]

    def __call__(self, input):
        return [self._vec(t) for t in input]

    def embed_query(self, input):
        return [self._vec(t) for t in input]


def _init_chroma() -> bool:
    """懒加载 ChromaDB，失败则永久降级为内置检索。"""
    global _client, _chroma_ready
    if _chroma_ready is not None:
        return _chroma_ready
    try:
        import chromadb
        try:
            _client = chromadb.PersistentClient(
                path=CHROMA_DIR,
                settings=chromadb.config.Settings(anonymized_telemetry=False),
            )
        except TypeError:
            # 不同版本参数差异，退化为最简构造
            _client = chromadb.PersistentClient(path=CHROMA_DIR)
        _chroma_ready = True
    except Exception:
        _client = None
        _chroma_ready = False
    return _chroma_ready


def _get_collection(h: dict):
    """获取（并惰性构建）该民宿的 collection。"""
    hid = h.get("id")
    if hid in _collections:
        return _collections[hid]
    chunks = get_chunks(hid)
    if not chunks:
        return None
    col = _client.get_or_create_collection(
        name=f"homestay_{hid}",
        embedding_function=_HashEmbedding(),
    )
    # 每次进程启动都 upsert 一次，保证 mock 数据变更后索引同步
    col.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"], "doc_type": c["doc_type"]} for c in chunks],
    )
    _collections[hid] = col
    return col


def backend_name() -> str:
    """当前向量检索后端：chromadb / builtin。"""
    return "chromadb" if _init_chroma() else "builtin"


def _chroma_candidates(h: dict, question: str, limit: int) -> list:
    """用 ChromaDB 粗排候选（返回知识块列表），异常时返回空列表触发兜底。"""
    if not _init_chroma():
        return []
    try:
        col = _get_collection(h)
        if col is None:
            return []
        total = col.count()
        if total == 0:
            return []
        res = col.query(query_texts=[question], n_results=min(limit, total))
        ids = (res.get("ids") or [[]])[0]
        by_id = {c["id"]: c for c in get_chunks(h.get("id"))}
        return [by_id[i] for i in ids if i in by_id]
    except Exception:
        # 任何异常都降级为纯 Python 检索，绝不影响接口可用
        global _chroma_ready
        _chroma_ready = False
        return []


# ================================================================ 对外检索
def retrieve(homestay_id: str, question: str, top_k: int = 4) -> list:
    """在指定民宿的独立知识库中检索，返回 Top-K 片段。

    返回：[{source, doc_type, snippet, score}]，score 为 0~1 的相对相关度。
    隔离保证：只检索 homestay_<ID> 这一个 collection，绝不跨店。
    """
    h = store.get_homestay(homestay_id)
    if h is None:
        return []

    all_chunks = get_chunks(h.get("id"))
    if not all_chunks:
        return []

    # 先用 ChromaDB 粗排候选；不可用时用全量知识块做内置检索
    candidates = _chroma_candidates(h, question, max(top_k * 4, 12))
    if not candidates:
        candidates = all_chunks

    scored = []
    for c in candidates:
        s = score_chunk(question, c["text"])
        scored.append((s, c))
    scored.sort(key=lambda x: -x[0])

    top = scored[:top_k]
    max_score = top[0][0] if top and top[0][0] > 0 else 1.0

    results = []
    for s, c in top:
        snippet = c["text"].replace("\n", " ").strip()
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"
        results.append({
            "source": c["source"],
            "doc_type": c["doc_type"],
            "snippet": snippet,
            "score": round(float(s) / max_score, 3) if max_score else 0.0,
        })
    return results


def build_context(homestay_id: str, question: str, top_k: int = 4) -> tuple:
    """检索并拼接成提示词上下文，返回 (context_text, sources)。"""
    results = retrieve(homestay_id, question, top_k)
    if not results:
        return "", []
    blocks = []
    for i, r in enumerate(results, 1):
        blocks.append(f"[资料{i}｜来源：{r['source']}]\n{r['snippet']}")
    return "\n\n".join(blocks), results


def collection_stats(homestay_id: str) -> dict:
    """调试用：返回该民宿 collection 的统计信息。"""
    chunks = get_chunks(homestay_id)
    return {
        "homestay_id": homestay_id,
        "collection": f"homestay_{homestay_id}",
        "backend": backend_name(),
        "chunk_count": len(chunks),
        "doc_types": sorted({c["doc_type"] for c in chunks}),
    }


# ================================================================ 文档库管理
def invalidate(homestay_id: str = None):
    """清除知识块缓存与向量集合缓存（文档增删改后调用）。

    传 None 表示清空全部（如模型/配置变更时）。
    """
    global _chroma_ready
    if homestay_id is None:
        _chunk_cache.clear()
        _collections.clear()
        return
    hid = str(homestay_id)
    _chunk_cache.pop(hid, None)
    _collections.pop(hid, None)


def _doc_entry(doc_id, title, scope, doc_type, content, **extra) -> dict:
    content = content or ""
    entry = {
        "id": doc_id,
        "title": title,
        "scope": scope,              # public=公用文档 / private=本店专属
        "doc_type": doc_type,
        "content": content,
        "chars": len(content),
        "chunks": len(chunk_text(content)),
        "editable": bool(extra.get("editable", False)),
        "removable": bool(extra.get("removable", False)),
        "homestay_id": extra.get("homestay_id"),
        "source": extra.get("source") or title,
        "updated_at": extra.get("updated_at") or "",
    }
    return entry


def list_documents(homestay_id: str) -> dict:
    """列出某民宿 RAG 文档库的全部文档（公用 + 本店专属 + 自定义）。

    用于「RAG 系统管理」页面清晰展示检索文档库。
    """
    h = store.get_homestay(homestay_id)
    if h is None:
        return {
            "homestay_id": homestay_id, "documents": [],
            "public_count": 0, "private_count": 0, "total_chunks": 0,
        }

    documents = []

    # 1) 公用知识文档（所有民宿共享）
    for filename, doc_type, source in GENERAL_DOCS:
        content = store.read_knowledge(filename)
        if content:
            documents.append(_doc_entry(
                f"pub::{filename}", source, "public", doc_type, content,
                source=source, updated_at="内置公用文档",
            ))
    local = CITY_LOCAL_DOCS.get(h.get("city"))
    if local:
        content = store.read_knowledge(local[0])
        if content:
            documents.append(_doc_entry(
                f"pub::{local[0]}", local[2], "public", local[1], content,
                source=local[2], updated_at="内置公用文档",
            ))

    # 2) 本店专属：AI 自动生成的经营档案 / 贷款合同
    documents.append(_doc_entry(
        "priv::profile", "您的民宿经营档案", "private", "homestay_profile",
        _homestay_profile_doc(h), source="系统自动生成", updated_at="实时生成",
    ))
    documents.append(_doc_entry(
        "priv::loan", "您的贷款合同", "private", "loan_contract",
        _loan_contract_doc(h), source="系统自动生成", updated_at="实时生成",
    ))

    # 3) 本店专属：老板与 AI 的对话记录
    history = store.list_chat_history(h.get("id"), limit=50)
    if history:
        lines = ["【我的 AI 咨询记录】以下为老板与本店 AI 经营助手的历史问答摘录："]
        for item in reversed(history):
            lines.append(f"问：{item.get('question', '')}")
            ans = str(item.get("answer", "")).strip()
            if ans:
                lines.append(f"答：{ans[:200]}")
        documents.append(_doc_entry(
            "priv::chat", "您的 AI 咨询记录", "private", "chat_history",
            "\n".join(lines), source="AI 对话沉淀",
            updated_at=history[0].get("at", ""),
        ))

    # 4) 本店专属：自定义上传/爬取的文档（可编辑、可删除）
    for doc in store.list_rag_docs(h.get("id")):
        documents.append(_doc_entry(
            doc.get("id"), doc.get("title") or "自定义文档",
            doc.get("scope") or "private", doc.get("doc_type") or "custom",
            doc.get("content") or "",
            editable=True, removable=True, homestay_id=doc.get("homestay_id") or h.get("id"),
            source=doc.get("source") or "自定义",
            updated_at=doc.get("updated_at") or doc.get("created_at") or "",
        ))

    total_chunks = sum(d["chunks"] for d in documents)
    return {
        "homestay_id": h.get("id"),
        "homestay_name": h.get("name"),
        "city": h.get("city"),
        "collection": f"homestay_{h.get('id')}",
        "backend": backend_name(),
        "documents": documents,
        "public_count": len([d for d in documents if d["scope"] == "public"]),
        "private_count": len([d for d in documents if d["scope"] == "private"]),
        "total_docs": len(documents),
        "total_chunks": total_chunks,
    }


# ================================================================ 评论定时采集
_REVIEW_SOURCES = ["携程", "美团", "飞猪", "小红书", "去哪儿"]


def simulate_crawl(homestay_id: str) -> dict:
    """模拟「定时爬取各平台评论」：把该店近期评价与关键词整理成文档入库。

    说明：演示环境不真正联网抓取（合规与稳定性考虑），而是基于本店已有
    公开评价样本生成一份与真实数据结构一致的「平台评论采集」文档，写入该店
    专属 RAG 文档库，供 AI 检索使用。
    """
    h = store.get_homestay(homestay_id)
    if h is None:
        raise ValueError(f"民宿不存在：{homestay_id}")

    today = datetime.now().strftime("%Y-%m-%d")
    samples = h.get("review_samples", []) or []
    keywords = h.get("keyword_counts", {}) or {}
    reviews = h.get("recent_reviews", {}) or {}

    lines = [f"【{today} 平台评论自动采集】民宿：{h.get('name')}（{h.get('id')}）"]
    lines.append(
        f"采集来源：{'、'.join(_REVIEW_SOURCES)}｜采集时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    lines.append(
        f"近 7 日累计点评 {reviews.get('total_7d', 0)} 条，其中差评 {reviews.get('bad_7d', 0)} 条；"
        f"当前 OTA 综合评分 {h.get('ota_score')} 分。"
    )
    if keywords:
        lines.append("关键词分布：" + "、".join(f"{k} {v} 次" for k, v in keywords.items()))
    lines.append("评价原文摘录：")
    for rv in samples[:20]:
        lines.append(
            f"- [{rv.get('platform', 'OTA')} {rv.get('date', '')} {rv.get('score', '')}分] "
            f"{rv.get('content', '')}"
        )

    doc = store.add_rag_doc({
        "homestay_id": h.get("id"),
        "title": f"平台评论采集 · {today}",
        "scope": "private",
        "doc_type": "review_crawl",
        "source": "平台评论自动采集",
        "tags": ["评论", "舆情"],
        "content": "\n".join(lines),
        "auto": True,
    })
    invalidate(h.get("id"))

    state = store.get_crawl_state()
    state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["last_homestay_id"] = h.get("id")
    state["count"] = int(state.get("count", 0)) + 1
    store.save_crawl_state(state)

    return {"doc": doc, "state": store.get_crawl_state()}


def crawl_all() -> dict:
    """对所有民宿执行一次评论采集（供定时任务调用）。"""
    created = []
    for h in store.list_homestays():
        try:
            res = simulate_crawl(h.get("id"))
            created.append(res["doc"])
        except Exception:
            continue
    return {"created": len(created), "state": store.get_crawl_state()}
