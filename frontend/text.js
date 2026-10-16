// Safe rendering of model answers: a small Markdown subset turned into DOM nodes.
// Model text only ever becomes text nodes — it is never parsed as HTML.

const INLINE = /\*\*(.+?)\*\*|`([^`\n]+)`|\*(?=\S)([^*\n]+?)(?<=\S)\*/g;
const PDF_NAME = /[\w-]+\.pdf\b/gi;
const LIST_ITEM = /^([-*•+]|\d+[.)])\s+(.*)$/;
const TABLE_RULE = /^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$/;
const ARABIC = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/g;
const LATIN = /[A-Za-z]/g;

function el(tag, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
}

const indent = (line) => line.match(/^\s*/)[0].length;
const isOrdered = (marker) => /^\d/.test(marker);

/** Majority script wins, so filenames inside an Arabic answer don't flip it to LTR. */
export function textDir(text) {
  const ar = text.match(ARABIC)?.length ?? 0;
  const lat = text.match(LATIN)?.length ?? 0;
  if (!ar && !lat) return "auto";
  return ar >= lat * 0.5 ? "rtl" : "ltr";
}

export function renderMarkdown(source, { tableLabel = "Table" } = {}) {
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  const out = document.createDocumentFragment();
  let para = [];

  const flush = () => {
    if (!para.length) return;
    const p = el("p");
    para.forEach((line, k) => {
      if (k) p.append(el("br"));
      inline(p, line);
    });
    out.append(p);
    para = [];
  };

  for (let i = 0; i < lines.length; ) {
    const line = lines[i].trim();
    let m;
    if (!line) {
      flush();
      i++;
    } else if ((m = line.match(/^#{1,6}\s+(.*)$/))) {
      flush();
      const heading = el("h4", "md-h");
      inline(heading, m[1]);
      out.append(heading);
      i++;
    } else if (/^([-*_])(\s*\1){2,}$/.test(line)) {
      flush();
      out.append(el("hr"));
      i++;
    } else if (line.startsWith("|") && TABLE_RULE.test(lines[i + 1]?.trim() ?? "")) {
      flush();
      i = table(lines, i, out, tableLabel);
    } else if (LIST_ITEM.test(line)) {
      flush();
      i = list(lines, i, out);
    } else {
      para.push(line);
      i++;
    }
  }
  flush();
  return out;
}

function cells(row) {
  return row.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
}

function table(lines, i, out, label) {
  const headRow = el("tr");
  for (const text of cells(lines[i])) {
    const th = el("th");
    th.scope = "col";
    inline(th, text);
    headRow.append(th);
  }
  const head = el("thead");
  head.append(headRow);

  const body = el("tbody");
  for (i += 2; i < lines.length && lines[i].trim().startsWith("|"); i++) {
    const tr = el("tr");
    for (const text of cells(lines[i])) {
      const td = el("td");
      inline(td, text);
      tr.append(td);
    }
    body.append(tr);
  }

  const tbl = el("table");
  tbl.append(head, body);
  const wrap = el("div", "table-wrap"); // scrolls on narrow screens; focusable for keyboard users
  wrap.tabIndex = 0;
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", label);
  wrap.append(tbl);
  out.append(wrap);
  return i;
}

// ponytail: one level of nesting; deeper levels flatten into it.
function list(lines, i, out) {
  const base = indent(lines[i]);
  const ordered = isOrdered(lines[i].trim().match(LIST_ITEM)[1]);
  const root = el(ordered ? "ol" : "ul");
  let item = null;

  const sibling = (raw) => {
    const m = raw.trim().match(LIST_ITEM);
    return !!m && indent(raw) < base + 2 && isOrdered(m[1]) === ordered;
  };

  for (; i < lines.length; i++) {
    const raw = lines[i];
    const line = raw.trim();

    if (!line) {
      // A blank line ends the list unless more items or indented content follow.
      let j = i + 1;
      while (j < lines.length && !lines[j].trim()) j++;
      if (j < lines.length && (sibling(lines[j]) || indent(lines[j]) >= base + 2)) {
        i = j - 1;
        continue;
      }
      break;
    }

    const m = line.match(LIST_ITEM);
    if (indent(raw) < base + 2) {
      if (!m || isOrdered(m[1]) !== ordered) break;
      item = el("li");
      inline(item, m[2]);
      if (ordered && !root.children.length) root.start = parseInt(m[1], 10);
      root.append(item);
    } else if (m) {
      let sub = item.lastElementChild;
      if (!sub || !/^(UL|OL)$/.test(sub.tagName)) {
        sub = el(isOrdered(m[1]) ? "ol" : "ul");
        item.append(sub);
      }
      const li = el("li");
      inline(li, m[2]);
      sub.append(li);
    } else {
      item.append(el("br"));
      inline(item, line);
    }
  }
  out.append(root);
  return i;
}

function inline(parent, text) {
  let last = 0;
  for (const m of text.matchAll(INLINE)) {
    if (m.index > last) plain(parent, text.slice(last, m.index));
    if (m[1] !== undefined) {
      const strong = el("strong");
      inline(strong, m[1]);
      parent.append(strong);
    } else if (m[2] !== undefined) {
      const code = el("code");
      code.textContent = m[2];
      parent.append(code);
    } else {
      const em = el("em");
      plain(em, m[3]);
      parent.append(em);
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) plain(parent, text.slice(last));
}

// Source filenames cited inline get a distinct, direction-isolated style.
function plain(parent, text) {
  let last = 0;
  for (const m of text.matchAll(PDF_NAME)) {
    if (m.index > last) parent.append(text.slice(last, m.index));
    const cite = el("span", "cite");
    cite.dir = "ltr";
    cite.textContent = m[0];
    parent.append(cite);
    last = m.index + m[0].length;
  }
  if (last < text.length) parent.append(text.slice(last));
}
