// EduAgent 路演 PPT 生成脚本（金漪湖·论剑 2026 智能体 OPC 创新创业大赛）
// 用法：node build_deck.js
"use strict";

const pptxgen = require("pptxgenjs");
const {
  warnIfSlideHasOverlaps,
  warnIfSlideElementsOutOfBounds,
} = require("./pptxgenjs_helpers/layout");

// ---------- 设计系统 ----------
const FONT = "Microsoft YaHei";
const MONO = "Consolas";
const C = {
  bg: "FAF9F5",       // 米白纸面
  card: "FFFFFF",     // 卡片
  cardTint: "F4F0E4", // 暖灰卡片
  ink: "26211C",      // 正文深墨
  sub: "6E6656",      // 次级文字
  muted: "8A8171",    // 弱化文字
  accent: "C96442",   // 砖红强调
  accentBg: "F7E7DE", // 砖红浅底
  teal: "2F5D5A",     // 深青证据色
  tealBg: "E7EEEB",   // 深青浅底
  hair: "DDD6C7",     // 暖灰细线
  dark: "1F1B16",     // 深墨底（封面/结尾）
  darkText: "F5F2EA",
  darkMuted: "B0A691",
  darkAccent: "E08A63",
  darkTeal: "7FA8A3",
};

const PAGE_W = 13.333;
const PAGE_H = 7.5;
const ML = 0.62;
const CW = PAGE_W - ML * 2; // 12.093
const TOTAL = 17;

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.theme = { headFontFace: FONT, bodyFontFace: FONT };
pptx.title = "EduAgent 个性化学习智能体 · 路演";
pptx.author = "wannaw";

const allSlides = [];
function newSlide(bgColor = C.bg) {
  const s = pptx.addSlide();
  s.background = { color: bgColor };
  allSlides.push(s);
  return s;
}

// 内容页页眉：kicker + 结论式标题 + 强调条 + 细分隔线
function addHeader(s, kicker, title) {
  s.addText(kicker, {
    x: ML, y: 0.38, w: 9, h: 0.26,
    fontFace: FONT, fontSize: 10.5, bold: true, color: C.teal,
    charSpacing: 3, align: "left", valign: "middle",
  });
  s.addText(title, {
    x: ML, y: 0.66, w: CW, h: 0.62,
    fontFace: FONT, fontSize: 24, bold: true, color: C.ink,
    align: "left", valign: "middle",
  });
  s.addShape("rect", { x: ML, y: 1.42, w: 0.5, h: 0.05, fill: { color: C.accent }, line: { type: "none" } });
  s.addShape("line", { x: ML, y: 1.58, w: CW, h: 0, line: { color: C.hair, width: 1 } });
}

// 页脚
function addFooter(s, pageNo) {
  s.addShape("line", { x: ML, y: 7.04, w: CW, h: 0, line: { color: C.hair, width: 0.75 } });
  s.addText("EduAgent 个性化学习智能体 · 金漪湖论剑 2026 智能体 OPC 创新创业大赛", {
    x: ML, y: 7.10, w: 9, h: 0.24, fontFace: FONT, fontSize: 8, color: C.muted, align: "left", valign: "middle",
  });
  s.addText(`${String(pageNo).padStart(2, "0")} / ${TOTAL}`, {
    x: PAGE_W - ML - 1.6, y: 7.10, w: 1.6, h: 0.24, fontFace: MONO, fontSize: 8, color: C.muted, align: "right", valign: "middle",
  });
}

// 通用卡片（文本内嵌，保证可编辑）
function card(s, x, y, w, h, runs, opts = {}) {
  s.addText(runs, {
    x, y, w, h,
    shape: "roundRect", rectRadius: 0.09,
    fill: { color: opts.fill || C.card },
    line: opts.noBorder ? { type: "none" } : { color: opts.border || C.hair, width: 1 },
    fontFace: FONT, align: opts.align || "center", valign: opts.valign || "middle",
    margin: opts.margin || [0.14, 0.16, 0.12, 0.16],
    ...(opts.paraSpaceAfter !== undefined ? { paraSpaceAfter: opts.paraSpaceAfter } : {}),
  });
}

function arrowRight(s, x, y, w = 0.4, h = 0.26, color = C.accent) {
  s.addShape("rightArrow", { x, y, w, h, fill: { color }, line: { type: "none" } });
}
function arrowLeft(s, x, y, w = 0.4, h = 0.26, color = C.accent) {
  s.addShape("leftArrow", { x, y, w, h, fill: { color }, line: { type: "none" } });
}
function arrowDown(s, x, y, w = 0.26, h = 0.3, color = C.teal) {
  s.addShape("downArrow", { x, y, w, h, fill: { color }, line: { type: "none" } });
}

// 节点连线 motif（封面/结尾身份层）
function drawMotif(s, nodes, edges, dotColor, lineColor, dotSize = 0.07) {
  edges.forEach(([a, b]) => {
    const [x1, y1] = nodes[a];
    const [x2, y2] = nodes[b];
    s.addShape("line", {
      x: Math.min(x1, x2), y: Math.min(y1, y2),
      w: Math.abs(x2 - x1), h: Math.abs(y2 - y1),
      line: { color: lineColor, width: 1 },
      flipH: x2 < x1 !== y2 < y1, // 校正斜线方向
      flipV: false,
    });
  });
  nodes.forEach(([x, y], i) => {
    s.addShape("ellipse", {
      x: x - dotSize / 2, y: y - dotSize / 2, w: dotSize, h: dotSize,
      fill: { color: i % 3 === 0 ? C.darkAccent : dotColor }, line: { type: "none" },
    });
  });
}

// ============================================================
// S1 封面（深墨）
// ============================================================
{
  const s = newSlide(C.dark);
  drawMotif(
    s,
    [[10.15, 1.3], [11.35, 0.85], [12.55, 1.7], [10.55, 2.5], [12.05, 3.1], [10.05, 3.9], [11.55, 4.5], [12.6, 5.3], [10.65, 5.6]],
    [[0, 1], [1, 2], [0, 3], [3, 4], [2, 4], [3, 5], [5, 6], [4, 6], [6, 7], [5, 8], [6, 8]],
    C.darkTeal, "3E5A55"
  );
  s.addText("金漪湖·论剑 2026 智能体 OPC 创新创业大赛 · OPC 智能体赛道", {
    x: 0.9, y: 1.15, w: 8.9, h: 0.32, fontFace: FONT, fontSize: 12.5, bold: true,
    color: C.darkAccent, charSpacing: 2, align: "left", valign: "middle",
  });
  s.addText("EduAgent", {
    x: 0.9, y: 1.75, w: 8.9, h: 1.15, fontFace: FONT, fontSize: 56, bold: true,
    color: C.darkText, align: "left", valign: "middle",
  });
  s.addText("个性化学习智能体", {
    x: 0.9, y: 2.95, w: 8.9, h: 0.62, fontFace: FONT, fontSize: 29, bold: true,
    color: C.darkAccent, align: "left", valign: "middle",
  });
  s.addShape("rect", { x: 0.92, y: 3.85, w: 0.55, h: 0.055, fill: { color: C.darkAccent }, line: { type: "none" } });
  s.addText("10 个 Agent 协同的「画像 — 规划 — 多模态产出 — 答疑」学习闭环", {
    x: 0.9, y: 4.1, w: 8.9, h: 0.4, fontFace: FONT, fontSize: 15,
    color: C.darkText, align: "left", valign: "middle",
  });
  s.addText("不再用一台问答 AI 应付所有学生——先理解你是谁，再为你生成整个学习过程。", {
    x: 0.9, y: 4.55, w: 8.9, h: 0.36, fontFace: FONT, fontSize: 11.5,
    color: C.darkMuted, align: "left", valign: "middle",
  });
  s.addShape("line", { x: 0.9, y: 6.35, w: 6.4, h: 0, line: { color: "4A4238", width: 1 } });
  s.addText("开发者：wannaw　｜　官方工具：remio 睿妙（aApp 已上架）　｜　形态：aApp · MCP　｜　2026.09", {
    x: 0.9, y: 6.5, w: 11.5, h: 0.3, fontFace: FONT, fontSize: 10.5,
    color: C.darkMuted, align: "left", valign: "middle",
  });
  s.addNotes("开场 30 秒：高校学习千人一面，一台问答 AI 完不成「画像→规划→多模态产出→答疑」闭环；EduAgent 用 10 个 Agent 协同完成。");
}

