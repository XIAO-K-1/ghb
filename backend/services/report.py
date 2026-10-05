"""AI 巡检报告生成。

流程：RAG 检索该民宿私有知识库 → 拼接 Prompt → 调用大模型 → 返回结构化 Markdown。
未配置大模型 API Key 或调用失败时，自动降级为「模板 + RAG 检索结果」拼装的离线报告，
报告结构完全一致（一、基础信息 二、风险摘要 三、AI分析 四、建议措施 五、巡检历史）。
"""
from datetime import datetime

from . import llm, rag, rules, store

REPORT_TITLE = "《豫宿巡·贷后风险巡检报告》"

# 报告生成时用于检索的“问题”（覆盖舆情、经营、资金、整改四类意图）
REPORT_QUERY = "经营风险 舆情分析 差评关键词 卫生差 流水下滑 贷款额度使用率 下期应还 整改建议"

RISK_CN = {"red": "🔴 高风险", "amber": "🟡 中风险", "green": "🟢 低风险"}


def _money(value) -> str:
    """金额格式化：元 → 万元。"""
    try:
        return f"{int(value) / 10000:.1f} 万元"
    except Exception:
        return str(value)


def _build_offline_report(h: dict, sources: list, warnings: list) -> str:
    """离线兜底报告：用真实数据 + RAG 检索片段拼装（无大模型也完整可用）。"""
    hid = h.get("id")
    reviews = h.get("recent_reviews", {}) or {}
    occ7 = h.get("occupancy_7d", []) or []
    trends = store.build_trends(h)
    loan_amount = int(h.get("loan_amount", 0) or 0)
    loan_used = int(h.get("loan_used", 0) or 0)
    ratio = loan_used / loan_amount if loan_amount else 0
    avg7 = round(sum(float(x) for x in occ7) / len(occ7), 3) if occ7 else 0
    kw_top = "、".join(f"{k}（{v}次）" for k, v in store.negative_keywords(h, 4))

    # 经营趋势判断：比较趋势数组首尾
    rev = trends["revenue"]
    rev_change = (rev[-1] - rev[0]) / rev[0] if rev and rev[0] else 0
    occ_change = trends["occupancy"][-1] - trends["occupancy"][0]

    related = [w for w in warnings if w.get("homestay_id") == hid]
    if related:
        trigger_text = "；".join(f"{w['rule_id']} {w['rule_name']}（{w['level']}）" for w in related)
    else:
        trigger_text = f"{h.get('risk_reason')}（当前未触发新的规则预警）"

    # 依据规则给出建议措施
    suggestions = []
    for w in related:
        suggestions.append(f"{w['rule_id']} 对应整改：{w['suggestion']}")
    if not suggestions:
        suggestions = [
            "保持现有经营节奏，重点关注节假日期间的差评变化，落实布草一客一换与 60℃以上高温洗涤标准。",
            "结合本地文旅资源设计「住宿 + 景点 + 体验」打包产品，在 OTA 平台持续优化详情页与图片。",
            "关注现金流覆盖率，确保月度经营性现金流入不低于月还款额的 1.5 倍，提前储备 2~3 期还款资金。",
        ]

    src_text = "\n".join(
        f"- 【{s['source']}】{s['snippet']}" for s in sources[:4]
    ) or "- 暂无可用知识片段"

    last_reports = store.list_reports(hid)
    history_text = (
        f"- 上次巡检时间：{h.get('last_inspection')}\n"
        f"- 当前风险等级：{RISK_CN.get(h.get('risk_level'), h.get('risk_level'))}\n"
        f"- 历史报告份数：{len(last_reports)} 份"
    )

    top_source = sources[0]["source"] if sources else "您的经营SOP文档"
    safety_line = int((h.get("monthly_repayment") or 0) * 1.5)
    suggestion_lines = "\n".join(
        f"{i}. {s}" for i, s in enumerate(suggestions, 1)
    )
    trend_text = (
        "较上次巡检风险上升，需重点跟踪"
        if h.get("risk_level") in ("red", "amber")
        else "风险平稳，维持常规巡检频率"
    )

    lines = [
        REPORT_TITLE,
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"民宿名称：{h.get('name')}",
        f"贷款金额：{_money(loan_amount)}",
        "",
        "## 一、基础信息",
        f"- 民宿编号：{hid}（{h.get('city')}）",
        f"- 民宿地址：{h.get('address')}",
        f"- 经营者：{(h.get('owner') or {}).get('name')}　联系电话：{(h.get('owner') or {}).get('phone')}",
        f"- 贷款金额：{_money(loan_amount)}　已用额度：{_money(loan_used)}（使用率 {ratio * 100:.0f}%）",
        f"- 授信额度：{_money(h.get('credit_limit'))}　剩余未偿还本金：{_money(h.get('loan_balance'))}",
        f"- 还款约定：{h.get('repayment_day')}，月还款额 {h.get('monthly_repayment')} 元，"
        f"下期还款日 {store.next_repayment_date(h)}",
        f"- 文化标签：{'、'.join(h.get('cultural_tags', []))}",
        "",
        "## 二、风险摘要",
        f"- 风险等级：{RISK_CN.get(h.get('risk_level'), h.get('risk_level'))}",
        f"- 风险原因：{h.get('risk_reason')}",
        f"- 触发规则：{trigger_text}",
        f"- 当前 OTA 评分：{h.get('ota_score')} 分；近 7 日点评 {reviews.get('total_7d')} 条，"
        f"差评 {reviews.get('bad_7d')} 条",
        f"- 差评关键词：{kw_top}",
        f"- 额度使用率：{ratio * 100:.0f}%；近 30 天流水下降：{float(h.get('flow_drop_30d', 0)) * 100:.0f}%",
        "",
        "## 三、AI分析",
        f"**舆情分析**：近 7 日共收到 {reviews.get('total_7d')} 条点评，其中差评 {reviews.get('bad_7d')} 条，"
        f"差评关键词集中在「{kw_top}」。结合《{top_source}》中的规范要求，当前问题主要表现为"
        "服务执行标准未落地，而非硬件不可逆缺陷，属于可通过流程整改快速改善的类型。",
        "",
        f"**经营趋势判断**：近 30 天入住率由 {trends['occupancy'][0] * 100:.0f}% 变化至 "
        f"{trends['occupancy'][-1] * 100:.0f}%（变化 {occ_change * 100:+.1f} 个百分点），"
        f"日均营收由 {rev[0]} 元变化至 {rev[-1]} 元（变化 {rev_change * 100:+.1f}%）。"
        f"近 7 日平均入住率 {avg7 * 100:.0f}%，月还款额 {h.get('monthly_repayment')} 元，"
        f"按 1.5 倍现金流覆盖率测算，月度经营现金流入安全线为 {safety_line} 元。",
        "",
        "**知识库依据**：",
        src_text,
        "",
        "## 四、建议措施",
        suggestion_lines,
        "",
        "## 五、巡检历史",
        history_text,
        f"- 风险变化趋势：{trend_text}",
    ]
    return "\n".join(lines)


