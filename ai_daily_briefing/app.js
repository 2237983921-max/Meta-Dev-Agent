const DATA_URL = "./data/latest.json";

const state = {
  payload: null,
};

function createSkeletons() {
  const newsGrid = document.getElementById("top-news");
  const watchGrid = document.getElementById("watchlist");
  const statsGrid = document.getElementById("stats-grid");

  newsGrid.innerHTML = "";
  watchGrid.innerHTML = "";
  statsGrid.innerHTML = "";

  for (let i = 0; i < 4; i += 1) {
    const block = document.createElement("div");
    block.className = "skeleton";
    statsGrid.appendChild(block);
  }

  for (let i = 0; i < 4; i += 1) {
    const block = document.createElement("div");
    block.className = "skeleton";
    newsGrid.appendChild(block);
  }

  for (let i = 0; i < 4; i += 1) {
    const block = document.createElement("div");
    block.className = "skeleton";
    watchGrid.appendChild(block);
  }
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) {
    node.textContent = value;
  }
}

function renderQuickCards(cards) {
  const root = document.getElementById("quick-cards");
  root.innerHTML = "";
  cards.forEach((card) => {
    const wrap = document.createElement("article");
    wrap.className = "quick-card";

    const title = document.createElement("div");
    title.className = "quick-card-title";
    title.textContent = card.title;

    const body = document.createElement("p");
    body.className = "quick-card-body";
    body.textContent = card.body;

    wrap.append(title, body);
    root.appendChild(wrap);
  });
}

function renderStats(stats) {
  const root = document.getElementById("stats-grid");
  const template = document.getElementById("stat-template");
  root.innerHTML = "";

  const cards = [
    {
      label: "行业新闻",
      value: String(stats.news_count),
      footnote: "今天抓到的 AI 大新闻条数",
    },
    {
      label: "X 动态",
      value: String(stats.x_count),
      footnote: "Gemini / Grok / Claude / ChatGPT 更新数",
    },
    {
      label: "可用源",
      value: `${stats.healthy_sources}/${stats.total_sources}`,
      footnote: "今天能正常刷新的抓取源",
    },
    {
      label: "阅读目标",
      value: "3 min",
      footnote: "默认按晨读节奏压缩信息量",
    },
  ];

  cards.forEach((card) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".stat-label").textContent = card.label;
    node.querySelector(".stat-value").textContent = card.value;
    node.querySelector(".stat-footnote").textContent = card.footnote;
    root.appendChild(node);
  });
}

function renderNews(items) {
  const root = document.getElementById("top-news");
  const template = document.getElementById("news-template");
  root.innerHTML = "";

  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "takeaway";
    empty.textContent = "今天还没有可展示的新闻，先检查数据源。";
    root.appendChild(empty);
    return;
  }

  items.forEach((item) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".tag").textContent = item.theme;
    node.querySelector(".timestamp").textContent = item.published_at;
    node.querySelector("h3").textContent = item.title;
    const originalTitle = node.querySelector(".original-title");
    originalTitle.textContent = item.original_title ? `原文：${item.original_title}` : "";
    originalTitle.style.display = item.original_title ? "block" : "none";
    node.querySelector(".source-brief").textContent = item.source_brief;
    node.querySelector(".ai-body").textContent = item.ai_summary;
    node.querySelector(".source").textContent = item.source;
    const link = node.querySelector("a");
    link.href = item.url || "#";
    root.appendChild(node);
  });
}

function renderWatchlist(items) {
  const root = document.getElementById("watchlist");
  const template = document.getElementById("watch-template");
  root.innerHTML = "";

  items.forEach((item) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".watch-name").textContent = item.name;
    node.querySelector(".watch-focus").textContent = `重点盯：${item.focus}`;
    node.querySelector(".watch-trend").textContent = item.trend;
    node.querySelector(".watch-status").textContent = item.status_line;
    node.querySelector(".watch-time").textContent = item.updated_at ? `最近更新：${item.updated_at}` : "今天还没有新动态";
    const link = node.querySelector(".watch-link");
    link.href = item.profile_url || "#";

    const highlights = node.querySelector(".highlight-list");
    if (!item.highlights.length) {
      const row = document.createElement("div");
      row.className = "highlight-row";
      row.textContent = "暂无更新";
      highlights.appendChild(row);
    } else {
      item.highlights.forEach((highlight) => {
        const row = document.createElement("article");
        row.className = "highlight-row";

        const title = document.createElement("a");
        title.className = "highlight-title";
        title.href = highlight.url || "#";
        title.target = "_blank";
        title.rel = "noreferrer";
        title.textContent = `${highlight.handle} ${highlight.title}`.trim();

        const meta = document.createElement("div");
        meta.className = "timestamp";
        meta.textContent = highlight.published_at;

        if (highlight.original_title) {
          const original = document.createElement("div");
          original.className = "highlight-original";
          original.textContent = `原文：${highlight.original_title}`;
          row.append(title, original, meta);
        } else {
          row.append(title, meta);
        }

        const summary = document.createElement("p");
        summary.className = "highlight-summary";
        summary.textContent = highlight.summary;

        row.append(summary);
        highlights.appendChild(row);
      });
    }

    root.appendChild(node);
  });
}

function formatSourceStatus(status) {
  const labels = {
    ok: "正常",
    stale: "较旧",
    error: "异常",
  };
  return labels[status] || status;
}

function renderSourceHealth(items) {
  const root = document.getElementById("source-health");
  root.innerHTML = "";

  items.forEach((item) => {
    const row = document.createElement("article");
    row.className = "source-row";

    const meta = document.createElement("div");
    meta.className = "source-meta";

    const name = document.createElement("div");
    name.className = "source-name";
    name.textContent = item.name;

    const message = document.createElement("div");
    message.className = "source-message";
    message.textContent = item.message;

    meta.append(name, message);

    const pill = document.createElement("span");
    pill.className = `source-pill ${item.status}`;
    pill.textContent = formatSourceStatus(item.status);

    row.append(meta, pill);
    root.appendChild(row);
  });
}

function renderNotes(items) {
  const root = document.getElementById("notes");
  root.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    root.appendChild(li);
  });
}

function renderPayload(payload) {
  state.payload = payload;
  setText("headline", payload.overview.headline);
  setText("summary", payload.overview.summary);
  setText("generated-label", `生成时间：${payload.generated_label}`);
  setText("mode-label", payload.mode === "demo" ? "当前是演示数据" : "当前是实时数据");

  renderQuickCards(payload.overview.quick_cards || []);
  renderStats(payload.stats);
  renderNews(payload.top_news || []);
  renderWatchlist(payload.x_watchlist || []);
  renderSourceHealth(payload.source_health || []);
  renderNotes(payload.notes || []);
}

async function loadData() {
  createSkeletons();
  const response = await fetch(`${DATA_URL}?t=${Date.now()}`);
  if (!response.ok) {
    throw new Error(`读取失败：${response.status}`);
  }
  const payload = await response.json();
  renderPayload(payload);
}

async function refreshPage() {
  const button = document.getElementById("refresh-button");
  button.disabled = true;
  button.textContent = "刷新中…";
  try {
    await loadData();
  } catch (error) {
    setText("headline", "今天的 AI 早报暂时没有加载成功");
    setText("summary", String(error.message || error));
  } finally {
    button.disabled = false;
    button.textContent = "刷新今天内容";
  }
}

document.getElementById("refresh-button").addEventListener("click", refreshPage);
loadData().catch((error) => {
  setText("headline", "今天的 AI 早报暂时没有加载成功");
  setText("summary", String(error.message || error));
});