// ============================================================
// S2 痛点：千人一面
// ============================================================
{
  const s = newSlide();
  addHeader(s, "01 · 痛点洞察", "同一个知识点，学生拿到的却是同一份讲义、同一套题");
  s.addText("千人一面", {
    x: ML, y: 1.86, w: 2.95, h: 1.0, fontFace: FONT, fontSize: 40, bold: true,
    color: C.accent, align: "left", valign: "middle",
  });
  s.addShape("line", { x: 3.85, y: 2.0, w: 0, h: 0.72, line: { color: C.hair, width: 1 } });
  s.addText("同一门课、同一知识点，不同基础、不同目标的学生，拿到的却是完全相同的讲义与题目——「教」与「学」的错配，是高校学习中最大的效率浪费。", {
    x: 4.1, y: 1.86, w: 8.6, h: 1.0, fontFace: FONT, fontSize: 13,
    color: C.ink, align: "left", valign: "middle", lineSpacingMultiple: 1.35,
  });
  const painCards = [
    { tag: "大一 / 大二学生", quote: "「基础不牢，公共课跟不上」", scene: "典型场景：考前复习、查漏补缺" },
    { tag: "备考学生", quote: "「千人一面，资料不对口」", scene: "典型场景：考研 / 期末针对性刷题" },
    { tag: "薄弱点修复者", quote: "「知道不会，但没人引导」", scene: "典型场景：就着一个知识点反复问" },
  ];
  painCards.forEach((p, i) => {
    const x = ML + i * (3.871 + 0.24);
    card(s, x, 3.15, 3.871, 2.25, [
      { text: p.tag, options: { fontSize: 10.5, bold: true, color: C.teal, charSpacing: 1, breakLine: true } },
      { text: p.quote, options: { fontSize: 15, bold: true, color: C.ink, breakLine: true, paraSpaceBefore: 10 } },
      { text: p.scene, options: { fontSize: 10, color: C.sub, paraSpaceBefore: 10 } },
    ], { fill: C.card, valign: "middle" });
  });
  s.addText([
    { text: "核心命题　", options: { fontSize: 12, bold: true, color: C.teal } },
    { text: "个性化学习需要「画像 → 规划 → 多模态产出 → 答疑」的闭环；单一问答 AI 只能答一题，完成不了这个闭环。", options: { fontSize: 12.5, bold: true, color: C.teal } },
  ], {
    x: ML, y: 5.75, w: CW, h: 0.9, shape: "roundRect", rectRadius: 0.09,
    fill: { color: C.tealBg }, line: { type: "none" }, fontFace: FONT,
    align: "center", valign: "middle", margin: [0.1, 0.2, 0.1, 0.24],
  });
  addFooter(s, 2);
  s.addNotes("强调痛点真实高频：需求研究采用赛道文本分析 + 权威公开资料 + 工程原型验证，不虚构问卷数据。");
}

// ============================================================
// S3 作品定位
// ============================================================
{
  const s = newSlide();
  addHeader(s, "02 · 作品定位", "EduAgent：先理解你是谁，再为你生成整个学习闭环");
  s.addShape("rect", { x: ML, y: 1.86, w: 0.07, h: 1.15, fill: { color: C.accent }, line: { type: "none" } });
  s.addText("面向高校学生的个性化多智能体学习助手——先理解你是谁、哪里薄弱、要学什么，再从结构化课程知识库中检索可追溯的知识，由 10 个分工明确的 Agent 协同产出个性化、多模态的学习资源。", {
    x: ML + 0.25, y: 1.86, w: CW - 0.25, h: 1.15, fontFace: FONT, fontSize: 14.5,
    color: C.ink, align: "left", valign: "middle", lineSpacingMultiple: 1.4,
  });
  const keys = [
    { k: "个性化", d: "8 维画像驱动规划、讲义、练习与答疑，资源随人、随基础、随目标变化" },
    { k: "多模态", d: "讲义 · 题目 · 代码 · 导图 · PPT · 阅读 · 动画，一次请求并行产出" },
    { k: "可追溯", d: "章节级来源引用 + 三级防幻觉兜底，证据不足显式标注，不编造" },
  ];
  keys.forEach((it, i) => {
    const x = ML + i * (3.871 + 0.24);
    card(s, x, 3.3, 3.871, 1.8, [
      { text: it.k, options: { fontSize: 19, bold: true, color: C.teal, breakLine: true } },
      { text: it.d, options: { fontSize: 10.5, color: C.sub, paraSpaceBefore: 8, lineSpacingMultiple: 1.3 } },
    ]);
  });
  const info = [
    ["作品名称", "EduAgent 个性化学习智能体"],
    ["参赛赛道", "OPC 智能体赛道"],
    ["官方工具", "remio 睿妙（aApp 已上架）"],
    ["交付形态", "aApp · MCP 双形态"],
  ];
  info.forEach((it, i) => {
    const x = ML + i * (2.861 + 0.216);
    card(s, x, 5.4, 2.861, 1.3, [
      { text: it[0], options: { fontSize: 9.5, color: C.muted, breakLine: true, charSpacing: 1 } },
      { text: it[1], options: { fontSize: 12, bold: true, color: C.ink, paraSpaceBefore: 8 } },
    ], { fill: C.cardTint, noBorder: true });
  });
  addFooter(s, 3);
  s.addNotes("一句话定位页。让学生用一句自然语言启动学习，三步内获得贴合自身基础、目标与时间投入的路径与资源。");
}

