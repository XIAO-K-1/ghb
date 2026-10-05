"""贷后风控规则引擎（R001-R004）。

设计原则：全部使用简单 if-else 判断，不引入机器学习模型。
规则命中后生成预警记录并持久化到 runtime.json；
同一「民宿 + 规则」在存在未关闭预警时不重复生成（去重）。
另外提供 AI 智能预警生成：依据民宿评分、评论、AI 对话记录等信息自动生成预警文案。
"""
from datetime import datetime

from . import llm, rag, store

# ------------------------------------------------------------------ 规则定义
RULE_R001 = "R001"
RULE_R002 = "R002"
RULE_R003 = "R003"
RULE_R004 = "R004"

RULE_NAMES = {
    RULE_R001: "OTA评分跌破4.0且差评激增",
    RULE_R002: "入住率连续7天低于30%",
    RULE_R003: "差评关键词集中",
    RULE_R004: "资金使用率高且流水大幅下滑",
}

# 各规则对应的可执行整改建议
SUGGESTIONS = {
    RULE_R001: (
        "① 客户经理 3 个工作日内上门核查卫生与服务流程；"
        "② 启动《卫生差评整改五步法》，生成《客房保洁排班优化表》，落实布草一客一换、60℃以上高温洗涤；"
        "③ 24 小时内逐条回复近 7 日差评并邀评，两周后复核评分是否回升至 4.2 以上。"
    ),
    RULE_R002: (
        "① 推出淡季连住优惠、周末特惠等促销活动，拉升入住率；"
        "② 结合本地文旅资源设计「住宿+景点+汉服」打包产品，在 OTA 平台做流量投放；"
        "③ 提醒借款人关注现金流，若连续两个月低于 25%，建议下调授信额度或追加增信措施。"
    ),
    RULE_R003: (
        "① 针对集中差评关键词生成专项整改任务清单，明确责任人与完成时限；"
        "② 卫生类问题生成《客房保洁排班优化表》与《布草清洗标准》，位置类问题补充交通指引与接站服务；"
        "③ 15 日内复核关键词出现频次，若未下降 50% 升级为红色预警并上报信贷主管。"
    ),
    RULE_R004: (
        "① 核查贷款资金用途，防范资金挪用风险，要求提供近 30 天经营流水与用款凭证；"
        "② 与借款人共同制定还款计划，确认下期应还金额的现金来源；"
        "③ 下季度授信额度建议调降 20%，并加强还款日前 5 日的跟踪提醒。"
    ),
}


def _hit(h: dict) -> list:
    """对单家民宿执行四条规则判断，返回命中的规则 ID 与指标。"""
    hits = []
    reviews = h.get("recent_reviews", {}) or {}
    ota_score = float(h.get("ota_score", 5.0))
    bad_7d = int(reviews.get("bad_7d", 0) or 0)
    occ7 = list(h.get("occupancy_7d", []) or [])
    keywords = h.get("keyword_counts", {}) or {}
    loan_amount = int(h.get("loan_amount", 0) or 0) or 1
    loan_used = int(h.get("loan_used", 0) or 0)
    flow_drop = float(h.get("flow_drop_30d", 0) or 0)

    # R001：OTA 评分 < 4.0 且近 7 日差评 > 3 → 红色
    if ota_score < 4.0 and bad_7d > 3:
        hits.append({
            "rule_id": RULE_R001,
            "level": "red",
            "reason": f"{h.get('name')}近7日差评+{bad_7d}，OTA评分{dict_score(ota_score)}已跌破4.0，建议立即核查",
            "metrics": {
                "ota_score": ota_score,
                "bad_7d": bad_7d,
                "total_7d": int(reviews.get("total_7d", 0) or 0),
                "threshold": {"ota_score": 4.0, "bad_7d": 3},
            },
        })

    # R002：入住率连续 7 天全部 < 30% → 黄色
    if len(occ7) >= 7 and all(float(x) < 0.30 for x in occ7[-7:]):
        hits.append({
            "rule_id": RULE_R002,
            "level": "amber",
            "reason": f"{h.get('name')}入住率连续7天低于30%（近7日最低 {min(occ7[-7:]) * 100:.0f}%），建议关注经营状况",
            "metrics": {
                "occupancy_7d": occ7[-7:],
                "avg_7d": round(sum(float(x) for x in occ7[-7:]) / 7, 3),
                "threshold": 0.30,
            },
        })

    # R003：差评关键词「卫生差 / 位置偏」出现次数 > 3 → 黄色
    hygiene = int(keywords.get("卫生差", 0) or 0)
    location = int(keywords.get("位置偏", 0) or 0)
    hot_words = []
    if hygiene > 3:
        hot_words.append(("卫生差", hygiene))
    if location > 3:
        hot_words.append(("位置偏", location))
    if hot_words:
        word_text = "、".join(f"{w}（{c}次）" for w, c in hot_words)
        hits.append({
            "rule_id": RULE_R003,
            "level": "amber",
            "reason": f"{h.get('name')}差评关键词集中在「{word_text}」，建议核查服务质量与到店指引",
            "metrics": {
                "keyword_counts": keywords,
                "hot_words": [{"keyword": w, "count": c} for w, c in hot_words],
                "threshold": 3,
            },
        })

    # R004：资金使用率 > 90% 且近 30 天流水下降 > 20% → 红色
    ratio = loan_used / loan_amount
    if ratio > 0.90 and flow_drop > 0.20:
        hits.append({
            "rule_id": RULE_R004,
            "level": "red",
            "reason": (
                f"{h.get('name')}贷款额度使用率 {ratio * 100:.0f}%，"
                f"近30天经营流水下降 {flow_drop * 100:.0f}%，存在还款风险"
            ),
            "metrics": {
                "loan_amount": loan_amount,
                "loan_used": loan_used,
                "used_ratio": round(ratio, 4),
                "flow_drop_30d": flow_drop,
                "monthly_repayment": h.get("monthly_repayment"),
                "threshold": {"used_ratio": 0.90, "flow_drop": 0.20},
            },
        })

    return hits