def _build_prompt(h: dict, context: str) -> list:
    """构造大模型提示词（要求输出五段式 Markdown）。"""
    system = (
        "你是工行河南分行「豫宿巡」贷后风控系统的 AI 巡检报告撰写助手。"
        "你只能依据用户提供的资料作答，不得编造数据。"
        "输出必须为结构化 Markdown，且严格包含以下五段："
        "一、基础信息；二、风险摘要；三、AI分析（含舆情分析与经营趋势判断）；"
        "四、建议措施（至少 3 条，可执行、含责任与时限）；五、巡检历史。"
        "语言专业、简洁，面向银行客户经理。"
    )
    user = (
        f"【该民宿资料】\n民宿：{h.get('name')}（{h.get('id')}，{h.get('city')}）\n"
        f"贷款金额：{h.get('loan_amount')} 元，已用额度：{h.get('loan_used')} 元，"
        f"剩余本金：{h.get('loan_balance')} 元，{h.get('repayment_day')}，月还款 {h.get('monthly_repayment')} 元。\n"
        f"当前入住率：{h.get('current_occupancy')}，OTA 评分：{h.get('ota_score')}，"
        f"近 7 日差评 {((h.get('recent_reviews') or {}).get('bad_7d'))} 条，风险等级：{h.get('risk_level')}。\n\n"
        f"【RAG 检索到的知识片段】\n{context}\n\n"
        "请基于以上资料，生成完整的《豫宿巡·贷后风险巡检报告》。"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


async def generate_report(homestay_id: str) -> dict:
    """生成（并持久化）AI 巡检报告。"""
    h = store.get_homestay(homestay_id)
    if h is None:
        raise ValueError(f"民宿不存在：{homestay_id}")

    context, sources = rag.build_context(h.get("id"), REPORT_QUERY, top_k=4)
    warnings = store.list_warnings()

    mode = "offline"
    content = ""
    degrade_reason = None
    if llm.provider("report") != "offline":
        try:
            content = await llm.chat(_build_prompt(h, context), temperature=0.3, scene="report")
            if content:
                mode = "llm"
        except llm.NoLLMConfigured:
            content = ""
            degrade_reason = "未配置「AI 巡检报告」模型，已使用离线模板报告。"
        except Exception as exc:
            content = ""
            degrade_reason = getattr(exc, "message", None) or f"大模型调用失败：{exc}"
            degrade_reason = f"大模型调用失败，已使用离线模板报告。原因：{degrade_reason}"

    if not content:
        content = _build_offline_report(h, sources, warnings)
        mode = "offline"

    report = {
        "report_id": "",
        "homestay_id": h.get("id"),
        "homestay_name": h.get("name"),
        "city": h.get("city"),
        "risk_level": h.get("risk_level"),
        "mode": mode,
        "report_content": content,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": [{"source": s["source"], "doc_type": s["doc_type"]} for s in sources],
        "pushed_to_app": False,
    }
    report = store.add_report(report)

    return {
        "report_id": report["report_id"],
        "homestay_id": report["homestay_id"],
        "homestay_name": report["homestay_name"],
        "risk_level": report["risk_level"],
        "mode": mode,
        "degrade_reason": degrade_reason,
        "generated_at": report["generated_at"],
        "report_content": content,
        "sources": report["sources"],
        "pushed_to_app": report.get("pushed_to_app", False),
    }


def related_warnings(homestay_id: str) -> list:
    """取该民宿当前未关闭的预警（供报告页展示）。"""
    return [w for w in store.list_warnings()
            if w.get("homestay_id") == homestay_id and w.get("status") != "closed"]


def rule_names() -> dict:
    return dict(rules.RULE_NAMES)