// ============================================================
// S4 为什么必须多 Agent
// ============================================================
{
  const s = newSlide();
  addHeader(s, "03 · 方案思路", "单一问答 AI 只能「答一题」，个性化学习需要多 Agent 闭环");
  // 左：单一问答 AI 局限
  card(s, ML, 1.82, 5.35, 4.3, [
    { text: "单一问答 AI", options: { fontSize: 14, bold: true, color: C.sub, breakLine: true, paraSpaceAfter: 12 } },
    { text: "× 无画像", options: { fontSize: 12, bold: true, color: C.ink } },
    { text: "　不知道你是谁、基础如何、目标是什么", options: { fontSize: 10.5, color: C.sub, breakLine: true, paraSpaceAfter: 10 } },
    { text: "× 无规划", options: { fontSize: 12, bold: true, color: C.ink } },
    { text: "　答完即止，没有学习路径与节奏", options: { fontSize: 10.5, color: C.sub, breakLine: true, paraSpaceAfter: 10 } },
    { text: "× 单模态", options: { fontSize: 12, bold: true, color: C.ink } },
    { text: "　只有一段文字，没有题、图与代码", options: { fontSize: 10.5, color: C.sub, breakLine: true, paraSpaceAfter: 10 } },
    { text: "× 无反馈", options: { fontSize: 12, bold: true, color: C.ink } },
    { text: "　不知道你学会了没有，更不会更新理解", options: { fontSize: 10.5, color: C.sub, breakLine: true } },
    { text: "结果：学生得到的只是「答案」，不是「学会」。", options: { fontSize: 11, bold: true, color: C.accent, breakLine: true, paraSpaceBefore: 12 } },
  ], { fill: C.cardTint, noBorder: true, margin: [0.2, 0.22, 0.16, 0.22], valign: "middle" });
  arrowRight(s, 6.08, 3.85, 0.6, 0.4, C.accent);
  // 右：多 Agent 闭环
  const steps = [
    ["画像理解", "8 维画像，先知道「你是谁」"],
    ["任务规划", "把目标拆成可执行的资源组合"],
    ["多模态产出", "讲义 / 题目 / 代码 / 导图并行生成"],
    ["引导式答疑", "苏格拉底式反问，而非直接报答案"],
    ["反馈更新", "判题回写画像，推荐下一轮复习"],
  ];
  const rx = 6.85, rw = 12.713 - rx;
  card(s, rx, 1.82, rw, 4.3, [
    { text: "EduAgent 多 Agent 闭环", options: { fontSize: 14, bold: true, color: C.teal, breakLine: true, paraSpaceAfter: 10 } },
    ...steps.flatMap((st, i) => [
      { text: `${i + 1}　`, options: { fontSize: 11.5, bold: true, color: C.accent, fontFace: MONO } },
      { text: st[0] + "　", options: { fontSize: 11.5, bold: true, color: C.ink } },
      { text: st[1], options: { fontSize: 10, color: C.sub, breakLine: true, paraSpaceAfter: 7 } },
    ]),
  ], { border: C.teal, margin: [0.2, 0.22, 0.14, 0.22], valign: "middle" });
  s.addText("闭环中的每一环都需要专门能力——多 Agent 不是炫技，是分工。", {
    x: ML, y: 6.32, w: CW, h: 0.5, fontFace: FONT, fontSize: 13, bold: true,
    color: C.accent, align: "left", valign: "middle",
  });
  addFooter(s, 4);
  s.addNotes("对比页：左边讲局限，右边讲闭环五环。记忆句：多 Agent 不是炫技，是分工。");
}

// ============================================================
// S5 学习闭环总览
// ============================================================
{
  const s = newSlide();
  addHeader(s, "03 · 方案思路", "一句话输入，走完「画像—检索—生成—反馈」完整闭环");
  const nodeW = 2.62, gap = 0.537;
  const xs = [0, 1, 2, 3].map(i => ML + i * (nodeW + gap));
  const row1 = [
    ["①", "学生输入", "一句自然语言描述需求"],
    ["②", "意图路由", "Router 识别意图与链路"],
    ["③", "画像理解", "8 维画像先行构建"],
    ["④", "知识检索", "Wiki 混合检索锚定知识"],
  ];
  const row2 = [
    ["⑧", "画像 / 路径更新", "回写画像，进入下一轮"],
    ["⑦", "测验反馈", "判题沉淀薄弱点"],
    ["⑥", "个性化资源", "7 类资源贴合画像产出"],
    ["⑤", "多 Agent 协作", "Doc / Quiz / Code 并行"],
  ];
  row1.forEach((n, i) => {
    card(s, xs[i], 1.92, nodeW, 1.28, [
      { text: n[0] + " ", options: { fontSize: 13, bold: true, color: C.accent, fontFace: MONO } },
      { text: n[1], options: { fontSize: 13, bold: true, color: C.ink, breakLine: true } },
      { text: n[2], options: { fontSize: 9.5, color: C.sub, paraSpaceBefore: 6 } },
    ]);
    if (i < 3) arrowRight(s, xs[i] + nodeW + 0.08, 2.45, 0.38, 0.24, C.teal);
  });
  arrowDown(s, xs[3] + nodeW / 2 - 0.13, 3.26, 0.26, 0.36, C.teal);
  row2.forEach((n, i) => {
    card(s, xs[i], 3.74, nodeW, 1.28, [
      { text: n[0] + " ", options: { fontSize: 13, bold: true, color: C.accent, fontFace: MONO } },
      { text: n[1], options: { fontSize: 13, bold: true, color: C.ink, breakLine: true } },
      { text: n[2], options: { fontSize: 9.5, color: C.sub, paraSpaceBefore: 6 } },
    ]);
    if (i > 0) arrowLeft(s, xs[i] - 0.46, 4.27, 0.38, 0.24, C.teal);
  });
  // 回环虚线：⑧ → ①（新一轮学习）
  s.addShape("line", { x: xs[0] + nodeW / 2, y: 3.28, w: 0, h: 0.42, line: { color: C.accent, width: 1.5, dashType: "dash", beginArrowType: "triangle" } });
  s.addText([
    { text: "不把大模型用于单轮问答——", options: { fontSize: 14, bold: true, color: C.ink } },
    { text: "形成「画像—知识组织—资源生成—练习反馈」的完整闭环，每一次学习都让系统更懂这个学生。", options: { fontSize: 13, color: C.ink } },
  ], {
    x: ML, y: 5.62, w: CW, h: 0.95, shape: "roundRect", rectRadius: 0.09,
    fill: { color: C.accentBg }, line: { type: "none" }, fontFace: FONT,
    align: "center", valign: "middle", margin: [0.1, 0.24, 0.1, 0.24],
  });
  addFooter(s, 5);
  s.addNotes("蛇形流程：上行左到右 ①②③④，下行右到左 ⑤⑥⑦⑧，虚线回到 ① 表示新一轮学习。");
}

