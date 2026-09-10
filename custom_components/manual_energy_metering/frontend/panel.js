const DOMAIN = "manual_energy_metering";
const STATIC_URL = `/${DOMAIN}_static`;
const MAX_CSV_BYTES = 20 * 1024 * 1024;

const METER_ICONS = {
  electricity: "electricity.png",
  gas: "gas.png",
  water: "water.png",
};

const ICONS = {
  add: "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",
  check: "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
  edit: "M3,17.25V21H6.75L17.81,9.94L14.06,6.19L3,17.25M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87L20.71,7.04Z",
  delete: "M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19C6,20.1 6.9,21 8,21H16C17.1,21 18,20.1 18,19V7H6V19Z",
  download: "M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z",
};

const TRANSLATIONS = {
  en: {
    eyebrow: "Manual Energy Metering",
    back: "Back",
    fallbackTitle: "Meter readings",
    description:
      "Add, edit, delete, and browse this meter's readings. Readings can also be entered between two existing readings. After a reading is added, edited, or deleted, the interpolation is adjusted accordingly.",
    energyStatistic: "Entity for the Energy Dashboard:",
    newReading: "Add a new meter reading",
    editReading: "Edit meter reading",
    dateTime: "Reading date and time",
    meterReading: "Meter reading",
    add: "Add reading",
    save: "Save changes",
    cancel: "Cancel",
    readings: "Meter readings",
    pageDescription: "Page {page} of {pages} · {count} readings in total",
    previous: "Previous",
    next: "Next",
    inputHint: "Enter without thousands separators.",
    noGrouping: "Enter the meter reading without thousands separators.",
    value: "Meter reading",
    actions: "Actions",
    edit: "Edit",
    delete: "Delete",
    exportCsv: "Export CSV",
    exportedCsv: "The CSV file was downloaded.",
    statisticsExportTitle: "Export an Energy Dashboard meter",
    statisticsExportDescription:
      "Select a compatible long-term statistic. Its complete hourly history is exported and can be imported as a new Manual Energy Metering meter in another Home Assistant instance.",
    statisticsSource: "Long-term statistic",
    statisticsMeterType: "Meter type",
    statisticsUnitConversion: "{source} is exported as {target}.",
    exportStatistics: "Export hourly history",
    loadingStatistics: "Loading compatible long-term statistics...",
    noStatistics:
      "No compatible energy or volume statistics with a sum were found.",
    statisticsExported:
      "The hourly history was downloaded. You can now import this CSV file in the target instance.",
    statisticsNegativeWarning:
      "Consumption was negative during the following hours and was replaced with 0 for the export:",
    closeExport: "Close export page",
    importTitle: "Import meter from CSV",
    importDescription:
      "Select a CSV file exported by Manual Energy Metering. The original name is suggested and can be replaced.",
    csvFile: "CSV file",
    importedMeterName: "Name of the new meter",
    importedMeterDetails: "{count} readings · {type} · {unit}",
    importedStatisticsDetails: "{count} hourly values · {type} · {unit}",
    importMeter: "Continue with this meter",
    importComplete:
      "The CSV data was accepted. Return to the Home Assistant setup dialog to configure photo recognition and finish creating the meter.",
    closeImport: "Close import page",
    meterTypes: {
      electricity: "Electricity",
      gas: "Gas",
      water: "Water",
    },
    empty: "No meter readings have been recorded yet.",
    loading: "Loading meter readings...",
    added: "The meter reading was added.",
    updated: "The meter reading was updated.",
    deleted: "The meter reading was deleted.",
    confirmDelete: "Delete {value} from {date}?",
    missingEntry:
      "No meter was selected. Open Manual Energy Metering under Settings > Devices & services and select the gear icon for the desired meter. To export an Energy Dashboard meter, select Add entry instead.",
    required: "Enter a date, a time, and a meter reading.",
    invalidValue: "Enter a valid, non-negative meter reading.",
    genericError: "The operation could not be completed.",
    errors: {
      entry_not_found: "The selected meter does not exist.",
      entry_not_loaded: "The selected meter is not loaded.",
      invalid_timestamp: "Enter a valid date and time.",
      invalid_value: "The reading must be a finite, non-negative number.",
      non_monotonic:
        "This reading would make the meter decrease. Correct an adjacent reading first.",
      reading_not_found: "This meter reading no longer exists.",
      timestamp_exists:
        "Another reading already exists at the selected date and time.",
      csv_invalid_size: "Select a non-empty CSV file up to 20 MiB.",
      csv_invalid_encoding: "The CSV file must use UTF-8 encoding.",
      csv_invalid_format: "This is not a valid exported meter CSV file.",
      csv_inconsistent_metadata: "The meter details differ between CSV rows.",
      csv_invalid_reading: "A CSV reading is incomplete or invalid.",
      csv_too_many_readings: "The CSV file contains too many readings.",
      csv_unsupported_version: "This CSV format version is not supported.",
      csv_invalid_meter: "The meter type and unit in the CSV do not match.",
      csv_duplicate_timestamp: "The CSV contains duplicate reading times.",
      csv_non_monotonic: "The readings in the CSV decrease over time.",
      csv_invalid_timestamp: "The CSV contains an invalid reading time.",
      csv_invalid_value: "The CSV contains an invalid meter reading.",
      csv_invalid_name: "Enter a name for the new meter.",
      csv_flow_not_found: "The import has expired. Start it again.",
      csv_import_failed: "The CSV file could not be imported.",
      csv_export_failed: "The statistics export could not be completed.",
      statistics_not_found:
        "The selected long-term statistic is no longer available.",
      statistics_invalid_meter_type:
        "The selected meter type does not match this statistic.",
      statistics_invalid_data:
        "The long-term statistic contains invalid hourly data.",
      statistics_decreasing:
        "This statistic contains a negative meter state and cannot be imported as an increasing meter.",
      statistics_empty: "The selected statistic has no hourly history.",
    },
  },
  de: {
    eyebrow: "Manuelle Energiemessung",
    back: "Zurück",
    fallbackTitle: "Zählerstände",
    description:
      "Hier kannst du die Zählerstände dieses Zählers eintragen, bearbeiten, löschen und ansehen. Zählerstände können auch zwischen zwei vorhandenen Zählerständen eingetragen werden. Nach dem Eintragen, Bearbeiten oder Löschen eines Zählerstands wird die Interpolation entsprechend angepasst.",
    energyStatistic: "Entität für das Energy Dashboard:",
    newReading: "Neuen Zählerstand eintragen",
    editReading: "Zählerstand bearbeiten",
    dateTime: "Ablesedatum und Uhrzeit",
    meterReading: "Zählerstand",
    add: "Zählerstand eintragen",
    save: "Änderungen speichern",
    cancel: "Abbrechen",
    readings: "Zählerstände",
    pageDescription: "Seite {page} von {pages} · insgesamt {count} Zählerstände",
    previous: "Zurück",
    next: "Weiter",
    inputHint: "Ohne Tausendertrennzeichen eingeben.",
    noGrouping: "Gib den Zählerstand ohne Tausendertrennzeichen ein.",
    value: "Zählerstand",
    actions: "Aktionen",
    edit: "Bearbeiten",
    delete: "Löschen",
    exportCsv: "CSV exportieren",
    exportedCsv: "Die CSV-Datei wurde heruntergeladen.",
    statisticsExportTitle: "Energy-Dashboard-Zähler exportieren",
    statisticsExportDescription:
      "Wähle eine kompatible Langzeitstatistik. Ihre vollständige Stundenhistorie wird exportiert und kann in einer anderen Home-Assistant-Instanz als neuer Zähler der Manuellen Energiemessung importiert werden.",
    statisticsSource: "Langzeitstatistik",
    statisticsMeterType: "Zählertyp",
    statisticsUnitConversion: "{source} wird als {target} exportiert.",
    exportStatistics: "Stundenhistorie exportieren",
    loadingStatistics: "Kompatible Langzeitstatistiken werden geladen...",
    noStatistics:
      "Es wurden keine kompatiblen Energie- oder Volumenstatistiken mit einer Summe gefunden.",
    statisticsExported:
      "Die Stundenhistorie wurde heruntergeladen. Du kannst diese CSV-Datei nun in der Zielinstanz importieren.",
    statisticsNegativeWarning:
      "In den folgenden Stunden war der Verbrauch negativ und wurde für den Export auf 0 gesetzt:",
    closeExport: "Exportseite schließen",
    importTitle: "Zähler aus CSV importieren",
    importDescription:
      "Wähle eine von der Manuellen Energiemessung exportierte CSV-Datei. Der ursprüngliche Name wird vorgeschlagen und kann ersetzt werden.",
    csvFile: "CSV-Datei",
    importedMeterName: "Name des neuen Zählers",
    importedMeterDetails: "{count} Zählerstände · {type} · {unit}",
    importedStatisticsDetails: "{count} Stundenwerte · {type} · {unit}",
    importMeter: "Mit diesem Zähler fortfahren",
    importComplete:
      "Die CSV-Daten wurden übernommen. Kehre zum Einrichtungsdialog von Home Assistant zurück, konfiguriere die Fotoerkennung und schließe das Anlegen des Zählers ab.",
    closeImport: "Importseite schließen",
    meterTypes: {
      electricity: "Strom",
      gas: "Gas",
      water: "Wasser",
    },
    empty: "Es wurden noch keine Zählerstände erfasst.",
    loading: "Zählerstände werden geladen...",
    added: "Der Zählerstand wurde eingetragen.",
    updated: "Der Zählerstand wurde aktualisiert.",
    deleted: "Der Zählerstand wurde gelöscht.",
    confirmDelete: "Soll {value} vom {date} gelöscht werden?",
    missingEntry:
      "Es wurde kein Zähler ausgewählt. Öffne unter Einstellungen > Geräte & Dienste die Manuelle Energiemessung und klicke beim gewünschten Zähler auf das Zahnradsymbol. Zum Exportieren eines Energy-Dashboard-Zählers wähle stattdessen Eintrag hinzufügen.",
    required: "Gib Datum, Uhrzeit und einen Zählerstand ein.",
    invalidValue: "Gib einen gültigen, nicht negativen Zählerstand ein.",
    genericError: "Die Aktion konnte nicht abgeschlossen werden.",
    errors: {
      entry_not_found: "Der ausgewählte Zähler existiert nicht.",
      entry_not_loaded: "Der ausgewählte Zähler ist nicht geladen.",
      invalid_timestamp: "Gib ein gültiges Datum und eine gültige Uhrzeit ein.",
      invalid_value:
        "Der Zählerstand muss eine endliche, nicht negative Zahl sein.",
      non_monotonic:
        "Dieser Wert würde den Zählerstand sinken lassen. Korrigiere zuerst einen benachbarten Zählerstand.",
      reading_not_found: "Dieser Zählerstand existiert nicht mehr.",
      timestamp_exists:
        "Zum ausgewählten Datum und Zeitpunkt existiert bereits ein anderer Zählerstand.",
      csv_invalid_size: "Wähle eine nicht leere CSV-Datei bis 20 MiB.",
      csv_invalid_encoding: "Die CSV-Datei muss UTF-8-kodiert sein.",
      csv_invalid_format: "Dies ist keine gültige exportierte Zähler-CSV-Datei.",
      csv_inconsistent_metadata: "Die Zählerangaben unterscheiden sich zwischen den CSV-Zeilen.",
      csv_invalid_reading: "Ein CSV-Zählerstand ist unvollständig oder ungültig.",
      csv_too_many_readings: "Die CSV-Datei enthält zu viele Zählerstände.",
      csv_unsupported_version: "Diese Version des CSV-Formats wird nicht unterstützt.",
      csv_invalid_meter: "Zählertyp und Einheit in der CSV passen nicht zusammen.",
      csv_duplicate_timestamp: "Die CSV enthält doppelte Ablesezeitpunkte.",
      csv_non_monotonic: "Die Zählerstände in der CSV fallen im Zeitverlauf.",
      csv_invalid_timestamp: "Die CSV enthält einen ungültigen Ablesezeitpunkt.",
      csv_invalid_value: "Die CSV enthält einen ungültigen Zählerstand.",
      csv_invalid_name: "Gib einen Namen für den neuen Zähler ein.",
      csv_flow_not_found: "Der Import ist abgelaufen. Starte ihn erneut.",
      csv_import_failed: "Die CSV-Datei konnte nicht importiert werden.",
      csv_export_failed: "Der Statistikexport konnte nicht abgeschlossen werden.",
      statistics_not_found:
        "Die ausgewählte Langzeitstatistik ist nicht mehr verfügbar.",
      statistics_invalid_meter_type:
        "Der ausgewählte Zählertyp passt nicht zu dieser Statistik.",
      statistics_invalid_data:
        "Die Langzeitstatistik enthält ungültige Stundendaten.",
      statistics_decreasing:
        "Diese Statistik enthält einen negativen Zählerstand und kann nicht als steigender Zähler importiert werden.",
      statistics_empty: "Die ausgewählte Statistik besitzt keine Stundenhistorie.",
    },
  },
};

class ManualEnergyMeteringPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._data = undefined;
    this._entryId = undefined;
    this._page = undefined;
    this._loadingStarted = false;
    this._busy = false;
    this._editingTimestamp = undefined;
    this._formTimestamp = undefined;
    this._formValue = "";
    this._importFlowId = new URLSearchParams(window.location.search).get(
      "import_flow"
    );
    this._exportFlowId = new URLSearchParams(window.location.search).get(
      "export_flow"
    );
    this._importFile = undefined;
    this._importMetadata = undefined;
    this._importName = "";
    this._importComplete = false;
    this._importMessage = undefined;
    this._exportStatistics = undefined;
    this._selectedStatisticId = "";
    this._selectedMeterType = "";
    this._exportComplete = false;
    this._exportMessage = undefined;
    this._statisticsLoading = false;
    this._correctedNegativeHours = [];
    this._exportUnit = "";
  }

  set hass(value) {
    if (this._importFlowId || this._exportFlowId) {
      this._hass = value;
      this._render();
      if (
        this._exportFlowId &&
        this.isConnected &&
        !this._statisticsLoading &&
        this._exportStatistics === undefined
      ) {
        this._loadExportStatistics();
      }
      return;
    }
    const oldLocale = this._locale;
    const oldTimeZone = this._timeZone;
    const entryChanged = this._syncEntryId();
    this._hass = value;
    if ((entryChanged || !this._loadingStarted) && this.isConnected) {
      this._render();
      this._load();
    } else if (
      this._data &&
      (oldLocale !== this._locale || oldTimeZone !== this._timeZone)
    ) {
      this._render();
    }
  }

  get hass() {
    return this._hass;
  }

  set narrow(value) {
    this.toggleAttribute("narrow", Boolean(value));
  }

  connectedCallback() {
    if (this._importFlowId || this._exportFlowId) {
      this._render();
      if (
        this._exportFlowId &&
        this._hass &&
        !this._statisticsLoading &&
        this._exportStatistics === undefined
      ) {
        this._loadExportStatistics();
      }
      return;
    }
    this._syncEntryId();
    this._formTimestamp ||= this._currentTimestamp();
    this._render();
    if (this._hass && !this._loadingStarted) {
      this._load();
    }
  }

  _syncEntryId() {
    const entryId = new URLSearchParams(window.location.search).get(
      "config_entry"
    );
    if (entryId === this._entryId) {
      return false;
    }
    this._entryId = entryId;
    this._data = undefined;
    this._page = undefined;
    this._loadingStarted = false;
    this._busy = false;
    this._editingTimestamp = undefined;
    this._formTimestamp = undefined;
    this._formValue = "";
    return true;
  }

  get _language() {
    return this._locale.toLowerCase().startsWith("de") ? "de" : "en";
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

  get _t() {
    return TRANSLATIONS[this._language];
  }

  async _load() {
    this._loadingStarted = true;
    if (!this._editingTimestamp) {
      this._formTimestamp = this._currentTimestamp();
    }
    if (!this._entryId) {
      this._render();
      return;
    }
    const entryId = this._entryId;
    const previousPage = this._data?.page;
    try {
      const data = await this._call(
        `${DOMAIN}/readings/list`,
        this._page ? { page: this._page } : {}
      );
      if (entryId !== this._entryId) {
        return;
      }
      this._data = data;
      this._page = data.page;
      this._busy = false;
      this._render();
    } catch (error) {
      if (entryId !== this._entryId) {
        return;
      }
      if (previousPage !== undefined) {
        this._page = previousPage;
      }
      this._busy = false;
      this._render();
      this._showMessage(this._localizedError(error), "error");
    }
  }

  async _call(type, data = {}) {
    return this._hass.callWS({
      type,
      config_entry_id: this._entryId,
      ...data,
    });
  }

  _render() {
    if (this._exportFlowId) {
      this._renderStatisticsExport();
      return;
    }
    if (this._importFlowId) {
      this._renderImport();
      return;
    }
    const t = this._t;
    const title = this._data?.name || t.fallbackTitle;
    const unit = this._data?.unit ? ` (${this._data.unit})` : "";
    const readings = this._data?.readings || [];
    const loading = this._entryId && !this._data;
    const showForm = Boolean(
      this._editingTimestamp || this._data?.is_latest_page
    );

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <main>
        <header class="hero">
          <button
            id="back-button"
            class="back-button"
            type="button"
            aria-label="${this._escapeAttribute(t.back)}"
            title="${this._escapeAttribute(t.back)}"
          ><ha-icon icon="mdi:arrow-left"></ha-icon></button>
          <div class="hero-content">
            <div class="eyebrow">${this._escape(t.eyebrow)}</div>
            <h1>
              <span>${this._escape(title)}</span>${this._renderMeterTypeIcon()}
            </h1>
            <p>${this._escape(t.description)}</p>
            ${this._renderStatisticId()}
          </div>
        </header>

        ${showForm ? this._renderEntryForm(unit) : ""}
        <div class="message panel-message" role="status" aria-live="polite"></div>

        <section class="readings-card" aria-labelledby="readings-title">
          <div class="section-heading table-heading">
            <div>
              <h2 id="readings-title">${this._escape(t.readings)}</h2>
              <p>${this._escape(this._formatPageDescription())}</p>
            </div>
            ${
              this._data
                ? `<div class="heading-actions">
                    <button id="export-csv" class="secondary export-button" type="button">
                      ${this._icon("download")}
                      <span>${this._escape(t.exportCsv)}</span>
                    </button>
                    <span class="count">${this._formatNumber(
                      this._data.reading_count
                    )}</span>
                  </div>`
                : ""
            }
          </div>
          ${
            loading
              ? `<div class="empty">${this._escape(t.loading)}</div>`
              : !this._entryId
                ? `<div class="empty error-text">${this._escape(
                    t.missingEntry
                  )}</div>`
                : readings.length === 0
                  ? `<div class="empty">${this._escape(t.empty)}</div>`
                  : `${this._renderTable(readings)}${this._renderPagination()}`
          }
        </section>
      </main>
    `;

    this.shadowRoot
      .querySelector("#reading-form")
      ?.addEventListener("submit", (event) => this._submit(event));
    this.shadowRoot
      .querySelector("#back-button")
      ?.addEventListener("click", () => window.history.back());
    this.shadowRoot
      .querySelector("#export-csv")
      ?.addEventListener("click", () => this._exportCsv());
    this.shadowRoot
      .querySelector("#cancel-edit")
      ?.addEventListener("click", () => this._cancelEdit());
    this.shadowRoot.querySelectorAll("[data-action='edit']").forEach((button) =>
      button.addEventListener("click", () =>
        this._editReading(Number(button.dataset.index))
      )
    );
    this.shadowRoot
      .querySelectorAll("[data-action='delete']")
      .forEach((button) =>
        button.addEventListener("click", () =>
          this._deleteReading(Number(button.dataset.index))
        )
      );
    this.shadowRoot.querySelectorAll("[data-page]").forEach((button) =>
      button.addEventListener("click", () =>
        this._goToPage(Number(button.dataset.page))
      )
    );
    this._setBusy(this._busy);
  }

  _renderStatisticsExport() {
    const t = this._t;
    const statistics = this._exportStatistics || [];
    const selected = statistics.find(
      (item) => item.statistic_id === this._selectedStatisticId
    );
    const meterTypes = selected?.meter_types || [];
    const conversion = selected
      ? t.statisticsUnitConversion
          .replace("{source}", selected.source_unit || "-")
          .replace("{target}", selected.target_unit)
      : "";

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <main class="import-page">
        <header class="hero">
          <button
            id="back-button"
            class="back-button"
            type="button"
            aria-label="${this._escapeAttribute(t.back)}"
            title="${this._escapeAttribute(t.back)}"
          ><ha-icon icon="mdi:arrow-left"></ha-icon></button>
          <div class="hero-content">
            <div class="eyebrow">${this._escape(t.eyebrow)}</div>
            <h1>${this._escape(t.statisticsExportTitle)}</h1>
            <p>${this._escape(t.statisticsExportDescription)}</p>
          </div>
        </header>

        <section class="entry-card import-card">
          ${
            this._exportComplete
              ? `<div class="import-complete">
                  <ha-icon icon="mdi:check-circle-outline"></ha-icon>
                  <p>${this._escape(t.statisticsExported)}</p>
                  ${this._renderNegativeStatisticsWarning()}
                  <button id="close-export" class="primary" type="button">
                    ${this._icon("check")}
                    <span>${this._escape(t.closeExport)}</span>
                  </button>
                </div>`
              : this._exportStatistics === undefined
                ? `<div class="empty no-border">${this._escape(
                    t.loadingStatistics
                  )}</div>`
                : statistics.length === 0
                  ? `<div class="empty no-border">${this._escape(
                      t.noStatistics
                    )}</div>`
                  : `<form id="statistics-export-form" class="import-form">
                      <label>
                        <span>${this._escape(t.statisticsSource)}</span>
                        <select id="statistics-source" ${
                          this._busy ? "disabled" : ""
                        }>
                          ${statistics
                            .map(
                              (item) => `<option
                                value="${this._escapeAttribute(
                                  item.statistic_id
                                )}"
                                ${
                                  item.statistic_id === this._selectedStatisticId
                                    ? "selected"
                                    : ""
                                }
                              >${this._escape(
                                `${item.name} (${item.statistic_id})`
                              )}</option>`
                            )
                            .join("")}
                        </select>
                      </label>
                      <label>
                        <span>${this._escape(t.statisticsMeterType)}</span>
                        <select id="statistics-meter-type" ${
                          this._busy ? "disabled" : ""
                        }>
                          ${meterTypes
                            .map(
                              (meterType) => `<option
                                value="${this._escapeAttribute(meterType)}"
                                ${
                                  meterType === this._selectedMeterType
                                    ? "selected"
                                    : ""
                                }
                              >${this._escape(
                                t.meterTypes[meterType] || meterType
                              )}</option>`
                            )
                            .join("")}
                        </select>
                        <small>${this._escape(conversion)}</small>
                      </label>
                      <div class="form-actions">
                        <button class="primary" type="submit" ${
                          this._busy ? "disabled" : ""
                        }>
                          ${this._icon("download")}
                          <span>${this._escape(t.exportStatistics)}</span>
                        </button>
                      </div>
                    </form>`
          }
          <div class="message ${this._escapeAttribute(
            this._exportMessage?.type || ""
          )}" role="status" aria-live="polite">${this._escape(
            this._exportMessage?.text || ""
          )}</div>
        </section>
      </main>
    `;

    this.shadowRoot
      .querySelector("#back-button")
      ?.addEventListener("click", () => this._closeImportPage());
    this.shadowRoot
      .querySelector("#close-export")
      ?.addEventListener("click", () => this._closeImportPage());
    this.shadowRoot
      .querySelector("#statistics-source")
      ?.addEventListener("change", (event) => {
        this._selectedStatisticId = event.target.value;
        const item = this._exportStatistics.find(
          (candidate) => candidate.statistic_id === event.target.value
        );
        this._selectedMeterType = item?.meter_types?.[0] || "";
        this._exportMessage = undefined;
        this._render();
      });
    this.shadowRoot
      .querySelector("#statistics-meter-type")
      ?.addEventListener("change", (event) => {
        this._selectedMeterType = event.target.value;
        this._exportMessage = undefined;
      });
    this.shadowRoot
      .querySelector("#statistics-export-form")
      ?.addEventListener("submit", (event) =>
        this._submitStatisticsExport(event)
      );
  }

  async _loadExportStatistics() {
    this._statisticsLoading = true;
    this._exportMessage = undefined;
    this._render();
    try {
      this._exportStatistics = await this._hass.callWS({
        type: `${DOMAIN}/statistics/list`,
      });
      const first = this._exportStatistics[0];
      this._selectedStatisticId = first?.statistic_id || "";
      this._selectedMeterType = first?.meter_types?.[0] || "";
    } catch (error) {
      this._exportStatistics = [];
      this._exportMessage = {
        text: this._localizedError(error),
        type: "error",
      };
    } finally {
      this._statisticsLoading = false;
      this._render();
    }
  }

  async _submitStatisticsExport(event) {
    event.preventDefault();
    if (
      this._busy ||
      !this._selectedStatisticId ||
      !this._selectedMeterType
    ) {
      return;
    }
    this._busy = true;
    this._exportMessage = undefined;
    this._correctedNegativeHours = [];
    this._render();
    try {
      const exported = await this._hass.callWS({
        type: `${DOMAIN}/statistics/export`,
        statistic_id: this._selectedStatisticId,
        meter_type: this._selectedMeterType,
      });
      this._correctedNegativeHours = Array.isArray(
        exported.corrected_negative_hours
      )
        ? exported.corrected_negative_hours.filter(
            (item) =>
              item &&
              typeof item.start === "string" &&
              typeof item.value === "number" &&
              Number.isFinite(item.value)
          )
        : [];
      this._exportUnit =
        typeof exported.unit === "string" ? exported.unit : "";
      this._downloadCsv(exported);
      const response = await this._hass.fetchWithAuth(
        `/api/${DOMAIN}/csv/export-complete?flow_id=${encodeURIComponent(
          this._exportFlowId
        )}`,
        { method: "POST" }
      );
      await this._readCsvResponse(response);
      this._exportComplete = true;
    } catch (error) {
      this._exportMessage = {
        text: this._localizedError(error),
        type: "error",
      };
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _renderNegativeStatisticsWarning() {
    if (!this._correctedNegativeHours.length) {
      return "";
    }
    return `
      <div class="statistics-warning" role="alert">
        <strong>${this._escape(this._t.statisticsNegativeWarning)}</strong>
        <ul>
          ${this._correctedNegativeHours
            .map(
              (item) =>
                `<li>${this._escape(
                  this._formatStatisticsCorrection(item)
                )}</li>`
            )
            .join("")}
        </ul>
      </div>
    `;
  }

  _formatStatisticsHour(timestamp) {
    const start = new Date(timestamp);
    if (Number.isNaN(start.getTime())) {
      return timestamp;
    }
    const end = new Date(start.getTime() + 60 * 60 * 1000);
    const formatter = new Intl.DateTimeFormat(this._locale, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: this._timeZone,
    });
    return `${formatter.format(start)} - ${formatter.format(end)}`;
  }

  _formatStatisticsCorrection(item) {
    const unit = this._exportUnit ? ` ${this._exportUnit}` : "";
    return `${this._formatStatisticsHour(item.start)}: ${this._formatNumber(
      item.value
    )}${unit}`;
  }

  _renderImport() {
    const t = this._t;
    const metadata = this._importMetadata;
    const meterType = metadata
      ? t.meterTypes[metadata.meter_type] || metadata.meter_type
      : "";
    const detailsTemplate = metadata?.statistics_count
      ? t.importedStatisticsDetails
      : t.importedMeterDetails;
    const details = metadata
      ? detailsTemplate
          .replace(
            "{count}",
            this._formatNumber(
              metadata.statistics_count || metadata.reading_count
            )
          )
          .replace("{type}", meterType)
          .replace("{unit}", metadata.unit)
      : "";

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <main class="import-page">
        <header class="hero">
          <button
            id="back-button"
            class="back-button"
            type="button"
            aria-label="${this._escapeAttribute(t.back)}"
            title="${this._escapeAttribute(t.back)}"
          ><ha-icon icon="mdi:arrow-left"></ha-icon></button>
          <div class="hero-content">
            <div class="eyebrow">${this._escape(t.eyebrow)}</div>
            <h1>${this._escape(t.importTitle)}</h1>
            <p>${this._escape(t.importDescription)}</p>
          </div>
        </header>

        <section class="entry-card import-card">
          ${
            this._importComplete
              ? `<div class="import-complete">
                  <ha-icon icon="mdi:check-circle-outline"></ha-icon>
                  <p>${this._escape(t.importComplete)}</p>
                  <button id="close-import" class="primary" type="button">
                    ${this._icon("check")}
                    <span>${this._escape(t.closeImport)}</span>
                  </button>
                </div>`
              : `<form id="csv-import-form" class="import-form">
                  <label>
                    <span>${this._escape(t.csvFile)}</span>
                    <input
                      id="csv-import-file"
                      type="file"
                      accept=".csv,text/csv"
                      ${this._busy ? "disabled" : ""}
                    />
                  </label>
                  ${
                    metadata
                      ? `<div class="selected-csv">
                          <strong>${this._escape(this._importFile?.name || "")}</strong>
                          <span>${this._escape(details)}</span>
                        </div>
                        <label>
                          <span>${this._escape(t.importedMeterName)}</span>
                          <input
                            id="imported-meter-name"
                            type="text"
                            maxlength="255"
                            required
                            value="${this._escapeAttribute(this._importName)}"
                            ${this._busy ? "disabled" : ""}
                          />
                        </label>`
                      : ""
                  }
                  <div class="form-actions">
                    <button
                      class="primary"
                      type="submit"
                      ${
                        !metadata ||
                        !this._importFile ||
                        !this._importName.trim() ||
                        this._busy ||
                        !this._hass
                          ? "disabled"
                          : ""
                      }
                    >
                      ${this._icon("add")}
                      <span>${this._escape(t.importMeter)}</span>
                    </button>
                  </div>
                </form>`
          }
          <div class="message ${this._escapeAttribute(
            this._importMessage?.type || ""
          )}" role="status" aria-live="polite">${this._escape(
            this._importMessage?.text || ""
          )}</div>
        </section>
      </main>
    `;

    this.shadowRoot
      .querySelector("#back-button")
      ?.addEventListener("click", () => this._closeImportPage());
    this.shadowRoot
      .querySelector("#csv-import-file")
      ?.addEventListener("change", (event) => this._inspectCsvFile(event));
    this.shadowRoot
      .querySelector("#imported-meter-name")
      ?.addEventListener("input", (event) => {
        this._importName = event.target.value;
        this._importMessage = undefined;
        const submit = this.shadowRoot.querySelector(
          "#csv-import-form button[type='submit']"
        );
        if (submit) {
          submit.disabled = !this._importName.trim();
        }
        this._showMessage("", "");
      });
    this.shadowRoot
      .querySelector("#csv-import-form")
      ?.addEventListener("submit", (event) => this._submitCsvImport(event));
    this.shadowRoot
      .querySelector("#close-import")
      ?.addEventListener("click", () => this._closeImportPage());
  }

  async _inspectCsvFile(event) {
    const file = event.target.files?.[0];
    this._importFile = undefined;
    this._importMetadata = undefined;
    this._importName = "";
    this._importMessage = undefined;
    if (!file) {
      this._render();
      return;
    }
    if (!file.size || file.size > MAX_CSV_BYTES) {
      this._importMessage = {
        text: this._t.errors.csv_invalid_size,
        type: "error",
      };
      this._render();
      return;
    }

    this._busy = true;
    this._render();
    try {
      const response = await this._hass.fetchWithAuth(
        `/api/${DOMAIN}/csv/inspect`,
        {
          method: "POST",
          headers: { "Content-Type": "text/csv" },
          body: file,
        }
      );
      const metadata = await this._readCsvResponse(response);
      this._importFile = file;
      this._importMetadata = metadata;
      this._importName = metadata.name;
    } catch (error) {
      this._importMessage = {
        text: this._localizedError(error),
        type: "error",
      };
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _submitCsvImport(event) {
    event.preventDefault();
    const name = this._importName.trim();
    if (
      this._busy ||
      !this._importFile ||
      !this._importMetadata ||
      !name ||
      !this._hass
    ) {
      if (!name) {
        this._importMessage = {
          text: this._t.errors.csv_invalid_name,
          type: "error",
        };
        this._render();
      }
      return;
    }

    this._busy = true;
    this._importMessage = undefined;
    this._render();
    const query = new URLSearchParams({
      flow_id: this._importFlowId,
      name,
    });
    try {
      const response = await this._hass.fetchWithAuth(
        `/api/${DOMAIN}/csv/import?${query.toString()}`,
        {
          method: "POST",
          headers: { "Content-Type": "text/csv" },
          body: this._importFile,
        }
      );
      await this._readCsvResponse(response);
      this._importComplete = true;
    } catch (error) {
      this._importMessage = {
        text: this._localizedError(error),
        type: "error",
      };
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _readCsvResponse(response) {
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

  _closeImportPage() {
    window.close();
    window.setTimeout(() => {
      if (!window.closed) {
        window.history.back();
      }
    }, 100);
  }

  _renderEntryForm(unit) {
    const t = this._t;
    return `
      <section class="entry-card" aria-labelledby="entry-title">
        <div class="section-heading">
          <div>
            <h2 id="entry-title">${this._escape(
              this._editingTimestamp ? t.editReading : t.newReading
            )}</h2>
          </div>
        </div>
        <form id="reading-form" class="reading-form">
          <label>
            <span>${this._escape(t.dateTime)}</span>
            <input
              id="timestamp"
              name="timestamp"
              type="datetime-local"
              step="1"
              required
              value="${this._escapeAttribute(this._formTimestamp || "")}"
            />
          </label>
          <label>
            <span>${this._escape(t.meterReading)}${this._escape(unit)}</span>
            <input
              id="value"
              name="value"
              type="text"
              inputmode="decimal"
              autocomplete="off"
              required
              aria-describedby="value-hint"
              value="${this._escapeAttribute(this._formValue)}"
            />
            <small id="value-hint">${this._escape(t.inputHint)}</small>
          </label>
          <div class="form-actions">
            <button class="primary" type="submit">
              ${this._icon(this._editingTimestamp ? "check" : "add")}
              <span>${this._escape(
                this._editingTimestamp ? t.save : t.add
              )}</span>
            </button>
            ${
              this._editingTimestamp
                ? `<button id="cancel-edit" class="secondary" type="button">${this._escape(
                    t.cancel
                  )}</button>`
                : ""
            }
          </div>
        </form>
      </section>
    `;
  }

  async _exportCsv() {
    if (this._busy || !this._data) {
      return;
    }
    this._setBusy(true);
    try {
      const exported = await this._call(`${DOMAIN}/readings/export`);
      this._downloadCsv(exported);
      this._busy = false;
      this._render();
      this._showMessage(this._t.exportedCsv, "success");
    } catch (error) {
      this._setBusy(false);
      this._showMessage(this._localizedError(error), "error");
    }
  }

  _downloadCsv(exported) {
    const blob = new Blob([exported.content], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = exported.filename;
    this.shadowRoot.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  _renderTable(readings) {
    const t = this._t;
    return `
      <div class="readings-table" role="table">
        <div class="table-header" role="row">
          <div role="columnheader">${this._escape(t.dateTime)}</div>
          <div role="columnheader">${this._escape(t.value)}</div>
          <div role="columnheader" class="actions-heading">${this._escape(
            t.actions
          )}</div>
        </div>
        ${readings
          .map(
            (reading, index) => `
              <div class="reading-row" role="row">
                <div class="reading-date" role="cell" data-label="${this._escapeAttribute(
                  t.dateTime
                )}">${this._escape(this._formatDate(reading.timestamp))}</div>
                <div class="reading-value" role="cell" data-label="${this._escapeAttribute(
                  t.value
                )}">${this._escape(this._formatReading(reading.value))}</div>
                <div class="row-actions" role="cell">
                  <button
                    class="action-button edit"
                    type="button"
                    data-action="edit"
                    data-index="${index}"
                    aria-label="${this._escapeAttribute(t.edit)}"
                    title="${this._escapeAttribute(t.edit)}"
                  >
                    ${this._icon("edit")}
                    <span>${this._escape(t.edit)}</span>
                  </button>
                  <button
                    class="action-button delete"
                    type="button"
                    data-action="delete"
                    data-index="${index}"
                    aria-label="${this._escapeAttribute(t.delete)}"
                    title="${this._escapeAttribute(t.delete)}"
                  >
                    ${this._icon("delete")}
                    <span>${this._escape(t.delete)}</span>
                  </button>
                </div>
              </div>
            `
          )
          .join("")}
      </div>
    `;
  }

  _formatPageDescription() {
    if (!this._data) {
      return "";
    }
    return this._t.pageDescription
      .replace("{page}", this._formatNumber(this._data.page))
      .replace("{pages}", this._formatNumber(this._data.page_count))
      .replace("{count}", this._formatNumber(this._data.reading_count));
  }

  _renderPagination() {
    if (!this._data || this._data.page_count <= 1) {
      return "";
    }
    const { page, page_count: pageCount } = this._data;
    const items = this._paginationItems(page, pageCount)
      .map((item) => {
        if (item === null) {
          return '<span class="ellipsis" aria-hidden="true">…</span>';
        }
        const active = item === page;
        return `<button
          class="page-button${active ? " active" : ""}"
          type="button"
          data-page="${item}"
          ${active ? 'aria-current="page"' : ""}
        >${this._formatNumber(item)}</button>`;
      })
      .join("");
    return `
      <nav class="pagination" aria-label="${this._escapeAttribute(
        this._t.readings
      )}">
        <button
          class="page-nav"
          type="button"
          data-page="${page - 1}"
          ${page === 1 ? "disabled" : ""}
        >${this._escape(this._t.previous)}</button>
        <div class="page-numbers">${items}</div>
        <button
          class="page-nav"
          type="button"
          data-page="${page + 1}"
          ${page === pageCount ? "disabled" : ""}
        >${this._escape(this._t.next)}</button>
      </nav>
    `;
  }

  _paginationItems(page, pageCount) {
    if (pageCount <= 7) {
      return Array.from({ length: pageCount }, (_, index) => index + 1);
    }
    const pages = [...new Set([1, pageCount, page - 1, page, page + 1])]
      .filter((item) => item >= 1 && item <= pageCount)
      .sort((left, right) => left - right);
    const items = [];
    pages.forEach((item, index) => {
      if (index > 0 && item - pages[index - 1] > 1) {
        items.push(null);
      }
      items.push(item);
    });
    return items;
  }

  async _goToPage(page) {
    if (this._busy || page === this._page || page < 1) {
      return;
    }
    this._editingTimestamp = undefined;
    this._formValue = "";
    this._page = page;
    this._setBusy(true);
    await this._load();
  }

  async _submit(event) {
    event.preventDefault();
    const timestampInput = this.shadowRoot.querySelector("#timestamp");
    const valueInput = this.shadowRoot.querySelector("#value");
    const timestamp = timestampInput.value;
    const rawValue = valueInput.value;
    const value = this._parseNumber(rawValue);

    if (!timestamp || rawValue.trim() === "") {
      this._showMessage(this._t.required, "error");
      return;
    }
    if (this._hasGroupingSeparator(rawValue)) {
      this._showMessage(this._t.noGrouping, "error");
      return;
    }
    if (!Number.isFinite(value) || value < 0) {
      this._showMessage(this._t.invalidValue, "error");
      return;
    }

    this._setBusy(true);
    try {
      if (this._editingTimestamp) {
        this._data = await this._call(`${DOMAIN}/readings/update`, {
          original_timestamp: this._editingTimestamp,
          timestamp,
          value,
          page: this._page,
        });
        this._page = this._data.page;
        this._editingTimestamp = undefined;
        this._formTimestamp = this._currentTimestamp();
        this._formValue = "";
        this._busy = false;
        this._render();
        this._showMessage(this._t.updated, "success");
      } else {
        this._data = await this._call(`${DOMAIN}/readings/add`, {
          timestamp,
          value,
        });
        this._page = this._data.page;
        this._formTimestamp = this._currentTimestamp();
        this._formValue = "";
        this._busy = false;
        this._render();
        this._showMessage(this._t.added, "success");
      }
    } catch (error) {
      this._setBusy(false);
      this._showMessage(this._localizedError(error), "error");
    }
  }

  _editReading(index) {
    const reading = this._data.readings[index];
    this._editingTimestamp = reading.timestamp;
    this._formTimestamp = this._formatInputTimestamp(
      new Date(reading.timestamp),
      false
    );
    this._formValue = this._formatInputNumber(reading.value);
    this._render();
    this.shadowRoot.querySelector("#value")?.focus();
    this.shadowRoot.querySelector(".entry-card")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  _cancelEdit() {
    this._editingTimestamp = undefined;
    this._formTimestamp = this._currentTimestamp();
    this._formValue = "";
    this._render();
  }

  async _deleteReading(index) {
    const reading = this._data.readings[index];
    const prompt = this._t.confirmDelete
      .replace("{value}", this._formatReading(reading.value))
      .replace("{date}", this._formatDate(reading.timestamp));
    if (!window.confirm(prompt)) {
      return;
    }

    this._setBusy(true);
    try {
      this._data = await this._call(`${DOMAIN}/readings/delete`, {
        timestamp: reading.timestamp,
        page: this._page,
      });
      this._page = this._data.page;
      if (this._editingTimestamp === reading.timestamp) {
        this._editingTimestamp = undefined;
        this._formTimestamp = this._currentTimestamp();
        this._formValue = "";
      }
      this._busy = false;
      this._render();
      this._showMessage(this._t.deleted, "success");
    } catch (error) {
      this._setBusy(false);
      this._showMessage(this._localizedError(error), "error");
    }
  }

  _setBusy(busy) {
    this._busy = busy;
    this.shadowRoot
      ?.querySelectorAll("button, input")
      .forEach((element) => (element.disabled = busy));
  }

  _showMessage(text, type) {
    const element = this.shadowRoot?.querySelector(".message");
    if (!element) {
      return;
    }
    element.textContent = text;
    element.className = `message ${type}`;
  }

  _localizedError(error) {
    const code = error?.code || error?.body?.code;
    return this._t.errors[code] || error?.message || this._t.genericError;
  }

  _currentTimestamp() {
    return this._formatInputTimestamp(new Date(), true);
  }

  _formatInputTimestamp(date, zeroSeconds) {
    const options = {
      timeZone: this._timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hourCycle: "h23",
    };
    const parts = Object.fromEntries(
      new Intl.DateTimeFormat("en-CA", options)
        .formatToParts(date)
        .filter((part) => part.type !== "literal")
        .map((part) => [part.type, part.value])
    );
    const second = zeroSeconds ? "00" : parts.second;
    return `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${second}`;
  }

  _formatDate(timestamp) {
    return new Intl.DateTimeFormat(this._locale, {
      dateStyle: "medium",
      timeStyle: "medium",
      timeZone: this._timeZone,
    }).format(new Date(timestamp));
  }

  _formatReading(value) {
    const number = this._formatNumber(value);
    return this._data?.unit ? `${number} ${this._data.unit}` : number;
  }

  _formatNumber(value) {
    return new Intl.NumberFormat(this._locale, {
      maximumFractionDigits: 20,
      useGrouping: true,
    }).format(value);
  }

  _formatInputNumber(value) {
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
    if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized)) {
      return Number.NaN;
    }
    return Number(normalized);
  }

  _icon(name) {
    return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${ICONS[name]}"></path></svg>`;
  }

  _renderMeterTypeIcon() {
    const filename = METER_ICONS[this._data?.meter_type];
    if (!filename) {
      return "";
    }
    return `<img class="meter-type-icon" src="${STATIC_URL}/icons/${filename}" alt="" aria-hidden="true" />`;
  }

  _renderStatisticId() {
    const statisticId = this._data?.statistic_id;
    if (!statisticId) {
      return "";
    }
    return `
      <div class="statistic-reference">
        <span>${this._escape(this._t.energyStatistic)}</span>
        <code>${this._escape(statisticId)}</code>
      </div>
    `;
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
      :host {
        display: block;
        min-height: 100%;
        color: var(--primary-text-color);
        background: var(--primary-background-color);
        box-sizing: border-box;
      }
      * { box-sizing: border-box; }
      main {
        width: min(1080px, calc(100% - 32px));
        margin: 0 auto;
        padding: 40px 0 64px;
      }
      .hero {
        display: grid;
        grid-template-columns: 48px minmax(0, 1fr);
        gap: 8px;
        max-width: 876px;
        margin-bottom: 28px;
      }
      .hero-content { min-width: 0; }
      .back-button {
        display: grid;
        place-items: center;
        width: 48px;
        height: 48px;
        min-height: 0;
        margin-top: 18px;
        padding: 0;
        border: 0;
        border-radius: 50%;
        color: var(--primary-text-color);
        background: transparent;
        cursor: pointer;
      }
      .back-button:hover { background: var(--secondary-background-color); }
      .back-button:focus-visible {
        outline: 2px solid var(--primary-color);
        outline-offset: 2px;
      }
      .back-button ha-icon { width: 24px; height: 24px; }
      .eyebrow {
        color: var(--primary-color);
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 8px;
      }
      h1, h2, p { margin-top: 0; }
      h1 {
        font-size: clamp(2rem, 5vw, 3.35rem);
        line-height: 1.02;
        letter-spacing: -0.045em;
        margin-bottom: 16px;
      }
      .meter-type-icon {
        width: auto;
        height: 0.72em;
        margin-left: 0.24em;
        vertical-align: -0.035em;
      }
      h2 { font-size: 1.25rem; margin-bottom: 0; }
      .hero p, .section-heading p {
        color: var(--secondary-text-color);
        line-height: 1.6;
        margin-bottom: 0;
      }
      .statistic-reference {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 6px 10px;
        margin-top: 14px;
        font: inherit;
        line-height: 1.6;
      }
      .statistic-reference span {
        color: var(--secondary-text-color);
      }
      .statistic-reference code {
        max-width: 100%;
        padding: 4px 7px;
        border-radius: 7px;
        color: var(--primary-text-color);
        background: var(--secondary-background-color);
        font: inherit;
        overflow-wrap: anywhere;
        user-select: all;
      }
      .entry-card, .readings-card {
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 18px;
        box-shadow: 0 12px 34px rgba(0, 0, 0, 0.08);
        overflow: hidden;
      }
      .entry-card { padding: 24px; margin-bottom: 22px; }
      .section-heading {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        align-items: center;
        margin-bottom: 18px;
      }
      .heading-actions {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .reading-form {
        display: grid;
        grid-template-columns: minmax(230px, 1.15fr) minmax(190px, 0.85fr) auto;
        gap: 16px;
        align-items: start;
      }
      label { display: grid; gap: 7px; }
      label span {
        color: var(--secondary-text-color);
        font-size: 0.82rem;
        font-weight: 700;
      }
      label small {
        color: var(--secondary-text-color);
        font-size: 0.74rem;
      }
      input, select {
        width: 100%;
        height: 48px;
        border: 1px solid var(--divider-color);
        border-radius: 11px;
        padding: 0 13px;
        color: var(--primary-text-color);
        background: var(--input-fill-color, var(--secondary-background-color));
        font: inherit;
        outline: none;
      }
      select { padding-right: 36px; }
      input:focus, select:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary-color) 22%, transparent);
      }
      button {
        min-height: 44px;
        border: 0;
        border-radius: 11px;
        padding: 0 15px;
        font: inherit;
        font-weight: 700;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
      }
      button svg { width: 19px; height: 19px; fill: currentColor; flex: none; }
      button:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
      button:disabled { cursor: wait; opacity: 0.55; }
      .form-actions { display: flex; gap: 8px; margin-top: 24px; }
      .primary { height: 48px; color: var(--text-primary-color, #fff); background: var(--primary-color); }
      .secondary { height: 48px; color: var(--primary-text-color); background: var(--secondary-background-color); }
      .export-button { height: 40px; min-height: 40px; }
      .import-card { max-width: 876px; }
      .import-form { display: grid; gap: 18px; }
      .import-form input[type="file"] {
        height: auto;
        min-height: 48px;
        padding: 10px 13px;
      }
      .selected-csv {
        display: grid;
        gap: 4px;
        padding: 13px 15px;
        border-radius: 11px;
        color: var(--secondary-text-color);
        background: var(--secondary-background-color);
      }
      .selected-csv strong {
        color: var(--primary-text-color);
        overflow-wrap: anywhere;
      }
      .import-complete {
        display: grid;
        justify-items: start;
        gap: 16px;
      }
      .import-complete > ha-icon {
        color: var(--success-color, #2e7d32);
        --mdc-icon-size: 38px;
      }
      .import-complete p { margin-bottom: 0; line-height: 1.6; }
      .statistics-warning {
        width: 100%;
        padding: 13px 15px;
        border: 1px solid var(--warning-color, #f9a825);
        border-radius: 11px;
        background: color-mix(in srgb, var(--warning-color, #f9a825) 12%, transparent);
        line-height: 1.5;
      }
      .statistics-warning strong { display: block; }
      .statistics-warning ul {
        max-height: 240px;
        margin: 10px 0 0;
        padding-left: 24px;
        overflow: auto;
        font-variant-numeric: tabular-nums;
      }
      .message { min-height: 0; margin-top: 0; }
      .message:not(:empty) {
        margin-top: 16px;
        border-radius: 10px;
        padding: 11px 13px;
        font-weight: 600;
      }
      .message.error { color: var(--error-color); background: color-mix(in srgb, var(--error-color) 10%, transparent); }
      .message.success { color: var(--success-color, #2e7d32); background: color-mix(in srgb, var(--success-color, #2e7d32) 10%, transparent); }
      .panel-message:not(:empty) { margin: 0 0 22px; }
      .readings-card { padding: 24px 0 0; }
      .table-heading { padding: 0 24px; }
      .table-heading p { margin-top: 6px; }
      .count {
        min-width: 40px;
        height: 40px;
        padding: 0 11px;
        display: grid;
        place-items: center;
        border-radius: 999px;
        color: var(--primary-color);
        background: color-mix(in srgb, var(--primary-color) 11%, transparent);
        font-weight: 800;
      }
      .readings-table { border-top: 1px solid var(--divider-color); }
      .table-header, .reading-row {
        display: grid;
        grid-template-columns: minmax(230px, 1.2fr) minmax(170px, 0.8fr) minmax(230px, auto);
        align-items: center;
        column-gap: 18px;
        padding: 14px 24px;
      }
      .table-header {
        min-height: 46px;
        color: var(--secondary-text-color);
        background: var(--secondary-background-color);
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }
      .reading-row { min-height: 70px; border-top: 1px solid var(--divider-color); }
      .table-header + .reading-row { border-top: 0; }
      .reading-date { font-variant-numeric: tabular-nums; }
      .reading-value { font-size: 1.05rem; font-weight: 800; font-variant-numeric: tabular-nums; }
      .actions-heading { text-align: right; }
      .row-actions { display: flex; justify-content: flex-end; gap: 8px; }
      .action-button { min-height: 38px; padding: 0 11px; background: var(--secondary-background-color); color: var(--primary-text-color); }
      .action-button.edit:hover { color: var(--primary-color); }
      .action-button.delete:hover { color: var(--error-color); }
      .empty { border-top: 1px solid var(--divider-color); padding: 36px 24px; color: var(--secondary-text-color); text-align: center; }
      .empty.no-border { border-top: 0; }
      .error-text { color: var(--error-color); }
      .pagination {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr) auto;
        align-items: center;
        gap: 14px;
        padding: 18px 24px;
        border-top: 1px solid var(--divider-color);
        background: var(--secondary-background-color);
      }
      .page-numbers {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 6px;
        min-width: 0;
      }
      .page-button, .page-nav {
        min-height: 38px;
        color: var(--primary-text-color);
        background: var(--card-background-color);
      }
      .page-button { min-width: 38px; padding: 0 10px; }
      .page-button.active {
        color: var(--text-primary-color, #fff);
        background: var(--primary-color);
      }
      .ellipsis { color: var(--secondary-text-color); padding: 0 3px; }

      @media (max-width: 760px) {
        main { width: min(100% - 20px, 620px); padding: 24px 0 40px; }
        .hero {
          grid-template-columns: 44px minmax(0, 1fr);
          gap: 4px;
          padding: 0;
        }
        .back-button { width: 44px; height: 44px; margin-top: 16px; }
        h1 { font-size: 2.2rem; }
        .entry-card { padding: 18px; }
        .reading-form { grid-template-columns: 1fr; }
        .form-actions { flex-wrap: wrap; margin-top: 0; }
        .form-actions button { flex: 1 1 180px; }
        .readings-card { padding-top: 18px; }
        .table-heading { padding: 0 18px; flex-wrap: wrap; }
        .table-header { display: none; }
        .reading-row {
          grid-template-columns: 1fr;
          gap: 12px;
          padding: 18px;
        }
        .reading-row:first-child { border-top: 1px solid var(--divider-color); }
        .reading-date::before, .reading-value::before {
          content: attr(data-label);
          display: block;
          margin-bottom: 3px;
          color: var(--secondary-text-color);
          font-size: 0.72rem;
          font-weight: 800;
          letter-spacing: 0.05em;
          text-transform: uppercase;
        }
        .row-actions { justify-content: stretch; }
        .action-button { flex: 1; }
        .pagination {
          grid-template-columns: 1fr 1fr;
          padding: 14px 18px;
        }
        .page-numbers {
          grid-column: 1 / -1;
          grid-row: 1;
          flex-wrap: wrap;
        }
        .page-nav { grid-row: 2; }
      }

      @media (max-width: 420px) {
        .row-actions { display: grid; grid-template-columns: 1fr 1fr; }
        .section-heading { align-items: flex-start; }
        .heading-actions { width: 100%; justify-content: space-between; }
      }
    `;
  }
}

if (!customElements.get("manual-energy-metering-panel")) {
  customElements.define(
    "manual-energy-metering-panel",
    ManualEnergyMeteringPanel
  );
}
