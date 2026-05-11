const state = {
  paused: false,
  timer: null,
  lastData: null,
  alerts: loadAlerts(),
  audioContext: null,
  newsSlides: {},
  lang: localStorage.getItem("quant-lang") || "zh",
  theme: localStorage.getItem("quant-theme") || "light",
};

const els = {
  clock: document.querySelector("#clock"),
  freshness: document.querySelector("#freshness"),
  symbols: document.querySelector("#symbols"),
  limit: document.querySelector("#limit"),
  interval: document.querySelector("#interval"),
  scanNow: document.querySelector("#scanNow"),
  pause: document.querySelector("#pause"),
  notifyPermission: document.querySelector("#notifyPermission"),
  alertSymbol: document.querySelector("#alertSymbol"),
  alertSide: document.querySelector("#alertSide"),
  alertCondition: document.querySelector("#alertCondition"),
  alertPrice: document.querySelector("#alertPrice"),
  addAlert: document.querySelector("#addAlert"),
  alerts: document.querySelector("#alerts"),
  marketContext: document.querySelector("#marketContext"),
  providers: document.querySelector("#providers"),
  rankings: document.querySelector("#rankings"),
  universeSize: document.querySelector("#universeSize"),
  topPick: document.querySelector("#topPick"),
  topScore: document.querySelector("#topScore"),
  langOptions: document.querySelectorAll("[data-lang]"),
  themeOptions: document.querySelectorAll("[data-theme-choice]"),
};

const I18N = {
  zh: {
    title: "美股实时量化筛选",
    waiting: "等待数据",
    connecting: "正在连接实时行情...",
    connectingDetails: "首次打开免费服务器可能需要几十秒。",
    lightTheme: "浅色",
    darkTheme: "深色",
    watchlist: "股票池",
    rankLimit: "榜单数量",
    refreshSeconds: "刷新秒数",
    refreshNow: "立即刷新",
    pauseRefresh: "暂停刷新",
    resumeRefresh: "继续刷新",
    priceAlerts: "价格警报",
    allowNotifications: "允许浏览器通知",
    symbolPlaceholder: "股票代码",
    pricePlaceholder: "价格",
    buy: "买入",
    sell: "卖出",
    addAlert: "添加警报",
    glossary: "新手词典",
    termVwap: "当天平均成本线，价格在它上方通常更强。",
    termPullbackName: "回踩",
    termPullback: "先涨后回落，等它跌回关键位置附近再观察。",
    termBaseName: "横盘企稳",
    termBase: "价格在小范围里走，不再明显往下掉。",
    termNoChaseName: "不追高",
    termNoChase: "刚冲太快时先别急，等回落或确认。",
    termRiskName: "失效线",
    termRisk: "跌破这里，原来的买入理由先取消。",
    termScaleName: "分批止盈",
    termScale: "涨到目标区先卖一部分，别一次赌到底。",
    noticeTitle: "说明",
    noticeBody: "评分是强弱排序，不是第二天 100% 上涨概率。买卖区间是观察建议，不是收益保证或下单指令。",
    topPick: "最佳观察",
    signalStrength: "信号强度",
    rank: "排名",
    symbol: "股票",
    price: "价格",
    today: "今日",
    momentumScore: "动量分",
    entryWindow: "买入时段",
    buyZone: "买入位置",
    sellZone: "卖出区间",
    macroReason: "大盘/热点理由",
    latestNews: "相关新闻",
    signal: "信号",
    trend: "走势",
    reasons: "理由",
    loadingRankings: "正在加载实时榜单...",
    connectingRankings: "正在连接数据源并加载实时榜单...",
    loading: "刷新中...",
    refreshFailed: "刷新失败",
    connectionFailed: "连接失败",
    noQuotes: "没有拿到行情。请检查网络或 API Key。",
    noMacro: "暂无宏观新闻",
    noNews: "暂无相关新闻",
    score: "分数",
    previousNews: "上一条新闻",
    nextNews: "下一条新闻",
    resetAlert: "重新启用",
    deleteAlert: "删除",
    noAlerts: "没有警报",
    triggered: "已触发",
    armed: "监控中",
    notificationUnsupported: "当前浏览器不支持系统通知",
    notificationOn: "价格警报通知已开启",
    notificationOff: "通知未开启，仍会页面内提示",
    beginnerTip: "新手看法",
    originalTerm: "原术语",
    unclassified: "未分类",
  },
  en: {
    title: "US Stock Live Quant Scanner",
    waiting: "Waiting for data",
    connecting: "Connecting to live market data...",
    connectingDetails: "First load on the free server can take a few dozen seconds.",
    lightTheme: "Light",
    darkTheme: "Dark",
    watchlist: "Watchlist",
    rankLimit: "Rank limit",
    refreshSeconds: "Refresh seconds",
    refreshNow: "Refresh now",
    pauseRefresh: "Pause refresh",
    resumeRefresh: "Resume refresh",
    priceAlerts: "Price alerts",
    allowNotifications: "Allow browser notifications",
    symbolPlaceholder: "Symbol",
    pricePlaceholder: "Price",
    buy: "Buy",
    sell: "Sell",
    addAlert: "Add alert",
    glossary: "Beginner glossary",
    termVwap: "Intraday average cost line. Price above it often means stronger demand.",
    termPullbackName: "Pullback",
    termPullback: "A stock rises, then falls back near a key level before you consider it.",
    termBaseName: "Base",
    termBase: "Price moves sideways in a tight range and stops falling aggressively.",
    termNoChaseName: "No chase",
    termNoChase: "Do not buy into a fast spike; wait for a pullback or confirmation.",
    termRiskName: "Invalidation line",
    termRisk: "If price breaks below this level, the bullish idea is no longer valid.",
    termScaleName: "Scale out",
    termScale: "Sell part of the position near the target zone instead of betting all at once.",
    noticeTitle: "Note",
    noticeBody: "Scores rank relative strength. They are not a 100% next-day guarantee. Buy/sell zones are observation guides, not trading instructions.",
    topPick: "Top pick",
    signalStrength: "Signal strength",
    rank: "Rank",
    symbol: "Symbol",
    price: "Price",
    today: "Today",
    momentumScore: "Momentum score",
    entryWindow: "Entry window",
    buyZone: "Buy zone",
    sellZone: "Sell zone",
    macroReason: "Macro reason",
    latestNews: "Latest news",
    signal: "Signal",
    trend: "Trend",
    reasons: "Reasons",
    loadingRankings: "Loading live rankings...",
    connectingRankings: "Connecting to data sources and loading live rankings...",
    loading: "Refreshing...",
    refreshFailed: "Refresh failed",
    connectionFailed: "Connection failed",
    noQuotes: "No quotes received. Check network or API keys.",
    noMacro: "No macro headlines loaded",
    noNews: "No recent headline",
    score: "score",
    previousNews: "Previous headline",
    nextNews: "Next headline",
    resetAlert: "Reset",
    deleteAlert: "Delete",
    noAlerts: "No alerts",
    triggered: "Triggered",
    armed: "Armed",
    notificationUnsupported: "This browser does not support system notifications",
    notificationOn: "Price alert notifications are enabled",
    notificationOff: "Notifications are off; in-page alerts will still work",
    beginnerTip: "Beginner read",
    originalTerm: "Original term",
    unclassified: "Unclassified",
  },
};

