/* ================================================================
   醫療評分系統 - Frontend Application
   ================================================================ */

// 自動偵測 ROOT_PATH：前端掛載在 /frontend 下，取其上層路徑
// 例如 https://domain/api/frontend/ → ROOT_PATH = "/api"
const _frontendPath = window.location.pathname.replace(/\/frontend\/?.*$/, "");
const API_BASE = window.location.origin + _frontendPath;

// ── State ──────────────────────────────────────────────────────
let departments = [];
let formulas = [];
let selectedFormulaId = null;
let selectedFormulaYaml = "";
let chatYaml = ""; // latest YAML from chat
let chatAttachments = []; // attached files [{filename, content}]

// ── Init ───────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadDepartments();
  loadDbFormulas();
});

// ================================================================
//  TAB NAVIGATION
// ================================================================

function switchTab(tabName) {
  // Nav buttons
  document
    .querySelectorAll(".nav-tab")
    .forEach((btn) => btn.classList.remove("active"));
  document
    .querySelector(`.nav-tab[data-tab="${tabName}"]`)
    .classList.add("active");
  // Tab content
  document
    .querySelectorAll(".tab-content")
    .forEach((el) => el.classList.remove("active"));
  document.getElementById(`tab-${tabName}`).classList.add("active");
  // Refresh data on tab switch
  if (tabName === "departments") loadDepartments();
  if (tabName === "formulas") {
    loadDepartments(true); // populate filters
    loadDbFormulas();
  }
}

// ================================================================
//  TOAST NOTIFICATIONS
// ================================================================

function showToast(msg, type = "info") {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3100);
}

// ================================================================
//  LOADING OVERLAY
// ================================================================

function showLoading() {
  document.getElementById("loadingOverlay").classList.remove("hidden");
}
function hideLoading() {
  document.getElementById("loadingOverlay").classList.add("hidden");
}

// ================================================================
//  API HELPERS
// ================================================================

async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ================================================================
//  DEPARTMENTS
// ================================================================

async function loadDepartments(silentForFilter = false) {
  try {
    departments = await apiFetch("/v1/departments");
    if (!silentForFilter) renderDeptGrid();
    populateDeptSelects();
  } catch (e) {
    if (!silentForFilter) showToast("載入科別失敗: " + e.message, "error");
  }
}

function renderDeptGrid() {
  const grid = document.getElementById("deptGrid");
  if (!departments.length) {
    grid.innerHTML =
      '<div class="empty-state">尚未建立任何科別，點右上方「新增科別」開始。</div>';
    return;
  }
  grid.innerHTML = departments
    .map(
      (d) => `
        <div class="dept-card">
            <div class="dept-card-header">
                <h3>${escHtml(d.name)}</h3>
                <div class="dept-card-actions">
                    <button title="刪除" class="del" onclick="deleteDepartment(${d.id}, '${escHtml(d.name)}')">X</button>
                </div>
            </div>
            ${d.description ? `<div class="dept-card-desc">${escHtml(d.description)}</div>` : ""}
            <div class="dept-card-meta">
                <span>ID: ${d.id}</span>
                <span>${formatDate(d.created_at)}</span>
            </div>
        </div>
    `,
    )
    .join("");
}

function populateDeptSelects() {
  // Filter dropdown on Formulas tab
  const filter = document.getElementById("formulaDeptFilter");
  const currentVal = filter.value;
  filter.innerHTML =
    '<option value="">全部科別</option>' +
    departments
      .map((d) => `<option value="${d.id}">${escHtml(d.name)}</option>`)
      .join("");
  filter.value = currentVal;

  // Create formula modal dropdown
  const sel = document.getElementById("formulaDeptSelect");
  sel.innerHTML = departments
    .map((d) => `<option value="${d.id}">${escHtml(d.name)}</option>`)
    .join("");
}

function showCreateDeptModal() {
  document.getElementById("deptNameInput").value = "";
  document.getElementById("deptDescInput").value = "";
  openModal("modalCreateDept");
  setTimeout(() => document.getElementById("deptNameInput").focus(), 100);
}

