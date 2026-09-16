# -*- coding: utf-8 -*-
"""
口语素材周刊 · 核心数据模型 (Pydantic v2)
严格遵循 CURRENT_REQUIREMENTS.md 与重构任务书 v1.0：
- 观点池 learning.viewpoints 可以有任意多个有区别的方向（不限两个）；
- 口语范本 speech.body 严格限定为两个主体段，每个段落有独立的小观点（claim）。
"""
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# ==============================================================================
# 1. 来源与资料包模型
# ==============================================================================

class SourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: str = "1.0"
    source_id: str = Field(..., description="稳定的文档唯一标识，如 src-ttzl-45288")
    media: str = Field(..., description="媒体名称")
    title: str = Field(..., description="原文标题")
    url: str = Field(..., description="原始链接")
    doc_type: Literal["report", "commentary", "award", "mixed", "unknown"] = "report"
    published_at: Optional[str] = Field(None, description="原始报道发表时间 (YYYY-MM-DD)")
    event_at: Optional[str] = Field(None, description="真实事件发生时间")
    award_at: Optional[str] = Field(None, description="获奖/公示时间")
    fetched_at: str = Field(..., description="抓取留档时间 ISO 字符串")
    content: str = Field(..., description="清洗后的正文完整内容")
    paragraphs: List[str] = Field(default_factory=list, description="正文分段列表")
    content_hash: str = Field(..., description="正文哈希（去空白 sha1）")
    status: Literal["complete", "summary", "supplement", "unknown"] = "complete"