// ============================================================
// S6 系统架构（记忆点页）
// ============================================================
{
  const s = newSlide();
  addHeader(s, "04 · 技术架构", "10 个 Agent 各司其职，LangGraph 编排，共享同一知识中枢");
  const bandX = 1.86, bandW = 12.713 - bandX; // 10.853
  const layerLabel = (txt, y, h, color = C.teal) => {
    s.addText(txt, { x: ML, y, w: 1.1, h, fontFace: FONT, fontSize: 11, bold: true, color, align: "left", valign: "middle" });
  };
  // 交互层
  layerLabel("交互层", 1.74, 0.7);
  const ui = [
    ["remio aApp", "对话为主 + UI 组件"],
    ["MCP 宿主", "14 工具跨宿主调用"],
  ];
  ui.forEach((b, i) => {
    const w = (bandW - 0.2) / 2;
    card(s, bandX + i * (w + 0.2), 1.74, w, 0.7, [
      { text: b[0], options: { fontSize: 11.5, bold: true, color: C.ink, breakLine: true } },
      { text: b[1], options: { fontSize: 9, color: C.sub, paraSpaceBefore: 2 } },
    ], { margin: [0.08, 0.12, 0.06, 0.14] });
  });
  arrowDown(s, 6.5, 2.48, 0.24, 0.2, C.muted);
  // 编排层
  layerLabel("编排层", 2.72, 1.98);
  card(s, bandX, 2.72, bandW, 1.98, "", { fill: C.card, border: C.teal, margin: [0.05, 0.05, 0.05, 0.05] });
  const ctrl = [["Router", "意图路由"], ["Profile", "8 维画像"], ["Planner", "任务拆解"]];
  ctrl.forEach((b, i) => {
    const x = 2.06 + i * 2.55;
    card(s, x, 2.88, 2.15, 0.56, [
      { text: b[0] + "　", options: { fontSize: 11, bold: true, color: C.teal, fontFace: MONO } },
      { text: b[1], options: { fontSize: 10, color: C.ink } },
    ], { fill: C.tealBg, noBorder: true, margin: [0.05, 0.08, 0.05, 0.12] });
    if (i < 2) arrowRight(s, x + 2.19, 3.06, 0.3, 0.2, C.teal);
  });
  s.addText("串行控制面：Profile 优先，其余 Agent 依赖画像", {
    x: 9.85, y: 2.88, w: 2.7, h: 0.56, fontFace: FONT, fontSize: 9, color: C.sub, align: "left", valign: "middle",
  });
  s.addText("生成面 · 并行生成", {
    x: 2.06, y: 3.56, w: 3, h: 0.24, fontFace: FONT, fontSize: 9, bold: true, color: C.accent, align: "left", valign: "middle",
  });
  const pool = [
    ["Doc", "讲义"], ["Quiz", "题目"], ["Code", "代码"],
    ["Media", "导图·PPT"], ["Reading", "阅读"], ["Tutor", "答疑"],
  ];
  const pw = (bandW - 0.36 - 5 * 0.1) / 6; // ≈1.731
  pool.forEach((b, i) => {
    const x = 2.06 + i * (pw + 0.1);
    card(s, x, 3.84, pw, 0.7, [
      { text: b[0], options: { fontSize: 10.5, bold: true, color: C.accent, fontFace: MONO, breakLine: true } },
      { text: b[1], options: { fontSize: 9.5, color: C.ink, paraSpaceBefore: 2 } },
    ], { fill: C.accentBg, noBorder: true, margin: [0.06, 0.06, 0.05, 0.1] });
  });
  arrowDown(s, 6.5, 4.74, 0.24, 0.18, C.muted);
  // 知识层
  layerLabel("知识层", 4.96, 0.8);
  const wiki = [
    ["知识图谱", "章节→知识点→概念 DAG"],
    ["RAG 混合检索", "向量 + BM25 + Rerank"],
    ["内容管理", "生成回写 · 版本管理"],
  ];
  wiki.forEach((b, i) => {
    const w = (bandW - 0.4) / 3;
    card(s, bandX + i * (w + 0.2), 4.96, w, 0.8, [
      { text: b[0], options: { fontSize: 11.5, bold: true, color: C.teal, breakLine: true } },
      { text: b[1], options: { fontSize: 9, color: C.sub, paraSpaceBefore: 2 } },
    ], { fill: C.tealBg, noBorder: true, margin: [0.08, 0.12, 0.06, 0.14] });
  });
  arrowDown(s, 6.5, 5.8, 0.24, 0.16, C.muted);
  // 基础层
  layerLabel("基础层", 6.0, 0.5);
  s.addText("LangGraph StateGraph 编排 · DeepSeek 主模型 + OpenAI 兼容回退 · SQLAlchemy + SQLite / PostgreSQL · numpy 向量检索 + bge-small-zh · MCP stdio JSON-RPC", {
    x: bandX, y: 6.0, w: bandW, h: 0.5, fontFace: FONT, fontSize: 9.5, color: C.sub,
    align: "center", valign: "middle", shape: "roundRect", rectRadius: 0.06,
    fill: { color: C.cardTint }, line: { type: "none" }, margin: [0.04, 0.14, 0.04, 0.14],
  });
  s.addText("编排规则：Router 先行 → Profile 串行优先 → Doc / Quiz / Code / Media 并行生成", {
    x: ML, y: 6.6, w: CW, h: 0.34, fontFace: FONT, fontSize: 11, bold: true, color: C.teal,
    align: "left", valign: "middle",
  });
  addFooter(s, 6);
  s.addNotes("架构页是记忆点。讲清四层：交互层双形态、编排层 10 Agent 分控制面与生成面、知识层 Wiki 三子系统、基础层工程栈。");
}

// ============================================================
// S7 10 Agent 职责表
// ============================================================
{
  const s = newSlide();
  addHeader(s, "04 · 技术架构", "10 个 Agent 与核心语义端点一一对应，职责清晰、可独立扩展");
  const rows = [
    ["Router", "意图识别，路由到正确链路", "route_intent（E1）"],
    ["Profile", "对话式构建 8 维学生画像", "build_profile（E2）"],
    ["Planner", "复合任务分解，规划资源组合", "plan_learning（E3）"],
    ["Doc", "基于 RAG 生成个性化讲义", "generate_document（E4）"],
    ["Quiz", "多类型出题与判题，沉淀薄弱点", "generate_quiz / grade_quiz（E5）"],
    ["Code", "生成可运行 Python 实操案例", "generate_code（E6）"],
    ["Media", "思维导图 / PPT 大纲 / 配图", "generate_mindmap / generate_ppt（E7·E8）"],
    ["Reading", "拓展阅读推荐，联网核实优先", "generate_reading（E9）"],
    ["Tutor", "苏格拉底式答疑，三级兜底", "tutor_answer（E10）"],
    ["Video", "检索推荐 B 站教学视频资源", "search_video（视频扩展端点）"],
  ];
  const header = [
    { text: "Agent", options: { bold: true, color: "FFFFFF", fontSize: 10.5 } },
    { text: "职责", options: { bold: true, color: "FFFFFF", fontSize: 10.5 } },
    { text: "remio 语义端点", options: { bold: true, color: "FFFFFF", fontSize: 10.5 } },
  ];
  const body = rows.map((r, i) => [
    { text: r[0], options: { bold: true, color: C.ink, fontSize: 10.5, fontFace: MONO, fill: { color: i % 2 ? C.cardTint : C.card } } },
    { text: r[1], options: { color: C.ink, fontSize: 10.5, fill: { color: i % 2 ? C.cardTint : C.card } } },
    { text: r[2], options: { color: C.teal, fontSize: 9.5, fontFace: MONO, fill: { color: i % 2 ? C.cardTint : C.card } } },
  ]);
  s.addTable([header, ...body], {
    x: ML, y: 1.78, w: CW, colW: [1.9, 5.6, 4.593],
    rowH: [0.38, ...rows.map(() => 0.415)],
    border: { type: "solid", pt: 0.75, color: C.hair },
    fill: { color: C.teal }, fontFace: FONT, valign: "middle",
    margin: [2, 8, 2, 8], autoPage: false,
  });
  s.addText("另有 E11 会话材料挂载（attach_material）与 3 个扩展端点（PPT 配图 / 薄弱点复习 / 动画分镜），连同主入口与内容事件订阅，共 18 个端点。", {
    x: ML, y: 6.55, w: CW, h: 0.34, fontFace: FONT, fontSize: 9.5, color: C.muted, align: "left", valign: "middle",
  });
  addFooter(s, 7);
  s.addNotes("表格页不必逐行讲，点一行即可：例如 Quiz 负责出题+判题+沉淀薄弱点，端点与平台 api.json 对齐。");
}

