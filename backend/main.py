"""豫宿巡 · 后端服务（FastAPI）。

一句话定位：解决「银行放了款之后怎么办」——
面向工行客户经理提供贷后风控驾驶舱，面向民宿老板提供 AI 经营赋能工具。

启动：
    python run.py
    # 或 uvicorn main:app --reload

接口文档：http://localhost:8000/docs
"""
import asyncio
import base64
import os
import time
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services import creative, llm, rag, report as report_service, rules, store

# ---------------------------------------------------------------- 应用初始化
app = FastAPI(
    title="豫宿巡 · 贷后风控与经营赋能 API",
    description=(
        "《豫宿巡——基于AI大模型与RAG的古都民宿贷后赋能与风控系统》后端服务。\n\n"
        "闭环：数据采集 → AI分析 → 贷后预警 → 经营赋能 → 风险改善。\n"
        "离线优先：未配置大模型 API Key 时自动降级为本地知识库抽取式答复；"
        "ChromaDB 未安装时自动降级为内置纯 Python 检索。"
    ),
    version="1.0.0",
)

# CORS：允许所有来源（前端 Vite 5173 通过代理访问，仍开放跨域便于联调）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------- 每日定时采集
# 老板端「RAG 系统」每天固定时间自动采集各平台评论，沉淀为专属 RAG 文档。
async def _daily_crawl_loop():
    """按 YSX_CRAWL_TIME（默认 03:00）每天执行一次评论采集。"""
    while True:
        try:
            hh, mm = (str(store.CRAWL_SCHEDULE).split(":") + ["0", "0"])[:2]
            now = datetime.now()
            nxt = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            if nxt <= now:
                nxt = nxt + timedelta(days=1)
            await asyncio.sleep(max(30, (nxt - now).total_seconds()))
            await asyncio.to_thread(rag.crawl_all)
        except asyncio.CancelledError:
            break
        except Exception:
            # 出错不影响服务，1 小时后再试
            await asyncio.sleep(3600)


@app.on_event("startup")
async def _startup_tasks():
    app.state.crawl_task = asyncio.create_task(_daily_crawl_loop())


@app.on_event("shutdown")
async def _shutdown_tasks():
    task = getattr(app.state, "crawl_task", None)
    if task:
        task.cancel()


# ---------------------------------------------------------------- 请求体模型
class ChatBody(BaseModel):
    homestay_id: str = Field(..., description="民宿 ID，例如 LY001")
    question: str = Field(..., description="老板的问题，例如：下个月我要还多少钱？")


class ReportBody(BaseModel):
    homestay_id: str


class CreativeBody(BaseModel):
    homestay_id: str
    theme: str = Field("", description="文创主题，例如：洛阳水席")
    count: int = Field(1, ge=1, le=4)


class VectorizeBody(BaseModel):
    image_url: str


class RegisterBody(BaseModel):
    username: str
    password: str
    name: str
    phone: str = ""
    homestay_id: str = ""


class LoginBody(BaseModel):
    username: str
    password: str


class MessageBody(BaseModel):
    homestay_id: str = Field(..., description="民宿 ID，例如 LY001")
    sender: str = Field("owner", description="发送方：owner=民宿老板 / bank=银行客户经理")
    text: str = Field(..., description="消息内容")


class MessageReadBody(BaseModel):
    homestay_id: str = Field("", description="标记该民宿已读；为空标记全部")


class WarningPatch(BaseModel):
    status: str = Field(..., description="processing 或 closed")


class RagDocBody(BaseModel):
    homestay_id: str = Field("", description="为空表示公用文档，所有民宿可见")
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="文档正文")
    doc_type: str = Field("custom", description="文档类型：custom / review_crawl / policy ...")
    tags: list = Field(default_factory=list)
    scope: str = Field("private", description="public 公用 / private 本店专属")


class RagDocPatch(BaseModel):
    title: str | None = None
    content: str | None = None
    doc_type: str | None = None
    source: str | None = None
    tags: list | None = None


class ModelSaveBody(BaseModel):
    scenes: dict = Field(default_factory=dict, description="场景 key → {provider, model, base_url, api_key}")


class ModelTestBody(BaseModel):
    scene: str = Field("chat", description="要测试的 AI 场景：chat / report / warning / copywriting / image")


