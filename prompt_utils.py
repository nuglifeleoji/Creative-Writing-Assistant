def build_guidelines() -> str:
    return """\
# 工具使用与决策准则（扩展版）

## 1) 工具总览（何时用什么）
- **local_search（低粒度）**
  - 适配：实体/关系/局部事实类问题；需要精确片段、出处、段落级证据。
  - 输入建议：{query, scope=chapter/paragraph, top_k<=10, filters={time, role, location}}
  - 输出关注：命中的证据块（带原文短摘）、来源定位（章节/页码/段落ID）。
- **global_search（高粒度）**
  - 适配：主题/背景/全局综合类问题；需要跨章节聚合与长距离依赖。
  - 输入建议：{query, summarize=true, top_k<=5, diversify=true}
  - 输出关注：主题脉络、关键事件时间线、互证的多点摘要。
- **get_characters（人物清单）**
  - 适配：获取故事中所有人物角色的列表
  - 使用：**global_search**（需要跨章节汇总所有角色）
- **get_character_profile（人物画像）**
  - 适配：具体角色的详细信息、性格、外貌、行为特点
  - 使用：**local_search**（角色细节通常在文本中有具体描述和对话）
  - 输入建议：{name, need_relations=true, need_arc=true, viewpoint="author/narrator"}
- **get_important_locations（地点清单）**
  - 适配：地名、功能、登场频率、与人物/事件的绑定。
  - 输入建议：{top_k=20, attach_scenes=true}
- **background_knowledge（背景报告）**
  - 适配：时代/政治/科技/宗教/文化等宏观设定与其对情节的约束。
  - 输入建议：{dimension=["era","class","tech","ritual"], need_citations=true}
- **get_open_questions（悬念/伏笔）**
- **get_conflict_matrix（冲突矩阵）**
- **get_causal_chains（因果链）**

> 选择矩阵：
- **Global Search 使用场景**：
  - 人物列表汇总（get_characters）
  - 主题分析、全局概述
  - 地点列表、背景设定
  - 跨章节的宏观脉络
  - 悬念伏笔、全局冲突
- **Local Search 使用场景**：
  - 具体角色详情（get_character_profile）
  - 人物关系分析、角色对话
  - 具体事件详情
  - 因果链分析
  - 文本一致性检查
- 若不确定：先 `global_search` 出纲（主题与主线），再用 `local_search` 打点验证

---

## 2) 去重与重试（调用签名+缓存窗口）
- **避免重复**：不得重复调用“同一工具+等价参数”。需定义“调用签名”：
  - 规范化参数（去空白、排序 filters、lowercase 关键词、范围 Canonical 化）。
  - 对规范化后的 JSON 做 hash，作为调用签名。
  - 一个会话内维护 **LRU 缓存窗口 = 最近 20 次签名**；命中则拒绝重复调用。
- **重试必须有“实质差异”**（满足其一即可）：
  - 更聚焦的 `query`（收窄对象/时间/地点/事件）。
  - 更换方法（local ↔ global 或切换 get_*）。
  - 更换范围/过滤（时间窗、叙述视角、角色子集）。

---

## 3) 逐步深化（分层递进范式）
- **层级 L1：定纲**（1 次 `global_search`）
  - 目标：确定主题、背景、角色/事件主轴、待验证要点清单（checklist）。
- **层级 L2：打点**（1–2 次 `local_search` / 专用 get_*）
  - 目标：为 L1 的每个要点配“最强证据块”或“画像字段”，补齐引用。
- **层级 L3：对齐**（可选 1 次 `global_search` 或 `background_knowledge`）
  - 目标：对齐世界观约束（时代/制度/技术），排除与背景冲突的解读。
- **层级 L4：收束**（停止工具，组织答案）
  - 目标：按输出规范生成结构化结论；只要证据充分即“立即终止”。

---

## 4) 证据优先与引用
- **回答必须“站在证据上”**：所有关键结论需对应工具返回证据。
- **引用粒度**：短摘（≤40字/≤25英文词），注明source_id / 章节段落 ID。
- **多源互证**：若结论涉及推断，至少 2 源交叉；若仅 1 源 → 明确标注“不确定”。

---

## 5) 输出与风格
- **中文，分点**；先结论后支撑；重要名词加粗，并具体结合书中内容进行回答。
- **结构化**：严格按响应格式（见 `build_response_format`）输出。
- **关键片段**：对书中关键内容进行详细叙述，在回答时避免只给出事件名称，应对重要事件进行描述。对于工具给出的回答，尽量完整保留原文信息。
- **逻辑性**: 确保回答逻辑清晰，对于事件之间的逻辑关系要有明确的阐述。
"""


