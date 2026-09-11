[Deutsche Dokumentation](README.de.md)

*Please leave a* :star: *if you find this integration useful!* :blush:

# Manual Energy Metering

<p align="center">
  <img
    src="custom_components/manual_energy_metering/brand/icon.png"
    alt="Manual Energy Metering logo"
    width="180"
  >
</p>

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Downloads](https://img.shields.io/github/downloads/jan-brinkmann/ha-manual-energy-metering/total?label=downloads)](https://github.com/jan-brinkmann/ha-manual-energy-metering/releases)

[![Release](https://img.shields.io/github/v/release/jan-brinkmann/ha-manual-energy-metering?label=release)](https://github.com/jan-brinkmann/ha-manual-energy-metering/releases/latest)
![GitHub commits since latest release](https://img.shields.io/github/commits-since/jan-brinkmann/ha-manual-energy-metering/latest)
[![Commit activity](https://img.shields.io/github/commit-activity/m/jan-brinkmann/ha-manual-energy-metering)](https://github.com/jan-brinkmann/ha-manual-energy-metering/commits/main)
[![Validate](https://github.com/jan-brinkmann/ha-manual-energy-metering/actions/workflows/validate.yml/badge.svg)](https://github.com/jan-brinkmann/ha-manual-energy-metering/actions/workflows/validate.yml)

`Manual Energy Metering` is a custom integration for Home Assistant. It is
intended for Home Assistant users who, for various reasons, cannot equip their
meters with a reading device that automatically makes meter readings available
to Home Assistant.

In a German-language Home Assistant interface, the integration is displayed as
**Manuelle Energiemessung**.

## Core features

- Create multiple independent manual meters, each with its own sensor entity and
  long-term statistic.
- Add, edit, and delete dated readings, including readings between existing
  historical values.
- Linearly interpolate consumption into hourly values for the Home Assistant
  Energy Dashboard.
- Close gaps or enter records maintained by hand or in spreadsheets over years
  or decades.
- Enter readings from a compact dashboard card, optionally with external
  Vision-LLM photo recognition.
- Export and import meters as CSV files, including compatible histories from
  other Home Assistant integrations.

## Supported meters

| Meter type | Unit | Example uses
| --- | --- | --- |
| Electricity | `Wh` or `kWh` | Main electricity meter for consumption and/or feed-in, PV generation |
| Gas | `kWh` | Gas heating, district heating station |
| Water | `L` | Main water meter, garden water meter |

The readings are retained in the `.storage` directory used by Home Assistant.

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

## Managing meter readings

Open **Settings > Devices & services**, select **Manual Energy Metering** on
the **Integrations** tab, and click the gear icon for the desired meter.

The management page lets you add, edit, delete, and browse the complete reading
history. Readings can also be added between two existing readings. The
interpolations are then adjusted accordingly.

Use **Export CSV** on this page to download all recorded meter readings. For an
electricity meter, choose whether the CSV uses `Wh` or `kWh`. When adding
another meter, choose **Import an exported CSV file**. The original meter name
is suggested during import, but you can replace it with any new name and choose
`Wh` or `kWh` for an imported electricity meter.

You can also transfer the hourly history of a compatible physical meter from
one Home Assistant instance to another:

1. On the source instance, open **Settings > Devices & services > Add
   integration > Manual Energy Metering**.
2. Choose **Export an Energy Dashboard meter**, select its meter and type,
   choose `Wh` or `kWh` for electricity, and download the CSV file.
3. On the target instance, add **Manual Energy Metering** again and choose
   **Import an exported CSV file**.

Electricity histories can be exported and imported in `Wh` or `kWh`. Other
energy histories use `kWh`, and volume histories use `L`. Existing gaps in the
hourly history remain gaps after import. Negative hourly consumption caused by
inaccurate source data is exported as `0`; its original value is retained in
the CSV column `original_change` and listed on the export page.

The actions `manual_energy_metering.add_reading` and
`manual_energy_metering.delete_reading` are also available under
**Developer tools > Actions** and can be used in automations. Deleting a
reading requires its exact stored timestamp.

## Energy Dashboard

After at least two readings, a statistic bearing the meter name appears. Its ID
has the form `manual_energy_metering:<internal_meter_id>`. The exact ID is shown
on the meter's management page and is also available in the sensor entity
`statistic_id` attribute.

Select this statistic under **Settings > Dashboards > Energy** as appropriate
for grid consumption, gas consumption, or water consumption. For the
retrospectively interpolated data, use the statistic with the
`manual_energy_metering:` prefix instead of the `sensor.*` statistic that is
automatically generated from the current sensor state.

Between two readings, the difference is distributed proportionally to the
actual elapsed time across hourly intervals. Partial hours receive the
corresponding proportion of consumption. No consumption is extrapolated before
the first or after the last reading.

## Dashboard card

The **Manual Energy Metering** dashboard card lets you enter a reading directly
from a dashboard. Add it through **Edit dashboard > Add card > Manual Energy
Metering** and select the meter entity.

The card editor can show or hide the photo buttons independently of the other
card content and independently of whether a provider is configured.

### Photo recognition

Photo recognition is configured separately for each meter. Configure it while
creating the meter or later under **Settings > Devices & services > Manual
Energy Metering > Reconfigure**.

Enter the address of an OpenAI-compatible vision provider, such as
`http://192.168.1.10:11434` for Ollama, and an API token if the provider requires
one. Model and prompt are prefilled and can be adjusted for each meter. Image
compression can also be enabled or disabled per meter.

Use **Take photo** or **Upload photo** in the dashboard card. The integration
sends the image to the configured provider but does not store it permanently.
The provider may apply its own storage and privacy policy. A compact progress
bar shows the current recognition stage and marks the last reached stage if an
error occurs.

The recognized reading and reading time are shown for confirmation. For an
uploaded file, the capture date and time from its image metadata are used when
available; otherwise the current time is used. Correct the values if necessary
and select **Add reading** to save the record. Without a configured provider,
all manual functions remain available.

After installing or updating the integration, fully restart Home Assistant and
reload the browser if the card is not shown in the card picker.

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
