const ROWS = [
  { key: "repository", domain: "update", suffix: "_update" },
  { key: "check", domain: "button", suffix: "_check_for_updates" },
  { key: "version", domain: "select", suffix: "_rollback_version" },
  { key: "install_version", domain: "button", suffix: "_install_version_and_pause" },
  { key: "reinstall", domain: "button", suffix: "_reinstall" },
  { key: "pause", domain: "switch", suffix: "_updates_paused" },
  { key: "status", domain: "sensor", suffix: "_status" },
];

const ROW_TAG = {
  update: "hui-update-entity-row",
  button: "hui-button-entity-row",
  select: "hui-select-entity-row",
  switch: "hui-toggle-entity-row",
  sensor: "hui-sensor-entity-row",
};

const ROW_KEYS = new Set(ROWS.map((row) => row.key));

function integrationEntities(hass) {
  return Object.values((hass && hass.entities) || {}).filter((entry) => {
    if (entry.platform === "github_custom_component") {
      return true;
    }
    return !entry.platform && ROW_KEYS.has(entry.translation_key);
  });
}

function devicesFor(hass) {
  const devices = (hass && hass.devices) || {};
  const ids = [];
  integrationEntities(hass).forEach((entry) => {
    if (entry.device_id && !ids.includes(entry.device_id)) {
      ids.push(entry.device_id);
    }
  });
  return ids.map((id) => ({
    id,
    name: (devices[id] && devices[id].name) || id,
  }));
}

function entityFor(hass, deviceId, row) {
  const match = integrationEntities(hass).find((entry) => {
    if (entry.device_id !== deviceId) {
      return false;
    }
    if (entry.translation_key === row.key) {
      return true;
    }
    return typeof entry.entity_id === "string" && entry.entity_id.endsWith(row.suffix);
  });
  if (!match || !hass.states[match.entity_id]) {
    return null;
  }
  return match.entity_id;
}

function createRow(entityId) {
  const domain = entityId.split(".", 1)[0];
  const preferred = ROW_TAG[domain];
  const tag = preferred && customElements.get(preferred) ? preferred : "hui-generic-entity-row";
  const row = document.createElement(tag);
  row.setConfig({ entity: entityId });
  return row;
}

class GitHubCustomComponentCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("github-custom-component-card-editor");
  }

  static getStubConfig(hass) {
    const devices = devicesFor(hass);
    return { device: devices.length ? devices[0].id : "" };
  }

  setConfig(config) {
    if (!config || typeof config !== "object") {
      throw new Error("Invalid card configuration");
    }
    this._config = config;
    this._signature = "";
  }

  set hass(hass) {
    this._hass = hass;
    const device = (this._config && this._config.device) || "";
    const ids = device ? ROWS.map((row) => entityFor(hass, device, row)).filter(Boolean) : [];
    const signature = `${device}:${ids.join(",")}`;
    if (signature !== this._signature) {
      this._signature = signature;
      this._ids = ids;
      this._paint();
      return;
    }
    if (this._rows) {
      this._rows.forEach((row) => {
        row.hass = hass;
      });
    }
  }

  getCardSize() {
    return 8;
  }

  _paint() {
    const hass = this._hass;
    if (!this._card) {
      this._card = document.createElement("ha-card");
      this._header = document.createElement("h1");
      this._header.className = "card-header";
      this._body = document.createElement("div");
      this._card.append(this._header, this._body);
      this.replaceChildren(this._card);
    }
    const device = (this._config && this._config.device) || "";
    const devices = hass ? devicesFor(hass) : [];
    const selected = devices.find((item) => item.id === device);
    this._header.textContent = selected ? selected.name : "GitHub - Custom_Component";
    this._body.replaceChildren();
    this._rows = [];
    if (!device) {
      this._body.append(note("Choose a folder for this card."));
      return;
    }
    if (!this._ids.length) {
      this._body.append(note("This folder has no controls yet. Restart Home Assistant after updating."));
      return;
    }
    this._ids.forEach((entityId) => {
      const row = createRow(entityId);
      row.hass = hass;
      this._rows.push(row);
      this._body.append(row);
    });
  }
}

class GitHubCustomComponentCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._paint();
  }

  set hass(hass) {
    this._hass = hass;
    this._paint();
  }

  _paint() {
    if (!this._hass) {
      return;
    }
    const devices = devicesFor(this._hass);
    const current = (this._config && this._config.device) || "";
    if (!this._select) {
      const label = document.createElement("label");
      label.textContent = "Folder";
      label.style.display = "block";
      label.style.marginBottom = "8px";
      this._select = document.createElement("select");
      this._select.style.width = "100%";
      this._select.style.padding = "8px";
      this._select.addEventListener("change", () => {
        const config = { ...(this._config || {}), device: this._select.value };
        this._config = config;
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.replaceChildren(label, this._select);
    }
    const options = devices.map((device) => device.id).join(",");
    if (this._options !== options) {
      this._options = options;
      this._select.replaceChildren();
      if (!devices.length) {
        const empty = document.createElement("option");
        empty.value = "";
        empty.textContent = "No folders configured";
        this._select.append(empty);
      }
      devices.forEach((device) => {
        const option = document.createElement("option");
        option.value = device.id;
        option.textContent = device.name;
        this._select.append(option);
      });
    }
    if (current && [...this._select.options].some((option) => option.value === current)) {
      this._select.value = current;
    }
  }
}

function note(text) {
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  paragraph.style.padding = "0 16px 16px";
  paragraph.style.margin = "0";
  return paragraph;
}

customElements.define("github-custom-component-card", GitHubCustomComponentCard);
customElements.define("github-custom-component-card-editor", GitHubCustomComponentCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "github-custom-component-card",
  name: "GitHub - Custom_Component",
  description:
    "Update, check, rollback, pause, and status for one folder. Add it to any dashboard page.",
  preview: true,
});
