/* 暖文雷达 — 分类表集中配置 v0.2.1
 * 所有枚举集中在这里维护，后端/前端/提示词统一引用，避免多处各写一套。
 * 修改分类表后应递增 taxonomyVersion，并用「按版本重分析」命令按需重跑。
 */

export const TAXONOMY_VERSION = '0.2.1';

/** 事件母题：描述"发生了什么类型的事件"（由模型阅读完整正文后判断，允许"其他"） */
export const EVENT_MOTIFS = [
  '水域救援', '火灾与险情救援', '道路交通救援', '医疗急救', '高空坠落或建筑险情救援',
  '应急救灾', '长期助学与陪伴', '困境成长', '技能助人', '适老服务', '助残与无障碍',
  '公益空间', '爱心餐食', '邻里长期守望', '职业岗位善意', '诚信与归还', '其他',
];

/** 社会关联/讨论主题：事件可以联系讨论的公共议题（用于筛选与统计，允许为空） */
export const SOCIAL_TOPICS = [
  '职业教育', '青年成长', '儿童监护', '适老服务', '公共服务', '无障碍', '职业责任',
  '社区互助', '规则与温度', '陌生人信任', '城乡关系', '公益可持续', '科技向善',
];

/** 行为类别（沿用天天正能量类目体系） */
export const BEHAVIOR_CATEGORIES = [
  '英勇救人', '助人为乐', '诚实守信', '敬业奉献', '自立自强', '孝老爱亲', '温情互助', '其他',
];

/** 材料价值 / 信息成熟度 */
export const MATERIAL_VALUES = ['高', '中', '低'];
export const INFO_MATURITIES = ['完整', '待补充', '线索'];

/** 信息缺口重要程度：只有 critical 影响"信息成熟度"与"优先补搜" */
export const GAP_IMPORTANCE = ['critical', 'optional'];

/** 建议用途（由代码根据 价值×成熟度 组合，模型不直接输出） */
export const USES = ['完整加工', '优先补搜', '短复述或案例', '继续观察', '暂时不用'];

export const USE_PRIORITY = { 完整加工: 0, 优先补搜: 1, 短复述或案例: 2, 继续观察: 3, 暂时不用: 4 };

/** 规则与提示词版本（写入每条 AI 分析记录，便于按版本重分析与对比） */
export const ANALYSIS_RULES_VERSION = '0.2.1';
export const PROMPT_VERSION = '2026-09-04.1';

/** 材料价值 × 信息成熟度 → 建议用途（代码组合，稳定规则） */
export function computeSuggestedUse(materialValue, infoMaturity, hasCriticalGap = false) {
  const gap = hasCriticalGap ? '待补充' : infoMaturity;
  if (materialValue === '低') return '暂时不用';
  if (materialValue === '高') {
    if (gap === '完整') return '完整加工';
    if (gap === '待补充') return '优先补搜';
    return '继续观察';
  }
  if (gap === '完整') return '短复述或案例';
  return '继续观察';
}
