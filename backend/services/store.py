"""数据读写层。

职责：
1. mock_data.json  —— 只读，提供 12 家民宿与演示账号；
2. runtime.json    —— 读写，持久化运行期生成的预警、巡检报告、注册用户；
3. 内存缓存        —— 避免每次请求都读盘；
4. 趋势生成        —— 以民宿 ID 为随机种子的确定性 30 天经营趋势。

字段口径说明（与前端约定）：
- loan_amount   贷款/授信合同金额（元）
- loan_used     已使用（已提用）额度（元）
- loan_balance  剩余未偿还本金余额（元）
- credit_limit  授信额度上限（元）
- monthly_repayment 每月应还金额（元）
"""
import json
import os
import random
import threading
import uuid
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------- 路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")
MOCK_PATH = os.path.join(DATA_DIR, "mock_data.json")
RUNTIME_PATH = os.path.join(DATA_DIR, "runtime.json")

# ---------------------------------------------------------------- 缓存与锁
_lock = threading.RLock()
_mock_cache = None
_runtime_cache = None


def _now_str() -> str:
    """当前时间字符串。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _read_json(path):
    """读取 JSON 文件（兼容 UTF-8 BOM）。"""
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _write_json(path, obj):
    """写入 JSON 文件（UTF-8，保留中文）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ---------------------------------------------------------------- mock 数据
def load_mock() -> dict:
    """加载 mock_data.json（只读，带内存缓存）。"""
    global _mock_cache
    with _lock:
        if _mock_cache is None:
            _mock_cache = _read_json(MOCK_PATH)
        return _mock_cache


def list_homestays() -> list:
    """全部民宿列表。"""
    return load_mock().get("homestays", [])


def get_homestay(homestay_id: str):
    """按 ID 获取单家民宿，找不到返回 None。"""
    if not homestay_id:
        return None
    for h in list_homestays():
        if h.get("id", "").upper() == str(homestay_id).upper():
            return h
    return None


def list_mock_users() -> list:
    """mock 中的预置账号。"""
    return load_mock().get("users", [])


def get_meta() -> dict:
    return load_mock().get("meta", {})


def read_knowledge(filename: str) -> str:
    """读取 knowledge 目录下的知识文档，不存在返回空串。"""
    path = os.path.join(KNOWLEDGE_DIR, filename)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


# ---------------------------------------------------------------- runtime 数据
def load_runtime() -> dict:
    """加载 runtime.json，不存在则自动创建空结构。"""
    global _runtime_cache
    with _lock:
        if _runtime_cache is None:
            if os.path.exists(RUNTIME_PATH):
                try:
                    _runtime_cache = _read_json(RUNTIME_PATH)
                except Exception:
                    _runtime_cache = None
            if _runtime_cache is None:
                _runtime_cache = {
                    "created_at": _now_str(),
                    "updated_at": _now_str(),
                    "warnings": [],
                    "reports": [],
                    "users": [],
                    "rag_docs": [],
                    "chat_history": [],
                    "model_config": {},
                    "crawl_state": {},
                    "messages": [],
                    "creative_works": [],
                }
                try:
                    _write_json(RUNTIME_PATH, _runtime_cache)
                except Exception:
                    # 只读文件系统等极端情况：仅用内存兜底，不影响接口可用
                    pass
        # 兼容老版本缺字段
        for key in ("warnings", "reports", "users", "rag_docs", "chat_history", "messages", "creative_works"):
            _runtime_cache.setdefault(key, [])
        _runtime_cache.setdefault("model_config", {})
        _runtime_cache.setdefault("crawl_state", {})
        return _runtime_cache


def save_runtime():
    """把内存中的 runtime 写回磁盘。"""
    with _lock:
        rt = load_runtime()
        rt["updated_at"] = _now_str()
        try:
            _write_json(RUNTIME_PATH, rt)
        except Exception:
            pass


