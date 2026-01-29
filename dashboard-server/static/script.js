/**
 * SCRIPT.JS - Dashboard & Logic
 * Organized for maintainability
 */

document.addEventListener("DOMContentLoaded", () => {

  /* ==========================================================================
     1. GLOBAL STATE & VARIABLES
     ========================================================================== */
  let attentionChart;
  let attentionDataAll = [];
  let attentionDataWindow = [];
  let timeLabels = [];
  let heatmapData = [];

  // ===== Live window config =====
  const WINDOW_SECONDS = 90;   // 1.5 minute
  const ALERT_SECONDS = 120;    // 2 minutes
  const SAMPLE_INTERVAL = 5;    // seconds
  const MAX_POINTS = WINDOW_SECONDS / SAMPLE_INTERVAL;
  const ALERT_POINTS = ALERT_SECONDS / SAMPLE_INTERVAL;

  const sessionStatus = document.getElementById("sessionStatus");

  const subjectName = document.getElementById("subjectName");

  const sessionTimerEl = document.getElementById("sessionTimer");
  let timerInterval = null;

  let sessionActive = false;
  let sessionPaused = false;
  let chartInterval = null;
  let sessionStartTime = null;
  let pausedAt = null;

  let timetableData = {};
  let facultyData = {};

  const INSIGHTS = [
  "health",
  "timeBelow",
  "pattern"
];

let currentInsightIndex = 0;
let forcedInsight = null;
let forceTimeout = null;

const insightCard = document.getElementById("sessionInsightCard");
const insightTitle = document.getElementById("card-title");
const insightValue = document.getElementById("insightValue");
const insightSub = document.getElementById("insightSub");

const insightLabel = document.getElementById("insightLabel");
const insightAvg = document.getElementById("insightAvg");
const insightStability = document.getElementById("insightStability");
const insightRisk = document.getElementById("insightRisk");

updateSessionStatus("inactive");

/* ==========================================================================
     1a. SESSION STATUS UPDATER
     ========================================================================== */

function updateSessionStatus(state) {
  if (!sessionStatus) return;

  sessionStatus.classList.remove("active", "paused", "inactive");

  const text = sessionStatus.querySelector(".status-text");

  if (state === "active") {
    sessionStatus.classList.add("active");
    text.textContent = "Session Live";
  }

  if (state === "paused") {
    sessionStatus.classList.add("paused");
    text.textContent = "Session Paused";
  }

  if (state === "inactive") {
    sessionStatus.classList.add("inactive");
    text.textContent = "Session Inactive";
  }
}

  /* ==========================================================================
     1b. SESSION HISTORY LOADER
     ========================================================================== */

async function loadSessionHistory() {
  const list = document.getElementById("allSessionsList");
  if (!list) return;

  list.innerHTML = "";

  try {
    const res = await fetch("/api/sessions");
    if (!res.ok) throw new Error("Failed to fetch sessions");

    const sessions = await res.json();

    if (!sessions.length) {
      list.innerHTML = `
        <div style="opacity:0.6; text-align:center; grid-column:1/-1;">
          No sessions recorded yet
        </div>`;
      return;
    }

sessions.forEach(s => {
  const start = new Date(s.start_time);
  const end = s.end_time ? new Date(s.end_time) : null;

  const duration = end
    ? Math.round((end - start) / 60000) + " min"
    : "—";

const row = document.createElement("div");
row.className = "session-row";
row.dataset.sessionId = s.id;

row.innerHTML = `
  <div class="session-info">
    <div style="font-weight:600" class="session-title">${s.subject}</div>
    <div style="font-size:0.75rem; opacity:0.6" class="session-id">ID: ${s.id}</div>
  </div>

  <div style="font-size:0.85rem; opacity:0.75" class="session-time">
    ${start.toLocaleString()}
  </div>

  <div style="font-size:0.85rem" class="session-duration">
    ${duration}
  </div>

  <div class="row-action">
    <input type="checkbox" class="row-checkbox" />
    <button class="row-delete-btn" title="Delete session">
      <i class="fas fa-trash"></i>
    </button>
  </div>
`;

list.appendChild(row);
});

  } catch (err) {
    console.error(err);
    list.innerHTML = `
      <div style="color:#f87171; grid-column:1/-1; text-align:center;">
        Failed to load sessions
      </div>`;
  }
}

  /* ==========================================================================
     2. DATA FETCHING (API & JSON)
     ========================================================================== */

  // Load Timetable and Faculty static data
  async function loadTimetableData() {
    try {
      const timetableRes = await fetch("/static/data/timetable.json");
      timetableData = await timetableRes.json();

      const facultyRes = await fetch("/static/data/faculty.json");
      facultyData = await facultyRes.json();
      
      // Initial update once data is loaded
      updateNavbarFromTimetable();
    } catch (err) {
      console.error("Error loading timetable data:", err);
    }
  }

  // Fetch Sensor Data from Flask Backend
  async function fetchSensorData() {
    try {
      const response = await fetch('http://172.20.10.2:5000/sensor-data');
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      const data = await response.json();

      // Update dashboard cards
      document.getElementById('tempValue').innerText = `${data.temperature.toFixed(1)} °C`;
      document.getElementById('humValue').innerText = `${data.humidity.toFixed(1)} %`;
      document.getElementById('noiseValue').innerText = `${data.noise}`;
      document.getElementById('lightValue').innerText = `${data.light}`;
      document.getElementById('co2Value').innerText = `${data.co2}`;
    } catch (err) {
      console.error("Error fetching sensor data:", err);
    }
  }

  /* ==========================================================================
     3. CHARTING & HEATMAP LOGIC
     ========================================================================== */

  function initAttentionChart() {
    const canvas = document.getElementById("attentionChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    attentionChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: timeLabels,
        datasets: [{
  data: attentionDataWindow,
  shadowColor: "rgba(99,102,241,0.35)",
shadowBlur: 12,

  // 🔵 Gradient stroke (dynamic)
  borderColor: (ctx) => {
    const chart = ctx.chart;
    const {ctx: c, chartArea} = chart;
    if (!chartArea) return "#7dd3fc";

    const gradient = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    gradient.addColorStop(0, "#93c5fd");
    gradient.addColorStop(1, "#6366f1");
    return gradient;
  },

  // 🌊 Subtle area fill
  fill: {
    target: "origin",
    above: "rgba(99,102,241,0.06)"
  },

  borderWidth: 2.5,
  tension: 0.35,

  // 🎯 Points only matter when bad
  pointRadius: (ctx) => ctx.raw < 40 ? 3 : 0,
  pointBackgroundColor: "rgba(248,113,113,0.75)",
  pointBorderColor: "rgba(248,113,113,0.9)",
  pointBorderWidth: 1,
  pointHoverRadius: 5
}]
      },
      devicePixelRatio: window.devicePixelRatio || 1,
      options: {
        animation: false,
          plugins: {
          legend: {
            display: false
          }
        },
        layout: {
  padding: 0
},
        maintainAspectRatio: false,
        responsive: true,
        interaction: {
        intersect: false,
        mode: "index"
      },
        scales: {
        y: {
  min: 0,
  max: 100,
  ticks: {
    padding: 10,          // 🔥 pushes labels away from axis
    align: "center",      // 🔥 prevents vertical drift
    font: { size: 11 }
  },
  grid: {
    drawTicks: false
  },
  border: { display: false }
},
        x: {
  ticks: {
    color: "rgba(148,163,184,0.6)",
    maxTicksLimit: 6,
    padding: 12,          // 🔥 THIS moves labels down
    font: {
      size: 11,
      lineHeight: 1.3
    }
  },
  grid: {
    drawTicks: false
  },
  border: {
    display: false
  }
}
      }
      }
    });
  }