async function createDepartment() {
  const name = document.getElementById("deptNameInput").value.trim();
  const desc = document.getElementById("deptDescInput").value.trim();
  if (!name) return showToast("請輸入科別名稱", "error");

  try {
    showLoading();
    await apiFetch("/v1/departments", {
      method: "POST",
      body: JSON.stringify({ name, description: desc || null }),
    });
    closeModal("modalCreateDept");
    showToast("科別建立成功", "success");
    await loadDepartments();
  } catch (e) {
    showToast("建立失敗: " + e.message, "error");
  } finally {
    hideLoading();
  }
}

async function deleteDepartment(id, name) {
  if (!confirm(`確定要刪除科別「${name}」嗎？其下所有公式也會一併刪除。`))
    return;
  try {
    showLoading();
    await apiFetch(`/v1/departments/${id}`, { method: "DELETE" });
    showToast("科別已刪除", "success");
    await loadDepartments();
    await loadDbFormulas();
  } catch (e) {
    showToast("刪除失敗: " + e.message, "error");
  } finally {
    hideLoading();
  }
}

// ================================================================
//  FORMULAS
// ================================================================

async function loadDbFormulas() {
  const deptId = document.getElementById("formulaDeptFilter").value;
  const qs = deptId ? `?department_id=${deptId}` : "";
  try {
    formulas = await apiFetch(`/v1/formulas${qs}`);
    renderFormulaList();
  } catch (e) {
    showToast("載入公式失敗: " + e.message, "error");
  }
}

function renderFormulaList() {
  const el = document.getElementById("dbFormulasList");
  if (!formulas.length) {
    el.innerHTML = '<div class="empty-state">尚無公式</div>';
    return;
  }
  el.innerHTML = formulas
    .map(
      (f) => `
        <div class="formula-item${f.id === selectedFormulaId ? " active" : ""}"
             onclick="selectFormula(${f.id})">
            <div class="formula-item-name">${escHtml(f.name)}</div>
            <div class="formula-item-meta">
                <span>科別 #${f.department_id}</span>
                <button class="formula-item-del" onclick="event.stopPropagation();deleteFormula(${f.id},'${escHtml(f.name)}')" title="刪除">X</button>
            </div>
        </div>
    `,
    )
    .join("");
}

function selectFormula(id) {
  selectedFormulaId = id;
  const f = formulas.find((x) => x.id === id);
  if (!f) return;

  selectedFormulaYaml = f.yaml_content || "";
  document.getElementById("formulaDetailName").textContent = f.name;
  document.getElementById("formulaDetailYaml").value = f.yaml_content || "";
  document.getElementById("formulaDetailAst").value = f.ast_data
    ? JSON.stringify(f.ast_data, null, 2)
    : "";

  // Reset calc
  document.getElementById("calcVarsForm").classList.add("hidden");
  document.getElementById("calcVarsForm").innerHTML = "";
  document.getElementById("calcSubmitBtn").classList.add("hidden");
  document.getElementById("noVarsMessage").style.display = "";
  document.getElementById("calcResult").innerHTML =
    '<div class="empty-state" style="margin-top:20px">尚無計算結果</div>';

  renderFormulaList(); // refresh active highlight
}

async function deleteFormula(id, name) {
  if (!confirm(`確定要刪除公式「${name}」嗎？`)) return;
  try {
    showLoading();
    await apiFetch(`/v1/formulas/${id}`, { method: "DELETE" });
    showToast("公式已刪除", "success");
    if (selectedFormulaId === id) {
      selectedFormulaId = null;
      document.getElementById("formulaDetailName").textContent = "";
      document.getElementById("formulaDetailYaml").value = "";
      document.getElementById("formulaDetailAst").value = "";
    }
    await loadDbFormulas();
  } catch (e) {
    showToast("刪除失敗: " + e.message, "error");
  } finally {
    hideLoading();
  }
}

