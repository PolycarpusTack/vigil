const state = {
  events: [],
  filtered: [],
  page: 1,
  pageSize: 15,
  selectedRaw: null,
  sortKey: "timestamp",
  sortDir: "desc",
  tutorialOn: false,
  views: {},
  bookmarks: {},
  notes: {},
  tail: {
    path: null,
    offset: 0,
    buffer: "",
    timer: null,
  },
};

const fieldGuide = {
  event_id: "Unique identifier for each audit event.",
  timestamp: "When the event occurred (ISO timestamp).",
  actor: "Who performed the action (user, service, system).",
  action: "What happened (operation, category, type).",
  parameters: "Input data related to the action (sanitized).",
  result: "Outcome (status, rows affected, message).",
  performance: "Timing and resource metrics.",
  error: "Captured error details (sanitized).",
  system: "Host and runtime metadata.",
  metadata: "Application context (env, app name).",
  custom: "Additional custom fields.",
};

const $ = (id) => document.getElementById(id);

function getEventKey(evt) {
  return (
    evt.event_id ||
    [evt.timestamp, evt.action, evt.user, evt.status].join("|")
  );
}

function isBookmarked(evt) {
  const key = getEventKey(evt);
  return Boolean(state.bookmarks[key]);
}

function setStatus(text) {
  $("loadStatus").textContent = text;
}

function setEventCount() {
  $("eventCount").textContent = `${state.filtered.length} events`;
}

function refreshUI() {
  setEventCount();
  renderChips();
  renderTable();
  renderSummary();
  renderInsights();
  renderTimeline();
  renderTimelineBySource();
  renderValidation();
  computeIntegrity();
  renderBookmarks();
}

function renderSummary() {
  const panel = $("summaryPanel");
  panel.innerHTML = "";
  const total = state.filtered.length;
  const success = state.filtered.filter((e) => e.status === "SUCCESS").length;
  const failure = state.filtered.filter((e) => e.status === "FAILURE").length;
  const byCategory = {};
  const byUser = {};
  const byAction = {};
  state.filtered.forEach((e) => {
    const key = e.category || "UNSPECIFIED";
    byCategory[key] = (byCategory[key] || 0) + 1;
    const userKey = e.user || "UNKNOWN";
    byUser[userKey] = (byUser[userKey] || 0) + 1;
    const actionKey = e.action || "UNKNOWN";
    byAction[actionKey] = (byAction[actionKey] || 0) + 1;
  });

  const cards = [
    ["Total Events", total],
    ["Success", success],
    ["Failure", failure],
    ["Categories", Object.keys(byCategory).length],
  ];

  cards.forEach(([label, value]) => {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `<h3>${label}</h3><div class="value">${value}</div>`;
    panel.appendChild(card);
  });

  Object.entries(byCategory)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .forEach(([cat, count]) => {
      const card = document.createElement("div");
      card.className = "summary-card";
      card.innerHTML = `<h3>${cat}</h3><div class="value">${count}</div>`;
      panel.appendChild(card);
    });

  const topUser = Object.entries(byUser).sort((a, b) => b[1] - a[1])[0];
  if (topUser) {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `<h3>Top User</h3><div class="value">${topUser[0]} (${topUser[1]})</div>`;
    panel.appendChild(card);
  }

  const topAction = Object.entries(byAction).sort((a, b) => b[1] - a[1])[0];
  if (topAction) {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `<h3>Top Action</h3><div class="value">${topAction[0]} (${topAction[1]})</div>`;
    panel.appendChild(card);
  }
}

function renderInsights() {
  const panel = $("insightsPanel");
  panel.innerHTML = "";
  const total = state.filtered.length || 1;
  const failureCount = state.filtered.filter((e) => e.status === "FAILURE").length;
  const errorCount = state.filtered.filter((e) => e.raw?.error?.occurred).length;
  const failureRate = Math.round((failureCount / total) * 100);
  const errorRate = Math.round((errorCount / total) * 100);

  const cards = [
    ["Failure Rate", `${failureRate}%`],
    ["Error Rate", `${errorRate}%`],
    ["Unique Users", new Set(state.filtered.map((e) => e.user || "UNKNOWN")).size],
    ["Unique Actions", new Set(state.filtered.map((e) => e.action || "UNKNOWN")).size],
  ];

  cards.forEach(([label, value]) => {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `<h3>${label}</h3><div class="value">${value}</div>`;
    panel.appendChild(card);
  });
}

function renderTimeline() {
  const chart = $("timelineChart");
  chart.innerHTML = "";
  if (state.filtered.length === 0) return;
  const buckets = {};
  state.filtered.forEach((e) => {
    const ts = e.timestamp ? new Date(e.timestamp) : null;
    if (!ts || Number.isNaN(ts.getTime())) return;
    const key = ts.toISOString().slice(0, 10);
    buckets[key] = (buckets[key] || 0) + 1;
  });
  const values = Object.values(buckets);
  const max = Math.max(...values, 1);
  Object.values(buckets).forEach((count) => {
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.height = `${Math.max(8, (count / max) * 80)}px`;
    chart.appendChild(bar);
  });
}