async function computeAttentiveness() {
  try {
    const res = await fetch("http://127.0.0.1:5001/attention");
    if (!res.ok) throw new Error("Attention API failed");
    const data = await res.json();
    return typeof data.attention === "number" ? data.attention : null;
  } catch (err) {
    console.error("Attention fetch error:", err);
    return null;
  }
}

const avgEng = document.getElementById("avgEng");
const peakEng = document.getElementById("peakEng");

function renderHeatmap(data) {
  const grid = document.getElementById("heatmapGrid");
  if (!grid) return;
  grid.innerHTML = "";

const columns = 12;
const rows = getComputedStyle(document.getElementById("heatmapGrid"))
  .gridTemplateRows.split(" ").length;

const maxCells = columns * rows;

  if (!data.length) {
    for (let i = 0; i < maxCells; i++) {
      const cell = document.createElement("div");
      cell.className = "heatmap-cell";
      grid.appendChild(cell);
    }
    avgEng.textContent = "—";
    peakEng.textContent = "—";
    return;
  }

  const trimmedData = data.slice(-maxCells);
  let sum = 0;
  let peak = 0;

  trimmedData.forEach(val => {
    sum += val;
    peak = Math.max(peak, val);

    const cell = document.createElement("div");
    cell.className = "heatmap-cell";

    if (val < 40) cell.style.background = "#1f2933";
    else if (val < 60) cell.style.background = "rgba(167,139,250,0.35)";
    else if (val < 80) cell.style.background = "rgba(167,139,250,0.65)";
    else cell.style.background = "#a78bfa";

    grid.appendChild(cell);
  });

  avgEng.textContent = Math.round(sum / trimmedData.length);
  peakEng.textContent = peak;
}

 /* ==========================================================================
     3.1. SESSION INSIGHTS LOGIC
     ========================================================================== */