class ModelListBody(BaseModel):
    scene: str = Field("chat", description="要查询可用模型的 AI 场景")
    keyword: str = Field("", description="按模型名模糊搜索，可选")


class CrawlBody(BaseModel):
    homestay_id: str = Field("", description="为空表示对所有民宿执行采集")


class CopywritingBody(BaseModel):
    homestay_id: str
    requirement: str = ""
    style: str = "xiaohongshu"


class StyleGenBody(BaseModel):
    homestay_id: str
    style_key: str
    count: int = Field(1, ge=1, le=4)
    image_url: str = ""


class ReportPushBody(BaseModel):
    report_id: str


# ---------------------------------------------------------------- 工具函数
def _make_token(username: str) -> str:
    """生成演示用 token（仅 base64 编码，非安全凭证，生产环境请使用 JWT）。"""
    raw = f"{username}:{int(time.time())}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def _public_user(user: dict) -> dict:
    """对外返回的用户信息（不含密码）。"""
    return {
        "username": user.get("username"),
        "name": user.get("name"),
        "phone": user.get("phone"),
        "homestay_id": user.get("homestay_id"),
        "role": user.get("role", "owner"),
    }


def _with_trends(h: dict) -> dict:
    """在民宿对象上附加确定性生成的 30 天趋势与派生指标。"""
    data = dict(h)
    data["trends"] = store.build_trends(h)
    data["used_ratio"] = store.used_ratio(h)
    data["available_credit"] = store.available_credit(h)
    data["next_repayment_date"] = store.next_repayment_date(h)
    return data


def _offline_answer(h: dict, question: str, sources: list) -> str:
    """无大模型时的抽取式答复：基于该民宿私有知识库片段组织答案。"""
    lines = [
        "根据您的专属知识库为您整理（仅检索本店资料，不涉及其他民宿）：",
        "",
    ]

    # 贷款/还款类问题：直接给出本店精确金额，演示多租户隔离效果
    loan_terms = ["还", "额度", "贷款", "授信", "利率", "逾期", "资金", "流水", "余额"]
    if any(t in question for t in loan_terms):
        lines.append(
            f"【您的贷款情况】{h.get('name')} 贷款金额 {int(h.get('loan_amount', 0)) / 10000:.1f} 万元，"
            f"已用额度 {int(h.get('loan_used', 0)) / 10000:.1f} 万元"
            f"（使用率 {store.used_ratio(h) * 100:.0f}%），剩余未偿还本金 "
            f"{int(h.get('loan_balance', 0)) / 10000:.1f} 万元；"
            f"{h.get('repayment_day')}还款，下期还款日为 {store.next_repayment_date(h)}，"
            f"下个月要还 {h.get('monthly_repayment')} 元。"
        )
        lines.append("")

    # 差评/卫生类问题
    if any(t in question for t in ["卫生", "差评", "评分", "投诉", "保洁", "布草"]):
        kw_top = "、".join(f"{k}（{v}次）" for k, v in store.negative_keywords(h, 3))
        lines.append(
            f"【您的舆情现状】当前 OTA 评分 {h.get('ota_score')} 分，近 7 日差评 "
            f"{(h.get('recent_reviews') or {}).get('bad_7d')} 条，高频关键词：{kw_top}。"
            "建议按《卫生差评整改五步法》执行：收集 → 归因 → 建表 → 执行 → 复核。"
        )
        lines.append("")

    # 定价/竞品类问题
    if any(t in question for t in ["定价", "价格", "房价", "竞品", "旺季", "淡季", "促销"]):
        lines.append(
            f"【您的定价参考】本店当前平均房价 {h.get('avg_price')} 元，入住率 "
            f"{float(h.get('current_occupancy', 0)) * 100:.0f}%。"
            "同区域竞品中端民宿挂牌价区间为 328~458 元，建议在 ±15% 内浮动；"
            "评分高于 4.6 可上浮 10%~15%，跌破 4.0 应先修复口碑再调价。"
        )
        lines.append("")

    for i, s in enumerate(sources, 1):
        lines.append(f"{i}. 【{s['source']}】{s['snippet']}")

    if sources:
        lines.append("")
        lines.append("📚 来源：" + "、".join(dict.fromkeys(s["source"] for s in sources)))
    lines.append("")
    lines.append("（当前为离线知识库模式：未配置 DASHSCOPE_API_KEY / DEEPSEEK_API_KEY，已自动降级为知识库抽取式答复。）")
    return "\n".join(lines)