function renderTimelineBySource() {
  const chart = $("timelineBySource");
  const legend = $("sourceLegend");
  chart.innerHTML = "";
  legend.innerHTML = "";
  if (state.filtered.length === 0) return;

  const sources = [...new Set(state.filtered.map((e) => e.source || "unknown"))];
  const colors = [
    "#38bdf8",
    "#fb7185",
    "#34d399",
    "#facc15",
    "#a78bfa",
    "#f97316",
  ];
  const colorMap = {};
  sources.forEach((s, i) => {
    colorMap[s] = colors[i % colors.length];
    const tag = document.createElement("div");
    tag.innerHTML = `<span class="swatch" style="background:${colorMap[s]}"></span>${s}`;
    legend.appendChild(tag);
  });

  const buckets = {};
  state.filtered.forEach((e) => {
    const ts = e.timestamp ? new Date(e.timestamp) : null;
    if (!ts || Number.isNaN(ts.getTime())) return;
    const key = ts.toISOString().slice(0, 10);
    buckets[key] = buckets[key] || {};
    const src = e.source || "unknown";
    buckets[key][src] = (buckets[key][src] || 0) + 1;
  });

  const days = Object.keys(buckets).sort();
  chart.classList.add("stack");
  days.forEach((day) => {
    const col = document.createElement("div");
    col.className = "stack-col";
    sources.forEach((s) => {
      const count = buckets[day][s] || 0;
      const bar = document.createElement("div");
      const height = Math.max(4, count * 6);
      bar.className = "bar";
      bar.style.height = `${height}px`;
      bar.style.background = colorMap[s];
      col.appendChild(bar);
    });
    chart.appendChild(col);
  });
}

function renderValidation() {
  const panel = $("validationPanel");
  panel.innerHTML = "";
  if (state.filtered.length === 0) {
    panel.innerHTML = "<li>No data loaded.</li>";
    return;
  }
  let missingTimestamp = 0;
  let missingAction = 0;
  let badTimestamp = 0;
  state.filtered.forEach((e) => {
    if (!e.timestamp) missingTimestamp += 1;
    if (!e.action) missingAction += 1;
    if (e.timestamp) {
      const ts = new Date(e.timestamp);
      if (Number.isNaN(ts.getTime())) badTimestamp += 1;
    }
  });

  const items = [
    `Missing timestamp: ${missingTimestamp}`,
    `Malformed timestamp: ${badTimestamp}`,
    `Missing action: ${missingAction}`,
  ];

  items.forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    panel.appendChild(li);
  });
}

function renderFieldGuide() {
  const container = $("fieldGuide");
  container.innerHTML = "";
  Object.entries(fieldGuide).forEach(([key, desc]) => {
    const div = document.createElement("div");
    div.innerHTML = `<strong>${key}</strong><div>${desc}</div>`;
    container.appendChild(div);
  });
}

