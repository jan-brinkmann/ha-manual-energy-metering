[Deutsche Dokumentation](README.de.md)

*Please leave a* :star: *if you find this integration useful!* :blush:

# Manual Energy Metering

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Downloads](https://img.shields.io/github/downloads/jan-brinkmann/ha-manual-energy-metering/total?label=downloads)](https://github.com/jan-brinkmann/ha-manual-energy-metering/releases)

[![Release](https://img.shields.io/github/v/release/jan-brinkmann/ha-manual-energy-metering?label=release)](https://github.com/jan-brinkmann/ha-manual-energy-metering/releases/latest)
![GitHub commits since latest release](https://img.shields.io/github/commits-since/jan-brinkmann/ha-manual-energy-metering/latest)
[![Commit activity](https://img.shields.io/github/commit-activity/m/jan-brinkmann/ha-manual-energy-metering)](https://github.com/jan-brinkmann/ha-manual-energy-metering/commits/main)
[![Validate](https://github.com/jan-brinkmann/ha-manual-energy-metering/actions/workflows/validate.yml/badge.svg)](https://github.com/jan-brinkmann/ha-manual-energy-metering/actions/workflows/validate.yml)

`Manual Energy Metering` is a custom integration for Home Assistant. It is
intended for Home Assistant users who, for various reasons, cannot equip their
electricity, gas, and/or water meters with a reading device that automatically
makes meter readings available to Home Assistant. The integration manages any
number of manually read electricity, gas, and water meters and distributes the
consumption between two readings linearly across the affected hours. The
resulting interpolated readings can be added to Home Assistant's Energy
Dashboard.

The integration can also close gaps in existing records. Historical meter
readings that have been documented by hand or in spreadsheets for years or even
decades can be entered as well. From these readings, the integration creates a
continuously interpolated long-term statistic for each recorded period.

In a German-language Home Assistant interface, the integration is displayed as
**Manuelle Energiemessung**.

## Supported meters

| Meter type | Unit | Example uses
| --- | --- | --- |
| Electricity | `Wh` or `kWh` | Main electricity meter for consumption and/or feed-in, PV generation |
| Gas | `kWh` | Gas heating, district heating station |
| Water | `L` | Main water meter, garden water meter |

Each meter receives its own sensor entity and external long-term statistic. The
readings are retained in the `.storage` directory used by Home Assistant.

## Installation

### Preferred: Installation through HACS

An existing HACS installation is required.

1. Open **HACS** in Home Assistant.
2. Open the three-dot menu in the upper-right corner and select
   **Custom repositories**.
3. Enter
   `https://github.com/jan-brinkmann/ha-manual-energy-metering` as the
   repository.
4. Select **Integration** as the type and add the repository.
5. Open **Manual Energy Metering** in HACS, select **Download**, and install the
   latest published version.
6. Fully restart Home Assistant.
7. Open **Settings > Devices & services > Add integration** and select
   **Manual Energy Metering**.
8. Create a separate integration entry for each physical meter.

### Alternative: Manual installation from GitHub

1. Open the **Releases** page of this repository on GitHub.
2. Download **Source code (zip)** from the latest release and extract it.
3. Copy the complete `custom_components/manual_energy_metering` directory from
   the extracted repository to
   `<configuration_directory>/custom_components/manual_energy_metering`.
   On Home Assistant OS, this path usually starts with `/config`. Create the
   `custom_components` directory if it does not exist yet.
4. Verify that the file is located at
   `<configuration_directory>/custom_components/manual_energy_metering/manifest.json`.
   An additional directory level named after the ZIP archive is incorrect here.
5. Fully restart Home Assistant.
6. Open **Settings > Devices & services > Add integration** and select
   **Manual Energy Metering**.
7. Create a separate integration entry for each physical meter.

**Manual Energy Metering** then appears as its own card on the
**Integrations** tab. Clicking the card shows a separate configuration entry for
each meter that has been created.

## Updating

### Updating through HACS

1. Open **HACS**, then open **Manual Energy Metering**.
2. Download the new release offered by HACS.
3. Fully restart Home Assistant when HACS indicates that a restart is pending.

### Manual update

1. Download and extract the archive for the desired, preferably latest, GitHub
   release.
2. Completely replace the existing
   `<configuration_directory>/custom_components/manual_energy_metering`
   directory with the directory of the same name from the new release. Do not
   copy the entire repository into `custom_components`.
3. Fully restart Home Assistant. Reloading the integration is not sufficient
   after updating its code.

Existing integration entries do not need to be deleted or recreated for an
update. Meter readings and configuration are stored by Home Assistant outside
the integration directory and remain intact when that directory is replaced.
Regardless, regularly back up your installation before Home Assistant updates.

## Dashboard card

The integration provides the **Manual Energy Metering** dashboard card for
entering new readings without navigating through **Settings > Devices &
services**. Add one card for each meter:

1. Open the desired dashboard and select **Edit dashboard**.
2. Select **Add card** and choose **Manual Energy Metering**.
3. Select the sensor entity belonging to the desired meter.
4. Choose separately whether the meter name, last meter reading, date of the
   last reading, and a link to the complete history are displayed.

The card pre-fills the reading date with the current date and time in the Home
Assistant time zone and sets the seconds to `00`. The meter-reading input stays
empty. Use the localized decimal separator, but do not enter thousands
separators. Displayed readings and dates use the Home Assistant locale. The
card follows Home Assistant's entity permissions; the signed-in user needs
control permission for the selected meter entity to submit a reading.

For administrators, the optional history link opens exactly the meter-specific
management page that is also reached through **Settings > Devices & services >
Manual Energy Metering > gear icon**. The link is hidden for non-administrators
because that management page requires administrator privileges.

The same card can be configured manually in a dashboard's YAML editor:

```yaml
type: custom:manual-energy-metering-card
entity: sensor.water_meter
show_name: true
show_last_reading: true
show_last_reading_timestamp: true
show_history_link: true
```

The integration automatically creates or updates a versioned Lovelace module
resource for the card, so no separate dashboard resource needs to be added in
the normal storage mode. In the legacy YAML resource mode, the integration uses
Home Assistant's global frontend-module loader instead because YAML resources
are read-only. After installing or updating the integration, fully restart Home
Assistant and reload the browser page if the card is not yet shown in the card
picker. The management page described below remains available for browsing,
editing, and deleting stored readings.

## Managing meter readings

Open **Settings > Devices & services**, find the **Manual Energy Metering** card
on the **Integrations** tab, and click the gear icon for the desired meter. This
opens the shared meter-reading management page. A description above the input
form explains its available functions.

The form on page 1 adds a new absolute meter reading. Date and time are
pre-filled with the current time in the Home Assistant time zone, with seconds
set to `00`; the meter-reading field remains empty. Use the localized decimal
separator, but do not enter thousands separators. Readings can be inserted
before, between, or after existing readings. Adding a value with an existing
timestamp corrects that reading. Chronologically sorted readings must not
decrease.

The complete history is divided into reverse-chronological pages. Page 1
contains only the ten latest readings together with the form for a new reading.
Each following archive page contains up to 100 older readings. Within each
page, the newest timestamp is shown first. Every row uses
localized date, time, and number formatting and provides buttons to edit or
delete that specific reading. The edit field deliberately omits thousands
separators and also allows the timestamp to be changed; deletion requires
confirmation.

After every addition, correction, or deletion, the integration compares the old
and new neighboring interpolation segments. It updates only hourly statistic
rows whose interpolated consumption or cumulative value actually changes and
deletes only hours that are no longer covered. All other statistic rows remain
unchanged. Inserting an intermediate reading therefore splits the previous
interval into two new intervals. Deleting an intermediate reading causes the
adjacent readings to be interpolated directly again.

Alternatively, the actions `manual_energy_metering.add_reading` and
`manual_energy_metering.delete_reading` are available under
**Developer tools > Actions**. They can also be used in automations. When
deleting a reading, the timestamp must exactly match the stored reading time.

## Timestamps and entity history

`recent_readings` and `last_reading_timestamp` are attributes of the
respective sensor entity, not separate menu items. You can find them as follows:

1. Open **Developer tools > States**.
2. Find the meter sensor entity, for example `sensor.water_meter`.
3. Open or expand the entity and inspect its state attributes.

`recent_readings` contains the 50 most recent readings, including their values
and stored reading times. `last_reading_timestamp` contains the time of the
latest reading.

Home Assistant stores all readings internally in a file at
`<configuration_directory>/.storage/manual_energy_metering.<internal_meter_id>`.
The `.storage` directory is hidden and belongs to the internal data storage of
Home Assistant. During normal use, this file does not need to and should not be
opened or edited manually.

The normal Home Assistant state history of a sensor entity cannot be backdated.
It therefore shows when a reading was entered into Home Assistant. This does not
mean that the actual reading time has been lost. Retrospective charts and the
Energy Dashboard use the separate interpolated long-term statistic
`manual_energy_metering:*`.

## Energy Dashboard

After at least two readings, a statistic bearing the meter name appears. Its ID
has the form `manual_energy_metering:<internal_meter_id>`. The exact ID is also
available in the sensor entity `statistic_id` attribute.

Select this statistic under **Settings > Dashboards > Energy** as appropriate
for grid consumption, gas consumption, or water consumption. For the
retrospectively interpolated data, use the statistic with the
`manual_energy_metering:` prefix instead of the `sensor.*` statistic that is
automatically generated from the current sensor state.

Between two readings, the difference is distributed proportionally to the
actual elapsed time across UTC hourly intervals. Partial hours receive the
corresponding proportion of consumption. No consumption is extrapolated before
the first or after the last reading.

## Examples

A water meter with a reading of `1 L` on January 1 at 00:00 and a reading of
`25 L` on January 2 at 00:00 produces 24 hourly values of `1 L` each.

For an electricity meter with a reading of `1000 kWh` on January 1 at 00:00
and a reading of `9760 kWh` on January 1 of the following year, the daily
consumption is
`24 kWh = (9760 kWh - 1000 kWh) / 365 days`, or `1 kWh` per hour.

## License

This project is released under the [MIT License](LICENSE). In particular, the
license permits private and commercial use, modification, further development,
and redistribution. The copyright notice and license text must be retained in
copies or substantial portions of the software.

Parts of this project were created with the assistance of generative AI,
including OpenAI Codex, and subsequently reviewed and revised by a human. This
does not impose any additional restrictions beyond the MIT License.
