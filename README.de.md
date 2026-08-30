[English documentation](README.md)

*Bitte vergebe einen* :star: *falls du diese Integration nützlich findest!* :blush:

# Manuelle Energiemessung

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Downloads](https://img.shields.io/github/downloads/jan-brinkmann/ha-manual-energy-metering/total?label=downloads)](https://github.com/jan-brinkmann/ha-manual-energy-metering/releases)

[![Release](https://img.shields.io/github/v/release/jan-brinkmann/ha-manual-energy-metering?label=release)](https://github.com/jan-brinkmann/ha-manual-energy-metering/releases/latest)
![GitHub commits since latest release](https://img.shields.io/github/commits-since/jan-brinkmann/ha-manual-energy-metering/latest)
[![Commit activity](https://img.shields.io/github/commit-activity/m/jan-brinkmann/ha-manual-energy-metering)](https://github.com/jan-brinkmann/ha-manual-energy-metering/commits/main)
[![Validate](https://github.com/jan-brinkmann/ha-manual-energy-metering/actions/workflows/validate.yml/badge.svg)](https://github.com/jan-brinkmann/ha-manual-energy-metering/actions/workflows/validate.yml)

`Manuelle Energiemessung` ist eine benutzerdefinierte Integration für Home Assistant. Sie
richtet sich an Home-Assistant-Nutzer, die ihre Strom-, Gas- und/oder Wasserzähler
aus unterschiedlichen Gründen nicht mit einem Lesegerät ausstatten können, das die
Zählerstände automatisch für Home Assistant verfügbar macht. Die Integration
verwaltet beliebig viele manuell abgelesene Strom-, Gas- und Wasserzähler und
verteilt den Verbrauch zwischen zwei Ablesungen linear auf die betroffenen
Stunden. Die daraus interpolierten Messwerte können anschließend in das Energy
Dashboard von Home Assistant eingetragen werden.

Mit der Integration lassen sich außerdem Lücken in bereits vorhandenen
Aufzeichnungen schließen. Ebenso können historische Zählerstände nachgetragen
werden, die über Jahre oder Jahrzehnte handschriftlich oder in Tabellen
dokumentiert wurden. Aus den eingepflegten Ablesungen erzeugt die Integration
eine durchgängig interpolierte Langzeitstatistik für die jeweils erfassten Zeiträume.

In einer englischsprachigen Home-Assistant-Oberfläche wird die Integration als
**Manual Energy Metering** angezeigt.

## Unterstützte Zähler

| Zählertyp | Einheit | Anwendungsbeispiele
| --- | --- | --- |
| Strom | `Wh` oder `kWh` | Hauptstromzähler für Bezug und/oder Einspeisung, PV-Erzeugung |
| Gas | `kWh` | Gasheizung, Fernwärmestation |
| Wasser | `L` | Hauptwasserzähler, Gartenwasserzähler |

Jeder Zähler erhält eine eigene Sensorentität und eine eigene externe
Langzeitstatistik. Die Messwerte bleiben im `.storage`-Verzeichnis von Home
Assistant erhalten.

## Installation

### Bevorzugt: Installation über HACS

Voraussetzung ist eine bereits eingerichtete HACS-Installation.

1. Öffne **HACS** in Home Assistant.
2. Öffne oben rechts das Drei-Punkte-Menü und wähle
   **Benutzerdefinierte Repositories**.
3. Trage als Repository
   `https://github.com/jan-brinkmann/ha-manual-energy-metering` ein.
4. Wähle als Typ **Integration** und füge das Repository hinzu.
5. Öffne in HACS **Manual Energy Metering**, wähle **Herunterladen** und
   installiere die neueste veröffentlichte Version.
6. Starte Home Assistant vollständig neu.
7. Öffne **Einstellungen > Geräte & Dienste > Integration hinzufügen** und wähle
   **Manuelle Energiemessung**.
8. Lege für jeden physischen Zähler einen eigenen Integrationseintrag an.

### Alternative: Manuelle Installation über GitHub

1. Öffne auf GitHub die Seite **Releases** dieses Repositorys.
2. Lade unter dem neuesten Release das Archiv **Source code (zip)** herunter und
   entpacke es.
3. Kopiere aus dem entpackten Repository den vollständigen Ordner
   `custom_components/manual_energy_metering` nach
   `<Konfigurationsverzeichnis>/custom_components/manual_energy_metering`.
   Bei Home Assistant OS beginnt dieser Pfad normalerweise mit `/config`. Falls
   `custom_components` noch nicht existiert, lege den Ordner an.
4. Prüfe, dass die Datei anschließend unter
   `<Konfigurationsverzeichnis>/custom_components/manual_energy_metering/manifest.json`
   liegt. Eine zusätzliche Verzeichnisebene aus dem Namen des ZIP-Archivs ist an
   dieser Stelle falsch.
5. Starte Home Assistant vollständig neu.
6. Öffne **Einstellungen > Geräte & Dienste > Integration hinzufügen** und wähle
   **Manuelle Energiemessung**.
7. Lege für jeden physischen Zähler einen eigenen Integrationseintrag an.

Anschließend erscheint **Manuelle Energiemessung** im Reiter **Integrationen** als
eigene Kachel. Nach einem Klick auf die Kachel erscheint für jeden angelegten
Zähler ein separater Konfigurationseintrag.

## Aktualisierung

### Aktualisierung über HACS

1. Öffne **HACS** und dort **Manual Energy Metering**.
2. Lade die von HACS angebotene neue Release-Version herunter.
3. Starte Home Assistant vollständig neu, sobald HACS den ausstehenden Neustart
   anzeigt.

### Manuelle Aktualisierung

1. Lade das Archiv des gewünschten, vorzugsweise neuesten GitHub-Releases herunter
   und entpacke es.
2. Ersetze den vorhandenen Ordner
   `<Konfigurationsverzeichnis>/custom_components/manual_energy_metering` vollständig
   durch den gleichnamigen Ordner aus dem neuen Release. Kopiere nicht das gesamte
   Repository in `custom_components`.
3. Starte Home Assistant vollständig neu. Ein bloßes Neuladen der Integration
   reicht nach einer Code-Aktualisierung nicht aus.

Die vorhandenen Integrationseinträge müssen für ein Update nicht gelöscht oder
neu angelegt werden. Zählerstände und Konfigurationen liegen außerhalb des
Integrationsordners im Home-Assistant-Speicher und bleiben beim Ersetzen des
Integrationsordners erhalten. Erstelle unabhängig davon vor Home-Assistant-Updates
regelmäßig ein Backup deiner Installation.

## Zählerstände verwalten

Öffne **Einstellungen > Geräte & Dienste**, suche im Reiter **Integrationen**
die Kachel **Manuelle Energiemessung** und klicke beim gewünschten Zähler auf das
Zahnradsymbol. Dadurch öffnet sich die gemeinsame Verwaltungsseite für die
Zählerstände. Oberhalb der Eingabemaske beschreibt ein kurzer Text die
verfügbaren Funktionen.

Mit der Eingabemaske auf Seite 1 wird ein neuer absoluter Zählerstand
erfasst. Datum und Uhrzeit sind mit der aktuellen Zeit in der
Home-Assistant-Zeitzone vorbelegt, wobei die Sekunden auf `00` gesetzt werden;
das Feld für den Zählerstand bleibt leer. Verwende das lokalisierte
Dezimaltrennzeichen, aber keine Tausendertrennzeichen. Messwerte können vor,
zwischen oder nach vorhandenen Ablesungen eingefügt werden. Ein Wert mit einem
bereits vorhandenen Zeitstempel korrigiert diesen Wert. Die zeitlich sortierten
Zählerstände dürfen nicht sinken.

Die vollständige Historie ist in absteigend chronologische Seiten unterteilt.
Seite 1 enthält ausschließlich die zehn neuesten Werte sowie die Eingabemaske
für einen neuen Zählerstand. Jede folgende Archivseite enthält bis zu 100 ältere
Werte. Innerhalb jeder Seite steht der neueste Ablesezeitpunkt oben. Jede Zeile
verwendet lokalisierte Datums-,
Uhrzeit- und Zahlenformatierung und besitzt Schaltflächen zum Bearbeiten und
Löschen. Das Eingabefeld beim Bearbeiten enthält bewusst keine
Tausendertrennzeichen; auch der Zeitstempel kann geändert werden. Vor dem
Löschen ist eine Bestätigung erforderlich.

Nach jedem Hinzufügen, Korrigieren oder Löschen entfernt die Integration die zuvor
interpolierte Langzeitstatistik dieses Zählers vollständig und baut sie aus den
aktuell gespeicherten Messwerten neu auf. Dadurch wird beim Einfügen eines
Zwischenwerts das alte Intervall in zwei neue Intervalle aufgeteilt. Beim Löschen
eines Zwischenwerts werden die benachbarten Ablesungen wieder direkt miteinander
interpoliert.

Alternativ stehen unter **Entwicklerwerkzeuge > Aktionen** die Aktionen
`manual_energy_metering.add_reading` und
`manual_energy_metering.delete_reading` zur Verfügung. Sie eignen sich auch für
Automatisierungen. Beim Löschen muss der Zeitstempel exakt dem gespeicherten
Ablesezeitpunkt entsprechen.

## Zeitangaben und Entitätsverlauf

`recent_readings` und `last_reading_timestamp` sind Attribute der jeweiligen
Sensorentität und keine eigenen Menüpunkte. Du findest sie so:

1. Öffne **Entwicklerwerkzeuge > Zustände**.
2. Suche die Sensorentität des Zählers, zum Beispiel `sensor.wasserzaehler`.
3. Öffne beziehungsweise erweitere die Entität und lies ihre Zustandsattribute.

`recent_readings` enthält dort die letzten 50 Ablesungen mit Wert und gespeichertem
Ablesezeitpunkt. `last_reading_timestamp` enthält den Zeitpunkt der neuesten
Ablesung.

Alle Ablesungen speichert Home Assistant intern in einer Datei unter
`<Konfigurationsverzeichnis>/.storage/manual_energy_metering.<interne_zaehler_id>`.
Das Verzeichnis `.storage` ist versteckt und gehört zur internen Datenhaltung von
Home Assistant. Für die normale Nutzung muss und sollte diese Datei nicht manuell
geöffnet oder bearbeitet werden.

Die normale Home-Assistant-Zustandshistorie einer Sensorentität kann nicht
rückdatiert werden. Sie zeigt deshalb, wann ein Zählerstand in Home Assistant
eingegeben wurde. Das bedeutet nicht, dass der Ablesezeitpunkt verloren ging. Für
rückwirkende Diagramme und das Energy Dashboard wird die separate interpolierte
Langzeitstatistik `manual_energy_metering:*` verwendet.

## Energy Dashboard

Nach mindestens zwei Ablesungen erscheint für den Zähler eine Statistik mit dem
Namen des Zählers. Ihre ID hat die Form
`manual_energy_metering:<interne_zaehler_id>`. Die konkrete ID steht außerdem im
Attribut `statistic_id` der Sensorentität.

Wähle diese Statistik in **Einstellungen > Dashboards > Energie** passend als
Netzverbrauch, Gasverbrauch oder Wasserverbrauch aus. Verwende für die
rückwirkend interpolierten Daten die Statistik mit dem Präfix
`manual_energy_metering:` und nicht die automatisch vom aktuellen Sensorzustand
erzeugte Statistik `sensor.*`.

Zwischen zwei Ablesungen wird die Differenz proportional zur tatsächlich
verstrichenen Zeit auf UTC-Stundenintervalle verteilt. Angefangene Stunden
erhalten den entsprechenden Teilverbrauch. Vor der ersten und nach der letzten
Ablesung wird kein Verbrauch extrapoliert.

## Beispiele

Bei einem Wasserzähler mit `1 L` am 1. Januar um 00:00 Uhr und
`25 L` am 2. Januar um 00:00 Uhr entstehen 24 Stundenwerte zu jeweils `1 L`.

Bei einem Stromzähler mit `1000 kWh` am 1. Januar um 00:00 Uhr und `9760 kWh`
am 1. Januar des Folgejahres ergibt sich ein täglicher Verbrauch von
`24 kWh = (9760 kWh - 1000 kWh) / 365 Tage` beziehungsweise ein stündlicher
Verbrauch von `1 kWh`.

## Lizenz

Dieses Projekt wird unter der [MIT-Lizenz](LICENSE) veröffentlicht. Sie erlaubt
insbesondere die private und kommerzielle Nutzung, Änderung, Weiterentwicklung und
Weitergabe. Bei Kopien oder wesentlichen Teilen der Software müssen der
Copyright-Hinweis und der Lizenztext erhalten bleiben.

Teile dieses Projekts wurden mit Unterstützung generativer KI, darunter OpenAI
Codex, erstellt und anschließend menschlich geprüft und weiterbearbeitet. Daraus
entstehen keine zusätzlichen Einschränkungen gegenüber der MIT-Lizenz.