function showCreateFormulaModal(yamlPrefill = "") {
  document.getElementById("formulaModalTitle").textContent = "新增公式";
  document.getElementById("formulaNameInput").value = "";
  document.getElementById("formulaDescInput").value = "";
  document.getElementById("formulaYamlInput").value = yamlPrefill || "";
  // Ensure dept list is populated
  populateDeptSelects();
  openModal("modalCreateFormula");
  setTimeout(() => document.getElementById("formulaNameInput").focus(), 100);
}

async function createFormula() {
  const deptId = document.getElementById("formulaDeptSelect").value;
  const name = document.getElementById("formulaNameInput").value.trim();
  const desc = document.getElementById("formulaDescInput").value.trim();
  const yaml = document.getElementById("formulaYamlInput").value.trim();

  if (!deptId) return showToast("請選擇科別", "error");
  if (!name) return showToast("請輸入公式名稱", "error");
  if (!yaml) return showToast("請輸入 YAML 公式內容", "error");

  try {
    showLoading();
    // Convert YAML to AST first
    let astData = {};
    try {
      const astRes = await apiFetch("/v1/formulas/convert-to-ast", {
        method: "POST",
        body: JSON.stringify({ yaml_content: yaml }),
      });
      astData = astRes || {};
    } catch {
      // If AST conversion fails, use empty object
      console.warn("AST conversion failed, using empty ast_data");
    }

    await apiFetch(`/v1/departments/${deptId}/formulas`, {
      method: "POST",
      body: JSON.stringify({
        name,
        description: desc || null,
        yaml_content: yaml,
        ast_data: astData,
      }),
    });

    closeModal("modalCreateFormula");
    showToast("公式建立成功", "success");
    await loadDbFormulas();
  } catch (e) {
    showToast("建立失敗: " + e.message, "error");
  } finally {
    hideLoading();
  }
}

// ================================================================
//  FORMULA CALCULATION
// ================================================================

async function parseFormulaVars() {
  const yaml = document.getElementById("formulaDetailYaml").value.trim();
  if (!yaml) return showToast("請先選擇一個公式", "error");

  try {
    showLoading();
    const data = await apiFetch("/v1/formulas/extract-variables", {
      method: "POST",
      body: JSON.stringify({ yaml_content: yaml }),
    });

    const form = document.getElementById("calcVarsForm");
    const vars = data.variables || [];

    if (!vars.length) {
      form.innerHTML =
        '<div class="empty-state">此公式沒有需要輸入的變數</div>';
      form.classList.remove("hidden");
      document.getElementById("noVarsMessage").style.display = "none";
      return;
    }

    form.innerHTML = vars
      .map((v) => {
        if (v.var_type === "boolean") {
          return `
                    <div class="var-field">
                        <label>${escHtml(v.name)} <span class="var-type-badge">${v.var_type}</span></label>
                        <select data-var="${v.name}" data-type="boolean">
                            <option value="false">否 (false)</option>
                            <option value="true">是 (true)</option>
                        </select>
                    </div>`;
        }
        return `
                <div class="var-field">
                    <label>${escHtml(v.name)} <span class="var-type-badge">${v.var_type}</span></label>
                    <input type="number" data-var="${v.name}" data-type="${v.var_type}"
                           placeholder="輸入 ${v.var_type}" step="${v.var_type === "int" ? "1" : "0.01"}">
                </div>`;
      })
      .join("");

    form.classList.remove("hidden");
    document.getElementById("calcSubmitBtn").classList.remove("hidden");
    document.getElementById("noVarsMessage").style.display = "none";
  } catch (e) {
    showToast("解析變數失敗: " + e.message, "error");
  } finally {
    hideLoading();
  }
}

