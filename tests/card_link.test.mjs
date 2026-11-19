// Tests for recipe links of the meal plan card (docs/spec/mealplan-card.md, L3, L4, L6).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const cardPath = new URL(
  "../custom_components/tandoor/frontend/tandoor-mealplan-card.js",
  import.meta.url
);

function loadCard() {
  const registry = new Map();
  const sandbox = {
    HTMLElement: class {},
    customElements: {
      get: (n) => registry.get(n),
      define: (n, c) => registry.set(n, c),
    },
    window: {},
    console: { info() {}, warn() {}, error() {}, log() {} },
    document: {},
  };
  vm.createContext(sandbox);
  vm.runInContext(readFileSync(cardPath, "utf8"), sandbox);
  return sandbox;
}

const URL48 = "http://tandoor.local/view/recipe/48";

test("L3: empty template keeps the Tandoor URL", () => {
  const { tandoorBuildLink } = loadCard();
  assert.equal(tandoorBuildLink("", URL48, 48), URL48);
  assert.equal(tandoorBuildLink(undefined, URL48, 48), URL48);
});

test("L4: placeholders are replaced", () => {
  const { tandoorBuildLink } = loadCard();
  assert.equal(
    tandoorBuildLink("https://x.kitshn.app/#{url}", URL48, 48),
    "https://x.kitshn.app/#http://tandoor.local/view/recipe/48"
  );
  assert.equal(
    tandoorBuildLink("https://app.example/r/{id}?u={url_encoded}&again={id}", URL48, 48),
    "https://app.example/r/48?u=http%3A%2F%2Ftandoor.local%2Fview%2Frecipe%2F48&again=48"
  );
});

test("L4: no recipe URL means no link, even with a template", () => {
  const { tandoorBuildLink } = loadCard();
  assert.equal(tandoorBuildLink("https://x.kitshn.app/#{url}", "", null), "");
  assert.equal(tandoorBuildLink("https://x.kitshn.app/#{url}", null, null), "");
});

test("L6: only http(s) links are opened", () => {
  const { tandoorSafeLink } = loadCard();
  assert.equal(tandoorSafeLink("https://x.kitshn.app/#a"), "https://x.kitshn.app/#a");
  assert.equal(tandoorSafeLink("HTTP://tandoor.local/x"), "HTTP://tandoor.local/x");
  assert.equal(tandoorSafeLink("kitshn://recipe/48"), "");
  assert.equal(tandoorSafeLink("javascript:alert(1)"), "");
  assert.equal(tandoorSafeLink(""), "");
});
