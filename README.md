[Deutsche Dokumentation](README.de.md)

*Please leave a* :star: *if you find this integration useful!* :blush:

# Manual Energy Metering

<p align="center">
  <img
    src="custom_components/manual_energy_metering/frontend/icons/banner.png"
    alt="Manual Energy Metering banner"
    width="100%"
    style="display: block; width: 100%; background-color: #ffffff;"
  >
</p>

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
- Enter readings in the physical meter's unit and display consumption in
  another unit in the Energy Dashboard, such as reading in `m³` and
  displaying consumption in `kWh`.
- Close gaps or enter records maintained by hand or in spreadsheets over years
  or decades.
- Enter readings from a compact dashboard card, optionally with external
  Vision-LLM photo recognition.
- Export and import meters as CSV files, including compatible histories from
  other Home Assistant integrations.

## Supported meters

| Meter type | Units | Example uses
| --- | --- | --- |
| Electricity | `cal`, `Gcal`, `GJ`, `GWh`, `J`, `kcal`, `kJ`, `kWh`, `Mcal`, `MJ`, `mWh`, `MWh`, `thm`, `TWh`, `Wh` | Main electricity meter for consumption and/or feed-in, PV generation |
| Gas | `CCF`, `ft³`, `L`, `MCF`, `m³`, plus all the electricity units above | Gas heating, district heating station |
| Water | `CCF`, `ft³`, `gal`, `L`, `MCF`, `m³` | Main water meter, garden water meter |

`gal` denotes US gallons and `thm` denotes US therms.

The readings are retained in the `.storage` directory used by Home Assistant.

<!-- ha-marketplace:exclude-start -->

## Installation

### Marketplace

The Marketplace is directly built into Home Assistant. You can
install **Manual Energy Metering** from the default catalog without a GitHub
account.

[![Open Manual Energy Metering in the Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=jan-brinkmann&repository=ha-manual-energy-metering&category=integration)

1. As an administrator, open **Settings > Marketplace** and read and accept the
   community-content notice when prompted.
2. Search for **Manual Energy Metering**, open the result, and select
   **Install**. Confirm the version in the installation dialog.
3. If Home Assistant requests a restart under **Settings > System > Repairs**,
   restart before setting up your meters.

[Marketplace documentation](https://www.home-assistant.io/integrations/marketplace/)

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

<!-- ha-marketplace:exclude-end -->

## Setting up meters

After installation, complete the integration setup if it opens automatically.
To open it yourself, go to **Settings > Devices & services > Add integration**
and select **Manual Energy Metering**. Create a separate integration entry for
each physical meter.

**Manual Energy Metering** then appears as its own card on the
**Integrations** tab. Clicking the card shows a separate configuration entry for
each meter that has been created.

## Updating

### Updating through the Marketplace (Home Assistant 2026.11 or later)

1. Open **Settings > Marketplace** and accept the community-content notice if
   prompted.
2. Open **Settings > Updates**, select **Manual Energy Metering**, and install
   the offered release.
3. Fully restart Home Assistant to apply the update. The restart reminder
   appears under **Settings > System > Repairs**.

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

When creating a meter, select the unit the physical meter uses. This is the
primary entity's unit and the unit for entering readings. Under **Secondary
entities**, select or deselect other units of the meter type. Each selected
unit has its own sensor and a column of converted readings.

Use **Export CSV** on this page to download all recorded meter readings. When
adding another meter, choose **Import an exported CSV file**. You can replace
the suggested meter name during import.

You can also transfer the hourly history of a compatible physical meter from
one Home Assistant instance to another:

1. On the source instance, open **Settings > Devices & services > Add
   integration > Manual Energy Metering**.
2. Choose **Export an Energy Dashboard meter**, select its meter and type,
   choose an available CSV unit, and download the file.
3. On the target instance, add **Manual Energy Metering** again and choose
   **Import an exported CSV file**.

CSV import and export support every unit listed for the meter type. The
primary unit is set when the meter is created. Importing the CSV in another
unit creates a separate, independent meter with that primary unit. Physical gas
histories default to `kWh` for energy and `m³` for volume on export. Water
histories default to `L`. Existing gaps in the hourly history remain gaps after
import.
Negative hourly consumption caused by inaccurate source data is exported as
`0`. Its original value is retained in the CSV column `original_change` and
listed on the export page.

The actions `manual_energy_metering.add_reading` and
`manual_energy_metering.delete_reading` are also available under
**Developer tools > Actions** and can be used in automations. Deleting a
reading requires its exact stored timestamp.

### Convert gas volume and energy

To calculate energy from a gas meter, multiply the difference between two
readings by the calorific value and the volume correction factor.

**Energy (kWh) = gas consumption (m³) × calorific value (kWh/m³) × volume correction factor**

The calorific value depends on the gas composition and can change over time.
The volume correction factor adjusts the measured volume to standard conditions
using pressure and temperature.
Use the factors from your gas bill for the relevant period.

Enter both values when setting up a gas meter or later under **Reconfigure**.
The editable defaults of `11.0 kWh/m³` and `0.95` give an estimate of
`10.45 kWh` per measured cubic meter. For example, `100 m³` gives `1,045 kWh`
with those values.

When you choose a CSV unit that converts between volume and energy, a manual
meter export uses that meter's settings. You can enter the factors during a
CSV import or an external statistics export. One pair of factors applies to
the whole CSV. The integration stores readings in the meter's chosen unit.

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

Each secondary entity has a copyable statistic ID. Conversion between gas
volume and energy uses the meter's calorific value and volume correction factor.
Changes to either factor recalculate the affected history. Clearing a unit's
checkbox removes its sensor and derived hourly statistic. Enabling it again
rebuilds the statistic from the stored readings.

Between two readings, the difference is distributed proportionally to the
actual elapsed time across hourly intervals. Partial hours receive the
corresponding proportion of consumption. No consumption is extrapolated before
the first or after the last reading.

### Example with gas readings in m³ and consumption in kWh

1. Create the gas meter with `m³` as its primary unit and enter the values
   shown on the physical meter, such as `1200 m³` and `1205 m³` on
   successive readings.
2. On the meter's management page, enable `kWh` under **Secondary entities**.
   The table shows converted values alongside the entered readings. Copy the
   statistic ID for `kWh`.
3. Select that statistic for gas consumption under **Settings > Dashboards >
   Energy**. With the default calorific value and volume correction factor
   described above, the difference of `5 m³` represents `52.25 kWh` of
   consumption. Continue entering readings in `m³`.

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

For **Upload photo**, choose **Date only** or **Date and meter reading** in the
dashboard card. The browser remembers your choice for each meter across page
reloads. **Date only** reads the capture date and time from the photo metadata
in your browser. If the metadata is missing, the form keeps its current date and
time. Enter the meter reading manually. Without a configured provider, the
switch is disabled and uploads use **Date only**.

**Date and meter reading** and **Take photo** send the image to the configured
provider for recognition. The integration does not store it permanently. The
provider may apply its own storage and privacy policy. The progress bar shows
the current recognition stage and marks the last reached stage if an error
occurs. For an uploaded photo, the capture time is used when available.
Otherwise, the form uses the current time.

Review the reading and date, then select **Add reading** to save the record.

The integration includes the card and registers it automatically. Reload the
browser if the card is missing from the card picker after setup. After an
integration update, fully restart Home Assistant first.

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
