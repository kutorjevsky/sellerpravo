// script.js
(() => {
  const problems = [
    {
      key: "penalty",
      label: "Штраф от маркетплейса",
      note: "Когда площадка списала деньги или выставила претензию: мы проверяем регламент, доказательства и собираем позицию так, чтобы она пережила поддержку и суд."
    },
    {
      key: "holds",
      label: "Неправильные удержания и взаиморасчеты",
      note: "Если цифры не сходятся: разбираем отчёты, сверяем основания удержаний, готовим претензию и переговорную рамку."
    },
    {
      key: "tm",
      label: "Товарные знаки и контент",
      note: "Если прилетела претензия правообладателя или блокировка контента: оцениваем риски, делаем ответ и, при необходимости, переговоры с правообладателем."
    },
    {
      key: "blocks",
      label: "Блокировка кабинета и карточек",
      note: "Если заблокировали карточки или кабинет: фиксируем нарушение, формируем пакет обращений и позицию для восстановления доступа."
    },
    {
      key: "loss",
      label: "Утеря и утилизация товара",
      note: "Если товар потеряли или утилизировали: собираем доказательства, считаем ущерб, выстраиваем претензию и дальнейшую тактику."
    },
    {
      key: "damages",
      label: "Убытки по вине маркетплейса",
      note: "Когда из-за действий площадки возникли потери: формируем доказательственную конструкцию и считаем убытки так, чтобы это не выглядело фантазией."
    },
    {
      key: "logistics",
      label: "Проблемы с логистикой",
      note: "Срывы сроков, неисполнение, повреждение: квалификация ситуации, претензия, расчёты, подготовка к суду при необходимости."
    }
  ];

  const packages = {
    pretrial_now: (problemKey) => {
      const base = [
        {
          name: "Пакет «Досудебка»",
          price: "6 000 – 10 000 ₽",
          includes: [
            "правовой анализ ситуации",
            "подготовка претензии или ответа на уведомление",
            "подготовка претензии",
            "устная консультация"
          ],
          meta: "Подходит, когда нужно быстро зафиксировать позицию и начать движение."
        },
        {
          name: "Пакет «Переговоры»",
          price: "10 000 – 15 000 ₽",
          includes: [
            "правовой анализ ситуации",
            "подготовка претензии или ответа на уведомление",
            "подготовка претензии",
            "устная консультация",
            "переговоры по электронной почте"
          ],
          meta: "Подходит, когда без переписки и контроля ответов всё развалится."
        }
      ];

      if (problemKey === "tm") {
        base.unshift({
          name: "Пакет «Товарный знак»",
          price: "15 000 – 20 000 ₽",
          includes: [
            "правовой анализ",
            "подготовка претензии или ответа на уведомление",
            "подготовка претензии",
            "устная консультация с правообладателем",
            "устные и личные переговоры с правообладателем"
          ],
          meta: "Подходит для ситуаций с правообладателем, где важны формулировки и тон переговоров."
        });
      }

      return base;
    },

    pretrial_next: () => ([
      {
        name: "Пакет «Документы для суда»",
        price: "15 000 – 25 000 ₽",
        includes: [
          "подготовка иска или возражений"
        ],
        meta: "Если договориться не получится или если на вас подали в суд."
      },
      {
        name: "Пакет «Упрощенка»",
        price: "25 000 – 35 000 ₽",
        includes: [
          "сопровождение упрощённого производства",
          "составление процессуальных документов"
        ],
        meta: "Если дело в упрощённом порядке и важно не проиграть его «по переписке»."
      },
      {
        name: "Пакет «Суд»",
        price: "45 000 – 70 000 ₽",
        includes: [
          "участие в суде первой инстанции"
        ],
        meta: "Если нужна очная защита и контроль процессуальной динамики."
      },
      {
        name: "Пакет «Иск + суд»",
        price: "50 000 – 80 000 ₽",
        includes: [
          "подготовка иска",
          "участие в суде первой инстанции"
        ],
        meta: "Нормальный вариант, когда нужен комплект, а не разрозненные действия."
      },
      {
        name: "Пакет «Досудебка + упрощенка»",
        price: "30 000 – 40 000 ₽",
        includes: [
          "досудебная работа",
          "сопровождение упрощённого производства"
        ],
        meta: "Если вы хотите сначала попробовать досудебно, но держать суд в фокусе."
      },
      {
        name: "Пакет «Досудебка + весь суд»",
        price: "60 000 – 90 000 ₽",
        includes: [
          "досудебная работа",
          "ведение дела в суде первой инстанции",
          "подготовка процессуальных документов по ходу дела"
        ],
        meta: "Если спор потенциально «длинный» и вы хотите одну линию защиты."
      },
      {
        name: "Пакет «Максимум»",
        price: "100 000 – 150 000 ₽",
        includes: [
          "досудебная работа",
          "ведение дела во всех трёх инстанциях"
        ],
        meta: "Если вы заранее понимаете, что вопрос принципиальный и будет тяжёлым."
      }
    ]),

    in_court: () => ([
      {
        name: "Пакет «Документы для суда»",
        price: "15 000 – 25 000 ₽",
        includes: [
          "подготовка иска или возражений"
        ],
        meta: "Если сейчас горит именно документ: иск, отзыв, возражения, пояснения."
      },
      {
        name: "Пакет «Упрощенка»",
        price: "25 000 – 35 000 ₽",
        includes: [
          "сопровождение упрощённого производства",
          "составление процессуальных документов"
        ],
        meta: "Если суд идёт в упрощённом порядке и нельзя пропускать сроки."
      },
      {
        name: "Пакет «Суд»",
        price: "45 000 – 70 000 ₽",
        includes: [
          "участие в суде первой инстанции"
        ],
        meta: "Если нужна процессуальная защита и управление ходом заседаний."
      },
      {
        name: "Пакет «Иск + суд»",
        price: "50 000 – 80 000 ₽",
        includes: [
          "подготовка иска",
          "участие в суде первой инстанции"
        ],
        meta: "Если вы ещё можете повлиять на конструкцию дела и её подачу."
      }
    ]),

    post_judgment: () => ([
      {
        name: "Пакет «Обжалование»",
        price: "30 000 – 40 000 ₽",
        includes: [
          "участие в суде апелляционной и кассационной инстанции"
        ],
        meta: "Если вы не согласны с решением и хотите нормальную правовую атаку, а не крик души на 40 страниц."
      }
    ])
  };

  const els = {
    chips: Array.from(document.querySelectorAll(".chip")),
    planBtn: document.getElementById("planBtn"),
    stageBlock: document.getElementById("stageBlock"),
    stageBtns: Array.from(document.querySelectorAll(".stageBtn")),
    specTitle: document.getElementById("specTitle"),
    specNote: document.getElementById("specNote"),
    specBody: document.getElementById("specBody")
  };

  const state = {
    problem: "penalty",
    planOpened: false,
    stage: null
  };

  function getProblem() {
    return problems.find(p => p.key === state.problem) || problems[0];
  }

  function setActiveChip() {
    els.chips.forEach(btn => {
      btn.classList.toggle("is-active", btn.dataset.problem === state.problem);
    });
  }

  function setActiveStage() {
    els.stageBtns.forEach(btn => {
      const isActive = btn.dataset.stage === state.stage;
      btn.classList.toggle("is-active", isActive);
      btn.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  }

  function renderSpec() {
    const p = getProblem();

    els.specTitle.textContent = p.label;

    if (!state.planOpened) {
      els.specNote.textContent = "Выберите проблему, нажмите «Получить план», затем укажите стадию. Справа появятся подходящие пакеты с составом работ и диапазоном цены.";
      els.specBody.innerHTML = `
        <div class="hint">
          <div class="hint__title">Что будет дальше</div>
          <div class="hint__text">
            Мы предложим конкретный пакет работ. Внутри пакета будет понятный артефакт: текст претензии или ответа, пакет приложений,
            рамка переписки и, если нужно, процессуальные документы.
          </div>
        </div>
      `;
      return;
    }

    if (!state.stage) {
      els.specNote.textContent = p.note;
      els.specBody.innerHTML = `
        <div class="hint">
          <div class="hint__title">Шаг 2</div>
          <div class="hint__text">
            Вы уже выбрали проблему. Теперь выберите стадию: досудебная работа, дело в суде или обжалование решения.
            После выбора мы покажем подходящие пакеты и ориентир стоимости.
          </div>
        </div>
      `;
      return;
    }

    let html = "";
    els.specNote.textContent = p.note;

    if (state.stage === "pretrial") {
      const now = packages.pretrial_now(state.problem);
      const next = packages.pretrial_next();

      html += `<div class="pkgGroupTitle">Подходит сейчас</div>`;
      html += `<div class="pkgs">${now.map(renderPkg).join("")}</div>`;

      html += `
        <details class="pkgDetails">
          <summary>Если дойдёт до суда, вот варианты</summary>
          <div class="pkgs" style="margin-top:10px;">
            ${next.map(renderPkg).join("")}
          </div>
        </details>
      `;
    }

    if (state.stage === "in_court") {
      const list = packages.in_court();
      html += `<div class="pkgGroupTitle">Пакеты для суда</div>`;
      html += `<div class="pkgs">${list.map(renderPkg).join("")}</div>`;
    }

    if (state.stage === "post_judgment") {
      const list = packages.post_judgment();
      html += `<div class="pkgGroupTitle">Пакет для обжалования</div>`;
      html += `<div class="pkgs">${list.map(renderPkg).join("")}</div>`;
    }

    els.specBody.innerHTML = html;
  }

  function renderPkg(p) {
    const items = (p.includes || []).map(i => `<li>${escapeHtml(i)}</li>`).join("");
    const meta = p.meta ? `<div class="pkg__meta">${escapeHtml(p.meta)}</div>` : "";
    return `
      <article class="pkg" aria-label="${escapeAttr(p.name)}">
        <div class="pkg__head">
          <div class="pkg__name">${escapeHtml(p.name)}</div>
          <div class="pkg__price">${escapeHtml(p.price)}</div>
        </div>
        <ul class="pkg__list">
          ${items}
        </ul>
        ${meta}
      </article>
    `;
  }

  function openPlan() {
    state.planOpened = true;
    els.stageBlock.classList.add("is-visible");
    renderSpec();

    // лёгкий скролл в пределах блока, чтобы человек заметил новый вопрос
    els.stageBlock.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function escapeAttr(str) {
    return escapeHtml(str).replaceAll("\n", " ");
  }

  // Events
  els.chips.forEach(btn => {
    btn.addEventListener("click", () => {
      state.problem = btn.dataset.problem;
      setActiveChip();
      renderSpec();
    });
  });

  els.planBtn.addEventListener("click", openPlan);

  els.stageBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      state.stage = btn.dataset.stage;
      setActiveStage();
      renderSpec();
    });
  });

  // Initial render
  setActiveChip();
  setActiveStage();
  renderSpec();
})();
