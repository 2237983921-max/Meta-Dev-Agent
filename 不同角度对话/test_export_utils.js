const assert = require("assert");
const ExportUtils = require("./export_utils.js");

const sampleState = {
  topicLabel: "话题：AI 会替代大部分白领工作吗？",
  modelName: "gpt-5",
  depthLabel: "Ultra（顶配高 token）",
  audienceLabel: "普通读者",
  moduleLabels: ["谁会占便宜，谁会吃亏"],
  issueType: "复合型",
  conflictAxes: ["利益分配", "风险承担"],
  topicDeconstruction: {
    surface_conflict: "大家在争 AI 是机会还是威胁",
    real_dispute: "谁会先失去议价权",
    key_variables: ["岗位标准化程度"],
    loud_but_minor: "社交媒体上的口号",
    silent_but_powerful: "企业真实成本压力",
  },
  agents: [
    {
      id: "agent_1",
      display_name: "小红",
      alias: "转行焦虑白领",
      age: "29岁",
      identity: "互联网运营",
      core_interest: "保住收入",
      main_fear: "被边缘化",
      info_type: "一线使用体验",
      dimensions: ["职业迁移"],
      blind_spot: "低估组织惯性",
      why_selected: "代表焦虑白领",
      content: "我最担心的是收入突然掉下去。",
    },
  ],
  roundtableMarkdown: "# 圆桌激辩\n\n## 小红\n我不同意把这事说成谁努力谁赢。",
  directorMarkdown: "# 局长整合报告\n\n真正的问题不是工具本身，而是谁先适应。",
  processLines: [
    "正在校验中转站配置",
    "已完成选角，4 位 Agent 将按顺序依次进入暗房",
    "局长正在拼接全局结构图",
  ],
};

const normalExport = ExportUtils.buildExportText(sampleState, { includeTrace: false });
assert(!normalExport.includes("【推演过程提示】"));
assert(!ExportUtils.containsProcessHintTerms(normalExport));
assert(normalExport.includes("【圆桌激辩】"));
assert(normalExport.includes("我不同意把这事说成谁努力谁赢"));

const traceExport = ExportUtils.buildExportText(sampleState, { includeTrace: true });
assert(traceExport.includes("【推演过程提示】"));
assert(traceExport.includes("正在校验中转站配置"));

const formalOnly = ExportUtils.collectFormalExportData(sampleState);
assert.strictEqual(formalOnly.processLines, undefined);
assert.strictEqual(formalOnly.topicLabel, sampleState.topicLabel);
assert.strictEqual(formalOnly.roundtableMarkdown, sampleState.roundtableMarkdown);

const shortVideoState = {
  topicLabel: "话题：短视频对年轻人的影响大不大",
  directorMarkdown: `# 局长整合报告

## A. 表层冲突
表面上大家在争短视频到底是娱乐工具，还是注意力毒药。

## B. 深层动力
真正拉扯年轻人的，不只是内容本身，而是平台分发、现实压力和低门槛情绪补偿绑在了一起。

## C. 共识地带
看起来最反短视频的家长，和最懂短视频的平台产品，其实都知道一件事：只靠“自觉一点”解决不了问题，得改环境和默认设置。

## D. 断层与错位
最大的错位是，年轻人把短视频当成喘口气，家长和老师把它当成单纯的堕落信号，平台则把它当成留存指标。三方说的不是同一件事。

## E. 嗓门与筹码
声音最大的是道德批评，真正有按钮的是平台和推荐算法，真正长期扛结果的是年轻人自己和陪他生活的家庭、老师。

## F. 隐藏变量
最大的误区不是“年轻人自制力差”，而是把一个被精密设计的注意力系统，误当成单纯的个人习惯问题。

## G. 未来触发器
如果学校、家长和平台只盯使用时长，不改内容密度、推送节奏和默认提醒，局面不会根本好转。

## H. 立体真相
短视频对年轻人的影响当然大，但它大得不在“看了会不会变坏”，而在它正在重新切年轻人的时间感、耐心阈值和现实满足方式。
它既不是纯粹的洪水猛兽，也不是无害消遣；它更像一条被平台修得很滑的下坡路，累的时候最容易一路滑下去。

## 行动建议
建议一：最该读这份报告的，不是已经在骂短视频的人，而是每天都靠它缓冲压力的年轻人、在做产品留存的人、以及正在承担后果的家长和老师。`,
};

