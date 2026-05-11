const state = {
  paused: false,
  timer: null,
  lastData: null,
  alerts: loadAlerts(),
  audioContext: null,
  newsSlides: {},
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
};

async function init() {
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
    els.pause.title = state.paused ? "继续刷新" : "暂停刷新";
    schedule();
  });
  els.interval.addEventListener("change", schedule);
  els.limit.addEventListener("change", () => scan());
  els.symbols.addEventListener("change", () => scan());
  els.notifyPermission.addEventListener("click", requestNotificationPermission);
  els.addAlert.addEventListener("click", addAlert);
  els.rankings.addEventListener("click", handleNewsNav);
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
    els.freshness.textContent = "刷新中...";
    const params = new URLSearchParams({
      symbols: els.symbols.value,
      limit: els.limit.value || "30",
    });
    const data = await fetchJson(`/api/scan?${params.toString()}`);
    state.lastData = data;
    render(data);
  } catch (error) {
    els.freshness.textContent = "刷新失败";
    els.providers.innerHTML = `<div class="provider"><span class="dot fail"></span><div>连接失败<br><small>${escapeHtml(error.message)}</small></div></div>`;
  }
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
    els.marketContext.innerHTML = `<span class="muted">No macro headlines loaded</span>`;
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
    els.rankings.innerHTML = `<tr><td colspan="8" class="empty">没有拿到行情。请检查网络或 API Key。</td></tr>`;
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
            <small>score ${row.score.toFixed(1)}</small>
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
          <td class="macro-cell">${escapeHtml(row.macro_reason || "No clear macro theme")}</td>
          <td class="news-cell">${newsCell(row.symbol, row.news_items || (row.news ? [row.news] : []))}</td>
          <td><span class="pill ${signalClass}">${escapeHtml(signalText(row.signal))}</span></td>
          <td>${sparkline(row.sparkline, row.change_pct >= 0)}</td>
          <td class="reasons">${escapeHtml(row.reasons.join(" · "))}</td>
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
  const map = {
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
  const fallback = {
    action: "先观察，不急着下单",
    time: plainText(entry.window || "等待更清晰的位置"),
    reason: vwapNote || "系统还没有看到足够清晰的入场形态。",
    term: label ? `原术语：${label}` : "原术语：未分类",
  };
  return map[label] || fallback;
}

function explainBuyZone(entry) {
  const label = entry.label || "";
  const trigger = entry.buy_zone?.trigger || "";
  const map = {
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
  return {
    action: map[label]?.action || plainText(entry.buy_zone?.label || "观察区间"),
    trigger: plainText(trigger),
    tip: map[label]?.tip || "新手看法：先等确认，不用急着抢第一秒。",
  };
}

function explainSellZone(entry) {
  const trigger = entry.sell_zone?.trigger || "";
  const risk = entry.sell_zone?.risk || "";
  return {
    risk: plainText(risk).replace("失效线", "跌破这里先退出"),
    trigger: plainText(trigger),
    tip: "新手看法：到目标区可以分批卖；跌破失效线先保护本金。",
  };
}

function signalText(signal) {
  const map = {
    "Strong watch": "重点观察",
    Watch: "观察",
    Weak: "偏弱",
    Neutral: "中性",
  };
  return map[signal] || signal;
}

function plainText(value) {
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
    els.freshness.textContent = "当前浏览器不支持系统通知";
    return;
  }
  const permission = await Notification.requestPermission();
  els.freshness.textContent = permission === "granted" ? "价格警报通知已开启" : "通知未开启，仍会页面内提示";
}

function renderAlerts() {
  if (!state.alerts.length) {
    els.alerts.innerHTML = `<div class="empty-alert">No alerts</div>`;
    return;
  }
  els.alerts.innerHTML = state.alerts
    .map((alert) => {
      const status = alert.triggered ? "triggered" : "armed";
      const side = alert.side === "buy" ? "BUY" : "SELL";
      return `
        <div class="alert-item ${status}">
          <div>
            <strong>${escapeHtml(alert.symbol)} ${side}</strong>
            <span>${escapeHtml(alert.condition)} ${formatMoney(alert.price)}</span>
            <small>${alert.triggered ? "Triggered" : "Armed"}</small>
          </div>
          <div class="alert-actions">
            <button type="button" title="重新启用" data-alert-action="reset" data-alert-id="${escapeHtml(alert.id)}">↻</button>
            <button type="button" title="删除" data-alert-action="delete" data-alert-id="${escapeHtml(alert.id)}">×</button>
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
    return `<span class="muted">No recent headline</span>`;
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
          <button type="button" title="上一条新闻" data-news-dir="-1" data-symbol="${escapeHtml(symbol)}">‹</button>
          <span>${selected + 1} / ${items.length}</span>
          <button type="button" title="下一条新闻" data-news-dir="1" data-symbol="${escapeHtml(symbol)}">›</button>
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