function computeSessionHealth() {
  if (!attentionDataAll.length) return null;

  const avg =
    attentionDataAll.reduce((a, b) => a + b, 0) / attentionDataAll.length;

  const volatility =
    Math.sqrt(
      attentionDataAll
        .map(v => Math.pow(v - avg, 2))
        .reduce((a, b) => a + b, 0) / attentionDataAll.length
    );

  let health = Math.round(avg - volatility / 2);
  health = Math.max(0, Math.min(100, health));

  return { health, volatility };
}

function computeTimeBelowThreshold(threshold = 40) {
  const recent = attentionDataWindow.slice(-ALERT_POINTS);
  return recent.filter(v => v < threshold).length * SAMPLE_INTERVAL;
}

function renderInsight(type) {
  if (type === "health") {
  const data = computeSessionHealth();
  if (!data) return;

  const avg =
    attentionDataAll.reduce((a, b) => a + b, 0) / attentionDataAll.length;

  const volatility = data.volatility;
  const health = data.health;

  // Primary
  insightTitle.textContent = "Session Health";
  insightValue.textContent = `${health} / 100`;

  // Label
  let label = "Stable Engagement";
  if (volatility > 25) label = "Highly Volatile";
  else if (health < 60) label = "At Risk";

  insightLabel.textContent = label;

  // Breakdown
  insightAvg.textContent = `Avg: ${Math.round(avg)}%`;
  insightStability.textContent =
    `Stability: ${volatility < 20 ? "High" : "Low"}`;
  insightRisk.textContent =
    `Risk: ${health < 60 ? "High" : "Low"}`;

  // Context
  insightSub.textContent =
    volatility > 25
      ? "Large fluctuations detected"
      : "Consistent engagement pattern";
}

  if (type === "timeBelow") {
    const seconds = computeTimeBelowThreshold();
    insightTitle.textContent = "Low Attention Time";
    insightValue.textContent = `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    insightSub.textContent = "Below 40% attentiveness";
  }

  if (type === "pattern") {
    insightTitle.textContent = "Engagement Pattern";
    insightValue.textContent = "Early Drop-off";
    insightSub.textContent = "Detected this session";
  }
}

  /* ==========================================================================
     4. SESSION CONTROL (START/PAUSE/STOP)
     ========================================================================== */

function startChartPlotting() {
  if (chartInterval) return; // HARD LOCK

  attentionDataAll.length = 0;
attentionDataWindow.length = 0;
timeLabels.length = 0;
heatmapData.length = 0;

  attentionChart.update();
  renderHeatmap([]);

  sessionStartTime = Date.now();
  sessionPaused = false;

  chartInterval = setInterval(async () => {
    if (!sessionActive || sessionPaused) return;

    const elapsed = Date.now() - sessionStartTime;
    const min = String(Math.floor(elapsed / 60000)).padStart(2, "0");
    const sec = String(Math.floor((elapsed % 60000) / 1000)).padStart(2, "0");

    const value = await computeAttentiveness();
if (value === null) return; // skip this tick

    // 1️⃣ Full-session memory
attentionDataAll.push(value);

// 2️⃣ Live window (chart + alert)
attentionDataWindow.push(value);
timeLabels.push(`${min}:${sec}`);

// 🔪 HARD SLIDING WINDOW
if (attentionDataWindow.length > MAX_POINTS) {
  attentionDataWindow.shift();
  timeLabels.shift();
}

// 3️⃣ Heatmap keeps rolling history
heatmapData.push(value);

    const lowTime = computeTimeBelowThreshold();

if (lowTime > 120 && forcedInsight !== "timeBelow") {
  forcedInsight = "timeBelow";
  renderInsight("timeBelow");

  clearTimeout(forceTimeout);
  forceTimeout = setTimeout(() => {
    forcedInsight = null;
    renderInsight("health");
  }, 7000);
}

    renderHeatmap(heatmapData);
    attentionChart.update();
  }, 5000);
}

  function pauseChartPlotting() {
    sessionPaused = true;
    pausedAt = Date.now();
  }

  function resumeChartPlotting() {
    if (!sessionPaused) return;
    const pauseDuration = Date.now() - pausedAt;
    sessionStartTime += pauseDuration;
    sessionPaused = false;
  }

async function stopChartPlotting() {

  // ===== STOP SESSION TIMER =====
clearInterval(timerInterval);
timerInterval = null;

if (sessionTimerEl) {
  sessionTimerEl.hidden = true;
  sessionTimerEl.textContent = "Session inactive";
  sessionTimerEl.className = "session-timer";
}
  if (chartInterval) {
    clearInterval(chartInterval);
    chartInterval = null;
  }

  sessionActive = false;
  sessionPaused = false;
  pauseBtn.textContent = "Pause";
  updateSessionStatus("inactive");

  // 🔥 HARD RESET UI STATE
  attentionDataAll.length = 0;
attentionDataWindow.length = 0;
timeLabels.length = 0;
heatmapData.length = 0;

  attentionChart.update();
  renderHeatmap([]);

  document.getElementById("avgEng").textContent = "—";
  document.getElementById("peakEng").textContent = "—";

  try {
    await fetch("http://127.0.0.1:5001/session/stop", { method: "POST" });
  } catch (e) {
    console.error("Failed to stop session", e);
  }
}

/* function updateButtonStates() {
  startBtn.disabled = sessionActive;
  pauseBtn.disabled = !sessionActive;
  stopBtn.disabled = !sessionActive;
}
*/

  /* ==========================================================================
     5. UI UPDATES (TIME & NAVBAR)
     ========================================================================== */

  function updateDateTime() {
    const now = new Date();
    const time = now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const date = now.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
    const el = document.getElementById("realtime-datetime");
    if (el) el.textContent = `${date} ${time}`;
  }

  function getCurrentClassFromTimetable() {
    const now = new Date();
    const day = now.toLocaleDateString("en-GB", { weekday: "long" });
    const time = now.toTimeString().slice(0, 5); // HH:MM

    const todaySchedule = timetableData[day];
    if (!todaySchedule) return { subject: "No Scheduled Class", faculty: "—" };

    for (const slot of todaySchedule) {
      if (time >= slot.start && time < slot.end) {
        if (slot.type === "BREAK") return { subject: slot.label, faculty: "—" };
        const facultyNames = slot.faculty.map(code => facultyData[code] || code).join(", ");
        return { subject: slot.subject, faculty: facultyNames };
      }
    }
    return { subject: "No Scheduled Class", faculty: "—" };
  }

  function updateNavbarFromTimetable() {
    const subjectEl = document.getElementById("subjectName");
    const facultyEl = document.getElementById("facultyName");
    if (!subjectEl || !facultyEl) return;

    const current = getCurrentClassFromTimetable();
    subjectEl.textContent = current.subject;
    facultyEl.textContent = current.faculty;
  }

  /* ==========================================================================
     5.1 SESSION TIMER
     ========================================================================== */

    function formatElapsed(ms) {
    const totalSec = Math.floor(ms / 1000);
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;

    if (h > 0) {
      return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;
    }
    return `${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;
  }

  /* ==========================================================================
     6. EVENT LISTENERS & INITIALIZATION
     ========================================================================== */

  // --- Initialize Components ---
  initAttentionChart();
  renderHeatmap([]);
  renderInsight("health");
  updateDateTime();
  setInterval(updateDateTime, 1000);

  loadSessionHistory();

/* ==========================================================================
   6a. SELECTION MODE BUTTON
   ========================================================================== */

/* ==========================================================================
   6a. SELECTION MODE BUTTON (SAFE)
   ========================================================================== */

const selectToggleBtn = document.getElementById("selectToggle");
const sessionList = document.querySelector(".session-list");
const sessionsContainer = document.getElementById("allSessionsList");
const selectionToolbar = document.getElementById("selectionToolbar");

if (selectToggleBtn && sessionList && sessionsContainer && selectionToolbar) {

  const selectionCountEl =
    selectionToolbar.querySelector(".selection-count");

  let selectionMode = false;

  selectToggleBtn.addEventListener("click", () => {
    selectionMode = !selectionMode;

    sessionList.classList.toggle("selection-mode", selectionMode);
    selectToggleBtn.classList.toggle("active", selectionMode);
    selectToggleBtn.textContent = selectionMode ? "Cancel" : "Select";

    selectionToolbar.style.display = selectionMode ? "flex" : "none";

    if (!selectionMode) clearSelections();
  });

  function clearSelections() {
    document.querySelectorAll(".row-checkbox").forEach(cb => {
      cb.checked = false;
      cb.closest(".session-row")?.classList.remove("selected");
    });
    updateSelectionCount();
  }

  function updateSelectionCount() {
    const count =
      document.querySelectorAll(".row-checkbox:checked").length;
    selectionCountEl.textContent = `${count} selected`;
  }

  sessionsContainer.addEventListener("click", (e) => {
    if (!selectionMode) return;

    const row = e.target.closest(".session-row");
    if (!row) return;
    if (e.target.closest(".row-delete-btn")) return;

    const checkbox = row.querySelector(".row-checkbox");
    if (!checkbox) return;

    if (e.target !== checkbox) {
      checkbox.checked = !checkbox.checked;
    }

    row.classList.toggle("selected", checkbox.checked);
    updateSelectionCount();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && selectionMode) {
      selectionMode = false;
      sessionList.classList.remove("selection-mode");
      selectToggleBtn.classList.remove("active");
      selectToggleBtn.textContent = "Select";
      selectionToolbar.style.display = "none";
      clearSelections();
    }
  });
}

/* ==========================================================================
   6b. DELETE LOGIC (SINGLE + BULK)
   ========================================================================== */

const deleteModal = document.getElementById("deleteModal");
const confirmDeleteBtn = document.getElementById("confirmDelete");
const cancelDeleteBtn = document.getElementById("cancelDelete");
const closeDeleteModal = document.getElementById("closeDeleteModal");

let deleteQueue = [];
let deleteRows = [];

function openDeleteModal({ ids, rows }) {
  deleteQueue = ids;
  deleteRows = rows;

  const title = document.getElementById("deleteModalTitle");
  const text = document.getElementById("deleteModalText");

  if (ids.length === 1) {
    title.textContent = "Delete session?";
    text.textContent = "This session will be permanently deleted.";
  } else {
    title.textContent = `Delete ${ids.length} sessions?`;
    text.textContent = "All selected sessions will be permanently deleted.";
  }

  deleteModal.classList.add("active");
}

function closeDeleteModalFn() {
  deleteModal.classList.remove("active");
  deleteQueue = [];
  deleteRows = [];
}

cancelDeleteBtn?.addEventListener("click", closeDeleteModalFn);
closeDeleteModal?.addEventListener("click", closeDeleteModalFn);

deleteModal?.addEventListener("click", (e) => {
  if (e.target === deleteModal) closeDeleteModalFn();
});

sessionsContainer?.addEventListener("click", (e) => {
  const deleteBtn = e.target.closest(".row-delete-btn");
  if (!deleteBtn) return;

  const row = deleteBtn.closest(".session-row");
  if (!row) return;

  const sessionId = row.dataset.sessionId;
  if (!sessionId) return;

  openDeleteModal({
    ids: [sessionId],
    rows: [row]
  });
});

const bulkDeleteBtn = document.querySelector(".bulk-delete-btn");

bulkDeleteBtn?.addEventListener("click", () => {
  const checked = document.querySelectorAll(".row-checkbox:checked");
  if (!checked.length) return;

  const ids = [];
  const rows = [];

  checked.forEach(cb => {
    const row = cb.closest(".session-row");
    if (!row) return;

    ids.push(row.dataset.sessionId);
    rows.push(row);
  });

  openDeleteModal({ ids, rows });
});

confirmDeleteBtn?.addEventListener("click", async () => {
  if (!deleteQueue.length) return;

  try {
    const res = await fetch("/api/sessions/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: deleteQueue })
    });

    if (!res.ok) throw new Error("Delete failed");

    // Remove rows from DOM
    deleteRows.forEach(row => row.remove());

    // Reset selection UI
    document.querySelectorAll(".row-checkbox").forEach(cb => cb.checked = false);
    document.querySelectorAll(".session-row").forEach(r => r.classList.remove("selected"));

    const countEl = document.querySelector(".selection-count");
    if (countEl) countEl.textContent = "0 selected";

    closeDeleteModalFn();

  } catch (err) {
    console.error(err);
    alert("Failed to delete sessions");
  }
});
  