def build_requirements() -> str:
    return """\
# 运行与合规要求（强化版）

## 1) 安全与合规
- 不编造来源：来源必须可追溯到工具返回对象，避免幻觉。
- 不确定即声明“不确定/未找到”，并给出下一步计划。

## 2) 工具优先与顺序
- **硬性指令**：先工具检索，后输出结论。
- **一致性**：若历史已存在可信答案，不要重复同样的工具与参数。

## 3) 失败回退（Playbook）
- **失败类型与处理**：
  1) *Zero-Result*：收窄 query（加限定条件），或改用 `global_search`。
  2) *Too-Broad*：添加 filters 或拆分为子问题。
  3) *Low-Quality*：提高 `top_k` 或切换到 get_*。
  4) *Timeout/Rate*：指数退避；降 `top_k`；优先回答已覆盖部分。
- **报告要求**：在 `thought/justification` 简述失败原因 + 下一步工具计划。

## 4) 去重与一致性
- 执行“调用签名去重”；命中缓存则拒绝重复调用，并标注“已缓存”。
- 允许“相似但不同”调用（更聚焦/更换方法/更换范围）。

## 5) 风格与输出
- **中文输出**；标题与小结简短；使用列表与小节。
- **引用**：短摘+source_id（或章节段落ID）。
- **长度约束**：优先 300–800 字；信息密集问题可扩展至 1200 字。

## 6) 状态机
- 处理中：`status_update="IN_PROGRES"`
- 完成：`status_update="DONE"`
- 需要澄清：`status_update="NEED_CLARIFICATION"`
- 超预算终止：`status_update="BUDGET_EXCEEDED"`

## 7) 质量自检清单
- 选择对了吗？
- 有重复调用吗？
- 有足够证据吗？
- 有互证吗？
- 已在“足够时即终止”吗？
- 输出结构与模板完全一致吗？
"""


def build_response_format() -> str:
    return """\
# 响应格式（严格模板）

## 1) 处理中（IN_PROGRES / NEED_CLARIFICATION）
```markdown
status_update: IN_PROGRES
thought:
- 本轮先 global_search 抽主线，再 local_search 验证
plan:
- Step1: global_search {query: "..."}
- Step2: get_characters {need_relations: true}
tools:
- name: global_search
  result_summary:
    - point: "主题A 概述"
    - cite: source_id=G1, snippet="……"
provisional_takeaways:
- 主题A 可能为“xxx”（证据：G1）
next_actions:
- local_search 针对人物B关键抉择片段

## 2) 完成（DONE）
status_update: DONE
summary:
- **主题**：……
- **时代/社会/设定**：……
- **主要人物与关系**：……
evidence:
- 主题：
  - [G1] "……"
- 人物关系：
  - [C1] "……"
limitations:
- 人物D 的动机仅见于单一证据
next_suggestions:
- 采集人物B 第X章庭审场景

##3) 超预算终止（BUDGET_EXCEEDED）
status_update: BUDGET_EXCEEDED
what_we_have:
- 已确认主题与三名主要人物画像
what_is_missing:
- 人物D 的关键抉择证据
next_plan_if_approved:
- 追加 2 次 local_search 限定相关章节

##4) 需要澄清（NEED_CLARIFICATION）
status_update: NEED_CLARIFICATION
clarify_questions:
- 你要聚焦原著的哪个版本？
- 是否需要包含番外章节？
"""