// ============================================================
// S8 LLM Wiki 知识中枢
// ============================================================
{
  const s = newSlide();
  addHeader(s, "04 · 技术架构", "LLM Wiki：所有 Agent 共享的知识中枢，内置两门完整课程");
  const subs = [
    ["知识图谱", "章节 → 知识点 → 概念的 DAG 依赖，支撑先修导航与学习路径规划"],
    ["RAG 混合检索", "bge-small-zh 向量 + BM25 双路召回，规则 Rerank 重排，章节级命中"],
    ["内容管理", "Agent 生成内容可回写、版本管理——知识库越用越厚"],
  ];
  subs.forEach((b, i) => {
    const x = ML + i * (3.871 + 0.24);
    card(s, x, 1.82, 3.871, 1.72, [
      { text: b[0], options: { fontSize: 14, bold: true, color: C.teal, breakLine: true } },
      { text: b[1], options: { fontSize: 10.5, color: C.sub, paraSpaceBefore: 8, lineSpacingMultiple: 1.3 } },
    ]);
  });
  const header = [
    { text: "课程", options: { bold: true, color: "FFFFFF", fontSize: 10.5 } },
    { text: "规模", options: { bold: true, color: "FFFFFF", fontSize: 10.5 } },
    { text: "交付形态", options: { bold: true, color: "FFFFFF", fontSize: 10.5 } },
  ];
  const courses = [
    ["计算机网络（CN101）", "13 章：总纲 + 12 讲 + 附录，默认课程", "remio aApp 内置"],
    ["算法设计与分析（ALG101）", "10 章 + 五类习题 + 9 个代码案例 + 4 个实验", "MCP 工具集"],
  ];
  const body = courses.map((r, i) => [
    { text: r[0], options: { bold: true, color: C.ink, fontSize: 10.5, fill: { color: i % 2 ? C.cardTint : C.card } } },
    { text: r[1], options: { color: C.ink, fontSize: 10.5, fill: { color: i % 2 ? C.cardTint : C.card } } },
    { text: r[2], options: { color: C.teal, fontSize: 10, fill: { color: i % 2 ? C.cardTint : C.card } } },
  ]);
  s.addTable([header, ...body], {
    x: ML, y: 3.86, w: CW, colW: [3.3, 6.2, 2.593],
    rowH: [0.38, 0.46, 0.46, 0.46],
    border: { type: "solid", pt: 0.75, color: C.hair },
    fill: { color: C.teal }, fontFace: FONT, valign: "middle",
    margin: [2, 8, 2, 8], autoPage: false,
  });
  s.addText([
    { text: "可扩展性　", options: { fontSize: 11.5, bold: true, color: C.accent } },
    { text: "知识库按目录自动发现注册——新增一门课只需一个目录，可从单科工具扩展为课程平台。", options: { fontSize: 11.5, color: C.ink } },
  ], {
    x: ML, y: 6.0, w: CW, h: 0.66, shape: "roundRect", rectRadius: 0.09,
    fill: { color: C.accentBg }, line: { type: "none" }, fontFace: FONT,
    align: "center", valign: "middle", margin: [0.06, 0.2, 0.06, 0.24],
  });
  addFooter(s, 8);
  s.addNotes("强调防幻觉是赛题刚性要求，Wiki 是所有 Agent 的事实边界；aApp 内置计算机网络，另一门经 MCP 提供。");
}

// ============================================================
// S9 防幻觉三道防线
// ============================================================
{
  const s = newSlide();
  addHeader(s, "04 · 技术架构", "三道防线 + 三级兜底，让每一段内容都可追溯");
  const defs = [
    ["01", "检索锚定", "生成只依据检索命中片段；证据不足时显式标注缺口，绝不编造"],
    ["02", "来源强制", "每段内容附 [来源：章节 > 小节]，可逐句回溯原文"],
    ["03", "输出过滤", "content_guard 校验来源引用，缺失即拦截重写"],
  ];
  defs.forEach((b, i) => {
    const x = ML + i * (3.871 + 0.24);
    card(s, x, 1.82, 3.871, 1.9, [
      { text: b[0], options: { fontSize: 18, bold: true, color: C.accent, fontFace: MONO, breakLine: true } },
      { text: b[1], options: { fontSize: 14, bold: true, color: C.ink, breakLine: true, paraSpaceBefore: 2 } },
      { text: b[2], options: { fontSize: 10, color: C.sub, paraSpaceBefore: 8, lineSpacingMultiple: 1.3 } },
    ]);
  });
  s.addText([
    { text: "remio 侧工程落地　", options: { fontSize: 10.5, bold: true, color: C.darkAccent } },
    { text: "run_prompt(capabilities=\"none\") 物理禁网 · search_notes → read_note 注入知识库正文 · 平台 rag 对 File 笔记失效时的兜底检索链路", options: { fontSize: 10, color: C.darkText, fontFace: MONO } },
  ], {
    x: ML, y: 3.98, w: CW, h: 0.82, shape: "roundRect", rectRadius: 0.09,
    fill: { color: C.dark }, line: { type: "none" }, fontFace: FONT,
    align: "center", valign: "middle", margin: [0.08, 0.2, 0.08, 0.24],
  });
  s.addText("答疑三级兜底：逐级显式升级，卡片标注来源层级，禁止静默切换", {
    x: ML, y: 5.06, w: CW, h: 0.3, fontFace: FONT, fontSize: 10.5, bold: true, color: C.sub, align: "left", valign: "middle",
  });
  const lv = [
    ["层级一 · 课程知识库", "search_notes 命中课程资料"],
    ["层级二 · 会话材料", "E11 上传的笔记 / 课件兜底"],
    ["层级三 · 网络", "仅引用实际抓取过的页面"],
  ];
  lv.forEach((b, i) => {
    const x = ML + i * (3.6 + 0.55);
    card(s, x, 5.46, 3.6, 1.05, [
      { text: b[0], options: { fontSize: 12, bold: true, color: C.teal, breakLine: true } },
      { text: b[1], options: { fontSize: 9.5, color: C.sub, paraSpaceBefore: 4 } },
    ], { fill: C.tealBg, noBorder: true, margin: [0.1, 0.14, 0.08, 0.16] });
    if (i < 2) arrowRight(s, x + 3.68, 5.86, 0.36, 0.24, C.accent);
  });
  addFooter(s, 9);
  s.addNotes("防幻觉是评审重点。强调两点：锚定型端点物理禁网；三级兜底每次升级都在卡片上显式标注来源层级。");
}

