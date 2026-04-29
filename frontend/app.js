const startStreamBtn = document.getElementById("startStreamBtn");
const stopStreamBtn = document.getElementById("stopStreamBtn");
const refreshBtn = document.getElementById("refreshBtn");
const historyFilter = document.getElementById("historyFilter");
const detectStatus = document.getElementById("detectStatus");
const summary = document.getElementById("summary");
const healthStatus = document.getElementById("healthStatus");
const historyList = document.getElementById("historyList");
const streamView = document.getElementById("streamView");
const liveState = document.getElementById("liveState");
const sourceDirDisplay = document.getElementById("sourceDirDisplay");
const blurFilterToggle = document.getElementById("blurFilterToggle");
const blurFilterLabel = document.getElementById("blurFilterLabel");

let statusTimer = null;
let historyTimer = null;

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    healthStatus.textContent = data.model_ready
      ? '算法模型已加载'
      : '模型未就绪，请先放置权重文件';
    if (data.source_dir) {
      sourceDirDisplay.textContent = data.source_dir;
      sourceDirDisplay.title = data.source_dir;
    }
  } catch {
    healthStatus.textContent = "后端未启动，请先运行 start.py";
    sourceDirDisplay.textContent = "无法连接后端";
  }
}

function setLiveState(running, hasDefect) {
  liveState.className = "status-pill";
  if (!running) {
    liveState.classList.add("status-idle");
    liveState.textContent = "未启动";
    return;
  }
  if (hasDefect) {
    liveState.classList.add("status-danger");
    liveState.textContent = "异常";
    return;
  }
  liveState.classList.add("status-ok");
  liveState.textContent = "正常";
}

function buildSummary(data) {
  if (!data) {
    summary.textContent = "暂无检测结果";
    return;
  }
  const running = Object.prototype.hasOwnProperty.call(data, "running") ? data.running : true;
  const stateText = running ? (data.has_defect ? "异常" : "正常") : "未启动";
  const confidence = (data.top_confidence * 100).toFixed(1);
  const updated = data.last_updated
    ? new Date(data.last_updated).toLocaleString()
    : data.created_at
      ? new Date(data.created_at).toLocaleString()
      : "-";
  summary.innerHTML = `
    <div>当前判定：${stateText}</div>
    <div class="box-line">预测标签：${data.predicted_label || "-"}</div>
    <div class="box-line">置信度：${confidence}%</div>
    <div class="box-line">缺陷框数量：${data.defect_count}</div>
    <div class="box-line">更新时间：${updated}</div>
    <div class="box-line">状态信息：${data.message || "检测中"}</div>
  `;
}

async function loadVideoStatus() {
  try {
    const response = await fetch("/api/video/status");
    const data = await response.json();
    if (!data.running) return;
    setLiveState(data.running, data.has_defect);
    buildSummary(data);
    detectStatus.textContent = data.message || "检测运行中";
    streamView.src = "/api/video/stream?t=" + Date.now();
  } catch {
    // 网络抖动时静默跳过，下一秒再试
  }
}

async function startVideo() {
  detectStatus.textContent = "正在启动检测...";
  try {
    const response = await fetch("/api/video/start", { method: "POST" });
    const data = await response.json();
    if (!response.ok) {
      detectStatus.textContent = data.detail || "启动失败";
      return;
    }
    streamView.src = "/api/video/stream?t=" + Date.now();
    detectStatus.textContent = "检测已启动";
    setLiveState(data.running, data.has_defect);
    buildSummary(data);
    if (statusTimer) clearInterval(statusTimer);
    statusTimer = setInterval(loadVideoStatus, 1000);
    if (historyTimer) clearInterval(historyTimer);
    historyTimer = setInterval(loadHistory, 3000); // 每 3 秒刷新历史
  } catch {
    detectStatus.textContent = "连接后端失败，请确认后端正在运行";
  }
}

async function stopVideo() {
  try {
    const response = await fetch("/api/video/stop", { method: "POST" });
    const data = await response.json();
    if (statusTimer) { clearInterval(statusTimer); statusTimer = null; }
    if (historyTimer) { clearInterval(historyTimer); historyTimer = null; }
    setLiveState(false, false);
    buildSummary(data);
    detectStatus.textContent = data.message || "检测已停止";
  } catch {
    detectStatus.textContent = "停止失败，请检查后端连接";
  }
}

function renderHistory(items) {
  if (!items.length) {
    historyList.innerHTML = `<div class="summary">暂无记录</div>`;
    return;
  }
  historyList.innerHTML = items.map((item) => {
    const tagClass = item.has_defect ? "pill-danger" : "pill-ok";
    const tagText = item.has_defect ? "异常" : "正常";
    const boxes = item.boxes
      .map((box) => `${box.label} ${(box.confidence * 100).toFixed(1)}%`)
      .join(" / ");
    const imgHtml = item.image_url
      ? `<img src="${item.image_url}" alt="record-${item.id}" />`
      : `<div class="history-no-img">无图片</div>`;
    return `
      <article class="history-item">
        ${imgHtml}
        <div class="history-body">
          <div class="history-top">
            <div class="pill ${tagClass}">${tagText}</div>
            <div class="history-time">${new Date(item.created_at).toLocaleString()}</div>
          </div>
          <div class="history-meta">
            <div class="box-line">置信度：${(item.top_confidence * 100).toFixed(1)}%</div>
            <div class="box-line">缺陷数：${item.defect_count}</div>
          </div>
          <div class="box-line history-boxes">框信息：${boxes || "无"}</div>
        </div>
      </article>
    `;
  }).join("");
}

async function loadHistory() {
  try {
    const params = new URLSearchParams();
    if (historyFilter.value !== "") params.set("has_defect", historyFilter.value);
    const response = await fetch(`/api/records?${params.toString()}`);
    const data = await response.json();
    renderHistory(data);
  } catch {
    historyList.innerHTML = `<div class="summary">历史记录加载失败</div>`;
  }
}

async function loadBlurFilter() {
  try {
    const res = await fetch("/api/blur-filter");
    const data = await res.json();
    blurFilterToggle.checked = data.enabled;
    blurFilterLabel.textContent = data.enabled ? "已启用" : "已关闭";
  } catch { /* 静默 */ }
}

async function toggleBlurFilter() {
  try {
    const res = await fetch("/api/blur-filter", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: blurFilterToggle.checked }),
    });
    const data = await res.json();
    blurFilterLabel.textContent = data.enabled ? "已启用" : "已关闭";
  } catch {
    blurFilterToggle.checked = !blurFilterToggle.checked; // 回滚
  }
}

startStreamBtn.addEventListener("click", startVideo);
stopStreamBtn.addEventListener("click", stopVideo);
refreshBtn.addEventListener("click", loadHistory);
historyFilter.addEventListener("change", loadHistory);
blurFilterToggle.addEventListener("change", toggleBlurFilter);

checkHealth();
loadBlurFilter();
loadHistory();
loadVideoStatus();
