const MSM_ENTITY = "sensor.medication_stock_manager";
const MSM_CARD_TAG = "medication-stock-manager-card";
const MSM_PANEL_TAG = "ha-panel-medication-stock-manager";
const MSM_CARD_VERSION = "1.4.2";

const MSM_DAYS = [
  ["mon", "Mon"],
  ["tue", "Tue"],
  ["wed", "Wed"],
  ["thu", "Thu"],
  ["fri", "Fri"],
  ["sat", "Sat"],
  ["sun", "Sun"],
];
const MSM_ALL_DAYS = MSM_DAYS.map(([value]) => value);

const MSM_TYPES = {
  capsule: "capsules",
  tablet: "tablets",
  chewable_tablet: "chewable tablets",
  plaster: "plasters",
  sachet: "sachets",
  syringe: "syringes",
  catheter: "catheters",
  sheet: "sheets",
  custom: "items",
};

const MSM_SCHEDULES = [
  ["daily", "Every day"],
  ["selected_weekdays", "Selected weekdays"],
  ["interval", "Every X days"],
  ["manual", "Manual (usage 0)"],
];

const MSM_DEFAULT_FIELDS = [
  "name",
  "owner",
  "item_type",
  "unit",
  "icon",
  "stock",
  "threshold",
  "package_size",
  "usage_per_day",
  "schedule_mode",
  "times",
  "days",
  "interval_days",
  "start_date",
  "enabled",
  "reminder_enabled",
  "reminder_title",
  "reminder_message",
  "product_url",
];

const MSM_DEFAULT_COLUMNS = ["name", "stock", "supply", "status"];
const MSM_SUPPLY_TYPES = new Set(["syringe", "catheter", "sheet"]);

class MedicationStockManagerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._config = {};
    this._message = "";
    this._messageKind = "ok";
    this._openItems = new Set();
    this._openOwners = new Set();
    this._newOwnerOpen = false;
    this._addItemOpen = false;
    this._drafts = new Map();
    this._addDraft = {};
    this._focusState = null;
    this._scrollPositions = new Map();
    this._pendingRender = false;
    this._managerSignature = null;
    this._activeStockItemId = null;
    this._optimisticStock = new Map();
    this._optimisticOrdered = new Map();
  }

  connectedCallback() {
    this._render(false);
  }

  setConfig(config) {
    const view = String(config?.view || "all").toLowerCase();
    const allowedViews = new Set([
      "all",
      "stock_table",
      "item_configuration",
      "create_item",
      "item_cards",
      "item_detail",
      "stock_buttons",
      "create_owner",
      "sidebar_settings",
    ]);
    if (!allowedViews.has(view)) {
      throw new Error(
        "view must be all, stock_table, stock_buttons, item_configuration, create_item, create_owner, sidebar_settings, item_cards, or item_detail"
      );
    }

    const owner = String(config?.owner || "all")
      .trim()
      .toLowerCase();
    if (!owner) {
      throw new Error("owner must be an owner ID or all");
    }

    this._config = { ...(config || {}), view, owner };
    if (this.isConnected) this._render();
  }

  set hass(hass) {
    const nextManagerState = hass?.states?.[MSM_ENTITY];
    const nextSignature = this._managerStateSignature(nextManagerState);
    this._hass = hass;

    if (!this.isConnected) {
      this._managerSignature = nextSignature;
      return;
    }

    if (
      this._managerSignature === nextSignature &&
      this.shadowRoot.querySelector("ha-card")
    ) {
      return;
    }

    const active = this.shadowRoot.activeElement;
    const editing =
      active && ["INPUT", "SELECT", "TEXTAREA"].includes(active.tagName);
    if (editing) {
      this._pendingRender = true;
      return;
    }

    this._managerSignature = nextSignature;
    this._optimisticStock.clear();
    this._optimisticOrdered.clear();
    this._render();
  }

  getCardSize() {
    const view = this._config.view || "all";
    if (view === "stock_table") return 4;
    if (view === "stock_buttons") return 8;
    if (view === "create_owner") return 8;
    if (view === "sidebar_settings") return 4;
    if (view === "create_item") return 8;
    if (view === "item_cards") return 8;
    if (view === "item_detail") return 4;
    return 12;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 4, rows: 8, min_rows: 2 };
  }

  _esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _num(value) {
    const number = Number(value ?? 0);
    if (!Number.isFinite(number)) return "0";
    return Number.isInteger(number)
      ? String(number)
      : number.toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
  }

  _bool(name, fallback) {
    return this._config[name] === undefined ? fallback : Boolean(this._config[name]);
  }

  _array(name, fallback = []) {
    return Array.isArray(this._config[name]) ? this._config[name] : fallback;
  }

  _items() {
    const items = this._hass?.states?.[MSM_ENTITY]?.attributes?.items || [];
    return items.map((item) => {
      const stock = this._optimisticStock.has(item.id)
        ? this._optimisticStock.get(item.id)
        : item.stock;
      const ordered = this._optimisticOrdered.has(item.id)
        ? this._optimisticOrdered.get(item.id)
        : item.ordered;
      return {
        ...item,
        stock,
        stock_text: this._num(stock),
        ordered,
      };
    });
  }

  _people() {
    return this._hass?.states?.[MSM_ENTITY]?.attributes?.people || [];
  }

  _personOptions(selected = "") {
    return [
      `<option value="">Auto-match by owner name / create new Person</option>`,
      ...this._people().map(
        (person) =>
          `<option value="${this._esc(person.entity_id)}" ` +
          `${person.entity_id === selected ? "selected" : ""}>` +
          `${this._esc(person.name)}</option>`
      ),
    ].join("");
  }

  _personSuggestion(entityId) {
    return this._people().find((person) => person.entity_id === entityId) || null;
  }

  _owners() {
    return this._hass?.states?.[MSM_ENTITY]?.attributes?.owners || [];
  }

  _owner(ownerId) {
    return this._owners().find((owner) => owner.id === ownerId) || null;
  }

  _ownerName(ownerId) {
    return this._owner(ownerId)?.name || ownerId;
  }

  _ownerOptions(selected = "") {
    return this._owners()
      .map(
        (owner) =>
          `<option value="${this._esc(owner.id)}" ` +
          `${owner.id === selected ? "selected" : ""}>` +
          `${this._esc(owner.name)}</option>`
      )
      .join("");
  }

  _filteredItems() {
    let items = [...this._items()];
    const owner = this._config.owner || "all";
    if (owner !== "all") items = items.filter((item) => item.owner === owner);

    const included = this._array("items");
    if (included.length) {
      const selected = new Set(included.map(String));
      items = items.filter(
        (item) => selected.has(item.id) || selected.has(item.name)
      );
    }

    const excluded = new Set(this._array("exclude_items").map(String));
    if (excluded.size) {
      items = items.filter(
        (item) => !excluded.has(item.id) && !excluded.has(item.name)
      );
    }

    const itemTypes = new Set(this._array("item_types").map(String));
    if (itemTypes.size) items = items.filter((item) => itemTypes.has(item.item_type));

    return items;
  }

  _managerStateSignature(stateObj) {
    if (!stateObj) return "missing";

    // Use actual manager content, not last_updated. The summary sensor can be
    // written again with identical data, and last_updated would otherwise
    // force a complete editor render and reset the page/table scroll.
    const attributes = stateObj.attributes || {};
    return JSON.stringify({
      state: stateObj.state,
      managerVersion: attributes.manager_version || "",
      items: attributes.items || [],
      owners: attributes.owners || [],
      people: attributes.people || [],
      ownerCounts: attributes.owner_counts || {},
      lowItems: attributes.low_items || 0,
      sidebar: attributes.sidebar || {},
    });
  }

  _nextParentNode(node) {
    if (!node) return null;
    if (node.parentElement) return node.parentElement;
    const root = node.getRootNode?.();
    return root?.host || null;
  }

  _captureViewportScroll() {
    const positions = [];
    const seen = new Set();

    const add = (element, left, top) => {
      if (!element || seen.has(element)) return;
      seen.add(element);
      positions.push({ element, left, top });
    };

    add(window, window.scrollX, window.scrollY);

    if (document.scrollingElement) {
      add(
        document.scrollingElement,
        document.scrollingElement.scrollLeft,
        document.scrollingElement.scrollTop
      );
    }

    let node = this;
    while ((node = this._nextParentNode(node))) {
      if (!(node instanceof HTMLElement)) continue;
      const style = getComputedStyle(node);
      const scrollable =
        /(auto|scroll|overlay)/.test(
          `${style.overflow} ${style.overflowX} ${style.overflowY}`
        ) ||
        node.scrollHeight > node.clientHeight ||
        node.scrollWidth > node.clientWidth;

      if (scrollable) add(node, node.scrollLeft, node.scrollTop);
    }

    return positions;
  }

  _restoreViewportScroll(positions) {
    const restore = () => {
      for (const position of positions || []) {
        if (position.element === window) {
          window.scrollTo(position.left, position.top);
        } else if (position.element?.isConnected) {
          position.element.scrollLeft = position.left;
          position.element.scrollTop = position.top;
        }
      }
    };

    restore();
    requestAnimationFrame(() => {
      restore();
      requestAnimationFrame(restore);
    });
  }

  _render() {
    if (!this.shadowRoot) return;
    const viewportScroll = this._captureViewportScroll();
    this._captureUiState();

    if (!this._hass) {
      this.shadowRoot.innerHTML = `<ha-card><div class="loading">Loading Medication Stock Manager…</div></ha-card>`;
      this._restoreViewportScroll(viewportScroll);
      return;
    }

    if (!this._hass.states[MSM_ENTITY]) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div class="missing">
            <h2>Medication Stock Manager</h2>
            <p>The manager entity is not available.</p>
            <p>Add or reload <strong>Medication Stock Manager</strong> under Settings → Devices &amp; services.</p>
          </div>
        </ha-card>`;
      this._restoreViewportScroll(viewportScroll);
      return;
    }

    const view = this._config.view || "all";
    const items = this._filteredItems();
    let content = "";

    if (view === "all") {
      content = [
        this._stockTableSection(
          items,
          "Medication and supply stock",
          "all"
        ),
        this._configurationSection(items),
        this._bool("show_create", true) ? this._addItemForm(false) : "",
        this._bool("show_create_owner", true)
          ? this._createOwnerSection()
          : "",
      ].join("");
    } else if (view === "stock_table") {
      content = this._stockTableSection(
        items,
        this._config.title || "Medication and supply stock",
        this._config.owner || "all"
      );
    } else if (view === "stock_buttons") {
      content = this._stockButtonsSection(items);
    } else if (view === "item_configuration") {
      content = this._configurationSection(items);
    } else if (view === "create_owner") {
      content = this._createOwnerSection();
    } else if (view === "sidebar_settings") {
      content = this._sidebarSettingsSection();
    } else if (view === "create_item") {
      content = this._addItemForm(true);
    } else if (view === "item_cards") {
      content = this._itemCardsSection(items);
    } else if (view === "item_detail") {
      content = this._itemDetailSection();
    }

    const embeddedClass = this._bool("embedded", false)
      ? "embedded"
      : "";
    const viewClass = `view-${view}`;

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <ha-card class="${embeddedClass} ${viewClass}">
        ${this._header(view)}
        ${this._message ? `<div class="message ${this._messageKind}">${this._esc(this._message)}</div>` : ""}
        ${content}
      </ha-card>`;

    this._bindEvents();
    this._restoreUiState();
    this._managerSignature = this._managerStateSignature(
      this._hass?.states?.[MSM_ENTITY]
    );
    this._pendingRender = false;
    this._restoreViewportScroll(viewportScroll);
  }

  _header(view) {
    if (!this._bool("show_header", view !== "item_cards")) return "";
    const defaults = {
      all: "Medication Stock Configuration",
      stock_table: "Medication and supply stock",
      stock_buttons: "Medication and supplies",
      item_configuration: "Item configuration",
      create_item: "New medication / item",
      create_owner: "New owner",
      sidebar_settings: "Sidebar settings",
      item_cards: "Medication and supplies",
      item_detail: "Medication or supply",
    };
    const descriptions = {
      all: "Stock, warning thresholds, usage, schedules, reminders, adding, and removing items.",
      stock_table: "Live stock and ordering status.",
      stock_buttons: "Interactive stock cards with ordering and stock controls.",
      item_configuration: "Configure stock, usage, schedules, reminders, and calendar assignment.",
      create_item: "Create a dynamically managed medication or medical supply.",
      create_owner: "Create and manage people who can own medication and supplies.",
      sidebar_settings: "Show, hide, and customize the integration-owned sidebar page.",
      item_cards: "Live medication and medical-supply status.",
      item_detail: "Live stock, schedule, order, and run-out information.",
    };
    const showRestore = this._bool(
      "show_restore_defaults",
      view === "all" || view === "item_configuration"
    );
    return `
      <div class="header">
        <div>
          <h1>${this._esc(this._config.title || defaults[view])}</h1>
          ${this._bool("show_description", true) ? `<p>${this._esc(this._config.description || descriptions[view])}</p>` : ""}
        </div>
        ${showRestore ? `<button class="danger" data-action="clear-all-items">Delete all items</button>` : ""}
      </div>`;
  }

  _captureUiState() {
    if (!this.shadowRoot.querySelector("ha-card")) return;

    this._openItems = new Set(
      [...this.shadowRoot.querySelectorAll("details[data-item-id][open]")]
        .map((details) => details.dataset.itemId)
        .filter(Boolean)
    );
    this._addItemOpen = Boolean(this.shadowRoot.querySelector("details.add-item[open]"));
    this._openOwners = new Set(
      [...this.shadowRoot.querySelectorAll("details.owner-card[data-owner-id][open]")]
        .map((details) => details.dataset.ownerId)
        .filter(Boolean)
    );
    this._newOwnerOpen = Boolean(
      this.shadowRoot.querySelector("details.owner-create-card[open]")
    );

    this.shadowRoot.querySelectorAll("[data-scroll-key]").forEach((element) => {
      this._scrollPositions.set(element.dataset.scrollKey, {
        left: element.scrollLeft,
        top: element.scrollTop,
      });
    });

    const active = this.shadowRoot.activeElement;
    if (!active || !["INPUT", "SELECT", "TEXTAREA"].includes(active.tagName)) {
      this._focusState = null;
      return;
    }

    const editor = active.closest(".editor");
    if (!editor) {
      this._focusState = null;
      return;
    }

    this._focusState = {
      editorId: editor.dataset.editor || "",
      field: active.dataset.field || "",
      add: active.dataset.add || "",
      day: active.dataset.day || "",
      addDay: active.dataset.addDay || "",
      selectionStart:
        typeof active.selectionStart === "number" ? active.selectionStart : null,
      selectionEnd:
        typeof active.selectionEnd === "number" ? active.selectionEnd : null,
    };
  }

  _restoreUiState() {
    for (const [id, draft] of this._drafts.entries()) {
      const editor = this.shadowRoot.querySelector(`[data-editor="${CSS.escape(id)}"]`);
      if (editor) this._applyDraft(editor, "field", draft);
    }

    const addEditor = this.shadowRoot.querySelector('[data-editor="new"]');
    if (addEditor) this._applyDraft(addEditor, "add", this._addDraft);

    this.shadowRoot.querySelectorAll(".editor").forEach((editor) => {
      this._updateScheduleVisibility(editor);
    });

    const restoreScroll = () => {
      this.shadowRoot.querySelectorAll("[data-scroll-key]").forEach((element) => {
        const position = this._scrollPositions.get(element.dataset.scrollKey);
        if (!position) return;
        element.scrollLeft = position.left;
        element.scrollTop = position.top;
      });
    };
    restoreScroll();
    requestAnimationFrame(restoreScroll);

    if (!this._focusState) return;
    const state = this._focusState;
    const editor = this.shadowRoot.querySelector(
      `[data-editor="${CSS.escape(state.editorId)}"]`
    );
    if (!editor) return;

    let selector = "";
    if (state.field) selector = `[data-field="${CSS.escape(state.field)}"]`;
    else if (state.add) selector = `[data-add="${CSS.escape(state.add)}"]`;
    else if (state.day) selector = `[data-day="${CSS.escape(state.day)}"]`;
    else if (state.addDay) selector = `[data-add-day="${CSS.escape(state.addDay)}"]`;

    const control = selector ? editor.querySelector(selector) : null;
    if (!control) return;
    control.focus({ preventScroll: true });
    if (
      state.selectionStart !== null &&
      state.selectionEnd !== null &&
      typeof control.setSelectionRange === "function"
    ) {
      try {
        control.setSelectionRange(state.selectionStart, state.selectionEnd);
      } catch (_error) {
        // Date and number controls may not support selection ranges.
      }
    }
  }

  _applyDraft(editor, prefix, draft) {
    if (!draft || typeof draft !== "object") return;
    for (const [field, value] of Object.entries(draft)) {
      if (field === "days") continue;
      const control = editor.querySelector(`[data-${prefix}="${CSS.escape(field)}"]`);
      if (!control) continue;
      if (control.type === "checkbox") control.checked = Boolean(value);
      else control.value = value ?? "";
    }

    if (Array.isArray(draft.days)) {
      const selector = prefix === "field" ? "[data-day]" : "[data-add-day]";
      editor.querySelectorAll(selector).forEach((checkbox) => {
        const value = prefix === "field" ? checkbox.dataset.day : checkbox.dataset.addDay;
        checkbox.checked = draft.days.includes(value);
      });
    }
  }

  _rememberDraft(event) {
    const control = event.target;
    const editor = control.closest(".editor");
    if (!editor) return;

    const editorId = editor.dataset.editor;
    const isNew = editorId === "new";
    const prefix = isNew ? "add" : "field";
    const field = control.dataset[prefix];
    const draft = isNew ? this._addDraft : { ...(this._drafts.get(editorId) || {}) };

    if (field) {
      draft[field] = control.type === "checkbox" ? control.checked : control.value;
    }

    if (control.dataset.day || control.dataset.addDay) {
      const selector = isNew ? "[data-add-day]" : "[data-day]";
      draft.days = [...editor.querySelectorAll(selector)]
        .filter((checkbox) => checkbox.checked)
        .map((checkbox) => (isNew ? checkbox.dataset.addDay : checkbox.dataset.day));
    }

    if (isNew) this._addDraft = draft;
    else this._drafts.set(editorId, draft);
  }

  _clearDraftField(id, field) {
    const draft = this._drafts.get(id);
    if (!draft || !(field in draft)) return;
    const next = { ...draft };
    delete next[field];
    if (Object.keys(next).length) this._drafts.set(id, next);
    else this._drafts.delete(id);
  }

  _scheduleMode(item) {
    if (item.schedule_mode !== "weekly") return item.schedule_mode || "manual";
    return new Set(item.days || []).size === MSM_ALL_DAYS.length
      ? "daily"
      : "selected_weekdays";
  }

  _category(item) {
    return MSM_SUPPLY_TYPES.has(item.item_type) ? "supply" : "medication";
  }

  _configuredItem() {
    const configuredEntity = String(this._config.entity || "");
    if (configuredEntity) {
      const state = this._hass?.states?.[configuredEntity];
      const itemId = state?.attributes?.item_id;
      if (itemId) {
        return this._items().find(
          (item) => item.id === itemId
        ) || null;
      }
    }

    const configuredItem = String(this._config.item_id || "");
    if (configuredItem) {
      return this._items().find(
        (item) => item.id === configuredItem
      ) || null;
    }

    return null;
  }

  _itemDetailSection() {
    const item = this._configuredItem();
    if (!item) {
      return `
        <section class="item-detail">
          <p class="muted">The medication or supply is unavailable.</p>
        </section>`;
    }

    const warning = item.low
      ? `
        <div class="detail-warning">
          ⚠️ <strong>Stock warning: ${
            item.ordered ? "check order" : "order a new supply"
          }.</strong>
        </div>
      `
      : `
        <div class="detail-ok">
          ✅ <strong>Stock is above its warning threshold.</strong>
        </div>
      `;

    const recurring = item.manual
      ? ""
      : `
        <p>Supply: <strong>${
          item.days_remaining ?? "—"
        } days</strong></p>
        <p>Order date: <strong>${
          this._esc(item.order_date || "—")
        }</strong></p>
        <p>Run-out date: <strong>${
          this._esc(item.run_out_date || "—")
        }</strong></p>
      `;

    const product = item.product_url
      ? `
        <p>
          <a
            href="${this._esc(item.product_url)}"
            target="_blank"
            rel="noopener noreferrer"
          >
            Open product page
          </a>
        </p>
      `
      : "";

    return `
      <section class="item-detail">
        <h2>${this._esc(item.stock_text)} ${this._esc(item.unit)}</h2>
        <p>
          Schedule:
          <strong>${this._esc(item.schedule_text)}</strong>
        </p>
        ${recurring}
        ${product}
        ${warning}
      </section>`;
  }

  _stockButtonsSection(items) {
    const ownerMode = this._config.owner || "all";
    const groupByOwner =
      ownerMode === "all" && this._bool("group_by_owner", true);

    if (!items.length) {
      return `<section class="stock-buttons"><div class="empty">No matching items.</div></section>`;
    }

    const renderCategory = (categoryItems, title, icon) => {
      if (!categoryItems.length) return "";
      return `
        <div class="stock-button-group">
          <div class="stock-button-heading">
            <ha-icon icon="${icon}"></ha-icon>
            <h2>${this._esc(title)}</h2>
            <span></span>
          </div>
          <div class="stock-button-list">
            ${categoryItems
              .map((item) => this._stockButton(item))
              .join("")}
          </div>
        </div>`;
    };

    const renderOwner = (ownerItems, ownerId) => {
      const ownerSuffix =
        ownerMode === "all"
          ? ` ${this._ownerName(ownerId)}`
          : ` ${this._ownerName(ownerMode)}`;
      const medications = ownerItems.filter(
        (item) => this._category(item) === "medication"
      );
      const supplies = ownerItems.filter(
        (item) => this._category(item) === "supply"
      );
      return [
        renderCategory(
          medications,
          `Medications${ownerSuffix}`,
          "mdi:calendar-month"
        ),
        renderCategory(
          supplies,
          `Medical Supplies${ownerSuffix}`,
          "mdi:medical-bag"
        ),
      ].join("");
    };

    let groups = "";
    if (groupByOwner) {
      for (const owner of this._owners()) {
        const ownerItems = items.filter(
          (item) => item.owner === owner.id
        );
        if (ownerItems.length) {
          groups += renderOwner(ownerItems, owner.id);
        }
      }
    } else {
      groups = renderOwner(items, ownerMode);
    }

    const active = items.find(
      (item) => item.id === this._activeStockItemId
    );
    if (!active && this._activeStockItemId) {
      this._activeStockItemId = null;
    }

    return `
      <section class="stock-buttons">
        ${groups}
      </section>
      ${active ? this._stockButtonModal(active) : ""}`;
  }

  _stockButton(item) {
    const recurringDetails = item.manual
      ? `<div class="stock-button-secondary">Manual</div>`
      : `
        <div class="stock-button-secondary">
          Order date: <strong>${this._esc(item.order_date || "—")}</strong>
        </div>
        <div class="stock-button-secondary">
          Run-out date: <strong>${this._esc(item.run_out_date || "—")}</strong>
        </div>
      `;

    const warning = item.low
      ? `
        <div class="stock-button-warning">
          ⚠️ Stock warning: ${
            item.ordered ? "check order." : "order a new supply."
          }
        </div>
      `
      : "";

    return `
      <button
        class="stock-button-card"
        data-action="open-stock-item"
        data-id="${this._esc(item.id)}"
      >
        <span class="stock-button-icon">
          <ha-icon icon="${this._esc(item.icon)}"></ha-icon>
        </span>
        <span class="stock-button-main">
          <strong>${this._esc(item.name)}</strong>
          <span>
            ${this._esc(this._num(item.stock))}
            ${this._esc(item.unit)}
          </span>
          ${recurringDetails}
          ${warning}
        </span>
        ${
          !item.manual && item.days_remaining !== null
            ? `
              <span class="stock-button-supply">
                <ha-icon icon="mdi:calendar-range"></ha-icon>
                <strong>${this._esc(item.days_remaining)} days</strong>
              </span>
            `
            : ""
        }
      </button>`;
  }

  _stockButtonModal(item) {
    return `
      <div class="stock-modal-backdrop" data-action="close-stock-item">
        <div class="stock-modal-panel" role="dialog" aria-modal="true">
          <div class="stock-modal-header">
            <div>
              <h2>${this._esc(item.name)}</h2>
              <p>${this._esc(item.owner_name || this._ownerName(item.owner))}</p>
            </div>
            <button
              class="stock-modal-close"
              data-action="close-stock-item"
              aria-label="Close"
            >×</button>
          </div>

          <div class="stock-modal-details">
            <h3>
              ${this._esc(this._num(item.stock))}
              ${this._esc(item.unit)}
            </h3>
            <p>
              Schedule:
              <strong>${this._esc(item.schedule_text)}</strong>
            </p>
            ${
              item.manual
                ? ""
                : `
                  <p>
                    Supply:
                    <strong>${this._esc(item.days_remaining ?? "—")} days</strong>
                  </p>
                  <p>
                    Order date:
                    <strong>${this._esc(item.order_date || "—")}</strong>
                  </p>
                  <p>
                    Run-out date:
                    <strong>${this._esc(item.run_out_date || "—")}</strong>
                  </p>
                `
            }
            ${
              item.product_url
                ? `<a href="${this._esc(item.product_url)}" target="_blank" rel="noopener noreferrer">Open product page</a>`
                : ""
            }
            ${
              item.low
                ? `
                  <div class="stock-modal-warning">
                    ⚠️ Stock warning: ${
                      item.ordered
                        ? "check order."
                        : "order a new supply."
                    }
                  </div>
                `
                : `<div class="stock-modal-ok">✅ Stock is above its warning threshold.</div>`
            }
          </div>

          <div class="stock-modal-actions">
            <button
              class="stock-action-large"
              data-action="receive"
              data-id="${this._esc(item.id)}"
            >
              <ha-icon icon="mdi:package-variant-plus"></ha-icon>
              <span>Received Box</span>
            </button>
            <button
              class="stock-action-large"
              data-action="ordered"
              data-id="${this._esc(item.id)}"
              data-ordered="${item.ordered ? "true" : "false"}"
            >
              <ha-icon icon="mdi:package-check"></ha-icon>
              <span>${item.ordered ? "Clear Ordered" : "Ordered Box"}</span>
            </button>
            <div class="stock-action-row">
              <button
                data-action="adjust"
                data-id="${this._esc(item.id)}"
                data-amount="-1"
              >
                <ha-icon icon="mdi:minus-circle"></ha-icon>
                <span>-1</span>
              </button>
              <button
                data-action="adjust"
                data-id="${this._esc(item.id)}"
                data-amount="1"
              >
                <ha-icon icon="mdi:plus-circle"></ha-icon>
                <span>+1</span>
              </button>
            </div>
          </div>
        </div>
      </div>`;
  }

  _createOwnerSection() {
    const showExisting = this._bool("show_existing_owners", true);
    return `
      <section class="owner-section">
        ${
          showExisting
            ? `
              <div class="owner-list">
                ${this._owners()
                  .map((owner) => this._ownerEditor(owner))
                  .join("")}
              </div>
            `
            : ""
        }
        <details class="owner-card owner-create-card" ${this._newOwnerOpen ? "open" : ""}>
          <summary>
            <strong>New Owner</strong>
            <ha-icon class="owner-add-icon" icon="mdi:plus"></ha-icon>
          </summary>
          <div class="owner-editor owner-create">
          <div class="owner-grid">
            <div class="field">
              <label>Name</label>
              <input data-owner-add="name" placeholder="Person or profile name">
            </div>
            <div class="field">
              <label>Owner ID</label>
              <input data-owner-add="owner_id" placeholder="Generated from name">
            </div>
            <div class="field wide">
              <label>Home Assistant Person</label>
              <select data-owner-add="person_entity">${this._personOptions("")}</select>
            </div>
            <div class="owner-auto-row wide">
              <label><input type="checkbox" data-owner-add="auto_create_person" checked> Create a Home Assistant Person when no match exists</label>
              <label><input type="checkbox" data-owner-add="auto_detect_notify" checked> Detect mobile notify entities from the Person's tracked device</label>
            </div>
            <div class="integration-owned-note wide">
              The medication calendar and control switches are created automatically under this integration.
            </div>
            <div class="field wide">
              <label>Reminder notification entities</label>
              <input data-owner-add="reminder_notify_entities" placeholder="notify.phone">
            </div>
            <div class="field wide">
              <label>Stock notification entities</label>
              <input data-owner-add="stock_notify_entities" placeholder="notify.phone, notify.second_phone">
            </div>
            <div class="owner-auto-row wide">
              <label><input type="checkbox" data-owner-add="tracking_enabled" checked> Stock warnings enabled</label>
              <label><input type="checkbox" data-owner-add="reminders_enabled" checked> Medication reminders enabled</label>
            </div>
            <div class="field wide">
              <label>Default medication reminder title</label>
              <input data-owner-add="default_reminder_title" value="Medication Reminder">
            </div>
            <div class="field wide">
              <label>Order reminder title</label>
              <input data-owner-add="order_title" value="Order Medication">
            </div>
            <div class="field wide">
              <label>Check-order reminder title</label>
              <input data-owner-add="check_order_title" value="Check Medication Order">
            </div>
            <div class="actions wide">
              <button class="primary" data-action="add-owner">
                Create owner
              </button>
            </div>
          </div>
          </div>
        </details>
      </section>`;
  }

  _ownerEditor(owner) {
    return `
      <details class="owner-card" data-owner-id="${this._esc(owner.id)}" ${this._openOwners.has(owner.id) ? "open" : ""}>
        <summary>
          <strong>${this._esc(owner.name)}</strong>
          <span>${this._esc(owner.id)}</span>
        </summary>
        <div
          class="owner-editor owner-grid"
          data-owner-editor="${this._esc(owner.id)}"
        >
          <div class="field">
            <label>Name</label>
            <input data-owner-field="name" value="${this._esc(owner.name)}">
          </div>
          <div class="field">
            <label>Owner ID</label>
            <input value="${this._esc(owner.id)}" disabled>
          </div>
          <div class="field wide">
            <label>Home Assistant Person</label>
            <select data-owner-field="person_entity">${this._personOptions(owner.person_entity || "")}</select>
          </div>
          <div class="owner-auto-row wide">
            <label><input type="checkbox" data-owner-field="auto_create_person" ${owner.auto_create_person !== false ? "checked" : ""}> Create missing Person</label>
            <label><input type="checkbox" data-owner-field="auto_detect_notify" ${owner.auto_detect_notify !== false ? "checked" : ""}> Auto-detect mobile notify entities</label>
          </div>
          <div class="integration-owned-note wide">
            Integration calendar: <strong>${this._esc(owner.calendar_entity || "Created automatically")}</strong>
          </div>
          <div class="field wide">
            <label>Reminder notification entities</label>
            <input data-owner-field="reminder_notify_entities" value="${this._esc((owner.reminder_notify_entities || []).join(", "))}">
          </div>
          <div class="field wide">
            <label>Stock notification entities</label>
            <input data-owner-field="stock_notify_entities" value="${this._esc((owner.stock_notify_entities || []).join(", "))}">
          </div>
          <div class="owner-auto-row wide">
            <label><input type="checkbox" data-owner-field="tracking_enabled" ${owner.tracking_enabled !== false ? "checked" : ""}> Stock warnings enabled</label>
            <label><input type="checkbox" data-owner-field="reminders_enabled" ${owner.reminders_enabled !== false ? "checked" : ""}> Medication reminders enabled</label>
          </div>
          <div class="field wide">
            <label>Default medication reminder title</label>
            <input data-owner-field="default_reminder_title" value="${this._esc(owner.default_reminder_title || "")}">
          </div>
          <div class="field wide">
            <label>Order reminder title</label>
            <input data-owner-field="order_title" value="${this._esc(owner.order_title || "")}">
          </div>
          <div class="field wide">
            <label>Check-order reminder title</label>
            <input data-owner-field="check_order_title" value="${this._esc(owner.check_order_title || "")}">
          </div>
          <div class="actions wide">
            <button
              class="primary"
              data-action="save-owner"
              data-owner-id="${this._esc(owner.id)}"
            >Save owner</button>
            <button
              class="danger"
              data-action="remove-owner"
              data-owner-id="${this._esc(owner.id)}"
            >Remove owner</button>
          </div>
        </div>
      </details>`;
  }

  _sidebarSettingsSection() {
    const settings =
      this._hass?.states?.[MSM_ENTITY]?.attributes?.sidebar || {};
    const enabled = settings.show_sidebar_panel !== false;
    const requireAdmin = settings.sidebar_require_admin !== false;

    return `
      <section class="sidebar-settings">
        <div class="sidebar-settings-grid">
          <div class="field">
            <label>Sidebar title</label>
            <input
              data-sidebar-setting="sidebar_title"
              value="${this._esc(
                settings.sidebar_title || "Medication Stock"
              )}"
            >
          </div>

          <div class="field">
            <label>Sidebar icon</label>
            <input
              data-sidebar-setting="sidebar_icon"
              value="${this._esc(
                settings.sidebar_icon || "mdi:medical-bag"
              )}"
              placeholder="mdi:medical-bag"
            >
          </div>

          <label class="sidebar-toggle">
            <input
              type="checkbox"
              data-sidebar-setting="show_sidebar_panel"
              ${enabled ? "checked" : ""}
            >
            <span>
              <strong>Show Medication Stock in the sidebar</strong>
              <small>
                This switch is also available under the integration device.
              </small>
            </span>
          </label>

          <label class="sidebar-toggle">
            <input
              type="checkbox"
              data-sidebar-setting="sidebar_require_admin"
              ${requireAdmin ? "checked" : ""}
            >
            <span>
              <strong>Administrators only</strong>
              <small>
                Disable this to allow non-admin Home Assistant users to open
                the sidebar page.
              </small>
            </span>
          </label>

          <div class="actions wide">
            <button
              class="primary"
              data-action="save-sidebar-settings"
            >
              Save sidebar settings
            </button>
          </div>
        </div>
      </section>`;
  }

  _collectSidebarSettings() {
    const result = {};
    this.shadowRoot
      .querySelectorAll("[data-sidebar-setting]")
      .forEach((element) => {
        const key = element.dataset.sidebarSetting;
        result[key] =
          element.type === "checkbox"
            ? element.checked
            : element.value;
      });
    return result;
  }

  _stockTableSection(items, title, keySuffix) {
    if (!items.length && !this._bool("show_empty", true)) return "";
    const columns = this._array("columns", MSM_DEFAULT_COLUMNS);
    const allowed = new Set([
      "name",
      "owner",
      "type",
      "stock",
      "threshold",
      "usage",
      "schedule",
      "supply",
      "order_date",
      "run_out_date",
      "status",
    ]);
    const selected = columns.filter((column) => allowed.has(column));
    const finalColumns = selected.length ? selected : MSM_DEFAULT_COLUMNS;
    const scrollKey =
      this._config.scroll_key ||
      `stock-${keySuffix}-${finalColumns.join("-")}`;
    const horizontalScroll = this._bool("horizontal_scroll", false);
    const ownerClass = finalColumns.includes("owner")
      ? " with-owner"
      : "";
    const tableClass = horizontalScroll
      ? "table-wrap scroll-enabled"
      : `table-wrap compact-table${ownerClass}`;

    return `
      <section class="stock-section">
        ${
          this._bool("show_section_title", true)
            ? `<h2>${this._esc(title)}</h2>`
            : ""
        }
        <div
          class="${tableClass}"
          data-scroll-key="${this._esc(scrollKey)}"
        >
          <table>
            <thead>
              <tr>
                ${finalColumns
                  .map(
                    (column) =>
                      `<th class="col-${this._esc(column)}">` +
                      `${this._esc(this._columnTitle(column))}</th>`
                  )
                  .join("")}
              </tr>
            </thead>
            <tbody>
              ${
                items.length
                  ? items
                      .map(
                        (item) =>
                          `<tr>${finalColumns
                            .map(
                              (column) =>
                                `<td class="col-${this._esc(column)}">` +
                                `${this._tableCell(item, column)}</td>`
                            )
                            .join("")}</tr>`
                      )
                      .join("")
                  : `<tr><td colspan="${finalColumns.length}" class="muted">No items</td></tr>`
              }
            </tbody>
          </table>
        </div>
      </section>`;
  }

  _columnTitle(column) {
    return {
      name: "Medication / item",
      owner: "Owner",
      type: "Type",
      stock: "Stock",
      threshold: "Threshold",
      usage: "Usage / day",
      schedule: "Schedule",
      supply: "Supply",
      order_date: "Order date",
      run_out_date: "Run-out date",
      status: "Status",
    }[column];
  }

  _tableCell(item, column) {
    const values = {
      name: `<strong>${this._esc(item.name)}</strong>`,
      owner: this._esc(item.owner_name || this._ownerName(item.owner)),
      type: this._esc(item.item_type.replaceAll("_", " ")),
      stock: `${this._esc(this._num(item.stock))} ${this._esc(item.unit)}`,
      threshold: `${this._esc(this._num(item.threshold))} ${this._esc(item.unit)}`,
      usage: item.manual ? "Manual" : `${this._esc(this._num(item.usage_per_day))} ${this._esc(item.unit)}`,
      schedule: this._esc(item.schedule_text),
      supply:
        item.manual || item.days_remaining === null
          ? "Manual"
          : `${this._esc(item.days_remaining)} days`,
      order_date: this._esc(item.order_date || "—"),
      run_out_date: this._esc(item.run_out_date || "—"),
      status: item.low ? (item.ordered ? "⚠️ Check order" : "⚠️ Order") : "✅ OK",
    };
    return values[column] ?? "";
  }

  _configurationSection(items) {
    return `
      <section>
        ${this._bool("show_section_title", (this._config.view || "all") === "all") ? `<h2>${this._esc(this._config.section_title || "Item configuration")}</h2>` : ""}
        ${this._bool("show_help", true) ? `<p class="section-note">Usage is the total amount used on each active day and is divided evenly over its configured times. A usage value of <strong>0</strong> is treated as manual.</p>` : ""}
        <div class="items">
          ${items.length ? items.map((item) => this._itemEditor(item)).join("") : `<div class="empty">No matching items.</div>`}
        </div>
      </section>`;
  }

  _itemCardsSection(items) {
    const groupBy = String(this._config.group_by || "category");
    if (groupBy === "none") {
      return `<section class="home-items"><div class="home-list">${items.map((item) => this._homeItem(item)).join("")}</div></section>`;
    }

    const medication = items.filter((item) => this._category(item) === "medication");
    const supplies = items.filter((item) => this._category(item) === "supply");
    const ownerLabel =
      this._config.owner === "all"
        ? "All"
        : this._ownerName(this._config.owner);
    return `
      <section class="home-items">
        ${medication.length ? `<div class="group-heading"><ha-icon icon="mdi:calendar-month"></ha-icon><h2>Medications ${this._esc(ownerLabel)}</h2><span></span></div><div class="home-list">${medication.map((item) => this._homeItem(item)).join("")}</div>` : ""}
        ${supplies.length ? `<div class="group-heading"><ha-icon icon="mdi:medical-bag"></ha-icon><h2>Medical Supplies ${this._esc(ownerLabel)}</h2><span></span></div><div class="home-list">${supplies.map((item) => this._homeItem(item)).join("")}</div>` : ""}
        ${!items.length ? `<div class="empty">No matching items.</div>` : ""}
      </section>`;
  }

  _homeItem(item) {
    const showActions = this._bool("show_actions", true);
    const showDates = this._bool("show_dates", true);
    const showSchedule = this._bool("show_schedule", true);
    const showProduct = this._bool("show_product_url", true);
    return `
      <details class="home-item" data-item-id="${this._esc(item.id)}" ${this._openItems.has(item.id) ? "open" : ""}>
        <summary>
          <div class="home-icon"><ha-icon icon="${this._esc(item.icon)}"></ha-icon></div>
          <div class="home-main">
            <strong>${this._esc(item.name)}</strong>
            <div>${this._esc(this._num(item.stock))} ${this._esc(item.unit)}</div>
            ${showDates && !item.manual ? `<small>Order date: ${this._esc(item.order_date || "—")}<br>Run-out date: ${this._esc(item.run_out_date || "—")}</small>` : ""}
            ${showSchedule && item.manual ? `<small>Manual</small>` : ""}
            ${item.low ? `<div class="warning">⚠️ ${item.ordered ? "Stock warning: check order." : "Stock warning: order a new supply."}</div>` : ""}
          </div>
          ${!item.manual && item.days_remaining !== null ? `<div class="home-supply"><ha-icon icon="mdi:calendar-range"></ha-icon><strong>${this._esc(item.days_remaining)} days</strong></div>` : ""}
        </summary>
        <div class="home-details">
          ${showSchedule ? `<div><strong>Schedule:</strong> ${this._esc(item.schedule_text)}</div>` : ""}
          <div><strong>Warning threshold:</strong> ${this._esc(this._num(item.threshold))} ${this._esc(item.unit)}</div>
          ${showProduct && item.product_url ? `<a href="${this._esc(item.product_url)}" target="_blank" rel="noreferrer">Open product page</a>` : ""}
          ${showActions ? this._actionButtons(item) : ""}
        </div>
      </details>`;
  }

  _fieldEnabled(field) {
    const fields = this._array("fields", MSM_DEFAULT_FIELDS);
    return fields.includes(field);
  }

  _itemEditor(item) {
    const mode = this._scheduleMode(item);
    const typeOptions = Object.keys(MSM_TYPES)
      .map((type) => `<option value="${type}" ${item.item_type === type ? "selected" : ""}>${this._esc(type.replaceAll("_", " "))}</option>`)
      .join("");
    const ownerOptions = this._ownerOptions(item.owner);
    const scheduleOptions = MSM_SCHEDULES
      .map(([value, label]) => `<option value="${value}" ${mode === value ? "selected" : ""}>${label}</option>`)
      .join("");

    const field = (name, html, classes = "") =>
      this._fieldEnabled(name) ? `<div class="field ${classes}" data-config-field="${name}">${html}</div>` : "";

    return `
      <details class="item" data-item-id="${this._esc(item.id)}" ${this._openItems.has(item.id) ? "open" : ""}>
        <summary>
          <div class="summary-main">
            <span class="status-dot ${item.low ? "low" : "ok"}"></span>
            <span><strong>${this._esc(item.name)}</strong><small>${this._esc(item.owner_name || this._ownerName(item.owner))} · ${this._esc(this._num(item.stock))} ${this._esc(item.unit)}</small></span>
          </div>
          <span class="summary-status">${item.low ? (item.ordered ? "Check order" : "Order") : "OK"}</span>
        </summary>
        <div class="editor" data-editor="${this._esc(item.id)}" data-schedule-mode="${this._esc(mode)}">
          ${field("name", `<label>Name</label><input data-field="name" value="${this._esc(item.name)}">`, "wide")}
          ${field("owner", `<label>Owner</label><select data-field="owner">${ownerOptions}</select>`)}
          ${field("item_type", `<label>Type</label><select data-field="item_type">${typeOptions}</select>`)}
          ${field("unit", `<label>Unit / custom type</label><input data-field="unit" value="${this._esc(item.unit)}">`)}
          ${field("icon", `<label>Icon</label><input data-field="icon" value="${this._esc(item.icon)}">`)}
          ${field("stock", `<label>Current stock</label><input type="number" min="0" step="0.001" data-field="stock" value="${this._esc(this._num(item.stock))}">`, "metric-field")}
          ${field("threshold", `<label>Warning threshold</label><input type="number" min="0" step="0.001" data-field="threshold" value="${this._esc(this._num(item.threshold))}">`, "metric-field")}
          ${field("package_size", `<label>Package / box size</label><input type="number" min="0" step="0.001" data-field="package_size" value="${this._esc(this._num(item.package_size))}">`, "metric-field")}
          ${field("usage_per_day", `<label>Usage per active day</label><input type="number" min="0" step="0.001" data-field="usage_per_day" value="${this._esc(this._num(item.usage_per_day))}">`, "metric-field")}
          ${field("schedule_mode", `<label>Schedule type</label><select data-field="schedule_mode">${scheduleOptions}</select>`, "schedule-mode")}
          ${field("times", `<label>Times</label><input data-field="times" placeholder="08:00, 20:00" value="${this._esc((item.times || []).join(", "))}">`, "schedule-times schedule-nonmanual")}
          ${field("days", `<label>Active weekdays</label><div class="days">${MSM_DAYS.map(([value, label]) => `<label class="day"><input type="checkbox" data-day="${value}" ${(item.days || []).includes(value) ? "checked" : ""}>${label}</label>`).join("")}</div>`, "wide schedule-weekdays schedule-options")}
          ${field("interval_days", `<label>Every X days</label><input type="number" min="1" step="1" data-field="interval_days" value="${this._esc(item.interval_days || 1)}">`, "schedule-half schedule-interval")}
          ${field("start_date", `<label>Interval start date</label><input type="date" data-field="start_date" value="${this._esc(item.start_date || "")}">`, "schedule-half schedule-interval")}
          ${(this._fieldEnabled("enabled") || this._fieldEnabled("reminder_enabled")) ? `
            <div class="schedule-checkbox-row">
              ${this._fieldEnabled("enabled") ? `<label><input type="checkbox" data-field="enabled" ${item.enabled ? "checked" : ""}> Automatic stock management enabled</label>` : ""}
              ${this._fieldEnabled("reminder_enabled") ? `<label><input type="checkbox" data-field="reminder_enabled" ${item.reminder_enabled ? "checked" : ""}> Send reminders at configured times</label>` : ""}
            </div>` : ""}
          ${field("reminder_title", `<label>Reminder title</label><input data-field="reminder_title" value="${this._esc(item.reminder_title || "")}">`, "wide reminder-field")}
          ${field("reminder_message", `<label>Reminder description</label><input data-field="reminder_message" value="${this._esc(item.reminder_message || "")}">`, "wide reminder-field")}
          ${field("product_url", `<label>Product URL</label><input data-field="product_url" value="${this._esc(item.product_url || "")}">`, "wide")}
          <div class="computed wide">
            <span><strong>Schedule:</strong> ${this._esc(item.schedule_text)}</span>
            <span><strong>Order date:</strong> ${this._esc(item.order_date || "—")}</span>
            <span><strong>Run-out date:</strong> ${this._esc(item.run_out_date || "—")}</span>
          </div>
          <div class="actions wide">
            <button class="primary" data-action="save" data-id="${this._esc(item.id)}">Save configuration</button>
            ${this._bool("show_actions", true) ? this._actionButtons(item, true) : ""}
            ${this._bool("show_remove", true) ? `<button class="danger" data-action="remove" data-id="${this._esc(item.id)}">Remove item</button>` : ""}
          </div>
        </div>
      </details>`;
  }

  _actionButtons(item, inline = false) {
    return `${inline ? "" : '<div class="actions home-actions">'}
      <button data-action="receive" data-id="${this._esc(item.id)}">Received Box</button>
      <button data-action="ordered" data-id="${this._esc(item.id)}" data-ordered="${item.ordered ? "true" : "false"}">${item.ordered ? "Clear Ordered" : "Ordered Box"}</button>
      <button data-action="adjust" data-id="${this._esc(item.id)}" data-amount="-1">−1</button>
      <button data-action="adjust" data-id="${this._esc(item.id)}" data-amount="1">+1</button>
      ${inline ? "" : "</div>"}`;
  }

  _addItemForm(alwaysOpen) {
    const owners = this._owners();
    if (!owners.length) {
      return `
        <section class="create-section">
          <div class="empty">
            Create an owner before creating medication or supplies.
          </div>
        </section>`;
    }

    const configuredOwner = String(
      this._config.default_owner || this._config.owner || ""
    ).toLowerCase();
    const owner = owners.some(
      (entry) => entry.id === configuredOwner
    )
      ? configuredOwner
      : owners[0].id;
    const lockedOwner =
      this._bool("lock_owner", false) &&
      this._config.owner !== "all";
    const open = alwaysOpen || this._addItemOpen;
    const defaultType = String(this._config.default_type || "capsule");
    const defaultUnit = String(this._config.default_unit || MSM_TYPES[defaultType] || "items");
    const defaultSchedule = String(this._config.default_schedule || "manual");
    const form = `
      <div class="editor" data-editor="new">
        <div class="field wide"><label>Name</label><input data-add="name" placeholder="Medication or supply name"></div>
        ${lockedOwner
          ? `<input type="hidden" data-add="owner" value="${this._esc(owner)}">`
          : `<div class="field"><label>Owner</label><select data-add="owner">${this._ownerOptions(owner)}</select></div>`
        }
        <div class="field"><label>Type</label><select data-add="item_type">${Object.keys(MSM_TYPES).map((type) => `<option value="${type}" ${type === defaultType ? "selected" : ""}>${this._esc(type.replaceAll("_", " "))}</option>`).join("")}</select></div>
        <div class="field"><label>Unit / custom type</label><input data-add="unit" value="${this._esc(defaultUnit)}"></div>
        <div class="field"><label>Icon</label><input data-add="icon" value="${this._esc(this._config.default_icon || "mdi:pill")}"></div>
        <div class="field metric-field"><label>Current stock</label><input type="number" min="0" step="0.001" data-add="stock" value="0"></div>
        <div class="field metric-field"><label>Warning threshold</label><input type="number" min="0" step="0.001" data-add="threshold" value="0"></div>
        <div class="field metric-field"><label>Package / box size</label><input type="number" min="0" step="0.001" data-add="package_size" value="0"></div>
        <div class="field metric-field"><label>Usage per active day</label><input type="number" min="0" step="0.001" data-add="usage_per_day" value="0"></div>
        <div class="field schedule-mode"><label>Schedule type</label><select data-add="schedule_mode">${MSM_SCHEDULES.map(([value, label]) => `<option value="${value}" ${value === defaultSchedule ? "selected" : ""}>${label}</option>`).join("")}</select></div>
        <div class="field schedule-times schedule-nonmanual"><label>Times</label><input data-add="times" placeholder="08:00, 20:00"></div>
        <div class="field wide schedule-weekdays schedule-options"><label>Active weekdays</label><div class="days">${MSM_DAYS.map(([value, label]) => `<label class="day"><input type="checkbox" data-add-day="${value}" checked>${label}</label>`).join("")}</div></div>
        <div class="field schedule-half schedule-interval"><label>Every X days</label><input type="number" min="1" step="1" data-add="interval_days" value="1"></div>
        <div class="field schedule-half schedule-interval"><label>Interval start date</label><input type="date" data-add="start_date" value="${new Date().toISOString().slice(0, 10)}"></div>
        <div class="schedule-checkbox-row">
          <label><input type="checkbox" data-add="enabled" checked> Automatic stock management enabled</label>
          <label><input type="checkbox" data-add="reminder_enabled"> Send reminders at configured times</label>
        </div>
        <div class="field wide reminder-field"><label>Reminder title</label><input data-add="reminder_title"></div>
        <div class="field wide reminder-field"><label>Reminder description</label><input data-add="reminder_message"></div>
        <div class="field wide"><label>Product URL</label><input data-add="product_url"></div>
        <div class="actions wide"><button class="primary" data-action="add">Create item</button></div>
      </div>`;

    if (alwaysOpen) return `<section class="create-section">${form}</section>`;
    return `
      <section>
        <details class="add-item" ${open ? "open" : ""}>
          <summary><strong>＋ New medication / item</strong></summary>
          ${form}
        </details>
      </section>`;
  }

  _updateScheduleVisibility(editor) {
    const isNew = editor.dataset.editor === "new";
    const prefix = isNew ? "add" : "field";
    const mode = editor.querySelector(`[data-${prefix}="schedule_mode"]`)?.value || editor.dataset.scheduleMode || "manual";
    editor.querySelectorAll(".schedule-nonmanual").forEach((element) => {
      element.hidden = mode === "manual";
    });
    editor.querySelectorAll(".schedule-weekdays").forEach((element) => {
      element.hidden = mode !== "selected_weekdays";
    });
    editor.querySelectorAll(".schedule-interval").forEach((element) => {
      element.hidden = mode !== "interval";
    });
  }

  _bindEvents() {
    this.shadowRoot.querySelectorAll("details[data-item-id]").forEach((details) => {
      details.addEventListener("toggle", () => {
        const id = details.dataset.itemId;
        if (!id) return;
        if (details.open) this._openItems.add(id);
        else this._openItems.delete(id);
      });
    });

    this.shadowRoot.querySelectorAll("details.owner-card[data-owner-id]").forEach((details) => {
      details.addEventListener("toggle", () => {
        const ownerId = details.dataset.ownerId;
        if (!ownerId) return;
        if (details.open) this._openOwners.add(ownerId);
        else this._openOwners.delete(ownerId);
      });
    });

    const newOwnerDetails = this.shadowRoot.querySelector(
      "details.owner-create-card"
    );
    newOwnerDetails?.addEventListener("toggle", () => {
      this._newOwnerOpen = newOwnerDetails.open;
    });

    const addDetails = this.shadowRoot.querySelector("details.add-item");
    addDetails?.addEventListener("toggle", () => {
      this._addItemOpen = addDetails.open;
    });

    this.shadowRoot.querySelectorAll(".editor").forEach((editor) => {
      editor.addEventListener("input", (event) => {
        this._rememberDraft(event);
        this._handleScheduleInput(editor, event.target);
      });
      editor.addEventListener("change", (event) => {
        this._rememberDraft(event);
        this._handleScheduleInput(editor, event.target);
      });
      editor.addEventListener("focusout", () => {
        if (!this._pendingRender) return;
        setTimeout(() => {
          const active = this.shadowRoot.activeElement;
          if (!active || !["INPUT", "SELECT", "TEXTAREA"].includes(active.tagName)) {
            this._render();
          }
        }, 0);
      });
    });

    this.shadowRoot.querySelectorAll("button[data-action], [data-action].stock-modal-backdrop").forEach((button) => {
      button.addEventListener("click", (event) => this._handleAction(event));
    });

    this.shadowRoot.querySelector(".stock-modal-panel")?.addEventListener(
      "click",
      (event) => event.stopPropagation()
    );

    this.shadowRoot.querySelectorAll('select[data-owner-add="person_entity"], select[data-owner-field="person_entity"]').forEach((select) => {
      select.addEventListener("change", () => {
        const suggestion = this._personSuggestion(select.value);
        if (!suggestion) return;
        const container = select.closest(".owner-editor");
        if (!container) return;
        const prefix = select.hasAttribute("data-owner-add")
          ? "data-owner-add"
          : "data-owner-field";
        const name = container.querySelector(`[${prefix}="name"]`);
        const reminders = container.querySelector(`[${prefix}="reminder_notify_entities"]`);
        const stock = container.querySelector(`[${prefix}="stock_notify_entities"]`);
        if (name && !name.value.trim()) name.value = suggestion.name || "";
        const detected = (suggestion.notify_entities || []).join(", ");
        if (reminders && !reminders.value.trim()) reminders.value = detected;
        if (stock && !stock.value.trim()) stock.value = detected;
      });
    });

    this.shadowRoot.querySelectorAll('select[data-add="item_type"]').forEach((select) => {
      select.addEventListener("change", (event) => {
        if (select.value === "custom") return;
        const editor = select.closest(".editor");
        const unit = editor?.querySelector('input[data-add="unit"]');
        if (unit) {
          unit.value = MSM_TYPES[select.value] || "items";
          this._rememberDraft({ target: unit });
        }
      });
    });

    this.shadowRoot.querySelectorAll('select[data-field="item_type"]').forEach((select) => {
      select.addEventListener("change", () => {
        if (select.value === "custom") return;
        const editor = select.closest(".editor");
        const unit = editor?.querySelector('input[data-field="unit"]');
        if (unit) {
          unit.value = MSM_TYPES[select.value] || "items";
          this._rememberDraft({ target: unit });
        }
      });
    });
  }

  _handleScheduleInput(editor, control) {
    const isNew = editor.dataset.editor === "new";
    const prefix = isNew ? "add" : "field";
    const schedule = editor.querySelector(`[data-${prefix}="schedule_mode"]`);
    const usage = editor.querySelector(`[data-${prefix}="usage_per_day"]`);

    if (control === usage) {
      if (Number(usage.value || 0) <= 0) schedule.value = "manual";
      else if (schedule.value === "manual") schedule.value = "daily";
      this._rememberDraft({ target: schedule });
    }

    if (control === schedule && schedule.value === "manual") {
      usage.value = "0";
      this._rememberDraft({ target: usage });
    }

    if (control === schedule || control === usage) {
      this._updateScheduleVisibility(editor);
    }
  }

  _optimisticItem(itemId) {
    return this._items().find((item) => item.id === itemId) || null;
  }

  _applyOptimisticStock(itemId, value) {
    this._optimisticStock.set(itemId, Math.max(Number(value || 0), 0));
    this._render();
  }

  _applyOptimisticOrdered(itemId, ordered) {
    this._optimisticOrdered.set(itemId, Boolean(ordered));
    this._render();
  }

  async _handleAction(event) {
    event.preventDefault();
    event.stopPropagation();
    const button = event.currentTarget;
    const action = button.dataset.action;
    const id = button.dataset.id;

    try {
      if ("disabled" in button) button.disabled = true;

      if (action === "open-stock-item") {
        this._activeStockItemId = id;
        this._render();
        return;
      }
      if (action === "close-stock-item") {
        this._activeStockItemId = null;
        this._render();
        return;
      }
      if (action === "save") await this._saveItem(id);
      if (action === "add") await this._addItem();
      if (action === "receive" && confirm("Add one received package to this item's stock?")) {
        const item = this._optimisticItem(id);
        if (item) {
          this._optimisticStock.set(
            id,
            Number(item.stock || 0) + Number(item.package_size || 0)
          );
          this._optimisticOrdered.set(id, false);
          this._render();
        }
        await this._service("receive_box", { item_id: id });
        this._clearDraftField(id, "stock");
        this._setMessage("Received package added.");
      }
      if (action === "ordered") {
        const currentlyOrdered = button.dataset.ordered === "true";
        const prompt = currentlyOrdered ? "Clear the ordered status?" : "Mark this item as ordered?";
        if (confirm(prompt)) {
          this._optimisticOrdered.set(id, !currentlyOrdered);
          this._render();
          await this._service("set_ordered", { item_id: id, ordered: !currentlyOrdered });
          this._setMessage(currentlyOrdered ? "Ordered status cleared." : "Item marked as ordered.");
        }
      }
      if (action === "adjust") {
        const amount = Number(button.dataset.amount);
        const item = this._optimisticItem(id);
        if (item) {
          this._optimisticStock.set(
            id,
            Math.max(Number(item.stock || 0) + amount, 0)
          );
          this._render();
        }
        await this._service("adjust_stock", { item_id: id, amount });
        this._clearDraftField(id, "stock");
      }
      if (
        action === "remove" &&
        confirm("Remove this item? Its generated medication schedule and stock calendar events will also be removed.")
      ) {
        await this._service("remove_item", { item_id: id });
        this._drafts.delete(id);
        this._openItems.delete(id);
        this._setMessage("Item and generated calendar events removed.");
      }
      if (
        action === "clear-all-items" &&
        confirm(
          "Permanently delete every medication and supply item? " +
          "Generated calendar entries will also be removed. " +
          "Owner profiles will remain."
        )
      ) {
        await this._service("clear_all_items", {});
        this._activeStockItemId = null;
        this._setMessage("All medication and supply items were deleted.");
      }
      if (action === "save-sidebar-settings") {
        const settings = this._collectSidebarSettings();
        await this._service("set_sidebar_options", settings);
        this._setMessage("Sidebar settings saved.");
      }
      if (action === "add-owner") {
        await this._addOwner();
      }
      if (action === "save-owner") {
        await this._saveOwner(button.dataset.ownerId);
      }
      if (
        action === "remove-owner" &&
        confirm("Remove this owner? The owner must have no assigned items.")
      ) {
        await this._service("remove_owner", {
          owner_id: button.dataset.ownerId,
        });
        this._setMessage("Owner removed.");
      }
    } catch (error) {
      this._optimisticStock.clear();
      this._optimisticOrdered.clear();
      console.error(error);
      this._setMessage(error?.message || "The action failed.", "error");
    } finally {
      if ("disabled" in button) button.disabled = false;
    }
  }

  _collectOwnerFields(container, attribute) {
    const result = {};
    container.querySelectorAll(`[${attribute}]`).forEach((element) => {
      const field = element.getAttribute(attribute);
      if (!field) return;
      result[field] = element.type === "checkbox"
        ? element.checked
        : element.value;
    });
    return result;
  }

  async _addOwner() {
    const container = this.shadowRoot.querySelector(".owner-create");
    if (!container) return;
    const data = this._collectOwnerFields(
      container,
      "data-owner-add"
    );
    if (!String(data.name || "").trim()) {
      throw new Error("Owner name is required.");
    }
    await this._service("add_owner", data);
    this._setMessage(`Created owner ${data.name}.`);
  }

  async _saveOwner(ownerId) {
    const container = this.shadowRoot.querySelector(
      `[data-owner-editor="${CSS.escape(ownerId)}"]`
    );
    if (!container) return;
    const data = this._collectOwnerFields(
      container,
      "data-owner-field"
    );
    await this._service("update_owner", {
      owner_id: ownerId,
      ...data,
    });
    this._setMessage(`Saved owner ${data.name || ownerId}.`);
  }

  _collectEditor(editor, prefix) {
    const result = {};
    editor.querySelectorAll(`[data-${prefix}]`).forEach((element) => {
      const field = element.dataset[prefix];
      if (!field) return;
      if (element.type === "checkbox") result[field] = element.checked;
      else if (element.type === "number") result[field] = Number(element.value || 0);
      else result[field] = element.value;
    });

    const daySelector = prefix === "field" ? "[data-day]" : "[data-add-day]";
    result.days = [...editor.querySelectorAll(daySelector)]
      .filter((checkbox) => checkbox.checked)
      .map((checkbox) => (prefix === "field" ? checkbox.dataset.day : checkbox.dataset.addDay));
    result.times = String(result.times || "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
    return result;
  }

  async _saveItem(id) {
    const editor = this.shadowRoot.querySelector(`[data-editor="${CSS.escape(id)}"]`);
    if (!editor) return;
    const data = this._collectEditor(editor, "field");
    this._validateSchedule(data);
    await this._service("update_item", { item_id: id, ...data });
    this._drafts.delete(id);
    const itemName = data.name || this._items().find((item) => item.id === id)?.name || id;
    this._setMessage(`Saved ${itemName}.`);
  }

  async _addItem() {
    const editor = this.shadowRoot.querySelector('[data-editor="new"]');
    if (!editor) return;
    const data = this._collectEditor(editor, "add");
    if (!String(data.name || "").trim()) throw new Error("Enter a name first.");
    this._validateSchedule(data);
    if (data.item_type !== "custom" && (!data.unit || data.unit === "items")) {
      data.unit = MSM_TYPES[data.item_type] || "items";
    }
    await this._service("add_item", data);
    this._addDraft = {};
    this._addItemOpen = false;
    this._setMessage(`Created ${data.name}. It will appear automatically on dynamic item cards.`);
  }

  _validateSchedule(data) {
    const usage = Number(data.usage_per_day || 0);
    if (data.schedule_mode === "manual" || usage <= 0) {
      data.schedule_mode = "manual";
      data.usage_per_day = 0;
      data.times = [];
      return;
    }
    if (!Array.isArray(data.times) || data.times.length === 0) {
      throw new Error("Add at least one valid time, such as 08:00.");
    }
    if (data.schedule_mode === "selected_weekdays") {
      if (!Array.isArray(data.days) || data.days.length === 0) {
        throw new Error("Select at least one active weekday.");
      }
    } else {
      data.days = [...MSM_ALL_DAYS];
    }
    if (data.schedule_mode === "interval") {
      data.interval_days = Math.max(Number(data.interval_days || 1), 1);
      if (!data.start_date) throw new Error("Select an interval start date.");
    }
  }

  async _service(service, data) {
    await this._hass.callService("medication_stock_manager", service, data);
  }

  _setMessage(message, kind = "ok") {
    this._message = message;
    this._messageKind = kind;
    this._render();
    window.setTimeout(() => {
      if (this._message === message) {
        this._message = "";
        this._render();
      }
    }, 4500);
  }

  _styles() {
    return `
      :host { display: block; }
      ha-card { padding: 20px; overflow: visible; overflow-anchor: none; }
      ha-card.embedded {
        padding: 0;
        background: transparent;
        box-shadow: none;
        border: 0;
      }
      .item-detail {
        padding: 4px 2px 12px;
      }
      .item-detail h2 {
        margin: 0 0 14px;
      }
      .item-detail p {
        margin: 8px 0;
      }
      .item-detail a {
        color: var(--primary-color);
      }
      .detail-warning {
        margin-top: 16px;
        color: var(--error-color);
        font-weight: 600;
      }
      .detail-ok {
        margin-top: 16px;
        color: var(--success-color, #43a047);
        font-weight: 600;
      }
      h1, h2 { margin: 0; }
      h1 { font-size: 1.45rem; }
      h2 { font-size: 1.08rem; margin-bottom: 10px; }
      p { margin: 6px 0 0; color: var(--secondary-text-color); }
      a { color: var(--primary-color); }
      [hidden] { display: none !important; }
      .header { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
      section { margin-top: 22px; }
      section:first-child { margin-top: 0; }
      .section-note { margin-bottom: 12px; }
      .loading, .missing, .empty { padding: 22px; }
      .message { margin: 12px 0; padding: 10px 12px; border-radius: 12px; background: color-mix(in srgb, var(--success-color, #43a047) 15%, transparent); }
      .message.error { background: color-mix(in srgb, var(--error-color) 16%, transparent); color: var(--error-color); }
      .table-wrap {
        overflow: visible;
        overflow-anchor: none;
        border: 1px solid var(--divider-color);
        border-radius: 14px;
      }
      .table-wrap.scroll-enabled {
        overflow-x: auto;
        overscroll-behavior-inline: contain;
        scrollbar-gutter: stable;
      }
      table {
        width: 100%;
        border-collapse: collapse;
      }
      .scroll-enabled table {
        min-width: 650px;
      }
      th, td {
        padding: 9px 10px;
        text-align: left;
        border-bottom: 1px solid var(--divider-color);
        vertical-align: top;
      }
      .scroll-enabled th,
      .scroll-enabled td {
        white-space: nowrap;
      }
      .scroll-enabled th:first-child,
      .scroll-enabled td:first-child {
        white-space: normal;
        min-width: 190px;
      }
      .compact-table table {
        min-width: 0;
        table-layout: fixed;
      }
      .compact-table th,
      .compact-table td {
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: normal;
      }
      .compact-table .col-name {
        width: 46%;
      }
      .compact-table .col-stock {
        width: 22%;
      }
      .compact-table .col-supply {
        width: 18%;
      }
      .compact-table .col-status {
        width: 14%;
        text-align: center;
      }
      .compact-table.with-owner .col-name {
        width: 34%;
      }
      .compact-table.with-owner .col-owner {
        width: 16%;
      }
      .compact-table.with-owner .col-stock {
        width: 22%;
      }
      .compact-table.with-owner .col-supply {
        width: 16%;
      }
      .compact-table.with-owner .col-status {
        width: 12%;
      }
      th { color: var(--secondary-text-color); font-size: .82rem; text-transform: uppercase; letter-spacing: .03em; }
      tr:last-child td { border-bottom: 0; }
      .muted, small { color: var(--secondary-text-color); }
      small { display: block; margin-top: 2px; font-weight: normal; }
      .items, .home-list { display: grid; gap: 10px; }
      details.item, details.add-item, details.home-item { border: 1px solid var(--divider-color); border-radius: 14px; background: var(--ha-card-background, var(--card-background-color)); overflow: hidden; }
      details > summary { list-style: none; cursor: pointer; }
      details > summary::-webkit-details-marker { display: none; }
      details.item > summary, details.add-item > summary { padding: 13px 15px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
      details[open] > summary { border-bottom: 1px solid var(--divider-color); }
      .summary-main { display: flex; align-items: center; gap: 10px; min-width: 0; }
      .summary-main span:last-child { min-width: 0; }
      .summary-main strong { overflow-wrap: anywhere; }
      .summary-status { color: var(--secondary-text-color); white-space: nowrap; }
      .status-dot { width: 11px; height: 11px; border-radius: 50%; flex: 0 0 11px; }
      .status-dot.ok { background: var(--success-color, #43a047); }
      .status-dot.low { background: var(--error-color); }
      .editor { padding: 15px; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
      .field {
        display: flex;
        flex-direction: column;
        gap: 5px;
        min-width: 0;
      }
      .field.wide,
      .actions.wide,
      .computed.wide {
        grid-column: 1 / -1;
      }
      .metric-field > label {
        height: 3.35em;
        min-height: 3.35em;
        display: flex;
        align-items: flex-end;
      }
      .schedule-mode,
      .schedule-times,
      .schedule-half {
        grid-column: span 2;
      }
      .schedule-checkbox-row {
        grid-column: 1 / -1;
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
        align-items: start;
      }
      .schedule-checkbox-row label,
      .owner-auto-row label {
        display: flex;
        align-items: flex-start;
        gap: 9px;
        color: var(--secondary-text-color);
        line-height: 1.45;
      }
      .owner-auto-row {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
      }
      .schedule-options,
      .reminder-field {
        grid-column: 1 / -1;
      }
      .field.check {
        justify-content: end;
      }
      .field.check label {
        display: flex;
        align-items: center;
        gap: 8px;
        min-height: 42px;
      }
      label { font-size: .82rem; color: var(--secondary-text-color); }
      input, select, textarea { width: 100%; box-sizing: border-box; min-height: 42px; padding: 8px 10px; border: 1px solid var(--divider-color); border-radius: 10px; background: var(--card-background-color); color: var(--primary-text-color); font: inherit; }
      input[type="checkbox"] { width: 18px; min-height: 18px; height: 18px; padding: 0; }
      .days { display: flex; flex-wrap: wrap; gap: 7px; }
      .day { display: flex; align-items: center; gap: 5px; border: 1px solid var(--divider-color); border-radius: 9px; padding: 7px 9px; color: var(--primary-text-color); }
      .computed { display: flex; flex-wrap: wrap; gap: 10px 18px; padding: 10px 12px; border-radius: 10px; background: color-mix(in srgb, var(--primary-color) 8%, transparent); color: var(--secondary-text-color); }
      .actions { display: flex; flex-wrap: wrap; gap: 8px; }
      button { border: 0; border-radius: 11px; min-height: 40px; padding: 8px 13px; cursor: pointer; background: color-mix(in srgb, var(--primary-text-color) 10%, transparent); color: var(--primary-text-color); font: inherit; font-weight: 600; }
      button.primary { background: var(--primary-color); color: var(--text-primary-color, white); }
      button.secondary { background: color-mix(in srgb, var(--primary-color) 15%, transparent); }
      button.danger { color: var(--error-color); background: color-mix(in srgb, var(--error-color) 12%, transparent); }
      button:disabled { opacity: .55; cursor: progress; }
      ha-card.view-stock_buttons {
        padding: 0;
        background: transparent;
        box-shadow: none;
        border: 0;
      }
      .stock-buttons {
        display: grid;
        gap: 18px;
      }
      .stock-button-group {
        display: grid;
        gap: 10px;
      }
      .stock-button-heading {
        display: flex;
        align-items: center;
        gap: 14px;
        margin: 4px 8px;
      }
      .stock-button-heading h2 {
        margin: 0;
        white-space: nowrap;
      }
      .stock-button-heading > span {
        height: 6px;
        border-radius: 6px;
        background: color-mix(
          in srgb,
          var(--primary-text-color) 10%,
          transparent
        );
        flex: 1;
      }
      .stock-button-list {
        display: grid;
        gap: 10px;
      }
      button.stock-button-card {
        width: 100%;
        min-height: 94px;
        display: grid;
        grid-template-columns: 46px minmax(0, 1fr) auto;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        border-radius: 28px;
        background: var(--ha-card-background, var(--card-background-color));
        color: var(--primary-text-color);
        text-align: left;
        box-shadow: none;
      }
      button.stock-button-card:hover {
        background: color-mix(
          in srgb,
          var(--primary-text-color) 8%,
          var(--ha-card-background, var(--card-background-color))
        );
      }
      .stock-button-icon {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        display: grid;
        place-items: center;
        background: color-mix(
          in srgb,
          var(--primary-text-color) 6%,
          transparent
        );
      }
      .stock-button-icon ha-icon {
        --mdc-icon-size: 24px;
      }
      .stock-button-main {
        min-width: 0;
        color: var(--secondary-text-color);
      }
      .stock-button-main > strong {
        display: block;
        color: var(--primary-text-color);
        overflow-wrap: anywhere;
      }
      .stock-button-secondary {
        font-size: .86rem;
        line-height: 1.35;
      }
      .stock-button-warning {
        margin-top: 4px;
        color: var(--error-color);
        font-weight: 700;
      }
      .stock-button-supply {
        display: flex;
        align-items: center;
        gap: 6px;
        white-space: nowrap;
      }
      .stock-button-supply ha-icon {
        --mdc-icon-size: 16px;
      }
      .stock-modal-backdrop {
        position: fixed;
        inset: 0;
        z-index: 9999;
        display: grid;
        place-items: center;
        padding: 20px;
        background: rgb(0 0 0 / 62%);
      }
      .stock-modal-panel {
        width: min(620px, 100%);
        max-height: calc(100vh - 40px);
        overflow-y: auto;
        padding: 20px;
        border-radius: 26px;
        background: var(--ha-card-background, var(--card-background-color));
        color: var(--primary-text-color);
        box-shadow: 0 18px 60px rgb(0 0 0 / 45%);
      }
      .stock-modal-header {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: flex-start;
        margin-bottom: 16px;
      }
      .stock-modal-header p {
        margin-top: 3px;
      }
      button.stock-modal-close {
        width: 42px;
        min-width: 42px;
        height: 42px;
        padding: 0;
        border-radius: 50%;
        font-size: 26px;
      }
      .stock-modal-details {
        padding: 14px 0 20px;
      }
      .stock-modal-details h3 {
        font-size: 1.4rem;
        margin: 0 0 14px;
      }
      .stock-modal-details p {
        margin: 8px 0;
      }
      .stock-modal-details a {
        display: inline-block;
        margin-top: 8px;
        color: var(--primary-color);
      }
      .stock-modal-warning {
        margin-top: 16px;
        color: var(--error-color);
        font-weight: 700;
      }
      .stock-modal-ok {
        margin-top: 16px;
        color: var(--success-color, #43a047);
        font-weight: 700;
      }
      .stock-modal-actions {
        display: grid;
        gap: 10px;
      }
      button.stock-action-large {
        width: 100%;
        min-height: 70px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        border-radius: 20px;
      }
      button.stock-action-large ha-icon {
        --mdc-icon-size: 30px;
      }
      .stock-action-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
      }
      .stock-action-row button {
        min-height: 52px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        border-radius: 16px;
      }
      .stock-action-row ha-icon {
        --mdc-icon-size: 23px;
      }
      .sidebar-settings {
        display: grid;
        gap: 16px;
      }
      .sidebar-settings-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px;
      }
      .sidebar-toggle {
        min-height: 58px;
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 13px 15px;
        border: 1px solid var(--divider-color);
        border-radius: 14px;
      }
      .sidebar-toggle input {
        margin-top: 4px;
      }
      .sidebar-toggle span {
        display: grid;
        gap: 3px;
      }
      .sidebar-toggle small {
        color: var(--secondary-text-color);
        line-height: 1.35;
      }
      .owner-section {
        display: grid;
        gap: 18px;
      }
      .owner-list {
        display: grid;
        gap: 10px;
      }
      details.owner-card {
        border: 1px solid var(--divider-color);
        border-radius: 14px;
        overflow: hidden;
      }
      details.owner-card > summary {
        padding: 13px 15px;
        display: flex;
        justify-content: space-between;
        gap: 12px;
      }
      details.owner-card > summary span {
        color: var(--secondary-text-color);
      }
      .owner-add-icon {
        color: var(--primary-color);
        transition: transform 160ms ease;
      }
      details.owner-create-card[open] .owner-add-icon {
        transform: rotate(45deg);
      }
      .owner-editor {
        padding: 15px;
      }
      .owner-create {
        border-top: 1px solid var(--divider-color);
      }
      .integration-owned-note {
        padding: 12px 14px;
        border-radius: 12px;
        background: color-mix(in srgb, var(--primary-color) 10%, transparent);
        color: var(--secondary-text-color);
      }
      .owner-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }
      .group-heading { display: flex; align-items: center; gap: 14px; margin: 18px 8px 10px; }
      .group-heading:first-child { margin-top: 0; }
      .group-heading ha-icon { width: 24px; }
      .group-heading h2 { margin: 0; white-space: nowrap; }
      .group-heading span { height: 6px; border-radius: 6px; background: color-mix(in srgb, var(--primary-text-color) 10%, transparent); flex: 1; }
      details.home-item > summary { padding: 14px 16px; display: grid; grid-template-columns: 44px minmax(0, 1fr) auto; align-items: center; gap: 12px; }
      .home-icon { width: 42px; height: 42px; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--primary-text-color) 6%, transparent); }
      .home-icon ha-icon { --mdc-icon-size: 24px; }
      .home-main { min-width: 0; color: var(--secondary-text-color); }
      .home-main > strong { color: var(--primary-text-color); display: block; overflow-wrap: anywhere; }
      .home-supply { display: flex; gap: 6px; align-items: center; white-space: nowrap; }
      .home-supply ha-icon { --mdc-icon-size: 16px; }
      .warning { color: var(--error-color); font-weight: 600; margin-top: 3px; }
      .home-details { padding: 14px 16px; display: grid; gap: 10px; color: var(--secondary-text-color); }
      .home-actions { margin-top: 4px; }
      @media (max-width: 900px) { .editor { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
      @media (max-width: 600px) {
        ha-card { padding: 14px; }
        .header { align-items: flex-start; flex-direction: column; }
        .editor { grid-template-columns: 1fr; }
        .field.wide,
        .actions.wide,
        .computed.wide,
        .schedule-mode,
        .schedule-times,
        .schedule-half,
        .schedule-check,
        .schedule-options,
        .reminder-field {
          grid-column: 1;
        }
        .metric-field > label {
          height: auto;
          min-height: auto;
        }
        .schedule-checkbox-row,
        .owner-auto-row {
          grid-template-columns: 1fr;
        }
        .actions button { flex: 1 1 42%; }
        .owner-grid,
        .sidebar-settings-grid {
          grid-template-columns: 1fr;
        }
        .owner-grid .wide,
        .sidebar-settings-grid .wide {
          grid-column: 1;
        }
        button.stock-button-card {
          grid-template-columns: 40px minmax(0, 1fr);
          border-radius: 22px;
        }
        .stock-button-supply {
          grid-column: 2;
        }
        .summary-status { display: none; }
        details.home-item > summary { grid-template-columns: 40px minmax(0, 1fr); }
        .home-supply { grid-column: 2; }
      }
    `;
  }
}


class MedicationStockManagerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._panel = null;
    this._cards = [];
    this._panelSignature = null;
  }

  set hass(value) {
    this._hass = value;
    this._cards.forEach((card) => {
      card.hass = value;
    });
  }

  set panel(value) {
    const nextSignature = this._panelStateSignature(value);
    const changed = nextSignature !== this._panelSignature;
    this._panel = value;
    this._panelSignature = nextSignature;

    if (!this.isConnected) return;
    if (!this.shadowRoot.childElementCount) {
      this._render(false);
      return;
    }

    // Home Assistant may assign a new panel object repeatedly even when the
    // actual panel metadata is unchanged. Rebuilding here destroyed every
    // child card, closed <details> menus, and reset the page scroll position.
    if (changed) {
      this._render(true);
    }
  }

  set narrow(_value) {}
  set route(_value) {}

  connectedCallback() {
    this._render();
  }

  _panelStateSignature(panel) {
    const config = panel?.config || {};
    return JSON.stringify({
      component: panel?.component_name || "",
      urlPath: panel?.url_path || "",
      title: panel?.title || config.sidebar_title || "",
      icon: panel?.icon || config.sidebar_icon || "",
      requireAdmin: panel?.require_admin ?? true,
      entryId: config.entry_id || "",
    });
  }

  _capturePanelScroll() {
    const positions = [];
    const seen = new Set();

    const add = (element, left, top) => {
      if (!element || seen.has(element)) return;
      seen.add(element);
      positions.push({ element, left, top });
    };

    add(window, window.scrollX, window.scrollY);

    if (document.scrollingElement) {
      add(
        document.scrollingElement,
        document.scrollingElement.scrollLeft,
        document.scrollingElement.scrollTop
      );
    }

    let node = this;
    while (node) {
      if (node.parentElement) {
        node = node.parentElement;
      } else {
        node = node.getRootNode?.()?.host || null;
      }
      if (!(node instanceof HTMLElement)) continue;

      const style = getComputedStyle(node);
      const scrollable =
        /(auto|scroll|overlay)/.test(
          `${style.overflow} ${style.overflowX} ${style.overflowY}`
        ) ||
        node.scrollHeight > node.clientHeight ||
        node.scrollWidth > node.clientWidth;

      if (scrollable) {
        add(node, node.scrollLeft, node.scrollTop);
      }
    }

    return positions;
  }

  _restorePanelScroll(positions) {
    const restore = () => {
      for (const position of positions || []) {
        if (position.element === window) {
          window.scrollTo(position.left, position.top);
        } else if (position.element?.isConnected) {
          position.element.scrollLeft = position.left;
          position.element.scrollTop = position.top;
        }
      }
    };

    restore();
    requestAnimationFrame(() => {
      restore();
      requestAnimationFrame(restore);
    });
  }

  _card(config) {
    const card = document.createElement(MSM_CARD_TAG);
    card.setConfig(config);
    if (this._hass) card.hass = this._hass;
    this._cards.push(card);
    return card;
  }

  _render(force = false) {
    if (!this.shadowRoot) return;
    if (this.shadowRoot.childElementCount && !force) return;

    const scrollPositions = force
      ? this._capturePanelScroll()
      : [];

    if (force) {
      this.shadowRoot.replaceChildren();
    }

    const style = document.createElement("style");
    style.textContent = `
      :host {
        display: block;
        min-height: 100%;
        background: var(--primary-background-color);
        color: var(--primary-text-color);
      }
      .page {
        width: min(1180px, calc(100% - 32px));
        margin: 0 auto;
        padding: 24px 0 48px;
      }
      .title {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 0 0 20px;
      }
      .title-spacer {
        flex: 1;
      }
      .settings-link {
        border: 1px solid var(--divider-color);
        border-radius: 18px;
        padding: 9px 14px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font: inherit;
        cursor: pointer;
      }
      .settings-link:hover {
        background: color-mix(
          in srgb,
          var(--primary-text-color) 8%,
          var(--card-background-color)
        );
      }
      .title ha-icon {
        --mdc-icon-size: 30px;
        color: var(--primary-color);
      }
      .title h1 {
        margin: 0;
        font-size: 1.8rem;
      }
      .grid {
        display: grid;
        gap: 18px;
      }
      @media (max-width: 600px) {
        .page {
          width: min(100% - 20px, 1180px);
          padding-top: 14px;
        }
        .title h1 {
          font-size: 1.45rem;
        }
      }
    `;

    const page = document.createElement("main");
    page.className = "page";
    const panelConfig = this._panel?.config || {};
    const panelTitle =
      this._panel?.title ||
      panelConfig.sidebar_title ||
      "Medication Stock";
    const panelIcon =
      this._panel?.icon ||
      panelConfig.sidebar_icon ||
      "mdi:medical-bag";

    const title = document.createElement("div");
    title.className = "title";
    title.innerHTML = `
      <ha-icon icon="${panelIcon}"></ha-icon>
      <h1>${panelTitle}</h1>
      <span class="title-spacer"></span>
      <button class="settings-link" type="button">
        Integration options
      </button>
    `;
    title
      .querySelector(".settings-link")
      ?.addEventListener("click", () => {
        history.pushState(
          null,
          "",
          "/config/integrations/integration/medication_stock_manager"
        );
        window.dispatchEvent(new Event("location-changed"));
      });
    const grid = document.createElement("div");
    grid.className = "grid";

    this._cards = [];
    grid.append(
      this._card({
        type: `custom:${MSM_CARD_TAG}`,
        view: "sidebar_settings",
        title: "Sidebar settings",
      }),
      this._card({
        type: `custom:${MSM_CARD_TAG}`,
        view: "create_owner",
        title: "Owners",
        show_existing_owners: true,
      }),
      this._card({
        type: `custom:${MSM_CARD_TAG}`,
        view: "create_item",
        owner: "all",
        title: "New Medication / Item",
        default_type: "capsule",
        default_schedule: "manual",
      }),
      this._card({
        type: `custom:${MSM_CARD_TAG}`,
        view: "item_configuration",
        owner: "all",
        title: "Medication & Item Configuration",
        show_restore_defaults: true,
        show_remove: true,
        show_actions: true,
      })
    );

    page.append(title, grid);
    this.shadowRoot.append(style, page);

    if (scrollPositions.length) {
      this._restorePanelScroll(scrollPositions);
    }
  }
}

