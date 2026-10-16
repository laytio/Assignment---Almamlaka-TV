import { renderMarkdown, textDir } from "./text.js";

// Same-origin endpoints. In development, serve.py proxies /api/* to FastAPI.
const API = { chat: "/api/chat", health: "/api/health" };
const TIMEOUT_MS = 120_000;
const MARK_SRC = "assets/almamlaka-mark.png";

const I18N = {
  en: {
    docTitle: "Almamlaka TV — Knowledge Assistant",
    skip: "Skip to question",
    railLabel: "About this assistant",
    channel: "Almamlaka TV",
    appTitle: "Knowledge Assistant",
    newChat: "New chat",
    langSwitch: "العربية",
    langSwitchLabel: "التبديل إلى العربية",
    kbTitle: "Knowledge base",
    kbLoading: "Connecting…",
    kbOnline: "Online · {n} documents",
    kbOffline: "Assistant offline",
    kbNote: "Answers are drawn only from these documents, with page-level citations. General knowledge is never used.",
    grounded: "Document-grounded",
    session: "Session",
    sessionNew: "new",
    eyebrow: "Digital Expansion Initiative",
    welcomeTitle: "Ask the documents.",
    welcomeLead: "Every answer comes from the initiative's source documents and cites the page it came from. Ask in English or Arabic.",
    suggestionsLabel: "Suggested questions",
    conversation: "Conversation",
    inputLabel: "Your question",
    placeholder: "Ask about the budget, timeline, team…",
    send: "Send question",
    hintScope: "Answers are limited to the provided documents.",
    hintKeys: "Enter to send · Shift + Enter for a new line",
    you: "You",
    assistant: "Almamlaka Assistant",
    sources: "Retrieved sources",
    pageShort: "p.",
    relevance: "relevance",
    copy: "Copy",
    copied: "Copied",
    loading1: "Searching the documents…",
    loading2: "Writing a grounded answer…",
    retry: "Try again",
    errNetwork: "Couldn't reach the assistant. Check your connection and try again.",
    errUnavailable: "The assistant service is unavailable right now. Please try again shortly.",
    errTimeout: "The assistant took too long to respond. Please try again.",
    errInvalid: "That question couldn't be processed. Please rephrase it.",
    errServer: "Something went wrong while answering. Please try again.",
    errBadResponse: "The assistant returned an unexpected response.",
    tableLabel: "Table",
  },
  ar: {
    docTitle: "قناة المملكة — المساعد المعرفي",
    skip: "انتقل إلى خانة السؤال",
    railLabel: "عن المساعد",
    channel: "قناة المملكة",
    appTitle: "المساعد المعرفي",
    newChat: "محادثة جديدة",
    langSwitch: "English",
    langSwitchLabel: "Switch to English",
    kbTitle: "قاعدة المعرفة",
    kbLoading: "جارٍ الاتصال…",
    kbOnline: "متصل · {n} وثائق",
    kbOffline: "المساعد غير متصل",
    kbNote: "تُستمد الإجابات من هذه الوثائق فقط، مع الإشارة إلى رقم الصفحة. لا تُستخدم أي معرفة عامة.",
    grounded: "إجابات موثّقة",
    session: "الجلسة",
    sessionNew: "جديدة",
    eyebrow: "مبادرة التوسع الرقمي",
    welcomeTitle: "اسأل الوثائق.",
    welcomeLead: "كل إجابة مستمدة من وثائق المبادرة ومرفقة برقم الصفحة التي وردت فيها. اسأل بالعربية أو بالإنجليزية.",
    suggestionsLabel: "أسئلة مقترحة",
    conversation: "المحادثة",
    inputLabel: "سؤالك",
    placeholder: "اسأل عن الميزانية، الجدول الزمني، الفريق…",
    send: "إرسال السؤال",
    hintScope: "تقتصر الإجابات على الوثائق المتوفرة.",
    hintKeys: "Enter للإرسال · Shift + Enter لسطر جديد",
    you: "أنت",
    assistant: "مساعد المملكة",
    sources: "المصادر المسترجعة",
    pageShort: "ص",
    relevance: "درجة الصلة",
    copy: "نسخ",
    copied: "تم النسخ",
    loading1: "جارٍ البحث في الوثائق…",
    loading2: "جارٍ صياغة إجابة موثّقة…",
    retry: "إعادة المحاولة",
    errNetwork: "تعذّر الوصول إلى المساعد. تحقّق من الاتصال وحاول مجدداً.",
    errUnavailable: "خدمة المساعد غير متاحة حالياً. يرجى المحاولة بعد قليل.",
    errTimeout: "استغرق المساعد وقتاً طويلاً للرد. يرجى المحاولة مجدداً.",
    errInvalid: "تعذّرت معالجة السؤال. يرجى إعادة صياغته.",
    errServer: "حدث خطأ أثناء إعداد الإجابة. يرجى المحاولة مجدداً.",
    errBadResponse: "أعاد المساعد استجابة غير متوقعة.",
    tableLabel: "جدول",
  },
};

