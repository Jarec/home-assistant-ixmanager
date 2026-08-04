# CLAUDE.md

HACS custom integration for the R-EVC EcoVolter wallbox (1st generation only) over the iXmanager cloud API. All code in `custom_components/ixmanager/`.

## Development

**No test suite, no build step** — do not invent `pytest` commands.

```bash
.venv/bin/ruff check custom_components      # --fix to autofix
.venv/bin/ruff format custom_components
.venv/bin/mypy custom_components/ixmanager
cp -r custom_components/ixmanager <ha-config>/custom_components/   # then restart HA
```

- mypy is not a pre-commit hook on purpose — it needs all of Home Assistant installed. CI and manual only.
- `hassfest` and the HACS validator are GitHub Actions, not local commands. Only CI can tell you whether the manifest, translations and layout are valid against the current HA release.
- Debug logging: `custom_components.ixmanager: debug` under `logger.logs` in `configuration.yaml`.
- Release: `gh workflow run release.yml -f version=X.Y.Z`, nothing else. The workflow validates, bumps `manifest.json`, commits, tags `vX.Y.Z` and publishes. **Never bump the version or create the tag by hand** — one input owning both is what stopped them drifting (`2.1.1` vs. `v2.1.2`). It also builds `ixmanager.zip`, which HACS downloads (`zip_release` in `hacs.json`), so the integration's files must stay at the *root* of that archive.
- Releases in this repository are **immutable** — assets can only be attached as the release is created, and neither the release nor its tag can be edited or deleted afterwards. A botched release can only be superseded by the next version.

## Architecture

One endpoint, `{BASE_URL}/thing/{controller_id}/properties`: `GET` with `keys`, `PATCH` with `{key: value}`. The coordinator polls `PROPERTIES_TO_FETCH` every 15s, entities read `coordinator.data`, writes go straight to the API client. **An entity is defined by which property key it reads.**

- The API returns properties bare or wrapped as `{"value": X}`; `_unwrap()` flattens that once — never unwrap in entity code.
- Entities are descriptions, not subclasses: one entity class per platform plus a tuple (`SENSORS`, `BINARY_SENSORS`, `SWITCHES`, `NUMBERS`).
- `util.py` must not import from the package — `coordinator.py` uses it and `entity.py` imports `coordinator.py`.

> **`key` vs. `property_key`.** `description.key` is the unique-ID suffix (`f"{serial}_{key}"`) and must never change, or every user's entity is orphaned. `property_key` is the API key. Sensors use the camelCase API key for both; switches and numbers use snake_case (`charging_enable` → `chargingEnable`) for historical reasons.

State rules, in rough order of how easily they get broken:

- **`unavailable` ≠ `unknown`.** `available` is inherited from `CoordinatorEntity` and means only "wallbox reachable on the last update". A property the API didn't report yields `None` from `_property_value` → `unknown`. Folding a missing value back into `available` tears holes in recorder history and fires availability automations.
- **The coordinator owns optimistic state.** `async_set_pending()` holds a written value with a `PENDING_WRITE_TIMEOUT` deadline and publishes it via `async_set_updated_data()`, notifying *every* listener (`maximumCurrent` bounds `target_current`, so one write moves two entities). Refreshes re-apply it until `values_match()` agrees, or the deadline passes and the rejection is logged. **Never add `_attr_assumed_state`; never mutate `coordinator.data` from an entity.**
- `_async_write_property` is the only write path: `async_set_pending()` → `PATCH` → `async_request_refresh()`. On `IXManagerError` it clears the pending value, refreshes, and raises a translated `HomeAssistantError` so the failure reaches the UI.
- The refresh debouncer is configured (`cooldown=WRITE_VERIFY_DELAY, immediate=False`), not bypassed: `async_request_refresh()` on the write path, `async_refresh()` on the error path. `PARALLEL_UPDATES = 1` on writable platforms so calls queue instead of dropping, `0` on read-only ones.
- **Auth failures must reach reauth**: 401/403 → `IXManagerAuthenticationError` → `ConfigEntryAuthFailed`, in both `async_setup_entry` and `_async_update_data`. Never collapse it into `UpdateFailed` or `return False`.
- `_warn_once()` for unexpected device values — the poll never stops, so a plain warning repeats every 15s. Module-level `value_fn`s stay silent and let the entity report.
- Coordinator lives in `entry.runtime_data`; `cable_type` is written to `entry.data`, not `entry.options`, and the update listener in `async_setup_entry` is what applies it without a restart.
- `cable_type` caps every number via `native_max_value`; `target_current` narrows further against live `maximumCurrent`; `boost_current` deliberately doesn't, since boost exists to override the normal limit. Don't clamp in `async_set_native_value` — the platform already raises `ServiceValidationError`.

## Adding an entity

1. `PROPERTY_*` constant in `const.py` **and append it to `PROPERTIES_TO_FETCH`** — otherwise the entity never gets a value.
2. Append a description to the platform's tuple. Sensors convert through `value_fn`.
3. Add `translation_key` to `strings.json`, `translations/en.json` **and** `translations/cs.json`; `icons.json` for a non-default icon.

New platforms also go in `PLATFORMS` (`const.py`), but **not** in `hacs.json` — `domains` and `iot_class` were dropped from the HACS schema and the validator rejects them.

## Conventions

- `from __future__ import annotations` is **banned** (`TID251`); HA requires Python 3.14+.
- Google docstrings with `Args:` / `Returns:` / `Raises:` on **every** function, including trivial getters.
- mypy uses HA core's strict settings incl. `explicit-override` — every override carries `@override`.
- Values written to the device are `WritableValue` (`util.py`), not `Any`. Values coming out of the API stay `Any` — untyped cloud JSON.
- No transport exception escapes `api_client.py`: `aiohttp.ClientError` and `TimeoutError` become `IXManagerConnectionError`.
- `strings.json` is the source of truth; `translations/en.json` is byte-identical and `cs.json` carries the same keys. Literal strings only — `[%key:…%]` is not expanded for custom integrations and renders raw.
- `_attr_has_entity_name = True` + `translation_key`; never `_attr_name`, it can't be translated.
