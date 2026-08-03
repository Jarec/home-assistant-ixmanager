# iXmanager Integration

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/kubacizek)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/kubacizek/home-assistant-ixmanager.svg)](https://github.com/kubacizek/home-assistant-ixmanager/releases)

This integration provides support for the [R-EVC Wallbox EcoVolter](https://r-evc.com/index.php?route=product/product&path=60&product_id=135), utilizing the iXmanager [API](https://evcharger.ixcommand.com).

**Only EcoVolter (1st generation) is supported by this integration.** If you have 2nd generation, you can use [EcoVolter Home Assistant Integration](https://github.com/samuelg0rd0n/ha-ecovolter-integration).

## Features
- Seamless integration with the R-EVC Wallbox EcoVolter charger.
- Control and monitor your wallbox through Home Assistant.
- Easy setup and configuration with iXmanager API.

## Prerequisites
Before setting up this integration, ensure you have:
- Home Assistant **2026.7.0** or newer.
- Connected your wallbox with the iXmanager app on iOS or Android.
- Generated an API key from your [iXmanager account](https://www.ixfield.com/app/account).

## Provided entities

| Platform | Entity | Notes |
| --- | --- | --- |
| `switch` | Charging | Enables/disables charging |
| `switch` | Single phase mode | Switches between single- and three-phase charging |
| `number` | Maximum charging current | Capped by the configured cable type |
| `number` | Target charging current | Capped by the cable type and the current maximum |
| `number` | Boost current | Capped by the cable type and the current maximum |
| `number` | Boost duration | 0–86400 s; see [Boost](#boost) below |
| `sensor` | Charging power | |
| `sensor` | Charging current L1 / L2 / L3 | |
| `sensor` | Total energy | |
| `sensor` | Boost remaining | Time left of the running boost |
| `sensor` | Wi-Fi signal strength | Diagnostic |
| `sensor` | Charging status | Diagnostic, SAE J1772 states |
| `sensor` | Wi-Fi network | Diagnostic |
| `sensor` | Wi-Fi BSSID | Diagnostic, disabled by default |
| `binary_sensor` | Charging active | On while the wallbox is actually charging |
| `binary_sensor` | Boost | On while a boost is running |

## Boost

The API has no dedicated "start boost" command — boost is driven entirely by the boost
duration:

1. Set **Boost current** to the current you want during the boost.
2. Set **Boost duration** to the number of seconds the boost should last. Writing a value
   greater than zero starts it; **Boost** turns on and **Boost remaining** counts down.
3. To cancel a running boost, set **Boost duration** back to `0`.

## Upgrading to 3.0.0

3.0.0 contains breaking changes:

- **Home Assistant 2026.7.0 is now the minimum.** Earlier releases claimed to support 2024.2, but the code has required a newer core for some time.
- **Four duplicate sensors were removed** — `chargingEnable` and `singlePhase` (already covered by the switches) and `maximumCurrent` and `targetCurrent` (already covered by the number entities). They will show up as *"restored / no longer provided by the integration"* in `Settings > Devices & Services > Entities`; delete them there. Update any automation that referenced them to use the corresponding switch or number entity.
- **Entity names are now translated** and follow Home Assistant naming conventions. Existing `entity_id`s are preserved — only the displayed friendly name changes.
- Charging current sensors now store full precision and round to two decimals for display, instead of rounding the stored value.
- Total energy is now displayed in kWh on new installations. Existing entities keep whatever unit they were registered with; change it under the entity's settings if you want kWh.

## Installation

### HACS Installation (Recommended)
1. Ensure that [HACS](https://hacs.xyz) is installed in your Home Assistant instance.
2. Go to HACS → Integrations
3. Click the three dots menu (⋮) in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/kubacizek/home-assistant-ixmanager`
6. Select category: "Integration"
7. Click "Add"
8. Search for "iXmanager" in HACS and install it
9. Restart Home Assistant

### Manual Installation
1. Download the latest release from the [releases page](https://github.com/kubacizek/home-assistant-ixmanager/releases)
2. Extract the `custom_components/ixmanager` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant to load the integration

## Configuration

1. Open Home Assistant and navigate to `Configuration > Devices & Services`.
2. Click on `Add Integration` and search for "iXmanager".
3. Enter the serial number of your wallbox (found on the charger or in your [iXmanager account](https://www.ixfield.com/app/account)) and your API key.
4. Complete the setup wizard to finalize the integration.

## Usage
Once the integration is configured, you can start using your R-EVC Wallbox EcoVolter directly from Home Assistant. Monitor charging status, control charging sessions, and integrate with other Home Assistant automations.