const SUGGESTIONS = {
  en: [
    ["Budget", "What is the total project budget?"],
    ["Timeline", "When is the public launch date?"],
    ["Team", "Who leads the project, and who is on the team?"],
    ["Metrics", "How will the project's success be measured?"],
  ],
  ar: [
    ["الميزانية", "ما هي الميزانية الإجمالية للمشروع؟"],
    ["الجدول الزمني", "متى موعد الإطلاق الرسمي للمنصة؟"],
    ["الفريق", "من يقود المشروع ومن هم أعضاء الفريق؟"],
    ["مؤشرات النجاح", "كيف سيتم قياس نجاح المشروع؟"],
  ],
};

// Static, trusted markup only.
const ICONS = {
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  doc: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5M12 16.5v.01"/>',
  retry: '<path d="M4 12a8 8 0 1 0 2.3-5.7"/><path d="M4 4v4h4"/>',
};

const $ = (selector) => document.querySelector(selector);
const ui = {
  scroller: $("#scroller"),
  welcome: $("#welcome"),
  suggestions: $("#suggestions"),
  messages: $("#messages"),
  form: $("#composer"),
  input: $("#question"),
  send: $("#send"),
  newChat: $("#newChat"),
  lang: $("#langToggle"),
  session: $("#sessionId"),
  kbStatus: $("#kbStatus"),
  kbStatusText: $("#kbStatusText"),
  docList: $("#docList"),
};

const state = {
  lang: initialLang(),
  sessionId: null,
  pending: null, // AbortController of the in-flight request
  docs: null, // null = loading, false = offline, array = online
};
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");

class ChatError extends Error {
  constructor(key) {
    super(key);
    this.key = key;
  }
}

// ---------- helpers ----------

function initialLang() {
  try {
    const saved = localStorage.getItem("lang");
    if (saved === "en" || saved === "ar") return saved;
  } catch {}
  return navigator.language?.toLowerCase().startsWith("ar") ? "ar" : "en";
}

function t(key, vars = {}) {
  return (I18N[state.lang][key] ?? I18N.en[key]).replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");
}

function h(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

/** Element whose text follows the UI language. */
function label(tag, className, key) {
  const node = h(tag, className, t(key));
  node.dataset.i18n = key;
  return node;
}

function icon(name, className) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.8");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  if (className) svg.setAttribute("class", className);
  svg.innerHTML = ICONS[name];
  return svg;
}

const docTitle = (file) => file.replace(/\.pdf$/i, "").replace(/^Almamlaka_/i, "").replace(/_/g, " ");

const clock = () =>
  new Date().toLocaleTimeString(state.lang === "ar" ? "ar-u-nu-latn" : "en", { hour: "numeric", minute: "2-digit" });

const behavior = () => (reduceMotion.matches ? "auto" : "smooth");

function scrollToEnd() {
  ui.scroller.scrollTo({ top: ui.scroller.scrollHeight, behavior: behavior() });
}

// ---------- rendering ----------

function applyLang() {
  const root = document.documentElement;
  root.lang = state.lang;
  root.dir = state.lang === "ar" ? "rtl" : "ltr";
  document.title = t("docTitle");
  for (const node of document.querySelectorAll("[data-i18n]")) node.textContent = t(node.dataset.i18n);
  for (const node of document.querySelectorAll("[data-i18n-attr]")) {
    for (const pair of node.dataset.i18nAttr.split(";")) {
      const [attr, key] = pair.split(":");
      node.setAttribute(attr, t(key));
    }
  }
  ui.lang.lang = state.lang === "ar" ? "en" : "ar";
  renderSuggestions();
  renderSession();
  renderStatus();
}

function renderSuggestions() {
  ui.suggestions.replaceChildren(
    ...SUGGESTIONS[state.lang].map(([tag, question], i) => {
      const btn = h("button", "suggestion");
      btn.type = "button";
      btn.style.setProperty("--i", i + 3);
      btn.disabled = !!state.pending;
      btn.append(h("span", "suggestion-tag", tag), h("span", "suggestion-text", question), icon("arrow", "suggestion-arrow"));
      btn.addEventListener("click", () => ask(question));
      return btn;
    }),
  );
}