function parseJSONL(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function parseJSON(text) {
  const data = JSON.parse(text);
  return Array.isArray(data) ? data : [data];
}

function parseCSV(text) {
  const lines = text.split("\n").filter((l) => l.trim().length > 0);
  if (lines.length === 0) return [];
  const headers = lines[0].split(",").map((h) => h.trim());
  return lines.slice(1).map((line) => {
    const values = line.split(",");
    const row = {};
    headers.forEach((h, i) => {
      row[h] = values[i] ? values[i].trim() : "";
    });
    return row;
  });
}

function normalizeEvent(raw, source = "") {
  const action = raw.action || {};
  const actor = raw.actor || {};
  const result = action.result || raw.result || {};
  return {
    event_id: raw.event_id || raw.id || "",
    timestamp: raw.timestamp || "",
    action: action.operation || raw.action || "",
    category: action.category || raw.category || "",
    user: actor.username || actor.id || raw.user || "",
    status: result.status || raw.status || "",
    source,
    raw,
  };
}

function renderTable() {
  const tbody = $("eventsBody");
  tbody.innerHTML = "";
  const start = (state.page - 1) * state.pageSize;
  const pageItems = state.filtered.slice(start, start + state.pageSize);

  if (state.filtered.length === 0) {
    const row = document.createElement("tr");
    row.className = "empty";
    row.innerHTML = `<td colspan="5">No events match the current filters.</td>`;
    tbody.appendChild(row);
    return;
  }

  pageItems.forEach((evt) => {
    const row = document.createElement("tr");
    if (evt.raw?.error?.occurred) row.classList.add("error-row");
    const star = isBookmarked(evt) ? "★ " : "";
    const source = evt.source ? ` <span class="meta">(${evt.source})</span>` : "";
    row.innerHTML = `
      <td>${evt.timestamp || "-"}</td>
      <td>${star}${evt.action || "-"}${source}</td>
      <td>${evt.category || "-"}</td>
      <td>${evt.user || "-"}</td>
      <td>${renderStatus(evt.status)}</td>
    `;
    row.addEventListener("click", () => {
      renderDetail(evt.raw);
      tbody.querySelectorAll("tr").forEach((r) => r.classList.remove("selected"));
      row.classList.add("selected");
    });
    tbody.appendChild(row);
  });

  updatePageInfo();
}

function renderStatus(status) {
  if (!status) return "-";
  const cls =
    status === "SUCCESS" ? "success" : status === "FAILURE" ? "failure" : "warning";
  return `<span class="pill ${cls}">${status}</span>`;
}

function renderDetail(raw) {
  const detail = $("eventDetail");
  const title = $("detailTitle");
  state.selectedRaw = raw;
  title.textContent = raw.event_id || raw.timestamp || "Event";
  detail.innerHTML = "";

  const sections = [
    ["event_id", raw.event_id],
    ["timestamp", raw.timestamp],
    ["actor", raw.actor],
    ["action", raw.action],
    ["parameters", raw.action?.parameters],
    ["result", raw.action?.result],
    ["performance", raw.performance],
    ["error", raw.error],
    ["system", raw.system],
    ["metadata", raw.metadata],
    ["custom", raw.custom],
  ];

  sections.forEach(([key, value]) => {
    const card = document.createElement("div");
    card.className = "detail-card";
    const desc = fieldGuide[key] || "Additional details.";
    card.innerHTML = `
      <h3>${key}</h3>
      <div class="desc">${desc}</div>
      <pre>${JSON.stringify(value ?? "", null, 2)}</pre>
    `;
    detail.appendChild(card);
  });

  renderNoteBox();
}

function matchSearch(evt, term, regexOn) {
  if (!term) return true;
  const target = [
    evt.event_id,
    evt.action,
    evt.user,
    evt.category,
    evt.status,
  ]
    .filter(Boolean)
    .join(" ");
  if (regexOn) {
    try {
      const re = new RegExp(term, "i");
      return re.test(target);
    } catch (err) {
      setStatus(`Invalid regex: ${err.message}`);
      return true;
    }
  }
  return target.toLowerCase().includes(term);
}

function parseQuery(q) {
  if (!q) return [];
  const tokens = [];
  const regex = /(\w+):(\".*?\"|\S+)/g;
  let match;
  while ((match = regex.exec(q)) !== null) {
    const key = match[1].toLowerCase();
    let value = match[2];
    if (value.startsWith("\"") && value.endsWith("\"")) {
      value = value.slice(1, -1);
    }
    tokens.push({ key, value });
  }
  return tokens;
}

function matchQuery(evt, queryText) {
  if (!queryText) return true;
  const tokens = parseQuery(queryText);
  if (tokens.length === 0) return true;
  return tokens.every((t) => {
    const v = t.value.toLowerCase();
    switch (t.key) {
      case "action":
        return (evt.action || "").toLowerCase().includes(v);
      case "category":
        return (evt.category || "").toLowerCase() === v;
      case "user":
        return (evt.user || "").toLowerCase().includes(v);
      case "status":
        return (evt.status || "").toLowerCase() === v;
      case "error":
        return (t.value === "true") === Boolean(evt.raw?.error?.occurred);
      case "before": {
        const ts = evt.timestamp ? new Date(evt.timestamp) : null;
        return ts ? ts <= new Date(t.value) : false;
      }
      case "after": {
        const ts = evt.timestamp ? new Date(evt.timestamp) : null;
        return ts ? ts >= new Date(t.value) : false;
      }
      case "source":
        return (evt.source || "").toLowerCase().includes(v);
      default:
        return true;
    }
  });
}

function applyFilters() {
  const term = $("searchInput").value.toLowerCase();
  const regexOn = $("regexToggle").value === "true";
  const queryText = $("queryInput").value.trim();
  const category = $("categoryFilter").value;
  const status = $("statusFilter").value;
  const onlyErrors = $("errorFilter").value === "true";
  const dateFrom = $("dateFrom").value;
  const dateTo = $("dateTo").value;

  state.filtered = state.events.filter((evt) => {
    const matchesTerm = matchSearch(evt, term, regexOn);
    const matchesQuery = matchQuery(evt, queryText);

    const matchesCategory = !category || evt.category === category;
    const matchesStatus = !status || evt.status === status;
    const matchesError = !onlyErrors || evt.raw?.error?.occurred === true;
    const ts = evt.timestamp ? new Date(evt.timestamp) : null;
    const afterFrom = !dateFrom || (ts && ts >= new Date(dateFrom));
    const beforeTo =
      !dateTo || (ts && ts <= new Date(dateTo + "T23:59:59"));

    return (
      matchesTerm &&
      matchesQuery &&
      matchesCategory &&
      matchesStatus &&
      matchesError &&
      afterFrom &&
      beforeTo
    );
  });

  state.page = 1;
  sortFiltered();
  renderChips(term, category, status, onlyErrors);
  refreshUI();
}

function handleFiles(files) {
  if (!files || files.length === 0) return;
  const readers = Array.from(files).map(
    (file) =>
      new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve({ file, text: reader.result });
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsText(file);
      })
  );

  Promise.all(readers)
    .then((results) => {
      const merged = [];
      results.forEach(({ file, text }) => {
        let parsed = [];
        if (file.name.endsWith(".jsonl") || file.name.endsWith(".txt")) {
          parsed = parseJSONL(text);
        } else if (file.name.endsWith(".json")) {
          parsed = parseJSON(text);
        } else if (file.name.endsWith(".csv")) {
          parsed = parseCSV(text);
        } else {
          throw new Error(`Unsupported file type: ${file.name}`);
        }
        parsed.forEach((raw) => merged.push(normalizeEvent(raw, file.name)));
      });

      state.events = merged;
      state.filtered = [...state.events];
      sortFiltered();
      state.page = 1;
      setStatus(`Loaded ${state.events.length} events from ${files.length} file(s)`);
      refreshUI();
    })
    .catch((err) => {
      setStatus(`Failed to parse file: ${err.message}`);
    });
}