/* ==========================================================================
   TIME TABLE LOGIC
   ========================================================================== */

  loadTimetableData().then(() => {
    setInterval(updateNavbarFromTimetable, 60000);
  });

  // --- Sensor Logic ---
  fetchSensorData();
  setInterval(fetchSensorData, 3000);

  // --- Modal Logic ---
  const logoutBtn = document.getElementById("logoutBtn");
  const logoutModal = document.getElementById("logoutModal");
  const cancelLogout = document.getElementById("cancelLogout");
  const closeLogout = document.getElementById("closeLogout");

  function closeModal() {
    logoutModal.classList.remove("active");
    logoutBtn.focus();
  }

  if (logoutBtn && logoutModal && cancelLogout && closeLogout) {
    logoutBtn.addEventListener("click", (e) => {
      e.preventDefault();
      logoutModal.classList.add("active");
    });
    cancelLogout.addEventListener("click", closeModal);
    closeLogout.addEventListener("click", closeModal);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && logoutModal.classList.contains("active")) closeModal();
    });
    logoutModal.addEventListener("click", (e) => {
      if (e.target === logoutModal) closeModal();
    });
  }

  // --- Session Control Listeners ---
  const startBtn = document.getElementById("startBtn");
  const pauseBtn = document.getElementById("pauseBtn");
  const stopBtn = document.getElementById("stopBtn");

  if (startBtn && pauseBtn && stopBtn) {
    startBtn.addEventListener("click", async () => {
  if (sessionActive) return;

  try {
    await fetch("http://127.0.0.1:5001/session/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject: subjectName.textContent || "Unknown" })
    });

    sessionActive = true;
    sessionPaused = false;
    updateSessionStatus("active");
    startChartPlotting();

    // ===== START SESSION TIMER =====
    sessionTimerEl.hidden = false;
    sessionTimerEl.className = "session-timer active";
    sessionTimerEl.textContent = "Session Live · 00:00";

    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      if (!sessionActive || sessionPaused) return;

      const elapsed = Date.now() - sessionStartTime;
      sessionTimerEl.textContent =
        `Session Live · ${formatElapsed(elapsed)}`;
    }, 1000);

  } catch (e) {
    console.error("Failed to start session", e);
  }
});

    pauseBtn.addEventListener("click", () => {
  if (!sessionActive) return;

  if (!sessionPaused) {
    pauseChartPlotting();
    sessionPaused = true;
    pauseBtn.textContent = "Resume";
    updateSessionStatus("paused");
    document.querySelector(".chart-wrapper")?.classList.add("paused");
    sessionTimerEl.className = "session-timer paused";
    sessionTimerEl.textContent =
      `⏸ Session Paused · ${formatElapsed(Date.now() - sessionStartTime)}`;
  } else {
    resumeChartPlotting();
    sessionPaused = false;
    pauseBtn.textContent = "Pause";
    updateSessionStatus("active");
    document.querySelector(".chart-wrapper")?.classList.remove("paused");
    sessionTimerEl.className = "session-timer active";
  }
});

    stopBtn.addEventListener("click", () => {
      if (!sessionActive) return;
      stopChartPlotting();
      document.querySelector(".chart-wrapper")?.classList.remove("paused");
      pauseBtn.textContent = "Pause";
    });
  }

// --- Insight Card Listener ---

  if (insightCard) {
  insightCard.addEventListener("click", () => {
    if (forcedInsight) return;

    currentInsightIndex =
      (currentInsightIndex + 1) % INSIGHTS.length;

    renderInsight(INSIGHTS[currentInsightIndex]);
  });
}

});