function t(key) {
  return I18N[state.lang]?.[key] || I18N.zh[key] || key;
}

function setLanguage(lang) {
  if (!I18N[lang] || state.lang === lang) {
    return;
  }
  state.lang = lang;
  localStorage.setItem("quant-lang", lang);
  applyLanguage();
  if (state.lastData) {
    render(state.lastData);
  } else {
    renderAlerts();
  }
}

function setTheme(theme) {
  if (!["light", "dark"].includes(theme) || state.theme === theme) {
    return;
  }
  state.theme = theme;
  localStorage.setItem("quant-theme", theme);
  applyTheme();
}

function applyLanguage() {
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((node) => {
    node.title = t(node.dataset.i18nTitle);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  els.langOptions.forEach((button) => {
    button.classList.toggle("active", button.dataset.lang === state.lang);
  });
  els.pause.title = state.paused ? t("resumeRefresh") : t("pauseRefresh");
}

function applyTheme() {
  document.documentElement.dataset.theme = state.theme;
  els.themeOptions.forEach((button) => {
    button.classList.toggle("active", button.dataset.themeChoice === state.theme);
  });
}

async function init() {
  applyLanguage();
  applyTheme();
  const config = await fetchJson("/api/config");
  els.symbols.value = config.watchlist.join(", ");
  bindEvents();
  tickClock();
  setInterval(tickClock, 1000);
  await scan();
  schedule();
}

function bindEvents() {
  els.scanNow.addEventListener("click", () => scan());
  els.pause.addEventListener("click", () => {
    state.paused = !state.paused;
    els.pause.textContent = state.paused ? "▶" : "⏸";
    els.pause.title = state.paused ? t("resumeRefresh") : t("pauseRefresh");
    schedule();
  });
  els.interval.addEventListener("change", schedule);
  els.limit.addEventListener("change", () => scan());
  els.symbols.addEventListener("change", () => scan());
  els.notifyPermission.addEventListener("click", requestNotificationPermission);
  els.addAlert.addEventListener("click", addAlert);
  els.rankings.addEventListener("click", handleNewsNav);
  els.langOptions.forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.lang));
  });
  els.themeOptions.forEach((button) => {
    button.addEventListener("click", () => setTheme(button.dataset.themeChoice));
  });
}

