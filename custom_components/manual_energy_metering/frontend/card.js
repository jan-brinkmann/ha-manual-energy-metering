const DOMAIN = "manual_energy_metering";
const STATIC_URL = `/${DOMAIN}_static`;
const CARD_TAG = "manual-energy-metering-card";
const EDITOR_TAG = "manual-energy-metering-card-editor";
const MAX_SOURCE_IMAGE_BYTES = 20 * 1024 * 1024;
const MAX_COMPRESSED_IMAGE_BYTES = 2 * 1024 * 1024;
const MAX_IMAGE_DIMENSION = 1600;
const VISION_REQUEST_TIMEOUT_MS = 120 * 1000;
const ALLOWED_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const RECOGNITION_STAGES = [
  "preparing",
  "uploading",
  "connecting",
  "request_sent",
  "response_received",
  "completed",
];

const EXIF_TAGS = {
  dateTime: 0x0132,
  exifIfd: 0x8769,
  dateTimeOriginal: 0x9003,
  dateTimeDigitized: 0x9004,
  offsetTime: 0x9010,
  offsetTimeOriginal: 0x9011,
  offsetTimeDigitized: 0x9012,
};

const METER_ICONS = {
  electricity: "electricity.png",
  gas: "gas.png",
  water: "water.png",
};

const DEFAULT_CONFIG = {
  show_name: true,
  show_last_reading: true,
  show_last_reading_timestamp: true,
  show_photo_buttons: true,
  show_history_link: true,
};

