const $ = (q, el = document) => el.querySelector(q);
const $$ = (q, el = document) => Array.from(el.querySelectorAll(q));
const apiInput = $("#apiBase");
const form = $("#scoreForm");
const fileInput = $("#files");
const drop = $("#drop");
const fileList = $("#fileList");
const fileToggle = $("#fileToggle");
const statusEl = $("#status");
const submitBtn = $("#submitBtn");
const table = $("#results");
const tbody = $("#results tbody");
const countEl = $("#count");
const dlBtn = $("#downloadJson");
const filterInput = $("#filter");
const infoBtn = $("#infoBtn");
const infoModal = $("#infoModal");
const infoClose = $("#infoModal .modal-close");

let fileState = { files: [], collapsed: true, limit: 5 };
let lastResults = [];

function setStatus(s) { statusEl.textContent = s; }
function human(n) { return typeof n === "number" ? n.toFixed(1) : n; }
function scoreClass(n) { return Number(n) >= 70 ? "score-ok" : "score-bad"; }

function openInfo() {
    infoModal.classList.add("open");
    infoModal.removeAttribute("hidden");
    infoClose.focus();
}
function closeInfo() {
    infoModal.classList.remove("open");
    infoModal.setAttribute("hidden", "");
    infoBtn.focus();
}

function listFiles(files) {
    fileState.files = Array.from(files);
    renderFileList();
}

function renderFileList() {
    const { files, collapsed, limit } = fileState;
    const shown = collapsed ? files.slice(0, limit) : files;
    fileList.innerHTML = shown.map(f => `<li>${escapeHtml(f.name)} (${(f.size / 1024).toFixed(1)} KB)</li>`).join("");

    const extra = files.length - shown.length;
    if (extra > 0 || (!collapsed && files.length > limit)) {
        fileToggle.hidden = false;
        fileToggle.textContent = collapsed ? `Show more (+${extra})` : "Show less";
    } else {
        fileToggle.hidden = true;
    }
}

function appendFilesFromDT(dt) {
    const existing = new DataTransfer();
    Array.from(fileInput.files).forEach(f => existing.items.add(f));
    Array.from(dt.files).forEach(f => existing.items.add(f));
    fileInput.files = existing.files;
    listFiles(fileInput.files); // renders once
}

fileToggle.addEventListener("click", () => {
    fileState.collapsed = !fileState.collapsed;
    renderFileList();
});
infoBtn.addEventListener("click", openInfo);
infoClose.addEventListener("click", closeInfo);
infoModal.addEventListener("click", (e) => { if (e.target === infoModal) closeInfo(); });
fileInput.addEventListener("change", () => listFiles(fileInput.files));
drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("drag"); });
drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
drop.addEventListener("drop", e => { e.preventDefault(); drop.classList.remove("drag"); appendFilesFromDT(e.dataTransfer); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !infoModal.hasAttribute("hidden")) closeInfo(); });
fileInput.addEventListener("change", () => listFiles(fileInput.files));

function toRows(arr) {
    return arr.map(r => ({
        name: r.name || "",
        score: Number(r.score ?? 0),
        years: r.years_experience || "",
        skills: r.skills || "",
        langs: r.languages || "",
        motivo: r.motivo || "",
        url: r.url || ""
    }));
}

function render(rows) {
    const q = filterInput.value.trim().toLowerCase();
    const filtered = q
        ? rows.filter(r =>
            (r.name.toLowerCase().includes(q)) ||
            (r.skills.toLowerCase().includes(q)) ||
            (r.langs.toLowerCase().includes(q)) ||
            (r.motivo.toLowerCase().includes(q))
        )
        : rows;

    tbody.innerHTML = filtered.map(r => `
    <tr>
      <td>${r.url ? `<a href="${r.url}" target="_blank" rel="noopener">${escapeHtml(r.name)}</a>` : escapeHtml(r.name)}</td>
      <td><span class="${scoreClass(r.score)}">${human(Number(r.score))}</span></td>
      <td>${escapeHtml(String(r.years))}</td>
      <td>${escapeHtml(r.skills)}</td>
      <td>${escapeHtml(r.langs)}</td>
      <td>${escapeHtml(r.motivo)}</td>
    </tr>
  `).join("");

    countEl.textContent = `${filtered.length} shown of ${rows.length} total`;
    dlBtn.disabled = rows.length === 0;
}

function escapeHtml(s) {
    return String(s)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

let sortKey = "score";
let sortDir = "desc";
function sortRows(rows, key = sortKey, dir = sortDir) {
    const copy = rows.slice();
    copy.sort((a, b) => {
        const va = a[key], vb = b[key];
        if (key === "score") return dir === "asc" ? va - vb : vb - va;
        return dir === "asc" ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
    });
    return copy;
}
$$("th[data-sort]").forEach(th => {
    th.addEventListener("click", () => {
        const k = th.getAttribute("data-sort");
        sortDir = (sortKey === k && sortDir === "asc") ? "desc" : "asc";
        sortKey = k;
        lastResults = sortRows(lastResults, sortKey, sortDir);
        render(lastResults);
    });
});

filterInput.addEventListener("input", () => render(lastResults));

dlBtn.addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(lastResults, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "results.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
});

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!fileInput.files.length) { setStatus("Select at least one PDF"); return; }

    const fd = new FormData();
    Array.from(fileInput.files).forEach(f => fd.append("files", f, f.name));
    fd.append("degree", $("#degree").value);
    fd.append("req", $("#req").value);
    fd.append("nice", $("#nice").value);
    fd.append("soft_req", $("#soft_req").value);
    fd.append("soft_nice", $("#soft_nice").value);
    fd.append("langs", $("#langs").value);
    fd.append("min_years", $("#min_years").value || "0");
    fd.append("notes", $("#notes").value);

    submitBtn.disabled = true;
    setStatus("Uploading and scoring...");
    try {
        const base = apiInput.value.replace(/\/+$/, "");
        const res = await fetch(`${base}/score/pdfs`, { method: "POST", body: fd });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const rows = toRows(data.results || []);
        lastResults = sortRows(rows);
        render(lastResults);
        setStatus(`Done. ${data.count ?? rows.length} candidates scored.`);
    } catch (err) {
        setStatus(`Error: ${err.message || err}`);
    } finally {
        submitBtn.disabled = false;
    }
});
