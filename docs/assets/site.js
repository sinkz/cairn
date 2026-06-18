const state = {
  lang: localStorage.getItem("cairn-lang") || "en",
  benchmark: null,
};

const text = {
  en: {
    updated: "Updated",
    suite: "Deterministic search benchmark",
    benchmarkUnavailable: "Benchmark data could not be loaded.",
  },
  pt: {
    updated: "Atualizado",
    suite: "Benchmark determinístico de busca",
    benchmarkUnavailable: "Não foi possível carregar os dados de benchmark.",
  },
};

function activeLang() {
  return state.lang === "pt" ? "pt" : "en";
}

function setLanguage(lang) {
  state.lang = lang === "pt" ? "pt" : "en";
  localStorage.setItem("cairn-lang", state.lang);
  document.body.dataset.lang = state.lang;
  document.documentElement.lang = state.lang === "pt" ? "pt-BR" : "en";

  document.querySelectorAll("[data-set-lang]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.setLang === state.lang));
  });

  renderBenchmark();
}

function formatMetric(metric, lang) {
  const precision = Number(metric.precision || 0);
  if (metric.format === "percent") {
    return new Intl.NumberFormat(lang === "pt" ? "pt-BR" : "en-US", {
      style: "percent",
      minimumFractionDigits: precision,
      maximumFractionDigits: precision,
    }).format(metric.value);
  }

  if (metric.format === "integer") {
    return new Intl.NumberFormat(lang === "pt" ? "pt-BR" : "en-US", {
      maximumFractionDigits: 0,
    }).format(metric.value);
  }

  return new Intl.NumberFormat(lang === "pt" ? "pt-BR" : "en-US", {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  }).format(metric.value);
}

function renderBenchmark() {
  const lang = activeLang();
  const labels = text[lang];
  const data = state.benchmark;
  const cards = document.getElementById("benchmark-cards");

  if (!cards) return;

  if (!data) {
    return;
  }

  document.getElementById("benchmark-suite").textContent = labels.suite;
  document.getElementById("benchmark-current-label").textContent = data.current.label[lang];
  document.getElementById("benchmark-note").textContent = data.suite.notes[lang];
  document.getElementById("benchmark-command").textContent = data.suite.command;
  document.getElementById("benchmark-updated").textContent = `${labels.updated} ${data.updated_at}`;

  cards.replaceChildren(
    ...data.current.metrics.map((metric) => {
      const article = document.createElement("article");
      article.className = "metric-card";

      const label = document.createElement("span");
      label.textContent = metric.label[lang];

      const value = document.createElement("strong");
      value.textContent = formatMetric(metric, lang);

      const description = document.createElement("p");
      description.textContent = metric.description[lang];

      article.append(label, value, description);
      return article;
    }),
  );
}

async function loadBenchmark() {
  try {
    const response = await fetch("data/benchmarks.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.benchmark = await response.json();
    renderBenchmark();
  } catch (error) {
    const cards = document.getElementById("benchmark-cards");
    if (cards) {
      cards.replaceChildren();
      const article = document.createElement("article");
      article.className = "metric-card";
      const label = document.createElement("span");
      label.textContent = "Benchmark";
      const value = document.createElement("strong");
      value.textContent = "--";
      const description = document.createElement("p");
      description.textContent = text[activeLang()].benchmarkUnavailable;
      article.append(label, value, description);
      cards.append(article);
    }
  }
}

document.querySelectorAll("[data-set-lang]").forEach((button) => {
  button.addEventListener("click", () => setLanguage(button.dataset.setLang));
});

function activateTab(target) {
  document.querySelectorAll("[data-tab-target]").forEach((button) => {
    button.setAttribute("aria-selected", String(button.dataset.tabTarget === target));
  });

  document.querySelectorAll("[data-tab-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.tabPanel !== target;
  });
}

document.querySelectorAll("[data-tab-target]").forEach((button) => {
  button.addEventListener("click", () => activateTab(button.dataset.tabTarget));
});

const selectedTab = document.querySelector('[data-tab-target][aria-selected="true"]');
if (selectedTab) {
  activateTab(selectedTab.dataset.tabTarget);
}

setLanguage(state.lang);
loadBenchmark();