class EventPacket(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: str = "1.0"
    packet_id: str = Field(..., description="稳定的事件包ID，如 pkt-2026-dan-jiao-xie")
    legacy_event_id: Optional[str] = Field(None, description="关联的旧版雷达事件ID哈希别名")
    title: str = Field(..., description="事件核心标题")
    source_ids: List[str] = Field(default_factory=list, description="引用的来源文档ID列表")
    core_facts: List[str] = Field(default_factory=list, description="客观核实的关键事实列表")
    quotes: List[str] = Field(default_factory=list, description="当事人或采访原话")
    timeline: List[str] = Field(default_factory=list, description="时间线节点")
    gaps: List[str] = Field(default_factory=list, description="信息缺口与未证实处")
    relevant_commentaries: List[str] = Field(default_factory=list, description="相关媒体评论要点或引用")


# ==============================================================================
# 2. 复述单元模型 (RetellingUnit)
# ==============================================================================

class MindmapLeaf(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str
    hint: str = Field(..., description="填空大框提示词/分类")
    answer: str = Field(..., description="完整参考答案内容")
    fact_refs: List[str] = Field(default_factory=list, description="对应材料事实依据")


class MindmapBranch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(..., description="主枝分类名称")
    leaves: List[MindmapLeaf] = Field(default_factory=list, description="下属待填叶节点")


class MindmapTree(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    center: str = Field(..., description="中心主题")
    branches: List[MindmapBranch] = Field(default_factory=list, description="思维导图主枝")


class RetellingUnit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: str = "1.0"
    id: str = Field(..., description="单元ID，如 R01, R02")
    category: Literal["社会热点", "暖文", "正向社会生活"] = "社会热点"
    packet_ref: Optional[str] = Field(None, description="引用的事件资料包ID")
    title: str = Field(..., description="材料标题")
    date_label: str = Field(..., description="时间标签，如 8月21日")
    source_label: str = Field(..., description="来源标注，如 合肥晚报 2026-08-25")
    material_paragraphs: List[str] = Field(..., description="新闻事实正文段落（事实为主，中性讲述）")
    keywords: List[str] = Field(default_factory=list, description="关键词网络节点")
    mindmap_tree: MindmapTree = Field(..., description="结构化分枝思维导图")
    ref_retelling: str = Field(..., description="集中参考复述文本（以事实为主）")
    mapkey: str = Field(..., description="导图参照文字")
    illustration_id: Optional[str] = Field(None, description="插画编号，如 ILL-R01")
    illustration_brief: Optional[str] = Field(None, description="插画需求描述")


# ==============================================================================
# 3. 评论单元模型 (CommentaryUnit) —— 观点池与范本严格解耦
# ==============================================================================

class ViewpointItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(..., description="观点编号，如 v1, v2")
    claim: str = Field(..., description="具体明确的判断，绝非仅关键词或空泛口号")
    evidence: str = Field(..., description="该判断在材料中的事实依据与出处")
    explanation: Optional[str] = Field(None, description="对该观点的简要补充说明")


class ReasoningLesson(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(..., description="推演主题，如 抓反差看成因 / 抓细节看深度")
    target_viewpoint_ids: List[str] = Field(default_factory=list, description="关联推导的观点ID列表")
    deduction_text: str = Field(..., description="细致的因果推演与处境还原过程，拒绝跳步")


class SpeechBodyParagraph(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(..., description="主体段编号，如 b1, b2")
    claim: str = Field(..., description="该段开头亮出的小观点（证明或解释什么）")
    paragraphs: List[str] = Field(..., description="围绕该小观点的论述理由与必要事实")


class LearningBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    recap_facts: List[str] = Field(..., description="材料回想核心事实（不提前剧透结论）")
    questions: List[str] = Field(..., description="具体有启发的思考问题（入口思考）")
    baseline_diagnostic: Optional[str] = Field(None, description="初步直觉与教学诊断")
    # 核心教学约束：观点池可以有任意多个方向（支持2, 5, 7条等），不限两个！
    viewpoints: List[ViewpointItem] = Field(..., description="多角度观点参考池")
    reasoning_lessons: List[ReasoningLesson] = Field(..., description="拆开讲：一至两处重点耐心推演")

    @field_validator("viewpoints")
    @classmethod
    def validate_viewpoints_count(cls, v):
        if len(v) < 2:
            raise ValueError(f"观点池至少需要提供 2 个不同方向的观点，当前仅有 {len(v)} 个")
        return v


class SpeechBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    selected_viewpoint_ids: List[str] = Field(default_factory=list, description="范本选定的观点主线ID")
    main_claim: str = Field(..., description="开头两三句话，亮明具体总判断，统领全文")
    # 核心教学约束：最终口语范本严格限定为恰好 2 个主体段展开！
    body: List[SpeechBodyParagraph] = Field(..., description="两个有不同增量的主体段")
    closing: str = Field(..., description="结尾单独成段收束，回到主线")

    @field_validator("body")
    @classmethod
    def validate_body_count(cls, v):
        if len(v) != 2:
            raise ValueError(f"最终口语范本必须且只能由 2 个主体段展开，当前提供了 {len(v)} 段")
        return v


class DeconstructionItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    target: str = Field(..., description="拆解对象，如 【开头亮剑统领】或【主体一立足细节】")
    instruction: str = Field(..., description="具体的论证方法说明与教学解析")


class TeachingBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    spine: str = Field(..., description="全文主线组织结构说明")
    deconstruction: List[DeconstructionItem] = Field(..., description="教学拆解要点")
    editor_notes: Optional[str] = Field(None, description="教师/编辑内部备注（不进学生版）")


class CommentaryUnit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: str = "1.0"
    id: str = Field(..., description="评论单元ID，如 C01, C02")
    retelling_ref: str = Field(..., description="对应的复述单元ID，如 R01")
    packet_ref: Optional[str] = Field(None, description="引用的事件资料包ID")
    title: str = Field(..., description="评论标题")
    learning: LearningBlock = Field(..., description="第1页问题与第2页多观点推演")
    speech: SpeechBlock = Field(..., description="第3页口语范本（双主体段）")
    teaching: TeachingBlock = Field(..., description="第3页拆解与教学指导")
    legacy_unreviewed: bool = Field(False, description="标记是否为旧版未经多观点重构的过渡稿")

    def get_spoken_paragraphs(self) -> List[str]:
        """返回规范化拼装的口语范本各段文本（开头总论、主体段落包含分论点、结尾独立收束）"""
        paras = []
        if self.speech.main_claim and self.speech.main_claim.strip():
            paras.append(self.speech.main_claim.strip())
        for b in self.speech.body:
            claim_clean = b.claim.strip()
            for idx, p in enumerate(b.paragraphs):
                p_clean = p.strip()
                if idx == 0:
                    if not p_clean.startswith(claim_clean):
                        paras.append(f"{claim_clean} {p_clean}")
                    else:
                        paras.append(p_clean)
                else:
                    paras.append(p_clean)
        if self.speech.closing and self.speech.closing.strip():
            paras.append(self.speech.closing.strip())
        return paras

    def get_full_spoken_text(self) -> str:
        """返回用于口语字数统计与朗读评测的完整连续文本"""
        return "".join(self.get_spoken_paragraphs())


# ==============================================================================
# 4. 原文拆解与积累单元模型 (ExcerptUnit)
# ==============================================================================

class ExcerptUnit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: str = "1.0"
    id: str = Field(..., description="拆解单元ID，如 F01, F02")
    topic: str = Field(..., description="拆解主题，如 低保装空调背后的治理温度")
    source_name: str = Field(..., description="媒体名称，如 新京报·快评")
    source_date: str = Field(..., description="发表日期，如 2026-08-15")
    source_url: Optional[str] = Field(None, description="原文链接")
    context: str = Field(..., description="前因后果与事件背景")
    quote_paragraphs: List[str] = Field(..., description="真实原文摘录段落")
    analyze: str = Field(..., description="重点拆解：作者为何这样论述、因果推演机制")
    memorize: Optional[str] = Field(None, description="值得记住的表达")
    method: Optional[str] = Field(None, description="可以借鉴的讲法")
    demo_title: str = Field(..., description="示范小标题，如 示范｜谈……，可以这样说")
    demo_text: str = Field(..., description="一段已经说成的口语表达示范")
    demo_is_hypothetical: bool = Field(False, description="该示范是否为教学假设案例（尊重真实案例）")


# ==============================================================================
# 5. 期刊清单模型 (IssueManifest)
# ==============================================================================

class BuildConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    pdf_render_timeout_ms: int = 10000
    font_family_serif: str = '"Songti SC", "STSong", "SimSun", serif'
    font_family_sans: str = '"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif'
    font_family_kaiti: str = '"Kaiti SC", "STKaiti", serif'
    min_font_size_pt: float = 9.0


class IssueManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: str = "1.0"
    issue_id: str = Field(..., description="期刊期号ID，如 sample-01-rev5")
    title: str = Field(..., description="刊名，如 口语素材周刊")
    kicker: str = "高中播音艺考口语素材周刊"
    issue_no_label: str = Field(..., description="期号显示，如 试刊 · 第 0 期")
    date_range: str = Field(..., description="本期素材时间范围")
    retelling_ids: List[str] = Field(..., description="入选复述单元ID列表")
    commentary_ids: List[str] = Field(..., description="入选评论单元ID列表")
    excerpt_ids: List[str] = Field(..., description="入选原文摘录单元ID列表")
    ai_prompt_path: Optional[str] = Field("ai-retelling-prompt.txt", description="AI陪练提示词路径")
    build_config: BuildConfig = Field(default_factory=BuildConfig)