# ---------------------------------------------------------------- 基础接口
@app.get("/", tags=["基础"], summary="服务首页")
async def root():
    return {
        "name": "豫宿巡 · 贷后风控与经营赋能 API",
        "docs": "/docs",
        "health": "/api/health",
        "note": "本系统只做贷后风控与经营赋能，不做预订、支付、客服聊天。",
    }


@app.get("/api/health", tags=["基础"], summary="健康检查")
async def health():
    return {
        "status": "ok",
        "llm": llm.provider("chat"),        # offline | qwen | deepseek | custom
        "vector": rag.backend_name(),       # chromadb | builtin
        "homestays": len(store.list_homestays()),
        "crawl": store.get_crawl_state(),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ---------------------------------------------------------------- 民宿
@app.get("/api/homestays", tags=["民宿"], summary="民宿列表")
async def list_homestays(
    city: str = Query(None, description="按城市过滤：洛阳/开封/安阳"),
    risk_level: str = Query(None, description="按风险等级过滤：red/amber/green"),
    keyword: str = Query(None, description="按关键词搜索：民宿名/地址/文化标签/差评关键词"),
):
    items = store.list_homestays()
    if city:
        items = [h for h in items if h.get("city") == city]
    if risk_level:
        items = [h for h in items if h.get("risk_level") == risk_level]
    if keyword:
        kw = keyword.strip()

        def _match(h):
            haystack = " ".join([
                h.get("name", ""),
                h.get("address", ""),
                " ".join(h.get("cultural_tags", []) or []),
                " ".join((h.get("keyword_counts") or {}).keys()),
            ])
            return kw in haystack

        items = [h for h in items if _match(h)]

    result = [_with_trends(h) for h in items]
    return {
        "list": result,
        "total": len(result),
        "summary": {
            "red": len([h for h in result if h.get("risk_level") == "red"]),
            "amber": len([h for h in result if h.get("risk_level") == "amber"]),
            "green": len([h for h in result if h.get("risk_level") == "green"]),
        },
    }


@app.get("/api/homestays/{homestay_id}", tags=["民宿"], summary="民宿详情（含 30 天趋势）")
async def get_homestay_detail(homestay_id: str):
    h = store.get_homestay(homestay_id)
    if not h:
        raise HTTPException(status_code=404, detail=f"民宿不存在：{homestay_id}")
    data = _with_trends(h)
    data["warnings"] = [w for w in store.list_warnings() if w.get("homestay_id") == h.get("id")]
    data["reports"] = store.list_reports(h.get("id"))
    return data


@app.get("/api/homestays/{homestay_id}/archive", tags=["民宿"], summary="民宿数字档案")
async def get_homestay_archive(homestay_id: str):
    h = store.get_homestay(homestay_id)
    if not h:
        raise HTTPException(status_code=404, detail=f"民宿不存在：{homestay_id}")
    return {
        "homestay": _with_trends(h),
        "trends": store.build_trends(h),
        "review_samples": h.get("review_samples", []),
        "keyword_counts": h.get("keyword_counts", {}),
        "reports": store.list_reports(h.get("id")),
        "knowledge_base": rag.collection_stats(h.get("id")),
    }


# ---------------------------------------------------------------- 预警
@app.get("/api/warnings", tags=["预警"], summary="预警列表")
async def list_warnings(
    status: str = Query(None, description="pending/processing/closed"),
    level: str = Query(None, description="red/amber"),
):
    items = store.list_warnings(status=status, level=level)
    return {"list": items, "total": len(items), "summary": store.warning_summary()}


@app.post("/api/warnings/trigger", tags=["预警"], summary="执行风控规则引擎")
async def trigger_warnings():
    return rules.run_rules()


@app.patch("/api/warnings/{warning_id}", tags=["预警"], summary="更新预警状态")
async def patch_warning(warning_id: str, body: WarningPatch):
    if body.status not in ("processing", "closed"):
        raise HTTPException(status_code=400, detail="status 仅支持 processing 或 closed")
    updated = store.update_warning_status(warning_id, body.status)
    if not updated:
        raise HTTPException(status_code=404, detail=f"预警不存在：{warning_id}")
    return {"ok": True, "warning": updated, "summary": store.warning_summary()}


@app.post("/api/warnings/ai-generate", tags=["预警"], summary="AI 自动生成预警（依据评分/评论/对话）")
async def ai_generate_warning(body: ReportBody):
    """由 AI 综合民宿评分、评论、经营数据与 AI 对话记录自动生成预警文案。"""
    try:
        return await rules.generate_ai_warning(body.homestay_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/api/warnings/{warning_id}/push", tags=["预警"], summary="下发预警至老板端")
async def push_warning(warning_id: str):
    updated = store.update_warning_fields(warning_id, {"pushed_to_app": True})
    if not updated:
        raise HTTPException(status_code=404, detail=f"预警不存在：{warning_id}")
    return {"ok": True, "warning": updated}


# ---------------------------------------------------------------- AI 经营助手（RAG）
@app.post("/api/chat", tags=["AI经营助手"], summary="AI 对话（RAG 私有知识库）")
async def chat(body: ChatBody):
    h = store.get_homestay(body.homestay_id)
    if not h:
        raise HTTPException(status_code=404, detail=f"民宿不存在：{body.homestay_id}")
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="question 不能为空")

    # 只在该民宿自己的 collection 内检索（多租户隔离）
    context, sources = rag.build_context(h.get("id"), body.question, top_k=4)

    mode = "offline"
    answer = ""
    if llm.provider("chat") != "offline":
        try:
            system = (
                "你是工行「豫宿巡」系统派驻民宿的 AI 经营助手，服务于民宿老板。"
                "你只能依据提供的资料回答，不得编造数据；若资料不足请明确说明。"
                "回答用中文，条理清晰，给出可执行建议，并在结尾以「📚 来源：」列出引用资料名称。"
            )
            user = (
                f"【本店资料（仅限本店，不得引用其他民宿数据）】\n"
                f"民宿：{h.get('name')}（{h.get('id')}，{h.get('city')}）\n"
                f"贷款金额 {h.get('loan_amount')} 元，已用 {h.get('loan_used')} 元，"
                f"下期还款日 {store.next_repayment_date(h)}，月还款 {h.get('monthly_repayment')} 元；"
                f"当前入住率 {h.get('current_occupancy')}，OTA 评分 {h.get('ota_score')}。\n\n"
                f"【检索到的知识片段】\n{context}\n\n"
                f"【老板的问题】{body.question}"
            )
            answer = await llm.chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.3, scene="chat",
            )
            mode = "llm"
        except llm.NoLLMConfigured:
            answer = ""
        except Exception as exc:
            # 不静默吞错：把可读原因记入模型管理页的出错提示，避免「配置了却悄悄降级」
            msg, status = llm._friendly_error(exc)
            llm._record_error("chat", msg, status)
            answer = ""

    if not answer:
        answer = _offline_answer(h, body.question, sources)
        mode = "offline"

    # 沉淀对话记录：作为该民宿专属 RAG 文档的一部分（多租户隔离）
    store.add_chat_history({
        "homestay_id": h.get("id"),
        "question": body.question,
        "answer": answer,
        "mode": mode,
    })

    return {
        "answer": answer,
        "sources": sources,
        "mode": mode,
        "homestay_id": h.get("id"),
        "homestay_name": h.get("name"),
    }


