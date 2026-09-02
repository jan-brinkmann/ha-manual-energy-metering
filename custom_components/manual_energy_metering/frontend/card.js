const DOMAIN = "manual_energy_metering";
const STATIC_URL = `/${DOMAIN}_static`;
const CARD_TAG = "manual-energy-metering-card";
const EDITOR_TAG = "manual-energy-metering-card-editor";

const METER_ICONS = {
  electricity: "electricity.png",
  gas: "gas.png",
  water: "water.png",
};

const DEFAULT_CONFIG = {
  show_name: true,
  show_last_reading: true,
  show_last_reading_timestamp: true,
  show_history_link: true,
};

const TRANSLATIONS = {
  en: {
    cardName: "Manual Energy Metering",
    cardDescription: "Enter a dated meter reading directly from a dashboard.",
    fallbackName: "Manual meter",
    newReading: "New meter reading",
    intro: "Record a new absolute reading for this meter.",
    meterReading: "Meter reading",
    readingDate: "Reading date and time",
    lastReading: "Last reading",
    lastReadingDate: "Last reading date",
    completeHistory: "View complete meter reading history",
    add: "Add reading",
    added: "The meter reading was added.",
    noReadings: "No readings yet",
    required: "Enter a meter reading and a reading date.",
    invalidValue: "Enter a non-negative numeric meter reading.",
    noGrouping: "Do not use thousands separators in the meter reading.",
    unavailable: "The selected meter entity is unavailable.",
    selectEntity: "Select a Manual Energy Metering sensor in the card editor.",
    genericError: "The meter reading could not be added.",
    editor: {
      entity: "Meter entity",
      show_name: "Show meter name",
      show_last_reading: "Show last reading",
      show_last_reading_timestamp: "Show last reading date",
      show_history_link: "Show link to complete history",
    },
    errors: {
      unauthorized: "You are not allowed to add readings to this meter.",
      entity_not_found: "The selected meter entity does not exist.",
      entry_not_found: "The selected meter does not exist.",
      entry_not_loaded: "The selected meter is not loaded.",
      invalid_timestamp: "Enter a valid reading date and time.",
      invalid_value: "Enter a valid non-negative meter reading.",
      non_monotonic:
        "The reading must not be lower than neighboring meter readings.",
    },
  },
  de: {
    cardName: "Manuelle Energiemessung",
    cardDescription:
      "Einen datierten Zählerstand direkt über ein Dashboard erfassen.",
    fallbackName: "Manueller Zähler",
    newReading: "Neuer Zählerstand",
    intro: "Erfasse einen neuen absoluten Stand für diesen Zähler.",
    meterReading: "Zählerstand",
    readingDate: "Ablesedatum und Uhrzeit",
    lastReading: "Letzter Zählerstand",
    lastReadingDate: "Letztes Ablesedatum",
    completeHistory: "Vollständige Zählerstandshistorie anzeigen",
    add: "Zählerstand eintragen",
    added: "Der Zählerstand wurde eingetragen.",
    noReadings: "Noch keine Zählerstände",
    required: "Trage einen Zählerstand und ein Ablesedatum ein.",
    invalidValue: "Trage einen nicht negativen numerischen Zählerstand ein.",
    noGrouping: "Verwende im Zählerstand keine Tausendertrennzeichen.",
    unavailable: "Die ausgewählte Zählerentität ist nicht verfügbar.",
    selectEntity:
      "Wähle im Karteneditor einen Sensor der Manuellen Energiemessung aus.",
    genericError: "Der Zählerstand konnte nicht eingetragen werden.",
    editor: {
      entity: "Zählerentität",
      show_name: "Zählername anzeigen",
      show_last_reading: "Letzten Zählerstand anzeigen",
      show_last_reading_timestamp: "Letztes Ablesedatum anzeigen",
      show_history_link: "Link zur vollständigen Historie anzeigen",
    },
    errors: {
      unauthorized:
        "Du bist nicht berechtigt, Zählerstände für diesen Zähler einzutragen.",
      entity_not_found: "Die ausgewählte Zählerentität existiert nicht.",
      entry_not_found: "Der ausgewählte Zähler existiert nicht.",
      entry_not_loaded: "Der ausgewählte Zähler ist nicht geladen.",
      invalid_timestamp: "Trage ein gültiges Ablesedatum mit Uhrzeit ein.",
      invalid_value: "Trage einen gültigen nicht negativen Zählerstand ein.",
      non_monotonic:
        "Der Wert darf benachbarte Zählerstände nicht unterschreiten.",
    },
  },
};