# ---------------------------------------------------------------- 预警
def list_warnings(status: str = None, level: str = None) -> list:
    """查询预警列表，可按状态/等级过滤。"""
    rt = load_runtime()
    result = list(rt.get("warnings", []))
    if status:
        result = [w for w in result if w.get("status") == status]
    if level:
        result = [w for w in result if w.get("level") == level]
    # 时间倒序（最新在前）
    result.sort(key=lambda w: w.get("created_at", ""), reverse=True)
    return result


def get_warning(warning_id: str):
    for w in load_runtime().get("warnings", []):
        if w.get("id") == warning_id:
            return w
    return None


def has_open_warning(homestay_id: str, rule_id: str) -> bool:
    """去重判断：同一民宿 + 同一规则，只要存在未关闭的预警就不再重复生成。"""
    for w in load_runtime().get("warnings", []):
        if (
            w.get("homestay_id") == homestay_id
            and w.get("rule_id") == rule_id
            and w.get("status") != "closed"
        ):
            return True
    return False


def add_warning(warning: dict) -> dict:
    """新增一条预警并持久化。"""
    with _lock:
        rt = load_runtime()
        if not warning.get("id"):
            warning["id"] = "W" + uuid.uuid4().hex[:10]
        rt["warnings"].append(warning)
        save_runtime()
        return warning


def update_warning_status(warning_id: str, status: str):
    """更新预警状态，返回更新后的对象；未找到返回 None。"""
    with _lock:
        rt = load_runtime()
        for w in rt.get("warnings", []):
            if w.get("id") == warning_id:
                w["status"] = status
                w["updated_at"] = _now_str()
                save_runtime()
                return w
    return None


def warning_summary() -> dict:
    """预警汇总：红/黄数量 + 待处理数量。"""
    warnings = list_warnings()
    red = len([w for w in warnings if w.get("level") == "red"])
    amber = len([w for w in warnings if w.get("level") == "amber"])
    pending = len([w for w in warnings if w.get("status") == "pending"])
    processing = len([w for w in warnings if w.get("status") == "processing"])
    closed = len([w for w in warnings if w.get("status") == "closed"])
    return {
        "total": len(warnings),
        "red": red,
        "amber": amber,
        "pending": pending,
        "processing": processing,
        "closed": closed,
    }


# ---------------------------------------------------------------- 报告
def list_reports(homestay_id: str = None) -> list:
    rt = load_runtime()
    result = list(rt.get("reports", []))
    if homestay_id:
        result = [r for r in result if r.get("homestay_id") == homestay_id]
    result.sort(key=lambda r: r.get("generated_at", ""), reverse=True)
    return result


def add_report(report: dict) -> dict:
    with _lock:
        rt = load_runtime()
        if not report.get("report_id"):
            report["report_id"] = "R" + uuid.uuid4().hex[:10]
        rt["reports"].append(report)
        save_runtime()
        return report


# ---------------------------------------------------------------- 注册用户
def list_runtime_users() -> list:
    return load_runtime().get("users", [])


def find_user(username: str):
    """在 mock 预置账号 + runtime 注册账号中查找用户。"""
    if not username:
        return None
    for u in list_mock_users():
        if u.get("username") == username:
            return u
    for u in list_runtime_users():
        if u.get("username") == username:
            return u
    return None


def add_user(user: dict) -> dict:
    with _lock:
        rt = load_runtime()
        rt["users"].append(user)
        save_runtime()
        return user


# ---------------------------------------------------------------- RAG 文档库
def list_rag_docs(homestay_id: str = None) -> list:
    """查询自定义 RAG 文档（按民宿过滤；homestay_id 为空则返回全部）。"""
    result = list(load_runtime().get("rag_docs", []))
    if homestay_id:
        result = [d for d in result if d.get("homestay_id") in (homestay_id, "", None)]
    result.sort(key=lambda d: d.get("updated_at", ""), reverse=True)
    return result


def get_rag_doc(doc_id: str):
    for d in load_runtime().get("rag_docs", []):
        if d.get("id") == doc_id:
            return d
    return None


