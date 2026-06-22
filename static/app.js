"use strict";

const $ = (sel) => document.querySelector(sel);
const state = { cvs: [], jobs: [], apps: [], activeCv: null, activeJob: null };

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

function busy(btn, on) {
  if (btn) btn.disabled = on;
}

// ---- Health -----------------------------------------------------------

async function loadHealth() {
  try {
    const h = await api("/api/health");
    const key = h.anthropic_key_configured ? "key ✓" : "NO API KEY ✗";
    $("#health").textContent = `model: ${h.model} · ${key}`;
  } catch (e) {
    $("#health").textContent = "backend unreachable";
  }
}

// ---- CVs --------------------------------------------------------------

async function loadCvs() {
  state.cvs = await api("/api/cv");
  const sel = $("#cvSelect");
  sel.innerHTML = "";
  for (const cv of state.cvs) {
    const opt = document.createElement("option");
    opt.value = cv.id;
    opt.textContent = `${cv.name} (#${cv.id})`;
    sel.appendChild(opt);
  }
  if (state.cvs.length) state.activeCv = Number(sel.value);
}

$("#cvSelect").addEventListener("change", (e) => {
  state.activeCv = Number(e.target.value);
});

$("#cvUploadBtn").addEventListener("click", async (e) => {
  const file = $("#cvFile").files[0];
  if (!file) return alert("Choose a file first.");
  busy(e.target, true);
  $("#cvStatus").textContent = "Uploading & analyzing…";
  try {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/cv/upload", { method: "POST", body: fd });
    if (!res.ok) throw new Error((await res.json()).detail);
    await loadCvs();
    $("#cvStatus").textContent = "CV analyzed and saved.";
  } catch (err) {
    $("#cvStatus").textContent = "Error: " + err.message;
  } finally {
    busy(e.target, false);
  }
});

$("#cvTextBtn").addEventListener("click", async (e) => {
  const name = $("#cvName").value.trim() || "My CV";
  const raw_text = $("#cvText").value.trim();
  if (!raw_text) return alert("Paste some CV text first.");
  busy(e.target, true);
  $("#cvStatus").textContent = "Analyzing…";
  try {
    await api("/api/cv", {
      method: "POST",
      body: JSON.stringify({ name, raw_text }),
    });
    await loadCvs();
    $("#cvStatus").textContent = "CV analyzed and saved.";
  } catch (err) {
    $("#cvStatus").textContent = "Error: " + err.message;
  } finally {
    busy(e.target, false);
  }
});

// ---- Jobs -------------------------------------------------------------

async function loadJobs() {
  state.jobs = await api("/api/jobs");
  const list = $("#jobList");
  list.innerHTML = "";
  for (const job of state.jobs) {
    const li = document.createElement("li");
    const left = document.createElement("div");
    left.innerHTML = `<strong>${esc(job.title)}</strong><div class="meta">${esc(
      job.company || job.source
    )}${job.location ? " · " + esc(job.location) : ""}</div>`;
    const right = document.createElement("div");
    const btn = document.createElement("button");
    btn.textContent = "Score & draft";
    btn.className = "secondary";
    btn.addEventListener("click", () => createApplication(job.id, btn));
    right.appendChild(btn);
    li.append(left, right);
    list.appendChild(li);
  }
}

$("#importBtn").addEventListener("click", async (e) => {
  const source = $("#importSource").value;
  const board = $("#importBoard").value.trim();
  const query = $("#importQuery").value.trim() || null;
  if (!board) return alert("Enter a board token, e.g. 'stripe'.");
  busy(e.target, true);
  try {
    await api("/api/jobs/import", {
      method: "POST",
      body: JSON.stringify({ source, board, query, limit: 25 }),
    });
    await loadJobs();
  } catch (err) {
    alert("Import failed: " + err.message);
  } finally {
    busy(e.target, false);
  }
});

$("#jobPasteBtn").addEventListener("click", async (e) => {
  const title = $("#jobTitle").value.trim();
  const description = $("#jobDesc").value.trim();
  if (!title || !description)
    return alert("Title and description are required.");
  busy(e.target, true);
  try {
    await api("/api/jobs", {
      method: "POST",
      body: JSON.stringify({
        title,
        company: $("#jobCompany").value.trim() || null,
        description,
      }),
    });
    $("#jobTitle").value = $("#jobCompany").value = $("#jobDesc").value = "";
    await loadJobs();
  } catch (err) {
    alert("Save failed: " + err.message);
  } finally {
    busy(e.target, false);
  }
});

// ---- Applications -----------------------------------------------------

