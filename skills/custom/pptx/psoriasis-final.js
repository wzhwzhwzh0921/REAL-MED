const pptxgen = require("pptxgenjs");
const path = require("path");
const fs = require("fs");

// Initialize presentation
let pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';
pres.author = '皮肤科专家';
pres.title = '中重度斑块型银屑病诊疗精要';
pres.subject = '含PsA管理点';

// Color palette - Medical professional style
const palette = {
  primary: "1A5276",
  secondary: "2E86AB",
  accent: "148F77",
  warning: "D35400",
  bg_dark: "1C2833",
  bg_light: "F8F9FA",
  text_main: "2C3E50",
  text_muted: "5D6D7E",
  card_fill: "FFFFFF",
  line_soft: "E5E8EB",
  chapter_C1: "1A5276",
  chapter_C2: "2E86AB",
  chapter_C3: "148F77",
  chapter_C4: "D35400",
  chapter_C5: "5D6D7E"
};

function addNotes(slide, notes) { slide.addNotes(notes); }
function addHeaderBand(slide, chapterColor) {
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.08, fill: { color: chapterColor } });
}
function addTitleWithAccent(slide, title, subtitle) {
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0.35, w: 0.1, h: 0.55, fill: { color: palette.primary } });
  slide.addText(title, { x: 0.25, y: 0.35, w: 9.5, h: 0.4, fontSize: 28, fontFace: "Arial", bold: true, color: palette.text_main, margin: 0 });
  if (subtitle) {
    slide.addText(subtitle, { x: 0.25, y: 0.7, w: 9.5, h: 0.25, fontSize: 14, fontFace: "Arial", color: palette.text_muted, margin: 0 });
  }
}