def add_rag_doc(doc: dict) -> dict:
    with _lock:
        rt = load_runtime()
        if not doc.get("id"):
            doc["id"] = "DOC" + uuid.uuid4().hex[:10]
        doc.setdefault("created_at", _now_str())
        doc["updated_at"] = _now_str()
        rt["rag_docs"].append(doc)
        save_runtime()
        return doc


def update_rag_doc(doc_id: str, patch: dict):
    """更新文档的标题/正文/标签，返回更新后的对象；未找到返回 None。"""
    with _lock:
        rt = load_runtime()
        for d in rt.get("rag_docs", []):
            if d.get("id") == doc_id:
                for key in ("title", "content", "tags", "doc_type", "source"):
                    if key in patch and patch[key] is not None:
                        d[key] = patch[key]
                d["updated_at"] = _now_str()
                save_runtime()
                return d
    return None


def delete_rag_doc(doc_id: str) -> bool:
    with _lock:
        rt = load_runtime()
        before = len(rt.get("rag_docs", []))
        rt["rag_docs"] = [d for d in rt.get("rag_docs", []) if d.get("id") != doc_id]
        changed = len(rt["rag_docs"]) != before
        if changed:
            save_runtime()
        return changed


# ---------------------------------------------------------------- AI 对话记录
def list_chat_history(homestay_id: str, limit: int = 50) -> list:
    result = [c for c in load_runtime().get("chat_history", []) if c.get("homestay_id") == homestay_id]
    result.sort(key=lambda c: c.get("at", ""), reverse=True)
    return result[:limit]


def add_chat_history(item: dict) -> dict:
    """记录老板与 AI 的对话（用于构建民宿专属 RAG 文档）。"""
    with _lock:
        rt = load_runtime()
        item.setdefault("at", _now_str())
        rt["chat_history"].append(item)
        # 仅保留最近 500 条，避免文件无限增长
        if len(rt["chat_history"]) > 500:
            rt["chat_history"] = rt["chat_history"][-500:]
        save_runtime()
        return item


def clear_chat_history(homestay_id: str):
    with _lock:
        rt = load_runtime()
        rt["chat_history"] = [c for c in rt.get("chat_history", []) if c.get("homestay_id") != homestay_id]
        save_runtime()


# ---------------------------------------------------------------- 消息中心（老板 ⇄ 银行客户经理）
def list_messages(homestay_id: str = None) -> list:
    """查询消息（可按民宿过滤，缺省返回全部），按时间正序。"""
    result = list(load_runtime().get("messages", []))
    if homestay_id:
        result = [m for m in result if m.get("homestay_id") == homestay_id]
    result.sort(key=lambda m: m.get("at", ""))
    return result


def send_message(homestay_id: str, sender: str, text: str) -> dict:
    """发送一条消息并持久化（sender：owner=民宿老板 / bank=银行客户经理）。"""
    with _lock:
        rt = load_runtime()
        msg = {
            "id": "M" + uuid.uuid4().hex[:10],
            "homestay_id": homestay_id,
            "sender": sender,
            "text": text,
            "at": _now_str(),
            "read": False,
        }
        rt.setdefault("messages", []).append(msg)
        # 仅保留最近 2000 条，避免文件无限增长
        if len(rt["messages"]) > 2000:
            rt["messages"] = rt["messages"][-2000:]
        save_runtime()
        return msg


def unread_message_count(from_sender: str = "owner") -> int:
    """统计指定方向（默认：老板发来）且未读的消息条数，供银行端导航角标使用。"""
    msgs = load_runtime().get("messages", [])
    return len([m for m in msgs if m.get("sender") == from_sender and not m.get("read")])


def mark_messages_read(homestay_id: str = None, from_sender: str = "owner") -> int:
    """把某个民宿（或全部）的指定方向消息标记为已读，返回标记条数。"""
    with _lock:
        rt = load_runtime()
        n = 0
        for m in rt.setdefault("messages", []):
            if m.get("sender") == from_sender and not m.get("read"):
                if not homestay_id or m.get("homestay_id") == homestay_id:
                    m["read"] = True
                    n += 1
        if n:
            save_runtime()
        return n