async function createApplication(jobId, btn) {
  if (!state.activeCv) return alert("Upload or select a CV first.");
  busy(btn, true);
  try {
    await api("/api/applications", {
      method: "POST",
      body: JSON.stringify({ cv_id: state.activeCv, job_id: jobId }),
    });
    await loadApps();
  } catch (err) {
    alert("Scoring failed: " + err.message);
  } finally {
    busy(btn, false);
  }
}

function scoreClass(s) {
  if (s == null) return "";
  if (s >= 70) return "score-high";
  if (s >= 45) return "score-mid";
  return "score-low";
}

async function loadApps() {
  state.apps = await api("/api/applications");
  const tbody = $("#appTable tbody");
  tbody.innerHTML = "";
  const jobById = Object.fromEntries(state.jobs.map((j) => [j.id, j]));
  for (const app of state.apps) {
    const job = jobById[app.job_id] || { title: "Job #" + app.job_id };
    const tr = document.createElement("tr");

    const tdJob = document.createElement("td");
    tdJob.innerHTML = `<strong>${esc(job.title)}</strong><div class="meta">${esc(
      job.company || ""
    )}</div>`;

    const tdScore = document.createElement("td");
    tdScore.innerHTML =
      app.match_score == null
        ? "—"
        : `<span class="${scoreClass(app.match_score)}">${app.match_score}</span>`;

    const tdStatus = document.createElement("td");
    const sel = document.createElement("select");
    for (const s of [
      "draft",
      "ready",
      "submitted",
      "interviewing",
      "offer",
      "rejected",
    ]) {
      const o = document.createElement("option");
      o.value = o.textContent = s;
      if (s === app.status) o.selected = true;
      sel.appendChild(o);
    }
    sel.addEventListener("change", () => updateStatus(app.id, sel.value));
    tdStatus.appendChild(sel);

    const tdActions = document.createElement("td");
    const viewBtn = document.createElement("button");
    viewBtn.className = "secondary";
    viewBtn.textContent = "Open";
    viewBtn.addEventListener("click", () => openDrawer(app.id));
    tdActions.appendChild(viewBtn);

    tr.append(tdJob, tdScore, tdStatus, tdActions);
    tbody.appendChild(tr);
  }
}

async function updateStatus(appId, status) {
  try {
    await api(`/api/applications/${appId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  } catch (err) {
    alert("Update failed: " + err.message);
  }
}

async function openDrawer(appId) {
  const app = await api(`/api/applications/${appId}`);
  const drawer = $("#drawer");
  const body = $("#drawerBody");
  const m = app.match || {};
  const tags = (arr) =>
    (arr || []).map((x) => `<span class="tag">${esc(x)}</span>`).join("");

  body.innerHTML = `
    <h2>Application #${app.id}</h2>
    <p><strong>Fit score:</strong>
      <span class="${scoreClass(app.match_score)}">${app.match_score ?? "—"}</span>
      — ${esc(m.verdict || "")}</p>
    <h3>Strengths</h3><div>${tags(m.strengths)}</div>
    <h3>Gaps</h3><div>${tags(m.gaps)}</div>
    <h3>Missing keywords</h3><div>${tags(m.missing_keywords)}</div>
    <h3>Cover letter</h3>
    <button id="genLetter">${
      app.cover_letter ? "Regenerate" : "Generate"
    } cover letter</button>
    <textarea id="letterInstr" rows="2"
      placeholder="Optional: extra instructions (tone, emphasis, length)…"></textarea>
    <pre id="letterOut">${esc(app.cover_letter || "(not generated yet)")}</pre>
  `;
  drawer.classList.remove("hidden");

  $("#genLetter").addEventListener("click", async (e) => {
    busy(e.target, true);
    $("#letterOut").textContent = "Drafting…";
    try {
      const updated = await api(`/api/applications/${appId}/cover-letter`, {
        method: "POST",
        body: JSON.stringify({
          instructions: $("#letterInstr").value.trim() || null,
        }),
      });
      $("#letterOut").textContent = updated.cover_letter;
      await loadApps();
    } catch (err) {
      $("#letterOut").textContent = "Error: " + err.message;
    } finally {
      busy(e.target, false);
    }
  });
}

$("#drawerClose").addEventListener("click", () =>
  $("#drawer").classList.add("hidden")
);

// ---- utils ------------------------------------------------------------

function esc(s) {
  return String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[c]
  );
}

// ---- boot -------------------------------------------------------------

(async function init() {
  await loadHealth();
  await loadCvs();
  await loadJobs();
  await loadApps();
})();