function renderSession() {
  ui.session.textContent = state.sessionId ? state.sessionId.slice(0, 8) : t("sessionNew");
  ui.session.title = state.sessionId ?? "";
}

function renderStatus() {
  const status = state.docs === null ? "loading" : state.docs ? "online" : "offline";
  ui.kbStatus.dataset.state = status;
  ui.kbStatusText.textContent =
    status === "online" ? t("kbOnline", { n: state.docs.length }) : t(status === "loading" ? "kbLoading" : "kbOffline");
}

function renderDocs() {
  ui.docList.replaceChildren(
    ...(state.docs || []).map((file) => {
      const li = h("li", "doc");
      const name = h("span", "doc-name", docTitle(file));
      const path = h("span", "doc-file", file);
      name.dir = path.dir = "ltr";
      li.append(icon("doc"), name, path);
      return li;
    }),
  );
}

function addUserMessage(text) {
  const msg = h("div", "msg msg-user");
  const bubble = h("div", "bubble");
  const body = h("div", "bubble-text", text);
  body.dir = textDir(text);
  bubble.append(body);
  const meta = h("div", "msg-meta");
  meta.append(label("span", "", "you"), h("span", "msg-time", clock()));
  msg.append(bubble, meta);
  ui.messages.append(msg);
}

function assistantShell(variant) {
  const msg = h("article", "msg msg-ai");
  const avatar = h("img", "avatar");
  avatar.src = MARK_SRC;
  avatar.alt = "";
  avatar.width = avatar.height = 36;
  const card = h("div", variant ? `card ${variant}` : "card");
  const head = h("header", "msg-head");
  head.append(label("span", "msg-name", "assistant"), h("span", "msg-time", clock()));
  card.append(head);
  msg.append(avatar, card);
  return { msg, card, head };
}

function addLoading() {
  const { msg, card } = assistantShell("is-loading");
  const signal = h("span", "signal");
  signal.setAttribute("aria-hidden", "true");
  for (let i = 0; i < 5; i++) signal.append(h("span"));
  const text = label("span", "loading-text", "loading1");
  const row = h("div", "loading-row");
  row.append(signal, text);
  card.append(row);
  ui.messages.append(msg);

  // Retrieval is quick; generation is the long part.
  const timer = setTimeout(() => {
    text.dataset.i18n = "loading2";
    text.textContent = t("loading2");
  }, 3500);
  return { node: msg, stop: () => clearTimeout(timer) };
}

function dedupeSources(list) {
  if (!Array.isArray(list)) return [];
  const best = new Map();
  for (const s of list) {
    if (!s || typeof s.source !== "string") continue;
    const score = Number.isFinite(Number(s.score)) ? Number(s.score) : null;
    const key = `${s.source}#${s.page}`;
    if (!best.has(key) || (score ?? -1) > (best.get(key).score ?? -1)) best.set(key, { source: s.source, page: s.page, score });
  }
  return [...best.values()].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
}

function buildSources(sources) {
  const foot = h("footer", "sources");
  const list = h("ul", "source-list");
  for (const s of sources) {
    const item = h("li", "source");
    item.title = s.source;

    const badge = h("span", "source-icon");
    badge.append(icon("doc"));

    const name = h("span", "source-name", docTitle(s.source));
    name.dir = "ltr";
    const meta = h("span", "source-meta");
    const page = h("span", "source-page");
    page.append(label("span", "", "pageShort"), ` ${s.page ?? "–"}`);
    meta.append(page);
    if (s.score !== null) {
      const bar = h("span", "score");
      bar.setAttribute("aria-hidden", "true");
      const fill = h("span");
      fill.style.setProperty("--v", Math.max(0, Math.min(1, s.score)));
      bar.append(fill);
      meta.append(bar, label("span", "sr-only", "relevance"), h("span", "score-num", s.score.toFixed(2)));
    }

    const body = h("span", "source-body");
    body.append(name, meta);
    item.append(badge, body);
    list.append(item);
  }
  foot.append(label("h3", "sources-label", "sources"), list);
  return foot;
}

function copyButton(text) {
  const btn = h("button", "btn-copy");
  btn.type = "button";
  const text_ = label("span", "", "copy");
  btn.append(icon("copy"), text_);
  btn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      return;
    }
    text_.dataset.i18n = "copied";
    text_.textContent = t("copied");
    btn.classList.add("is-done");
    setTimeout(() => {
      text_.dataset.i18n = "copy";
      text_.textContent = t("copy");
      btn.classList.remove("is-done");
    }, 1600);
  });
  return btn;
}

