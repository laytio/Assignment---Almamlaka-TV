// Run: node frontend/text.test.mjs
// Checks that model text never becomes markup, and that the Markdown subset and direction detection hold.
import assert from "node:assert/strict";

class FakeElement {
  constructor(tag) {
    this.tagName = tag?.toUpperCase();
    this.children = [];
    this.attributes = {};
  }
  append(...nodes) {
    for (const n of nodes) this.children.push(typeof n === "string" ? { text: n } : n);
  }
  setAttribute(name, value) {
    this.attributes[name] = value;
  }
  set textContent(value) {
    this.children = [{ text: String(value) }];
  }
  get lastElementChild() {
    return this.children.findLast((c) => c.tagName) ?? null;
  }
}
globalThis.document = { createElement: (tag) => new FakeElement(tag), createDocumentFragment: () => new FakeElement() };

const { renderMarkdown, textDir } = await import("./text.js");

const ALLOWED = new Set("p br strong em code span h4 hr ul ol li div table thead tbody tr th td".split(" "));
const tags = (n, out = []) => {
  if (n.tagName) out.push(n.tagName.toLowerCase());
  for (const c of n.children ?? []) tags(c, out);
  return out;
};
const text = (n) => n.text ?? (n.children ?? []).map(text).join("");
const render = (md) => {
  const root = renderMarkdown(md);
  const found = tags(root); // the fragment itself has no tag
  for (const tag of found) assert.ok(ALLOWED.has(tag), `unexpected <${tag}>`);
  return { root, found };
};

// 1. HTML in answers stays text.
{
  const payload = '<img src=x onerror="alert(1)"> **<script>alert(2)</script>**';
  const { root, found } = render(payload);
  assert.deepEqual(found, ["p", "strong"]);
  assert.equal(text(root), '<img src=x onerror="alert(1)"> <script>alert(2)</script>');
}

// 2. Tables.
{
  const { found } = render("| Quarter | Total |\n|---|---:|\n| Q1 2027 | $630,000 |\n| Q2 2027 | $720,000 |");
  assert.equal(found.filter((t) => t === "td").length, 4);
  assert.ok(found.includes("th") && found.includes("table"));
}

// 3. Ordered list with a nested bullet, then a paragraph.
{
  const { root, found } = render("1. **Original:** $2,400,000\n   - Q1: $630,000\n2. **Revised:** $2,600,000\n\nDone.");
  assert.deepEqual(found.filter((t) => /^(ol|ul|li|p)$/.test(t)), ["ol", "li", "ul", "li", "li", "p"]);
  assert.match(text(root), /Done\.$/);
}

// 4. Filenames are styled citations, and their underscores aren't read as italics.
{
  const { found } = render("See Almamlaka_Budget_Timeline.pdf, page 1 and *note*.");
  assert.deepEqual(found, ["p", "span", "em"]);
}

// 5. Direction: majority script wins.
assert.equal(textDir("What is the total project budget?"), "ltr");
assert.equal(textDir("ما هي الميزانية الإجمالية للمشروع؟"), "rtl");
assert.equal(textDir("الميزانية الإجمالية هي 2,600,000 دولار (Almamlaka_Budget_Timeline.pdf، الصفحة 1)."), "rtl");
assert.equal(textDir("123"), "auto");

console.log("text.js: all checks passed");