function languageFor(hass) {
  const locale =
    hass?.locale?.language || hass?.language || navigator.language || "en";
  return locale.toLowerCase().startsWith("de") ? "de" : "en";
}

function normalizeConfig(config) {
  return { ...DEFAULT_CONFIG, ...config };
}

class ManualEnergyMeteringCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  set hass(value) {
    this._hass = value;
    const form = this.shadowRoot.querySelector("ha-form");
    if (form) {
      form.hass = value;
    } else {
      this._render();
    }
  }

  setConfig(config) {
    this._config = normalizeConfig(config);
    this._render();
  }

  _render() {
    if (!this._config) {
      return;
    }
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-form { display: block; }
      </style>
      <ha-form></ha-form>
    `;
    const form = this.shadowRoot.querySelector("ha-form");
    form.hass = this._hass;
    form.data = {
      entity: this._config.entity,
      show_name: this._config.show_name,
      show_last_reading: this._config.show_last_reading,
      show_last_reading_timestamp: this._config.show_last_reading_timestamp,
      show_history_link: this._config.show_history_link,
    };
    form.schema = [
      {
        name: "entity",
        required: true,
        selector: {
          entity: {
            filter: [{ integration: DOMAIN, domain: "sensor" }],
          },
        },
      },
      { name: "show_name", selector: { boolean: {} } },
      { name: "show_last_reading", selector: { boolean: {} } },
      {
        name: "show_last_reading_timestamp",
        selector: { boolean: {} },
      },
      { name: "show_history_link", selector: { boolean: {} } },
    ];
    form.computeLabel = (schema) =>
      TRANSLATIONS[languageFor(this._hass)].editor[schema.name] || schema.name;
    form.addEventListener("value-changed", (event) => {
      const config = normalizeConfig({
        ...this._config,
        ...event.detail.value,
      });
      this._config = config;
      this.dispatchEvent(
        new CustomEvent("config-changed", {
          detail: { config },
          bubbles: true,
          composed: true,
        })
      );
    });
  }
}

class ManualEnergyMeteringCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement(EDITOR_TAG);
  }

  static getStubConfig() {
    return { ...DEFAULT_CONFIG };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._formValue = "";
    this._formTimestamp = "";
    this._timestampDirty = false;
    this._busy = false;
    this._message = undefined;
    this._lastResult = undefined;
    this._historyEntity = undefined;
    this._historyUrl = undefined;
    this._historyLoading = false;
  }

  setConfig(config) {
    if (!config) {
      throw new Error("Invalid card configuration");
    }
    const previousEntity = this._config?.entity;
    this._config = normalizeConfig(config);
    if (previousEntity && previousEntity !== this._config.entity) {
      this._resetForm();
      this._lastResult = undefined;
      this._message = undefined;
      this._resetHistoryLink();
    }
    this._ensureTimestamp();
    this._render();
    this._resolveHistoryLink();
  }

  set hass(value) {
    const entityId = this._config?.entity;
    const previousState = entityId ? this._hass?.states?.[entityId] : undefined;
    const previousLocale = this._locale;
    const previousTimeZone = this._timeZone;
    this._hass = value;
    const currentState = entityId ? value?.states?.[entityId] : undefined;

    if (previousState !== currentState) {
      this._lastResult = undefined;
    }
    if (previousTimeZone !== this._timeZone && !this._timestampDirty) {
      this._formTimestamp = "";
    }
    this._ensureTimestamp();
    this._resolveHistoryLink();
    if (
      !this.shadowRoot.firstElementChild ||
      previousState !== currentState ||
      previousLocale !== this._locale ||
      previousTimeZone !== this._timeZone
    ) {
      this._render();
    }
  }

  connectedCallback() {
    this._ensureTimestamp();
    this._render();
  }

  getCardSize() {
    return 7;
  }

  getGridOptions() {
    return {
      columns: 12,
      min_columns: 6,
    };
  }

  get _language() {
    return languageFor(this._hass);
  }

  get _t() {
    return TRANSLATIONS[this._language];
  }

  get _locale() {
    return (
      this._hass?.locale?.language ||
      this._hass?.language ||
      navigator.language ||
      "en"
    );
  }

  get _timeZone() {
    return this._hass?.config?.time_zone || undefined;
  }

  _ensureTimestamp() {
    if (!this._formTimestamp && !this._timestampDirty && this._hass) {
      this._formTimestamp = this._formatInputTimestamp(new Date());
    }
  }

  _resetForm() {
    this._formValue = "";
    this._formTimestamp = this._hass
      ? this._formatInputTimestamp(new Date())
      : "";
    this._timestampDirty = false;
  }

  _stateData() {
    const entityId = this._config?.entity;
    const state = entityId ? this._hass?.states?.[entityId] : undefined;
    const attributes = state?.attributes || {};
    const result = this._lastResult || {};
    return {
      state,
      name:
        result.name ||
        attributes.friendly_name ||
        entityId ||
        this._t.fallbackName,
      meterType: attributes.meter_type,
      unit: result.unit ?? attributes.unit_of_measurement ?? "",
      lastReading:
        result.last_reading !== undefined
          ? result.last_reading
          : attributes.last_reading,
      lastReadingTimestamp:
        result.last_reading_timestamp !== undefined
          ? result.last_reading_timestamp
          : attributes.last_reading_timestamp,
    };
  }

  _render() {
    if (!this._config) {
      return;
    }
    const t = this._t;
    const data = this._stateData();
    const showName = this._config.show_name;
    const showLastReading = this._config.show_last_reading;
    const showLastReadingTimestamp =
      this._config.show_last_reading_timestamp;
    const hasEntity = Boolean(this._config.entity);
    const available = Boolean(
      data.state && data.state.state !== "unavailable"
    );
    const unit = data.unit ? ` (${data.unit})` : "";

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <ha-card>
        <div class="content">
          ${
            showName
              ? `<h2><span>${this._escape(
                  data.name
                )}</span>${this._renderMeterTypeIcon(data.meterType)}</h2>`
              : ""
          }
          ${this._renderSummary(
            data,
            showLastReading,
            showLastReadingTimestamp
          )}
          <section class="entry">
            <div class="entry-heading">
              <span class="eyebrow">${this._escape(t.newReading)}</span>
              <p>${this._escape(t.intro)}</p>
            </div>
            <form id="reading-form">
              <label>
                <span>${this._escape(t.meterReading + unit)}</span>
                <input
                  id="value"
                  type="text"
                  inputmode="decimal"
                  autocomplete="off"
                  required
                  value="${this._escapeAttribute(this._formValue)}"
                />
              </label>
              <label>
                <span>${this._escape(t.readingDate)}</span>
                <input
                  id="timestamp"
                  type="datetime-local"
                  step="1"
                  required
                  value="${this._escapeAttribute(this._formTimestamp)}"
                />
              </label>
              <button type="submit" ${
                !hasEntity || !available || this._busy ? "disabled" : ""
              }>
                <ha-icon icon="mdi:send"></ha-icon>
                <span>${this._escape(t.add)}</span>
              </button>
            </form>
          </section>
          <div class="message ${this._escapeAttribute(
            this._message?.type || ""
          )}" role="status" aria-live="polite">${this._escape(
            this._message?.text ||
              (!hasEntity ? t.selectEntity : !available ? t.unavailable : "")
          )}</div>
          ${this._renderHistoryLink()}
        </div>
      </ha-card>
    `;

    const form = this.shadowRoot.querySelector("#reading-form");
    form?.addEventListener("submit", (event) => this._submit(event));
    this.shadowRoot.querySelector("#value")?.addEventListener("input", (event) => {
      this._formValue = event.target.value;
      this._message = undefined;
    });
    this.shadowRoot
      .querySelector("#timestamp")
      ?.addEventListener("input", (event) => {
        this._formTimestamp = event.target.value;
        this._timestampDirty = true;
        this._message = undefined;
      });
  }

  _renderSummary(data, showLastReading, showLastReadingTimestamp) {
    if (!showLastReading && !showLastReadingTimestamp) {
      return "";
    }
    const noReading =
      data.lastReading === null || data.lastReading === undefined;
    const reading = noReading
      ? this._t.noReadings
      : this._formatReading(data.lastReading, data.unit);
    const timestamp = data.lastReadingTimestamp
      ? this._formatDate(data.lastReadingTimestamp)
      : this._t.noReadings;
    return `
      <dl class="summary">
        ${
          showLastReading
            ? `<div><dt>${this._escape(
                this._t.lastReading
              )}</dt><dd>${this._escape(reading)}</dd></div>`
            : ""
        }
        ${
          showLastReadingTimestamp
            ? `<div><dt>${this._escape(
                this._t.lastReadingDate
              )}</dt><dd>${this._escape(timestamp)}</dd></div>`
            : ""
        }
      </dl>
    `;
  }

  _renderMeterTypeIcon(meterType) {
    const filename = METER_ICONS[meterType];
    if (!filename) {
      return "";
    }
    return `<img class="meter-type-icon" src="${STATIC_URL}/icons/${filename}" alt="" aria-hidden="true" />`;
  }

  _resetHistoryLink() {
    this._historyEntity = undefined;
    this._historyUrl = undefined;
    this._historyLoading = false;
  }

  _resolveHistoryLink() {
    const entityId = this._config?.entity;
    if (
      !this._config?.show_history_link ||
      !this._hass?.user?.is_admin ||
      !entityId ||
      this._historyLoading ||
      this._historyEntity === entityId
    ) {
      return;
    }

    this._historyEntity = entityId;
    this._historyUrl = undefined;
    this._historyLoading = true;
    this._hass
      .callWS({
        type: "config/entity_registry/get",
        entity_id: entityId,
      })
      .then((entityEntry) => {
        if (
          this._config?.show_history_link &&
          this._config?.entity === entityId &&
          entityEntry?.config_entry_id
        ) {
          this._historyUrl = `/${DOMAIN}?config_entry=${encodeURIComponent(
            entityEntry.config_entry_id
          )}`;
        }
      })
      .catch(() => {
        // The management page and entity-registry details require an admin.
      })
      .finally(() => {
        if (this._config?.entity === entityId) {
          this._historyLoading = false;
          this._render();
        }
      });
  }

  _renderHistoryLink() {
    if (
      !this._config.show_history_link ||
      !this._hass?.user?.is_admin ||
      !this._historyUrl
    ) {
      return "";
    }
    return `
      <div class="history-link">
        <a href="${this._escapeAttribute(this._historyUrl)}">
          <ha-icon icon="mdi:history"></ha-icon>
          <span>${this._escape(this._t.completeHistory)}</span>
        </a>
      </div>
    `;
  }

  async _submit(event) {
    event.preventDefault();
    if (this._busy || !this._config.entity) {
      return;
    }
    const valueInput = this.shadowRoot.querySelector("#value");
    const timestampInput = this.shadowRoot.querySelector("#timestamp");
    const rawValue = valueInput.value;
    const timestamp = timestampInput.value;
    this._formValue = rawValue;
    this._formTimestamp = timestamp;
    this._timestampDirty = true;

    if (!timestamp || rawValue.trim() === "") {
      this._setMessage(this._t.required, "error");
      return;
    }
    if (this._hasGroupingSeparator(rawValue)) {
      this._setMessage(this._t.noGrouping, "error");
      return;
    }
    const value = this._parseNumber(rawValue);
    if (!Number.isFinite(value) || value < 0) {
      this._setMessage(this._t.invalidValue, "error");
      return;
    }

    this._setBusy(true);
    try {
      this._lastResult = await this._hass.callWS({
        type: `${DOMAIN}/card/add`,
        entity_id: this._config.entity,
        value,
        timestamp,
      });
      this._resetForm();
      this._busy = false;
      this._message = { text: this._t.added, type: "success" };
      this._render();
    } catch (error) {
      this._setBusy(false);
      this._setMessage(this._localizedError(error), "error");
    }
  }

  _setBusy(busy) {
    this._busy = busy;
    this.shadowRoot
      .querySelectorAll("button, input")
      .forEach((element) => (element.disabled = busy));
  }

  _setMessage(text, type) {
    this._message = { text, type };
    const element = this.shadowRoot.querySelector(".message");
    if (element) {
      element.textContent = text;
      element.className = `message ${type}`;
    }
  }

  _localizedError(error) {
    const code = error?.code || error?.body?.code;
    return this._t.errors[code] || error?.message || this._t.genericError;
  }

  _formatInputTimestamp(date) {
    const parts = Object.fromEntries(
      new Intl.DateTimeFormat("en-CA", {
        timeZone: this._timeZone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hourCycle: "h23",
      })
        .formatToParts(date)
        .filter((part) => part.type !== "literal")
        .map((part) => [part.type, part.value])
    );
    return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:00`;
  }

  _formatDate(timestamp) {
    return new Intl.DateTimeFormat(this._locale, {
      dateStyle: "medium",
      timeStyle: "medium",
      timeZone: this._timeZone,
    }).format(new Date(timestamp));
  }

  _formatReading(value, unit) {
    const number = new Intl.NumberFormat(this._locale, {
      maximumFractionDigits: 20,
      useGrouping: true,
    }).format(value);
    return unit ? `${number} ${unit}` : number;
  }

  _hasGroupingSeparator(value) {
    const trimmed = value.trim();
    const group = new Intl.NumberFormat(this._locale)
      .formatToParts(12345.6)
      .find((part) => part.type === "group")?.value;
    return Boolean((group && trimmed.includes(group)) || /\s/.test(trimmed));
  }

  _parseNumber(value) {
    const parts = new Intl.NumberFormat(this._locale).formatToParts(12345.6);
    const decimal = parts.find((part) => part.type === "decimal")?.value || ".";
    let normalized = value.trim();
    if (decimal !== ".") {
      normalized = normalized.replace(decimal, ".");
    }
    const digitFormatter = new Intl.NumberFormat(this._locale, {
      useGrouping: false,
    });
    for (let digit = 0; digit <= 9; digit += 1) {
      normalized = normalized
        .split(digitFormatter.format(digit))
        .join(String(digit));
    }
    if (!/^[+]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized)) {
      return Number.NaN;
    }
    return Number(normalized);
  }

  _escape(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _escapeAttribute(value) {
    return this._escape(value);
  }

  _styles() {
    return `
      :host { display: block; }
      * { box-sizing: border-box; }
      ha-card {
        overflow: hidden;
        color: var(--primary-text-color);
        background: var(--ha-card-background, var(--card-background-color));
      }
      .content { padding: 20px; }
      h2 {
        margin: 0 0 16px;
        font-size: 1.25rem;
        line-height: 1.3;
        font-weight: 500;
      }
      .meter-type-icon {
        width: auto;
        height: 0.72em;
        margin-left: 0.24em;
        vertical-align: -0.035em;
      }
      .summary {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 6px 24px;
        margin: 0 0 16px;
      }
      .summary div {
        min-width: 0;
      }
      .summary div:only-child { grid-column: 1 / -1; }
      dt {
        margin-bottom: 2px;
        color: var(--secondary-text-color);
        font-size: 0.78rem;
        line-height: 1.2;
      }
      dd {
        margin: 0;
        overflow-wrap: anywhere;
        font-size: 1rem;
        font-weight: 500;
      }
      .entry {
        padding-top: 16px;
        border-top: 1px solid var(--divider-color);
      }
      .entry-heading { margin-bottom: 13px; }
      .eyebrow {
        color: var(--primary-color);
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }
      p {
        margin: 4px 0 0;
        color: var(--secondary-text-color);
        font-size: 0.9rem;
      }
      form {
        display: grid;
        grid-template-columns: minmax(125px, 0.8fr) minmax(210px, 1.2fr) auto;
        gap: 12px;
        align-items: end;
      }
      label { display: grid; gap: 6px; min-width: 0; }
      label span {
        color: var(--secondary-text-color);
        font-size: 0.8rem;
        font-weight: 500;
      }
      input {
        width: 100%;
        height: 42px;
        padding: 0 12px;
        border: 1px solid var(--outline-color, var(--divider-color));
        border-radius: 10px;
        outline: none;
        color: var(--primary-text-color);
        background: var(--card-background-color);
        font: inherit;
        color-scheme: light dark;
      }
      input:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 1px var(--primary-color);
      }
      button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        min-height: 42px;
        padding: 0 16px;
        border: 0;
        border-radius: 10px;
        color: var(--text-primary-color, white);
        background: var(--primary-color);
        font: inherit;
        font-weight: 600;
        cursor: pointer;
      }
      button:disabled { opacity: 0.45; cursor: default; }
      ha-icon { --mdc-icon-size: 19px; }
      .message {
        min-height: 1.25em;
        margin-top: 12px;
        color: var(--secondary-text-color);
        font-size: 0.85rem;
      }
      .message:empty { margin-top: 0; min-height: 0; }
      .message.success { color: var(--success-color, #2e7d32); }
      .message.error { color: var(--error-color); }
      .history-link {
        display: flex;
        justify-content: flex-end;
        margin-top: 12px;
      }
      .history-link a {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        color: var(--primary-color);
        font-size: 0.88rem;
        font-weight: 500;
        text-decoration: none;
      }
      .history-link a:hover { text-decoration: underline; }
      @media (max-width: 620px) {
        .summary { column-gap: 12px; }
        form { grid-template-columns: 1fr; }
        button { width: 100%; }
      }
    `;
  }
}

if (!customElements.get(EDITOR_TAG)) {
  customElements.define(EDITOR_TAG, ManualEnergyMeteringCardEditor);
}
if (!customElements.get(CARD_TAG)) {
  customElements.define(CARD_TAG, ManualEnergyMeteringCard);
}

const language = languageFor();
const cardMetadata = {
  type: CARD_TAG,
  name: TRANSLATIONS[language].cardName,
  description: TRANSLATIONS[language].cardDescription,
  preview: false,
  documentationURL:
    "https://github.com/jan-brinkmann/ha-manual-energy-metering#dashboard-card",
  getEntitySuggestion: (hass, entityId) => {
    const statisticId = hass.states[entityId]?.attributes?.statistic_id;
    if (!String(statisticId || "").startsWith(`${DOMAIN}:`)) {
      return null;
    }
    return {
      config: {
        type: `custom:${CARD_TAG}`,
        entity: entityId,
        ...DEFAULT_CONFIG,
      },
    };
  },
};

window.customCards = window.customCards || [];
const existingMetadata = window.customCards.find(
  (card) => card.type === CARD_TAG
);
if (existingMetadata) {
  Object.assign(existingMetadata, cardMetadata);
} else {
  window.customCards.push(cardMetadata);
}
