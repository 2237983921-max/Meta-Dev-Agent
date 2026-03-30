class MemeTracker {
  constructor() {
    this.storageKeys = {
      settings: "memeRadar.live.settings",
      watchlist: "memeRadar.live.watchlist",
      seenAlerts: "memeRadar.live.seenAlerts"
    };

    this.defaultSettings = {
      soundEnabled: true,
      scanFrequency: 30,
      keywords: ["PEPE", "WIF", "BONK", "POPCAT", "FLOKI", "BRETT", "MEW", "MOG", "NEIRO", "FWOG"],
      xApiToken: "",
      rpcUrl: "",
      dexApiKey: "",
      alertRules: {
        newToken: true,
        kol: true,
        spike: true,
        whale: true
      },
      spikeThreshold: 50
    };

    this.settings = this.loadSettings();
    this.watchlist = new Set(this.loadArray(this.storageKeys.watchlist));
    this.seenAlerts = new Set(this.loadArray(this.storageKeys.seenAlerts));
    this.dashboard = {
      mode: "live",
      generatedAt: "",
      summary: {},
      tokens: [],
      feed: [],
      alerts: [],
      socials: []
    };
    this.feedPaused = false;
    this.isRunning = false;
    this.pollInterval = null;
    this.lastError = "";
    this.lastRefreshAt = null;

    this.onDataUpdate = null;
    this.onNewAlert = null;
    this.onStatsUpdate = null;
    this.onWatchlistChange = null;
    this.onSettingsChange = null;
    this.onError = null;
  }

  loadArray(key) {
    try {
      const parsed = JSON.parse(localStorage.getItem(key) || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  loadSettings() {
    try {
      const stored = JSON.parse(localStorage.getItem(this.storageKeys.settings) || "{}");
      return {
        ...this.defaultSettings,
        ...stored,
        alertRules: {
          ...this.defaultSettings.alertRules,
          ...(stored.alertRules || {})
        },
        keywords: Array.isArray(stored.keywords) && stored.keywords.length
          ? stored.keywords
          : [...this.defaultSettings.keywords]
      };
    } catch (error) {
      return { ...this.defaultSettings, keywords: [...this.defaultSettings.keywords] };
    }
  }

  persistSettings() {
    localStorage.setItem(this.storageKeys.settings, JSON.stringify(this.settings));
  }

  persistWatchlist() {
    localStorage.setItem(this.storageKeys.watchlist, JSON.stringify([...this.watchlist]));
  }

  persistSeenAlerts() {
    localStorage.setItem(this.storageKeys.seenAlerts, JSON.stringify([...this.seenAlerts]));
  }

  start() {
    if (this.isRunning) {
      return;
    }

    this.isRunning = true;
    this.refresh(true);
    this.restartPolling();
  }

  stop() {
    this.isRunning = false;
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  restartPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }

    this.pollInterval = setInterval(() => {
      if (!this.feedPaused) {
        this.refresh();
      }
    }, this.getScanDelayMs());
  }

  getScanDelayMs() {
    return Math.max(10_000, Number(this.settings.scanFrequency || 30) * 1000);
  }

  async refresh(isInitial = false) {
    try {
      const query = encodeURIComponent(this.settings.keywords.join(","));
      const response = await fetch(`/api/dashboard?keywords=${query}`, {
        headers: { Accept: "application/json" }
      });

      if (!response.ok) {
        throw new Error(`实时接口返回 ${response.status}`);
      }

      const nextDashboard = await response.json();
      const previousAlerts = new Set((this.dashboard.alerts || []).map((alert) => alert.id));

      this.dashboard = nextDashboard;
      this.lastError = "";
      this.lastRefreshAt = new Date();

      const newAlerts = (nextDashboard.alerts || []).filter((alert) => {
        return !previousAlerts.has(alert.id) && !this.seenAlerts.has(alert.id);
      });

      this.onDataUpdate?.(nextDashboard, { isInitial, newAlerts });
      newAlerts.forEach((alert) => this.onNewAlert?.(alert));
      this.onStatsUpdate?.();
    } catch (error) {
      this.lastError = error instanceof Error ? error.message : "无法连接实时数据源";
      this.onError?.(this.lastError);
    }
  }

  getTrendingTokens() {
    return [...(this.dashboard.tokens || [])];
  }

  getAlerts() {
    return (this.dashboard.alerts || []).map((alert) => ({
      ...alert,
      read: this.seenAlerts.has(alert.id)
    }));
  }

  getFeedItems(filter = {}) {
    const mode = filter.mode || "all";
    const query = (filter.query || "").trim().toLowerCase();
    const items = this.dashboard.feed || [];

    return items.filter((item) => {
      const token = this.searchToken(item.symbol || "");
      const haystack = `${item.title} ${item.description} ${item.symbol} ${item.name} ${item.chain}`.toLowerCase();

      if (query && !haystack.includes(query)) {
        return false;
      }

      if (mode === "all") return true;
      if (mode === "new") return item.type === "new-pair";
      if (mode === "high") return item.importance >= 80;
      if (mode === "pump") return item.type === "boosted";
      if (mode === "watchlist") return token ? this.isWatchlisted(token.symbol) : false;
      if (mode === "kol") return item.type === "boosted" || item.type === "volume-spike";
      return true;
    });
  }

  getCommunityProjects() {
    return [...(this.dashboard.socials || [])];
  }

  getStats() {
    const alerts = this.getAlerts();
    return {
      scanned: (this.dashboard.feed || []).length,
      detected: (this.dashboard.tokens || []).length,
      alerts: alerts.filter((alert) => !alert.read).length,
      watchlist: this.watchlist.size,
      averageSentiment: this.dashboard.summary?.avgSentiment || 0
    };
  }

  getPulseSummary() {
    const summary = this.dashboard.summary || {};
    return {
      mood: summary.marketMode || "等待连接",
      summary: `主导链 ${summary.dominantChain || "-"}，24h 总成交 ${this.formatCurrency(summary.totalVolume24h || 0)}。`,
      narrative: summary.topNarrative || "社区混沌流",
      topToken: summary.topToken || "-",
      priorityAlerts: (this.dashboard.alerts || []).filter((alert) => !this.seenAlerts.has(alert.id)).length,
      lastScanAt: this.lastRefreshAt
    };
  }

  searchToken(query) {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return null;
    }

    return this.getTrendingTokens().find((token) => {
      return token.symbol.toLowerCase() === normalized
        || token.symbolRaw.toLowerCase() === normalized.replace("$", "")
        || token.name.toLowerCase().includes(normalized)
        || token.tokenAddress.toLowerCase() === normalized;
    }) || null;
  }

  updateSettings(nextSettings) {
    this.settings = {
      ...this.settings,
      ...nextSettings,
      alertRules: {
        ...this.settings.alertRules,
        ...(nextSettings.alertRules || {})
      }
    };

    this.settings.scanFrequency = Number(this.settings.scanFrequency) || 30;
    this.settings.soundEnabled = Boolean(this.settings.soundEnabled);
    this.settings.keywords = Array.isArray(this.settings.keywords)
      ? this.settings.keywords.map((keyword) => keyword.trim()).filter(Boolean)
      : [...this.defaultSettings.keywords];

    this.persistSettings();
    if (this.isRunning) {
      this.restartPolling();
      this.refresh();
    }

    this.onSettingsChange?.(this.settings);
    this.onStatsUpdate?.();
  }

  toggleWatchlist(symbol) {
    if (this.watchlist.has(symbol)) {
      this.watchlist.delete(symbol);
    } else {
      this.watchlist.add(symbol);
    }

    this.persistWatchlist();
    this.onWatchlistChange?.([...this.watchlist]);
    this.onStatsUpdate?.();
    return this.watchlist.has(symbol);
  }

  isWatchlisted(symbol) {
    return this.watchlist.has(symbol);
  }

  markAllAlertsRead() {
    (this.dashboard.alerts || []).forEach((alert) => this.seenAlerts.add(alert.id));
    this.persistSeenAlerts();
    this.onStatsUpdate?.();
  }

  markAlertRead(alertId) {
    this.seenAlerts.add(alertId);
    this.persistSeenAlerts();
  }

  formatCurrency(value) {
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
    if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
    return `$${Math.round(value)}`;
  }
}