// ============================================================
// S10 产品演示动线（记忆点页）
// ============================================================
{
  const s = newSlide();
  addHeader(s, "05 · 产品演示", "5 分钟实测：从一句话到 5 类资源 + 苏格拉底式答疑");
  const steps = [
    ["1", "一句话输入", "「我是计算机大一学生，基础一般，帮我复习 TCP 三次握手」"],
    ["2", "画像确认", "E2 弹出画像卡：专业 / 年级 / 基础 / 目标一次确认"],
    ["3", "计划拆解", "E3 把复习目标拆成讲义 / 题目 / 代码 / 导图 / 阅读"],
    ["4", "并行生成", "5 类资源同时产出，全部附章节级来源引用"],
    ["5", "苏格拉底答疑", "引导式反问作答；知识库 → 材料 → 网络来源显式标注"],
  ];
  const w = 2.246, g = 0.2157;
  steps.forEach((st, i) => {
    const x = ML + i * (w + g);
    card(s, x, 1.9, w, 2.4, [
      { text: st[0], options: { fontSize: 22, bold: true, color: C.accent, fontFace: MONO, breakLine: true } },
      { text: st[1], options: { fontSize: 13, bold: true, color: C.ink, breakLine: true, paraSpaceBefore: 4 } },
      { text: st[2], options: { fontSize: 10.5, color: C.sub, paraSpaceBefore: 8, lineSpacingMultiple: 1.35 } },
    ], { margin: [0.16, 0.14, 0.12, 0.14], valign: "middle" });
  });
  s.addText("5 分钟实测，证明这不是单轮问答。", {
    x: ML, y: 4.62, w: CW, h: 0.4, fontFace: FONT, fontSize: 14, bold: true, color: C.accent, align: "left", valign: "middle",
  });
  const entries = [
    ["remio 市场搜索「EduAgent」安装", ""],
    ["MCP 宿主调用 generate_quiz", ""],
  ];
  entries.forEach((e, i) => {
    const x = ML + i * (5.9265 + 0.24);
    s.addText(e[0], {
      x, y: 5.32, w: 5.9265, h: 0.62, shape: "roundRect", rectRadius: 0.09,
      fill: { color: C.card }, line: { color: C.hair, width: 1 },
      fontFace: MONO, fontSize: 10.5, color: C.teal, align: "center", valign: "middle",
    });
  });
  s.addText("重点记忆点：第 4 步「5 类资源并行生成」 x 第 5 步「苏格拉底式答疑」", {
    x: ML, y: 6.22, w: CW, h: 0.6, shape: "roundRect", rectRadius: 0.09,
    fill: { color: C.tealBg }, line: { type: "none" }, fontFace: FONT,
    fontSize: 11.5, bold: true, color: C.teal, align: "center", valign: "middle",
  });
  addFooter(s, 10);
  s.addNotes("演示动线记忆点：第 4 步并行生成、第 5 步苏格拉底答疑。现场可用触发语实测，亦可在 MCP 宿主调用工具演示。");
}

// ============================================================
// S11 多模态资源产出
// ============================================================
{
  const s = newSlide();
  addHeader(s, "05 · 产品演示", "一次学习请求，并行产出 7 类多模态资源");
  const tiles = [
    ["讲义", "章节结构 + 文末来源引用", "generate_document"],
    ["练习题", "选择 / 填空 / 编程，选错给解析", "generate_quiz"],
    ["代码案例", "可运行 Python，一键复制", "generate_code"],
    ["思维导图", "知识结构可视化", "generate_mindmap"],
    ["PPT 大纲", "教学演示自动生成", "generate_ppt"],
    ["拓展阅读", "联网核实优先，只引真实页面", "generate_reading"],
    ["动画脚本", "算法过程分镜脚本", "generate_animation"],
  ];
  const w = 2.861, g = 0.2167;
  tiles.forEach((t, i) => {
    const row = Math.floor(i / 4), col = i % 4;
    const x = ML + col * (w + g), y = 1.86 + row * (1.75 + 0.25);
    card(s, x, y, w, 1.75, [
      { text: t[0], options: { fontSize: 14.5, bold: true, color: C.ink, breakLine: true } },
      { text: t[1], options: { fontSize: 10, color: C.sub, breakLine: true, paraSpaceBefore: 5, lineSpacingMultiple: 1.25 } },
      { text: t[2], options: { fontSize: 9, color: C.teal, fontFace: MONO, paraSpaceBefore: 8 } },
    ], { valign: "middle" });
  });
  // 第 8 格：关键数据
  card(s, ML + 3 * (w + g), 1.86 + 1.75 + 0.25, w, 1.75, [
    { text: "≥ 5 类", options: { fontSize: 22, bold: true, color: C.accent, breakLine: true } },
    { text: "一次请求并行产出的资源类型", options: { fontSize: 9.5, color: C.ink, breakLine: true, paraSpaceBefore: 5, lineSpacingMultiple: 1.25 } },
    { text: "判题结果自动回写画像", options: { fontSize: 8.5, color: C.sub, paraSpaceBefore: 8 } },
  ], { fill: C.accentBg, noBorder: true, valign: "middle" });
  s.addText("一次「帮我复习 TCP 三次握手」，同时产出讲义、题目、代码、导图与阅读——资源组合随画像变化。", {
    x: ML, y: 6.15, w: CW, h: 0.5, fontFace: FONT, fontSize: 11.5, bold: true, color: C.ink, align: "left", valign: "middle",
  });
  addFooter(s, 11);
  s.addNotes("7 类资源 + 右下关键数据格。强调「并行」与「随画像变化」。");
}

// ============================================================
// S12 remio aApp 落地
// ============================================================
{
  const s = newSlide();
  addHeader(s, "06 · 落地形态", "remio 原生 aApp 已上架市场，18 个端点开箱即用");
  // 左：aApp 身份卡（深墨）
  s.addText([
    { text: "remio 原生 aApp", options: { fontSize: 15, bold: true, color: C.darkText, breakLine: true } },
    { text: "已上架市场", options: { fontSize: 10.5, bold: true, color: C.darkAccent, breakLine: true, paraSpaceBefore: 4, paraSpaceAfter: 18 } },
    { text: "id　　　 eduagent-pro", options: { fontSize: 10.5, color: C.darkText, fontFace: MONO, breakLine: true, paraSpaceAfter: 10 } },
    { text: "版本　　v1", options: { fontSize: 10.5, color: C.darkText, fontFace: MONO, breakLine: true, paraSpaceAfter: 10 } },
    { text: "端点数　18", options: { fontSize: 10.5, color: C.darkText, fontFace: MONO, breakLine: true, paraSpaceAfter: 18 } },
    { text: "11 个核心端点（E1–E11）", options: { fontSize: 9.5, color: C.darkMuted, breakLine: true, paraSpaceAfter: 7 } },
    { text: "5 个扩展端点：判题 / PPT 配图 / 薄弱点复习 / 动画分镜 / B 站视频", options: { fontSize: 9.5, color: C.darkMuted, breakLine: true, paraSpaceAfter: 7 } },
    { text: "另有主入口 + 内容事件订阅", options: { fontSize: 9.5, color: C.darkMuted, breakLine: true } },
    { text: "交互原则：对话为主，card / list / choice 组件为辅", options: { fontSize: 9.5, color: C.darkMuted, breakLine: true, paraSpaceBefore: 12 } },
  ], {
    x: ML, y: 1.86, w: 4.95, h: 4.75, shape: "roundRect", rectRadius: 0.09,
    fill: { color: C.dark }, line: { type: "none" }, fontFace: FONT,
    align: "center", valign: "middle", margin: [0.24, 0.24, 0.2, 0.24],
  });
  // 右：学习资产与自动化
  const feats = [
    ["学习资产沉淀", "画像与错题弱点自动回写 remio 笔记《EduAgent 学生画像》，判题即更新"],
    ["订阅自动化", "画像笔记变更 → POST /_event 自动推送薄弱点自测题到会话"],
    ["每日复习自测", "聊天菜单一键回顾最近答错的知识点，形成复习节奏"],
    ["会话材料挂载", "E11 上传自己的课件 / 笔记，参与检索与生成，成为兜底知识源"],
  ];
  feats.forEach((f, i) => {
    const x = 5.82, w = 12.713 - x;
    card(s, x, 1.86 + i * (1.1 + 0.117), w, 1.1, [
      { text: f[0], options: { fontSize: 12.5, bold: true, color: C.teal, breakLine: true } },
      { text: f[1], options: { fontSize: 10, color: C.sub, paraSpaceBefore: 4 } },
    ], { margin: [0.1, 0.16, 0.08, 0.16] });
  });
  addFooter(s, 12);
  s.addNotes("强调「已上架、可实测」：市场搜 EduAgent 即可安装；自动化是 remio 原生能力（事件订阅 + 消息推送）。");
}