# ---------------------------------------------------------------- RAG 系统管理
@app.get("/api/rag/documents", tags=["RAG系统"], summary="RAG 文档库（公用 + 本店专属）")
async def rag_documents(homestay_id: str = Query(..., description="民宿 ID")):
    """清晰展示该民宿 RAG 检索用到的全部文档：公用知识 + 本店专属 + 自定义。"""
    return rag.list_documents(homestay_id)


@app.post("/api/rag/documents", tags=["RAG系统"], summary="新增 RAG 文档")
async def rag_add_document(body: RagDocBody):
    scope = body.scope if body.scope in ("public", "private") else "private"
    if scope == "private":
        if not body.homestay_id:
            raise HTTPException(status_code=400, detail="本店专属文档必须指定 homestay_id")
        if not store.get_homestay(body.homestay_id):
            raise HTTPException(status_code=404, detail=f"民宿不存在：{body.homestay_id}")
    homestay_id = "" if scope == "public" else body.homestay_id
    doc = store.add_rag_doc({
        "homestay_id": homestay_id,
        "title": (body.title or "").strip() or "未命名文档",
        "content": body.content or "",
        "doc_type": body.doc_type or "custom",
        "tags": body.tags or [],
        "scope": scope,
        "source": "人工维护",
    })
    rag.invalidate(homestay_id or None)
    return {"doc": doc, "library": rag.list_documents(body.homestay_id) if body.homestay_id else None}


