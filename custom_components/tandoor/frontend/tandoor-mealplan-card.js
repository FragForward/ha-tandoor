/* Tandoor Mealplan Card v1.3
 * Shows the Tandoor meal plan with recipe images, times and servings.
 * Data source: the "Meal plan today" sensor of the ha-tandoor integration
 * (attribute "days": [{date, meals: [{name, meal_type, servings, image, url,
 *  working_time, waiting_time}]}]).
 *
 * Example card config:
 *   type: custom:tandoor-mealplan-card
 *   entity: sensor.tandoor_essensplan_heute   # your "Meal plan today" sensor
 *   days_to_show: 2
 */

const TANDOOR_CARD_DEFAULTS = {
  days_to_show: 2,
  max_meals_per_day: 0, // 0 = alle
  title: "Essensplan",
  show_image: true,
  show_times: true,
  clickable: true,
  hide_empty_days: false,
};

function tandoorFindMealplanSensor(hass) {
  if (!hass) return "";
  return (
    Object.keys(hass.states).find(
      (id) =>
        id.startsWith("sensor.") &&
        hass.states[id].attributes &&
        Array.isArray(hass.states[id].attributes.days)
    ) || ""
  );
}

class TandoorMealplanCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("tandoor-mealplan-card-editor");
  }

  static getStubConfig(hass) {
    return { entity: tandoorFindMealplanSensor(hass), days_to_show: 2 };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error(
        "tandoor-mealplan-card: 'entity' fehlt (der Sensor 'Essensplan heute' der Tandoor-Integration)"
      );
    }
    this._config = Object.assign({}, TANDOOR_CARD_DEFAULTS, config);
    this._lastKey = null;
  }

  set hass(hass) {
    this._hass = hass;
    const st = hass.states[this._config.entity];
    const key = st ? st.last_updated + "|" + st.state : "missing";
    if (key === this._lastKey) return;
    this._lastKey = key;
    this._render(st);
  }

  getCardSize() {
    return 4;
  }

  _esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  _dayLabel(dateStr) {
    const d = new Date(dateStr + "T00:00:00");
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diff = Math.round((d - today) / 86400000);
    const dat = d.toLocaleDateString(undefined, { day: "numeric", month: "long" });
    if (diff === 0) return "Heute · " + dat;
    if (diff === 1) return "Morgen · " + dat;
    return d.toLocaleDateString(undefined, { weekday: "long" }) + " · " + dat;
  }

  _tile(m) {
    const c = this._config;
    const img = c.show_image && m.image
      ? `<div class="img" style="background-image:url('${this._esc(m.image)}')"></div>`
      : `<div class="img noimg"><ha-icon icon="mdi:silverware-fork-knife"></ha-icon></div>`;
    const chips = [];
    if (c.show_times && m.working_time) chips.push(`<span class="chip"><ha-icon icon="mdi:knife"></ha-icon>${m.working_time} min</span>`);
    if (c.show_times && m.waiting_time) chips.push(`<span class="chip"><ha-icon icon="mdi:timer-sand"></ha-icon>${m.waiting_time} min</span>`);
    if (m.servings) chips.push(`<span class="chip"><ha-icon icon="mdi:account-multiple"></ha-icon>${m.servings}</span>`);
    return `
      <div class="tile ${c.clickable && m.url ? "click" : ""}" ${c.clickable && m.url ? `data-link="${this._esc(m.url)}"` : ""}>
        ${img}
        ${m.meal_type ? `<span class="typ">${this._esc(m.meal_type)}</span>` : ""}
        <div class="body">
          <div class="name">${this._esc(m.name)}</div>
          <div class="chips">${chips.join("")}</div>
        </div>
      </div>`;
  }

  _render(st) {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const c = this._config;

    let content;
    if (!st) {
      content = `<div class="leer">Sensor <b>${this._esc(c.entity)}</b> nicht gefunden.</div>`;
    } else {
      const days = (st.attributes.days || []).slice(0, c.days_to_show);
      content = days
        .filter((d) => !c.hide_empty_days || (d.meals && d.meals.length))
        .map((d) => {
          const meals = c.max_meals_per_day > 0
            ? (d.meals || []).slice(0, c.max_meals_per_day)
            : d.meals || [];
          return `
          <div class="tag">
            <div class="taglabel">${this._esc(this._dayLabel(d.date))}</div>
            ${meals.length
              ? `<div class="row ${meals.length === 1 ? "solo" : ""}">${meals.map((m) => this._tile(m)).join("")}</div>`
              : `<div class="leer">nichts geplant</div>`}
          </div>`;
        })
        .join("");
      if (!content) content = `<div class="leer">nichts geplant</div>`;
    }

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 12px 16px 16px; }
        .titel { font-size: var(--ha-card-header-font-size, 22px); color: var(--ha-card-header-color, var(--primary-text-color)); padding: 4px 0 4px; display: flex; align-items: center; gap: 8px; }
        .titel ha-icon { color: var(--accent-color, #ff9800); }
        .taglabel { font-weight: 600; font-size: 14px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.5px; margin: 10px 0 8px; }
        .row { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 4px; }
        .tile { position: relative; flex: 1 0 200px; max-width: 100%; border-radius: 12px; overflow: hidden; background: var(--secondary-background-color); box-shadow: 0 1px 4px rgba(0,0,0,0.25); }
        .tile.click { cursor: pointer; transition: transform .15s ease; }
        .tile.click:hover { transform: scale(1.03); }
        .img { height: 110px; background-size: cover; background-position: center; }
        .row.solo .img { height: 190px; }
        .img.noimg { display: flex; align-items: center; justify-content: center; color: var(--disabled-text-color); --mdc-icon-size: 42px; }
        .typ { position: absolute; top: 8px; left: 8px; background: rgba(0,0,0,0.65); color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 10px; }
        .body { padding: 8px 10px 10px; }
        .name { font-weight: 600; font-size: 14px; line-height: 1.25; color: var(--primary-text-color); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 2.5em; }
        .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
        .chip { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; color: var(--secondary-text-color); background: var(--divider-color); border-radius: 10px; padding: 1px 7px; --mdc-icon-size: 13px; }
        .leer { color: var(--secondary-text-color); font-style: italic; padding: 4px 0 8px; }
      </style>
      <ha-card>
        ${c.title ? `<div class="titel"><ha-icon icon="mdi:silverware-fork-knife"></ha-icon>${this._esc(c.title)}</div>` : ""}
        ${content}
      </ha-card>`;

    this.shadowRoot.querySelectorAll(".tile.click").forEach((el) => {
      el.addEventListener("click", () => window.open(el.dataset.link, "_blank"));
    });
  }
}

class TandoorMealplanCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = Object.assign({}, TANDOOR_CARD_DEFAULTS, config);
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _labels(lang) {
    const de = {
      entity: "Essensplan-Sensor (Tandoor „Essensplan heute“)",
      title: "Titel",
      days_to_show: "Angezeigte Tage",
      max_meals_per_day: "Max. Mahlzeiten pro Tag (0 = alle)",
      show_image: "Rezeptbilder anzeigen",
      show_times: "Arbeits-/Wartezeit anzeigen",
      clickable: "Klick öffnet Rezept in Tandoor",
      hide_empty_days: "Leere Tage ausblenden",
    };
    const en = {
      entity: "Meal plan sensor (Tandoor 'Meal plan today')",
      title: "Title",
      days_to_show: "Days to show",
      max_meals_per_day: "Max meals per day (0 = all)",
      show_image: "Show recipe images",
      show_times: "Show working/waiting time",
      clickable: "Click opens recipe in Tandoor",
      hide_empty_days: "Hide empty days",
    };
    return String(lang || "").startsWith("de") ? de : en;
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (e) => {
        const config = { type: "custom:tandoor-mealplan-card", ...e.detail.value };
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.appendChild(this._form);
    }
    const labels = this._labels(this._hass.language);
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = [
      {
        name: "entity",
        required: true,
        selector: { entity: { domain: "sensor", integration: "tandoor" } },
      },
      { name: "title", selector: { text: {} } },
      {
        name: "days_to_show",
        selector: { number: { min: 1, max: 7, mode: "slider" } },
      },
      {
        name: "max_meals_per_day",
        selector: { number: { min: 0, max: 8, mode: "slider" } },
      },
      { name: "show_image", selector: { boolean: {} } },
      { name: "show_times", selector: { boolean: {} } },
      { name: "clickable", selector: { boolean: {} } },
      { name: "hide_empty_days", selector: { boolean: {} } },
    ];
    this._form.computeLabel = (schema) => labels[schema.name] || schema.name;
  }
}

customElements.define("tandoor-mealplan-card", TandoorMealplanCard);
customElements.define("tandoor-mealplan-card-editor", TandoorMealplanCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "tandoor-mealplan-card",
  name: "Tandoor Mealplan Card",
  description: "Meal plan from Tandoor Recipes with recipe images (needs the ha-tandoor integration)",
  preview: true,
});