function clearData() {
  state.events = [];
  state.filtered = [];
  state.page = 1;
  stopTail();
  refreshUI();
  $("eventDetail").innerHTML = `<div class="placeholder">No event selected.</div>`;
  $("detailTitle").textContent = "Select an event";
  state.selectedRaw = null;
  setStatus("No file loaded.");
}

function toggleTutorial() {
  state.tutorialOn = !state.tutorialOn;
  const panel = $("tutorialPanel");
  const btn = $("tutorialToggle");
  if (state.tutorialOn) {
    panel.classList.add("active");
    btn.textContent = "Tutorial: On";
  } else {
    panel.classList.remove("active");
    btn.textContent = "Tutorial: Off";
  }
}

function renderChips(
  term = "",
  category = "",
  status = "",
  onlyErrors = false
) {
  const chips = $("activeChips");
  chips.innerHTML = "";
  const items = [];
  if (term) items.push(`Search: ${term}`);
  const regexOn = $("regexToggle").value === "true";
  if (regexOn && term) items.push("Regex: on");
  const queryText = $("queryInput").value.trim();
  if (queryText) items.push(`Query: ${queryText}`);
  if (category) items.push(`Category: ${category}`);
  if (status) items.push(`Status: ${status}`);
  if (onlyErrors) items.push("Errors Only");
  const dateFrom = $("dateFrom").value;
  const dateTo = $("dateTo").value;
  if (dateFrom) items.push(`From: ${dateFrom}`);
  if (dateTo) items.push(`To: ${dateTo}`);
  if (state.sortKey) {
    items.push(`Sort: ${state.sortKey} (${state.sortDir})`);
  }
  if (items.length === 0) return;
  items.forEach((text) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = text;
    chips.appendChild(chip);
  });
}

function resetFilters() {
  $("searchInput").value = "";
  $("regexToggle").value = "false";
  $("queryInput").value = "";
  $("categoryFilter").value = "";
  $("statusFilter").value = "";
  $("errorFilter").value = "";
  $("dateFrom").value = "";
  $("dateTo").value = "";
  applyFilters();
}

function updatePageInfo() {
  const pages = Math.max(1, Math.ceil(state.filtered.length / state.pageSize));
  $("pageInfo").textContent = `Page ${state.page} of ${pages}`;
  $("prevPage").disabled = state.page <= 1;
  $("nextPage").disabled = state.page >= pages;
}

function nextPage() {
  const pages = Math.max(1, Math.ceil(state.filtered.length / state.pageSize));
  if (state.page < pages) {
    state.page += 1;
    renderTable();
  }
}

function prevPage() {
  if (state.page > 1) {
    state.page -= 1;
    renderTable();
  }
}

function copyEventJson() {
  if (!state.selectedRaw) return;
  const text = JSON.stringify(state.selectedRaw, null, 2);
  navigator.clipboard.writeText(text).catch(() => {});
}

function renderNoteBox() {
  const box = $("noteBox");
  if (!state.selectedRaw) {
    box.innerHTML = "";
    return;
  }
  const evt = normalizeEvent(state.selectedRaw);
  const key = getEventKey(evt);
  const note = state.notes[key] || "";
  box.innerHTML = `
    <label class="field">
      <span>Note</span>
      <textarea id="noteInput" placeholder="Add a note about this event...">${note}</textarea>
    </label>
  `;
  const input = $("noteInput");
  input.addEventListener("input", () => {
    state.notes[key] = input.value;
    saveNotes();
    renderBookmarks();
  });
}

function toggleBookmark() {
  if (!state.selectedRaw) return;
  const evt = normalizeEvent(state.selectedRaw);
  const key = getEventKey(evt);
  if (state.bookmarks[key]) {
    delete state.bookmarks[key];
  } else {
    state.bookmarks[key] = {
      event: evt,
      note: state.notes[key] || "",
      saved_at: new Date().toISOString(),
    };
  }
  saveBookmarks();
  renderBookmarks();
  renderTable();
}

function loadSample() {
  fetch("sample_logs.jsonl")
    .then((res) => res.text())
    .then((text) => {
      const parsed = parseJSONL(text);
      state.events = parsed.map((raw) => normalizeEvent(raw, "sample_logs.jsonl"));
      state.filtered = [...state.events];
      state.page = 1;
      sortFiltered();
      setStatus(`Loaded ${state.events.length} events from sample_logs.jsonl`);
      refreshUI();
    })
    .catch((err) => {
      setStatus(`Failed to load sample: ${err.message}`);
    });
}

async function selectTailFile() {
  if (!window.__TAURI__) {
    setStatus("Live tail is available in Tauri desktop mode.");
    return;
  }
  const { dialog } = window.__TAURI__;
  const path = await dialog.open({
    filters: [{ name: "Logs", extensions: ["jsonl", "txt"] }],
  });
  if (path) {
    state.tail.path = path;
    state.tail.offset = 0;
    state.tail.buffer = "";
    $("tailStatus").textContent = `Tail: ready (${path})`;
  }
}