def dict_score(score: float) -> str:
    """评分展示保留一位小数。"""
    return f"{score:.1f}"


def build_warning(h: dict, hit: dict) -> dict:
    """把规则命中结果组装成预警记录。"""
    return {
        "id": "",
        "homestay_id": h.get("id"),
        "homestay_name": h.get("name"),
        "city": h.get("city"),
        "owner_name": (h.get("owner") or {}).get("name"),
        "owner_phone": (h.get("owner") or {}).get("phone"),
        "rule_id": hit["rule_id"],
        "rule_name": RULE_NAMES.get(hit["rule_id"], hit["rule_id"]),
        "level": hit["level"],
        "reason": hit["reason"],
        "suggestion": SUGGESTIONS.get(hit["rule_id"], ""),
        "status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": hit.get("metrics", {}),
    }


def evaluate_all() -> list:
    """对所有民宿执行规则，返回全部命中项（不落库）。"""
    results = []
    for h in store.list_homestays():
        for hit in _hit(h):
            results.append(build_warning(h, hit))
    return results


def run_rules() -> dict:
    """执行规则引擎：生成新预警（自动去重）并返回结果。

    返回：{created: [新增预警], all: [当前全部预警], summary: {...}, matched: 命中总数}
    """
    created = []
    for h in store.list_homestays():
        for hit in _hit(h):
            # 去重：同一民宿 + 同一规则，只要存在未关闭预警就跳过
            if store.has_open_warning(h.get("id"), hit["rule_id"]):
                continue
            warning = store.add_warning(build_warning(h, hit))
            created.append(warning)

    return {
        "created": created,
        "created_count": len(created),
        "all": store.list_warnings(),
        "summary": store.warning_summary(),
    }


# ================================================================ AI 智能预警
AI_RULE_ID = "AI"
AI_RULE_NAME = "AI智能预警"

_AI_QUERY = "经营风险 舆情差评 卫生差 入住率下滑 流水下降 额度使用率 还款压力 整改建议"


