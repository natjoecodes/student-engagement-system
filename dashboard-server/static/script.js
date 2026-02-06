/**
 * SCRIPT.JS - Dashboard & Logic
 * Organized for maintainability
 */

document.addEventListener("DOMContentLoaded", () => {

  const isDashboard = document.querySelector(".dashboard-container");
  const isSessionsPage = document.querySelector(".sessions-page");

  /* ==========================================================================
     1. GLOBAL STATE & VARIABLES
     ========================================================================== */
  let attentionChart;
  let attentionDataAll = [];
  let attentionDataWindow = [];
  let timeLabels = [];
  let heatmapData = [];

  let sensorInterval = null;

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

const SENSOR_RULES = {
  co2: {
    optimal: [600, 800],
    warning: [800, 1000],
    danger: [1000, Infinity],
    unit: "ppm"
  },
  temperature: {
    optimal: [22, 28],
    warning: [28, 32],
    danger: [32, Infinity],
    unit: "°C"
  },
  humidity: {
    optimal: [40, 60],
    warning: [60, 70],
    danger: [70, Infinity],
    unit: "%"
  },
  noise: {
    optimal: [0, 35],
    warning: [35, 50],
    danger: [50, Infinity],
    unit: "dB"
  },
  light: {
    optimal: [300, 500],
    warning: [200, 300],
    danger: [0, 200],
    unit: "lux"
  }
};

let currentInsightIndex = 0;
let forcedInsight = null;
let forceTimeout = null;

const INSIGHT_STATE = {
  INACTIVE: "inactive",
  COLLECTING: "collecting",
  ACTIVE: "active"
};

let insightState = INSIGHT_STATE.INACTIVE;

const insightCard = document.getElementById("sessionInsightCard");
const insightTitle = document.getElementById("card-title");
const insightValue = document.getElementById("insightValue");
const insightSub = document.getElementById("insightSub");

const insightLabel = document.getElementById("insightLabel");
const insightAvg = document.getElementById("insightAvg");
const insightStability = document.getElementById("insightStability");
const insightRisk = document.getElementById("insightRisk");

updateSessionStatus("inactive");

const backBtn = document.getElementById("backBtn");

backBtn?.addEventListener("click", () => {
  if (document.referrer) {
    history.back();
  } else {
    window.location.href = "/dashboard";
  }
});

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
    <div style="font-weight:600" class="session-title">
      ${s.subject}
    </div>
    <div style="font-size:0.8rem; opacity:0.7" class="session-faculty">
      ${s.faculty || "—"}
    </div>
  </div>

  <div style="font-size:0.85rem; opacity:0.75" class="session-time">
  ${start.toLocaleString("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: true
  })
  .replace(" am", " AM")
  .replace(" pm", " PM")
}
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

    // ===== SENSOR HELPERS =====

  function computeSensorPercent(value, rule) {
    const clamp = (v, min, max) => Math.max(min, Math.min(max, v));

    // OPTIMAL → 30–70%
    if (value >= rule.optimal[0] && value <= rule.optimal[1]) {
      const [min, max] = rule.optimal;
      const t = (value - min) / (max - min);
      return clamp(30 + t * 40, 30, 70);
    }

    // WARNING → 70–90%
    if (value >= rule.warning[0] && value <= rule.warning[1]) {
      const [min, max] = rule.warning;
      const t = (value - min) / (max - min);
      return clamp(70 + t * 20, 70, 90);
    }

    // DANGER → 90–100%
    const dangerMin = rule.danger[0];
    const span = rule.warning[1] - rule.warning[0] || 1;
    const t = (value - dangerMin) / span;
    return clamp(90 + t * 10, 90, 100);
  }

  function evaluateSensor(value, rule) {
  if (value >= rule.optimal[0] && value <= rule.optimal[1]) {
    return "optimal";
  }
  if (value >= rule.warning[0] && value <= rule.warning[1]) {
    return "warning";
  }
  return "danger";
}

function updateSensorCard({
  card,
  valueEl,
  fillEl,
  statusEl,
  value,
  rule
}) {
  const state = evaluateSensor(value, rule);

  valueEl.innerHTML = `${value}<span>${rule.unit}</span>`;

  const percent = computeSensorPercent(Number(value), rule);
  fillEl.style.width = `${percent}%`;

  card.dataset.state = state;

  statusEl.className =
    "sensor-status " +
    (state === "optimal" ? "ok" : state);

  statusEl.textContent =
    state === "optimal"
      ? "Normal"
      : state === "warning"
      ? "Warning"
      : "Critical";

  return state;
}

  // Fetch Sensor Data from Flask Backend
  async function fetchSensorData() {
    const alertStates = [];

    try {
      const response = await fetch('/sensor-data');
      if (!sessionActive || sessionPaused) return;
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      
      const data = await response.json();

    alertStates.push(
      updateSensorCard({
        card: document.getElementById("co2Value").closest(".card"),
        valueEl: document.getElementById("co2Value"),
        fillEl: document.getElementById("co2Value")
          .closest(".card")
          .querySelector(".sensor-fill"),
        statusEl: document.getElementById("co2Value")
          .closest(".card")
          .querySelector(".sensor-status"),
        value: data.co2,
        rule: SENSOR_RULES.co2
      })
    );

    alertStates.push(
      updateSensorCard({
        card: document.getElementById("tempValue").closest(".card"),
        valueEl: document.getElementById("tempValue"),
        fillEl: document.getElementById("tempValue")
          .closest(".card")
          .querySelector(".sensor-fill"),
        statusEl: document.getElementById("tempValue")
          .closest(".card")
          .querySelector(".sensor-status"),
        value: data.temperature.toFixed(1),
        rule: SENSOR_RULES.temperature
      })
    );

    alertStates.push(
      updateSensorCard({
        card: document.getElementById("humValue").closest(".card"),
        valueEl: document.getElementById("humValue"),
        fillEl: document.getElementById("humValue")
          .closest(".card")
          .querySelector(".sensor-fill"),
        statusEl: document.getElementById("humValue")
          .closest(".card")
          .querySelector(".sensor-status"),
        value: data.humidity.toFixed(1),
        rule: SENSOR_RULES.humidity
      })
    );

    alertStates.push(
      updateSensorCard({
        card: document.getElementById("noiseValue").closest(".card"),
        valueEl: document.getElementById("noiseValue"),
        fillEl: document.getElementById("noiseValue")
          .closest(".card")
          .querySelector(".sensor-fill"),
        statusEl: document.getElementById("noiseValue")
          .closest(".card")
          .querySelector(".sensor-status"),
        value: data.noise,
        rule: SENSOR_RULES.noise
      })
    );

    alertStates.push(
      updateSensorCard({
        card: document.getElementById("lightValue").closest(".card"),
        valueEl: document.getElementById("lightValue"),
        fillEl: document.getElementById("lightValue")
          .closest(".card")
          .querySelector(".sensor-fill"),
        statusEl: document.getElementById("lightValue")
          .closest(".card")
          .querySelector(".sensor-status"),
        value: data.light,
        rule: SENSOR_RULES.light
      })
    );

    } catch (err) {
      console.error("Error fetching sensor data:", err);
    }
    updateGlobalAlert(alertStates);
  }

  function startSensorPolling() {
  if (sensorInterval) return;

  fetchSensorData(); // immediate first hit
  sensorInterval = setInterval(fetchSensorData, 3000);
}

function stopSensorPolling() {
  clearInterval(sensorInterval);
  sensorInterval = null;

  if (!document.querySelector(".right-panel")) return;

  document.querySelectorAll(".right-panel .card").forEach(card => {
    const value = card.querySelector(".sensor-value");
    const fill = card.querySelector(".sensor-fill");
    const status = card.querySelector(".sensor-status");

    if (value) value.innerHTML = "—<span></span>";
    if (fill) fill.style.width = "0%";   // 🔴 THIS WAS MISSING
    if (status) {
      status.className = "sensor-status";
      status.textContent = "—";
    }

    delete card.dataset.state;
  });

  // Reset sensor UI
  document.getElementById("tempValue").innerHTML = "—<span>°C</span>";
  document.getElementById("humValue").innerHTML = "—<span>%</span>";
  document.getElementById("noiseValue").innerHTML = "—<span>dB</span>";
  document.getElementById("lightValue").innerHTML = "—<span>lux</span>";
  document.getElementById("co2Value").innerHTML = "—<span>ppm</span>";
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

    if (val === 0) {
      cell.style.background = "rgba(88, 80, 150, 0.35)";
    }
    else if (val < 40) {
      cell.style.background = "#1f2933";
    }
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

function renderInsightInactive() {
  insightTitle.textContent = "Session Health";
  insightValue.textContent = "No data";
  insightValue.classList.add("muted");

  insightLabel.textContent = "Session inactive";

  insightAvg.textContent = "Avg: —%";
  insightStability.textContent = "Stability: —";
  insightRisk.textContent = "Risk: —";

  insightSub.textContent = "";
}

function renderInsightCollecting() {
  insightTitle.textContent = "Session Health";
  insightValue.textContent = "Collecting…";
  insightValue.classList.add("muted");

  insightLabel.textContent = "Gathering engagement data";
  insightSub.textContent = "Needs ~30 seconds of live data";

  insightAvg.textContent = "Avg: —%";
  insightStability.textContent = "Stability: —";
  insightRisk.textContent = "Risk: —";
}

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

function updateInsightState() {
  if (!sessionActive) {
    insightState = INSIGHT_STATE.INACTIVE;
    renderInsightInactive();
    return;
  }

  if (attentionDataAll.length < 6) { // < 30 seconds of data
    insightState = INSIGHT_STATE.COLLECTING;
    renderInsightCollecting();
    return;
  }

  insightState = INSIGHT_STATE.ACTIVE;
  renderInsight("health");
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

  insightCard.classList.remove("health-good","health-warn","health-risk");

if (health >= 75) insightCard.classList.add("health-good");
else if (health >= 60) insightCard.classList.add("health-warn");
else insightCard.classList.add("health-risk");

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
updateInsightState();

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
  updateInsightState();

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

function updateGlobalAlert(states) {
  const alertBar = document.querySelector(".scoped-alert");
  if (!alertBar) return;

  if (states.includes("danger")) {
    alertBar.style.opacity = "1";
    alertBar.querySelector(".alert-emphasis").textContent =
      "Critical environment";
    alertBar.querySelector(".alert-text").textContent =
      "Immediate attention required";
    return;
  }

  if (states.includes("warning")) {
    alertBar.style.opacity = "1";
    alertBar.querySelector(".alert-emphasis").textContent =
      "Suboptimal conditions";
    alertBar.querySelector(".alert-text").textContent =
      "Environmental stress detected";
    return;
  }

  alertBar.style.opacity = "0.6";
  alertBar.querySelector(".alert-emphasis").textContent =
    "Environment stable";
  alertBar.querySelector(".alert-text").textContent =
    "All parameters within range";
}

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
  if (isDashboard) {
    initAttentionChart();
    renderHeatmap([]);
    updateInsightState();
    stopSensorPolling();
  }

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
    if (e.key === "Escape" && selectionMode && !deleteModalOpen) {
      selectionMode = false;
      sessionList.classList.remove("selection-mode");
      selectToggleBtn.classList.remove("active");
      selectToggleBtn.textContent = "Select";
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

let deleteModalOpen = false;

function openDeleteModal({ ids, rows }) {
  deleteQueue = ids;
  deleteRows = rows;
  deleteModalOpen = true;

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
  deleteModalOpen = false;
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
    const facultyName = document.getElementById("facultyName")?.textContent || "—";

    await fetch("http://127.0.0.1:5001/session/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subject: subjectName.textContent || "Unknown",
        faculty: facultyName
      })
    });

    sessionActive = true;
    sessionPaused = false;
    updateSessionStatus("active");
    updateInsightState();
    startChartPlotting();
    startSensorPolling();

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
    stopSensorPolling();
    document.querySelectorAll(".sensor-fill").forEach(fill => {
    fill.style.opacity = "0.5"; // visual freeze
  });
    pauseBtn.textContent = "Resume";
    updateSessionStatus("paused");
    document.querySelector(".chart-wrapper")?.classList.add("paused");
    sessionTimerEl.className = "session-timer paused";
    sessionTimerEl.textContent =
      `⏸ Session Paused · ${formatElapsed(Date.now() - sessionStartTime)}`;
  } else {
    resumeChartPlotting();
    sessionPaused = false;
    startSensorPolling();
    pauseBtn.textContent = "Pause";
    updateSessionStatus("active");
    document.querySelector(".chart-wrapper")?.classList.remove("paused");
    sessionTimerEl.className = "session-timer active";
  }
});

    stopBtn.addEventListener("click", () => {
      if (!sessionActive) return;
      stopChartPlotting();
      stopSensorPolling();
      document.querySelectorAll(".sensor-fill").forEach(fill => {
  fill.style.opacity = "1";
});
      document.querySelector(".chart-wrapper")?.classList.remove("paused");
      pauseBtn.textContent = "Pause";
    });
  }

// --- Insight Card Listener ---

if (insightCard) {
  insightCard.addEventListener("click", () => {
    if (forcedInsight) return;
    if (insightState !== INSIGHT_STATE.ACTIVE) return;

    currentInsightIndex =
      (currentInsightIndex + 1) % INSIGHTS.length;

    renderInsight(INSIGHTS[currentInsightIndex]);
  });
}

});