async function tailTick() {
  if (!window.__TAURI__ || !state.tail.path) return;
  const { invoke } = window.__TAURI__;
  const result = await invoke("read_tail_chunk", {
    path: state.tail.path,
    offset: state.tail.offset,
  });
  const chunk = result[0];
  const newOffset = result[1];
  if (!chunk) return;
  state.tail.offset = newOffset;
  const combined = state.tail.buffer + chunk;
  const lines = combined.split("\n");
  state.tail.buffer = lines.pop() || "";
  const newEvents = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      const raw = JSON.parse(trimmed);
      newEvents.push(normalizeEvent(raw, state.tail.path));
    } catch {
      // ignore malformed lines
    }
  }
  if (newEvents.length > 0) {
    state.events = state.events.concat(newEvents);
    state.filtered = [...state.events];
    sortFiltered();
    refreshUI();
  }
}

function startTail() {
  if (!window.__TAURI__) {
    setStatus("Live tail is available in Tauri desktop mode.");
    return;
  }
  if (!state.tail.path) {
    setStatus("Select a file to tail first.");
    return;
  }
  const interval = parseInt($("tailInterval").value, 10) || 2000;
  if (state.tail.timer) clearInterval(state.tail.timer);
  state.tail.timer = setInterval(tailTick, interval);
  $("tailStatus").textContent = "Tail: running";
}

function stopTail() {
  if (state.tail.timer) {
    clearInterval(state.tail.timer);
    state.tail.timer = null;
  }
  $("tailStatus").textContent = "Tail: stopped";
}

function toggleTail() {
  if (state.tail.timer) stopTail();
  else startTail();
}

function applyPreset(type) {
  if (type === "failures") {
    $("queryInput").value = "status:FAILURE";
  } else if (type === "logins") {
    $("queryInput").value = "action:login";
  } else if (type === "errors") {
    $("queryInput").value = "error:true";
  }
  applyFilters();
}

function loadViews() {
  try {
    const raw = localStorage.getItem("audit_views");
    state.views = raw ? JSON.parse(raw) : {};
  } catch {
    state.views = {};
  }
  renderViews();
}

function saveViews() {
  localStorage.setItem("audit_views", JSON.stringify(state.views));
}

function loadBookmarks() {
  try {
    const raw = localStorage.getItem("audit_bookmarks");
    state.bookmarks = raw ? JSON.parse(raw) : {};
  } catch {
    state.bookmarks = {};
  }
  renderBookmarks();
}

function saveBookmarks() {
  localStorage.setItem("audit_bookmarks", JSON.stringify(state.bookmarks));
}

function loadNotes() {
  try {
    const raw = localStorage.getItem("audit_notes");
    state.notes = raw ? JSON.parse(raw) : {};
  } catch {
    state.notes = {};
  }
}

function saveNotes() {
  localStorage.setItem("audit_notes", JSON.stringify(state.notes));
}

function renderBookmarks() {
  const list = $("bookmarkList");
  list.innerHTML = "";
  const items = Object.values(state.bookmarks);
  if (items.length === 0) {
    list.innerHTML = "<div class='meta'>No bookmarks yet.</div>";
    return;
  }
  items
    .sort((a, b) => (b.saved_at || "").localeCompare(a.saved_at || ""))
    .forEach((b) => {
      const item = document.createElement("div");
      item.className = "bookmark-item";
      item.innerHTML = `
        <div><strong>${b.event.action || "Event"}</strong> <span class="meta">${b.event.timestamp || ""}</span></div>
        <div class="meta">${b.note || ""}</div>
      `;
      const actions = document.createElement("div");
      actions.className = "actions";
      const openBtn = document.createElement("button");
      openBtn.className = "btn ghost";
      openBtn.textContent = "Open";
      openBtn.addEventListener("click", () => {
        renderDetail(b.event.raw || b.event);
      });
      const delBtn = document.createElement("button");
      delBtn.className = "btn ghost";
      delBtn.textContent = "Remove";
      delBtn.addEventListener("click", () => {
        const key = getEventKey(b.event);
        delete state.bookmarks[key];
        saveBookmarks();
        renderBookmarks();
        renderTable();
      });
      actions.appendChild(openBtn);
      actions.appendChild(delBtn);
      item.appendChild(actions);
      list.appendChild(item);
    });
}

function renderViews() {
  const list = $("viewList");
  list.innerHTML = "";
  const names = Object.keys(state.views);
  if (names.length === 0) {
    list.innerHTML = "<div class='meta'>No saved views yet.</div>";
    return;
  }
  names.forEach((name) => {
    const item = document.createElement("div");
    item.className = "view-item";
    item.innerHTML = `<span>${name}</span>`;
    const actions = document.createElement("div");
    const loadBtn = document.createElement("button");
    loadBtn.className = "btn ghost";
    loadBtn.textContent = "Load";
    loadBtn.addEventListener("click", () => applyView(name));
    const delBtn = document.createElement("button");
    delBtn.className = "btn ghost";
    delBtn.textContent = "Delete";
    delBtn.addEventListener("click", () => deleteView(name));
    actions.appendChild(loadBtn);
    actions.appendChild(delBtn);
    item.appendChild(actions);
    list.appendChild(item);
  });
}

