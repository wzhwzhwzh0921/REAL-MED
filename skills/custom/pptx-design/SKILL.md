---
name: pptx-design
description: "PPT design specification generator. Use this skill BEFORE generating any PPTX file. It forces a structured design-first workflow: narrative planning, color palette, layout tokens, per-slide shape requirements, and content capacity budgeting. Output is a Design Spec document that pptx skill then uses to write pptxgenjs code."
---

# pptx-design: 先设计，再生成

在写 `pptxgenjs` 代码之前，先输出一份**紧凑的 Design Spec**，然后立即用 **write_file 工具**写完整的 Node.js 脚本并用 **bash 工具**运行。

**Design Spec 必须紧凑：总输出不超过 400 行 YAML/表格，不允许无限展开。**

---

## 工作流

```
Step 0: 理解主题 → 拟定叙事章节
Step 1: 输出 Design Spec（CONCISE，≤400行）并用 write_file 写入 workspace
Step 2: 立即用 write_file 工具写完整的 pptxgenjs Node.js 脚本到 workspace，然后用 bash 运行
```

**Step 1 和 Step 2 必须连续执行，不允许只输出 Design Spec 就停止。**
**Step 2 必须调用 write_file 工具写脚本，不能把代码内联在 AI 文本里输出。**

---

## Design Spec 必须包含（紧凑格式）

### A. 叙事骨架（≤20行）

```yaml
deck_theme: "主题名称"
audience: "目标受众"
narrative_arc: "起→承→转→合"
chapters:
  - {id: C1, name: "背景", slides: [1,2]}
  - {id: C2, name: "分析", slides: [3,4,5]}
  - {id: C3, name: "方案", slides: [6,7,8]}
  - {id: C4, name: "结论", slides: [9,10]}
```

每页叙事角色（一行一页）：
```
P01 [C1·封面]  narrative: 建立主题
P02 [C1·目录]  narrative: 阅读路径
P03 [C2·内容]  narrative: 背景数据，为什么重要
...
```

### B. 配色方案（≤15行）

选一个策略，写出 hex：

| 策略 | 适用 |
|------|------|
| 单主色+深浅 | 商务/科技/汇报 |
| 双色对比（深封面+浅内容页） | 大多数场景 |
| 柔和暖色系 | 人文/历史/教育 |
| 深色舞台系 | 数据展示/产品发布 |

必须定义：`primary` / `accent` / `bg_dark` / `bg_light` / `text_main` / `text_muted` / `line_soft` / `card_fill` / `cover_overlay` / `chapter_colors: {C1,C2,C3,C4}`

约束：全 deck 常驻颜色 ≤4 个主角色；所有颜色必须来自 palette，不得单页发明新色。

### C. 版式参数（≤10行，仅必要参数）

```yaml
page_margin_x: 0.45
title_y: 0.35 / title_h: 0.5
card_radius: 0.08 / card_gap: 0.18
header_band_h: 0.08 / section_band_w: 0.16
# 容量约束
title_max_lines: 2 / title_safe_chars: 14
body_max_lines: 4 / body_safe_chars: 20
bullet_max: 4
```

### D. 幻灯片规划（每页1行，格式固定）

```
P## | 标题 | 类型 | 章节 | 必须shape | 容量预算
P01 | 封面 | cover | C1 | 全幅背景+装饰圆+底部横条 | 标题≤2行
P02 | 目录 | agenda | C1 | 左色带+编号圆+分割线 | 每项≤14字
P03 | 标题xxx | content-text | C2 | 顶部色带+双卡片+分割线 | 每卡bullet≤4条
...
```

类型选项：`cover / agenda / section / content-text / content-image / card-grid / stats / timeline / comparison / closing`

---

## Shape 强制规则（每页必须遵守）

**S1** 每页至少 2 类 shape，其中 1 类必须是结构型（背景矩形/标题色带/卡片容器/分割线/时间轴主线）

**S2** 每页至少 1 个视觉锚点（大色块/宽标题带/大号数字卡/时间轴主线+节点/整列色条）

**S3** 章节归属必须有 shape 承载（顶部章节带/左侧竖条/编号徽标/章节角标）

**S4** 容器尺寸先按内容容量定，再微调美感

