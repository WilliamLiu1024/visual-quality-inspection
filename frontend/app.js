const sourceInput = document.getElementById("sourceInput");
const sampleImageSelect = document.getElementById("sampleImageSelect");
const runSampleBtn = document.getElementById("runSampleBtn");
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

let statusTimer = null;

async function checkHealth() {
  const response = await fetch("/api/health");
  const data = await response.json();
  healthStatus.textContent = data.model_ready
    ? `模型已加载，当前算法：${data.detector_name}`
    : `模型未就绪，当前算法：${data.detector_name}`;
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
    <div class="box-line">推理任务：${data.inference_task || "-"}</div>
    <div class="box-line">当前置信度：${confidence}%</div>
    <div class="box-line">缺陷框数量：${data.defect_count}</div>
    <div class="box-line">来源：${data.source || data.image_url || "-"}</div>
    <div class="box-line">更新时间：${updated}</div>
    <div class="box-line">状态信息：${data.message || "识别完成"}</div>
  `;
}

async function loadSamples() {
  const response = await fetch("/api/test-images");
  const data = await response.json();
  sampleImageSelect.innerHTML = data
    .map((item) => `<option value="${item.name}">${item.name}</option>`)
    .join("");
  if (data[0]) {
    streamView.src = data[0].image_url;
  }
}

async function runSample() {
  if (!sampleImageSelect.value) {
    detectStatus.textContent = "没有可识别的测试图片";
    return;
  }

  detectStatus.textContent = "正在识别测试图...";
  const response = await fetch(`/api/test-images/${encodeURIComponent(sampleImageSelect.value)}/detect`, { method: "POST" });
  const data = await response.json();
  if (!response.ok) {
    detectStatus.textContent = data.detail || "测试图识别失败";
    return;
  }

  streamView.src = data.annotated_image_url;
  setLiveState(true, data.has_defect);
  buildSummary(data);
  detectStatus.textContent = data.has_defect ? "测试图识别完成：异常" : "测试图识别完成：正常";
  await loadHistory();
}

async function loadVideoStatus() {
  const response = await fetch("/api/video/status");
  const data = await response.json();
  if (!data.running) {
    return;
  }
  setLiveState(data.running, data.has_defect);
  buildSummary(data);
  detectStatus.textContent = data.message || "视频流状态已更新";
  streamView.src = "/api/video/stream?t=" + Date.now();
  if (data.has_defect) {
    loadHistory();
  }
}

async function startVideo() {
  detectStatus.textContent = "正在启动动态序列流...";
  const response = await fetch("/api/video/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source: sourceInput.value.trim() || String.raw`D:\05Data\visual-quality-inspection\data\test` }),
  });
  const data = await response.json();

  if (!response.ok) {
    detectStatus.textContent = data.detail || "动态序列流启动失败";
    return;
  }

  streamView.src = "/api/video/stream?t=" + Date.now();
  detectStatus.textContent = "动态序列流已启动";
  setLiveState(data.running, data.has_defect);
  buildSummary(data);
  if (statusTimer) {
    clearInterval(statusTimer);
  }
  statusTimer = setInterval(loadVideoStatus, 1000);
}

async function stopVideo() {
  const response = await fetch("/api/video/stop", { method: "POST" });
  const data = await response.json();
  if (statusTimer) {
    clearInterval(statusTimer);
    statusTimer = null;
  }
  setLiveState(false, false);
  buildSummary(data);
  detectStatus.textContent = data.message || "视频流已停止";
}

function renderHistory(items) {
  if (!items.length) {
    historyList.innerHTML = `<div class="summary">暂无记录</div>`;
    return;
  }

  historyList.innerHTML = items
    .map((item) => {
      const tagClass = item.has_defect ? "pill-danger" : "pill-ok";
      const tagText = item.has_defect ? "异常" : "正常";
      const boxes = item.boxes
        .map((box) => `${box.label} ${(box.confidence * 100).toFixed(1)}%`)
        .join(" / ");

      return `
        <article class="history-item">
          <img src="${item.image_url}" alt="record-${item.id}" />
          <div class="history-body">
            <div class="history-top">
              <div class="pill ${tagClass}">${tagText}</div>
              <div class="history-time">${new Date(item.created_at).toLocaleString()}</div>
            </div>
            <div class="history-meta">
              <div class="box-line">预测标签：${item.predicted_label}</div>
              <div class="box-line">推理任务：${item.inference_task}</div>
              <div class="box-line">置信度：${(item.top_confidence * 100).toFixed(1)}%</div>
              <div class="box-line">缺陷数：${item.defect_count}</div>
            </div>
            <div class="box-line history-boxes">框信息：${boxes || "无"}</div>
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadHistory() {
  const params = new URLSearchParams();
  if (historyFilter.value !== "") {
    params.set("has_defect", historyFilter.value);
  }
  const response = await fetch(`/api/records?${params.toString()}`);
  const data = await response.json();
  renderHistory(data);
}

runSampleBtn.addEventListener("click", runSample);
startStreamBtn.addEventListener("click", startVideo);
stopStreamBtn.addEventListener("click", stopVideo);
refreshBtn.addEventListener("click", loadHistory);
historyFilter.addEventListener("change", loadHistory);
sampleImageSelect.addEventListener("change", () => {
  if (sampleImageSelect.value) {
    streamView.src = `/test-images/${encodeURIComponent(sampleImageSelect.value)}`;
    detectStatus.textContent = `已选择测试图：${sampleImageSelect.value}`;
  }
});

checkHealth();
loadSamples();
loadHistory();
loadVideoStatus();