function saveView() {
  const name = $("viewName").value.trim();
  if (!name) return;
  state.views[name] = {
    search: $("searchInput").value,
    regex: $("regexToggle").value,
    query: $("queryInput").value,
    category: $("categoryFilter").value,
    status: $("statusFilter").value,
    errorOnly: $("errorFilter").value,
    dateFrom: $("dateFrom").value,
    dateTo: $("dateTo").value,
    sortKey: state.sortKey,
    sortDir: state.sortDir,
  };
  saveViews();
  renderViews();
}

function applyView(name) {
  const v = state.views[name];
  if (!v) return;
  $("searchInput").value = v.search || "";
  $("regexToggle").value = v.regex || "false";
  $("queryInput").value = v.query || "";
  $("categoryFilter").value = v.category || "";
  $("statusFilter").value = v.status || "";
  $("errorFilter").value = v.errorOnly || "";
  $("dateFrom").value = v.dateFrom || "";
  $("dateTo").value = v.dateTo || "";
  state.sortKey = v.sortKey || "timestamp";
  state.sortDir = v.sortDir || "desc";
  applyFilters();
}

function deleteView(name) {
  delete state.views[name];
  saveViews();
  renderViews();
}

function toggleHelp(force) {
  const modal = $("helpModal");
  if (force === true) modal.classList.add("active");
  else if (force === false) modal.classList.remove("active");
  else modal.classList.toggle("active");
}

function sortFiltered() {
  const { sortKey, sortDir } = state;
  state.filtered.sort((a, b) => {
    const av = (a[sortKey] || "").toString();
    const bv = (b[sortKey] || "").toString();
    if (sortKey === "timestamp") {
      const ad = new Date(av).getTime() || 0;
      const bd = new Date(bv).getTime() || 0;
      return sortDir === "asc" ? ad - bd : bd - ad;
    }
    if (av < bv) return sortDir === "asc" ? -1 : 1;
    if (av > bv) return sortDir === "asc" ? 1 : -1;
    return 0;
  });
}

function stableStringify(obj) {
  if (obj === null || typeof obj !== "object") return JSON.stringify(obj);
  if (Array.isArray(obj)) {
    return "[" + obj.map(stableStringify).join(",") + "]";
  }
  const keys = Object.keys(obj).sort();
  const entries = keys.map((k) => `"${k}":${stableStringify(obj[k])}`);
  return "{" + entries.join(",") + "}";
}

function isCryptoAvailable() {
  return Boolean(globalThis.crypto && crypto.subtle);
}

async function sha256Hex(input) {
  if (!globalThis.crypto || !crypto.subtle) {
    return fnv1aHex(input);
  }
  const data = new TextEncoder().encode(input);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function fnv1aHex(input) {
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i);
    hash = (hash * 0x01000193) >>> 0;
  }
  return hash.toString(16).padStart(8, "0");
}

async function computeIntegrity() {
  const panel = $("integrityPanel");
  const list = $("integrityList");
  panel.innerHTML = "";
  list.innerHTML = "";
  const data = state.filtered.length ? state.filtered : state.events;
  if (data.length === 0) {
    panel.innerHTML = "<div class='meta'>No data loaded.</div>";
    return;
  }
  const hashMode = isCryptoAvailable() ? "SHA-256" : "FNV-1a (fallback)";

  const ordered = [...data].sort((a, b) => {
    const ad = new Date(a.timestamp || 0).getTime() || 0;
    const bd = new Date(b.timestamp || 0).getTime() || 0;
    return ad - bd;
  });

  let prev = "0";
  let mismatches = 0;
  const rows = [];
  for (const evt of ordered) {
    const payload = stableStringify({ prev, event: evt.raw });
    const hash = await sha256Hex(payload);
    evt.computed_hash = hash;
    const prevMismatch = evt.raw?.prev_hash && evt.raw.prev_hash !== prev;
    const hashMismatch = evt.raw?.hash && evt.raw.hash !== hash;
    if (prevMismatch || hashMismatch) mismatches += 1;
    rows.push({
      ts: evt.timestamp || "",
      prev: prev.slice(0, 12),
      hash: hash.slice(0, 12),
      ok: !(prevMismatch || hashMismatch),
    });
    prev = hash;
  }

  const cards = [
    ["Chain Hash", prev.slice(0, 16) + "..."],
    ["Events", ordered.length],
    ["Mismatches", mismatches],
    [
      "Hash Mode <span class=\"info\" title=\"If SHA-256 is unavailable, the app uses a non-cryptographic fallback for display-only integrity.\"><svg viewBox=\"0 0 24 24\" class=\"info-icon\" aria-hidden=\"true\"><circle cx=\"12\" cy=\"12\" r=\"10\" stroke=\"currentColor\" stroke-width=\"2\" fill=\"none\" /><line x1=\"12\" y1=\"10\" x2=\"12\" y2=\"16\" stroke=\"currentColor\" stroke-width=\"2\" /><circle cx=\"12\" cy=\"7\" r=\"1\" fill=\"currentColor\" /></svg></span>",
      hashMode,
    ],
  ];
  cards.forEach(([label, value]) => {
    const card = document.createElement("div");
    card.className = "summary-card";
    card.innerHTML = `<h3>${label}</h3><div class="value">${value}</div>`;
    panel.appendChild(card);
  });

  rows.slice(-100).forEach((r) => {
    const row = document.createElement("div");
    row.className = "integrity-row" + (r.ok ? "" : " bad");
    row.innerHTML = `<div>${r.ts || "-"}</div><div>${r.prev}</div><div>${r.hash}</div><div>${r.ok ? "OK" : "BAD"}</div>`;
    list.appendChild(row);
  });
}

