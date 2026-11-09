/* Adaptive Intelligence question card, no external dependencies.
 * HA native websocket call_service with return_response.
 * Read-only: never changes an entity or invokes a device action.
 */
class AdaptiveExplainCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this._query = "";
    this._busy = false;
    this._ready = false;
  }
  setConfig(config) {
    this._config = config || {};
    if (!this._ready) this._build();
  }
  set hass(hass) {
    this._hass = hass;
  }
  getCardSize() { return 5; }
  _build() {
    this._ready = true;
    const root = this.shadowRoot;
    const sheet = document.createElement("style");
    sheet.textContent = `
      :host { display: block; color: var(--primary-text-color); }
      ha-card { display:block; padding: 20px; }
      h2 { margin: 0 0 8px; font-size: 21px; }
      p.intro { color:var(--secondary-text-color); margin:0 0 16px; line-height:1.55; }
      .form { display:flex; gap:10px; flex-wrap:wrap; }
      input { flex: 1 1 240px; width:100%; box-sizing:border-box; padding:13px 14px; border:1px solid var(--divider-color); border-radius:10px; background:var(--card-background-color); color:var(--primary-text-color); font:inherit; min-width:0; }
      button { cursor:pointer; font:inherit; padding:11px 16px; border-radius:10px; border:1px solid var(--divider-color); color:var(--primary-text-color); background:var(--secondary-background-color); }
      button.submit { border:0; background:var(--primary-color); color:var(--text-primary-color, white); font-weight:600; }
      button:disabled { cursor:wait; opacity:.65; }
      .examples { display:flex; flex-wrap:wrap; gap:8px; margin-top:13px; }
      .examples button { font-size:13px; text-align:left; }
      .result { display:none; white-space:pre-wrap; line-height:1.6; margin-top:18px; background:var(--secondary-background-color); border-radius:12px; padding:16px; overflow-wrap:anywhere; }
      .result.visible {display:block}
      .meta { font-size:12px; color:var(--secondary-text-color); margin-top:10px; }
      .causes { margin:10px 0 0; padding-left:19px; }
      .causes li { margin:5px 0; }
      .hint {color:var(--secondary-text-color);font-size:12px;margin-top:12px}
    `;
    root.appendChild(sheet);
    const card = document.createElement("ha-card");
    const title = document.createElement("h2"); title.textContent = "Ask Adaptive Intelligence";
    const intro = document.createElement("p");
    intro.className = "intro";
    intro.textContent = "Ask why a light is on, off, or not responding automatically. Answers use live Home Assistant evidence and identify what remains uncertain.";
    const form = document.createElement("form"); form.className = "form";
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Why isn't the Snug Sofa LED turning on automatically tonight?";
    input.autocomplete = "off";
    input.maxLength = 512;
    input.setAttribute("aria-label", "Ask a question about a light");
    const submit = document.createElement("button");
    submit.className = "submit"; submit.type="submit"; submit.textContent="Explain";
    form.append(input, submit);
    form.addEventListener("submit", (e) => {e.preventDefault(); this._ask(input.value);});
    const examples = document.createElement("div"); examples.className="examples";
    for (const sample of [
      "Why isn't the Snug Sofa LED turning on automatically tonight?",
      "Why is the Snug Sofa LED on?",
      "Why isn't the Snug Corner light turning on?"
    ]) {
      const b=document.createElement("button");b.type="button";b.textContent=sample;
      b.addEventListener("click",()=>{ input.value=sample; this._ask(sample); });
      examples.appendChild(b);
    }
    const result=document.createElement("section");result.className="result";result.setAttribute("aria-live","polite");
    const hint=document.createElement("div");hint.className="hint";
    hint.textContent="Diagnostic queries only — this dashboard will never switch a light or modify an automation.";
    card.append(title,intro,form,examples,result,hint);root.appendChild(card);
    this._els={input,submit,result};
  }
  async _ask(raw) {
    const q=String(raw||"").trim();
    if (!q || this._busy) return;
    this._busy=true; this._els.submit.disabled=true;
    this._els.submit.textContent="Checking…";
    this._els.result.className="result visible";
    this._els.result.textContent="Inspecting Home Assistant configuration and live states…";
    try {
      if (!this._hass || !this._hass.connection) throw Error("Home Assistant is not connected.");
      const payload = await this._hass.connection.sendMessagePromise({
        type:"call_service",domain:"adaptive_intelligence",service:"explain_light",
        service_data:{query:q},return_response:true
      });
      const r=payload && (payload.response || payload);
      if (!r || typeof r !== "object") throw Error("The integration returned no diagnostic response.");
      this._els.result.replaceChildren();
      const text=document.createElement("div");
      text.textContent=r.answer || "No explanation was returned.";
      this._els.result.appendChild(text);
      if (Array.isArray(r.causes) && r.causes.length) {
        const list=document.createElement("ul");list.className="causes";
        for(const cause of r.causes) {
          const li=document.createElement("li");
          li.textContent=(cause.certainty === "confirmed" ? "Confirmed: " : "Possible: ")+(cause.detail || cause.code);
          list.appendChild(li);
        }
        this._els.result.appendChild(list);
      }
      if(Array.isArray(r.candidates) && r.candidates.length) {
        const label=document.createElement("div");
        label.textContent="More than one light matches. Select the one you mean:";
        this._els.result.appendChild(label);
        const choices=document.createElement("div"); choices.className="examples";
        for (const entity of r.candidates) {
          if (typeof entity !== "string" || !entity.startsWith("light.")) continue;
          const choice=document.createElement("button");
          choice.type="button";choice.textContent=entity;
          choice.addEventListener("click",()=>{this._els.input.value=entity;this._ask(entity);});
          choices.appendChild(choice);
        }
        this._els.result.appendChild(choices);
      }
      const meta=document.createElement("div");meta.className="meta";
      meta.textContent="Evidence: "+(r.certainty || r.status || "not yet verified")+
        " · Read only · "+new Date().toLocaleTimeString();
      this._els.result.appendChild(meta);
    } catch (err) {
      this._els.result.textContent="Unable to explain this light: "+
        (err && err.message ? err.message : String(err))+
        ". Check that Adaptive Intelligence is loaded and the explain_light service is registered.";
    } finally {
      this._busy=false;this._els.submit.disabled=false;this._els.submit.textContent="Explain";
    }
  }
}
if (!customElements.get("adaptive-explain-card")) customElements.define("adaptive-explain-card", AdaptiveExplainCard);
window.customCards=window.customCards||[];
if (!window.customCards.some(x=>x.type==="adaptive-explain-card")) {
  window.customCards.push({type:"adaptive-explain-card",name:"Adaptive Intelligence — Ask Why",
    description:"Read-only natural-language lighting diagnostics."});
}