# ---------------------------------------------------------------- AI 文创产物（按民宿隔离，仅本店老板可见）
def list_creative_works(homestay_id: str = None) -> list:
    """查询 AI 文创产物历史（图片/文案），可按民宿过滤；时间倒序（最新在前）。"""
    result = list(load_runtime().get("creative_works", []))
    if homestay_id:
        result = [w for w in result if w.get("homestay_id") == homestay_id]
    result.sort(key=lambda w: w.get("at", ""), reverse=True)
    return result


def add_creative_work(work: dict) -> dict:
    """持久化一条 AI 文创产物（图片或文案），仅对生成账号（民宿）可见。"""
    with _lock:
        rt = load_runtime()
        if not work.get("id"):
            work["id"] = "CW" + uuid.uuid4().hex[:10]
        work.setdefault("at", _now_str())
        rt.setdefault("creative_works", []).append(work)
        # 每店仅保留最近 200 条，避免文件无限增长
        hid = work.get("homestay_id")
        same = [w for w in rt["creative_works"] if w.get("homestay_id") == hid]
        other = [w for w in rt["creative_works"] if w.get("homestay_id") != hid]
        rt["creative_works"] = other + same[-200:]
        save_runtime()
        return work


# ---------------------------------------------------------------- 模型配置
def get_model_config() -> dict:
    """返回运行时的多场景模型配置（为空则回退环境变量，由 llm 层处理）。"""
    return dict(load_runtime().get("model_config", {}) or {})


def save_model_config(config: dict) -> dict:
    with _lock:
        rt = load_runtime()
        rt["model_config"] = dict(config or {})
        save_runtime()
        return rt["model_config"]


# ---------------------------------------------------------------- 评论爬取状态
# 每日固定采集时间（HH:MM，可用环境变量 YSX_CRAWL_TIME 覆盖）
CRAWL_SCHEDULE = os.environ.get("YSX_CRAWL_TIME", "03:00")


def get_crawl_state() -> dict:
    state = dict(load_runtime().get("crawl_state", {}) or {})
    state.setdefault("schedule", CRAWL_SCHEDULE)
    state.setdefault("enabled", True)
    state.setdefault("sources", ["携程", "美团", "飞猪", "小红书", "去哪儿"])
    return state


def save_crawl_state(state: dict) -> dict:
    with _lock:
        rt = load_runtime()
        rt["crawl_state"] = dict(state or {})
        save_runtime()
        return rt["crawl_state"]


# ---------------------------------------------------------------- 预警扩展字段
def update_warning_fields(warning_id: str, fields: dict):
    """更新预警的任意字段（如 pushed_to_app / ai_generated）。"""
    with _lock:
        rt = load_runtime()
        for w in rt.get("warnings", []):
            if w.get("id") == warning_id:
                w.update(fields or {})
                w["updated_at"] = _now_str()
                save_runtime()
                return w
    return None


def get_report(report_id: str):
    for r in load_runtime().get("reports", []):
        if r.get("report_id") == report_id or r.get("id") == report_id:
            return r
    return None


def update_report_fields(report_id: str, fields: dict):
    with _lock:
        rt = load_runtime()
        for r in rt.get("reports", []):
            if r.get("report_id") == report_id or r.get("id") == report_id:
                r.update(fields or {})
                r["updated_at"] = _now_str()
                save_runtime()
                return r
    return None


# ---------------------------------------------------------------- 业务派生
# 负面（差评）关键词白名单：用于把「差评关键词」与「好评关键词」区分开
NEGATIVE_KEYWORDS = {
    "卫生差", "隔音差", "服务差", "位置偏", "设施差", "交通不便", "性价比低", "停车难", "潮味", "路不好走",
}


def negative_keywords(h: dict, limit: int = 4) -> list:
    """返回该民宿的差评关键词 Top-N（若无负面关键词则退回全部关键词）。"""
    counts = h.get("keyword_counts", {}) or {}
    neg = [(k, v) for k, v in counts.items() if k in NEGATIVE_KEYWORDS]
    if not neg:
        neg = list(counts.items())
    neg.sort(key=lambda kv: -kv[1])
    return neg[:limit]