function setupSorting() {
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.getAttribute("data-sort");
      if (state.sortKey === key) {
        state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
      } else {
        state.sortKey = key;
        state.sortDir = "asc";
      }
      document
        .querySelectorAll("th[data-sort]")
        .forEach((el) => el.classList.remove("sorted", "asc"));
      th.classList.add("sorted");
      if (state.sortDir === "asc") th.classList.add("asc");
      sortFiltered();
      renderTable();
    });
  });
}

function buildReportHtml() {
  const total = state.filtered.length;
  const success = state.filtered.filter((e) => e.status === "SUCCESS").length;
  const failure = state.filtered.filter((e) => e.status === "FAILURE").length;
  const byCategory = {};
  const byUser = {};
  const byAction = {};
  state.filtered.forEach((e) => {
    const cat = e.category || "UNSPECIFIED";
    byCategory[cat] = (byCategory[cat] || 0) + 1;
    const user = e.user || "UNKNOWN";
    byUser[user] = (byUser[user] || 0) + 1;
    const action = e.action || "UNKNOWN";
    byAction[action] = (byAction[action] || 0) + 1;
  });

  const topCats = Object.entries(byCategory)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  const topUsers = Object.entries(byUser)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  const topActions = Object.entries(byAction)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  const rows = state.filtered.slice(0, 200).map((e) => ({
    timestamp: e.timestamp,
    action: e.action,
    category: e.category,
    user: e.user,
    status: e.status,
  }));

  const tableRows = rows
    .map(
      (r) =>
        `<tr><td>${r.timestamp || "-"}</td><td>${r.action || "-"}</td><td>${r.category || "-"}</td><td>${r.user || "-"}</td><td>${r.status || "-"}</td></tr>`
    )
    .join("");

  const list = (items) =>
    items.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("");

  return `
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Audit Report</title>
  <style>
    body { font-family: "Segoe UI", Arial, sans-serif; padding: 24px; color: #0b1220; }
    h1 { margin-bottom: 6px; }
    .meta { color: #475569; margin-bottom: 20px; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 10px; margin-bottom: 20px; }
    .card { border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; }
    .card h3 { margin: 0 0 6px; font-size: 12px; color: #64748b; }
    .card .value { font-size: 18px; font-weight: 700; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #e2e8f0; font-size: 12px; }
    .section { margin-bottom: 18px; }
  </style>
</head>
<body>
  <h1>Audit Report</h1>
  <div class="meta">Generated ${new Date().toISOString()}</div>

  <div class="grid">
    <div class="card"><h3>Total Events</h3><div class="value">${total}</div></div>
    <div class="card"><h3>Success</h3><div class="value">${success}</div></div>
    <div class="card"><h3>Failure</h3><div class="value">${failure}</div></div>
    <div class="card"><h3>Categories</h3><div class="value">${Object.keys(byCategory).length}</div></div>
  </div>

  <div class="section">
    <h2>Top Categories</h2>
    <table><tbody>${list(topCats)}</tbody></table>
  </div>

  <div class="section">
    <h2>Top Users</h2>
    <table><tbody>${list(topUsers)}</tbody></table>
  </div>

  <div class="section">
    <h2>Top Actions</h2>
    <table><tbody>${list(topActions)}</tbody></table>
  </div>

  <div class="section">
    <h2>Events (first 200)</h2>
    <table>
      <thead><tr><th>Timestamp</th><th>Action</th><th>Category</th><th>User</th><th>Status</th></tr></thead>
      <tbody>${tableRows}</tbody>
    </table>
  </div>
</body>
</html>`;
}

function printReport() {
  const printWindow = window.open("", "print");
  if (!printWindow) return;
  printWindow.document.write(buildReportHtml());
  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
}