const TRANSLATIONS = {
  en: {
    cardName: "Manual Energy Metering",
    cardDescription: "Enter a dated meter reading directly from a dashboard.",
    fallbackName: "Manual meter",
    meterReading: "Meter reading",
    readingDate: "Reading date and time",
    lastReading: "Last reading",
    lastReadingDate: "Last reading date",
    completeHistory: "View complete meter reading history",
    takePhoto: "Take photo",
    uploadPhoto: "Upload photo",
    photoHint:
      "The recognized value is shown for confirmation before saving. For uploaded photos, the capture time is used when available; the reading time remains editable.",
    photoNotConfigured:
      "Configure photo recognition for this meter to use these buttons.",
    recognizing: "The meter reading is being recognized...",
    recognized: "Reading recognized. Confirm or correct the value, then add it.",
    recognitionStatus: "Recognition progress",
    recognitionSteps: {
      preparing: "Prepare image",
      uploading: "Upload image",
      connecting: "Connect to LLM",
      request_sent: "Image and prompt sent",
      response_received: "Response received",
      completed: "Result processed",
    },
    previewAlt: "Selected meter photograph",
    add: "Add reading",
    added: "The meter reading was added.",
    noReadings: "No readings yet",
    required: "Enter a meter reading and a reading date.",
    invalidValue: "Enter a non-negative numeric meter reading.",
    noGrouping: "Do not use thousands separators in the meter reading.",
    unavailable: "The selected meter entity is unavailable.",
    selectEntity: "Select a Manual Energy Metering sensor in the card editor.",
    genericError: "The meter reading could not be added.",
    invalidImage: "Select a JPEG, PNG, or WebP image.",
    imageTooLarge: "The selected image is too large.",
    imageProcessingFailed: "The image could not be prepared for recognition.",
    editor: {
      entity: "Meter entity",
      show_name: "Show meter name",
      show_last_reading: "Show last reading",
      show_last_reading_timestamp: "Show last reading date",
      show_photo_buttons: "Show photo buttons",
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
      vision_not_configured:
        "Configure photo recognition for this meter before using it.",
      vision_invalid_url: "The configured vision provider address is invalid.",
      vision_invalid_image: "The image is invalid or unsupported.",
      vision_image_too_large: "The original image is too large.",
      vision_provider_error: "The vision provider rejected the request.",
      vision_provider_unavailable: "The vision provider is unavailable.",
      vision_provider_timeout:
        "The vision provider did not respond within the time limit.",
      vision_invalid_response:
        "The vision provider returned an invalid meter reading.",
      vision_not_recognized:
        "No meter reading could be recognized reliably in the image.",
    },
  },
  de: {
    cardName: "Manuelle Energiemessung",
    cardDescription:
      "Einen datierten Zählerstand direkt über ein Dashboard erfassen.",
    fallbackName: "Manueller Zähler",
    meterReading: "Zählerstand",
    readingDate: "Ablesedatum und Uhrzeit",
    lastReading: "Letzter Zählerstand",
    lastReadingDate: "Letztes Ablesedatum",
    completeHistory: "Vollständige Zählerstandshistorie anzeigen",
    takePhoto: "Foto aufnehmen",
    uploadPhoto: "Foto hochladen",
    photoHint:
      "Der erkannte Wert wird vor dem Speichern zur Bestätigung angezeigt. Bei hochgeladenen Fotos wird, falls vorhanden, der Aufnahmezeitpunkt verwendet und bleibt editierbar.",
    photoNotConfigured:
      "Konfiguriere die Fotoerkennung für diesen Zähler, um diese Schaltflächen zu verwenden.",
    recognizing: "Der Zählerstand wird erkannt...",
    recognized:
      "Zählerstand erkannt. Bestätige oder korrigiere den Wert und trage ihn anschließend ein.",
    recognitionStatus: "Fortschritt der Erkennung",
    recognitionSteps: {
      preparing: "Bild vorbereiten",
      uploading: "Bild übertragen",
      connecting: "Verbindung zum LLM",
      request_sent: "Bild und Prompt abgeschickt",
      response_received: "Antwort erhalten",
      completed: "Ergebnis verarbeitet",
    },
    previewAlt: "Ausgewähltes Zählerfoto",
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
    invalidImage: "Wähle ein Bild im Format JPEG, PNG oder WebP aus.",
    imageTooLarge: "Das ausgewählte Bild ist zu groß.",
    imageProcessingFailed:
      "Das Bild konnte nicht für die Erkennung vorbereitet werden.",
    editor: {
      entity: "Zählerentität",
      show_name: "Zählername anzeigen",
      show_last_reading: "Letzten Zählerstand anzeigen",
      show_last_reading_timestamp: "Letztes Ablesedatum anzeigen",
      show_photo_buttons: "Schaltflächen für Fotos anzeigen",
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
      vision_not_configured:
        "Konfiguriere zuerst die Fotoerkennung für diesen Zähler.",
      vision_invalid_url:
        "Die konfigurierte Adresse des Vision-Providers ist ungültig.",
      vision_invalid_image: "Das Bild ist ungültig oder wird nicht unterstützt.",
      vision_image_too_large: "Das Originalbild ist zu groß.",
      vision_provider_error: "Der Vision-Provider hat die Anfrage abgelehnt.",
      vision_provider_unavailable: "Der Vision-Provider ist nicht erreichbar.",
      vision_provider_timeout:
        "Der Vision-Provider hat nicht innerhalb des Zeitlimits geantwortet.",
      vision_invalid_response:
        "Der Vision-Provider hat keinen gültigen Zählerstand zurückgegeben.",
      vision_not_recognized:
        "Auf dem Bild konnte kein Zählerstand zuverlässig erkannt werden.",
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
      show_photo_buttons: this._config.show_photo_buttons,
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
      { name: "show_photo_buttons", selector: { boolean: {} } },
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
    this._photoPreview = undefined;
    this._recognitionStage = undefined;
    this._recognitionFailed = false;
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
    if (!this._config?.show_photo_buttons) {
      return 7;
    }
    if (this._photoPreview) {
      return 12;
    }
    return this._recognitionStage ? 10 : 9;
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
    this._photoPreview = undefined;
    this._recognitionStage = undefined;
    this._recognitionFailed = false;
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
      visionConfigured: Boolean(attributes.vision_configured),
      compressImage: attributes.vision_compress_image !== false,
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
    const showPhotoButtons = this._config.show_photo_buttons;
    const hasEntity = Boolean(this._config.entity);
    const available = Boolean(
      data.state && data.state.state !== "unavailable"
    );
    const unit = data.unit ? ` (${data.unit})` : "";
    const photoContent = showPhotoButtons
      ? `${this._renderPhotoControls(
          hasEntity,
          available,
          data.visionConfigured
        )}${this._renderRecognitionProgress()}${this._renderPhotoPreview()}`
      : "";

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
          ${photoContent}
          <form id="reading-form">
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
            <div class="form-actions">
              <button type="submit" ${
                !hasEntity || !available || this._busy ? "disabled" : ""
              }>
                <ha-icon icon="mdi:plus"></ha-icon>
                <span>${this._escape(t.add)}</span>
              </button>
              ${this._renderHistoryLink()}
            </div>
          </form>
          <div class="message ${this._escapeAttribute(
            this._message?.type || ""
          )}" role="status" aria-live="polite">${this._escape(
            this._message?.text ||
              (!hasEntity ? t.selectEntity : !available ? t.unavailable : "")
          )}</div>
        </div>
      </ha-card>
    `;

    const form = this.shadowRoot.querySelector("#reading-form");
    form?.addEventListener("submit", (event) => this._submit(event));
    this.shadowRoot
      .querySelectorAll(".photo-input")
      .forEach((input) =>
        input.addEventListener("change", (event) => this._recognizePhoto(event))
      );
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

  _renderPhotoControls(hasEntity, available, visionConfigured) {
    const disabled =
      !hasEntity || !available || !visionConfigured || this._busy;
    const inputAttributes = `class="photo-input" type="file" accept="image/*" ${
      disabled ? "disabled" : ""
    }`;
    return `
      <section class="photo-capture">
        <div class="photo-buttons">
          <label class="photo-button ${disabled ? "disabled" : ""}">
            <input ${inputAttributes} capture="environment" />
            <ha-icon icon="mdi:camera"></ha-icon>
            <span>${this._escape(this._t.takePhoto)}</span>
          </label>
          <label class="photo-button ${disabled ? "disabled" : ""}">
            <input ${inputAttributes} data-read-photo-timestamp="true" />
            <ha-icon icon="mdi:image-plus"></ha-icon>
            <span>${this._escape(this._t.uploadPhoto)}</span>
          </label>
        </div>
        <p>${this._escape(
          visionConfigured ? this._t.photoHint : this._t.photoNotConfigured
        )}</p>
      </section>
    `;
  }

  _renderRecognitionProgress() {
    const currentIndex = RECOGNITION_STAGES.indexOf(this._recognitionStage);
    if (currentIndex < 0) {
      return "";
    }

    const finished =
      this._recognitionStage === "completed" && !this._recognitionFailed;
    const label =
      this._t.recognitionSteps[this._recognitionStage] ||
      this._recognitionStage;
    const segments = RECOGNITION_STAGES.map((stage, index) => {
      const complete =
        index < currentIndex || (finished && index === currentIndex);
      const stateClass = complete
        ? "complete"
        : index === currentIndex
          ? this._recognitionFailed
            ? "error"
            : "current"
          : "";
      return `<span class="recognition-segment ${stateClass}" title="${this._escapeAttribute(
        this._t.recognitionSteps[stage] || stage
      )}"></span>`;
    }).join("");
    const icon = this._recognitionFailed
      ? "mdi:alert-circle-outline"
      : finished
        ? "mdi:check-circle-outline"
        : "mdi:progress-clock";

    return `
      <section class="recognition-progress">
        <div
          class="recognition-track"
          role="progressbar"
          aria-label="${this._escapeAttribute(this._t.recognitionStatus)}"
          aria-valuemin="0"
          aria-valuemax="${RECOGNITION_STAGES.length}"
          aria-valuenow="${currentIndex + 1}"
          aria-valuetext="${this._escapeAttribute(label)}"
        >${segments}</div>
        <div class="recognition-current ${
          this._recognitionFailed ? "error" : finished ? "complete" : ""
        }" role="status" aria-live="polite">
          <ha-icon icon="${icon}"></ha-icon>
          <span>${this._escape(label)}</span>
          <span class="recognition-count">${currentIndex + 1} / ${
            RECOGNITION_STAGES.length
          }</span>
        </div>
      </section>
    `;
  }

  _renderPhotoPreview() {
    if (!this._photoPreview) {
      return "";
    }
    return `
      <div class="photo-preview">
        <img src="${this._escapeAttribute(
          this._photoPreview
        )}" alt="${this._escapeAttribute(this._t.previewAlt)}" />
        <p>${this._escape(this._t.recognized)}</p>
      </div>
    `;
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

  _setRecognitionStage(stage) {
    if (!RECOGNITION_STAGES.includes(stage)) {
      return;
    }
    this._recognitionStage = stage;
    this._recognitionFailed = false;
    this._render();
  }

  async _readRecognitionResponse(response) {
    const contentType = response.headers.get("Content-Type") || "";
    if (!response.ok || !contentType.includes("text/event-stream")) {
      let payload;
      try {
        payload = await response.json();
      } catch (_error) {
        throw new Error(this._t.genericError);
      }
      if (!response.ok) {
        const error = new Error(payload?.message || this._t.genericError);
        error.code = payload?.code;
        throw error;
      }
      return payload;
    }
    if (!response.body?.getReader) {
      throw new Error(this._t.genericError);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let dataLines = [];
    let result;

    const handleEvent = () => {
      if (!dataLines.length) {
        return;
      }
      const rawPayload = dataLines.join("\n");
      dataLines = [];
      let payload;
      try {
        payload = JSON.parse(rawPayload);
      } catch (_error) {
        throw new Error(this._t.genericError);
      }
      if (payload?.event === "progress") {
        this._setRecognitionStage(payload.stage);
      } else if (payload?.event === "error") {
        const error = new Error(payload.message || this._t.genericError);
        error.code = payload.code;
        throw error;
      } else if (payload?.event === "result") {
        result = payload;
      }
    };
    const processLine = (line) => {
      const normalized = line.endsWith("\r") ? line.slice(0, -1) : line;
      if (normalized === "") {
        handleEvent();
      } else if (normalized.startsWith("data:")) {
        dataLines.push(normalized.slice(5).trimStart());
      }
    };

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
          processLine(buffer.slice(0, newlineIndex));
          buffer = buffer.slice(newlineIndex + 1);
        }
      }
      buffer += decoder.decode();
      if (buffer) {
        buffer.split("\n").forEach(processLine);
      }
      handleEvent();
    } finally {
      reader.releaseLock();
    }

    if (!result) {
      throw new Error(this._t.genericError);
    }
    return result;
  }

  async _recognizePhoto(event) {
    const input = event.target;
    const file = input.files?.[0];
    input.value = "";
    if (!file || this._busy || !this._config.entity) {
      return;
    }

    const entityId = this._config.entity;
    const currentTimestamp = this._formatInputTimestamp(new Date());
    const readPhotoTimestamp = input.dataset.readPhotoTimestamp === "true";
    this._photoPreview = undefined;
    this._recognitionStage = "preparing";
    this._recognitionFailed = false;
    this._busy = true;
    this._message = { text: this._t.recognizing, type: "info" };
    this._render();
    try {
      const [prepared, photoTimestamp] = await Promise.all([
        this._prepareImage(file, this._stateData().compressImage),
        readPhotoTimestamp
          ? this._readPhotoTimestamp(file)
          : Promise.resolve(undefined),
      ]);
      const timestamp = photoTimestamp || currentTimestamp;
      if (photoTimestamp && this._config.entity === entityId) {
        this._formTimestamp = photoTimestamp;
        this._timestampDirty = true;
      }
      this._setRecognitionStage("uploading");
      const controller = new AbortController();
      const timeoutId = window.setTimeout(
        () => controller.abort(),
        VISION_REQUEST_TIMEOUT_MS
      );
      let result;
      try {
        const response = await this._hass.fetchWithAuth(
          `/api/${DOMAIN}/recognize/${encodeURIComponent(entityId)}`,
          {
            method: "POST",
            headers: {
              Accept: "text/event-stream, application/json",
              "Content-Type": prepared.mimeType,
            },
            body: prepared.file,
            signal: controller.signal,
          }
        );
        result = await this._readRecognitionResponse(response);
      } catch (error) {
        if (controller.signal.aborted) {
          const timeoutError = new Error(
            this._t.errors.vision_provider_timeout
          );
          timeoutError.code = "vision_provider_timeout";
          throw timeoutError;
        }
        throw error;
      } finally {
        window.clearTimeout(timeoutId);
      }
      if (this._config.entity !== entityId) {
        return;
      }
      if (this._recognitionStage !== "completed") {
        this._recognitionStage = "completed";
      }
      this._formValue = this._formatInputReading(result.value);
      this._formTimestamp = timestamp;
      this._timestampDirty = true;
      this._photoPreview = prepared.dataUrl;
      this._message = { text: this._t.recognized, type: "success" };
    } catch (error) {
      if (this._config.entity === entityId) {
        this._recognitionFailed = true;
        this._message = {
          text: this._localizedError(error),
          type: "error",
        };
      }
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _readPhotoTimestamp(file) {
    if (!file.size || file.size > MAX_SOURCE_IMAGE_BYTES) {
      return undefined;
    }
    try {
      const view = new DataView(await file.arrayBuffer());
      const tiff = this._findExifTiff(view);
      if (!tiff) {
        return undefined;
      }
      const metadata = this._readExifDateTime(view, tiff);
      return metadata
        ? this._formatExifDateTime(metadata)
        : undefined;
    } catch (_error) {
      // Missing or malformed metadata must not prevent photo recognition.
      return undefined;
    }
  }

  _findExifTiff(view) {
    const hasBytes = (offset, values) =>
      offset >= 0 &&
      offset + values.length <= view.byteLength &&
      values.every((value, index) => view.getUint8(offset + index) === value);
    const tiffRange = (offset, length) => {
      const exifHeader = [0x45, 0x78, 0x69, 0x66, 0x00, 0x00];
      if (length >= exifHeader.length && hasBytes(offset, exifHeader)) {
        offset += exifHeader.length;
        length -= exifHeader.length;
      }
      return length >= 8 && offset + length <= view.byteLength
        ? { offset, length }
        : undefined;
    };

    if (view.byteLength >= 4 && view.getUint16(0, false) === 0xffd8) {
      let cursor = 2;
      while (cursor + 4 <= view.byteLength) {
        if (view.getUint8(cursor) !== 0xff) {
          break;
        }
        while (
          cursor < view.byteLength &&
          view.getUint8(cursor) === 0xff
        ) {
          cursor += 1;
        }
        if (cursor >= view.byteLength) {
          break;
        }
        const marker = view.getUint8(cursor);
        cursor += 1;
        if (marker === 0xda || marker === 0xd9) {
          break;
        }
        if (marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) {
          continue;
        }
        if (cursor + 2 > view.byteLength) {
          break;
        }
        const segmentLength = view.getUint16(cursor, false);
        if (
          segmentLength < 2 ||
          cursor + segmentLength > view.byteLength
        ) {
          break;
        }
        const dataOffset = cursor + 2;
        const dataLength = segmentLength - 2;
        if (
          marker === 0xe1 &&
          hasBytes(dataOffset, [0x45, 0x78, 0x69, 0x66, 0x00, 0x00])
        ) {
          return tiffRange(dataOffset, dataLength);
        }
        cursor += segmentLength;
      }
      return undefined;
    }

    if (
      view.byteLength >= 8 &&
      hasBytes(0, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
    ) {
      let cursor = 8;
      while (cursor + 12 <= view.byteLength) {
        const chunkLength = view.getUint32(cursor, false);
        const dataOffset = cursor + 8;
        const chunkEnd = dataOffset + chunkLength;
        if (chunkEnd + 4 > view.byteLength) {
          break;
        }
        if (hasBytes(cursor + 4, [0x65, 0x58, 0x49, 0x66])) {
          return tiffRange(dataOffset, chunkLength);
        }
        cursor = chunkEnd + 4;
      }
      return undefined;
    }

    if (
      view.byteLength >= 12 &&
      hasBytes(0, [0x52, 0x49, 0x46, 0x46]) &&
      hasBytes(8, [0x57, 0x45, 0x42, 0x50])
    ) {
      let cursor = 12;
      while (cursor + 8 <= view.byteLength) {
        const chunkLength = view.getUint32(cursor + 4, true);
        const dataOffset = cursor + 8;
        if (dataOffset + chunkLength > view.byteLength) {
          break;
        }
        if (hasBytes(cursor, [0x45, 0x58, 0x49, 0x46])) {
          return tiffRange(dataOffset, chunkLength);
        }
        cursor = dataOffset + chunkLength + (chunkLength % 2);
      }
    }
    return undefined;
  }

  _readExifDateTime(view, tiff) {
    const end = tiff.offset + tiff.length;
    const canRead = (offset, length) =>
      offset >= tiff.offset &&
      length >= 0 &&
      offset + length <= end &&
      offset + length <= view.byteLength;
    if (!canRead(tiff.offset, 8)) {
      return undefined;
    }

    const byteOrder = view.getUint16(tiff.offset, false);
    if (byteOrder !== 0x4949 && byteOrder !== 0x4d4d) {
      return undefined;
    }
    const littleEndian = byteOrder === 0x4949;
    const readUint16 = (offset) =>
      canRead(offset, 2)
        ? view.getUint16(offset, littleEndian)
        : undefined;
    const readUint32 = (offset) =>
      canRead(offset, 4)
        ? view.getUint32(offset, littleEndian)
        : undefined;
    if (readUint16(tiff.offset + 2) !== 42) {
      return undefined;
    }

    const readIfd = (relativeOffset) => {
      const entries = new Map();
      if (!Number.isInteger(relativeOffset)) {
        return entries;
      }
      const directoryOffset = tiff.offset + relativeOffset;
      const count = readUint16(directoryOffset);
      if (count === undefined) {
        return entries;
      }
      for (let index = 0; index < count; index += 1) {
        const entryOffset = directoryOffset + 2 + index * 12;
        if (!canRead(entryOffset, 12)) {
          break;
        }
        entries.set(readUint16(entryOffset), {
          offset: entryOffset,
          type: readUint16(entryOffset + 2),
          count: readUint32(entryOffset + 4),
        });
      }
      return entries;
    };
    const readAscii = (entry) => {
      if (
        !entry ||
        entry.type !== 2 ||
        !entry.count ||
        entry.count > 128
      ) {
        return undefined;
      }
      let valueOffset = entry.offset + 8;
      if (entry.count > 4) {
        const relativeOffset = readUint32(entry.offset + 8);
        if (relativeOffset === undefined) {
          return undefined;
        }
        valueOffset = tiff.offset + relativeOffset;
      }
      if (!canRead(valueOffset, entry.count)) {
        return undefined;
      }
      let value = "";
      for (let index = 0; index < entry.count; index += 1) {
        const character = view.getUint8(valueOffset + index);
        if (character === 0) {
          break;
        }
        value += String.fromCharCode(character);
      }
      return value.trim() || undefined;
    };
    const readLong = (entry) =>
      entry?.type === 4 && entry.count === 1
        ? readUint32(entry.offset + 8)
        : undefined;

    const firstIfdOffset = readUint32(tiff.offset + 4);
    if (firstIfdOffset === undefined) {
      return undefined;
    }
    const ifd = readIfd(firstIfdOffset);
    const exifIfdOffset = readLong(ifd.get(EXIF_TAGS.exifIfd));
    const exifIfd =
      exifIfdOffset === undefined ? new Map() : readIfd(exifIfdOffset);
    const fromIfds = (tag) =>
      readAscii(exifIfd.get(tag)) || readAscii(ifd.get(tag));
    const generalOffset = fromIfds(EXIF_TAGS.offsetTime);

    const original = fromIfds(EXIF_TAGS.dateTimeOriginal);
    if (original) {
      return {
        dateTime: original,
        offset:
          fromIfds(EXIF_TAGS.offsetTimeOriginal) || generalOffset,
      };
    }
    const digitized = fromIfds(EXIF_TAGS.dateTimeDigitized);
    if (digitized) {
      return {
        dateTime: digitized,
        offset:
          fromIfds(EXIF_TAGS.offsetTimeDigitized) || generalOffset,
      };
    }
    const dateTime = fromIfds(EXIF_TAGS.dateTime);
    return dateTime
      ? { dateTime, offset: generalOffset }
      : undefined;
  }

  _formatExifDateTime(metadata) {
    const match = /^(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/.exec(
      metadata.dateTime.trim()
    );
    if (!match) {
      return undefined;
    }
    const values = match.slice(1, 6).map((value) => Number(value));
    const [year, month, day, hour, minute] = values;
    if (
      year < 1 ||
      year > 9999 ||
      month < 1 ||
      month > 12 ||
      hour > 23 ||
      minute > 59
    ) {
      return undefined;
    }
    const validationDate = new Date(0);
    validationDate.setUTCFullYear(year, month - 1, day);
    validationDate.setUTCHours(hour, minute, 0, 0);
    if (
      validationDate.getUTCFullYear() !== year ||
      validationDate.getUTCMonth() !== month - 1 ||
      validationDate.getUTCDate() !== day ||
      validationDate.getUTCHours() !== hour ||
      validationDate.getUTCMinutes() !== minute
    ) {
      return undefined;
    }

    const pad = (value) => String(value).padStart(2, "0");
    const localTimestamp =
      String(year).padStart(4, "0") +
      "-" +
      pad(month) +
      "-" +
      pad(day) +
      "T" +
      pad(hour) +
      ":" +
      pad(minute) +
      ":" +
      "00";
    const offset = String(metadata.offset || "")
      .trim()
      .replace(/^([+-]\d{2})(\d{2})$/, "$1:$2");
    if (/^(?:Z|[+-]\d{2}:\d{2})$/.test(offset)) {
      const instant = new Date(localTimestamp + offset);
      if (!Number.isNaN(instant.getTime())) {
        return this._formatPhotoInstant(instant);
      }
    }
    return localTimestamp;
  }

  _formatPhotoInstant(date) {
    const parts = Object.fromEntries(
      new Intl.DateTimeFormat("en-CA", {
        timeZone: this._timeZone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
      })
        .formatToParts(date)
        .filter((part) => part.type !== "literal")
        .map((part) => [part.type, part.value])
    );
    return (
      parts.year +
      "-" +
      parts.month +
      "-" +
      parts.day +
      "T" +
      parts.hour +
      ":" +
      parts.minute +
      ":" +
      "00"
    );
  }

  async _prepareImage(file, compressImage) {
    const sourceMimeType = file.type.toLowerCase();
    if (!sourceMimeType.startsWith("image/") || !file.size) {
      throw new Error(this._t.invalidImage);
    }
    if (file.size > MAX_SOURCE_IMAGE_BYTES) {
      throw new Error(this._t.imageTooLarge);
    }

    let uploadFile = file;
    let mimeType = sourceMimeType;
    if (compressImage) {
      const objectUrl = URL.createObjectURL(file);
      const image = new Image();
      try {
        await new Promise((resolve, reject) => {
          image.onload = resolve;
          image.onerror = reject;
          image.src = objectUrl;
        });
      } catch (_error) {
        throw new Error(this._t.imageProcessingFailed);
      } finally {
        URL.revokeObjectURL(objectUrl);
      }
      if (!image.naturalWidth || !image.naturalHeight) {
        throw new Error(this._t.imageProcessingFailed);
      }

      const scale = Math.min(
        1,
        MAX_IMAGE_DIMENSION / Math.max(image.naturalWidth, image.naturalHeight)
      );
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      const context = canvas.getContext("2d");
      if (!context) {
        throw new Error(this._t.imageProcessingFailed);
      }
      context.fillStyle = "#fff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);

      let blob;
      for (const quality of [0.86, 0.72, 0.58, 0.44]) {
        blob = await new Promise((resolve) =>
          canvas.toBlob(resolve, "image/jpeg", quality)
        );
        if (!blob || blob.size <= MAX_COMPRESSED_IMAGE_BYTES) {
          break;
        }
      }
      if (!blob) {
        throw new Error(this._t.imageProcessingFailed);
      }
      if (blob.size > MAX_COMPRESSED_IMAGE_BYTES) {
        throw new Error(this._t.imageTooLarge);
      }
      uploadFile = blob;
      mimeType = "image/jpeg";
    } else if (!ALLOWED_IMAGE_TYPES.has(mimeType)) {
      throw new Error(this._t.invalidImage);
    }

    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error(this._t.imageProcessingFailed));
      reader.readAsDataURL(uploadFile);
    });
    if (typeof dataUrl !== "string" || !dataUrl.includes(",")) {
      throw new Error(this._t.imageProcessingFailed);
    }
    return {
      file: uploadFile,
      dataUrl,
      mimeType,
    };
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

  _formatInputReading(value) {
    return new Intl.NumberFormat(this._locale, {
      maximumFractionDigits: 20,
      useGrouping: false,
    }).format(value);
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
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 18px;
        box-shadow: 0 12px 34px rgba(0, 0, 0, 0.08);
      }
      .content { padding: 24px; }
      h2 {
        margin: 0 0 12px;
        font-size: 1.25rem;
        line-height: 1.3;
        font-weight: 600;
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
        margin: 0 0 18px;
      }
      .summary div {
        min-width: 0;
      }
      .summary div:only-child { grid-column: 1 / -1; }
      .photo-capture {
        margin: -2px 0 18px;
      }
      .photo-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }
      .photo-button {
        position: relative;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        min-height: 42px;
        padding: 0 13px;
        border: 1px solid var(--divider-color);
        border-radius: 11px;
        color: var(--primary-text-color);
        background: var(--secondary-background-color);
        font-weight: 650;
        cursor: pointer;
      }
      .photo-button:hover:not(.disabled) {
        border-color: var(--primary-color);
      }
      .photo-button:focus-within {
        outline: 2px solid var(--primary-color);
        outline-offset: 2px;
      }
      .photo-button.disabled { opacity: 0.55; cursor: not-allowed; }
      .photo-input {
        position: absolute;
        width: 1px;
        height: 1px;
        opacity: 0;
        pointer-events: none;
      }
      .photo-capture p, .photo-preview p {
        margin: 8px 0 0;
        color: var(--secondary-text-color);
        font-size: 0.8rem;
        line-height: 1.45;
      }
      .recognition-progress {
        margin: -7px 0 18px;
      }
      .recognition-track {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 4px;
      }
      .recognition-segment {
        height: 5px;
        border-radius: 999px;
        background: color-mix(in srgb, var(--primary-text-color) 14%, transparent);
      }
      .recognition-segment.complete,
      .recognition-segment.current {
        background: var(--primary-color);
      }
      .recognition-segment.current {
        animation: recognition-pulse 1.2s ease-in-out infinite;
      }
      .recognition-segment.error {
        background: var(--error-color);
      }
      .recognition-current {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 7px;
        color: var(--secondary-text-color);
        font-size: 0.8rem;
        line-height: 1.3;
      }
      .recognition-current.complete {
        color: var(--success-color, #2e7d32);
      }
      .recognition-current.error {
        color: var(--error-color);
      }
      .recognition-current ha-icon {
        --mdc-icon-size: 17px;
      }
      .recognition-count {
        margin-left: auto;
        color: inherit;
        font-variant-numeric: tabular-nums;
      }
      @keyframes recognition-pulse {
        50% { opacity: 0.42; }
      }
      .photo-preview {
        margin: 0 0 18px;
      }
      .photo-preview img {
        display: block;
        width: 100%;
        max-height: 280px;
        border-radius: 12px;
        object-fit: contain;
        background: var(--secondary-background-color);
      }
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
      form {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 16px;
        align-items: start;
      }
      label { display: grid; gap: 7px; min-width: 0; }
      label span {
        color: var(--secondary-text-color);
        font-size: 0.82rem;
        font-weight: 700;
      }
      input {
        width: 100%;
        height: 48px;
        padding: 0 13px;
        border: 1px solid var(--divider-color);
        border-radius: 11px;
        color: var(--primary-text-color);
        background: var(--input-fill-color, var(--secondary-background-color));
        font: inherit;
        outline: none;
        color-scheme: light dark;
      }
      input:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary-color) 22%, transparent);
      }
      button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        min-height: 48px;
        padding: 0 15px;
        border: 0;
        border-radius: 11px;
        color: var(--text-primary-color, #fff);
        background: var(--primary-color);
        font: inherit;
        font-weight: 700;
        cursor: pointer;
      }
      button:focus-visible {
        outline: 2px solid var(--primary-color);
        outline-offset: 2px;
      }
      button:disabled { opacity: 0.55; cursor: wait; }
      ha-icon { --mdc-icon-size: 19px; }
      .form-actions {
        grid-column: 1 / -1;
        display: grid;
        justify-items: start;
        gap: 10px;
      }
      .message {
        min-height: 0;
        margin-top: 0;
        color: var(--secondary-text-color);
        font-size: 0.85rem;
      }
      .message:not(:empty) {
        margin-top: 16px;
        padding: 11px 13px;
        border-radius: 10px;
        font-weight: 600;
      }
      .message.info {
        color: var(--primary-color);
        background: color-mix(in srgb, var(--primary-color) 10%, transparent);
      }
      .message.success {
        color: var(--success-color, #2e7d32);
        background: color-mix(in srgb, var(--success-color, #2e7d32) 10%, transparent);
      }
      .message.error {
        color: var(--error-color);
        background: color-mix(in srgb, var(--error-color) 10%, transparent);
      }
      .history-link {
        display: flex;
        justify-content: flex-start;
        margin-top: 0;
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
      @media (prefers-reduced-motion: reduce) {
        .recognition-segment.current { animation: none; }
      }
      @media (max-width: 620px) {
        .content { padding: 18px; }
        .summary { column-gap: 12px; }
        .photo-buttons { display: grid; grid-template-columns: 1fr 1fr; }
        form { grid-template-columns: 1fr; }
        .form-actions { grid-column: auto; justify-items: stretch; }
        button { width: 100%; }
        .history-link { justify-content: center; }
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