def available_credit(h: dict) -> int:
    """剩余可用额度。"""
    return max(0, int(h.get("credit_limit", 0)) - int(h.get("loan_used", 0)))


def used_ratio(h: dict) -> float:
    """额度使用率 = 已用 / 贷款金额。"""
    amount = int(h.get("loan_amount", 0)) or 1
    return round(int(h.get("loan_used", 0)) / amount, 4)


def next_repayment_date(h: dict) -> str:
    """根据还款日推算下期还款日期（YYYY-MM-DD）。"""
    day_text = str(h.get("repayment_day", "每月15日"))
    digits = "".join(ch for ch in day_text if ch.isdigit())
    day = int(digits) if digits else 15
    day = min(max(day, 1), 28)
    today = date.today()
    candidate = today.replace(day=day)
    if candidate < today:
        # 已过本月还款日 → 推到下个月
        year = today.year + (1 if today.month == 12 else 0)
        month = 1 if today.month == 12 else today.month + 1
        candidate = date(year, month, day)
    return candidate.strftime("%Y-%m-%d")


def build_trends(h: dict, days: int = 30) -> dict:
    """确定性生成近 N 天经营趋势（同一民宿每次结果一致）。

    以民宿 ID 作为随机种子，风险等级与流水下滑比例决定趋势斜率：
    红色高风险民宿的营收/入住率整体呈下滑态势，绿色民宿基本平稳。
    """
    rnd = random.Random("yusuxun-" + str(h.get("id", "unknown")))
    risk = h.get("risk_level", "green")
    drop = float(h.get("flow_drop_30d", 0) or 0)
    base_occ = float(h.get("current_occupancy", 0.4))
    base_price = float(h.get("avg_price", 350))
    base_ota = float(h.get("ota_score", 4.3))
    monthly_revenue = float(h.get("monthly_revenue", 60000))

    # 反推客房数，使"入住率 × 房价 × 客房数 × 天数 ≈ 月营收"
    rooms = max(1, round(monthly_revenue / max(base_price * max(base_occ, 0.05) * 30, 1)))

    dates, occ_list, price_list, rev_list, ota_list = [], [], [], [], []
    today = date.today()
    for i in range(days - 1, -1, -1):
        dates.append((today - timedelta(days=i)).strftime("%Y-%m-%d"))

    for idx in range(days):
        t = idx / (days - 1) if days > 1 else 1.0  # 0=最早, 1=今天
        # 风险店：越早营收越高 → 呈下滑；健康店：几乎持平
        decay = 1.0 + drop * (1.0 - t)
        if risk == "amber":
            decay = 1.0 + drop * 0.6 * (1.0 - t)

        occ_v = base_occ * decay * rnd.uniform(0.96, 1.04)
        rev_v = (monthly_revenue / days) * decay * rnd.uniform(0.95, 1.05)
        price_v = base_price * (1 + 0.02 * (1 - t)) * rnd.uniform(0.98, 1.02)
        # 评分：风险店由高走低，健康店窄幅波动
        ota_v = base_ota + (1 - t) * (drop * 1.4 if risk == "red" else drop * 0.5)
        ota_v += rnd.uniform(-0.05, 0.05)

        occ_list.append(round(min(max(occ_v, 0.05), 0.98), 3))
        price_list.append(int(round(price_v)))
        rev_list.append(int(round(rev_v)))
        ota_list.append(round(min(max(ota_v, 3.0), 5.0), 1))

    # 最后一天强制对齐当前真实值，保证与详情页数据自洽
    occ_list[-1] = round(base_occ, 3)
    price_list[-1] = int(round(base_price))
    rev_list[-1] = int(round(monthly_revenue / days))
    ota_list[-1] = round(base_ota, 1)

    return {
        "dates": dates,
        "occupancy": occ_list,
        "avg_price": price_list,
        "revenue": rev_list,
        "ota": ota_list,
        "rooms": rooms,
    }
