/**
 * SCRIPT.JS - Dashboard & Logic
 * Organized for maintainability
 */

document.addEventListener("DOMContentLoaded", () => {
  loadSessionHistory();
  /* ==========================================================================
     1. GLOBAL STATE & VARIABLES
     ========================================================================== */
  let attentionChart;
  let attentionData = [];
  let timeLabels = [];
  let heatmapData = [];

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
const insightTitle = document.getElementById("insightTitle");
const insightValue = document.getElementById("insightValue");
const insightSub = document.getElementById("insightSub");

const insightLabel = document.getElementById("insightLabel");
const insightAvg = document.getElementById("insightAvg");
const insightStability = document.getElementById("insightStability");
const insightRisk = document.getElementById("insightRisk");

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
          label: "Attentiveness (%)",
          data: attentionData,
          borderWidth: 2,
          tension: 0.35,
          fill: false
        }]
      },
      options: {
        animation: false,
        responsive: true,
        scales: {
          y: { min: 0, max: 100, title: { display: true, text: "Attentiveness (%)" } },
          x: { title: { display: true, text: "Time (mm:ss)" } }
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
  if (!attentionData.length) return null;

  const avg =
    attentionData.reduce((a, b) => a + b, 0) / attentionData.length;

  const volatility =
    Math.sqrt(
      attentionData
        .map(v => Math.pow(v - avg, 2))
        .reduce((a, b) => a + b, 0) / attentionData.length
    );

  let health = Math.round(avg - volatility / 2);
  health = Math.max(0, Math.min(100, health));

  return { health, volatility };
}

function computeTimeBelowThreshold(threshold = 40) {
  return attentionData.filter(v => v < threshold).length * 5; // seconds
}

function renderInsight(type) {
  if (type === "health") {
  const data = computeSessionHealth();
  if (!data) return;

  const avg =
    attentionData.reduce((a, b) => a + b, 0) / attentionData.length;

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

  attentionData.length = 0;
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

    timeLabels.push(`${min}:${sec}`);
    attentionData.push(value);
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
  if (chartInterval) {
    clearInterval(chartInterval);
    chartInterval = null;
  }

  sessionActive = false;
  sessionPaused = false;
  pauseBtn.textContent = "Pause";

  // 🔥 HARD RESET UI STATE
  attentionData.length = 0;
  timeLabels.length = 0;
  heatmapData.length = 0;

  attentionChart.update();
  renderHeatmap([]);

  document.getElementById("avgEng").textContent = "—";
  document.getElementById("peakEng").textContent = "—";

  try {
    await fetch("http://127.0.0.1:5001/session/stop", { method: "POST" });
    loadSessionHistory();
  } catch (e) {
    console.error("Failed to stop session", e);
  }
}

function updateButtonStates() {
  startBtn.disabled = sessionActive;
  pauseBtn.disabled = !sessionActive;
  stopBtn.disabled = !sessionActive;
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
     6. EVENT LISTENERS & INITIALIZATION
     ========================================================================== */

  // --- Initialize Components ---
  initAttentionChart();
  renderHeatmap([]);
  renderInsight("health");
  updateDateTime();
  setInterval(updateDateTime, 1000);
  
  // --- Timetable Logic ---
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

  // HIstory Tab Modal Logic

  // --- History Modal Logic (FIXED) ---
const historyModal = document.getElementById("historyModal");
const openHistoryCard = document.getElementById("openHistoryCard");
const openHistoryArrow = document.getElementById("openHistoryModal");
const closeHistory = document.getElementById("closeHistoryModal");

if (historyModal && closeHistory) {

  const open = () => historyModal.classList.add("active");

  openHistoryCard?.addEventListener("click", open);
  openHistoryArrow?.addEventListener("click", (e) => {
    e.stopPropagation(); // prevent double fire
    open();
  });

  closeHistory.addEventListener("click", () => {
    historyModal.classList.remove("active");
  });

  historyModal.addEventListener("click", (e) => {
    if (e.target === historyModal) {
      historyModal.classList.remove("active");
    }
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
    startChartPlotting();

  } catch (e) {
    console.error("Failed to start session", e);
  }
});

    pauseBtn.addEventListener("click", () => {
      if (!sessionActive) return;
      if (!sessionPaused) {
        pauseChartPlotting();
        pauseBtn.textContent = "Resume";
      } else {
        resumeChartPlotting();
        pauseBtn.textContent = "Pause";
      }
    });

    stopBtn.addEventListener("click", () => {
      if (!sessionActive) return;
      stopChartPlotting();
      pauseBtn.textContent = "Pause";
    });
  }
});

async function loadSessionHistory() {
  try {
    const res = await fetch("http://localhost:5001/sessions");
    const sessions = await res.json();

    if (!sessions || !sessions.length) return;

    // ✅ Modal lists
    renderAllSessions(sessions);

  } catch (err) {
    console.error("Failed to load sessions", err);
  }
}

function renderAllSessions(sessions) {
  const recentContainer = document.getElementById("recentSessionsList");
  const pastContainer = document.getElementById("pastSessionsList");

  recentContainer.innerHTML = "";
  pastContainer.innerHTML = "";

  const recent = sessions.slice(0, 5);
  const past = sessions.slice(5);

  recent.forEach(s => recentContainer.appendChild(createSessionCard(s)));
  past.forEach(s => pastContainer.appendChild(createSessionCard(s)));
}

function createSessionCard(s) {
  const card = document.createElement("div");
  card.className = "session-card";

  card.innerHTML = `
    <b>${s[3]}</b>
    <div class="session-meta">${new Date(s[1]).toLocaleString()}</div>
    <div class="session-stats">
      <span>Avg: ${Math.round(s[4])}%</span>
      <span>Peak: ${Math.round(s[5])}%</span>
    </div>
  `;

  return card;
}

insightCard?.addEventListener("click", () => {
  if (forcedInsight) return;

  currentInsightIndex =
    (currentInsightIndex + 1) % INSIGHTS.length;

  renderInsight(INSIGHTS[currentInsightIndex]);
});