各类型最低要求：
- `cover`：全幅背景矩形 + 装饰shape(圆/横条) + 标题承载区
- `agenda`：左/顶色带 + 每项编号圆/方块 + 分割线或底板
- `section`：大面积色块背景 + 章节编号shape + 辅助线/色带（**不能只有居中大标题**）
- `content-text`：标题色带 + 内容容器框 + 多栏时有分隔
- `card-grid`：每张卡独立矩形底板 + 标题/正文层级分隔
- `stats`：大数字callout容器 + 辅助说明底板/标签条
- `timeline`：主线 + 每节点圆形/圆角框 + 标签容器
- `comparison`：左右各自底板 + 中间分割线或色差
- `closing`：呼应封面的背景shape + 收束装饰

---

## Box / 容量规则（精简版）

| 规则 | 内容 |
|------|------|
| A | 3条以上bullet必须放入容器框 |
| B | 高亮数字必须用callout box（accent背景+白字） |
| C | 标题区必须有承载结构（色带/分割线/标签/左侧条） |
| D | 不裸放文字（至少给底板/分割线/左侧条之一） |
| E | 图片必须有容器（边框/蒙版/底板+caption） |
| F | 多栏页面每栏有明确边界（竖线/独立卡片/背景色差） |
| G | 先按最大内容量定容器高，再微调美感 |
| H | bullet超4条时：合并同类/改双列/改卡片/拆页 |
| I | 图片容器先声明比例假设（16:9/4:3/1:1）和裁切策略 |

---

## 关键 pptxgenjs 片段（参考）

```js
// 全幅背景
slide.addShape(pptx.ShapeType.rect, {x:0,y:0,w:13.33,h:7.5, fill:{color:palette.bg_dark}});
// 顶部章节色带
slide.addShape(pptx.ShapeType.rect, {x:0,y:0,w:13.33,h:0.08, fill:{color:palette.primary}});
// 左侧竖条
slide.addShape(pptx.ShapeType.rect, {x:0.35,y:0.5,w:0.16,h:6.2, fill:{color:palette.primary}});
// 编号圆
slide.addShape(pptx.ShapeType.ellipse, {x:1.0,y:1.6,w:0.32,h:0.32, fill:{color:palette.accent}});
// 分割线
slide.addShape(pptx.ShapeType.line, {x:0.8,y:1.5,w:11.4,h:0, line:{color:palette.line_soft,width:1.2}});
// 装饰圆（半透明）
slide.addShape(pptx.ShapeType.ellipse, {x:10.9,y:0.5,w:1.1,h:1.1, fill:{color:palette.accent,transparency:20}});
// 卡片组（循环对齐）
const cw=3.7, ch=1.7, gap=0.22;
[0,1,2].forEach(i => slide.addShape(pptx.ShapeType.roundRect, {
  x:0.8+i*(cw+gap), y:1.6, w:cw, h:ch,
  fill:{color:palette.card_fill}, line:{color:palette.line_soft,width:1.0}, radius:0.08
}));
// 时间轴主线 + 节点
slide.addShape(pptx.ShapeType.line, {x:1.2,y:3.1,w:10.5,h:0, line:{color:palette.primary,width:2.0}});
[1.5,4.0,6.5,9.0].forEach(x => slide.addShape(pptx.ShapeType.ellipse, {x,y:2.98,w:0.24,h:0.24, fill:{color:palette.accent}}));
// 图片容器框
slide.addShape(pptx.ShapeType.rect, {x:0.8,y:1.4,w:5.2,h:4.1, line:{color:palette.primary,width:1.5}, radius:0.06});
slide.addImage({path:imgPath, x:0.95,y:1.55,w:4.9,h:3.8});
```

---

## 反模式（避免）

| ❌ 避免 | ✅ 改法 |
|---------|---------|
| 每页都是标题+bullet | 根据内容选不同类型 |
| 纯白底+黑字+无shape | 标题色带+内容卡片+分割线 |
| section页只有居中标题 | 加深底+编号shape+辅助线 |
| 图片直接贴白底 | 加边框/蒙版/底板+caption |
| 三个大数字散放 | 每个做成callout卡 |
| 时间轴只有文字 | 主线+节点圆+标签框 |
| 目录有编号但正文无章节归属 | 每页加章节角标/色带 |
| bullet超4条硬缩字号 | 合并/改卡片/拆页 |

---

## 一句话原则

**先设计叙事骨架和 shape 骨架，Design Spec 写完立即用 write_file 工具写 Node.js 脚本、用 bash 工具运行，不允许只输出设计文档就停止，也不允许把代码内联在 AI 文字里。**