@app.patch("/api/rag/documents/{doc_id}", tags=["RAG系统"], summary="修改 RAG 文档")
async def rag_update_document(doc_id: str, body: RagDocPatch):
    patch = body.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")
    doc = store.update_rag_doc(doc_id, patch)
    if not doc:
        raise HTTPException(status_code=404, detail=f"文档不存在或不可修改：{doc_id}")
    hid = doc.get("homestay_id") or ""
    rag.invalidate(hid or None)
    return {"doc": doc, "library": rag.list_documents(hid) if hid else None}


@app.delete("/api/rag/documents/{doc_id}", tags=["RAG系统"], summary="删除 RAG 文档")
async def rag_delete_document(doc_id: str):
    doc = store.get_rag_doc(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"文档不存在：{doc_id}")
    store.delete_rag_doc(doc_id)
    hid = doc.get("homestay_id") or ""
    rag.invalidate(hid or None)
    return {"ok": True, "deleted": doc_id, "library": rag.list_documents(hid) if hid else None}


@app.post("/api/rag/crawl", tags=["RAG系统"], summary="采集各平台评论写入 RAG 文档库")
async def rag_crawl(body: CrawlBody):
    """每日定时采集：模拟抓取各平台对该民宿的评价，沉淀为专属 RAG 文档。"""
    if body.homestay_id:
        try:
            result = rag.simulate_crawl(body.homestay_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return {
            "created": 1,
            "doc": result["doc"],
            "state": result["state"],
            "library": rag.list_documents(body.homestay_id),
        }
    return rag.crawl_all()


# ---------------------------------------------------------------- 模型管理
@app.get("/api/models", tags=["模型管理"], summary="AI 场景模型配置总览")
async def get_models():
    """返回各 AI 场景（对话/报告/预警/文案）当前使用的模型、Base URL 与 Key 脱敏信息。"""
    return llm.describe()


@app.post("/api/models", tags=["模型管理"], summary="保存 AI 场景模型配置")
async def save_models(body: ModelSaveBody):
    """按场景保存模型配置，运行期立即生效（api_key 留空表示沿用旧值）。"""
    return llm.save_scenes(body.scenes)


@app.post("/api/models/test", tags=["模型管理"], summary="测试 AI 场景模型连通性")
async def test_model(body: ModelTestBody):
    """对指定场景发起一次最小真实请求，返回上游的真实报错（如 401 / 404）。

    用于确认「模型管理」里配置的模型与 Key 是否真正生效，避免静默降级。
    """
    return await llm.test_connection(body.scene)


@app.post("/api/models/available", tags=["模型管理"], summary="获取场景可用模型列表")
async def available_models(body: ModelListBody):
    """调用提供方官方的「模型列表」接口，返回当下真正可用的模型名。

    模型名会随官方版本迭代变化，直接拉取可避免手写模型名过期导致的 404。
    """
    return await llm.list_models(body.scene, body.keyword)


# ---------------------------------------------------------------- AI 巡检报告
@app.post("/api/report/generate", tags=["巡检报告"], summary="生成 AI 巡检报告")
async def generate_report(body: ReportBody):
    try:
        return await report_service.generate_report(body.homestay_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/reports", tags=["巡检报告"], summary="历史报告列表")
async def list_reports(homestay_id: str = Query(None, description="按民宿过滤")):
    items = store.list_reports(homestay_id)
    return {"list": items, "total": len(items)}


@app.get("/api/reports/{report_id}", tags=["巡检报告"], summary="报告详情")
async def get_report_detail(report_id: str):
    report = store.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"报告不存在：{report_id}")
    return report


@app.post("/api/reports/push", tags=["巡检报告"], summary="下发巡检报告至老板端")
async def push_report(body: ReportPushBody):
    report = store.get_report(body.report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"报告不存在：{body.report_id}")
    updated = store.update_report_fields(body.report_id, {
        "pushed_to_app": True,
        "pushed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    return {"ok": True, "report": updated}


# ---------------------------------------------------------------- 消息中心（老板 ⇄ 银行客户经理）
@app.get("/api/messages", tags=["消息中心"], summary="拉取消息（可按民宿过滤，时间正序）")
async def list_messages(homestay_id: str = Query(None, description="民宿 ID，缺省返回全部")):
    return store.list_messages(homestay_id)


@app.get("/api/messages/bank/unread", tags=["消息中心"], summary="银行端未读角标（老板发来未读条数）")
async def bank_unread():
    return {"count": store.unread_message_count("owner")}


@app.post("/api/messages", tags=["消息中心"], summary="发送消息（老板或银行）")
async def send_message(body: MessageBody):
    h = store.get_homestay(body.homestay_id)
    if not h:
        raise HTTPException(status_code=404, detail=f"民宿不存在：{body.homestay_id}")
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="消息内容不能为空")
    if body.sender not in ("owner", "bank"):
        raise HTTPException(status_code=422, detail="sender 仅支持 owner / bank")
    # 收到对方新消息后，把已读标记重新置为 False，便于未读角标提示
    return store.send_message(h.get("id"), body.sender, text[:500])


@app.post("/api/messages/read", tags=["消息中心"], summary="标记某民宿（或全部）老板消息已读")
async def read_messages(body: MessageReadBody):
    n = store.mark_messages_read(body.homestay_id or None, "owner")
    return {"marked": n}


# ---------------------------------------------------------------- AI 文创
@app.get("/api/creative/styles", tags=["AI文创"], summary="文创生图样式库 + 文案风格")
async def creative_styles(homestay_id: str = Query(None, description="民宿 ID（用于生成样式封面）")):
    """返回生图样式墙（含封面，提示词不下发）与文案风格列表。"""
    return {
        "styles": creative.list_styles(homestay_id),
        "copy_styles": creative.COPY_STYLES,
    }


@app.post("/api/creative/style-generate", tags=["AI文创"], summary="按样式生成文创图片")
async def creative_style_generate(body: StyleGenBody):
    """按选中的样式生成图片；样式提示词由后端持有，不对老板展示。"""
    if not store.get_homestay(body.homestay_id):
        raise HTTPException(status_code=404, detail=f"民宿不存在：{body.homestay_id}")
    result = await creative.generate_by_style(body.homestay_id, body.style_key, body.count, body.image_url)
    # 产物按民宿持久化，仅本店老板可在「我的 → AI 文创产物」中查看
    store.add_creative_work({
        "homestay_id": result.get("homestay_id"),
        "type": "image",
        "style_key": body.style_key,
        "source": "style",
        "title": result.get("style_title") or "文创图片",
        "image_urls": result.get("image_urls") or [],
        "provider": result.get("provider"),
        "mode": "llm" if result.get("provider") not in (None, "", "fallback_url") else "offline",
    })
    return result


@app.post("/api/creative/copywriting", tags=["AI文创"], summary="根据民宿信息生成宣传文案")
async def creative_copywriting(body: CopywritingBody):
    try:
        result = await creative.generate_copywriting(body.homestay_id, body.requirement, body.style)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    store.add_creative_work({
        "homestay_id": result.get("homestay_id"),
        "type": "copy",
        "style": result.get("style"),
        "title": result.get("style_name") or "宣传文案",
        "content": result.get("content") or "",
        "mode": result.get("mode") or "offline",
    })
    return result


@app.post("/api/creative/generate", tags=["AI文创"], summary="生成文创图片")
async def creative_generate(body: CreativeBody):
    if not store.get_homestay(body.homestay_id):
        raise HTTPException(status_code=404, detail=f"民宿不存在：{body.homestay_id}")
    result = await creative.generate_images(body.homestay_id, body.theme, body.count)
    store.add_creative_work({
        "homestay_id": result.get("homestay_id"),
        "type": "image",
        "source": "custom",
        "title": (body.theme or "").strip() or "文创图片",
        "image_urls": result.get("image_urls") or [],
        "provider": result.get("provider"),
        "mode": "llm" if result.get("provider") not in (None, "", "fallback_url") else "offline",
    })
    return result


@app.get("/api/creative/works", tags=["AI文创"], summary="查询本店 AI 文创产物历史")
async def creative_works(homestay_id: str = Query("", description="民宿 ID；为空返回全部民宿")) -> dict:
    """返回该民宿老板生成的文创产物（图片 + 文案），按时间倒序。"""
    return {"works": store.list_creative_works(homestay_id or None)}


@app.post("/api/creative/vectorize", tags=["AI文创"], summary="图片矢量化（PNG → SVG）")
async def creative_vectorize(body: VectorizeBody):
    try:
        return creative.vectorize(body.image_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------- 登录注册
@app.post("/api/auth/register", tags=["认证"], summary="注册（民宿老板）")
async def register(body: RegisterBody):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少 6 位")
    if store.find_user(body.username):
        raise HTTPException(status_code=400, detail=f"用户名已存在：{body.username}")
    if body.homestay_id and not store.get_homestay(body.homestay_id):
        raise HTTPException(status_code=400, detail=f"民宿不存在：{body.homestay_id}")

    user = {
        "username": body.username,
        "password": body.password,  # 演示用明文，生产环境必须加盐哈希存储
        "name": body.name or body.username,
        "phone": body.phone,
        "homestay_id": body.homestay_id or "LY001",
        "role": "owner",
        "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    store.add_user(user)
    return {"token": _make_token(user["username"]), "user": _public_user(user)}


@app.post("/api/auth/login", tags=["认证"], summary="登录")
async def login(body: LoginBody):
    user = store.find_user(body.username)
    if not user:
        raise HTTPException(status_code=400, detail="用户名不存在，请先注册")
    if user.get("password") != body.password:
        raise HTTPException(status_code=400, detail="密码错误，请重新输入")
    homestay = store.get_homestay(user.get("homestay_id"))
    return {
        "token": _make_token(user["username"]),
        "user": _public_user(user),
        "homestay": {
            "id": homestay.get("id"),
            "name": homestay.get("name"),
            "city": homestay.get("city"),
            "risk_level": homestay.get("risk_level"),
        } if homestay else None,
    }


# ---------------------------------------------------------------- 贷后驾驶舱
@app.get("/api/dashboard", tags=["驾驶舱"], summary="贷后驾驶舱数据")
async def dashboard():
    homestays = store.list_homestays()
    warnings = store.list_warnings()
    total = len(homestays) or 1

    red_list = [h for h in homestays if h.get("risk_level") == "red"]
    amber_list = [h for h in homestays if h.get("risk_level") == "amber"]
    green_list = [h for h in homestays if h.get("risk_level") == "green"]

    kpi = {
        "total_homestays": len(homestays),
        "red": len(red_list),
        "amber": len(amber_list),
        "green": len(green_list),
        "total_loan_amount": sum(int(h.get("loan_amount", 0) or 0) for h in homestays),
        "total_loan_used": sum(int(h.get("loan_used", 0) or 0) for h in homestays),
        "total_loan_balance": sum(int(h.get("loan_balance", 0) or 0) for h in homestays),
        "avg_occupancy": round(sum(float(h.get("current_occupancy", 0)) for h in homestays) / total, 3),
        "avg_ota": round(sum(float(h.get("ota_score", 0)) for h in homestays) / total, 2),
        "warning_count": len(warnings),
        "pending_warnings": len([w for w in warnings if w.get("status") == "pending"]),
    }

    # 分城市统计
    by_city = []
    for city in ["洛阳", "开封", "安阳"]:
        group = [h for h in homestays if h.get("city") == city]
        if not group:
            continue
        by_city.append({
            "city": city,
            "count": len(group),
            "loan_amount": sum(int(h.get("loan_amount", 0) or 0) for h in group),
            "loan_balance": sum(int(h.get("loan_balance", 0) or 0) for h in group),
            "red": len([h for h in group if h.get("risk_level") == "red"]),
            "amber": len([h for h in group if h.get("risk_level") == "amber"]),
            "green": len([h for h in group if h.get("risk_level") == "green"]),
        })

    risk_distribution = [
        {"name": "高风险", "value": len(red_list)},
        {"name": "中风险", "value": len(amber_list)},
        {"name": "低风险", "value": len(green_list)},
    ]

    # 今日待办：按风险等级 + 贷款余额排序，附触发规则
    order = {"red": 0, "amber": 1, "green": 2}
    todos = []
    for h in sorted(homestays, key=lambda x: (order.get(x.get("risk_level"), 9), -int(x.get("loan_balance", 0) or 0))):
        related = [w for w in warnings if w.get("homestay_id") == h.get("id") and w.get("status") != "closed"]
        todos.append({
            "id": h.get("id"),
            "name": h.get("name"),
            "city": h.get("city"),
            "owner_name": (h.get("owner") or {}).get("name"),
            "owner_phone": (h.get("owner") or {}).get("phone"),
            "risk_level": h.get("risk_level"),
            "risk_reason": h.get("risk_reason"),
            "rule_ids": sorted({w.get("rule_id") for w in related}),
            "warning_count": len(related),
            "loan_balance": h.get("loan_balance"),
            "occupancy": h.get("current_occupancy"),
            "ota_score": h.get("ota_score"),
            "last_inspection": h.get("last_inspection"),
            "suggestion": related[0].get("suggestion") if related else "",
        })

    map_points = [{
        "id": h.get("id"),
        "name": h.get("name"),
        "city": h.get("city"),
        "lat": (h.get("location") or {}).get("lat"),
        "lng": (h.get("location") or {}).get("lng"),
        "risk_level": h.get("risk_level"),
        "loan_balance": h.get("loan_balance"),
        "occupancy": h.get("current_occupancy"),
        "ota_score": h.get("ota_score"),
    } for h in homestays]

    # ---------- 驾驶舱增强：组合指标 / 全辖趋势 / 高风险清单 / 城市对比 ----------
    total_amount = kpi["total_loan_amount"] or 1
    loan_utilization = round(kpi["total_loan_used"] / total_amount, 4)
    # 组合健康度：绿 100 / 黄 60 / 红 25 加权平均
    portfolio_health = round(
        (len(green_list) * 100 + len(amber_list) * 60 + len(red_list) * 25) / total, 1
    )
    # 未来 30 天预计应收回款（月还款额合计）
    monthly_repayment_total = sum(int(h.get("monthly_repayment", 0) or 0) for h in homestays)

    # 全辖 30 天经营趋势（各店均值）
    trend_sets = [store.build_trends(h) for h in homestays]
    trend_dates, occ_trend, rev_trend = [], [], []
    if trend_sets:
        trend_dates = trend_sets[0]["dates"]
        n = len(trend_dates)
        for i in range(n):
            occ_trend.append(round(sum(t["occupancy"][i] for t in trend_sets) / len(trend_sets), 3))
            rev_trend.append(int(sum(t["revenue"][i] for t in trend_sets) / len(trend_sets)))

    # 高风险清单（按剩余本金降序）
    top_risk = sorted(
        [{
            "id": h.get("id"),
            "name": h.get("name"),
            "city": h.get("city"),
            "risk_level": h.get("risk_level"),
            "risk_reason": h.get("risk_reason"),
            "loan_balance": h.get("loan_balance"),
            "loan_amount": h.get("loan_amount"),
            "occupancy": h.get("current_occupancy"),
            "ota_score": h.get("ota_score"),
            "flow_drop_30d": h.get("flow_drop_30d"),
            "keyword_counts": h.get("keyword_counts"),
        } for h in homestays if h.get("risk_level") == "red"],
        key=lambda x: -int(x.get("loan_balance", 0) or 0),
    )[:6]

    # 城市风险对比（含风险指数）
    city_metrics = []
    for c in by_city:
        group = [h for h in homestays if h.get("city") == c["city"]]
        cnt = max(len(group), 1)
        city_metrics.append({
            "city": c["city"],
            "count": c["count"],
            "loan_balance": c["loan_balance"],
            "avg_ota": round(sum(float(h.get("ota_score", 0)) for h in group) / cnt, 2),
            "avg_occupancy": round(sum(float(h.get("current_occupancy", 0)) for h in group) / cnt, 3),
            "risk_index": round((c["red"] * 100 + c["amber"] * 55 + c["green"] * 20) / cnt, 1),
        })

    return {
        "kpi": kpi,
        "by_city": by_city,
        "risk_distribution": risk_distribution,
        "todos": todos,
        "map_points": map_points,
        "warning_summary": store.warning_summary(),
        "enhanced": {
            "loan_utilization": loan_utilization,
            "portfolio_health": portfolio_health,
            "monthly_repayment_total": monthly_repayment_total,
            "avg_ota": kpi["avg_ota"],
            "trend": {"dates": trend_dates, "occupancy": occ_trend, "revenue": rev_trend},
            "top_risk": top_risk,
            "city_metrics": city_metrics,
        },
        "crawl": store.get_crawl_state(),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


if __name__ == "__main__":
    import uvicorn

    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