function downloadFile(name, content, type) {
  const blob = new Blob([content], { type });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = name;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function exportJson() {
  const payload = state.filtered.map((e) => e.raw);
  downloadFile("audit_export.json", JSON.stringify(payload, null, 2), "application/json");
}

function exportCsv() {
  const rows = state.filtered.map((e) => ({
    event_id: e.event_id,
    timestamp: e.timestamp,
    action: e.action,
    category: e.category,
    user: e.user,
    status: e.status,
  }));
  const headers = Object.keys(rows[0] || {});
  const lines = [headers.join(",")].concat(
    rows.map((r) => headers.map((h) => `"${(r[h] || "").toString().replace(/\"/g, '""')}"`).join(","))
  );
  downloadFile("audit_export.csv", lines.join("\n"), "text/csv");
}

function exportReportHtml() {
  const html = buildReportHtml();
  downloadFile("audit_report.html", html, "text/html");
}

async function exportPdf() {
  if (!window.__TAURI__) {
    alert("PDF export is available in the Tauri desktop app.");
    return;
  }
  const { dialog, invoke } = window.__TAURI__;
  const path = await dialog.save({
    defaultPath: "audit_report.pdf",
    filters: [{ name: "PDF", extensions: ["pdf"] }],
  });
  if (!path) return;

  const byCategory = {};
  const byUser = {};
  const byAction = {};
  state.filtered.forEach((e) => {
    const cat = e.category || "UNSPECIFIED";
    byCategory[cat] = (byCategory[cat] || 0) + 1;
    const user = e.user || "UNKNOWN";
    byUser[user] = (byUser[user] || 0) + 1;
    const action = e.action || "UNKNOWN";
    byAction[action] = (byAction[action] || 0) + 1;
  });

  const payload = {
    total: state.filtered.length,
    success: state.filtered.filter((e) => e.status === "SUCCESS").length,
    failure: state.filtered.filter((e) => e.status === "FAILURE").length,
    top_categories: Object.entries(byCategory),
    top_users: Object.entries(byUser),
    top_actions: Object.entries(byAction),
    rows: state.filtered.slice(0, 100).map((e) => ({
      timestamp: e.timestamp || "",
      action: e.action || "",
      category: e.category || "",
      user: e.user || "",
      status: e.status || "",
    })),
  };

  await invoke("generate_pdf_report", { path, payload });
  alert("PDF report saved.");
}

function generateWizardYaml() {
  const appName = $("wizAppName").value || "my_app";
  const env = $("wizEnv").value || "production";
  const dir = $("wizDir").value || "./logs/audit";
  const fmt = $("wizFormat").value || "json";
  const sanitize = $("wizSanitize").value || "true";
  const yaml = [
    "audit_framework:",
    "  core:",
    `    enabled: true`,
    `    application_name: \"${appName}\"`,
    `    environment: \"${env}\"`,
    "",
    "  storage:",
    "    backends:",
    "      - type: file",
    "        enabled: true",
    `        directory: ${dir}`,
    `        format: ${fmt}`,
    "",
    "  processing:",
    "    sanitization:",
    `      enabled: ${sanitize}`,
    "",
  ].join("\n");

  $("wizardOutput").textContent = yaml;
}

function downloadWizardYaml() {
  const content = $("wizardOutput").textContent || "";
  if (!content.trim()) {
    generateWizardYaml();
  }
  downloadFile("audit_config.yaml", $("wizardOutput").textContent, "text/yaml");
}

document.addEventListener("DOMContentLoaded", () => {
  renderFieldGuide();
  $("fileInput").addEventListener("change", (e) => handleFiles(e.target.files));
  $("applyFilters").addEventListener("click", applyFilters);
  $("clearData").addEventListener("click", clearData);
  $("resetFilters").addEventListener("click", resetFilters);
  $("tutorialToggle").addEventListener("click", toggleTutorial);
  $("exportJson").addEventListener("click", exportJson);
  $("exportCsv").addEventListener("click", exportCsv);
  $("exportReport").addEventListener("click", exportReportHtml);
  $("exportPdf").addEventListener("click", exportPdf);
  $("wizardGenerate").addEventListener("click", generateWizardYaml);
  $("wizardDownload").addEventListener("click", downloadWizardYaml);
  $("prevPage").addEventListener("click", prevPage);
  $("nextPage").addEventListener("click", nextPage);
  $("copyEvent").addEventListener("click", copyEventJson);
  $("loadSample").addEventListener("click", loadSample);
  $("printReport").addEventListener("click", printReport);
  $("saveView").addEventListener("click", saveView);
  $("helpToggle").addEventListener("click", () => toggleHelp());
  $("helpClose").addEventListener("click", () => toggleHelp(false));
  $("bookmarkEvent").addEventListener("click", toggleBookmark);
  $("noteEvent").addEventListener("click", renderNoteBox);
  $("tailSelect").addEventListener("click", selectTailFile);
  $("tailToggle").addEventListener("click", toggleTail);
  $("presetFailures").addEventListener("click", () => applyPreset("failures"));
  $("presetLogins").addEventListener("click", () => applyPreset("logins"));
  $("presetErrors").addEventListener("click", () => applyPreset("errors"));
  $("searchInput").addEventListener("keyup", (e) => {
    if (e.key === "Enter") applyFilters();
  });
  $("queryInput").addEventListener("keyup", (e) => {
    if (e.key === "Enter") applyFilters();
  });
  $("regexToggle").addEventListener("change", applyFilters);
  $("dateFrom").addEventListener("change", applyFilters);
  $("dateTo").addEventListener("change", applyFilters);
  setupSorting();
  setEventCount();
  renderSummary();
  renderInsights();
  renderTimeline();
  renderValidation();
  loadViews();
  loadNotes();
  loadBookmarks();
  generateWizardYaml();

  document.addEventListener("keydown", (e) => {
    if (e.key === "/") {
      e.preventDefault();
      $("searchInput").focus();
    } else if (e.key === "f") {
      applyPreset("failures");
    } else if (e.key === "l") {
      applyPreset("logins");
    } else if (e.key === "e") {
      applyPreset("errors");
    } else if (e.key === "n") {
      nextPage();
    } else if (e.key === "p") {
      prevPage();
    } else if (e.key === "?") {
      toggleHelp();
    } else if (e.key === "Escape") {
      toggleHelp(false);
    }
  });
});