async function calculateScore() {
  const yaml = document.getElementById("formulaDetailYaml").value.trim();
  if (!yaml) return showToast("請先選擇一個公式", "error");

  // Collect variables
  const variables = {};
  let valid = true;
  document.querySelectorAll("#calcVarsForm [data-var]").forEach((el) => {
    const name = el.dataset.var;
    const type = el.dataset.type;
    if (type === "boolean") {
      variables[name] = el.value === "true";
    } else {
      const num = parseFloat(el.value);
      if (isNaN(num)) {
        valid = false;
        el.style.borderColor = "var(--danger)";
      } else {
        el.style.borderColor = "";
        variables[name] = type === "int" ? Math.round(num) : num;
      }
    }
  });
  if (!valid) return showToast("請填寫所有變數", "error");

  try {
    showLoading();
    const data = await apiFetch("/v1/formulas/calculate", {
      method: "POST",
      body: JSON.stringify({ yaml_content: yaml, variables }),
    });
    renderCalcResult(data);
  } catch (e) {
    showToast("計算失敗: " + e.message, "error");
  } finally {
    hideLoading();
  }
}

function renderCalcResult(data) {
  const el = document.getElementById("calcResult");

  // Determine risk class
  const riskText = (data.risk_level || "").toLowerCase();
  let riskClass = "";
  if (riskText.includes("低") || riskText.includes("low"))
    riskClass = "risk-low";
  else if (
    riskText.includes("高") ||
    riskText.includes("high") ||
    riskText.includes("危")
  )
    riskClass = "risk-high";
  else riskClass = "risk-medium";

  let html = `
        <div class="result-card">
            <h4>${escHtml(data.score_name || "評分結果")}</h4>
            <div class="result-total">${data.global_score.toFixed(3)}</div>
            <span class="result-risk ${riskClass}">${escHtml(data.risk_level || "未定義")}</span>
        </div>`;

  // Module scores
  if (data.module_scores) {
    for (const [key, mod] of Object.entries(data.module_scores)) {
      html += `
            <div class="result-card">
                <div class="module-score">
                    <div class="module-score-name">${escHtml(mod.module_name || key)}</div>
                    <div class="module-score-value">${mod.module_score.toFixed(3)}</div>
                    ${
                      mod.rules_applied && mod.rules_applied.length
                        ? `
                    <ul class="module-rules">
                        ${mod.rules_applied.map((r) => `<li>${escHtml(r)}</li>`).join("")}
                    </ul>`
                        : ""
                    }
                </div>
            </div>`;
    }
  }

  el.innerHTML = html;
}

// ================================================================
//  AI CHAT
// ================================================================

function handleChatKeydown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendChat();
  }
}