const quickSummary = ExportUtils.extractQuickSummary(shortVideoState);
assert(quickSummary.one_line_judgment.text.includes("影响当然大"));
assert(quickSummary.biggest_misconception.text.includes("不是“年轻人自制力差”"));
assert(quickSummary.key_conflict.text.includes("最大的错位"));
assert(quickSummary.priority_readers.text.includes("最该读这份报告"));
assert(quickSummary.signature_line.text.length >= 18);

const reportModules = ExportUtils.extractReportModules({
  ...shortVideoState,
  moduleLabels: ["谁会占便宜，谁会吃亏"],
  roundtableMarkdown: "## 圆桌激辩\n\n有人反驳，也有人补充。",
});
assert(reportModules.combined.some((item) => item.label === "谁会占便宜，谁会吃亏"));
assert(reportModules.combined.some((item) => item.label === "圆桌激辩"));
assert(reportModules.combined.some((item) => item.label === "嗓门与筹码"));
assert(reportModules.combined.some((item) => item.label === "未来触发器"));
assert(reportModules.combined.some((item) => item.label === "行动建议"));

const shareState = {
  topicLabel: "话题：短视频对年轻人的影响大不大",
  modelName: "claude-opus-4-6-thinking",
  depthLabel: "Ultra（顶配高 token）",
  moduleLabels: ["谁会占便宜，谁会吃亏"],
  agents: [
    {
      id: "a1",
      display_name: "小林",
      alias: "被短视频陪伴的学生",
      identity: "大二学生",
      core_interest: "快速放松",
      content: "我不是不知道刷久了会空，可我一天最轻松的时候就是刷短视频那二十分钟。",
    },
    {
      id: "a2",
      display_name: "王老师",
      alias: "学校一线老师",
      identity: "初中班主任",
      core_interest: "学习节奏稳定",
      content: "我最怕的不是孩子看视频，而是他已经很难在一件慢的事情上停下来。",
    },
    {
      id: "a3",
      display_name: "陈产品",
      alias: "平台增长侧",
      identity: "内容平台产品经理",
      core_interest: "留存指标",
      content: "真正决定结果的不是内容好不好，而是默认推荐把人往哪里推。",
    },
  ],
  roundtableMarkdown: `# 圆桌激辩

## 小林
我不同意把责任全丢给年轻人自控差，因为你累到那个份上，手机就是最低成本的出口。

## 王老师
我同意压力是真的，但问题是你把“出口”做成了默认入口，最后孩子连安静十分钟都做不到。

## 陈产品
你们都说得对，但真正有按钮的人不是孩子，也不是老师，是推荐系统和默认设置。`,
  directorMarkdown: `# 局长整合报告

## C. 共识地带
看起来最反短视频的老师，和最懂增长的产品经理，其实都知道一件事：只靠喊“自律一点”没有用。

## D. 断层与错位
最大的错位是，年轻人把短视频当成喘口气，家长和老师把它当成堕落信号，平台把它当成留存指标。

## E. 嗓门与筹码
声音最大的是道德批评，真正有按钮的是平台和推荐算法。

## F. 隐藏变量
最大的误区不是年轻人自制力差，而是把一个被精密设计的注意力系统，误当成单纯的个人习惯问题。

## G. 未来触发器
如果学校、家长和平台只盯使用时长，不改推送密度和默认提醒，局面不会根本好转。

## H. 立体真相
短视频对年轻人的影响当然大，但它大得不在“会不会带坏人”，而在它正在改写年轻人的时间感和满足方式。

## 行动建议
建议一：给年轻人先减压，不要一边把他推到高压环境里，一边只要求他自律。
建议二：给家长和老师一个看得懂的判断框架，别把所有问题都归到“孩子意志差”。
建议三：平台先改默认设置，把最容易连刷的机制往后放。`,
};

const sharePacket = ExportUtils.extractSharePacket(shareState);
assert.strictEqual(sharePacket.agentHighlights.length, 3);
assert.strictEqual(sharePacket.roundtableHighlights.length, 3);
assert(sharePacket.directorHighlights.some((item) => item.title === "嗓门与筹码"));
assert.strictEqual(sharePacket.actionSuggestions.length, 3);
assert(sharePacket.actionSuggestions[0].text.includes("给年轻人先减压"));

console.log("export utils ok");