def _offline_ai_warning(h: dict, sources: list) -> tuple:
    """离线兜底：依据真实指标拼装预警原因与建议。"""
    reviews = h.get("recent_reviews", {}) or {}
    kw = "、".join(f"{k}（{v}次）" for k, v in store.negative_keywords(h, 3)) or "暂无明显差评关键词"
    chat = store.list_chat_history(h.get("id"), limit=5)
    chat_hint = ""
    if chat:
        qs = "；".join(c.get("question", "")[:24] for c in chat[:3] if c.get("question"))
        chat_hint = f"结合老板近期在 AI 助手中的咨询（{qs}），" if qs else ""

    reason = (
        f"AI 综合分析：{h.get('name')} 当前 OTA 评分 {h.get('ota_score')} 分，"
        f"近 7 日点评 {reviews.get('total_7d', 0)} 条（差评 {reviews.get('bad_7d', 0)} 条），"
        f"高频差评关键词：{kw}；当前入住率 {float(h.get('current_occupancy', 0)) * 100:.0f}%，"
        f"近 30 天经营流水下降 {float(h.get('flow_drop_30d', 0)) * 100:.0f}%，"
        f"额度使用率 {int(h.get('loan_used', 0)) / max(int(h.get('loan_amount', 0) or 1), 1) * 100:.0f}%。"
        f"{chat_hint}综合判断该店存在贷后经营风险，建议尽快介入关注。"
    )
    suggestion = (
        "① 客户经理 3 个工作日内联系经营者核实经营与还款计划；"
        "② 针对集中差评关键词制定专项整改清单，落实布草一客一换与高温洗涤标准；"
        "③ 若入住率与流水持续下滑，评估下调授信额度或追加增信措施；"
        "④ 提醒经营者提前储备不少于 2 期还款资金，防范逾期风险。"
    )
    return reason, suggestion


async def generate_ai_warning(homestay_id: str) -> dict:
    """AI 依据民宿评分、评论、对话记录等信息自动生成一条预警并发往老板端。"""
    h = store.get_homestay(homestay_id)
    if h is None:
        raise ValueError(f"民宿不存在：{homestay_id}")

    context, sources = rag.build_context(h.get("id"), _AI_QUERY, top_k=4)
    reason, suggestion = _offline_ai_warning(h, sources)
    mode = "offline"
    degrade_reason = None

    if llm.provider("warning") != "offline":
        try:
            system = (
                "你是工行「豫宿巡」贷后风控系统的 AI 风险分析师。"
                "请依据提供的民宿数据与知识片段，判断是否存在贷后经营风险，"
                "并输出两行，第一行以「原因：」开头（60~120字，引用具体指标），"
                "第二行以「建议：」开头（给出 3~4 条可执行整改建议）。"
                "只能依据资料，不得编造数据。"
            )
            user = (
                f"民宿：{h.get('name')}（{h.get('id')}，{h.get('city')}）\n"
                f"OTA 评分 {h.get('ota_score')}，入住率 {h.get('current_occupancy')}，"
                f"近 7 日差评 {((h.get('recent_reviews') or {}).get('bad_7d'))} 条，"
                f"近 30 天流水下降 {h.get('flow_drop_30d')}，"
                f"额度使用率 {int(h.get('loan_used', 0)) / max(int(h.get('loan_amount', 0) or 1), 1):.2f}。\n"
                f"【知识库片段】\n{context}"
            )
            text = await llm.chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.35, scene="warning",
            )
            if text:
                reason_line, sug_line = "", ""
                for line in text.splitlines():
                    line = line.strip().lstrip("#* ").strip()
                    if line.startswith("原因"):
                        reason_line = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                    elif line.startswith("建议"):
                        sug_line = line.split("：", 1)[-1].split(":", 1)[-1].strip()
                if reason_line:
                    reason = reason_line
                if sug_line:
                    suggestion = sug_line
                if reason_line or sug_line:
                    mode = "llm"
        except llm.NoLLMConfigured:
            degrade_reason = "未配置「AI 预警生成」模型，已使用规则引擎模板文案。"
        except Exception as exc:
            detail = getattr(exc, "message", None) or str(exc)
            degrade_reason = f"大模型调用失败，已使用规则引擎模板文案。原因：{detail}"

    level = h.get("risk_level") if h.get("risk_level") in ("red", "amber") else "amber"
    warning = store.add_warning({
        "id": "",
        "homestay_id": h.get("id"),
        "homestay_name": h.get("name"),
        "city": h.get("city"),
        "owner_name": (h.get("owner") or {}).get("name"),
        "owner_phone": (h.get("owner") or {}).get("phone"),
        "rule_id": AI_RULE_ID,
        "rule_name": AI_RULE_NAME,
        "level": level,
        "reason": reason,
        "suggestion": suggestion,
        "status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {},
        "ai_generated": True,
        "mode": mode,
        "pushed_to_app": False,
        "sources": [{"source": s["source"], "doc_type": s["doc_type"]} for s in sources],
    })

    return {
        "warning": warning,
        "mode": mode,
        "degrade_reason": degrade_reason,
        "sources": [{"source": s["source"], "doc_type": s["doc_type"]} for s in sources],
        "summary": store.warning_summary(),
    }