const registeredMedicationStockManagerCard = customElements.get(
  MSM_CARD_TAG
);

if (!registeredMedicationStockManagerCard) {
  customElements.define(MSM_CARD_TAG, MedicationStockManagerCard);
} else if (
  registeredMedicationStockManagerCard !== MedicationStockManagerCard
) {
  // Home Assistant can load an old resource before a newly versioned one.
  // The custom-element registry cannot be redefined, so copy the complete
  // current implementation onto the already registered constructor.
  for (const property of Reflect.ownKeys(
    MedicationStockManagerCard.prototype
  )) {
    if (property === "constructor") continue;
    const descriptor = Object.getOwnPropertyDescriptor(
      MedicationStockManagerCard.prototype,
      property
    );
    if (descriptor) {
      Object.defineProperty(
        registeredMedicationStockManagerCard.prototype,
        property,
        descriptor
      );
    }
  }
}

const activeMedicationStockManagerCard = customElements.get(MSM_CARD_TAG);
if (activeMedicationStockManagerCard) {
  Object.defineProperty(
    activeMedicationStockManagerCard.prototype,
    "msmVersion",
    {
      value: MSM_CARD_VERSION,
      configurable: true,
      writable: true,
    }
  );
}


function registerOrUpgradePanelElement(tagName, implementation) {
  const registered = customElements.get(tagName);
  if (!registered) {
    // A CustomElement constructor can only be registered once, so aliases
    // receive a small subclass of the current implementation.
    const PanelElement = class extends implementation {};
    customElements.define(tagName, PanelElement);
    return;
  }

  for (const property of Reflect.ownKeys(implementation.prototype)) {
    if (property === "constructor") continue;
    const descriptor = Object.getOwnPropertyDescriptor(
      implementation.prototype,
      property
    );
    if (descriptor) {
      Object.defineProperty(
        registered.prototype,
        property,
        descriptor
      );
    }
  }
}

for (const panelTag of [
  MSM_PANEL_TAG,
  "ha-panel-medication-stock-manager-panel",
  "medication-stock-manager-panel",
]) {
  registerOrUpgradePanelElement(
    panelTag,
    MedicationStockManagerPanel
  );
}

window.customCards = window.customCards || [];
const existingCardMetadata = window.customCards.find(
  (card) => card.type === MSM_CARD_TAG
);
if (existingCardMetadata) {
  existingCardMetadata.name = "Medication Stock Manager";
  existingCardMetadata.description =
    `Dynamic medication and medical-supply views (v${MSM_CARD_VERSION}).`;
} else {
  window.customCards.push({
    type: MSM_CARD_TAG,
    name: "Medication Stock Manager",
    description:
      `Dynamic medication and medical-supply views (v${MSM_CARD_VERSION}).`,
    preview: false,
  });
}

console.info(
  `%c Medication Stock Manager Card v${MSM_CARD_VERSION} active `,
  "background:#03a9f4;color:#fff;padding:4px;border-radius:4px"
);
