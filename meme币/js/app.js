(function() {
  "use strict";

  const CHAIN_COLORS = {
    SOLANA: "#9f7bff",
    ETHEREUM: "#6f8cff",
    BASE: "#59c3ff",
    BSC: "#ffd166"
  };

  const tracker = new MemeTracker();
  const dashboardFilterState = { mode: "all" };
  const fullFeedState = { mode: "all", query: "" };
  const tableState = { range: "24h" };
  let lastErrorToast = "";
  let currentPage = "dashboard";

  const dom = {
    navItems: document.querySelectorAll(".nav-item"),
    pages: document.querySelectorAll(".page"),
    feedFilter: document.getElementById("feed-filter"),
    fullFeedSearch: document.getElementById("feed-search"),
    searchInput: document.getElementById("search-input"),
    chipButtons: document.querySelectorAll(".filter-chips .chip"),
    rangeTabs: document.querySelectorAll(".panel-tabs .tab"),
    pauseFeedButton: document.getElementById("pause-feed"),
    toggleSoundButton: document.getElementById("toggle-sound"),
    clearAlertsButton: document.getElementById("clear-alerts"),
    toggleAlertsButton: document.getElementById("toggle-alerts"),
    heroTrendingButton: document.getElementById("hero-open-trending"),
    heroSettingsButton: document.getElementById("hero-open-settings"),
    saveSettingsButton: document.getElementById("save-settings"),
    tokenModal: document.getElementById("token-modal"),
    modalClose: document.getElementById("modal-close"),
    modalTrackButton: document.getElementById("modal-track-btn")
  };

  bindNavigation();
  bindControls();
  hydrateSettingsForm();
  renderAll();
  tracker.start();

  tracker.onDataUpdate = (_dashboard, meta) => {
    lastErrorToast = "";
    renderAll();
    if (currentPage === "trending") renderTrendingPage();
    if (currentPage === "feed") renderFullFeed();
    if (currentPage === "alerts") renderFullAlerts();
    if (currentPage === "kol") renderCommunityPage();

    meta.newAlerts
      .filter((alert) => shouldNotify(alert))
      .slice(0, 3)
      .forEach((alert) => showToast(alertToastType(alert.type), alert.title, alert.description));
  };

  tracker.onStatsUpdate = () => {
    updateStats();
    updatePulse();
    updateConnectionStatus();
    renderWatchlist();
    renderSignals();
  };

  tracker.onWatchlistChange = () => {
    renderDashboardFeed();
    renderTokenTable();
    renderWatchlist();
    renderSignals();
    if (currentPage === "feed") renderFullFeed();
    if (currentPage === "trending") renderTrendingPage();
    updateTrackButtonState(currentModalSymbol());
  };

  tracker.onSettingsChange = () => {
    hydrateSettingsForm();
    updateSoundButton();
    updateConnectionStatus();
  };

  tracker.onError = (message) => {
    updateConnectionStatus();
    if (message !== lastErrorToast) {
      lastErrorToast = message;
      showToast("warning", "实时数据连接异常", message);
    }
  };

  function bindNavigation() {
    dom.navItems.forEach((item) => {
      item.addEventListener("click", () => switchPage(item.dataset.page));
    });
  }

  function bindControls() {
    dom.feedFilter?.addEventListener("change", (event) => {
      dashboardFilterState.mode = event.target.value;
      renderDashboardFeed();
    });

    dom.fullFeedSearch?.addEventListener("input", (event) => {
      fullFeedState.query = event.target.value;
      renderFullFeed();
    });

    dom.chipButtons.forEach((chip) => {
      chip.addEventListener("click", () => {
        dom.chipButtons.forEach((button) => button.classList.remove("active"));
        chip.classList.add("active");
        fullFeedState.mode = chip.dataset.filter;
        renderFullFeed();
      });
    });

    dom.rangeTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        dom.rangeTabs.forEach((button) => button.classList.remove("active"));
        tab.classList.add("active");
        tableState.range = tab.dataset.range;
        renderTokenTable();
      });
    });

    dom.pauseFeedButton?.addEventListener("click", () => {
      tracker.feedPaused = !tracker.feedPaused;
      dom.pauseFeedButton.innerHTML = tracker.feedPaused
        ? '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>'
        : '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>';
      showToast("info", tracker.feedPaused ? "自动刷新已暂停" : "自动刷新已恢复", tracker.feedPaused ? "后端不会继续轮询，页面会保留当前快照。" : "现在会按你设置的刷新频率自动拉取真实数据。");
    });

    dom.toggleSoundButton?.addEventListener("click", () => {
      tracker.updateSettings({ soundEnabled: !tracker.settings.soundEnabled });
      showToast("info", tracker.settings.soundEnabled ? "声音提醒已开启" : "声音提醒已关闭", "这个偏好会保存在浏览器本地。");
    });

    dom.clearAlertsButton?.addEventListener("click", () => {
      tracker.markAllAlertsRead();
      renderAlertsList();
      if (currentPage === "alerts") {
        renderFullAlerts();
      }
    });

    dom.toggleAlertsButton?.addEventListener("click", () => switchPage("alerts"));
    dom.heroTrendingButton?.addEventListener("click", () => switchPage("trending"));
    dom.heroSettingsButton?.addEventListener("click", () => switchPage("settings"));
    dom.saveSettingsButton?.addEventListener("click", saveSettingsFromForm);

    dom.searchInput?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        openSearchedToken();
      }
    });

    dom.modalClose?.addEventListener("click", () => dom.tokenModal.classList.add("hidden"));
    dom.tokenModal?.addEventListener("click", (event) => {
      if (event.target === dom.tokenModal) {
        dom.tokenModal.classList.add("hidden");
      }
    });

    dom.modalTrackButton?.addEventListener("click", () => {
      const symbol = dom.modalTrackButton.dataset.symbol;
      if (!symbol) return;

      const isWatching = tracker.toggleWatchlist(symbol);
      showToast("success", isWatching ? `${symbol} 已加入观察列表` : `${symbol} 已移出观察列表`, isWatching ? "这个代币以后会在榜单和信号流里优先高亮。" : "它仍然会继续出现在真实行情榜单里。");
    });

    document.addEventListener("keydown", (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        dom.searchInput?.focus();
      }
      if (event.key === "Escape") {
        dom.tokenModal?.classList.add("hidden");
      }
    });
  }

  function switchPage(page) {
    currentPage = page;
    dom.navItems.forEach((item) => item.classList.toggle("active", item.dataset.page === page));
    dom.pages.forEach((pageNode) => pageNode.classList.toggle("active", pageNode.id === `page-${page}`));

    if (page === "feed") renderFullFeed();
    if (page === "trending") renderTrendingPage();
    if (page === "alerts") renderFullAlerts();
    if (page === "kol") renderCommunityPage();
  }

  function renderAll() {
    updateSoundButton();
    updateStats();
    updatePulse();
    updateConnectionStatus();
    renderDashboardFeed();
    renderTokenTable();
    renderAlertsList();
    renderWatchlist();
    renderSignals();
    renderHeatmap();
  }

  function renderDashboardFeed() {
    const items = tracker.getFeedItems({ mode: dashboardFilterState.mode });
    renderFeedIntoContainer("feed-list", items.slice(0, 28));
  }

  function renderFullFeed() {
    const items = tracker.getFeedItems(fullFeedState);
    renderFeedIntoContainer("full-feed-list", items.slice(0, 80));
  }

  function renderFeedIntoContainer(containerId, items) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";

    if (!items.length) {
      container.innerHTML = '<div class="empty-state">当前筛选条件下还没有匹配到的市场信号，等下一轮刷新或换一个关键词试试。</div>';
      return;
    }

    items.forEach((item) => {
      const token = tracker.searchToken(item.symbol || "");
      const node = document.createElement("div");
      node.innerHTML = createFeedItemHTML(item, token);
      const element = node.firstElementChild;
      if (token) {
        element.addEventListener("click", () => showTokenModal(token.symbol));
        element.querySelectorAll(".token-mention").forEach((badge) => {
          badge.addEventListener("click", (event) => {
            event.stopPropagation();
            showTokenModal(token.symbol);
          });
        });
      }
      container.appendChild(element);
    });
  }

  function createFeedItemHTML(item, token) {
    const tags = [];
    if (item.type === "new-pair") tags.push('<span class="feed-tag new-token">🆕 新币</span>');
    if (item.type === "boosted") tags.push('<span class="feed-tag pump">🔥 Boost</span>');
    if (item.type === "volume-spike") tags.push('<span class="feed-tag hot">⚡ 量能</span>');
    if (item.type === "momentum-up") tags.push('<span class="feed-tag hot">📈 动量</span>');
    if (tracker.isWatchlisted(item.symbol)) tags.push('<span class="feed-tag watch">🎯 观察列表</span>');

    const highlightClass = item.importance >= 80 ? "highlight" : "";
    const watchClass = tracker.isWatchlisted(item.symbol) ? "watchlisted" : "";
    const tokenVisual = renderTokenVisual(token, "feed-avatar");
    const chainColor = token ? (CHAIN_COLORS[token.chain?.toUpperCase?.()] || "#c5d9e7") : "#c5d9e7";

    return `
      <div class="feed-item ${highlightClass} ${watchClass}">
        ${tokenVisual}
        <div class="feed-content">
          <div class="feed-user">
            <span class="feed-username">${escapeHTML(item.title)}</span>
            <span class="feed-handle">${escapeHTML(item.symbol || "")}</span>
            <span class="feed-handle">${escapeHTML(item.chain || "")}</span>
            <span class="feed-time">${formatTime(item.timestamp)}</span>
          </div>
          <div class="feed-text">${escapeHTML(item.description)} ${item.symbol ? `<span class="token-mention" data-token="${item.symbol}">${escapeHTML(item.symbol)}</span>` : ""}</div>
          <div class="feed-tags">${tags.join("")}</div>
          <div class="feed-meta">
            <span>价格 ${formatPrice(item.priceUsd || 0)}</span>
            <span>24H ${formatSigned(item.priceChange24h || 0)}%</span>
            <span>成交 ${formatCurrency(item.volumeH24 || 0)}</span>
            <span style="margin-left:auto;color:${chainColor};font-weight:700;">优先级 ${item.importance}</span>
          </div>
        </div>
      </div>
    `;
  }

  function renderTokenTable() {
    const container = document.getElementById("token-table-body");
    if (!container) return;
    container.innerHTML = "";

    const header = document.getElementById("table-volume-label");
    const tokens = getRankedTokensForTable().slice(0, 10);

    if (header) {
      header.textContent = tableState.range === "1h" ? "1h 成交" : tableState.range === "7d" ? "市值" : "24h 成交";
    }

    tokens.forEach((token, index) => {
      const sentimentClass = token.sentiment >= 66 ? "positive" : token.sentiment >= 45 ? "neutral" : "negative";
      const watching = tracker.isWatchlisted(token.symbol);
      const canvasId = `spark-${token.id.replace(/[^a-z0-9]/gi, "")}`;
      const secondaryMetric = tableState.range === "1h"
        ? formatCurrency(token.volume.h1)
        : tableState.range === "7d"
          ? formatCurrency(token.marketCap)
          : formatCurrency(token.volume.h24);
      const row = document.createElement("div");
      row.className = `token-row ${watching ? "watchlisted" : ""}`;
      row.innerHTML = `
        <span class="col-rank">${index + 1}</span>
        <span class="col-name">
          ${renderTokenVisual(token, "token-icon-small")}
          <span class="token-info-col">
            <span class="token-ticker">${escapeHTML(token.symbol)}</span><br>
            <span class="token-chain-tag">${escapeHTML(token.chain)} · ${escapeHTML(token.dexId || "")}</span>
          </span>
        </span>
        <span class="col-mentions">${secondaryMetric}</span>
        <span class="col-sentiment">
          <span class="sentiment-wrap">
            <span class="sentiment-bar">
              <span class="sentiment-bar-fill ${sentimentClass}" style="width:${token.sentiment}%"></span>
            </span>
            <span class="muted">${token.sentiment}%</span>
          </span>
        </span>
        <span class="col-chart"><canvas id="${canvasId}" width="82" height="30"></canvas></span>
        <span class="col-action">
          <button class="action-btn ${watching ? "watching" : ""}" data-symbol="${token.symbol}">
            ${watching ? "已追踪" : "追踪"}
          </button>
        </span>
      `;
      row.addEventListener("click", () => showTokenModal(token.symbol));
      row.querySelector(".action-btn").addEventListener("click", (event) => {
        event.stopPropagation();
        const isWatching = tracker.toggleWatchlist(token.symbol);
        showToast("success", isWatching ? `${token.symbol} 已加入观察列表` : `${token.symbol} 已移出观察列表`, "这是本地状态，不影响实时行情拉取。");
      });
      container.appendChild(row);

      requestAnimationFrame(() => {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const color = token.score >= 76 ? "#68ffb6" : token.score >= 60 ? "#ffce73" : "#ff5d84";
        SparklineChart.draw(canvas, token.sparkline, color);
      });
    });
  }

  function getRankedTokensForTable() {
    const tokens = [...tracker.getTrendingTokens()];

    if (tableState.range === "1h") {
      return tokens.sort((left, right) => (right.priceChange.h1 + right.volume.h1 / 20_000) - (left.priceChange.h1 + left.volume.h1 / 20_000));
    }

    if (tableState.range === "7d") {
      return tokens.sort((left, right) => (right.marketCap + right.liquidityUsd * 3) - (left.marketCap + left.liquidityUsd * 3));
    }

    return tokens;
  }

  function renderAlertsList() {
    renderAlertsIntoContainer("alerts-list", tracker.getAlerts().slice(0, 16));
  }

  function renderFullAlerts() {
    renderAlertsIntoContainer("full-alerts-list", tracker.getAlerts());
  }

  function renderAlertsIntoContainer(containerId, alerts) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";

    if (!alerts.length) {
      container.innerHTML = '<div class="empty-state">还没有高优先提醒。真实数据刷新后，重要的 Boost、新币和量能异常会出现在这里。</div>';
      return;
    }

    alerts.forEach((alert) => {
      const token = tracker.searchToken(alert.symbol || "");
      const item = document.createElement("div");
      item.className = `alert-item ${alert.read ? "" : "unread"}`.trim();
      item.innerHTML = `
        <div class="alert-icon ${alertCssClass(alert.type)}">${alertBadge(alert.type)}</div>
        <div class="alert-content">
          <div class="alert-title">${escapeHTML(alert.title)}</div>
          <div class="alert-desc">${escapeHTML(alert.description)}</div>
          <div class="alert-time">${formatTime(alert.timestamp)}</div>
        </div>
      `;

      if (token) {
        item.style.cursor = "pointer";
        item.addEventListener("click", () => {
          tracker.markAlertRead(alert.id);
          showTokenModal(token.symbol);
          renderAlertsList();
          if (currentPage === "alerts") renderFullAlerts();
        });
      }

      container.appendChild(item);
    });
  }

  function renderWatchlist() {
    const container = document.getElementById("watchlist-list");
    if (!container) return;
    container.innerHTML = "";

    const watchlist = tracker.getTrendingTokens().filter((token) => tracker.isWatchlisted(token.symbol));
    if (!watchlist.length) {
      container.innerHTML = '<div class="empty-state">观察列表还是空的。你可以从热榜或详情弹窗把真实跟踪目标加进来。</div>';
      return;
    }

    watchlist.forEach((token) => {
      const card = document.createElement("div");
      card.className = "watch-card";
      card.innerHTML = `
        <div class="watch-card-header">
          <div class="watch-card-title">
            ${renderTokenVisual(token, "token-icon-small")}
            <span>${escapeHTML(token.symbol)}</span>
          </div>
          <span class="watch-card-score">Signal ${token.score}</span>
        </div>
        <div class="watch-card-meta">
          <span>${escapeHTML(token.chain)}</span>
          <span>价格 ${formatPrice(token.priceUsd)}</span>
          <span>24H ${formatSigned(token.priceChange.h24)}%</span>
          <span>成交 ${formatCurrency(token.volume.h24)}</span>
        </div>
      `;
      card.addEventListener("click", () => showTokenModal(token.symbol));
      container.appendChild(card);
    });
  }

  function renderSignals() {
    const container = document.getElementById("signal-list");
    if (!container) return;
    container.innerHTML = "";

    tracker.getTrendingTokens().slice(0, 6).forEach((token) => {
      const levelClass = token.score >= 78 ? "hot" : token.score >= 65 ? "good" : "warm";
      const item = document.createElement("div");
      item.className = "signal-item";
      item.innerHTML = `
        <div class="signal-item-header">
          <div class="signal-token">
            ${renderTokenVisual(token, "token-icon-small")}
            <div>
              <div><strong>${escapeHTML(token.symbol)}</strong></div>
              <div class="signal-meta">${escapeHTML(token.chain)} · ${escapeHTML((token.tags || []).join(" · ") || "实时行情")}</div>
            </div>
          </div>
          <span class="score-pill ${levelClass}">${token.score}</span>
        </div>
        <div class="signal-bar"><div class="signal-bar-fill" style="width:${token.score}%"></div></div>
      `;
      item.addEventListener("click", () => showTokenModal(token.symbol));
      container.appendChild(item);
    });
  }

  function renderHeatmap() {
    const container = document.getElementById("heatmap-container");
    if (!container) return;
    container.innerHTML = "";

    tracker.getTrendingTokens().slice(0, 18).forEach((token) => {
      const size = Math.max(12, Math.min(30, 12 + token.score / 5));
      const hue = token.sentiment >= 68 ? 150 : token.sentiment >= 45 ? 45 : 348;
      const alpha = Math.min(1, 0.28 + token.score / 140);
      const item = document.createElement("span");
      item.className = "heatmap-item";
      item.textContent = `${token.symbol}`;
      item.style.fontSize = `${size}px`;
      item.style.background = `hsla(${hue}, 85%, 56%, 0.12)`;
      item.style.border = `1px solid hsla(${hue}, 85%, 56%, 0.2)`;
      item.style.color = `hsla(${hue}, 90%, 78%, ${alpha})`;
      item.addEventListener("click", () => showTokenModal(token.symbol));
      container.appendChild(item);
    });
  }

  function renderTrendingPage() {
    const container = document.getElementById("trending-grid");
    if (!container) return;
    container.innerHTML = "";

    tracker.getTrendingTokens().forEach((token) => {
      const canvasId = `trend-${token.id.replace(/[^a-z0-9]/gi, "")}`;
      const card = document.createElement("article");
      card.className = "trending-card";
      card.innerHTML = `
        <div class="trending-card-header">
          ${renderTokenVisual(token, "trending-card-icon")}
          <div>
            <div class="trending-card-name">${escapeHTML(token.name)}</div>
            <div class="trending-card-ticker">${escapeHTML(token.symbol)} · ${escapeHTML(token.chain)}</div>
          </div>
        </div>
        <div class="trending-card-stats">
          <div class="trending-stat">
            <span class="trending-stat-label">价格</span>
            <span class="trending-stat-value">${formatPrice(token.priceUsd)}</span>
          </div>
          <div class="trending-stat">
            <span class="trending-stat-label">24H 涨跌</span>
            <span class="trending-stat-value ${token.priceChange.h24 >= 0 ? "up" : "down"}">${formatSigned(token.priceChange.h24)}%</span>
          </div>
          <div class="trending-stat">
            <span class="trending-stat-label">24H 成交</span>
            <span class="trending-stat-value">${formatCurrency(token.volume.h24)}</span>
          </div>
          <div class="trending-stat">
            <span class="trending-stat-label">流动性</span>
            <span class="trending-stat-value">${formatCurrency(token.liquidityUsd)}</span>
          </div>
        </div>
        <div class="trending-card-chart"><canvas id="${canvasId}" width="260" height="60"></canvas></div>
        <div class="trending-card-footer">
          <span>${escapeHTML((token.tags || []).join(" · ") || "实时行情")}</span>
          <span>${tracker.isWatchlisted(token.symbol) ? "已在观察列表" : `Signal ${token.score}`}</span>
        </div>
      `;
      card.addEventListener("click", () => showTokenModal(token.symbol));
      container.appendChild(card);

      requestAnimationFrame(() => {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const color = token.priceChange.h24 >= 0 ? "#68ffb6" : "#ff5d84";
        SparklineChart.draw(canvas, token.sparkline, color, 0.16);
      });
    });
  }

  function renderCommunityPage() {
    const container = document.getElementById("kol-grid");
    if (!container) return;
    container.innerHTML = "";

    const cards = tracker.getCommunityProjects();
    if (!cards.length) {
      container.innerHTML = '<div class="empty-state">这些代币暂时没有返回可用的社媒链接。</div>';
      return;
    }

    cards.forEach((project) => {
      const card = document.createElement("article");
      card.className = "kol-card";
      card.innerHTML = `
        <div class="kol-header">
          ${renderTokenVisual(project, "kol-avatar")}
          <div>
            <div class="kol-name">${escapeHTML(project.name)}</div>
            <div class="kol-handle">${escapeHTML(project.symbol)} · ${escapeHTML(project.chain)}</div>
            <div class="kol-followers">Boost ${project.boostActive} · 社媒 ${project.socialCount} 个</div>
          </div>
        </div>
        <div class="kol-recent">
          <h4>项目链接</h4>
          <div class="kol-tweet">
            ${project.twitter ? `<div><a href="${project.twitter}" target="_blank" rel="noreferrer">Twitter / X</a></div>` : ""}
            ${project.telegram ? `<div><a href="${project.telegram}" target="_blank" rel="noreferrer">Telegram</a></div>` : ""}
            ${project.website ? `<div><a href="${project.website}" target="_blank" rel="noreferrer">Website</a></div>` : ""}
            ${project.description ? `<div style="margin-top:8px;">${escapeHTML(project.description)}</div>` : ""}
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  }

  function showTokenModal(symbol) {
    const token = tracker.searchToken(symbol);
    if (!token) return;

    const modalIcon = document.getElementById("modal-icon");
    modalIcon.innerHTML = token.icon
      ? `<img src="${escapeAttribute(token.icon)}" alt="${escapeAttribute(token.symbol)}">`
      : escapeHTML(token.symbolRaw.slice(0, 1).toUpperCase());

    document.getElementById("modal-name").textContent = token.name;
    document.getElementById("modal-ticker").textContent = token.symbol;
    document.getElementById("modal-chain").textContent = token.chain.toUpperCase();
    document.getElementById("modal-mentions").textContent = formatPrice(token.priceUsd);
    document.getElementById("modal-users").textContent = token.socialCount;
    document.getElementById("modal-sentiment").textContent = `${token.sentiment}%`;
    document.getElementById("modal-discovered").textContent = token.ageHours < 9999 ? `${token.ageHours.toFixed(1)} 小时前` : "-";
    document.getElementById("modal-score").textContent = token.score;
    document.getElementById("modal-volume").textContent = formatCurrency(token.volume.h24);

    const dexLink = document.getElementById("modal-dex-link");
    dexLink.href = token.pairUrl || "#";
    dexLink.textContent = "DEX Screener";

    const twitterLink = document.getElementById("modal-twitter-link");
    twitterLink.href = token.links.twitter || `https://twitter.com/search?q=${encodeURIComponent(token.symbol)}`;
    twitterLink.textContent = token.links.twitter ? "项目 X" : "X 搜索";

    updateTrackButtonState(token.symbol);

    const relatedSignals = tracker.getFeedItems({ mode: "all" }).filter((item) => item.tokenId === token.id).slice(0, 5);
    const list = document.getElementById("modal-tweets-list");
    list.innerHTML = "";

    if (!relatedSignals.length) {
      list.innerHTML = '<div class="empty-state" style="min-height:120px;">当前没有更多与这个代币关联的即时信号。</div>';
    } else {
      relatedSignals.forEach((signal) => {
        const item = document.createElement("div");
        item.style.cssText = "padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:13px;";
        item.innerHTML = `
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
            <strong>${escapeHTML(signal.title)}</strong>
            <span class="muted">${escapeHTML(signal.badge || "")}</span>
            <span class="muted" style="margin-left:auto;">${formatTime(signal.timestamp)}</span>
          </div>
          <div style="line-height:1.6;color:var(--text-secondary);">${escapeHTML(signal.description)}</div>
        `;
        list.appendChild(item);
      });
    }

    requestAnimationFrame(() => {
      const canvas = document.getElementById("modal-chart");
      const color = token.priceChange.h24 >= 0 ? "#68ffb6" : "#ff5d84";
      SparklineChart.drawModalChart(canvas, token.sparkline, color);
    });

    dom.tokenModal.classList.remove("hidden");
  }

  function updateTrackButtonState(symbol) {
    if (!dom.modalTrackButton || !symbol) return;
    const watching = tracker.isWatchlisted(symbol);
    dom.modalTrackButton.dataset.symbol = symbol;
    dom.modalTrackButton.textContent = watching ? "移出观察列表" : "加入观察列表";
  }

  function currentModalSymbol() {
    return dom.modalTrackButton?.dataset.symbol || "";
  }

  function updateStats() {
    const stats = tracker.getStats();
    const summary = tracker.dashboard.summary || {};
    document.getElementById("stat-scanned").textContent = stats.scanned;
    document.getElementById("stat-detected").textContent = stats.detected;
    document.getElementById("stat-alerts").textContent = stats.alerts;
    document.getElementById("stat-watchlist").textContent = stats.watchlist;
    document.getElementById("stat-scanned-rate").textContent = Math.max(1, Math.round(60 / (tracker.getScanDelayMs() / 1000)));
    document.getElementById("sidebar-tweets").textContent = stats.scanned;
    document.getElementById("sidebar-tokens").textContent = stats.detected;
    document.getElementById("sidebar-watchlist").textContent = stats.watchlist;
    document.getElementById("alert-badge").textContent = stats.alerts;
    document.getElementById("nav-alert-count").textContent = stats.alerts;
    document.getElementById("stat-market-mode").textContent = summary.marketMode || "等待连接";
    document.getElementById("watchlist-note").textContent = summary.topToken || "本地已保存";
  }

  function updatePulse() {
    const pulse = tracker.getPulseSummary();
    document.getElementById("pulse-sentiment").textContent = pulse.mood;
    document.getElementById("pulse-summary").textContent = pulse.summary;
    document.getElementById("pulse-top-token").textContent = pulse.topToken;
    document.getElementById("pulse-priority-alerts").textContent = pulse.priorityAlerts;
    document.getElementById("pulse-last-scan").textContent = pulse.lastScanAt ? formatTime(pulse.lastScanAt) : "等待连接";
    document.getElementById("pulse-narrative").textContent = pulse.narrative;
  }

  function updateConnectionStatus() {
    const connectionText = document.getElementById("conn-status-text");
    if (tracker.lastError) {
      connectionText.textContent = "连接异常";
      return;
    }

    const seconds = Math.round(tracker.getScanDelayMs() / 1000);
    connectionText.textContent = `DEX Screener · ${seconds}s 刷新`;
  }

  function hydrateSettingsForm() {
    document.getElementById("twitter-api").value = tracker.settings.xApiToken || "";
    document.getElementById("rpc-url").value = tracker.settings.rpcUrl || "";
    document.getElementById("dex-api").value = tracker.settings.dexApiKey || "";
    document.getElementById("keywords").value = tracker.settings.keywords.join(", ");
    document.getElementById("scan-freq").value = String(tracker.settings.scanFrequency);
    document.getElementById("alert-new-token").checked = tracker.settings.alertRules.newToken;
    document.getElementById("alert-kol").checked = tracker.settings.alertRules.kol;
    document.getElementById("alert-spike").checked = tracker.settings.alertRules.spike;
    document.getElementById("alert-whale").checked = tracker.settings.alertRules.whale;
    document.getElementById("spike-threshold").value = tracker.settings.spikeThreshold;
  }

  function saveSettingsFromForm() {
    const keywords = document.getElementById("keywords").value
      .split(",")
      .map((keyword) => keyword.trim())
      .filter(Boolean);

    tracker.updateSettings({
      xApiToken: document.getElementById("twitter-api").value.trim(),
      rpcUrl: document.getElementById("rpc-url").value.trim(),
      dexApiKey: document.getElementById("dex-api").value.trim(),
      scanFrequency: Number(document.getElementById("scan-freq").value),
      spikeThreshold: Number(document.getElementById("spike-threshold").value),
      keywords,
      alertRules: {
        newToken: document.getElementById("alert-new-token").checked,
        kol: document.getElementById("alert-kol").checked,
        spike: document.getElementById("alert-spike").checked,
        whale: document.getElementById("alert-whale").checked
      }
    });

    showToast("success", "设置已保存", "关键词和刷新频率已经生效，后端会按新的种子重新抓取实时数据。");
  }

  function openSearchedToken() {
    const query = dom.searchInput?.value.trim();
    if (!query) return;
    const token = tracker.searchToken(query);

    if (!token) {
      showToast("warning", "没有匹配到代币", `当前实时数据里还没找到 ${query}。你可以把它加到关键词里再刷新。`);
      return;
    }

    showTokenModal(token.symbol);
    dom.searchInput.value = "";
  }

  function updateSoundButton() {
    if (!dom.toggleSoundButton) return;
    dom.toggleSoundButton.style.color = tracker.settings.soundEnabled ? "var(--accent-cyan)" : "var(--text-muted)";
  }

  function shouldNotify(alert) {
    if (alert.type === "new-pair") return tracker.settings.alertRules.newToken;
    if (alert.type === "boosted") return tracker.settings.alertRules.kol;
    if (alert.type === "volume-spike" || alert.type === "momentum-up" || alert.type === "drawdown") return tracker.settings.alertRules.spike;
    return tracker.settings.alertRules.whale;
  }

  function alertToastType(type) {
    if (type === "new-pair") return "alert";
    if (type === "boosted") return "warning";
    if (type === "volume-spike" || type === "momentum-up") return "success";
    return "info";
  }

  function alertCssClass(type) {
    if (type === "new-pair") return "new-token";
    if (type === "boosted") return "kol-mention";
    if (type === "volume-spike" || type === "momentum-up") return "spike";
    return "whale";
  }

  function alertBadge(type) {
    if (type === "new-pair") return "🆕";
    if (type === "boosted") return "🔥";
    if (type === "volume-spike" || type === "momentum-up") return "⚡";
    return "💡";
  }

  function showToast(type, title, desc = "", duration = 4200) {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    const iconMap = { success: "✅", warning: "⚠️", alert: "🚨", info: "💡" };
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${iconMap[type] || "💡"}</span>
      <div>
        <div class="toast-title">${escapeHTML(title)}</div>
        <div class="toast-desc">${escapeHTML(desc)}</div>
      </div>
    `;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = "toast-out 0.25s ease forwards";
      setTimeout(() => toast.remove(), 250);
    }, duration);
  }

  function renderTokenVisual(token, className) {
    const fallback = escapeHTML((token?.symbolRaw || token?.symbol || "?").replace("$", "").slice(0, 1).toUpperCase());
    if (token?.icon) {
      return `<span class="${className}"><img src="${escapeAttribute(token.icon)}" alt="${escapeAttribute(token.symbol || token.name || "token")}"></span>`;
    }
    return `<span class="${className}">${fallback}</span>`;
  }

  function formatPrice(value) {
    if (!value) return "$0";
    if (value >= 1) return `$${value.toFixed(4)}`;
    if (value >= 0.01) return `$${value.toFixed(5)}`;
    if (value >= 0.0001) return `$${value.toFixed(6)}`;
    return `$${value.toExponential(2)}`;
  }

  function formatCurrency(value) {
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
    if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
    return `$${Math.round(value)}`;
  }

  function formatSigned(value) {
    const rounded = Number(value || 0).toFixed(2);
    return Number(rounded) > 0 ? `+${rounded}` : rounded;
  }

  function formatTime(date) {
    const now = new Date();
    const diff = Math.floor((now - new Date(date)) / 1000);
    if (diff < 10) return "刚刚";
    if (diff < 60) return `${diff} 秒前`;
    if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
    return `${Math.floor(diff / 86400)} 天前`;
  }

  function escapeHTML(input) {
    const div = document.createElement("div");
    div.textContent = input ?? "";
    return div.innerHTML;
  }

  function escapeAttribute(input) {
    return escapeHTML(input).replace(/"/g, "&quot;");
  }
})();