function schedule() {
  if (state.timer) {
    clearTimeout(state.timer);
  }
  if (state.paused) {
    return;
  }
  const seconds = Math.max(1, Number(els.interval.value) || 1);
  state.timer = setTimeout(async () => {
    await scan();
    schedule();
  }, seconds * 1000);
}

async function scan() {
  try {
    setConnectingState();
    const params = new URLSearchParams({
      symbols: els.symbols.value,
      limit: els.limit.value || "30",
    });
    const data = await fetchJson(`/api/scan?${params.toString()}`);
    state.lastData = data;
    render(data);
  } catch (error) {
    els.freshness.textContent = t("refreshFailed");
    els.providers.innerHTML = `<div class="provider"><span class="dot fail"></span><div>${escapeHtml(t("connectionFailed"))}<br><small>${escapeHtml(error.message)}</small></div></div>`;
  }
}

function setConnectingState() {
  els.freshness.textContent = state.lastData ? t("loading") : t("connecting");
  if (state.lastData) {
    return;
  }
  els.providers.innerHTML = `
    <div class="provider connecting-provider">
      <span class="dot loading-dot"></span>
      <div>
        ${escapeHtml(t("connecting"))}
        <br />
        <small>${escapeHtml(t("connectingDetails"))}</small>
      </div>
    </div>
  `;
  els.rankings.innerHTML = `<tr><td colspan="13" class="empty">${escapeHtml(t("connectingRankings"))}</td></tr>`;
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function render(data) {
  const generated = new Date(data.generated_at);
  els.freshness.textContent = `UTC ${generated.toLocaleTimeString("en-US", { hour12: false })}`;
  els.universeSize.textContent = data.universe_size;

  const top = data.ranked[0];
  els.topPick.textContent = top ? top.symbol : "--";
  els.topScore.textContent = top ? `${Math.round(top.continuation_probability * 100)}/100` : "--";

  renderProviders(data.providers);
  renderMarketContext(data.market_context || []);
  renderRankings(data.ranked);
  checkAlerts(data.ranked);
  renderAlerts();
}

function renderProviders(providers) {
  els.providers.innerHTML = providers
    .map((provider) => {
      const statusClass = !provider.enabled ? "off" : provider.ok ? "ok" : "fail";
      const latency = provider.latency_ms === null ? "" : ` · ${provider.latency_ms}ms`;
      return `
        <div class="provider">
          <span class="dot ${statusClass}"></span>
          <div>
            ${escapeHtml(provider.provider)}
            <br />
            <small>${escapeHtml(provider.message)}${latency}</small>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderMarketContext(items) {
  if (!items.length) {
    els.marketContext.innerHTML = `<span class="muted">${escapeHtml(t("noMacro"))}</span>`;
    return;
  }
  els.marketContext.innerHTML = items
    .slice(0, 4)
    .map((item) => {
      const title = escapeHtml(item.title || "Market headline");
      const theme = escapeHtml(item.theme || "Market");
      const url = escapeHtml(item.url || "");
      const link = url ? `<a href="${url}" target="_blank" rel="noreferrer">${title}</a>` : `<strong>${title}</strong>`;
      return `
        <div class="context-item">
          <span>${theme}</span>
          ${link}
        </div>
      `;
    })
    .join("");
}

function renderRankings(rows) {
  if (!rows.length) {
    els.rankings.innerHTML = `<tr><td colspan="13" class="empty">${escapeHtml(t("noQuotes"))}</td></tr>`;
    return;
  }

  els.rankings.innerHTML = rows
    .map((row) => {
      const changeClass = row.change_pct >= 0 ? "positive" : "negative";
      const signalClass = row.signal === "Strong watch" ? "strong" : row.signal === "Weak" ? "weak" : "";
      const entry = explainEntryWindow(row.entry_window);
      const buyZone = explainBuyZone(row.entry_window);
      const sellZone = explainSellZone(row.entry_window);
      return `
        <tr>
          <td>${row.rank}</td>
          <td>
            <div class="symbol">${escapeHtml(row.symbol)}</div>
            <small>${escapeHtml(row.providers.join(" / "))}</small>
          </td>
          <td>${formatMoney(row.price)}</td>
          <td class="${changeClass}">${formatPct(row.change_pct)}</td>
          <td>
            <strong>${Math.round(row.continuation_probability * 100)}/100</strong>
            <br />
            <small>${escapeHtml(t("score"))} ${row.score.toFixed(1)}</small>
          </td>
          <td class="entry">
            <strong>${escapeHtml(entry.action)}</strong>
            <span>${escapeHtml(entry.time)}</span>
            <small>${escapeHtml(entry.reason)}</small>
            <em>${escapeHtml(entry.term)}</em>
          </td>
          <td class="buy-zone">
            <strong>${escapeHtml(row.entry_window.buy_zone.range)}</strong>
            <span>${escapeHtml(buyZone.action)}</span>
            <small>${escapeHtml(buyZone.trigger)}</small>
            <em>${escapeHtml(buyZone.tip)}</em>
          </td>
          <td class="sell-zone">
            <strong>${escapeHtml(row.entry_window.sell_zone.target)}</strong>
            <span>${escapeHtml(sellZone.risk)}</span>
            <small>${escapeHtml(sellZone.trigger)}</small>
            <em>${escapeHtml(sellZone.tip)}</em>
          </td>
          <td class="macro-cell">${escapeHtml(macroText(row.macro_reason || "No clear macro theme"))}</td>
          <td class="news-cell">${newsCell(row.symbol, row.news_items || (row.news ? [row.news] : []))}</td>
          <td><span class="pill ${signalClass}">${escapeHtml(signalText(row.signal))}</span></td>
          <td>${sparkline(row.sparkline, row.change_pct >= 0)}</td>
          <td class="reasons">${escapeHtml(row.reasons.map(reasonText).join(" · "))}</td>
        </tr>
      `;
    })
    .join("");
}

function handleNewsNav(event) {
  const button = event.target.closest("[data-news-dir]");
  if (!button) {
    return;
  }
  const symbol = button.dataset.symbol;
  const direction = Number(button.dataset.newsDir);
  const row = state.lastData?.ranked?.find((item) => item.symbol === symbol);
  const items = row?.news_items || (row?.news ? [row.news] : []);
  if (!symbol || items.length <= 1) {
    return;
  }
  const current = state.newsSlides[symbol] || 0;
  state.newsSlides[symbol] = (current + direction + items.length) % items.length;
  renderRankings(state.lastData.ranked);
}

function explainEntryWindow(entry) {
  const label = entry.label || "";
  const vwapNote = plainText(entry.rationale || "");
  const map = entryWindowCopy();
  const fallback = {
    action: state.lang === "zh" ? "先观察，不急着下单" : "Observe first, do not rush",
    time: plainText(entry.window || (state.lang === "zh" ? "等待更清晰的位置" : "Wait for a cleaner setup")),
    reason: vwapNote || (state.lang === "zh" ? "系统还没有看到足够清晰的入场形态。" : "The system does not see a clean enough entry pattern yet."),
    term: label ? `${t("originalTerm")}: ${label}` : `${t("originalTerm")}: ${t("unclassified")}`,
  };
  return map[label] || fallback;
}

function explainBuyZone(entry) {
  const label = entry.label || "";
  const trigger = entry.buy_zone?.trigger || "";
  const map = buyZoneCopy();
  return {
    action: map[label]?.action || plainText(entry.buy_zone?.label || (state.lang === "zh" ? "观察区间" : "Observe zone")),
    trigger: plainText(trigger),
    tip: map[label]?.tip || `${t("beginnerTip")}: ${state.lang === "zh" ? "先等确认，不用急着抢第一秒。" : "Wait for confirmation; you do not need to catch the first second."}`,
  };
}

function explainSellZone(entry) {
  const trigger = entry.sell_zone?.trigger || "";
  const risk = entry.sell_zone?.risk || "";
  return {
    risk: plainText(risk).replace("失效线", "跌破这里先退出"),
    trigger: plainText(trigger),
    tip:
      state.lang === "zh"
        ? "新手看法：到目标区可以分批卖；跌破失效线先保护本金。"
        : "Beginner read: scale out near the target zone; protect capital if price breaks the invalidation line.",
  };
}

function signalText(signal) {
  const map =
    state.lang === "zh"
      ? {
          "Strong watch": "重点观察",
          Watch: "观察",
          Weak: "偏弱",
          Neutral: "中性",
        }
      : {
          "Strong watch": "Strong watch",
          Watch: "Watch",
          Weak: "Weak",
          Neutral: "Neutral",
        };
  return map[signal] || signal;
}

function entryWindowCopy() {
  if (state.lang === "en") {
    return {
      "No chase": {
        action: "Do not buy yet; wait for strength",
        time: "Recheck after price climbs back above VWAP",
        reason: "Today is weak, so chasing can easily buy the top of a bounce.",
        term: "Original term: No chase",
      },
      "Wait for pullback": {
        action: "Wait for the morning pullback to stabilize",
        time: "Watch 10:00-11:30 ET",
        reason: "If it opens high and fades, let the first wave of selling settle before judging support.",
        term: "Original term: Pullback",
      },
      "VWAP pullback": {
        action: "Wait near the VWAP average-cost line",
        time: "Do not chase the high; wait for price near VWAP",
        reason: "After a fast move, the cleaner entry usually comes from a controlled pullback.",
        term: "Original term: VWAP pullback",
      },
      "Breakout confirm": {
        action: "Wait for breakout confirmation",
        time: "10:15-11:00 ET or 14:30-15:30 ET",
        reason: "A breakout is cleaner when price retests the prior high and holds above it.",
        term: "Original term: Breakout confirm",
      },
      "Midday base": {
        action: "Wait for a stable midday base",
        time: "11:00-13:30 ET",
        reason: "Let price move sideways in a tight range and stop falling before looking for an upside push.",
        term: "Original term: Midday base",
      },
      "Late confirm": {
        action: "Wait for clearer late-day direction",
        time: "14:30-15:45 ET",
        reason: "The signal is not clean enough yet; late-day action often shows whether buyers want to hold overnight.",
        term: "Original term: Late confirm",
      },
    };
  }
  return {
    "No chase": {
      action: "先别买，等重新转强",
      time: "价格重新站回平均成本线后再看",
      reason: "今天偏弱，直接追进去容易买在反弹最高处。",
      term: "原术语：No chase / 不追高",
    },
    "Wait for pullback": {
      action: "等早盘回落后站稳",
      time: "美东 10:00-11:30 观察",
      reason: "如果高开后往下走，先等第一波卖压释放，再看是否止跌。",
      term: "原术语：pullback / 回踩",
    },
    "VWAP pullback": {
      action: "等回到平均成本线附近",
      time: "不要追最高点，等价格靠近 VWAP",
      reason: "涨得太快时，比较舒服的位置通常来自回落确认。",
      term: "原术语：VWAP pullback",
    },
    "Breakout confirm": {
      action: "等突破后确认没跌回去",
      time: "美东 10:15-11:00 或 14:30-15:30",
      reason: "价格冲过前面高点后，回落还守得住，才说明买盘更稳。",
      term: "原术语：Breakout confirm",
    },
    "Midday base": {
      action: "等午盘稳住再决定",
      time: "美东 11:00-13:30",
      reason: "价格先在小范围内横着走，不再明显下跌，再看是否向上离开。",
      term: "原术语：Midday base / 横盘企稳",
    },
    "Late confirm": {
      action: "等尾盘方向更清楚",
      time: "美东 14:30-15:45",
      reason: "当前信号不够干净，尾盘更能看出资金是否愿意持有过夜。",
      term: "原术语：Late confirm",
    },
  };
}

function buyZoneCopy() {
  if (state.lang === "en") {
    return {
      "No chase": {
        action: "Only consider it after strength returns",
        tip: "Beginner read: do not guess the bottom before price stabilizes.",
      },
      "VWAP pullback": {
        action: "24-hour observation buy zone",
        tip: "Beginner read: once price enters the zone, first check whether it stops falling.",
      },
      "Wait for pullback": {
        action: "Consider it only after the pullback holds",
        tip: "Beginner read: touching the zone is not enough; wait for price to turn back up.",
      },
      "Breakout confirm": {
        action: "Consider it after the breakout retest holds",
        tip: "Beginner read: avoid buying the exact moment it spikes.",
      },
      "Midday base": {
        action: "Consider after midday stabilization",
        tip: "Beginner read: first see whether price stops making new downside progress.",
      },
      "Late confirm": {
        action: "Consider if it holds into the close",
        tip: "Beginner read: when the signal is average, move less and wait for cleaner confirmation.",
      },
    };
  }
  return {
    "No chase": {
      action: "只在重新转强时考虑",
      tip: "新手看法：没站稳前不要提前猜底。",
    },
    "VWAP pullback": {
      action: "24小时观察买入区",
      tip: "新手看法：价格进入区间后，先看它能不能停止下跌。",
    },
    "Wait for pullback": {
      action: "回落守住后再考虑",
      tip: "新手看法：不是跌到区间就买，要等重新往上。",
    },
    "Breakout confirm": {
      action: "突破后回落不破再考虑",
      tip: "新手看法：避免在刚冲高的瞬间追进去。",
    },
    "Midday base": {
      action: "午盘走稳后再考虑",
      tip: "新手看法：先看价格是否不再继续往下掉。",
    },
    "Late confirm": {
      action: "尾盘站稳附近再考虑",
      tip: "新手看法：信号普通时少动，等更确定。",
    },
  };
}

function plainText(value) {
  if (state.lang === "en") {
    return String(value || "")
      .replaceAll("等待重新站上 VWAP 后再评估", "Wait until price reclaims VWAP before reassessing")
      .replaceAll("美东", "ET")
      .replaceAll("回踩确认", "pullback confirmation")
      .replaceAll("回踩 VWAP 附近，不追高点", "Pull back near VWAP; do not chase the high")
      .replaceAll("确认突破", "breakout confirmation")
      .replaceAll("横盘企稳", "sideways base stabilization")
      .replaceAll("尾盘确认", "late-day confirmation")
      .replaceAll("当日走势偏弱，直接追入风险较高。", "Today is weak; chasing carries higher risk.")
      .replaceAll("高开后回落，优先等开盘情绪释放后观察是否守住 VWAP/前低。", "If it opens high and fades, let opening pressure settle and check whether VWAP/support holds.")
      .replaceAll("强势高开且价格偏离 VWAP，较好的位置通常来自回踩而不是尖峰追入。", "When price gaps strongly away from VWAP, a cleaner entry usually comes from a pullback rather than chasing the spike.")
      .replaceAll("盘中趋势仍在抬高，可等突破后回踩不破再观察。", "Intraday trend is still lifting; wait for a breakout and a retest that holds.")
      .replaceAll("走势偏强但不是极强，适合等午盘收敛后再看方向。", "The move is strong but not extreme; wait for midday consolidation before judging direction.")
      .replaceAll("信号不够清晰，等待尾盘资金方向更稳。", "The signal is not clean enough; wait for late-day money flow to clarify.")
      .replaceAll("当前距估算 VWAP", "Estimated distance from VWAP")
      .replaceAll("等待实时价格恢复", "Wait for live price to recover")
      .replaceAll("重新站上 VWAP 且 5-15 分钟不跌回", "Reclaim VWAP and hold it for 5-15 minutes")
      .replaceAll("回踩区间内缩量企稳，随后放量转强", "Stabilize inside the pullback zone, then strengthen on higher volume")
      .replaceAll("开盘回落后守住支撑，重新上穿短线均价", "Hold support after the opening pullback and reclaim the short-term average")
      .replaceAll("突破前高后回踩不破，避免直接追最高点", "Break prior high, then retest and hold; avoid chasing the top")
      .replaceAll("午盘窄幅整理后向上离开区间", "Leave a tight midday range to the upside")
      .replaceAll("尾盘放量站稳当前价附近", "Hold near current price on stronger late-day volume")
      .replaceAll("冲高靠近目标区可分批止盈；跌破买入区下沿/VWAP 减仓", "Scale out near the target zone; reduce if it breaks below the buy zone or VWAP")
      .replaceAll("午盘突破后若量能衰减，可在目标区分批卖出", "After a midday breakout, scale out near target if volume fades")
      .replaceAll("尾盘确认失败或跌回 VWAP，优先退出观察", "If late confirmation fails or price falls back below VWAP, step aside first")
      .replaceAll("只适合反弹观察；不能站稳 VWAP 就不持有", "Only a bounce watch; do not hold if it cannot stay above VWAP")
      .replaceAll("达到目标区或跌破失效线时重新评估", "Reassess when target is reached or invalidation breaks")
      .replaceAll("失效线", "Invalidation")
      .replaceAll("观察区", "Observe zone")
      .replaceAll("24小时", "24h");
  }
  return String(value || "")
    .replaceAll("VWAP", "平均成本线")
    .replaceAll("pullback", "回落确认")
    .replaceAll("Pullback", "回落确认")
    .replaceAll("observe zone", "观察区")
    .replaceAll("24h", "24小时")
    .replaceAll("重新站上", "重新涨回")
    .replaceAll("上穿", "涨回")
    .replaceAll("缩量企稳", "下跌变慢并稳住")
    .replaceAll("放量转强", "买的人明显变多")
    .replaceAll("前高", "前面的高点")
    .replaceAll("回踩不破", "回落后没有跌破")
    .replaceAll("窄幅整理", "小范围来回走")
    .replaceAll("量能衰减", "买入力量变弱")
    .replaceAll("减仓", "卖出一部分")
    .replaceAll("退出观察", "先退出/先不看多")
    .replaceAll("不持有", "先不持有");
}

function reasonText(value) {
  if (state.lang !== "en") {
    return value;
  }
  return String(value || "")
    .replace(/当日涨幅 ([+-]?\d+\.?\d*)%/, "Today's move $1%")
    .replace(/盘中强度 ([+-]?\d+\.?\d*)%/, "Intraday strength $1%")
    .replace(/开盘跳空 ([+-]?\d+\.?\d*)%/, "Opening gap $1%")
    .replace("价格靠近日内高位", "Price is near the intraday high")
    .replace(/(\d+) 个数据源确认/, "$1 providers confirmed")
    .replace("数据完整度较高", "Good data completeness");
}

function macroText(value) {
  if (state.lang !== "en") {
    return value;
  }
  return String(value || "")
    .replace("AI/chip headline tailwind; watch for sector-wide rotation.", "AI/chip headline tailwind; watch for sector-wide rotation.")
    .replace("Macro backdrop: General market.", "Macro backdrop: General market.")
    .replace("No clear macro theme", "No clear macro theme");
}

function addAlert() {
  const symbol = els.alertSymbol.value.trim().toUpperCase();
  const price = Number(els.alertPrice.value);
  if (!symbol || !Number.isFinite(price) || price <= 0) {
    return;
  }
  const alert = {
    id: `${symbol}-${Date.now()}`,
    symbol,
    side: els.alertSide.value,
    condition: els.alertCondition.value,
    price,
    triggered: false,
    createdAt: new Date().toISOString(),
  };
  state.alerts.unshift(alert);
  saveAlerts();
  renderAlerts();
  els.alertSymbol.value = "";
  els.alertPrice.value = "";
}

function checkAlerts(rows) {
  const prices = new Map(rows.map((row) => [row.symbol, row.price]));
  let changed = false;
  for (const alert of state.alerts) {
    if (alert.triggered) {
      continue;
    }
    const price = prices.get(alert.symbol);
    if (price === null || price === undefined) {
      continue;
    }
    const hit = alert.condition === ">=" ? price >= alert.price : price <= alert.price;
    if (hit) {
      alert.triggered = true;
      alert.triggeredAt = new Date().toISOString();
      changed = true;
      fireAlert(alert, price);
    }
  }
  if (changed) {
    saveAlerts();
  }
}

function fireAlert(alert, price) {
  const side = alert.side === "buy" ? "BUY" : "SELL";
  const message = `${alert.symbol} ${side} alert: ${formatMoney(price)} hit ${alert.condition} ${formatMoney(alert.price)}`;
  playAlertTone();
  if ("Notification" in window && Notification.permission === "granted") {
    new Notification("Quant price alert", { body: message });
  }
  els.freshness.textContent = message;
}

function playAlertTone() {
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) {
    return;
  }
  state.audioContext = state.audioContext || new AudioContext();
  const oscillator = state.audioContext.createOscillator();
  const gain = state.audioContext.createGain();
  oscillator.type = "sine";
  oscillator.frequency.value = 880;
  gain.gain.setValueAtTime(0.001, state.audioContext.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.18, state.audioContext.currentTime + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.001, state.audioContext.currentTime + 0.45);
  oscillator.connect(gain);
  gain.connect(state.audioContext.destination);
  oscillator.start();
  oscillator.stop(state.audioContext.currentTime + 0.5);
}

async function requestNotificationPermission() {
  if (!("Notification" in window)) {
    els.freshness.textContent = t("notificationUnsupported");
    return;
  }
  const permission = await Notification.requestPermission();
  els.freshness.textContent = permission === "granted" ? t("notificationOn") : t("notificationOff");
}

function renderAlerts() {
  if (!state.alerts.length) {
    els.alerts.innerHTML = `<div class="empty-alert">${escapeHtml(t("noAlerts"))}</div>`;
    return;
  }
  els.alerts.innerHTML = state.alerts
    .map((alert) => {
      const status = alert.triggered ? "triggered" : "armed";
      const side = alert.side === "buy" ? t("buy").toUpperCase() : t("sell").toUpperCase();
      return `
        <div class="alert-item ${status}">
          <div>
            <strong>${escapeHtml(alert.symbol)} ${side}</strong>
            <span>${escapeHtml(alert.condition)} ${formatMoney(alert.price)}</span>
            <small>${alert.triggered ? escapeHtml(t("triggered")) : escapeHtml(t("armed"))}</small>
          </div>
          <div class="alert-actions">
            <button type="button" title="${escapeHtml(t("resetAlert"))}" data-alert-action="reset" data-alert-id="${escapeHtml(alert.id)}">↻</button>
            <button type="button" title="${escapeHtml(t("deleteAlert"))}" data-alert-action="delete" data-alert-id="${escapeHtml(alert.id)}">×</button>
          </div>
        </div>
      `;
    })
    .join("");
  els.alerts.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.dataset.alertId;
      const action = button.dataset.alertAction;
      if (action === "delete") {
        state.alerts = state.alerts.filter((alert) => alert.id !== id);
      } else if (action === "reset") {
        const alert = state.alerts.find((item) => item.id === id);
        if (alert) {
          alert.triggered = false;
          delete alert.triggeredAt;
        }
      }
      saveAlerts();
      renderAlerts();
    });
  });
}

function loadAlerts() {
  try {
    const value = JSON.parse(localStorage.getItem("quant-alerts") || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

function saveAlerts() {
  localStorage.setItem("quant-alerts", JSON.stringify(state.alerts));
}

function newsCell(symbol, newsItems) {
  const items = Array.isArray(newsItems) ? newsItems.filter(Boolean) : [];
  if (!items.length) {
    return `<span class="muted">${escapeHtml(t("noNews"))}</span>`;
  }
  const selected = Math.min(state.newsSlides[symbol] || 0, items.length - 1);
  const news = items[selected];
  const title = escapeHtml(news.title);
  const source = escapeHtml(news.source || "News");
  const url = escapeHtml(news.url || "");
  const controls =
    items.length > 1
      ? `
        <div class="news-controls" aria-label="${escapeHtml(symbol)} news controls">
          <button type="button" title="${escapeHtml(t("previousNews"))}" data-news-dir="-1" data-symbol="${escapeHtml(symbol)}">‹</button>
          <span>${selected + 1} / ${items.length}</span>
          <button type="button" title="${escapeHtml(t("nextNews"))}" data-news-dir="1" data-symbol="${escapeHtml(symbol)}">›</button>
        </div>
      `
      : "";
  const link = url ? `<a href="${url}" target="_blank" rel="noreferrer">${title}</a>` : `<strong>${title}</strong>`;
  return `
    <div class="news-carousel">
      ${controls}
      ${link}
      <small>${source}</small>
    </div>
  `;
}

function sparkline(points, positive) {
  if (!points.length) {
    return "--";
  }
  const width = 108;
  const height = 34;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const spread = max - min || 1;
  const step = width / Math.max(points.length - 1, 1);
  const d = points
    .map((point, index) => {
      const x = index * step;
      const y = height - ((point - min) / spread) * (height - 4) - 2;
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const color = positive ? "#087f5b" : "#c92a2a";
  return `
    <svg class="spark" viewBox="0 0 ${width} ${height}" aria-hidden="true">
      <path d="${d}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" />
    </svg>
  `;
}

function tickClock() {
  els.clock.textContent = new Date().toLocaleTimeString("en-US", { hour12: false });
}

function formatMoney(value) {
  if (value === null || value === undefined) {
    return "--";
  }
  return `$${Number(value).toFixed(2)}`;
}

function formatPct(value) {
  const number = Number(value) || 0;
  return `${number >= 0 ? "+" : ""}${number.toFixed(2)}%`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

init();
