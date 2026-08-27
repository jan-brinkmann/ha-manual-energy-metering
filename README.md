*Bitte vergebe einen :star: falls du diese Integration nützlich findest! :blush:*

# Manual Energy Metering

`Manual Energy Metering` ist eine lokale Custom Integration für Home Assistant. Sie
richtet sich an Home-Assistant-Nutzer, die ihre Strom-, Gas- und/oder Wasserzähler
aus unterschiedlichen Gründen nicht mit einem Lesegerät ausstatten können, das die
Zählerstände automatisch für Home Assistant verfügbar macht. Die Integration
verwaltet beliebig viele manuell abgelesene Strom-, Gas- und Wasserzähler und
verteilt den Verbrauch zwischen zwei Ablesungen linear auf die betroffenen
Stunden.

In einer deutschsprachigen Home-Assistant-Oberfläche wird die Integration als
**Manuelle Energiemessung** angezeigt.

## Unterstützte Zähler

| Zählertyp | Einheit | Anwendungsbeispiel
| --- | --- | --- |
| Strom | `Wh` oder `kWh` | Hauptstromzähler für Bezug und/oder Einspeisung, PV-Erzeugung |
| Gas | `kWh` | Gasheizung, Fernwärmestation |
| Wasser | `L` | Hauptwasserzähler, Gartenwasserzähler |

Jeder Zähler erhält eine eigene Sensorentität und eine eigene externe
Langzeitstatistik. Die Messwerte bleiben im `.storage`-Verzeichnis von Home
Assistant erhalten.

## Installation

### Manuelle Installation über GitHub

1. Öffne auf GitHub die Seite **Releases** dieses Repositorys.
2. Lade unter dem neuesten Release das Archiv **Source code (zip)** herunter und
   entpacke es. Falls noch kein Release vorhanden ist, kannst du ersatzweise über
   **Code > Download ZIP** den aktuellen Entwicklungsstand herunterladen.
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
eigene Kachel. Nach einem Klick auf die Kachel, erscheint für jeden angelegten Zähler
ein separater Konfigurationseintrag. 

## Aktualisierung

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

## Zählerstände erfassen

Öffne **Einstellungen > Geräte & Dienste**, suche im Reiter **Integrationen**
die Kachel **Manuelle Energiemessung**. Klicke beim gewünschten Zähler auf das
Zahnradsymbol. Gib den absoluten Zählerstand und den Zeitpunkt der
Ablesung ein.

Alternativ steht unter **Entwicklerwerkzeuge > Aktionen** die Aktion
`manual_energy_metering.add_reading` zur Verfügung. Sie eignet sich auch für
Automatisierungen. Ein Wert mit einem bereits vorhandenen Zeitstempel korrigiert
diesen Wert. Die zeitlich sortierten Zählerstände dürfen nicht sinken.

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

Nach mindestens einer Ablesung erscheint für den Zähler eine Statistik mit dem
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

Bei einem Wasserzähler mit `1 L` am 1. Januar um 00:00 Uhr und `25 L` am
2. Januar um 00:00 Uhr entstehen 24 Stundenwerte zu jeweils `1 L`.

Bei einem Stromzähler mit `1000 kWh` am 1. Januar um 00:00 Uhr und `9760 kWh` am
1. Januar des Folgejahres, ergibt sich am täglicher Verbrauch von `24 kWh = (9760 kWh - 1000 kWh) / 365 Tage`
bzw. ein ständlicher Verbrauch von `1 kWh`.

## Lizenz

Dieses Projekt wird unter der [MIT-Lizenz](LICENSE) veröffentlicht. Sie erlaubt
insbesondere die private und kommerzielle Nutzung, Änderung, Weiterentwicklung und
Weitergabe. Bei Kopien oder wesentlichen Teilen der Software müssen der
Copyright-Hinweis und der Lizenztext erhalten bleiben.

Teile dieses Projekts wurden mit Unterstützung generativer KI, darunter OpenAI
Codex, erstellt und anschließend menschlich geprüft und weiterbearbeitet. Daraus
entstehen keine zusätzlichen Einschränkungen gegenüber der MIT-Lizenz.