function autoResizeChatInput(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

async function sendChat() {
  const input = document.getElementById("chatInput");
  const msg = input.value.trim();
  if (!msg && !chatAttachments.length) return;

  // Collect attachments
  const attachments = chatAttachments.length ? [...chatAttachments] : null;
  const attachNames = attachments ? attachments.map((a) => a.filename) : [];

  // Clear input & attachments
  input.value = "";
  input.style.height = "auto";
  clearChatAttachments();

  // Remove welcome message
  const welcome = document.querySelector(".chat-welcome");
  if (welcome) welcome.remove();

  // Add user bubble (show attached file names if any)
  let displayMsg = msg;
  if (attachNames.length) {
    displayMsg += "\n[" + attachNames.join(", ") + "]";
  }
  appendChatMsg("user", displayMsg);

  // Add typing indicator
  const typingEl = appendTypingIndicator();

  // Disable send
  const btn = document.getElementById("chatSendBtn");
  btn.disabled = true;

  try {
    const body = { message: msg || "(see attached files)" };
    if (attachments) body.attachments = attachments;

    const data = await apiFetch("/v1/ai/chat", {
      method: "POST",
      body: JSON.stringify(body),
    });

    // Remove typing
    typingEl.remove();

    // Add AI reply
    appendChatMsg("ai", data.reply);

    // If YAML generated, show in sidebar
    if (data.generated_yaml) {
      chatYaml = data.generated_yaml;
      document.getElementById("chatYamlPreview").value = chatYaml;
      document.getElementById("btnSaveChatYaml").disabled = false;
    }
  } catch (e) {
    typingEl.remove();
    appendChatMsg("ai", `Error: ${e.message}`);
  } finally {
    btn.disabled = false;
    input.focus();
  }
}

function appendChatMsg(role, text) {
  const container = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = `chat-msg ${role}`;

  const avatar = role === "user" ? "U" : "AI";
  const formattedText = formatChatText(text);

  div.innerHTML = `
        <div class="chat-avatar">${avatar}</div>
        <div class="chat-bubble">${formattedText}</div>
    `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function appendTypingIndicator() {
  const container = document.getElementById("chatMessages");
  const div = document.createElement("div");
  div.className = "chat-typing";
  div.innerHTML = `
        <div class="chat-avatar">AI</div>
        <div class="typing-dots"><span></span><span></span><span></span></div>
    `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function formatChatText(text) {
  // Simple markdown-like formatting
  let html = escHtml(text);
  // Code blocks  ```...```
  html = html.replace(/```([\s\S]*?)```/g, "<pre>$1</pre>");
  // Inline code `...`
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Bold **...**
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  // Newlines
  html = html.replace(/\n/g, "<br>");
  return html;
}

function clearChatYaml() {
  chatYaml = "";
  document.getElementById("chatYamlPreview").value = "";
  document.getElementById("btnSaveChatYaml").disabled = true;
}

// ================================================================
//  FILE ATTACHMENTS
// ================================================================

function handleFileAttach(event) {
  const files = Array.from(event.target.files);
  if (!files.length) return;

  const MAX_SIZE = 2 * 1024 * 1024; // 2MB for docx

  files.forEach((file) => {
    if (file.size > MAX_SIZE) {
      showToast(`${file.name} too large (max 2MB)`, "error");
      return;
    }

    const isDocx = file.name.toLowerCase().endsWith(".docx");

    if (isDocx) {
      // Use mammoth.js to extract text from DOCX
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const result = await mammoth.extractRawText({
            arrayBuffer: e.target.result,
          });
          chatAttachments.push({
            filename: file.name,
            content: result.value,
          });
          renderChatAttachments();
        } catch (err) {
          showToast(`${file.name} DOCX parsing failed`, "error");
        }
      };
      reader.readAsArrayBuffer(file);
    } else {
      // Plain text files
      if (file.size > 512 * 1024) {
        showToast(`${file.name} too large (max 512KB)`, "error");
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        chatAttachments.push({
          filename: file.name,
          content: e.target.result,
        });
        renderChatAttachments();
      };
      reader.readAsText(file);
    }
  });

  // Reset input so same file can be re-selected
  event.target.value = "";
}

function removeChatAttachment(index) {
  chatAttachments.splice(index, 1);
  renderChatAttachments();
}

function clearChatAttachments() {
  chatAttachments = [];
  renderChatAttachments();
}

function renderChatAttachments() {
  const el = document.getElementById("chatAttachments");
  if (!chatAttachments.length) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML = chatAttachments
    .map(
      (a, i) => `
      <span class="attach-badge">
        <span class="attach-badge-name" title="${escHtml(a.filename)}">${escHtml(a.filename)}</span>
        <button onclick="removeChatAttachment(${i})" title="移除">x</button>
      </span>`,
    )
    .join("");
}

function saveChatYamlToFormula() {
  if (!chatYaml) return showToast("沒有可儲存的 YAML 公式", "error");
  // Open create formula modal with YAML pre-filled
  showCreateFormulaModal(chatYaml);
}

// ================================================================
//  MODAL HELPERS
// ================================================================

function openModal(id) {
  document.getElementById(id).classList.remove("hidden");
}

function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}

// Close modal on overlay click
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("modal-overlay")) {
    e.target.classList.add("hidden");
  }
});

// Close modal on Escape
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    document
      .querySelectorAll(".modal-overlay:not(.hidden)")
      .forEach((m) => m.classList.add("hidden"));
  }
});

// ================================================================
//  UTILITIES
// ================================================================

function escHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("zh-TW", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}