function buildAnswer(data) {
  // Defensive: some Qwen builds emit an empty reasoning block even with reasoning disabled.
  const answer = data.answer.replace(/<think>[\s\S]*?<\/think>/gi, "").trim();
  const { msg, card, head } = assistantShell();
  const body = h("div", "answer");
  body.dir = textDir(answer);
  body.append(renderMarkdown(answer, { tableLabel: t("tableLabel") }));
  card.append(body);
  const sources = dedupeSources(data.sources);
  if (sources.length) card.append(buildSources(sources));
  if (navigator.clipboard) head.append(copyButton(answer));
  return msg;
}

function buildError(key, question) {
  const { msg, card } = assistantShell("is-error");
  const text = h("p", "error-text");
  text.append(icon("alert"), label("span", "", key));
  const retry = h("button", "btn-retry");
  retry.type = "button";
  retry.append(icon("retry"), label("span", "", "retry"));
  retry.addEventListener("click", () => {
    msg.remove();
    ui.input.focus();
    ask(question, { retry: true });
  });
  card.append(text, retry);
  return msg;
}

// ---------- behaviour ----------

function setPending(ctrl) {
  state.pending = ctrl;
  updateSend();
  for (const btn of ui.suggestions.querySelectorAll("button")) btn.disabled = !!ctrl;
}

function updateSend() {
  ui.send.disabled = !!state.pending || !ui.input.value.trim();
}

function autosize() {
  ui.input.style.height = "auto";
  ui.input.style.height = `${Math.min(ui.input.scrollHeight, 180)}px`;
}

async function ask(question, { retry = false } = {}) {
  question = question.trim();
  if (!question || state.pending) return;

  ui.welcome.hidden = true;
  if (!retry) addUserMessage(question);
  const loading = addLoading();
  scrollToEnd();

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort("timeout"), TIMEOUT_MS);
  setPending(ctrl);

  let result;
  try {
    const res = await fetch(API.chat, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ question, session_id: state.sessionId }),
      signal: ctrl.signal,
    });
    const data = await res.json().catch(() => null);
    if (ctrl.signal.aborted) throw ctrl.signal.reason;
    if (!res.ok) {
      throw new ChatError(res.status === 422 ? "errInvalid" : res.status >= 502 ? "errUnavailable" : "errServer");
    }
    if (!data || typeof data.answer !== "string") throw new ChatError("errBadResponse");
    if (typeof data.session_id === "string") state.sessionId = data.session_id;
    result = buildAnswer(data);
  } catch (err) {
    if (ctrl.signal.aborted && ctrl.signal.reason !== "timeout") return; // cancelled by New chat
    result = buildError(err instanceof ChatError ? err.key : ctrl.signal.aborted ? "errTimeout" : "errNetwork", question);
  } finally {
    clearTimeout(timer);
    loading.stop();
    if (state.pending === ctrl) setPending(null);
  }

  loading.node.replaceWith(result);
  renderSession();
  // Long answers: show their start rather than their end.
  if (result.offsetHeight > ui.scroller.clientHeight * 0.8) result.scrollIntoView({ block: "start", behavior: behavior() });
  else scrollToEnd();
}

function newChat() {
  state.pending?.abort("reset");
  setPending(null);
  state.sessionId = null;
  ui.messages.replaceChildren();
  ui.welcome.hidden = false;
  renderSuggestions();
  renderSession();
  ui.scroller.scrollTo({ top: 0 });
  ui.input.focus();
}

async function loadHealth() {
  try {
    const res = await fetch(API.health, { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error(String(res.status));
    const data = await res.json();
    state.docs = Array.isArray(data.documents) ? data.documents : [];
  } catch {
    state.docs = false;
  }
  renderDocs();
  renderStatus();
}

ui.form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = ui.input.value;
  if (!question.trim() || state.pending) return;
  ui.input.value = "";
  autosize();
  updateSend();
  ask(question);
});

ui.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    ui.form.requestSubmit();
  }
});

ui.input.addEventListener("input", () => {
  autosize();
  updateSend();
});

ui.newChat.addEventListener("click", newChat);

ui.lang.addEventListener("click", () => {
  state.lang = state.lang === "ar" ? "en" : "ar";
  try {
    localStorage.setItem("lang", state.lang);
  } catch {}
  applyLang();
});

applyLang();
loadHealth();