// ============================================================
// S13 双形态交付
// ============================================================
{
  const s = newSlide();
  addHeader(s, "06 · 落地形态", "同一引擎，两种交付：remio aApp 与 MCP 跨宿主");
  const forms = [
    ["01", "remio 原生 aApp", ["赛道官方工具原生作品", "市场 id：eduagent-pro", "定位：参赛本体，开箱即用"]],
    ["02", "MCP 工具集", ["14 个工具 · stdio JSON-RPC", "零新增三方依赖", "定位：任意 MCP 宿主跨产品调用"]],
  ];
  forms.forEach((f, i) => {
    const x = ML + i * (5.9265 + 0.24);
    card(s, x, 1.86, 5.9265, 3.3, [
      { text: f[0], options: { fontSize: 18, bold: true, color: C.accent, fontFace: MONO, breakLine: true } },
      { text: f[1], options: { fontSize: 15, bold: true, color: C.ink, breakLine: true, paraSpaceBefore: 2, paraSpaceAfter: 10 } },
      ...f[2].map((line, j) => ({
        text: line,
        options: { fontSize: 10, color: j === 2 ? C.accent : C.sub, bold: j === 2, breakLine: true, paraSpaceAfter: 6 },
      })),
    ], { margin: [0.2, 0.18, 0.14, 0.18] });
  });
  s.addText([
    { text: "一处研发，多宿主复用　", options: { fontSize: 13.5, bold: true, color: C.accent } },
    { text: "——知识检索与生成能力以 MCP 开放，可被 Claude Desktop 等任何智能体产品调用。", options: { fontSize: 12, color: C.ink } },
  ], {
    x: ML, y: 5.5, w: CW, h: 0.95, shape: "roundRect", rectRadius: 0.09,
    fill: { color: C.accentBg }, line: { type: "none" }, fontFace: FONT,
    align: "center", valign: "middle", margin: [0.08, 0.24, 0.08, 0.24],
  });
  addFooter(s, 13);
  s.addNotes("双形态：同一套 Agent 引擎既服务本赛道（aApp），又能走出 remio（MCP 跨宿主复用）。");
}

// ============================================================
// S14 创新点小结
// ============================================================
{
  const s = newSlide();
  addHeader(s, "07 · 创新性", "五个创新点：画像贯穿、知识中枢、双形态、防幻觉、可观测");
  const inno = [
    ["01", "画像贯穿的生成闭环", "画像不是一次性表单：驱动规划、讲义、练习、答疑，并在判题后持续更新"],
    ["02", "多课程知识中枢", "知识库按目录自动发现注册，从一门课平滑扩展为课程平台"],
    ["03", "双形态同引擎交付", "remio 原生 aApp + MCP 跨宿主复用，一处研发、多处运行"],
    ["04", "防幻觉的工程落地", "三道防线 + 三级兜底；含平台 rag 失效时 search_notes → read_note 兜底链路"],
    ["05", "Agent 可观测", "运行事件全程记录（learning_activities），行为可审计、可复盘"],
  ];
  inno.forEach((it, i) => {
    const y = 1.82 + i * (0.9 + 0.1);
    card(s, ML, y, CW, 0.9, [
      { text: it[0], options: { fontSize: 15, bold: true, color: C.accent, fontFace: MONO } },
      { text: "　" + it[1], options: { fontSize: 13, bold: true, color: C.ink } },
      { text: "　　" + it[2], options: { fontSize: 10.5, color: C.sub } },
    ], { margin: [0.08, 0.2, 0.08, 0.2], valign: "middle" });
  });
  addFooter(s, 14);
  s.addNotes("五个创新点逐条一句话，评委记住 1、3、4 即可。");
}

// ============================================================
// S15 完成度与验收
// ============================================================
{
  const s = newSlide();
  addHeader(s, "07 · 完成度", "主路径全部实测通过，评审可一句话触发全链路");
  const header = [
    { text: "检查项", options: { bold: true, color: "FFFFFF", fontSize: 10.5 } },
    { text: "预期表现", options: { bold: true, color: "FFFFFF", fontSize: 10.5 } },
  ];
  const checks = [
    ["流式输出", "对话流式不白屏；答疑卡片即出并带来源标注"],
    ["来源引用", "讲义 / 答疑末尾附 [来源：章节 > 小节]，可回溯"],
    ["画像生效", "建档后，生成资源的难度与表达随画像变化"],
    ["多资源协同", "一次请求同时产出讲义、练习、代码、导图、阅读等 ≥5 类资源"],
    ["多课程", "「换到算法课」后经 MCP 切换知识库（aApp 内置计算机网络）"],
    ["跨产品", "remio 外宿主可调 generate_quiz / list_courses（MCP）"],
  ];
  const body = checks.map((r, i) => [
    { text: r[0], options: { bold: true, color: C.ink, fontSize: 10.5, fill: { color: i % 2 ? C.cardTint : C.card } } },
    { text: r[1], options: { color: C.ink, fontSize: 10.5, fill: { color: i % 2 ? C.cardTint : C.card } } },
  ]);
  s.addTable([header, ...body], {
    x: ML, y: 1.78, w: CW, colW: [2.5, 9.593],
    rowH: [0.38, ...checks.map(() => 0.42)],
    border: { type: "solid", pt: 0.75, color: C.hair },
    fill: { color: C.teal }, fontFace: FONT, valign: "middle",
    margin: [2, 8, 2, 8], autoPage: false,
  });
  s.addText([
    { text: "评审触发语　", options: { fontSize: 10.5, bold: true, color: C.darkAccent } },
    { text: "「我是计算机大一学生，基础一般，帮我复习 TCP 三次握手」", options: { fontSize: 11, color: C.darkText, fontFace: MONO } },
    { text: "　——建档 → 规划 → 生成 → 判题 → 答疑，全链路实测", options: { fontSize: 10, color: C.darkMuted } },
  ], {
    x: ML, y: 5.32, w: CW, h: 0.85, shape: "roundRect", rectRadius: 0.09,
    fill: { color: C.dark }, line: { type: "none" }, fontFace: FONT,
    align: "center", valign: "middle", margin: [0.08, 0.2, 0.08, 0.24],
  });
  // 量化证据（2026-09-09 实跑，详见 remio/docs/08_评测报告.md）
  const stats = [
    ["142/142", "引擎测试通过"],
    ["11/11", "质量基线通过"],
    ["100%", "RAG top-1（24 条真实查询）"],
    ["18/18", "端点三方一致"],
  ];
  stats.forEach((st, i) => {
    const x = ML + i * (2.873 + 0.2);
    card(s, x, 6.3, 2.873, 0.62, [
      { text: st[0] + "　", options: { fontSize: 14, bold: true, color: C.accent, fontFace: MONO } },
      { text: st[1], options: { fontSize: 9, color: C.sub } },
    ], { fill: C.cardTint, noBorder: true, margin: [0.05, 0.1, 0.05, 0.12] });
  });
  addFooter(s, 15);
  s.addNotes("验收表逐条可测。底部为 2026-09-09 实跑量化基线：142/142 测试、11/11 质量基线、RAG 内容相关 top-1 100%（24 查询）、18 端点三方一致；复现：uv run pytest / tests/evals/eval_rag_hit_real.py / app.mcp_server --self-test。邀请评委用触发语现场实测收口。");
}

