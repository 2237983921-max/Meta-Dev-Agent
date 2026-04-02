(function (global) {
  const FORMAL_AGENT_KEYS = [
    "id",
    "display_name",
    "alias",
    "age",
    "identity",
    "core_interest",
    "main_fear",
    "info_type",
    "dimensions",
    "blind_spot",
    "why_selected",
    "content",
  ];

  const PROCESS_HINT_TERMS = ["正在", "已完成选角", "局长正在", "配置"];

  function normalizeText(text) {
    return String(text || "")
      .replace(/\r/g, "")
      .replace(/\u3000/g, " ")
      .replace(/[ \t]+\n/g, "\n")
      .replace(/[ \t]{2,}/g, " ")
      .trim();
  }

  function stripMarkdown(text) {
    return normalizeText(text)
      .replace(/^#{1,6}\s+/gm, "")
      .replace(/^\s*[-*+]\s+/gm, "")
      .replace(/^\s*\d+\.\s+/gm, "")
      .replace(/^>\s?/gm, "")
      .replace(/`{1,3}([^`]+)`{1,3}/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/[|]/g, " ")
      .replace(/[*_~]/g, "");
  }

  function splitSentences(text) {
    const clean = stripMarkdown(text);
    if (!clean) return [];
    return clean
      .split(/\n+/)
      .flatMap((line) => line.match(/[^。！？!?]+[。！？!?]?/g) || [])
      .map((part) => normalizeText(part))
      .filter(Boolean);
  }

  function parseDirectorSections(markdown) {
    const lines = String(markdown || "").replace(/\r/g, "").split("\n");
    const sections = [];
    let currentTitle = "";
    let currentBody = [];

    function pushSection() {
      const content = normalizeText(currentBody.join("\n"));
      if (!currentTitle && !content) return;
      sections.push({
        title: normalizeText(currentTitle || "总览"),
        content,
      });
    }

    lines.forEach((line) => {
      const heading = line.match(/^#{1,6}\s+(.+?)\s*$/);
      if (heading) {
        pushSection();
        currentTitle = heading[1];
        currentBody = [];
      } else {
        currentBody.push(line);
      }
    });

    pushSection();
    return sections.filter((section) => section.title || section.content);
  }

  function findSection(sections, needles) {
    for (const needle of needles) {
      const matched = sections.find((section) =>
        String(section.title || "").includes(needle)
      );
      if (matched) return matched;
    }
    return null;
  }

  function buildSentencePool(sections) {
    return sections.flatMap((section) =>
      splitSentences(section.content).map((text) => ({
        text,
        source: section.title || "总览",
      }))
    );
  }

  function clampSummaryText(text, maxLength = 92) {
    const clean = normalizeText(text);
    if (!clean || clean.length <= maxLength) return clean;
    const softStops = ["。", "；", "，"];
    for (const stop of softStops) {
      const idx = clean.lastIndexOf(stop, maxLength);
      if (idx >= Math.floor(maxLength * 0.5)) {
        return clean.slice(0, idx + 1);
      }
    }
    return `${clean.slice(0, maxLength - 1)}…`;
  }

  function makeSummaryField(text, source, maxLength) {
    return {
      text: clampSummaryText(text, maxLength),
      source: normalizeText(source || "局长整合报告"),
    };
  }

  function pickSentence(candidates, predicate) {
    return candidates.find((item) => predicate(item.text));
  }

  function extractReaderTargets(text) {
    const candidates = [];
    const patterns = [
      /面向[“"'「]?([^”"'」：:\n]{2,24})[”"'」]?/g,
      /给([^：:\n]{2,20})[:：]/g,
      /最该读这份报告的[^，。；\n]*[，,]([^。；\n]+)/g,
    ];

    patterns.forEach((pattern) => {
      const regex = new RegExp(pattern);
      let match = regex.exec(text);
      while (match) {
        const value = normalizeText(match[1])
          .replace(/^(不是|而是)/, "")
          .replace(/[、，,；;]+$/g, "");
        if (value) candidates.push(value);
        match = regex.exec(text);
      }
    });

    return [...new Set(candidates)].slice(0, 3);
  }

  function extractQuickSummary(state) {
    const formal = collectFormalExportData(state);
    const sections = parseDirectorSections(formal.directorMarkdown);
    const allSentences = buildSentencePool(sections);
    const truthSection =
      findSection(sections, ["立体真相", "真相", "总结"]) || sections[sections.length - 1] || null;
    const conflictSection =
      findSection(sections, ["断层与错位", "深层动力", "表层冲突"]) || truthSection;
    const actionSection = findSection(sections, ["行动建议", "建议"]);
    const blindspotSection =
      findSection(sections, ["隐藏变量", "断层与错位", "表层冲突"]) || conflictSection;

    const truthSentences = buildSentencePool(truthSection ? [truthSection] : []);
    const conflictSentences = buildSentencePool(conflictSection ? [conflictSection] : []);
    const actionSentences = buildSentencePool(actionSection ? [actionSection] : []);
    const blindspotSentences = buildSentencePool(blindspotSection ? [blindspotSection] : []);

    const misconceptionSentence =
      pickSentence(allSentences, (text) => /不是.+而是.+/.test(text)) ||
      blindspotSentences[0] ||
      truthSentences[0] ||
      allSentences[0];

    const oneLineSentence =
      pickSentence(
        truthSentences,
        (text) => /不是.+而是.+|真正|关键|本质|影响/.test(text)
      ) ||
      truthSentences[0] ||
      misconceptionSentence ||
      allSentences[0] || { text: "局长整合报告尚未生成。", source: "局长整合报告" };

    const keyConflictSentence =
      pickSentence(
        conflictSentences,
        (text) => /错位|冲突|分歧|断层|争的不是|差异/.test(text)
      ) ||
      conflictSentences[0] ||
      misconceptionSentence ||
      oneLineSentence;

    const readerSentence =
      pickSentence(
        actionSentences,
        (text) => /最该读|更应该|如果你是|面向|给.+建议|值得/.test(text)
      ) ||
      (() => {
        const targets = extractReaderTargets(actionSection?.content || "");
        if (!targets.length) return null;
        return {
          text: `最该读这份报告的，是${targets.join("、")}。`,
          source: actionSection?.title || "行动建议",
        };
      })() ||
      pickSentence(
        allSentences,
        (text) => /年轻人|家长|老师|平台|决策者|管理者/.test(text)
      ) ||
      oneLineSentence;

    const signatureSentence =
      truthSentences.find((item) => item.text !== oneLineSentence.text) ||
      pickSentence(
        allSentences,
        (text) => /不是.+而是.+|归根到底|最后|真正/.test(text) && text !== oneLineSentence.text
      ) ||
      oneLineSentence;

    return {
      one_line_judgment: makeSummaryField(
        oneLineSentence.text,
        oneLineSentence.source,
        78
      ),
      biggest_misconception: makeSummaryField(
        misconceptionSentence.text,
        misconceptionSentence.source,
        92
      ),
      key_conflict: makeSummaryField(
        keyConflictSentence.text,
        keyConflictSentence.source,
        92
      ),
      priority_readers: makeSummaryField(
        readerSentence.text,
        readerSentence.source,
        92
      ),
      signature_line: makeSummaryField(
        signatureSentence.text,
        signatureSentence.source,
        110
      ),
    };
  }

  function trimForCard(text, maxLength = 120) {
    return clampSummaryText(text, maxLength);
  }

  function scoreSentence(text, preferredPatterns = []) {
    let score = 0;
    preferredPatterns.forEach((pattern, index) => {
      if (pattern.test(text)) score += Math.max(12 - index, 4);
    });
    if (/不是.+而是.+/.test(text)) score += 10;
    if (/最|真正|关键|根本|最大|一定|不会|其实/.test(text)) score += 4;
    if (text.length >= 18 && text.length <= 88) score += 3;
    if (text.length > 120) score -= 3;
    return score;
  }

  function pickBestSentence(sentences, preferredPatterns = []) {
    const pool = sentences.filter(Boolean);
    if (!pool.length) return null;
    return [...pool].sort((a, b) => {
      const scoreDiff =
        scoreSentence(b.text || b, preferredPatterns) -
        scoreSentence(a.text || a, preferredPatterns);
      if (scoreDiff !== 0) return scoreDiff;
      return String(a.text || a).length - String(b.text || b).length;
    })[0];
  }

  function parseNamedBlocks(markdown) {
    return parseDirectorSections(markdown).filter(
      (section) => !/^圆桌激辩|局长整合报告$/i.test(String(section.title || ""))
    );
  }

  function extractActionSuggestions(state, maxItems = 3) {
    const formal = collectFormalExportData(state);
    const sections = parseDirectorSections(formal.directorMarkdown);
    const actionSection = findSection(sections, ["行动建议", "建议"]);
    if (!actionSection) return [];

    const rawBlocks = String(actionSection.content || "")
      .split(/\n+/)
      .map((line) => normalizeText(line))
      .filter(Boolean);

    const grouped = [];
    let current = "";
    rawBlocks.forEach((line) => {
      if (/^(建议[一二三四五六七八九十\d]+[:：]|[\d一二三四五六七八九十]+[、.．])/.test(line)) {
        if (current) grouped.push(current);
        current = line;
      } else if (current) {
        current = `${current} ${line}`;
      } else {
        grouped.push(line);
      }
    });
    if (current) grouped.push(current);

    const blocks = grouped.length ? grouped : rawBlocks;
    return blocks
      .map((text, index) => ({
        title: `建议 ${index + 1}`,
        text: trimForCard(text, 140),
        source: actionSection.title || "行动建议",
      }))
      .slice(0, maxItems);
  }

  function extractAgentHighlights(state, maxItems = 4) {
    const formal = collectFormalExportData(state);
    return formal.agents
      .map((agent) => {
        const sentences = splitSentences(agent.content).map((text) => ({
          text,
          source: agent.display_name || agent.id || "Agent",
        }));
        const best = pickBestSentence(sentences, [
          /不是.+而是.+/,
          /我最|我怕|我担心|我更关心/,
          /关键|根本|真正|说到底/,
        ]);
        if (!best) return null;
        return {
          speaker: agent.display_name || agent.id || "Agent",
          role: agent.alias || agent.identity || "关键视角",
          text: trimForCard(best.text, 92),
          source: "暗房独白",
        };
      })
      .filter(Boolean)
      .slice(0, maxItems);
  }

  function extractRoundtableHighlights(state, maxItems = 3) {
    const formal = collectFormalExportData(state);
    if (!formal.roundtableMarkdown) return [];
    const blocks = parseNamedBlocks(formal.roundtableMarkdown);
    const highlights = blocks
      .map((section) => {
        const sentences = splitSentences(section.content).map((text) => ({
          text,
          source: section.title || "圆桌激辩",
        }));
        const best = pickBestSentence(sentences, [
          /不同意|问题是|你这话|但你忽略了|反过来|补一句/,
          /其实|真正|关键|根本/,
          /共识|一样|反而/,
        ]);
        if (!best) return null;
        return {
          speaker: section.title || "圆桌激辩",
          text: trimForCard(best.text, 92),
          source: "圆桌激辩",
        };
      })
      .filter(Boolean);

    if (highlights.length) return highlights.slice(0, maxItems);

    return splitSentences(formal.roundtableMarkdown)
      .map((text) => ({ speaker: "圆桌激辩", text: trimForCard(text, 92), source: "圆桌激辩" }))
      .slice(0, maxItems);
  }

  function extractDirectorHighlights(state, maxItems = 4) {
    const formal = collectFormalExportData(state);
    const sections = parseDirectorSections(formal.directorMarkdown);
    const desired = [
      ["C. 共识地带", ["共识地带"]],
      ["D. 断层与错位", ["断层与错位"]],
      ["E. 嗓门与筹码", ["嗓门与筹码"]],
      ["F. 隐藏变量", ["隐藏变量"]],
      ["G. 未来触发器", ["未来触发器"]],
      ["H. 立体真相", ["立体真相", "真相"]],
    ];

    return desired
      .map(([label, needles]) => {
        const section = findSection(sections, needles);
        if (!section) return null;
        const sentences = splitSentences(section.content).map((text) => ({
          text,
          source: section.title || label,
        }));
        const best =
          pickBestSentence(sentences, [/不是.+而是.+/, /真正|关键|最|不会|其实/, /共识|错位|按钮|触发器/]) ||
          sentences[0];
        if (!best) return null;
        return {
          title: label.replace(/^[A-Z]\.\s*/, ""),
          text: trimForCard(best.text, 110),
          source: best.source,
        };
      })
      .filter(Boolean)
      .slice(0, maxItems);
  }

  function extractSharePacket(state) {
    const formal = collectFormalExportData(state);
    return {
      quickSummary: extractQuickSummary(formal),
      reportModules: extractReportModules(formal),
      casting: formal.agents.map((agent) => ({
        display_name: agent.display_name || agent.id || "",
        identity: agent.identity || "",
        alias: agent.alias || "关键视角",
        core_interest: agent.core_interest || "",
      })),
      agentHighlights: extractAgentHighlights(formal, 4),
      roundtableHighlights: extractRoundtableHighlights(formal, 3),
      directorHighlights: extractDirectorHighlights(formal, 4),
      actionSuggestions: extractActionSuggestions(formal, 3),
    };
  }

  function hasSectionWithNeedles(sections, needles) {
    return Boolean(findSection(sections, needles));
  }

  function extractReportModules(state) {
    const formal = collectFormalExportData(state);
    const sections = parseDirectorSections(formal.directorMarkdown);
    const userModules = (formal.moduleLabels || []).map((label) => ({
      key: normalizeText(label).toLowerCase(),
      label: normalizeText(label),
      source: "user",
    }));

    const structureDefs = [
      {
        key: "roundtable",
        label: "圆桌激辩",
        enabled: Boolean(formal.roundtableMarkdown),
      },
      {
        key: "voice_vs_power",
        label: "嗓门与筹码",
        enabled: hasSectionWithNeedles(sections, ["嗓门与筹码"]),
      },
      {
        key: "future_triggers",
        label: "未来触发器",
        enabled: hasSectionWithNeedles(sections, ["未来触发器"]),
      },
      {
        key: "action_suggestions",
        label: "行动建议",
        enabled: hasSectionWithNeedles(sections, ["行动建议"]),
      },
      {
        key: "common_ground",
        label: "共识地带",
        enabled: hasSectionWithNeedles(sections, ["共识地带"]),
      },
      {
        key: "fact_layering",
        label: "事实 / 推断 / 情绪分层",
        enabled:
          /事实层|推断层|情绪层/.test(formal.directorMarkdown) ||
          hasSectionWithNeedles(sections, ["事实/推断/情绪分层", "事实 / 推断 / 情绪分层"]),
      },
    ];

    const structureModules = structureDefs
      .filter((item) => item.enabled)
      .map((item) => ({ key: item.key, label: item.label, source: "structure" }));

    const combined = [...userModules];
    const seen = new Set(userModules.map((item) => item.label));
    structureModules.forEach((item) => {
      if (seen.has(item.label)) return;
      combined.push(item);
      seen.add(item.label);
    });

    return {
      userModules,
      structureModules,
      combined,
    };
  }

  function cloneAgent(agent) {
    const next = {};
    FORMAL_AGENT_KEYS.forEach((key) => {
      const value = agent && agent[key];
      if (Array.isArray(value)) {
        next[key] = [...value];
      } else {
        next[key] = value ?? (key === "dimensions" ? [] : "");
      }
    });
    return next;
  }

  function collectFormalExportData(state) {
    const agents = Array.isArray(state?.agents) ? state.agents.map(cloneAgent) : [];
    const decon = state?.topicDeconstruction || {};
    return {
      topicLabel: String(state?.topicLabel || "").trim(),
      modelName: String(state?.modelName || "").trim(),
      depthLabel: String(state?.depthLabel || "").trim(),
      audienceLabel: String(state?.audienceLabel || "").trim(),
      moduleLabels: Array.isArray(state?.moduleLabels) ? [...state.moduleLabels] : [],
      issueType: String(state?.issueType || "").trim(),
      conflictAxes: Array.isArray(state?.conflictAxes) ? [...state.conflictAxes] : [],
      topicDeconstruction: {
        surface_conflict: String(decon.surface_conflict || "").trim(),
        real_dispute: String(decon.real_dispute || "").trim(),
        key_variables: Array.isArray(decon.key_variables) ? [...decon.key_variables] : [],
        loud_but_minor: String(decon.loud_but_minor || "").trim(),
        silent_but_powerful: String(decon.silent_but_powerful || "").trim(),
      },
      agents,
      roundtableMarkdown: String(state?.roundtableMarkdown || "").trim(),
      directorMarkdown: String(state?.directorMarkdown || "").trim(),
    };
  }

  function collectTraceLines(state) {
    return Array.isArray(state?.processLines)
      ? state.processLines.map((line) => String(line || "").trim()).filter(Boolean)
      : [];
  }

  function buildExportText(state, options = {}) {
    const includeTrace = Boolean(options.includeTrace);
    const formal = collectFormalExportData(state);
    const traceLines = includeTrace ? collectTraceLines(state) : [];
    const lines = ["推演局报告", formal.topicLabel || "", `模型：${formal.modelName}`];

    if (formal.depthLabel) lines.push(`分析深度：${formal.depthLabel}`);
    if (formal.audienceLabel) lines.push(`目标读者：${formal.audienceLabel}`);
    if (formal.moduleLabels.length) lines.push(`增强模块：${formal.moduleLabels.join("；")}`);

    if (includeTrace) {
      lines.push("", "【推演过程提示】", ...(traceLines.length ? traceLines : ["无"]));
    }

    if (formal.issueType || formal.conflictAxes.length || formal.agents.length) {
      const decon = formal.topicDeconstruction;
      lines.push("", "【选角总览】");
      if (formal.issueType) lines.push(`议题类型：${formal.issueType}`);
      if (formal.conflictAxes.length) lines.push(`冲突轴：${formal.conflictAxes.join("；")}`);
      formal.agents.forEach((agent) => {
        lines.push(
          `- ${agent.display_name || agent.id || ""}｜${agent.age || ""}｜补充标签：${agent.alias || "关键视角"}`,
          `  身份：${agent.identity || ""}`,
          `  为什么上场：${agent.why_selected || ""}`
        );
      });
      if (decon.surface_conflict) lines.push(`表层冲突：${decon.surface_conflict}`);
      if (decon.real_dispute) lines.push(`实际争议：${decon.real_dispute}`);
      if (decon.key_variables.length) lines.push(`关键变量：${decon.key_variables.join("；")}`);
      if (decon.loud_but_minor) lines.push(`响但次要：${decon.loud_but_minor}`);
      if (decon.silent_but_powerful) lines.push(`沉默但关键：${decon.silent_but_powerful}`);
    }

    if (formal.agents.length) {
      lines.push("", "【Agent 暗房独白】");
      formal.agents.forEach((agent) => {
        lines.push(
          `\n### ${agent.display_name || agent.id || ""}`,
          `年龄：${agent.age || ""}`,
          `补充标签：${agent.alias || "关键视角"}`,
          `身份：${agent.identity || ""}`,
          `利益：${agent.core_interest || ""}`,
          `恐惧：${agent.main_fear || ""}`,
          `维度：${Array.isArray(agent.dimensions) ? agent.dimensions.join(" / ") : ""}`,
          agent.content || ""
        );
      });
    }

    if (formal.roundtableMarkdown) {
      lines.push("", "【圆桌激辩】", formal.roundtableMarkdown);
    }

    lines.push("", "【局长整合报告】", formal.directorMarkdown || "");
    return lines.join("\n");
  }

  function containsProcessHintTerms(text) {
    return PROCESS_HINT_TERMS.some((term) => String(text || "").includes(term));
  }

  const api = {
    PROCESS_HINT_TERMS,
    collectFormalExportData,
    collectTraceLines,
    buildExportText,
    extractQuickSummary,
    extractReportModules,
    extractActionSuggestions,
    extractSharePacket,
    containsProcessHintTerms,
  };

  global.TuYanJuExportUtils = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : window);