// SLIDE 1: Cover
function createCoverSlide() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_dark };
  slide.addShape(pres.shapes.OVAL, { x: 7.5, y: -0.5, w: 3.5, h: 3.5, fill: { color: palette.primary, transparency: 30 } });
  slide.addShape(pres.shapes.OVAL, { x: 8.5, y: 3.5, w: 2, h: 2, fill: { color: palette.secondary, transparency: 40 } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.1, w: 10, h: 0.525, fill: { color: palette.primary } });
  slide.addText("中重度斑块型银屑病", { x: 0.5, y: 1.8, w: 9, h: 0.8, fontSize: 40, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
  slide.addText("诊疗精要", { x: 0.5, y: 2.5, w: 9, h: 0.6, fontSize: 36, fontFace: "Arial", bold: true, color: palette.secondary, margin: 0 });
  slide.addText("含 PsA 管理要点", { x: 0.5, y: 3.2, w: 9, h: 0.4, fontSize: 20, fontFace: "Arial", color: "FFFFFF", margin: 0 });
  slide.addText("三甲医院皮肤科 临床讲座", { x: 0.5, y: 4.0, w: 9, h: 0.35, fontSize: 16, fontFace: "Arial", color: palette.text_muted, margin: 0 });
  addNotes(slide, "【演讲者备注】\n欢迎各位同道参加今天的讲座。本次课程将系统讲解中重度斑块型银屑病的诊断与治疗，特别强调PsA（银屑病关节炎）管理要点。\n时间安排：约60分钟，含问答环节。\n重点参考：《中国银屑病诊疗指南(2018版)》、《2024生物制剂/小分子药物指南》及《2025质控共识》。");
}

// SLIDE 2: Agenda
function createAgendaSlide() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.15, h: 5.625, fill: { color: palette.primary } });
  slide.addText("讲座大纲", { x: 0.5, y: 0.35, w: 9, h: 0.5, fontSize: 32, fontFace: "Arial", bold: true, color: palette.text_main, margin: 0 });
  const agendaItems = [
    { num: "01", title: "疾病概述", desc: "免疫介导慢性炎症、共病风险" },
    { num: "02", title: "诊断与评估", desc: "PASI/BSA/PGA/IGA/DLQI评分系统" },
    { num: "03", title: "治疗选择", desc: "2024指南、生物制剂比较、达标目标" },
    { num: "04", title: "案例与实践", desc: "儿童脓疱型、超适应证、监测框架" }
  ];
  agendaItems.forEach((item, i) => {
    const y = 1.2 + i * 1.05;
    slide.addShape(pres.shapes.OVAL, { x: 0.6, y: y, w: 0.5, h: 0.5, fill: { color: palette.primary } });
    slide.addText(item.num, { x: 0.6, y: y, w: 0.5, h: 0.5, fontSize: 16, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
    slide.addText(item.title, { x: 1.3, y: y + 0.05, w: 4, h: 0.3, fontSize: 18, fontFace: "Arial", bold: true, color: palette.text_main, margin: 0 });
    slide.addText(item.desc, { x: 1.3, y: y + 0.35, w: 7, h: 0.25, fontSize: 12, fontFace: "Arial", color: palette.text_muted, margin: 0 });
  });
  addNotes(slide, "【演讲者备注】\n本次讲座分为四个部分：\n1. 首先介绍银屑病作为免疫介导的慢性炎症性疾病的本质，以及其共病风险\n2. 重点讲解各种评分系统在严重度评估中的应用，包括10分制判定标准\n3. 详细介绍2024年生物制剂指南和2025年质控共识的要点\n4. 通过实际案例帮助大家理解临床实践中的应用");
}

// SLIDE 3: Section - Diagnosis
function createSectionC2() {
  let slide = pres.addSlide();
  slide.background = { color: palette.secondary };
  slide.addShape(pres.shapes.OVAL, { x: 7, y: -1, w: 4, h: 4, fill: { color: "FFFFFF", transparency: 90 } });
  slide.addShape(pres.shapes.OVAL, { x: 0.8, y: 2.0, w: 1.2, h: 1.2, fill: { color: "FFFFFF", transparency: 20 } });
  slide.addText("02", { x: 0.8, y: 2.0, w: 1.2, h: 1.2, fontSize: 36, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  slide.addText("诊断与评估", { x: 2.2, y: 2.1, w: 7, h: 0.9, fontSize: 44, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
  slide.addText("严重度评分系统与10分制", { x: 2.2, y: 2.9, w: 7, h: 0.4, fontSize: 18, fontFace: "Arial", color: "FFFFFF", margin: 0 });
  addNotes(slide, "【演讲者备注】\n第二章将详细讲解银屑病严重度的评估体系。\n核心评分工具：PASI、BSA、PGA、IGA、DLQI。\n这些工具是判断患者是否需要系统治疗的关键依据。");
}

// SLIDE 4: PASI & BSA
function createPASIBSA() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  addHeaderBand(slide, palette.chapter_C2);
  addTitleWithAccent(slide, "PASI 与 BSA 评分", "银屑病严重度核心指标");
  const cardY = 1.3, cardH = 3.8, card1X = 0.4, card1W = 4.4, card2X = 5.1, card2W = 4.4;
  
  // PASI Card
  slide.addShape(pres.shapes.RECTANGLE, { x: card1X, y: cardY, w: card1W, h: cardH, fill: { color: palette.card_fill }, line: { color: palette.line_soft, width: 1 } });
  slide.addShape(pres.shapes.RECTANGLE, { x: card1X, y: cardY, w: card1W, h: 0.45, fill: { color: palette.secondary } });
  slide.addText("PASI评分", { x: card1X + 0.15, y: cardY + 0.08, w: card1W - 0.3, h: 0.35, fontSize: 16, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
  slide.addText([
    { text: "评估范围：", options: { bold: true, breakLine: true } },
    { text: "红斑(E)、浸润(I)、鳞屑(D) x 头/躯/上肢/下肢面积", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "评分范围：0 - 72分", options: { bold: true, breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "严重度分层：", options: { bold: true, breakLine: true } },
    { text: "轻度：PASI < 10", options: { bullet: true, breakLine: true } },
    { text: "中度：PASI 10-30", options: { bullet: true, breakLine: true } },
    { text: "重度：PASI > 30 或 BSA > 10%", options: { bullet: true, breakLine: false } }
  ], { x: card1X + 0.2, y: cardY + 0.6, w: card1W - 0.4, h: 3.0, fontSize: 12, fontFace: "Arial", color: palette.text_main, valign: "top", margin: 0 });
  
  // BSA Card
  slide.addShape(pres.shapes.RECTANGLE, { x: card2X, y: cardY, w: card2W, h: cardH, fill: { color: palette.card_fill }, line: { color: palette.line_soft, width: 1 } });
  slide.addShape(pres.shapes.RECTANGLE, { x: card2X, y: cardY, w: card2W, h: 0.45, fill: { color: palette.accent } });
  slide.addText("BSA评分", { x: card2X + 0.15, y: cardY + 0.08, w: card2W - 0.3, h: 0.35, fontSize: 16, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
  slide.addText([
    { text: "评估范围：", options: { bold: true, breakLine: true } },
    { text: "患者手掌约等于1% BSA", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "临床判定标准：", options: { bold: true, breakLine: true } },
    { text: "轻度：BSA < 3%", options: { bullet: true, breakLine: true } },
    { text: "中度：BSA 3-10%", options: { bullet: true, breakLine: true } },
    { text: "重度：BSA > 10%", options: { bullet: true, breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "10分制中：>=3分为中度，>=7分为重度", options: { bold: true, breakLine: false } }
  ], { x: card2X + 0.2, y: cardY + 0.6, w: card2W - 0.4, h: 3.0, fontSize: 12, fontFace: "Arial", color: palette.text_main, valign: "top", margin: 0 });
  addNotes(slide, "【演讲者备注】\nPASI评分是最常用的银屑病严重度评估工具，综合评估四个解剖部位的皮损严重度和受累面积。\n注意：PASI评分需要专业培训，BSA更直观，便于快速筛查。临床实践中，BSA>10%或PASI>30通常被视为进入系统治疗的门槛。");
}

// SLIDE 5: PGA/IGA
function createPGAIGA() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  addHeaderBand(slide, palette.chapter_C2);
  addTitleWithAccent(slide, "PGA 与 IGA 总体分级", "医师与研究者评估量表");
  const tableData = [
    [{ text: "分数", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }, { text: "PGA描述", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }, { text: "IGA描述", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }, { text: "10分制", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }],
    [{ text: "0", options: { align: "center", fill: { color: "E8F6F3" } } }, { text: "清除 (Clear)", options: { fill: { color: "E8F6F3" } } }, { text: "清除", options: { fill: { color: "E8F6F3" } } }, { text: "0", options: { align: "center", fill: { color: "E8F6F3" } } }],
    [{ text: "1", options: { align: "center" } }, { text: "几乎清除", options: {} }, { text: "几乎清除", options: {} }, { text: "1", options: { align: "center" } }],
    [{ text: "2", options: { align: "center", fill: { color: "FDF2E9" } } }, { text: "轻度 (Mild)", options: { fill: { color: "FDF2E9" } } }, { text: "轻度", options: { fill: { color: "FDF2E9" } } }, { text: "2-3", options: { align: "center", fill: { color: "FDF2E9" } } }],
    [{ text: "3", options: { align: "center" } }, { text: "中度 (Moderate)", options: {} }, { text: "中度", options: {} }, { text: "4-5", options: { align: "center" } }],
    [{ text: "4", options: { align: "center", fill: { color: "FADBD8" } } }, { text: "重度 (Severe)", options: { fill: { color: "FADBD8" } } }, { text: "重度", options: { fill: { color: "FADBD8" } } }, { text: "6-7", options: { align: "center", fill: { color: "FADBD8" } } }],
    [{ text: "5", options: { align: "center", fill: { color: "F1948A" }, color: "FFFFFF" } }, { text: "极重度", options: { fill: { color: "F1948A" }, color: "FFFFFF" } }, { text: "极重度", options: { fill: { color: "F1948A" }, color: "FFFFFF" } }, { text: "8-10", options: { align: "center", fill: { color: "F1948A" }, color: "FFFFFF" } }]
  ];
  slide.addTable(tableData, { x: 0.5, y: 1.2, w: 9, h: 3.5, colW: [1, 2.8, 2.2, 2], fontSize: 12, fontFace: "Arial", color: palette.text_main, border: { pt: 0.5, color: palette.line_soft }, valign: "middle" });
  slide.addText("注：IGA 0/1 = 几乎清除/清除，是达标治疗的核心目标", { x: 0.5, y: 4.9, w: 9, h: 0.3, fontSize: 11, fontFace: "Arial", italic: true, color: palette.text_muted, margin: 0 });
  addNotes(slide, "【演讲者备注】\nPGA和IGA是医师整体评估工具，用于快速评估银屑病总体严重度。\n关键要点：PGA/IGA 0/1分代表\"清除\"或\"几乎清除\"，这是现代达标治疗(T2T)的核心目标。5分制便于临床快速沟通，10分制可用于更精细的分层。");
}

// SLIDE 6: DLQI
function createDLQI() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  addHeaderBand(slide, palette.chapter_C2);
  addTitleWithAccent(slide, "DLQI 量化损害", "皮肤病生活质量指数");
  const callouts = [{ value: "10", label: "影响显著", sub: "DLQI >= 10", color: palette.warning }, { value: "30", label: "极大影响", sub: "DLQI 最高分", color: palette.primary }];
  callouts.forEach((c, i) => {
    const cx = 0.6 + i * 4.8;
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.4, w: 4.2, h: 2.2, fill: { color: palette.card_fill }, line: { color: palette.line_soft, width: 1 } });
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.4, w: 4.2, h: 0.08, fill: { color: c.color } });
    slide.addText(c.value, { x: cx, y: 1.7, w: 4.2, h: 0.9, fontSize: 56, fontFace: "Arial", bold: true, color: c.color, align: "center", margin: 0 });
    slide.addText(c.sub, { x: cx, y: 2.55, w: 4.2, h: 0.35, fontSize: 18, fontFace: "Arial", bold: true, color: palette.text_main, align: "center", margin: 0 });
    slide.addText(c.label, { x: cx, y: 2.9, w: 4.2, h: 0.35, fontSize: 14, fontFace: "Arial", color: palette.text_muted, align: "center", margin: 0 });
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.85, w: 9, h: 1.4, fill: { color: palette.card_fill }, line: { color: palette.line_soft, width: 1 } });
  slide.addText([
    { text: "DLQI临床意义：", options: { bold: true, breakLine: true } },
    { text: "评估皮肤病对患者生活质量的影响（症状、情感、社交、日常活动等10个问题）", options: { bullet: true, breakLine: true } },
    { text: "用于医患沟通：让患者理解疾病影响的概念", options: { bullet: true, breakLine: true } },
    { text: "进入系统治疗的参考标准之一：DLQI >= 10", options: { bullet: true, breakLine: false } }
  ], { x: 0.7, y: 3.95, w: 8.6, h: 1.2, fontSize: 12, fontFace: "Arial", color: palette.text_main, valign: "top", margin: 0 });
  addNotes(slide, "【演讲者备注】\nDLQI(Dermatology Life Quality Index)是评估银屑病对患者生活质量影响的重要工具。临床应用：1.筛查工具：10个问题，2分钟内完成患者自评 2.治疗门槛：DLQI >= 10 3.疗效评估 4.医患沟通。注意：DLQI是主观评估，与客观皮损评估可互补。");
}

// SLIDE 7: MCQ & 10-point
function createMCQ10point() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  addHeaderBand(slide, palette.chapter_C2);
  addTitleWithAccent(slide, "10分制严重度判定", "MCQ开场 进入系统治疗路径");
  const boxW = 2.6, boxH = 1.1, boxY = 1.5;
  
  // BSA box
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: boxY, w: boxW, h: boxH, fill: { color: palette.secondary } });
  slide.addText("BSA", { x: 0.4, y: boxY + 0.15, w: boxW, h: 0.35, fontSize: 16, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", margin: 0 });
  slide.addText("体表受累面积", { x: 0.4, y: boxY + 0.45, w: boxW, h: 0.25, fontSize: 11, fontFace: "Arial", color: "FFFFFF", align: "center", margin: 0 });
  slide.addText(">=3分", { x: 0.4, y: boxY + 0.7, w: boxW, h: 0.3, fontSize: 20, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", margin: 0 });
  slide.addText("->", { x: 3.0, y: boxY + 0.3, w: 0.5, h: 0.5, fontSize: 24, color: palette.text_muted, align: "center", margin: 0 });
  
  // PASI box
  slide.addShape(pres.shapes.RECTANGLE, { x: 3.5, y: boxY, w: boxW, h: boxH, fill: { color: palette.accent } });
  slide.addText("PASI", { x: 3.5, y: boxY + 0.15, w: boxW, h: 0.35, fontSize: 16, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", margin: 0 });
  slide.addText("面积严重度指数", { x: 3.5, y: boxY + 0.45, w: boxW, h: 0.25, fontSize: 11, fontFace: "Arial", color: "FFFFFF", align: "center", margin: 0 });
  slide.addText(">=7分", { x: 3.5, y: boxY + 0.7, w: boxW, h: 0.3, fontSize: 20, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", margin: 0 });
  slide.addText("->", { x: 6.1, y: boxY + 0.3, w: 0.5, h: 0.5, fontSize: 24, color: palette.text_muted, align: "center", margin: 0 });
  
  // DLQI box
  slide.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: boxY, w: boxW, h: boxH, fill: { color: palette.warning } });
  slide.addText("DLQI", { x: 6.6, y: boxY + 0.15, w: boxW, h: 0.35, fontSize: 16, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", margin: 0 });
  slide.addText("生活质量影响", { x: 6.6, y: boxY + 0.45, w: boxW, h: 0.25, fontSize: 11, fontFace: "Arial", color: "FFFFFF", align: "center", margin: 0 });
  slide.addText(">=10分", { x: 6.6, y: boxY + 0.7, w: boxW, h: 0.3, fontSize: 20, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", margin: 0 });
  
  // Decision box
  slide.addShape(pres.shapes.RECTANGLE, { x: 2.5, y: 3.0, w: 5, h: 1.2, fill: { color: palette.primary } });
  slide.addText("任一指标达标 -> 重度判定", { x: 2.5, y: 3.05, w: 5, h: 0.45, fontSize: 16, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", margin: 0 });
  slide.addText("进入系统/生物制剂治疗路径", { x: 2.5, y: 3.5, w: 5, h: 0.35, fontSize: 14, fontFace: "Arial", color: "FFFFFF", align: "center", margin: 0 });
  
  // MCQ
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.5, w: 9, h: 0.9, fill: { color: palette.card_fill }, line: { color: palette.secondary, width: 2 } });
  slide.addText("MCQ开场：患者BSA=8%，PASI=12，DLQI=15，该患者是否需要系统治疗？", { x: 0.7, y: 4.6, w: 8.6, h: 0.7, fontSize: 13, fontFace: "Arial", italic: true, color: palette.text_main, valign: "middle", margin: 0 });
  addNotes(slide, "【演讲者备注】\nMCQ开场问题用于教学互动。答案：是。分析：BSA=8% -> 5-6分；PASI=12 -> 中度偏重；DLQI=15 -> >10分。三条标准满足任一条即达到系统治疗门槛。");
}

// SLIDE 8: Section Treatment
function createSectionC3() {
  let slide = pres.addSlide();
  slide.background = { color: palette.accent };
  slide.addShape(pres.shapes.OVAL, { x: -1, y: 3, w: 4, h: 4, fill: { color: "FFFFFF", transparency: 90 } });
  slide.addShape(pres.shapes.OVAL, { x: 0.8, y: 2.0, w: 1.2, h: 1.2, fill: { color: "FFFFFF", transparency: 20 } });
  slide.addText("03", { x: 0.8, y: 2.0, w: 1.2, h: 1.2, fontSize: 36, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  slide.addText("治疗选择", { x: 2.2, y: 2.1, w: 7, h: 0.9, fontSize: 44, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
  slide.addText("2024生物制剂指南 - 2025质控共识", { x: 2.2, y: 2.9, w: 7, h: 0.4, fontSize: 18, fontFace: "Arial", color: "FFFFFF", margin: 0 });
  addNotes(slide, "【演讲者备注】\n第三章将系统讲解银屑病的系统治疗选择。核心指南依据：2024年生物制剂/小分子药物临床应用指南、2025年银屑病诊疗质量控制共识。达标治疗目标：PASI90或IGA0/1。");
}

// SLIDE 9: Guidelines
function createGuidelines() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  addHeaderBand(slide, palette.chapter_C3);
  addTitleWithAccent(slide, "2024 生物制剂指南要点", "2025 诊疗质控共识");
  const cards = [
    { title: "传统系统治疗", items: ["环孢素 A", "甲氨蝶呤", "阿维 A", "硫唑嘌呤"], color: palette.text_muted },
    { title: "生物制剂", items: ["TNF-α 抑制剂", "IL-12/23 抑制剂", "IL-17A 抑制剂", "IL-23 抑制剂"], color: palette.secondary },
    { title: "小分子药物", items: ["PDE4 抑制剂", "JAK 抑制剂", "TYK2 抑制剂"], color: palette.accent }
  ];
  const cardW = 2.9, cardH = 2.6;
  cards.forEach((card, i) => {
    const cx = 0.5 + i * 3.15;
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.3, w: cardW, h: cardH, fill: { color: palette.card_fill }, line: { color: palette.line_soft, width: 1 } });
    slide.addShape(pres.shapes.RECTANGLE, { x: cx, y: 1.3, w: cardW, h: 0.45, fill: { color: card.color } });
    slide.addText(card.title, { x: cx + 0.1, y: 1.38, w: cardW - 0.2, h: 0.35, fontSize: 14, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
    slide.addText(card.items.map((item, j) => ({ text: item, options: { bullet: true, breakLine: j < card.items.length - 1 } })), { x: cx + 0.15, y: 1.9, w: cardW - 0.3, h: 1.9, fontSize: 12, fontFace: "Arial", color: palette.text_main, valign: "top", margin: 0 });
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.2, w: 9, h: 1.1, fill: { color: palette.primary } });
  slide.addText([
    { text: "中国指南特色：", options: { bold: true, breakLine: true } },
    { text: "强调传统系统治疗仍是重要选择，尤其在资源受限地区", options: { bullet: true, breakLine: true } },
    { text: "生物制剂选择需考虑疗效、安全性、经济因素及患者意愿", options: { bullet: true, breakLine: false } }
  ], { x: 0.7, y: 4.3, w: 8.6, h: 0.9, fontSize: 12, fontFace: "Arial", color: "FFFFFF", valign: "top", margin: 0 });
  addNotes(slide, "【演讲者备注】\n2024年指南对治疗药物进行了系统分类。传统系统治疗：环孢素A、甲氨蝶呤、阿维A。生物制剂：TNF-α、IL-12/23、IL-17A、IL-23抑制剂。小分子药物：PDE4、JAK、TYK2抑制剂。中国指南强调治疗选择应个体化。");
}

// SLIDE 10: Biologics Comparison
function createBiologicsComparison() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  addHeaderBand(slide, palette.chapter_C3);
  addTitleWithAccent(slide, "生物制剂靶点比较", "TNF-α / IL-12/23 / IL-17A");
  const tableData = [
    [{ text: "靶点", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }, { text: "代表药物", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }, { text: "PASI90率", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }, { text: "起效速度", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }, { text: "特殊优势", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }],
    [{ text: "TNF-α", options: { fill: { color: "E8F4F8" }, bold: true } }, { text: "英夫利西单抗\n阿达木单抗", options: { fill: { color: "E8F4F8" } } }, { text: "~50-60%", options: { fill: { color: "E8F4F8" }, align: "center" } }, { text: "中等", options: { fill: { color: "E8F4F8" }, align: "center" } }, { text: "PsA共病患者\n优选", options: { fill: { color: "E8F4F8" } } }],
    [{ text: "IL-12/23", options: { bold: true } }, { text: "乌司奴单抗", options: {} }, { text: "~60-70%", options: { align: "center" } }, { text: "中等", options: { align: "center" } }, { text: "长期维持\n疗效稳定", options: {} }],
    [{ text: "IL-17A", options: { fill: { color: "E8F4F8" }, bold: true } }, { text: "司库奇尤单抗\n依奇珠单抗", options: { fill: { color: "E8F4F8" } } }, { text: "~70-80%", options: { fill: { color: "E8F4F8" }, align: "center" } }, { text: "快速", options: { fill: { color: "E8F4F8" }, align: "center" } }, { text: "起效快\n银屑甲疗效好", options: { fill: { color: "E8F4F8" } } }]
  ];
  slide.addTable(tableData, { x: 0.4, y: 1.2, w: 9.2, h: 2.8, colW: [1.6, 2.2, 1.6, 1.4, 2.4], fontSize: 11, fontFace: "Arial", color: palette.text_main, border: { pt: 0.5, color: palette.line_soft }, valign: "middle" });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.2, w: 9, h: 1.1, fill: { color: palette.accent } });
  slide.addText("达标治疗目标", { x: 0.7, y: 4.3, w: 8.6, h: 0.4, fontSize: 16, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
  slide.addText("PASI90 改善 或 IGA 0/1（清除/几乎清除）", { x: 0.7, y: 4.7, w: 8.6, h: 0.35, fontSize: 14, fontFace: "Arial", color: "FFFFFF", margin: 0 });
  addNotes(slide, "【演讲者备注】\n生物制剂比较：1.TNF-α抑制剂：经典靶点，对PsA患者可能更有优势 2.IL-12/23抑制剂：长期维持疗效稳定 3.IL-17A抑制剂：起效快速（2-4周），银屑甲疗效显著。达标治疗新标准：PASI90或IGA0/1。");
}

// SLIDE 11: Treatment Goals
function createTreatmentGoals() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  addHeaderBand(slide, palette.chapter_C3);
  addTitleWithAccent(slide, "达标治疗目标", "PASI90 / IGA 0/1");
  const goals = [{ value: "PASI90", label: "银屑病面积及严重度指数\n改善90%", sub: "核心目标", color: palette.secondary }, { value: "IGA 0/1", label: "研究者总体评估\n0=清除 1=几乎清除", sub: "临床目标", color: palette.accent }];
  goals.forEach((g, i) => {
    const gx = 0.8 + i * 4.6;
    slide.addShape(pres.shapes.RECTANGLE, { x: gx, y: 1.3, w: 4.2, h: 2.4, fill: { color: palette.card_fill }, line: { color: g.color, width: 3 } });
    slide.addText(g.value, { x: gx, y: 1.5, w: 4.2, h: 0.7, fontSize: 32, fontFace: "Arial", bold: true, color: g.color, align: "center", margin: 0 });
    slide.addText(g.label, { x: gx, y: 2.2, w: 4.2, h: 0.7, fontSize: 12, fontFace: "Arial", color: palette.text_main, align: "center", margin: 0 });
    slide.addText(g.sub, { x: gx, y: 3.1, w: 4.2, h: 0.35, fontSize: 14, fontFace: "Arial", bold: true, color: g.color, align: "center", margin: 0 });
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.0, w: 9, h: 1.3, fill: { color: "F0F4F8" }, line: { color: palette.line_soft, width: 1 } });
  slide.addText([
    { text: "评估时间点：", options: { bold: true, breakLine: true } },
    { text: "诱导期：12-16周进行中期评估", options: { bullet: true, breakLine: true } },
    { text: "维持期：每3-6个月评估一次", options: { bullet: true, breakLine: true } },
    { text: "未达标：考虑更换治疗方案或加用其他药物", options: { bullet: true, breakLine: false } }
  ], { x: 0.7, y: 4.1, w: 8.6, h: 1.1, fontSize: 12, fontFace: "Arial", color: palette.text_main, valign: "top", margin: 0 });
  addNotes(slide, "【演讲者备注】\n达标治疗(Treat-to-Target)是银屑病治疗的核心理念。关键要点：1.PASI90是金标准 2.IGA 0/1是临床可操作的目标 3.二者相辅相成。评估时机：12-16周诱导期末评估，达标后每3-6个月维持评估。");
}

// SLIDE 12: TB/HBV Screening
function createScreeningFlow() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  addHeaderBand(slide, palette.chapter_C3);
  addTitleWithAccent(slide, "生物制剂用药前筛查流程", "TB/HBV筛查");
  const steps = [
    { num: "1", title: "病史采集", detail: "结核病史、HBV感染史、疫苗接种史" },
    { num: "2", title: "TB筛查", detail: "T-SPOT.TB 或 PPD试验\n胸部X线检查" },
    { num: "3", title: "HBV筛查", detail: "HBsAg、抗-HBs、HBeAg、抗-HBe、抗-HBc\nHBV DNA（如HBsAg阳性）" },
    { num: "4", title: "其他检查", detail: "血常规、肝肾功能、妊娠试验（育龄期）" },
    { num: "5", title: "综合评估", detail: "排除活动性结核、HBV感染\n后方可启动生物制剂治疗" }
  ];
  const stepH = 0.72, startY = 1.2;
  slide.addShape(pres.shapes.RECTANGLE, { x: 1.0, y: startY + 0.1, w: 0.06, h: stepH * steps.length - 0.1, fill: { color: palette.primary } });
  steps.forEach((step, i) => {
    const sy = startY + i * stepH;
    slide.addShape(pres.shapes.OVAL, { x: 0.82, y: sy, w: 0.42, h: 0.42, fill: { color: palette.primary } });
    slide.addText(step.num, { x: 0.82, y: sy, w: 0.42, h: 0.42, fontSize: 14, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
    slide.addText(step.title, { x: 1.5, y: sy, w: 2, h: 0.35, fontSize: 14, fontFace: "Arial", bold: true, color: palette.text_main, margin: 0 });
    slide.addText(step.detail, { x: 1.5, y: sy + 0.3, w: 4, h: 0.4, fontSize: 10, fontFace: "Arial", color: palette.text_muted, margin: 0 });
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 5.8, y: 1.2, w: 3.8, h: 3.5, fill: { color: palette.warning } });
  slide.addText("重要警示", { x: 6.0, y: 1.35, w: 3.4, h: 0.4, fontSize: 16, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
  slide.addText([
    { text: "活动性结核：", options: { bold: true, breakLine: true } },
    { text: "  先行抗结核治疗", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "HBV感染：", options: { bold: true, breakLine: true } },
    { text: "  HBsAg阳性者需抗病毒治疗", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "潜伏结核感染：", options: { bold: true, breakLine: true } },
    { text: "  预防性抗结核治疗后", options: { breakLine: true } },
    { text: "  可考虑生物制剂", options: { breakLine: false } }
  ], { x: 6.0, y: 1.8, w: 3.4, h: 2.7, fontSize: 11, fontFace: "Arial", color: "FFFFFF", valign: "top", margin: 0 });
  addNotes(slide, "【演讲者备注】\n生物制剂用药前筛查是确保用药安全的关键步骤。结核筛查：T-SPOT.TB或PPD试验二选一，胸部X线检查。HBV筛查：HBsAg阳性者需进一步检测HBV DNA，高病毒载量者需先抗病毒治疗。这是2025年质控共识中的重点要求。");
}

// SLIDE 13: Section Case
function createSectionC4() {
  let slide = pres.addSlide();
  slide.background = { color: palette.warning };
  slide.addShape(pres.shapes.OVAL, { x: 7, y: -1, w: 4, h: 4, fill: { color: "FFFFFF", transparency: 90 } });
  slide.addShape(pres.shapes.OVAL, { x: 0.8, y: 2.0, w: 1.2, h: 1.2, fill: { color: "FFFFFF", transparency: 20 } });
  slide.addText("04", { x: 0.8, y: 2.0, w: 1.2, h: 1.2, fontSize: 36, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  slide.addText("案例与实践", { x: 2.2, y: 2.1, w: 7, h: 0.9, fontSize: 44, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
  slide.addText("儿童脓疱型 - 超适应证 - 监测框架", { x: 2.2, y: 2.9, w: 7, h: 0.4, fontSize: 18, fontFace: "Arial", color: "FFFFFF", margin: 0 });
  addNotes(slide, "【演讲者备注】\n第四章通过实际案例帮助大家理解临床实践中的应用要点。案例背景：8岁泛发性脓疱型银屑病儿童患者，涉及超适应证用药的伦理和实践问题，需要特别注意筛查和监测。");
}

// SLIDE 14: Case Study
function createCaseStudy() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  addHeaderBand(slide, palette.chapter_C4);
  addTitleWithAccent(slide, "案例研究：8岁泛发性脓疱型", "家属询问生物制剂治疗");
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.2, w: 4.5, h: 2.8, fill: { color: palette.card_fill }, line: { color: palette.warning, width: 2 } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.2, w: 4.5, h: 0.45, fill: { color: palette.warning } });
  slide.addText("病例基本信息", { x: 0.55, y: 1.28, w: 4.2, h: 0.35, fontSize: 14, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
  slide.addText([
    { text: "年龄：", options: { bold: true } }, { text: "8岁男童", options: { breakLine: true } },
    { text: "疾病类型：", options: { bold: true } }, { text: "泛发性脓疱型银屑病(GPP)", options: { breakLine: true } },
    { text: "病程：", options: { bold: true } }, { text: "反复发作3年", options: { breakLine: true } },
    { text: "治疗史：", options: { bold: true } }, { text: "阿维A、环孢素均效果欠佳", options: { breakLine: true } },
    { text: "就诊诉求：", options: { bold: true } }, { text: "家属询问生物制剂治疗", options: { breakLine: false } }
  ], { x: 0.6, y: 1.8, w: 4.1, h: 2.0, fontSize: 12, fontFace: "Arial", color: palette.text_main, valign: "top", margin: 0 });
  slide.addShape(pres.shapes.RECTANGLE, { x: 5.1, y: 1.2, w: 4.5, h: 2.8, fill: { color: palette.card_fill }, line: { color: palette.line_soft, width: 1 } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 5.1, y: 1.2, w: 4.5, h: 0.45, fill: { color: palette.primary } });
  slide.addText("临床挑战", { x: 5.25, y: 1.28, w: 4.2, h: 0.35, fontSize: 14, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
  slide.addText([
    { text: "1. 年龄限制", options: { bold: true, breakLine: true } }, { text: "   多数生物制剂在我国仅获批>=18岁", options: { breakLine: true } },
    { text: "2. 超适应证问题", options: { bold: true, breakLine: true } }, { text: "   需充分知情同意", options: { breakLine: true } },
    { text: "3. 安全性考量", options: { bold: true, breakLine: true } }, { text: "   儿童感染风险更需关注", options: { breakLine: false } }
  ], { x: 5.3, y: 1.8, w: 4.1, h: 2.0, fontSize: 11, fontFace: "Arial", color: palette.text_main, valign: "top", margin: 0 });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.2, w: 9.2, h: 1.1, fill: { color: palette.secondary } });
  slide.addText("关键问题：该患儿能否使用生物制剂？如何进行规范化管理？", { x: 0.6, y: 4.4, w: 8.8, h: 0.7, fontSize: 15, fontFace: "Arial", bold: true, color: "FFFFFF", valign: "middle", margin: 0 });
  addNotes(slide, "【演讲者备注】\n这是一个典型的临床挑战性病例。8岁男童，病情反复发作，传统系统治疗效果欠佳，家属主动询问生物制剂。临床挑战：1.年龄问题 2.超适应证 3.获益风险评估：GPP可危及生命，需权衡利弊。");
}

// SLIDE 15: Off-label
function createOffLabel() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  addHeaderBand(slide, palette.chapter_C4);
  addTitleWithAccent(slide, "超适应证评估与筛查", "规范化超适应证用药流程");
  const steps = [
    { title: "适应证评估", detail: "确认是否属于超适应证\n查阅最新循证证据", color: palette.secondary },
    { title: "知情同意", detail: "充分告知利弊\n签署知情同意书", color: palette.warning },
    { title: "TB/HBV筛查", detail: "同成人标准流程\n排除禁忌", color: palette.accent },
    { title: "伦理委员会审批", detail: "必要时提请审批\n保留完整记录", color: palette.primary }
  ];
  const boxW = 2.2, boxH = 1.4;
  steps.forEach((step, i) => {
    const sx = 0.5 + i * 2.4;
    slide.addShape(pres.shapes.RECTANGLE, { x: sx, y: 1.3, w: boxW, h: boxH, fill: { color: step.color } });
    slide.addText(step.title, { x: sx, y: 1.45, w: boxW, h: 0.4, fontSize: 13, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", margin: 0 });
    slide.addText(step.detail, { x: sx + 0.1, y: 1.85, w: boxW - 0.2, h: 0.75, fontSize: 10, fontFace: "Arial", color: "FFFFFF", align: "center", margin: 0 });
    if (i < steps.length - 1) slide.addText("->", { x: sx + boxW, y: 1.75, w: 0.2, h: 0.5, fontSize: 18, color: palette.text_muted, align: "center", margin: 0 });
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.0, w: 9, h: 2.3, fill: { color: palette.card_fill }, line: { color: palette.warning, width: 2 } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 3.0, w: 9, h: 0.45, fill: { color: palette.warning } });
  slide.addText("儿童患者TB/HBV筛查注意事项", { x: 0.7, y: 3.08, w: 8.6, h: 0.35, fontSize: 14, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
  slide.addText([
    { text: "PPD试验：儿童结核筛查首选方法", options: { bullet: true, breakLine: true } },
    { text: "T-SPOT.TB：更特异，适用于PPD阳性或卡介苗接种者", options: { bullet: true, breakLine: true } },
    { text: "HBV血清学：母亲HBsAg阳性者需关注垂直传播风险", options: { bullet: true, breakLine: true } },
    { text: "胸部X线：必须进行，排除活动性肺结核", options: { bullet: true, breakLine: false } }
  ], { x: 0.7, y: 3.55, w: 8.6, h: 1.6, fontSize: 12, fontFace: "Arial", color: palette.text_main, valign: "top", margin: 0 });
  addNotes(slide, "【演讲者备注】\n超适应证用药需要规范化管理。流程：1.适应证评估 2.知情同意 3.TB/HBV筛查 4.伦理委员会审批。儿童患者特殊考虑：PPD试验是首选筛查方法，部分儿童已接种卡介苗，T-SPOT.TB更特异。");
}

// SLIDE 16: Follow-up
function createFollowup() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  addHeaderBand(slide, palette.chapter_C4);
  addTitleWithAccent(slide, "随访监测框架", "生物制剂长期管理");
  const tableData = [
    [{ text: "监测项目", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }, { text: "基线", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }, { text: "诱导期", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }, { text: "维持期", options: { fill: { color: palette.primary }, color: "FFFFFF", bold: true, align: "center" } }],
    [{ text: "PASI/BSA", options: { bold: true } }, { text: "是", options: { align: "center" } }, { text: "每4-8周", options: { align: "center" } }, { text: "每3-6月", options: { align: "center" } }],
    [{ text: "DLQI", options: { bold: true } }, { text: "是", options: { align: "center" } }, { text: "每12周", options: { align: "center" } }, { text: "每6月", options: { align: "center" } }],
    [{ text: "血常规", options: { bold: true } }, { text: "是", options: { align: "center" } }, { text: "每4-8周", options: { align: "center" } }, { text: "每3-6月", options: { align: "center" } }],
    [{ text: "肝肾功能", options: { bold: true } }, { text: "是", options: { align: "center" } }, { text: "每4-8周", options: { align: "center" } }, { text: "每3-6月", options: { align: "center" } }],
    [{ text: "TB筛查", options: { bold: true, color: palette.warning } }, { text: "是", options: { align: "center", color: palette.warning } }, { text: "每6-12月", options: { align: "center", color: palette.warning } }, { text: "每年1次", options: { align: "center", color: palette.warning } }],
    [{ text: "HBV DNA", options: { bold: true, color: palette.warning } }, { text: "是", options: { align: "center", color: palette.warning } }, { text: "每3-6月", options: { align: "center", color: palette.warning } }, { text: "每6-12月", options: { align: "center", color: palette.warning } }]
  ];
  slide.addTable(tableData, { x: 0.5, y: 1.15, w: 9, h: 3.2, colW: [2.2, 1.4, 2.4, 3], fontSize: 12, fontFace: "Arial", color: palette.text_main, border: { pt: 0.5, color: palette.line_soft }, valign: "middle" });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.55, w: 9, h: 0.85, fill: { color: "F0F4F8" }, line: { color: palette.line_soft, width: 1 } });
  slide.addText([
    { text: "注：", options: { bold: true } },
    { text: "TB/HBV监测为2025年质控共识重点强调项目，需纳入标准化随访流程。儿童患者可适当调整监测频率，但需保证最低监测频次。", options: {} }
  ], { x: 0.7, y: 4.65, w: 8.6, h: 0.65, fontSize: 11, fontFace: "Arial", color: palette.text_main, valign: "top", margin: 0 });
  addNotes(slide, "【演讲者备注】\n生物制剂长期治疗需要规范化随访监测。监测原则：疗效评估（PASI/BSA/DLQI）、安全性监测（血常规、肝肾功能）、感染筛查（TB/HBV定期监测）。诱导期监测更密集，维持期可适当降低但仍需定期。2025年质控共识特别强调TB/HBV监测的重要性。");
}

// SLIDE 17: Section References
function createSectionC5() {
  let slide = pres.addSlide();
  slide.background = { color: palette.chapter_C5 };
  slide.addShape(pres.shapes.OVAL, { x: 7, y: 3, w: 4, h: 4, fill: { color: "FFFFFF", transparency: 90 } });
  slide.addShape(pres.shapes.OVAL, { x: 0.8, y: 2.0, w: 1.2, h: 1.2, fill: { color: "FFFFFF", transparency: 20 } });
  slide.addText("05", { x: 0.8, y: 2.0, w: 1.2, h: 1.2, fontSize: 36, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  slide.addText("参考文献", { x: 2.2, y: 2.1, w: 7, h: 0.9, fontSize: 44, fontFace: "Arial", bold: true, color: "FFFFFF", margin: 0 });
  slide.addText("核心指南与专家共识", { x: 2.2, y: 2.9, w: 7, h: 0.4, fontSize: 18, fontFace: "Arial", color: "FFFFFF", margin: 0 });
  addNotes(slide, "【演讲者备注】\n参考文献部分将列出本次讲座的核心依据文献。主要参考来源：中国银屑病诊疗指南（2018版）、2024年生物制剂/小分子药物临床应用指南、2025年银屑病诊疗质量控制专家共识。");
}

// SLIDE 18: References
function createReferences() {
  let slide = pres.addSlide();
  slide.background = { color: palette.bg_light };
  addHeaderBand(slide, palette.chapter_C5);
  addTitleWithAccent(slide, "主要参考文献", "核心指南与专家共识");
  const refs = [
    { num: "1", title: "中国银屑病诊疗指南(2018版)", detail: "中华医学会皮肤性病学分会银屑病专业委员会\n《中华皮肤科杂志》, 2019" },
    { num: "2", title: "2024生物制剂/小分子药物临床应用指南", detail: "中华医学会皮肤性病学分会\n《中华皮肤科杂志》, 2024" },
    { num: "3", title: "2025银屑病诊疗质量控制专家共识", detail: "国家皮肤与免疫疾病临床医学研究中心\n《中华皮肤科杂志》, 2025" }
  ];
  refs.forEach((ref, i) => {
    const ry = 1.2 + i * 1.4;
    slide.addShape(pres.shapes.OVAL, { x: 0.5, y: ry + 0.2, w: 0.5, h: 0.5, fill: { color: palette.primary } });
    slide.addText(ref.num, { x: 0.5, y: ry + 0.2, w: 0.5, h: 0.5, fontSize: 18, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
    slide.addText(ref.title, { x: 1.2, y: ry + 0.15, w: 8.3, h: 0.4, fontSize: 16, fontFace: "Arial", bold: true, color: palette.text_main, margin: 0 });
    slide.addText(ref.detail, { x: 1.2, y: ry + 0.55, w: 8.3, h: 0.55, fontSize: 11, fontFace: "Arial", color: palette.text_muted, margin: 0 });
    if (i < refs.length - 1) slide.addShape(pres.shapes.LINE, { x: 0.5, y: ry + 1.28, w: 9, h: 0, line: { color: palette.line_soft, width: 0.5 } });
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 5.0, w: 9, h: 0.4, fill: { color: palette.primary } });
  slide.addText("感谢各位同道的聆听与交流", { x: 0.5, y: 5.0, w: 9, h: 0.4, fontSize: 14, fontFace: "Arial", bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  addNotes(slide, "【演讲者备注】\n参考文献完整列表：1.中国银屑病诊疗指南(2018版) 2.2024生物制剂/小分子药物临床应用指南 3.2025银屑病诊疗质量控制专家共识。这些文献均可通过中华皮肤科杂志或相关专业数据库获取。");
}

// Generate presentation
async function generatePresentation() {
  console.log("Generating psoriasis lecture presentation...");
  createCoverSlide();
  createAgendaSlide();
  createSectionC2();
  createPASIBSA();
  createPGAIGA();
  createDLQI();
  createMCQ10point();
  createSectionC3();
  createGuidelines();
  createBiologicsComparison();
  createTreatmentGoals();
  createScreeningFlow();
  createSectionC4();
  createCaseStudy();
  createOffLabel();
  createFollowup();
  createSectionC5();
  createReferences();
  
  const outPath = path.join(process.env.OUTPUTS_DIR, "中重度斑块型银屑病诊疗精要.pptx");
  pres.writeFile({ fileName: outPath })
    .then(() => console.log("Presentation saved:", outPath))
    .catch(err => { console.error(err); process.exit(1); });
}

generatePresentation();
