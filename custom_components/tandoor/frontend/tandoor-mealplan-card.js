/* Tandoor Mealplan Card v0.5.4
 * Shows the Tandoor meal plan with recipe images, times and servings.
 * Data source: the "Meal plan today" sensor of the ha-tandoor integration
 * (attribute "days": [{date, meals: [{name, meal_type, servings, image, url,
 *  working_time, waiting_time}]}]).
 *
 * Example card config:
 *   type: custom:tandoor-mealplan-card
 *   entity: sensor.tandoor_essensplan_heute   # your "Meal plan today" sensor
 *   days_to_show: 2
 *
 * This file also registers custom:tandoor-kochliste-card (see below) so no
 * extra Lovelace resource is needed.
 */

const TANDOOR_CARD_DEFAULTS = {
  days_to_show: 2,
  max_meals_per_day: 0, // 0 = alle
  title: "Essensplan",
  show_image: true,
  show_times: true,
  clickable: true,
  hide_empty_days: false,
  compact_no_image: true, // Rezepte ohne Bild schmaler (ohne großen Platzhalter) anzeigen
  compact_empty_days: true, // Tage ohne Rezept kompakt in einer Zeile anzeigen
  show_rating: true, // Bewertungssterne anzeigen und bearbeitbar machen
  recipe_popup: true, // Klick öffnet Rezept im In-Page-Dialog (statt neuem Tab) – nötig für Fully Kiosk
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
    const hasImg = !!(c.show_image && m.image);
    // Kein Bild + Kompaktmodus: Kachel ohne großen Bild-/Platzhalterblock rendern.
    const compact = !hasImg && c.compact_no_image;
    const rid = m.recipe_id != null ? String(m.recipe_id) : "";
    const canPopup = c.recipe_popup && rid;
    const link = c.clickable && m.url ? this._esc(m.url) : "";
    const clickable = canPopup || link;
    let img = "";
    if (hasImg) {
      img = `<div class="img" style="background-image:url('${this._esc(m.image)}')"></div>`;
    } else if (!compact) {
      img = `<div class="img noimg"><ha-icon icon="mdi:silverware-fork-knife"></ha-icon></div>`;
    }
    // Sterne oben rechts + großes unsichtbares Tap-Target zum Bewerten.
    const stars = c.show_rating && rid
      ? `<div class="starbox">
           <div class="stars">${this._stars(m.rating)}</div>
           <button class="ratebtn" aria-label="Bewerten" data-recipe-id="${rid}" data-rating="${Math.round(Number(m.rating) || 0)}"></button>
         </div>`
      : "";
    const chips = [];
    // Im Kompaktmodus gibt es keinen Bildbereich für das absolut positionierte
    // Typ-Label — daher als Chip mit einreihen.
    if (compact && m.meal_type) chips.push(`<span class="chip typchip">${this._esc(m.meal_type)}</span>`);
    if (c.show_times && m.working_time) chips.push(`<span class="chip"><ha-icon icon="mdi:knife"></ha-icon>${m.working_time} min</span>`);
    if (c.show_times && m.waiting_time) chips.push(`<span class="chip"><ha-icon icon="mdi:timer-sand"></ha-icon>${m.waiting_time} min</span>`);
    if (m.servings) chips.push(`<span class="chip"><ha-icon icon="mdi:account-multiple"></ha-icon>${m.servings}</span>`);
    const nameIcon = compact ? `<ha-icon class="nameicon" icon="mdi:silverware-fork-knife"></ha-icon>` : "";
    return `
      <div class="tile ${compact ? "compact" : ""} ${clickable ? "click" : ""}" data-recipe-id="${rid}" ${link ? `data-link="${link}"` : ""}>
        ${img}
        ${!compact && m.meal_type ? `<span class="typ">${this._esc(m.meal_type)}</span>` : ""}
        ${stars}
        <div class="body">
          <div class="name">${nameIcon}${this._esc(m.name)}</div>
          ${chips.length ? `<div class="chips">${chips.join("")}</div>` : ""}
        </div>
      </div>`;
  }

  _render(st) {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const c = this._config;

    let content;
    try {
      if (!st) {
        content = `<div class="leer">Sensor <b>${this._esc(c.entity)}</b> nicht gefunden.</div>`;
      } else {
        const days = (st.attributes && Array.isArray(st.attributes.days) ? st.attributes.days : []).slice(0, c.days_to_show);
        content = days
          .filter((d) => !c.hide_empty_days || (d.meals && d.meals.length))
          .map((d) => {
            const meals = c.max_meals_per_day > 0
              ? (d.meals || []).slice(0, c.max_meals_per_day)
              : d.meals || [];
            const label = this._esc(this._dayLabel(d.date));
            if (!meals.length) {
              // Leerer Tag: kompakt in einer Zeile (Label + Hinweis) statt großem Block.
              return c.compact_empty_days
                ? `<div class="tag empty"><span class="taglabel inline">${label}</span><span class="leer">nichts geplant</span></div>`
                : `<div class="tag"><div class="taglabel">${label}</div><div class="leer">nichts geplant</div></div>`;
            }
            return `
          <div class="tag">
            <div class="taglabel">${label}</div>
            <div class="row ${meals.length === 1 ? "solo" : ""}">${meals.map((m) => this._tile(m)).join("")}</div>
          </div>`;
          })
          .join("");
        if (!content) content = `<div class="leer">nichts geplant</div>`;
      }
    } catch (err) {
      // Nie die HA-Fehlerkarte auslösen — lieber lesbare Meldung in der Karte zeigen.
      content = `<div class="leer">Anzeige fehlgeschlagen: ${this._esc((err && err.message) || err)}</div>`;
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
        .tile.compact { flex: 0 1 220px; }
        .img { height: 110px; background-size: cover; background-position: center; }
        .row.solo .img { height: 190px; }
        .img.noimg { display: flex; align-items: center; justify-content: center; color: var(--disabled-text-color); --mdc-icon-size: 42px; }
        .typ { position: absolute; top: 8px; left: 8px; background: rgba(0,0,0,0.65); color: #fff; font-size: 11px; padding: 2px 8px; border-radius: 10px; }
        .body { padding: 8px 10px 10px; }
        .tile.compact .body { padding: 10px 12px; }
        .name { font-weight: 600; font-size: 14px; line-height: 1.25; color: var(--primary-text-color); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 2.5em; }
        .tile.compact .name { min-height: 0; display: block; }
        .name .nameicon { color: var(--secondary-text-color); --mdc-icon-size: 18px; margin-right: 6px; vertical-align: -4px; }
        .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
        .chip { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; color: var(--secondary-text-color); background: var(--divider-color); border-radius: 10px; padding: 1px 7px; --mdc-icon-size: 13px; }
        .chip.typchip { color: var(--primary-text-color); }
        .leer { color: var(--secondary-text-color); font-style: italic; padding: 4px 0 8px; }
        .tag.empty { display: flex; align-items: baseline; gap: 8px; }
        .taglabel.inline { margin: 8px 0; }
        .tag.empty .leer { padding: 0; }
        .starbox { position: absolute; top: 6px; right: 6px; z-index: 2; }
        .stars { display: flex; gap: 1px; background: rgba(0,0,0,0.55); border-radius: 12px; padding: 3px 6px; --mdc-icon-size: 15px; color: #ffca28; pointer-events: none; }
        .tile.compact .stars { background: var(--divider-color); }
        .ratebtn { position: absolute; top: -8px; right: -8px; width: 56px; height: 48px; padding: 0; margin: 0; border: 0; background: transparent; cursor: pointer; }
        .tdlg-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: flex-start; justify-content: center; z-index: 9; padding: 24px 12px; overflow-y: auto; }
        .tdlg { background: var(--ha-card-background, var(--card-background-color, #fff)); color: var(--primary-text-color); border-radius: 16px; max-width: 560px; width: 100%; box-shadow: 0 8px 40px rgba(0,0,0,0.5); position: relative; overflow: hidden; }
        .tdlg-x { position: absolute; top: 8px; right: 8px; z-index: 3; width: 36px; height: 36px; border-radius: 50%; border: 0; background: rgba(0,0,0,0.5); color: #fff; font-size: 16px; line-height: 1; cursor: pointer; }
        .tdlg-img { height: 200px; background-size: cover; background-position: center; }
        .tdlg-body { padding: 14px 18px 20px; }
        .tdlg-body h2 { margin: 0 0 6px; font-size: 20px; line-height: 1.25; }
        .tdlg-meta { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
        .tdlg-desc { color: var(--secondary-text-color); margin: 8px 0; }
        .tdlg-step { margin-top: 14px; }
        .tdlg-step h3 { margin: 0 0 6px; font-size: 15px; }
        .tdlg-ings { list-style: none; margin: 0 0 8px; padding: 0; }
        .tdlg-ings li { padding: 3px 0; border-bottom: 1px solid var(--divider-color); font-size: 14px; }
        .tdlg-ings li.ing-header { font-weight: 700; border: 0; padding-top: 8px; }
        .tdlg-instr { white-space: pre-wrap; line-height: 1.5; font-size: 14px; }
        .tdlg-rate { display: flex; align-items: center; gap: 4px; margin: 10px 0; --mdc-icon-size: 30px; }
        .tdlg-rate ha-icon { color: #ffca28; cursor: pointer; }
        .tdlg-rate .lbl { color: var(--secondary-text-color); font-size: 13px; margin-left: 8px; }
        .tdlg-actions { display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
        .tdlg-btn { display: inline-flex; align-items: center; gap: 6px; border: 0; border-radius: 10px; padding: 9px 14px; font-size: 14px; cursor: pointer; background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); --mdc-icon-size: 18px; }
        .tdlg-btn.sec { background: var(--divider-color); color: var(--primary-text-color); }
        .tdlg-loading { padding: 40px; text-align: center; color: var(--secondary-text-color); }
      </style>
      <ha-card>
        ${c.title ? `<div class="titel"><ha-icon icon="mdi:silverware-fork-knife"></ha-icon>${this._esc(c.title)}</div>` : ""}
        ${content}
      </ha-card>
      <div class="tdlg-backdrop" style="display:none">
        <div class="tdlg"><button class="tdlg-x" aria-label="Schließen">✕</button><div class="tdlg-content"></div></div>
      </div>`;

    const back = this.shadowRoot.querySelector(".tdlg-backdrop");
    if (back) {
      back.addEventListener("click", (ev) => { if (ev.target === back) this._closeDialog(); });
      back.querySelector(".tdlg-x").addEventListener("click", () => this._closeDialog());
    }
    this.shadowRoot.querySelectorAll(".ratebtn").forEach((el) => {
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        this._openRatingDialog(el.dataset.recipeId, Number(el.dataset.rating) || 0);
      });
    });
    this.shadowRoot.querySelectorAll(".tile.click").forEach((el) => {
      el.addEventListener("click", () => this._onTileClick(el));
    });
  }

  _onTileClick(el) {
    const rid = el.dataset.recipeId || "";
    const url = el.dataset.link || "";
    if (this._config.recipe_popup && rid) {
      this._openRecipeDialog(rid);
    } else if (/^https?:\/\//i.test(url)) {
      window.open(url, "_blank", "noopener");
    }
  }

  _openDialog(html) {
    const back = this.shadowRoot && this.shadowRoot.querySelector(".tdlg-backdrop");
    const content = back && back.querySelector(".tdlg-content");
    if (!back || !content) return;
    content.innerHTML = html;
    back.style.display = "flex";
    this._dialogOpen = true;
    if (!this._onKey) {
      this._onKey = (ev) => { if (ev.key === "Escape") this._closeDialog(); };
    }
    document.addEventListener("keydown", this._onKey);
  }

  _setDialogContent(html) {
    const content = this.shadowRoot && this.shadowRoot.querySelector(".tdlg-backdrop .tdlg-content");
    if (content) content.innerHTML = html;
  }

  _closeDialog() {
    const back = this.shadowRoot && this.shadowRoot.querySelector(".tdlg-backdrop");
    if (back) back.style.display = "none";
    this._dialogOpen = false;
    if (this._onKey) document.removeEventListener("keydown", this._onKey);
    if (this._pendingRender !== undefined) {
      const st = this._pendingRender;
      this._pendingRender = undefined;
      this._render(st);
    }
  }

  async _openRecipeDialog(recipeId) {
    this._openDialog(`<div class="tdlg-loading">Rezept wird geladen…</div>`);
    try {
      const r = await this._hass.callWS({
        type: "tandoor/recipe",
        recipe_id: Number(recipeId),
        entity_id: this._config.entity,
      });
      this._setDialogContent(this._recipeHtml(r));
      this._wireDialogRecipe();
    } catch (err) {
      this._setDialogContent(
        `<div class="tdlg-body"><h2>Rezept</h2><p>Konnte nicht geladen werden.</p><p class="leer">${this._esc((err && err.message) || err)}</p><div class="tdlg-actions"><button class="tdlg-btn sec tdlg-close">Schließen</button></div></div>`
      );
      const cl = this.shadowRoot.querySelector(".tdlg-content .tdlg-close");
      if (cl) cl.addEventListener("click", () => this._closeDialog());
    }
  }

  _recipeHtml(r) {
    const c = this._config;
    const meta = [];
    if (r.working_time) meta.push(`<span class="chip"><ha-icon icon="mdi:knife"></ha-icon>${r.working_time} min</span>`);
    if (r.waiting_time) meta.push(`<span class="chip"><ha-icon icon="mdi:timer-sand"></ha-icon>${r.waiting_time} min</span>`);
    if (r.servings) meta.push(`<span class="chip"><ha-icon icon="mdi:account-multiple"></ha-icon>${r.servings}</span>`);
    const steps = (r.steps || []).map((s) => {
      const ings = (s.ingredients || []).map((i) => {
        if (i.header != null) return `<li class="ing-header">${this._esc(i.header)}</li>`;
        const amt = i.amount ? `${this._fmtAmount(i.amount)} ` : "";
        const unit = i.unit ? `${this._esc(i.unit)} ` : "";
        const note = i.note ? ` <span class="leer">(${this._esc(i.note)})</span>` : "";
        return `<li>${amt}${unit}${this._esc(i.food)}${note}</li>`;
      }).join("");
      const instr = s.instruction ? `<div class="tdlg-instr">${this._esc(s.instruction)}</div>` : "";
      const head = s.name ? `<h3>${this._esc(s.name)}</h3>` : "";
      if (!ings && !instr && !head) return "";
      return `<div class="tdlg-step">${head}${ings ? `<ul class="tdlg-ings">${ings}</ul>` : ""}${instr}</div>`;
    }).join("");
    const rated = Math.round(Number(r.rating) || 0);
    const rate = c.show_rating && r.id != null
      ? `<div class="tdlg-rate" data-recipe-id="${this._esc(String(r.id))}">${this._starPicker(r.rating)}<span class="lbl">${rated ? "Bewertung ändern" : "Zum Bewerten tippen"}</span></div>`
      : "";
    const img = r.image ? `<div class="tdlg-img" style="background-image:url('${this._esc(r.image)}')"></div>` : "";
    return `
      ${img}
      <div class="tdlg-body">
        <h2>${this._esc(r.name)}</h2>
        ${meta.length ? `<div class="tdlg-meta">${meta.join("")}</div>` : ""}
        ${rate}
        ${r.description ? `<div class="tdlg-desc">${this._esc(r.description)}</div>` : ""}
        ${steps}
        <div class="tdlg-actions">
          ${r.url ? `<button class="tdlg-btn tdlg-open" data-url="${this._esc(r.url)}"><ha-icon icon="mdi:open-in-new"></ha-icon>In Tandoor öffnen</button>` : ""}
          <button class="tdlg-btn sec tdlg-close">Schließen</button>
        </div>
      </div>`;
  }

  _wireDialogRecipe() {
    const root = this.shadowRoot && this.shadowRoot.querySelector(".tdlg-content");
    if (!root) return;
    const open = root.querySelector(".tdlg-open");
    if (open) {
      open.addEventListener("click", () => {
        const u = open.dataset.url || "";
        if (/^https?:\/\//i.test(u)) window.open(u, "_blank", "noopener");
      });
    }
    const close = root.querySelector(".tdlg-close");
    if (close) close.addEventListener("click", () => this._closeDialog());
    const rate = root.querySelector(".tdlg-rate");
    if (rate) {
      rate.querySelectorAll("ha-icon[data-val]").forEach((el) => {
        el.addEventListener("click", () => this._applyRating(rate.dataset.recipeId, Number(el.dataset.val), true));
      });
    }
  }

  _openRatingDialog(recipeId, current) {
    if (!recipeId) return;
    this._openDialog(
      `<div class="tdlg-body">
        <h2>Bewertung</h2>
        <div class="tdlg-rate" data-recipe-id="${this._esc(String(recipeId))}">${this._starPicker(current)}</div>
        <div class="tdlg-actions">
          <button class="tdlg-btn sec tdlg-clear">Keine Bewertung</button>
          <button class="tdlg-btn sec tdlg-close">Abbrechen</button>
        </div>
      </div>`
    );
    const root = this.shadowRoot.querySelector(".tdlg-content");
    if (!root) return;
    root.querySelectorAll(".tdlg-rate ha-icon[data-val]").forEach((el) => {
      el.addEventListener("click", () => this._applyRating(recipeId, Number(el.dataset.val), false));
    });
    root.querySelector(".tdlg-clear").addEventListener("click", () => this._applyRating(recipeId, 0, false));
    root.querySelector(".tdlg-close").addEventListener("click", () => this._closeDialog());
  }

  async _applyRating(recipeId, rating, keepDialog) {
    // Optimistische Sofortanzeige im Dialog.
    const rate = this.shadowRoot.querySelector(`.tdlg-rate[data-recipe-id="${recipeId}"]`);
    if (rate) {
      const r = Math.round(Number(rating) || 0);
      rate.querySelectorAll("ha-icon[data-val]").forEach((el) => {
        el.setAttribute("icon", Number(el.dataset.val) <= r ? "mdi:star" : "mdi:star-outline");
      });
    }
    try {
      await this._hass.callWS({
        type: "tandoor/set_rating",
        recipe_id: Number(recipeId),
        rating: rating || null,
        entity_id: this._config.entity,
      });
    } catch (err) {
      const root = this.shadowRoot.querySelector(".tdlg-content");
      if (root) {
        const warn = document.createElement("div");
        warn.className = "leer";
        warn.textContent = "Bewertung fehlgeschlagen: " + ((err && err.message) || err);
        root.appendChild(warn);
      }
      return;
    }
    if (!keepDialog) this._closeDialog();
  }

  _stars(rating) {
    const r = Math.round(Number(rating) || 0);
    let out = "";
    for (let i = 1; i <= 5; i++) {
      out += `<ha-icon icon="${i <= r ? "mdi:star" : "mdi:star-outline"}"></ha-icon>`;
    }
    return out;
  }

  _starPicker(rating) {
    const r = Math.round(Number(rating) || 0);
    let out = "";
    for (let i = 1; i <= 5; i++) {
      out += `<ha-icon data-val="${i}" icon="${i <= r ? "mdi:star" : "mdi:star-outline"}"></ha-icon>`;
    }
    return out;
  }

  _fmtAmount(a) {
    const n = Number(a);
    if (!Number.isFinite(n)) return this._esc(a);
    return Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100);
  }

  set hass(hass) {
    this._hass = hass;
    const st = hass.states[this._config.entity];
    const key = st ? st.last_updated + "|" + st.state : "missing";
    if (key === this._lastKey) return;
    this._lastKey = key;
    // Nicht neu rendern, solange ein Dialog offen ist — sonst würde er weggerissen.
    if (this._dialogOpen) {
      this._pendingRender = st;
      return;
    }
    try {
      this._render(st);
    } catch (err) {
      // Absturz beim Rendern darf nicht die HA-Fehlerkarte (rotes Kästchen) auslösen.
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      this.shadowRoot.innerHTML = `<ha-card style="padding:12px 16px 16px"><div style="color:var(--secondary-text-color);font-style:italic">Tandoor-Karte: Anzeige fehlgeschlagen (${this._esc((err && err.message) || err)})</div></ha-card>`;
    }
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
      compact_no_image: "Rezepte ohne Bild kompakt anzeigen",
      compact_empty_days: "Leere Tage kompakt (einzeilig) anzeigen",
      show_rating: "Bewertungssterne anzeigen/bearbeiten",
      recipe_popup: "Rezept im Popup öffnen (Fully Kiosk)",
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
      compact_no_image: "Compact tiles for recipes without image",
      compact_empty_days: "Compact (single-line) empty days",
      show_rating: "Show/edit rating stars",
      recipe_popup: "Open recipe in popup (Fully Kiosk)",
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
      { name: "compact_no_image", selector: { boolean: {} } },
      { name: "show_times", selector: { boolean: {} } },
      { name: "show_rating", selector: { boolean: {} } },
      { name: "clickable", selector: { boolean: {} } },
      { name: "recipe_popup", selector: { boolean: {} } },
      { name: "hide_empty_days", selector: { boolean: {} } },
      { name: "compact_empty_days", selector: { boolean: {} } },
    ];
    this._form.computeLabel = (schema) => labels[schema.name] || schema.name;
  }
}

/* Tandoor Kochliste Card v0.5.4
 * Shows the Kochliste (cooking backlog) of the Essensplan website.
 * Data source: the "Kochliste" sensor of the ha-tandoor integration
 * (attributes "rezepte": [{id, titel, recipe_id, bild, quelle, status,
 *  hinzugefuegt, gekocht_am}] and "batch").
 *
 * Example card config:
 *   type: custom:tandoor-kochliste-card
 *   entity: sensor.tandoor_kochliste   # optional, auto-detected
 */

const TANDOOR_KOCHLISTE_DEFAULTS = {
  title: "Kochliste",
  essensplan_url: "http://192.168.1.4:8091",
  show_gekocht: true, // gekochte Rezepte der letzten Tage klein anzeigen
  gekocht_tage: 3,
  confirm_gekocht: true, // vor dem Abhaken nachfragen
};

function tandoorFindKochlisteSensor(hass) {
  if (!hass) return "";
  return (
    Object.keys(hass.states).find(
      (id) =>
        id.startsWith("sensor.") &&
        hass.states[id].attributes &&
        Array.isArray(hass.states[id].attributes.rezepte)
    ) || ""
  );
}

class TandoorKochlisteCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("tandoor-kochliste-card-editor");
  }

  static getStubConfig(hass) {
    return { entity: tandoorFindKochlisteSensor(hass) };
  }

  setConfig(config) {
    this._config = Object.assign({}, TANDOOR_KOCHLISTE_DEFAULTS, config);
    this._lastKey = null;
  }

  getCardSize() {
    return 4;
  }

  _esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  _entityId() {
    return (this._config && this._config.entity) || this._autoEntity || "";
  }

  set hass(hass) {
    this._hass = hass;
    if (this._config && !this._config.entity && !this._autoEntity) {
      this._autoEntity = tandoorFindKochlisteSensor(hass);
    }
    const st = hass.states[this._entityId()];
    const key = st ? st.last_updated + "|" + st.state : "missing";
    if (key === this._lastKey) return;
    this._lastKey = key;
    // Nicht neu rendern, solange ein Dialog offen ist — sonst würde er weggerissen.
    if (this._dialogOpen) {
      this._pendingRender = st;
      return;
    }
    try {
      this._render(st);
    } catch (err) {
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      this.shadowRoot.innerHTML = `<ha-card style="padding:12px 16px 16px"><div style="color:var(--secondary-text-color);font-style:italic">Kochliste-Karte: Anzeige fehlgeschlagen (${this._esc((err && err.message) || err)})</div></ha-card>`;
    }
  }

  _row(r) {
    const einkaufen = r.status === "einkaufen";
    const rid = r.recipe_id != null ? this._esc(String(r.recipe_id)) : "";
    const img = r.bild
      ? `<div class="kimg" style="background-image:url('${this._esc(r.bild)}')"></div>`
      : `<div class="kimg noimg"><ha-icon icon="mdi:chef-hat"></ha-icon></div>`;
    const chip = einkaufen
      ? `<span class="kchip einkaufen">🛒 einkaufen</span>`
      : `<span class="kchip kochbar">kochbar</span>`;
    const action = einkaufen
      ? `<button class="kbtn eingekauft" data-id="${this._esc(r.id)}" data-titel="${this._esc(r.titel)}"><ha-icon icon="mdi:cart-check"></ha-icon>Eingekauft ✓</button>`
      : `<button class="kbtn gekocht" data-id="${this._esc(r.id)}" data-recipe-id="${rid}" data-titel="${this._esc(r.titel)}"><ha-icon icon="mdi:check"></ha-icon>Gekocht ✓</button>`;
    return `
      <div class="krow ${einkaufen ? "dim" : ""}">
        <div class="ktap"${rid ? ` data-recipe-id="${rid}"` : ""}>
          ${img}
          <div class="kmain">
            <div class="ktitel">${this._esc(r.titel)}</div>
            <div class="kchips">${chip}</div>
          </div>
        </div>
        ${action}
      </div>`;
  }

  _doneRow(r) {
    let when = "";
    if (r.gekocht_am) {
      const d = new Date(r.gekocht_am);
      if (!isNaN(d)) {
        when = " · " + d.toLocaleDateString(undefined, { day: "numeric", month: "long" });
      }
    }
    return `<div class="kdone">✓ ${this._esc(r.titel)}${this._esc(when)}</div>`;
  }

  _render(st) {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const c = this._config;

    let content;
    try {
      if (!st) {
        content = `<div class="leer">Kochliste-Sensor ${this._entityId() ? `<b>${this._esc(this._entityId())}</b> nicht gefunden` : "nicht gefunden (Option essensplan_url der Tandoor-Integration prüfen)"}.</div>`;
      } else {
        const rezepte =
          st.attributes && Array.isArray(st.attributes.rezepte)
            ? st.attributes.rezepte.filter((r) => r && typeof r === "object")
            : [];
        const offen = rezepte.filter((r) => r.status !== "gekocht");
        const kochbar = offen.filter((r) => r.status !== "einkaufen");
        const einkaufen = offen.filter((r) => r.status === "einkaufen");
        const maxAge = (Number(c.gekocht_tage) || 3) * 86400000;
        const done = c.show_gekocht
          ? rezepte.filter((r) => {
              if (r.status !== "gekocht" || !r.gekocht_am) return false;
              const d = new Date(r.gekocht_am);
              return !isNaN(d) && Date.now() - d.getTime() <= maxAge;
            })
          : [];
        // Nur Rezepte zeigen, deren Zutaten schon auf der Einkaufsliste (Bring)
        // sind — der Rest wartet eingeklappt. Ohne bring-Info (alte API): alle.
        const hatBringInfo = einkaufen.some((r) => r.bring !== undefined);
        const imBring = hatBringInfo ? einkaufen.filter((r) => r.bring) : einkaufen;
        const geplant = hatBringInfo ? einkaufen.filter((r) => !r.bring) : [];
        // Einkaufs-Fortschritt: wie viele der offenen Rezepte sind schon eingekauft?
        const einkaufBlock = einkaufen.length
          ? `<div class="ksub"><span>🛒 Zum Einkaufen · <b>${kochbar.length}/${offen.length}</b> eingekauft</span><button class="kbtn shoplink"><ha-icon icon="mdi:cart-outline"></ha-icon>Einkaufsliste</button></div>` +
            imBring.map((r) => this._row(r)).join("") +
            (geplant.length
              ? `<button class="kfold">${this._geplantOffen ? "▾" : "▸"} ${geplant.length} weitere geplant (noch nicht auf der Einkaufsliste)</button><div class="kfold-liste" style="display:${this._geplantOffen ? "block" : "none"}">${geplant.map((r) => this._row(r)).join("")}</div>`
              : "")
          : "";
        content =
          (kochbar.length
            ? kochbar.map((r) => this._row(r)).join("")
            : `<div class="leer">${offen.length ? "Noch nichts kochbar — erst einkaufen 🛒" : "Kochliste ist leer — alles gekocht! 🎉"}</div>`) +
          einkaufBlock +
          (done.length ? `<div class="kdones">${done.map((r) => this._doneRow(r)).join("")}</div>` : "");
      }
    } catch (err) {
      // Nie die HA-Fehlerkarte auslösen — lieber lesbare Meldung in der Karte zeigen.
      content = `<div class="leer">Anzeige fehlgeschlagen: ${this._esc((err && err.message) || err)}</div>`;
    }

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 12px 16px 16px; }
        .titel { font-size: var(--ha-card-header-font-size, 22px); color: var(--ha-card-header-color, var(--primary-text-color)); padding: 4px 0 8px; display: flex; align-items: center; gap: 8px; }
        .titel ha-icon { color: var(--accent-color, #ff9800); }
        .krow { display: flex; align-items: center; gap: 12px; padding: 7px 0; border-bottom: 1px solid var(--divider-color); }
        .krow:last-of-type { border-bottom: 0; }
        .krow.dim .kimg, .krow.dim .ktitel { opacity: 0.55; }
        .kimg { width: 60px; height: 60px; flex: 0 0 60px; border-radius: 50%; background-size: cover; background-position: center; box-shadow: 0 1px 4px rgba(0,0,0,0.25); }
        .kimg.noimg { display: flex; align-items: center; justify-content: center; background: var(--secondary-background-color); color: var(--disabled-text-color); --mdc-icon-size: 28px; }
        .kmain { flex: 1 1 auto; min-width: 0; }
        .ktitel { font-weight: 600; font-size: 14px; line-height: 1.25; color: var(--primary-text-color); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
        .kchips { margin-top: 4px; }
        .kchip { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; border-radius: 10px; padding: 1px 8px; background: var(--divider-color); color: var(--secondary-text-color); }
        .kchip.einkaufen { background: rgba(255, 152, 0, 0.18); color: var(--accent-color, #ff9800); }
        .kbtn { flex: 0 0 auto; display: inline-flex; align-items: center; gap: 5px; border: 0; border-radius: 10px; padding: 8px 12px; font-size: 13px; font-weight: 600; cursor: pointer; --mdc-icon-size: 17px; }
        .kbtn.gekocht { background: rgba(76, 175, 80, 0.9); color: #fff; }
        .kbtn.gekocht:disabled { opacity: 0.5; cursor: default; }
        .kbtn.shoplink { background: var(--divider-color); color: var(--secondary-text-color); font-weight: 400; }
        .kbtn.eingekauft { background: rgba(255, 152, 0, 0.85); color: #fff; }
        .kbtn.eingekauft:disabled { opacity: 0.5; cursor: default; }
        .ksub { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 12px; padding: 6px 0 2px; border-top: 1px solid var(--divider-color); font-size: 13px; color: var(--secondary-text-color); }
        .ksub .kbtn { padding: 5px 10px; font-size: 12px; }
        .ktap { flex: 1 1 auto; min-width: 0; display: flex; align-items: center; gap: 12px; }
        .ktap[data-recipe-id] { cursor: pointer; }
        .kfold { display: block; width: 100%; text-align: left; background: none; border: 0; color: var(--secondary-text-color); font-size: 12px; padding: 8px 0 2px; cursor: pointer; }
        .tdlg.breit { max-width: 560px; }
        .tdlg-frame { display: block; width: 100%; height: 78vh; border: 0; }
        .tdlg-img { height: 200px; background-size: cover; background-position: center; }
        .tdlg-meta { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
        .chip { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; color: var(--secondary-text-color); background: var(--divider-color); border-radius: 10px; padding: 1px 7px; --mdc-icon-size: 13px; }
        .tdlg-desc { color: var(--secondary-text-color); margin: 8px 0; }
        .tdlg-step { margin-top: 14px; }
        .tdlg-step h3 { margin: 0 0 6px; font-size: 15px; }
        .tdlg-ings { list-style: none; margin: 0 0 8px; padding: 0; }
        .tdlg-ings li { padding: 3px 0; border-bottom: 1px solid var(--divider-color); font-size: 14px; }
        .tdlg-ings li.ing-header { font-weight: 700; border: 0; padding-top: 8px; }
        .tdlg-instr { white-space: pre-wrap; line-height: 1.5; font-size: 14px; }
        .tdlg-loading { padding: 40px; text-align: center; color: var(--secondary-text-color); }
        .kdones { margin-top: 10px; padding-top: 6px; border-top: 1px solid var(--divider-color); }
        .kdone { font-size: 12px; color: var(--secondary-text-color); padding: 2px 0; }
        .leer { color: var(--secondary-text-color); font-style: italic; padding: 4px 0 8px; }
        .kwarn { color: var(--error-color, #f44336); font-size: 12px; padding: 4px 0; }
        .tdlg-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: flex-start; justify-content: center; z-index: 9; padding: 24px 12px; overflow-y: auto; }
        .tdlg { background: var(--ha-card-background, var(--card-background-color, #fff)); color: var(--primary-text-color); border-radius: 16px; max-width: 420px; width: 100%; box-shadow: 0 8px 40px rgba(0,0,0,0.5); position: relative; overflow: hidden; }
        .tdlg-x { position: absolute; top: 8px; right: 8px; z-index: 3; width: 36px; height: 36px; border-radius: 50%; border: 0; background: rgba(0,0,0,0.5); color: #fff; font-size: 16px; line-height: 1; cursor: pointer; }
        .tdlg-body { padding: 16px 18px 20px; }
        .tdlg-body h2 { margin: 0 24px 6px 0; font-size: 19px; line-height: 1.25; }
        .klbl { color: var(--secondary-text-color); font-size: 13px; margin: 0 0 6px; }
        .tdlg-rate { display: flex; align-items: center; gap: 4px; margin: 10px 0; --mdc-icon-size: 34px; }
        .tdlg-rate ha-icon { color: #ffca28; cursor: pointer; }
        .kcomment { width: 100%; box-sizing: border-box; margin-top: 8px; padding: 9px 10px; border-radius: 10px; border: 1px solid var(--divider-color); background: var(--secondary-background-color); color: var(--primary-text-color); font: inherit; font-size: 14px; resize: vertical; }
        .tdlg-actions { display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
        .tdlg-btn { display: inline-flex; align-items: center; gap: 6px; border: 0; border-radius: 10px; padding: 9px 14px; font-size: 14px; cursor: pointer; background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); --mdc-icon-size: 18px; }
        .tdlg-btn.sec { background: var(--divider-color); color: var(--primary-text-color); }
      </style>
      <ha-card>
        ${c.title ? `<div class="titel"><ha-icon icon="mdi:chef-hat"></ha-icon>${this._esc(c.title)}</div>` : ""}
        ${content}
      </ha-card>
      <div class="tdlg-backdrop" style="display:none">
        <div class="tdlg"><button class="tdlg-x" aria-label="Schließen">✕</button><div class="tdlg-content"></div></div>
      </div>`;

    const back = this.shadowRoot.querySelector(".tdlg-backdrop");
    if (back) {
      back.addEventListener("click", (ev) => { if (ev.target === back) this._closeDialog(); });
      back.querySelector(".tdlg-x").addEventListener("click", () => this._closeDialog());
    }
    this.shadowRoot.querySelectorAll(".kbtn.gekocht").forEach((el) => {
      el.addEventListener("click", () => this._onGekocht(el));
    });
    this.shadowRoot.querySelectorAll(".kbtn.eingekauft").forEach((el) => {
      el.addEventListener("click", () => this._onEingekauft(el));
    });
    // Einkaufsliste im In-Page-Dialog öffnen (kein neuer Tab — Fully Kiosk!)
    this.shadowRoot.querySelectorAll(".kbtn.shoplink").forEach((el) => {
      el.addEventListener("click", () => this._openEinkaufDialog());
    });
    // Tipp auf Bild/Titel öffnet das Rezept im Dialog
    this.shadowRoot.querySelectorAll(".ktap[data-recipe-id]").forEach((el) => {
      el.addEventListener("click", () => {
        const rid = el.dataset.recipeId || "";
        if (rid) this._openRecipeDialog(rid);
      });
    });
    const fold = this.shadowRoot.querySelector(".kfold");
    if (fold) {
      fold.addEventListener("click", () => {
        this._geplantOffen = !this._geplantOffen;
        const liste = this.shadowRoot.querySelector(".kfold-liste");
        if (liste) liste.style.display = this._geplantOffen ? "block" : "none";
        fold.textContent = (this._geplantOffen ? "▾" : "▸") + fold.textContent.slice(1);
      });
    }
  }

  _setDialogContent(html) {
    const content = this.shadowRoot && this.shadowRoot.querySelector(".tdlg-backdrop .tdlg-content");
    if (content) content.innerHTML = html;
  }

  _openEinkaufDialog() {
    const base = String(this._config.essensplan_url || "").replace(/\/+$/, "");
    if (!/^https?:\/\//i.test(base)) return;
    this._openDialog(`<iframe class="tdlg-frame" src="${this._esc(base + "/einkauf.php")}"></iframe>`);
    const dlg = this.shadowRoot.querySelector(".tdlg");
    if (dlg) dlg.classList.add("breit");
  }

  async _openRecipeDialog(recipeId) {
    this._openDialog(`<div class="tdlg-loading">Rezept wird geladen…</div>`);
    try {
      const r = await this._hass.callWS({
        type: "tandoor/recipe",
        recipe_id: Number(recipeId),
        entity_id: this._config.entity || undefined,
      });
      this._setDialogContent(this._recipeHtml(r));
      this._wireDialogRecipe();
    } catch (err) {
      this._setDialogContent(
        `<div class="tdlg-body"><h2>Rezept</h2><p>Konnte nicht geladen werden.</p><p class="leer">${this._esc((err && err.message) || err)}</p><div class="tdlg-actions"><button class="tdlg-btn sec tdlg-close">Schließen</button></div></div>`
      );
      const cl = this.shadowRoot.querySelector(".tdlg-content .tdlg-close");
      if (cl) cl.addEventListener("click", () => this._closeDialog());
    }
  }

  _fmtAmount(a) {
    const n = Number(a);
    if (!Number.isFinite(n)) return this._esc(a);
    return Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100);
  }

  _recipeHtml(r) {
    const meta = [];
    if (r.working_time) meta.push(`<span class="chip"><ha-icon icon="mdi:knife"></ha-icon>${r.working_time} min</span>`);
    if (r.waiting_time) meta.push(`<span class="chip"><ha-icon icon="mdi:timer-sand"></ha-icon>${r.waiting_time} min</span>`);
    if (r.servings) meta.push(`<span class="chip"><ha-icon icon="mdi:account-multiple"></ha-icon>${r.servings}</span>`);
    const steps = (r.steps || []).map((s) => {
      const ings = (s.ingredients || []).map((i) => {
        if (i.header != null) return `<li class="ing-header">${this._esc(i.header)}</li>`;
        const amt = i.amount ? `${this._fmtAmount(i.amount)} ` : "";
        const unit = i.unit ? `${this._esc(i.unit)} ` : "";
        const note = i.note ? ` <span class="leer">(${this._esc(i.note)})</span>` : "";
        return `<li>${amt}${unit}${this._esc(i.food)}${note}</li>`;
      }).join("");
      const instr = s.instruction ? `<div class="tdlg-instr">${this._esc(s.instruction)}</div>` : "";
      const head = s.name ? `<h3>${this._esc(s.name)}</h3>` : "";
      if (!ings && !instr && !head) return "";
      return `<div class="tdlg-step">${head}${ings ? `<ul class="tdlg-ings">${ings}</ul>` : ""}${instr}</div>`;
    }).join("");
    const img = r.image ? `<div class="tdlg-img" style="background-image:url('${this._esc(r.image)}')"></div>` : "";
    return `
      ${img}
      <div class="tdlg-body">
        <h2>${this._esc(r.name)}</h2>
        ${meta.length ? `<div class="tdlg-meta">${meta.join("")}</div>` : ""}
        ${r.description ? `<div class="tdlg-desc">${this._esc(r.description)}</div>` : ""}
        ${steps}
        <div class="tdlg-actions">
          <button class="tdlg-btn sec tdlg-close">Schließen</button>
        </div>
      </div>`;
  }

  _wireDialogRecipe() {
    const root = this.shadowRoot && this.shadowRoot.querySelector(".tdlg-content");
    if (!root) return;
    const close = root.querySelector(".tdlg-close");
    if (close) close.addEventListener("click", () => this._closeDialog());
  }

  _showWarn(text) {
    const card = this.shadowRoot && this.shadowRoot.querySelector("ha-card");
    if (!card) return;
    const warn = document.createElement("div");
    warn.className = "kwarn";
    warn.textContent = text;
    card.appendChild(warn);
  }

  async _onEingekauft(btn) {
    const id = btn.dataset.id || "";
    const titel = btn.dataset.titel || "";
    if (!id) return;
    if (!window.confirm(`„${titel}“ als eingekauft markieren? Es wird damit kochbar.`)) return;
    btn.disabled = true;
    try {
      await this._hass.callService("tandoor", "kochliste_kochbar", { id });
    } catch (err) {
      btn.disabled = false;
      this._showWarn("Markieren fehlgeschlagen: " + ((err && err.message) || err));
    }
  }

  async _onGekocht(btn) {
    const id = btn.dataset.id || "";
    const titel = btn.dataset.titel || "";
    const recipeId = btn.dataset.recipeId || "";
    if (!id) return;
    if (this._config.confirm_gekocht && !window.confirm(`„${titel}“ als gekocht markieren?`)) return;
    btn.disabled = true;
    try {
      await this._hass.callService("tandoor", "kochliste_gekocht", { id });
    } catch (err) {
      btn.disabled = false;
      this._showWarn("Abhaken fehlgeschlagen: " + ((err && err.message) || err));
      return;
    }
    // Sterne-Dialog nur für Rezepte, die in Tandoor existieren (recipe_id).
    if (recipeId) this._openSterneDialog(recipeId, titel);
  }

  _openSterneDialog(recipeId, titel) {
    this._sterne = 0;
    this._openDialog(`
      <div class="tdlg-body">
        <h2>${this._esc(titel)}</h2>
        <p class="klbl">Wie hat es geschmeckt?</p>
        <div class="tdlg-rate">${this._starPicker(0)}</div>
        <textarea class="kcomment" rows="2" placeholder="Kommentar (optional)"></textarea>
        <div class="tdlg-actions">
          <button class="tdlg-btn sec k-later">Später</button>
          <button class="tdlg-btn k-save">Speichern</button>
        </div>
      </div>`);
    const root = this.shadowRoot.querySelector(".tdlg-content");
    if (!root) return;
    root.querySelectorAll(".tdlg-rate ha-icon[data-val]").forEach((el) => {
      el.addEventListener("click", () => {
        this._sterne = Number(el.dataset.val) || 0;
        root.querySelectorAll(".tdlg-rate ha-icon[data-val]").forEach((s) => {
          s.setAttribute("icon", Number(s.dataset.val) <= this._sterne ? "mdi:star" : "mdi:star-outline");
        });
      });
    });
    root.querySelector(".k-later").addEventListener("click", () => this._closeDialog());
    root.querySelector(".k-save").addEventListener("click", async () => {
      const kommentar = (root.querySelector(".kcomment").value || "").trim();
      try {
        await this._hass.callService("tandoor", "kochliste_bewerten", {
          recipe_id: Number(recipeId),
          sterne: this._sterne,
          kommentar,
        });
      } catch (err) {
        const warn = document.createElement("div");
        warn.className = "kwarn";
        warn.textContent = "Bewertung fehlgeschlagen: " + ((err && err.message) || err);
        root.appendChild(warn);
        return;
      }
      this._closeDialog();
    });
  }

  _starPicker(rating) {
    const r = Math.round(Number(rating) || 0);
    let out = "";
    for (let i = 1; i <= 5; i++) {
      out += `<ha-icon data-val="${i}" icon="${i <= r ? "mdi:star" : "mdi:star-outline"}"></ha-icon>`;
    }
    return out;
  }

  _openDialog(html) {
    const back = this.shadowRoot && this.shadowRoot.querySelector(".tdlg-backdrop");
    const content = back && back.querySelector(".tdlg-content");
    if (!back || !content) return;
    content.innerHTML = html;
    back.style.display = "flex";
    this._dialogOpen = true;
    if (!this._onKey) {
      this._onKey = (ev) => { if (ev.key === "Escape") this._closeDialog(); };
    }
    document.addEventListener("keydown", this._onKey);
  }

  _closeDialog() {
    const back = this.shadowRoot && this.shadowRoot.querySelector(".tdlg-backdrop");
    if (back) back.style.display = "none";
    const dlg = this.shadowRoot && this.shadowRoot.querySelector(".tdlg");
    if (dlg) dlg.classList.remove("breit");
    this._dialogOpen = false;
    if (this._onKey) document.removeEventListener("keydown", this._onKey);
    if (this._pendingRender !== undefined) {
      const st = this._pendingRender;
      this._pendingRender = undefined;
      this._render(st);
    }
  }
}

class TandoorKochlisteCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = Object.assign({}, TANDOOR_KOCHLISTE_DEFAULTS, config);
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _labels(lang) {
    const de = {
      entity: "Kochliste-Sensor (Tandoor „Kochliste“)",
      title: "Titel",
      essensplan_url: "Essensplan-URL (für den Einkaufslisten-Link)",
      show_gekocht: "Gekochte der letzten Tage anzeigen",
      gekocht_tage: "Gekochte anzeigen für (Tage)",
      confirm_gekocht: "Vor dem Abhaken nachfragen",
    };
    const en = {
      entity: "Kochliste sensor (Tandoor 'Kochliste')",
      title: "Title",
      essensplan_url: "Essensplan URL (for the shopping list link)",
      show_gekocht: "Show recently cooked recipes",
      gekocht_tage: "Show cooked for (days)",
      confirm_gekocht: "Confirm before marking as cooked",
    };
    return String(lang || "").startsWith("de") ? de : en;
  }

  _render() {
    if (!this._hass || !this._config) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (e) => {
        const config = { type: "custom:tandoor-kochliste-card", ...e.detail.value };
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
        selector: { entity: { domain: "sensor", integration: "tandoor" } },
      },
      { name: "title", selector: { text: {} } },
      { name: "essensplan_url", selector: { text: {} } },
      { name: "show_gekocht", selector: { boolean: {} } },
      {
        name: "gekocht_tage",
        selector: { number: { min: 1, max: 14, mode: "slider" } },
      },
      { name: "confirm_gekocht", selector: { boolean: {} } },
    ];
    this._form.computeLabel = (schema) => labels[schema.name] || schema.name;
  }
}

// Doppelte Registrierung (z.B. Modul zusätzlich als manuelle Lovelace-Ressource
// geladen) darf keinen Top-Level-Fehler werfen, sonst wird das Element ggf. gar
// nicht definiert → "custom element doesn't exist" (rotes Kästchen).
if (!customElements.get("tandoor-mealplan-card")) {
  customElements.define("tandoor-mealplan-card", TandoorMealplanCard);
}
if (!customElements.get("tandoor-mealplan-card-editor")) {
  customElements.define("tandoor-mealplan-card-editor", TandoorMealplanCardEditor);
}
if (!customElements.get("tandoor-kochliste-card")) {
  customElements.define("tandoor-kochliste-card", TandoorKochlisteCard);
}
if (!customElements.get("tandoor-kochliste-card-editor")) {
  customElements.define("tandoor-kochliste-card-editor", TandoorKochlisteCardEditor);
}
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "tandoor-mealplan-card")) {
  window.customCards.push({
    type: "tandoor-mealplan-card",
    name: "Tandoor Mealplan Card",
    description: "Meal plan from Tandoor Recipes with recipe images (needs the ha-tandoor integration)",
    preview: true,
  });
}
if (!window.customCards.some((c) => c.type === "tandoor-kochliste-card")) {
  window.customCards.push({
    type: "tandoor-kochliste-card",
    name: "Tandoor Kochliste Card",
    description: "Kochliste (cooking backlog) of the Essensplan website with cooked check-off and star rating (needs the ha-tandoor integration)",
    preview: true,
  });
}