// ============================================================
// S16 商业模式与落地规划
// ============================================================
{
  const s = newSlide();
  addHeader(s, "08 · 商业与规划", "从作品到产品：订阅 + 院校共建 + 平台分成，落地金漪湖");
  s.addText("商业模式", {
    x: ML, y: 1.78, w: 3, h: 0.3, fontFace: FONT, fontSize: 13, bold: true, color: C.teal, align: "left", valign: "middle",
  });
  const biz = [
    ["B2C · 学生订阅", "个性化学习包、考试季冲刺包，按学期 / 科目订阅"],
    ["B2B · 院校共建", "课程知识库授权 + 学习分析看板，服务教学数字化"],
    ["平台分成", "remio 市场付费 aApp 与增值内容，随生态规模增长"],
  ];
  biz.forEach((b, i) => {
    card(s, ML, 2.18 + i * (1.25 + 0.15), 5.85, 1.25, [
      { text: b[0], options: { fontSize: 12.5, bold: true, color: C.ink, breakLine: true } },
      { text: b[1], options: { fontSize: 10, color: C.sub, paraSpaceBefore: 5, lineSpacingMultiple: 1.25 } },
    ]);
  });
  s.addText("落地规划", {
    x: 6.82, y: 1.78, w: 3, h: 0.3, fontFace: FONT, fontSize: 13, bold: true, color: C.teal, align: "left", valign: "middle",
  });
  s.addShape("line", { x: 7.06, y: 2.32, w: 0, h: 3.6, line: { color: C.hair, width: 1.5 } });
  const plan = [
    ["2026.09", "复赛优化", "按辅导意见打磨 Demo、文档与演示"],
    ["2026.10", "决赛路演", "现场实测闭环，冲击产业落地奖"],
    ["赛后", "落地转化", "注册落地金义新区，入驻金漪湖 OPC 社区，对接高校课程试点"],
  ];
  plan.forEach((p, i) => {
    const y = 2.18 + i * 1.4;
    s.addShape("ellipse", { x: 6.97, y: y + 0.1, w: 0.18, h: 0.18, fill: { color: C.accent }, line: { type: "none" } });
    s.addText([
      { text: p[0] + "　", options: { fontSize: 10.5, bold: true, color: C.accent, fontFace: MONO } },
      { text: p[1], options: { fontSize: 12.5, bold: true, color: C.ink, breakLine: true } },
      { text: p[2], options: { fontSize: 10, color: C.sub, paraSpaceBefore: 4, lineSpacingMultiple: 1.25 } },
    ], { x: 7.35, y, w: 5.37, h: 1.2, fontFace: FONT, align: "left", valign: "top" });
  });
  s.addText("按大赛要求，获奖项目须注册落地金义新区并入驻金漪湖 OPC 社区——已纳入项目规划，可享人才安居、算力补贴、载体保障等政策。", {
    x: ML, y: 6.35, w: CW, h: 0.5, fontFace: FONT, fontSize: 10.5, color: C.sub,
    align: "center", valign: "middle", shape: "roundRect", rectRadius: 0.09,
    fill: { color: C.cardTint }, line: { type: "none" }, margin: [0.05, 0.2, 0.05, 0.2],
  });
  addFooter(s, 16);
  s.addNotes("商业化不堆数字：讲清三类收入来源与落地动作即可；主动回应「注册落地金义新区」的大赛要求。");
}

// ============================================================
// S17 结尾（深墨）
// ============================================================
{
  const s = newSlide(C.dark);
  drawMotif(
    s,
    [[1.2, 5.2], [2.6, 5.8], [1.8, 6.6], [3.6, 6.4], [0.9, 6.3]],
    [[0, 1], [1, 2], [1, 3], [2, 4], [0, 4]],
    C.darkTeal, "3E5A55"
  );
  s.addText("多 Agent 不是炫技——", {
    x: 0.9, y: 1.7, w: 11.5, h: 0.7, fontFace: FONT, fontSize: 30, bold: true,
    color: C.darkText, align: "left", valign: "middle",
  });
  s.addText([
    { text: "是让「个性化学习」成为", options: { fontSize: 30, bold: true, color: C.darkText } },
    { text: "可交付的闭环", options: { fontSize: 30, bold: true, color: C.darkAccent } },
    { text: "。", options: { fontSize: 30, bold: true, color: C.darkText } },
  ], {
    x: 0.9, y: 2.45, w: 11.5, h: 0.7, fontFace: FONT, align: "left", valign: "middle",
  });
  s.addShape("rect", { x: 0.92, y: 3.45, w: 0.55, h: 0.055, fill: { color: C.darkAccent }, line: { type: "none" } });
  const chips = ["remio 市场搜索「EduAgent」", "MCP：注册即用 14 工具"];
  chips.forEach((c, i) => {
    s.addText(c, {
      x: 0.9 + i * (3.6 + 0.3), y: 3.85, w: 3.6, h: 0.62, shape: "roundRect", rectRadius: 0.09,
      fill: { color: "2A251E" }, line: { color: "4A4238", width: 1 },
      fontFace: MONO, fontSize: 10.5, color: C.darkAccent, align: "center", valign: "middle",
    });
  });
  s.addText("开发者：wannaw　·　开源协议与 AI 工具使用标注见随附《AI 工具与开源合规说明》", {
    x: 4.3, y: 5.0, w: 8.1, h: 0.3, fontFace: FONT, fontSize: 10, color: C.darkMuted, align: "left", valign: "middle",
  });
  s.addText("谢谢观看 · 恳请评委指正", {
    x: 4.3, y: 5.75, w: 8.1, h: 0.5, fontFace: FONT, fontSize: 16, bold: true, color: C.darkText, align: "left", valign: "middle",
  });
  s.addNotes("收口一句话 + 三个体验入口 + 合规声明 + 致谢。");
}

// ---------- 诊断 + 输出 ----------
allSlides.forEach((s) => {
  warnIfSlideHasOverlaps(s, pptx);
  warnIfSlideElementsOutOfBounds(s, pptx);
});

pptx.writeFile({ fileName: "EduAgent-路演PPT.pptx" }).then(() => {
  console.log("OK: EduAgent-路演PPT.pptx, slides =", allSlides.length);
});
