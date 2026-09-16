/**
 * ZCode 自定义模型供应商 - 自动拉取模型列表插件 (开源旗舰版)
 * 1. 极致现代视觉：精致高级渐变质感按钮（自适应深浅主题、悬停微光与物理动效）
 * 2. 100% 精准识别：外部已展示模型标注「已添加」并不勾选，未展示新模型标注「新模型」并默认勾选
 * 3. 完美交互：滚动位置丝毫不动，搜索就地过滤
 * 4. 自动原生刷新：保存后自动触发官方刷新与组件重新装载，新模型卡片秒级呈现
 * 5. 跨进程安全 IPC 桥梁：原生无 CORS 限制、极速安全持久化
 */
(() => {
  if (window.__ZCODE_MODEL_PULLER_LOADED_PRO__) return;
  window.__ZCODE_MODEL_PULLER_LOADED_PRO__ = true;

  console.log("[ZCode-Model-Puller] 开源旗舰版插件已装载");

  // 样式系统
  const style = document.createElement("style");
  style.id = "zcode-model-puller-style-pro";
  style.textContent = `
    :root {
      --zpull-bg: #ffffff;
      --zpull-fg: #18181b;
      --zpull-fg-muted: #71717a;
      --zpull-border: #e4e4e7;
      --zpull-border-subtle: #f4f4f5;
      --zpull-input-bg: #ffffff;
      --zpull-input-border: #d4d4d8;
      --zpull-list-bg: #fcfcfd;
      --zpull-item-hover: #f4f4f5;
      --zpull-header-bg: #fafafa;
      --zpull-footer-bg: #fafafa;
      --zpull-shadow: 0 20px 40px rgba(0, 0, 0, 0.12);
      --zpull-btn-cancel-bg: #f4f4f5;
      --zpull-btn-cancel-border: #e4e4e7;
      --zpull-btn-cancel-fg: #27272a;
      --zpull-btn-cancel-hover: #e4e4e7;
      --zpull-badge-exists-bg: #f4f4f5;
      --zpull-badge-exists-fg: #71717a;
      --zpull-badge-exists-border: #e4e4e7;
      --zpull-badge-new-bg: #ecfdf5;
      --zpull-badge-new-fg: #059669;
      --zpull-badge-new-border: #a7f3d0;

      /* 浅色模式按钮高级质感 */
      --zpull-trigger-bg: linear-gradient(135deg, #f0f7ff 0%, #e0effe 100%);
      --zpull-trigger-fg: #1d4ed8;
      --zpull-trigger-border: rgba(59, 130, 246, 0.32);
      --zpull-trigger-hover-bg: linear-gradient(135deg, #e0effe 0%, #bae6fd 100%);
      --zpull-trigger-hover-shadow: 0 4px 12px rgba(37, 99, 235, 0.18);
    }

    .dark, html.dark, body.dark {
      --zpull-bg: #1c1c1e;
      --zpull-fg: #f0f0f0;
      --zpull-fg-muted: #a1a1aa;
      --zpull-border: rgba(255, 255, 255, 0.14);
      --zpull-border-subtle: rgba(255, 255, 255, 0.06);
      --zpull-input-bg: #141416;
      --zpull-input-border: rgba(255, 255, 255, 0.15);
      --zpull-list-bg: #151517;
      --zpull-item-hover: rgba(255, 255, 255, 0.05);
      --zpull-header-bg: #19191b;
      --zpull-footer-bg: #19191b;
      --zpull-shadow: 0 24px 48px rgba(0, 0, 0, 0.6);
      --zpull-btn-cancel-bg: rgba(255, 255, 255, 0.08);
      --zpull-btn-cancel-border: rgba(255, 255, 255, 0.1);
      --zpull-btn-cancel-fg: #eee;
      --zpull-btn-cancel-hover: rgba(255, 255, 255, 0.14);
      --zpull-badge-exists-bg: rgba(107, 114, 128, 0.2);
      --zpull-badge-exists-fg: #9ca3af;
      --zpull-badge-exists-border: rgba(107, 114, 128, 0.25);
      --zpull-badge-new-bg: rgba(16, 185, 129, 0.15);
      --zpull-badge-new-fg: #10b981;
      --zpull-badge-new-border: rgba(16, 185, 129, 0.3);

      /* 暗黑模式按钮高级质感 */
      --zpull-trigger-bg: linear-gradient(135deg, rgba(37, 99, 235, 0.2) 0%, rgba(30, 58, 138, 0.28) 100%);
      --zpull-trigger-fg: #60a5fa;
      --zpull-trigger-border: rgba(96, 165, 250, 0.38);
      --zpull-trigger-hover-bg: linear-gradient(135deg, rgba(37, 99, 235, 0.3) 0%, rgba(30, 58, 138, 0.42) 100%);
      --zpull-trigger-hover-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
    }

    /* 现代高级感触发按钮样式 */
    #zcode-auto-pull-models-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      margin-left: 8px;
      margin-top: 4px;
      height: 36px;
      padding: 0 14px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      background: var(--zpull-trigger-bg);
      color: var(--zpull-trigger-fg);
      border: 1px solid var(--zpull-trigger-border);
      cursor: pointer;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      user-select: none;
    }
    #zcode-auto-pull-models-btn:hover {
      background: var(--zpull-trigger-hover-bg);
      box-shadow: var(--zpull-trigger-hover-shadow);
      transform: translateY(-1px);
    }
    #zcode-auto-pull-models-btn:active {
      transform: translateY(0);
    }
    #zcode-auto-pull-models-btn.loading {
      opacity: 0.75;
      cursor: wait;
      pointer-events: none;
    }
    .zcode-pull-bolt-icon {
      width: 15px;
      height: 15px;
      fill: currentColor;
      transition: transform 0.2s;
    }
    #zcode-auto-pull-models-btn:hover .zcode-pull-bolt-icon {
      transform: scale(1.15);
    }

    @keyframes zcodeSpin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    .zcode-spin-icon {
      animation: zcodeSpin 1s linear infinite;
    }

    /* 弹窗遮罩 */
    .zcode-pull-modal-overlay {
      position: fixed;
      inset: 0;
      z-index: 999999;
      background: rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(5px);
      display: flex;
      align-items: center;
      justify-content: center;
      animation: zcodeFadeIn 0.15s ease-out;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    @keyframes zcodeFadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    .zcode-pull-modal {
      width: 580px;
      max-width: 92vw;
      max-height: 85vh;
      background: var(--zpull-bg);
      color: var(--zpull-fg);
      border: 1px solid var(--zpull-border);
      border-radius: 14px;
      box-shadow: var(--zpull-shadow);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      animation: zcodeScaleIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes zcodeScaleIn {
      from { opacity: 0; transform: scale(0.96); }
      to { opacity: 1; transform: scale(1); }
    }
    .zcode-pull-header {
      padding: 16px 20px;
      background: var(--zpull-header-bg);
      border-bottom: 1px solid var(--zpull-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .zcode-pull-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--zpull-fg);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .zcode-pull-close {
      background: transparent;
      border: none;
      color: var(--zpull-fg-muted);
      cursor: pointer;
      font-size: 18px;
      padding: 4px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s;
    }
    .zcode-pull-close:hover {
      background: var(--zpull-item-hover);
      color: var(--zpull-fg);
    }
    .zcode-pull-body {
      padding: 16px 20px;
      overflow-y: hidden;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .zcode-pull-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }
    .zcode-pull-search {
      flex: 1;
      background: var(--zpull-input-bg);
      border: 1px solid var(--zpull-input-border);
      border-radius: 8px;
      padding: 7px 12px;
      color: var(--zpull-fg);
      font-size: 13px;
      outline: none;
      transition: border-color 0.15s;
    }
    .zcode-pull-search:focus {
      border-color: #3b82f6;
    }
    .zcode-pull-btn-group {
      display: flex;
      gap: 6px;
    }
    .zcode-pull-mini-btn {
      background: var(--zpull-btn-cancel-bg);
      border: 1px solid var(--zpull-btn-cancel-border);
      color: var(--zpull-fg);
      font-size: 12px;
      padding: 5px 10px;
      border-radius: 6px;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s;
    }
    .zcode-pull-mini-btn:hover {
      background: var(--zpull-btn-cancel-hover);
    }
    .zcode-pull-list {
      flex: 1;
      max-height: 380px;
      overflow-y: auto;
      border: 1px solid var(--zpull-border);
      border-radius: 8px;
      background: var(--zpull-list-bg);
    }
    .zcode-pull-item {
      display: flex;
      align-items: center;
      padding: 9px 12px;
      cursor: pointer;
      user-select: none;
      transition: background 0.1s;
      border-bottom: 1px solid var(--zpull-border-subtle);
    }
    .zcode-pull-item:last-child {
      border-bottom: none;
    }
    .zcode-pull-item:hover {
      background: var(--zpull-item-hover);
    }
    .zcode-pull-item input[type="checkbox"] {
      margin-right: 12px;
      accent-color: #2563eb;
      width: 16px;
      height: 16px;
      cursor: pointer;
      pointer-events: none;
    }
    .zcode-pull-item-name {
      flex: 1;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 13px;
      color: var(--zpull-fg);
    }
    .zcode-pull-badge {
      font-size: 11px;
      padding: 2px 7px;
      border-radius: 4px;
      font-weight: 500;
    }
    .zcode-pull-badge-new {
      background: var(--zpull-badge-new-bg);
      color: var(--zpull-badge-new-fg);
      border: 1px solid var(--zpull-badge-new-border);
    }
    .zcode-pull-badge-exists {
      background: var(--zpull-badge-exists-bg);
      color: var(--zpull-badge-exists-fg);
      border: 1px solid var(--zpull-badge-exists-border);
    }
    .zcode-pull-footer {
      padding: 14px 20px;
      background: var(--zpull-footer-bg);
      border-top: 1px solid var(--zpull-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .zcode-pull-count-info {
      font-size: 13px;
      color: var(--zpull-fg-muted);
    }
    .zcode-pull-footer-btns {
      display: flex;
      gap: 10px;
    }
    .zcode-pull-btn-cancel {
      padding: 7px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      background: var(--zpull-btn-cancel-bg);
      border: 1px solid var(--zpull-btn-cancel-border);
      color: var(--zpull-btn-cancel-fg);
      cursor: pointer;
      transition: all 0.15s;
    }
    .zcode-pull-btn-cancel:hover {
      background: var(--zpull-btn-cancel-hover);
    }
    .zcode-pull-btn-submit {
      padding: 7px 18px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      background: #2563eb;
      border: 1px solid rgba(59, 130, 246, 0.5);
      color: #fff;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .zcode-pull-btn-submit:hover {
      background: #1d4ed8;
    }
    .zcode-pull-btn-submit:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .zcode-custom-toast {
      position: fixed;
      top: 24px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 1000000;
      background: var(--zpull-bg);
      color: var(--zpull-fg);
      padding: 10px 20px;
      border-radius: 10px;
      border: 1px solid var(--zpull-border);
      box-shadow: var(--zpull-shadow);
      font-size: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
      animation: zcodeToastPop 0.25s ease-out;
    }
    @keyframes zcodeToastPop {
      from { opacity: 0; transform: translate(-50%, -10px); }
      to { opacity: 1; transform: translate(-50%, 0); }
    }
  `;
  document.head.appendChild(style);

  function showToast(message, duration = 3000) {
    const existing = document.querySelector(".zcode-custom-toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = "zcode-custom-toast";
    toast.innerHTML = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = "opacity 0.2s, transform 0.2s";
      toast.style.opacity = "0";
      toast.style.transform = "translate(-50%, -10px)";
      setTimeout(() => toast.remove(), 200);
    }, duration);
  }

  function getZCodeApi() {
    return window.zcode;
  }

  // 自定义供应商配置（ZCode 3.12+ 存放于 ~/.zcode/v2/provider_config.json）
  async function readZCodeConfig() {
    const api = getZCodeApi();
    if (api?.readProviderConfigFile) {
      const res = await api.readProviderConfigFile();
      return res?.data ?? null;
    }
    return null;
  }

  async function writeZCodeConfig(data) {
    const api = getZCodeApi();
    if (api?.writeProviderConfigFile) {
      const res = await api.writeProviderConfigFile(data);
      return !!res?.success;
    }
    return false;
  }

  function normalizeUrl(url) {
    return (url || "").trim().replace(/\/+$/, "");
  }

  function getProviderRules(cfg) {
    const rules = cfg?.config?.providerConfigRules?.providerRules;
    return Array.isArray(rules) ? rules : [];
  }

  // 依据 Base URL / API Key / 供应商名称定位当前编辑的供应商规则
  function resolveProviderRule(cfg, baseUrl, apiKey, providerName) {
    const rules = getProviderRules(cfg);
    const cleanBase = normalizeUrl(baseUrl);

    if (cleanBase) {
      const byBase = rules.find((r) => normalizeUrl(r?.config?.api?.baseUrl) === cleanBase);
      if (byBase) return byBase;
    }

    const key = (apiKey || "").trim();
    if (key) {
      const byKey = rules.find((r) => (r?.config?.access?.apiKey || "").trim() === key);
      if (byKey) return byKey;
    }

    const name = (providerName || "").trim();
    if (name) {
      const byName = rules.find((r) => (r?.providerName || "").trim() === name);
      if (byName) return byName;
    }

    if (rules.length === 1) return rules[0];
    return null;
  }

  // 供应商已声明的全部模型 ID
  function getExistingModelIds(rule) {
    const found = new Set();
    const cfg = rule?.config || {};
    for (const list of [cfg.personalModelIds, cfg.modelOrder, cfg.builtinModelIds]) {
      if (!Array.isArray(list)) continue;
      for (const id of list) {
        if (typeof id === "string" && id.trim()) found.add(id.trim());
      }
    }
    return found;
  }

  function getCurrentProviderName() {
    const nameInputs = document.querySelectorAll("input[value]");
    for (const inp of nameInputs) {
      const val = inp.value.trim();
      if (val && !val.startsWith("http") && !val.startsWith("sk-") && !val.includes("/")) {
        return val;
      }
    }
    return "";
  }

  function getFormCredentials() {
    let baseUrl = "";
    let apiKey = "";

    const inputs = Array.from(document.querySelectorAll("input"));
    for (const input of inputs) {
      const val = input.value.trim();
      const placeholder = (input.placeholder || "").toLowerCase();
      const testid = input.getAttribute("data-testid") || "";

      if (
        !apiKey &&
        (input.type === "password" ||
          testid.includes("Pne") ||
          placeholder.includes("key") ||
          placeholder.includes("sk-"))
      ) {
        if (val) apiKey = val;
      }

      if (
        !baseUrl &&
        input.type === "text" &&
        (placeholder.includes("http") ||
          placeholder.includes("v1") ||
          placeholder.includes("api") ||
          val.startsWith("http"))
      ) {
        if (val) baseUrl = val;
      }
    }

    return { baseUrl, apiKey };
  }

  // 精准识别外部已存在的模型列表
  async function getExistingModels(baseUrl, apiKey) {
    const existing = new Set();

    // 1. 扫描页面输入框中的模型 ID
    const inputs = document.querySelectorAll("input");
    for (const inp of inputs) {
      const val = (inp.value || "").trim();
      if (!val) continue;
      if (val.startsWith("http://") || val.startsWith("https://") || val.startsWith("sk-")) {
        continue;
      }

      const isFontMono = inp.classList.contains("font-mono");
      const isModelPlaceholder =
        (inp.placeholder || "").includes("模型") || (inp.placeholder || "").toLowerCase().includes("model");
      const isInsideModelList = inp.closest(".divide-y, .divide-input-border, [class*='divide-']");

      if (isFontMono || isModelPlaceholder || isInsideModelList) {
        existing.add(val);
      }
    }

    // 2. 结合 provider_config.json 辅助校验
    try {
      const cfg = await readZCodeConfig();
      const rule = resolveProviderRule(cfg, baseUrl, apiKey, getCurrentProviderName());
      if (rule) {
        for (const id of getExistingModelIds(rule)) existing.add(id);
      }
    } catch (e) {
      console.warn("[ZCode-Model-Puller] 读取配置辅助识别出错:", e);
    }

    console.log("[ZCode-Model-Puller] 外部已展示模型列表:", Array.from(existing));
    return existing;
  }

  /**
   * 核心突破：百分之百自动触发官方原生刷新
   * 直接联动页面上部的原生刷新按钮与左侧导航，促使 React 立即重新加载模型
   */
  function triggerZCodeUIRefresh() {
    console.log("[ZCode-Model-Puller] 触发原生自动刷新...");

    // 1. 优先点击页面右上方的官方原生刷新按钮
    // 特征：位于“管理自定义模型供应商...”文案同一横向容器右侧
    let refreshClicked = false;
    const descParagraph = Array.from(document.querySelectorAll("p")).find(
      (p) => p.textContent.includes("管理自定义模型供应商") || p.textContent.includes("配置后可在聊天时选择使用")
    );
    if (descParagraph && descParagraph.parentElement) {
      const btn = descParagraph.parentElement.querySelector("button");
      if (btn) {
        console.log("[ZCode-Model-Puller] 点击官方主刷新按钮");
        btn.click();
        refreshClicked = true;
      }
    }

    // 2. 兜底尝试查找右上角带有刷新旋转图标的按钮
    if (!refreshClicked) {
      const buttons = Array.from(document.querySelectorAll("button"));
      for (const b of buttons) {
        const aria = (b.getAttribute("aria-label") || "").toLowerCase();
        const title = (b.getAttribute("title") || "").toLowerCase();
        const rect = b.getBoundingClientRect();
        if (
          (aria.includes("刷新") || aria.includes("refresh") || title.includes("刷新") || title.includes("refresh")) ||
          (rect.top < 180 && rect.right > window.innerWidth - 200 && b.querySelector("svg"))
        ) {
          b.click();
          refreshClicked = true;
          break;
        }
      }
    }

    // 3. 伴随轻点当前选中的供应商项，触发组件重新渲染
    setTimeout(() => {
      const pName = getCurrentProviderName();
      if (pName) {
        const sideItems = Array.from(
          document.querySelectorAll("div[class*='rounded'], button, div[class*='cursor-pointer']")
        );
        for (const item of sideItems) {
          const rect = item.getBoundingClientRect();
          if (rect.left < 360 && item.textContent.includes(pName)) {
            item.click();
            break;
          }
        }
      }
    }, 150);
  }

  // 模型选择弹窗
  async function openModelSelectModal(models, baseUrl, apiKey) {
    const existingModels = await getExistingModels(baseUrl, apiKey);

    const stateMap = new Map();
    let newCount = 0;
    for (const id of models) {
      const exists = existingModels.has(id);
      const selected = !exists; // 仅新模型默认勾选
      stateMap.set(id, { exists, selected });
      if (!exists) newCount++;
    }

    const overlay = document.createElement("div");
    overlay.className = "zcode-pull-modal-overlay";

    overlay.innerHTML = `
      <div class="zcode-pull-modal">
        <div class="zcode-pull-header">
          <div class="zcode-pull-title">
            <svg class="zcode-pull-bolt-icon" viewBox="0 0 24 24" style="color: #3b82f6;">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
            <span>选择要同步的模型 (共 ${models.length} 个，待添加新模型 ${newCount} 个)</span>
          </div>
          <button class="zcode-pull-close" id="zcode-modal-close-btn" title="关闭">✕</button>
        </div>
        <div class="zcode-pull-body">
          <div class="zcode-pull-toolbar">
            <input type="text" class="zcode-pull-search" id="zcode-modal-search" placeholder="搜索模型名称..." />
            <div class="zcode-pull-btn-group">
              <button class="zcode-pull-mini-btn" id="zcode-select-all">全选</button>
              <button class="zcode-pull-mini-btn" id="zcode-select-none">清空</button>
              <button class="zcode-pull-mini-btn" id="zcode-select-new">仅选新模型 (${newCount})</button>
            </div>
          </div>
          <div class="zcode-pull-list" id="zcode-modal-list">
            ${models
              .map((id) => {
                const info = stateMap.get(id);
                return `
              <div class="zcode-pull-item" data-id="${id}">
                <input type="checkbox" ${info.selected ? "checked" : ""} data-id="${id}" />
                <span class="zcode-pull-item-name">${id}</span>
                ${
                  info.exists
                    ? `<span class="zcode-pull-badge zcode-pull-badge-exists">已添加</span>`
                    : `<span class="zcode-pull-badge zcode-pull-badge-new">新模型</span>`
                }
              </div>
            `;
              })
              .join("")}
          </div>
        </div>
        <div class="zcode-pull-footer">
          <div class="zcode-pull-count-info" id="zcode-pull-count-info">
            已选中 <strong style="color: #2563eb;" id="zcode-selected-num">${newCount}</strong> / ${models.length} 个模型
          </div>
          <div class="zcode-pull-footer-btns">
            <button class="zcode-pull-btn-cancel" id="zcode-modal-cancel">取消</button>
            <button class="zcode-pull-btn-submit" id="zcode-modal-confirm" ${
              newCount === 0 ? "disabled" : ""
            }>
              <span>确认添加并保存 (<span id="zcode-btn-selected-num">${newCount}</span>)</span>
            </button>
          </div>
        </div>
      </div>
    `;

    function updateCountsOnly() {
      let selCount = 0;
      for (const [_, info] of stateMap) {
        if (info.selected) selCount++;
      }
      const numSpan = overlay.querySelector("#zcode-selected-num");
      const btnNumSpan = overlay.querySelector("#zcode-btn-selected-num");
      const confirmBtn = overlay.querySelector("#zcode-modal-confirm");

      if (numSpan) numSpan.textContent = selCount;
      if (btnNumSpan) btnNumSpan.textContent = selCount;
      if (confirmBtn) confirmBtn.disabled = selCount === 0;
    }

    const listContainer = overlay.querySelector("#zcode-modal-list");
    listContainer.addEventListener("click", (e) => {
      const itemEl = e.target.closest(".zcode-pull-item");
      if (!itemEl) return;
      const id = itemEl.getAttribute("data-id");
      const info = stateMap.get(id);
      if (info) {
        info.selected = !info.selected;
        const checkbox = itemEl.querySelector("input[type='checkbox']");
        if (checkbox) checkbox.checked = info.selected;
        updateCountsOnly();
      }
    });

    const searchInput = overlay.querySelector("#zcode-modal-search");
    searchInput.oninput = (e) => {
      const kw = e.target.value.toLowerCase().trim();
      const items = listContainer.querySelectorAll(".zcode-pull-item");
      items.forEach((it) => {
        const id = it.getAttribute("data-id").toLowerCase();
        it.style.display = id.includes(kw) ? "flex" : "none";
      });
    };

    overlay.querySelector("#zcode-select-all").onclick = () => {
      for (const [id, info] of stateMap) {
        info.selected = true;
      }
      listContainer.querySelectorAll("input[type='checkbox']").forEach((cb) => (cb.checked = true));
      updateCountsOnly();
    };

    overlay.querySelector("#zcode-select-none").onclick = () => {
      for (const [id, info] of stateMap) {
        info.selected = false;
      }
      listContainer.querySelectorAll("input[type='checkbox']").forEach((cb) => (cb.checked = false));
      updateCountsOnly();
    };

    overlay.querySelector("#zcode-select-new").onclick = () => {
      for (const [id, info] of stateMap) {
        info.selected = !info.exists;
      }
      listContainer.querySelectorAll(".zcode-pull-item").forEach((it) => {
        const id = it.getAttribute("data-id");
        const cb = it.querySelector("input[type='checkbox']");
        const info = stateMap.get(id);
        if (cb && info) cb.checked = info.selected;
      });
      updateCountsOnly();
    };

    const closeModal = () => overlay.remove();
    overlay.querySelector("#zcode-modal-close-btn").onclick = closeModal;
    overlay.querySelector("#zcode-modal-cancel").onclick = closeModal;

    const confirmBtn = overlay.querySelector("#zcode-modal-confirm");
    confirmBtn.onclick = async () => {
      const toAdd = [];
      for (const [id, info] of stateMap) {
        if (info.selected) toAdd.push(id);
      }
      if (toAdd.length === 0) return;

      confirmBtn.disabled = true;
      confirmBtn.innerHTML = `<span>⏳ 正在保存...</span>`;

      try {
        console.log("[ZCode-Model-Puller] 通过 IPC 读取供应商配置...");
        const cfg = await readZCodeConfig();
        if (!cfg || !cfg.config) {
          throw new Error("未能获取到 ZCode 供应商配置数据");
        }

        const rule = resolveProviderRule(cfg, baseUrl, apiKey, getCurrentProviderName());
        if (!rule) {
          throw new Error(
            baseUrl
              ? `未在配置中找到与 ${baseUrl} 匹配的供应商，请先保存该供应商后再拉取`
              : "未找到匹配的供应商，请先填写 Base URL 并保存"
          );
        }

        const pcfg = rule.config || (rule.config = {});
        const existingIds = getExistingModelIds(rule);
        const added = toAdd.filter((id) => !existingIds.has(id));

        // 1. 写入模型清单（保持既有顺序，新模型追加在末尾）
        const personal = Array.isArray(pcfg.personalModelIds) ? pcfg.personalModelIds.slice() : [];
        for (const id of toAdd) {
          if (!personal.includes(id)) personal.push(id);
        }
        pcfg.personalModelIds = personal;

        const order = Array.isArray(pcfg.modelOrder) ? pcfg.modelOrder.slice() : [];
        for (const id of toAdd) {
          if (!order.includes(id)) order.push(id);
        }
        pcfg.modelOrder = order;

        // 2. 为新模型补模型规则：直接复制同供应商已有规则的 config，确保结构始终合法
        const mcr = cfg.config.modelConfigRules || (cfg.config.modelConfigRules = {});
        if (!Array.isArray(mcr.providerModelRules)) mcr.providerModelRules = [];
        if (!Array.isArray(mcr.manualProviderModelRules)) mcr.manualProviderModelRules = [];

        const siblings = mcr.providerModelRules.filter((r) => r?.providerId === rule.providerId && r.config);
        if (siblings.length > 0 && added.length > 0) {
          const template = JSON.parse(JSON.stringify(siblings[siblings.length - 1].config));
          const declared = new Set(
            mcr.providerModelRules.filter((r) => r?.providerId === rule.providerId).map((r) => r.modelId)
          );
          for (const id of added) {
            if (declared.has(id)) continue;
            mcr.providerModelRules.push({
              modelId: id,
              providerId: rule.providerId,
              config: JSON.parse(JSON.stringify(template)),
            });
          }
        }

        console.log(
          `[ZCode-Model-Puller] 成功写入 ${added.length} 个新模型到:`,
          rule.providerName || rule.providerId
        );
        const ok = await writeZCodeConfig(cfg);
        if (!ok) {
          throw new Error("写入配置文件失败");
        }

        showToast(`🎉 成功添加 ${toAdd.length} 个模型！已自动刷新列表`);
        closeModal();

        // 自动触发官方原生刷新，新模型卡片即刻展现在列表中！
        setTimeout(() => {
          triggerZCodeUIRefresh();
        }, 120);
      } catch (err) {
        console.error("[ZCode-Model-Puller] 保存失败:", err);
        showToast(`❌ 保存出错: ${err.message}`);
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = `<span>确认添加并保存 (${toAdd.length})</span>`;
      }
    };

    document.body.appendChild(overlay);
  }

  // 注入高级质感按钮
  function checkAndInject() {
    let addModelBtn = document.querySelector('[data-testid="Goe"]');
    if (!addModelBtn) {
      const btns = Array.from(document.querySelectorAll("button"));
      addModelBtn = btns.find(
        (b) => b.textContent.includes("添加模型") && b.getAttribute("id") !== "zcode-auto-pull-models-btn"
      );
    }

    if (!addModelBtn) return;

    const parent = addModelBtn.parentElement;
    if (!parent || parent.querySelector("#zcode-auto-pull-models-btn")) return;

    parent.style.display = "flex";
    parent.style.flexWrap = "wrap";
    parent.style.alignItems = "center";
    parent.style.gap = "8px";

    const pullBtn = document.createElement("button");
    pullBtn.id = "zcode-auto-pull-models-btn";
    pullBtn.type = "button";
    pullBtn.setAttribute("title", "根据当前 Base URL 和 API Key 自动拉取所有可用模型");

    pullBtn.innerHTML = `
      <svg class="zcode-pull-bolt-icon" viewBox="0 0 24 24">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
      </svg>
      <span>自动拉取模型</span>
    `;

    pullBtn.onclick = async (e) => {
      e.preventDefault();
      e.stopPropagation();

      const { baseUrl, apiKey } = getFormCredentials();
      console.log("[ZCode-Model-Puller] 点击拉取，凭据:", { baseUrl, hasKey: !!apiKey });

      if (!baseUrl) {
        showToast("⚠️ 请先在上方填写 Base URL");
        return;
      }

      pullBtn.classList.add("loading");
      pullBtn.innerHTML = `
        <svg class="zcode-spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 14px; height: 14px;">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
          <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path>
        </svg>
        <span>正在拉取模型...</span>
      `;

      try {
        let result = null;
        const api = getZCodeApi();
        if (api?.fetchModelsFromUrl) {
          result = await api.fetchModelsFromUrl(baseUrl, apiKey);
        } else {
          try {
            const cleanUrl = baseUrl.replace(/\/+$/, "");
            const candidates = [
              cleanUrl.endsWith("/v1") ? `${cleanUrl}/models` : `${cleanUrl}/v1/models`,
              `${cleanUrl}/models`,
            ];
            if (cleanUrl.endsWith("/api")) candidates.unshift(`${cleanUrl}/v1/models`);

            for (const u of candidates) {
              try {
                const headers = { Accept: "application/json" };
                if (apiKey) {
                  headers["Authorization"] = `Bearer ${apiKey}`;
                  headers["x-api-key"] = apiKey;
                }
                const res = await fetch(u, { headers });
                if (res.ok) {
                  const data = await res.json();
                  const list = (data.data || data.models || data).map((m) =>
                    typeof m === "string" ? m : m.id || m.name
                  );
                  result = { success: true, models: list.filter(Boolean) };
                  break;
                }
              } catch (e) {}
            }
          } catch (fetchErr) {
            result = { success: false, error: fetchErr.message };
          }
        }

        if (result?.success && result.models?.length > 0) {
          await openModelSelectModal(result.models, baseUrl, apiKey);
        } else {
          showToast(`❌ 拉取失败: ${result?.error || "未获取到模型，请检查地址和 Key"}`);
        }
      } catch (err) {
        showToast(`❌ 请求异常: ${err.message}`);
      } finally {
        pullBtn.classList.remove("loading");
        pullBtn.innerHTML = `
          <svg class="zcode-pull-bolt-icon" viewBox="0 0 24 24">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
          </svg>
          <span>自动拉取模型</span>
        `;
      }
    };

    addModelBtn.after(pullBtn);
  }

  const observer = new MutationObserver(() => checkAndInject());
  observer.observe(document.body, { childList: true, subtree: true });
  checkAndInject();
})();
