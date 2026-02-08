// Настройте под себя:
const TG_HANDLE = "your_handle"; // без @, например: sellerpravo

const offers = {
  fine: {
    badge: "Ситуация",
    title: "Штраф или претензия площадки",
    deliverable: "Готовый ответ или претензию под регламент площадки и ведение электронных переговоров до результата или понятного “упора”.",
    docs: [
      "уведомление о штрафе или претензии (скрин или письмо)",
      "карточка товара и история изменений",
      "переписка с поддержкой",
      "документы по поставке и качеству (если есть)"
    ],
    eta: "обычно 1–3 рабочих дня до первого документа",
    price: "от 12 000 ₽"
  },
  returns: {
    badge: "Ситуация",
    title: "Удержания, возвраты, необоснованные списания",
    deliverable: "Претензия и позиция по удержаниям, электронные переговоры, подготовка пакета для возврата денег или зачёта.",
    docs: [
      "отчёты по удержаниям и детализация списаний",
      "доказательства отгрузки и приемки (УПД, накладные)",
      "переписка и решения по обращениям",
      "скрины личного кабинета по спорным операциям"
    ],
    eta: "обычно 2–5 рабочих дней до первого документа",
    price: "от 18 000 ₽"
  },
  card: {
    badge: "Ситуация",
    title: "Карточка товара, ТЗ, несоответствия, модерация",
    deliverable: "Позиция и документы под правила площадки: ответ на претензию, корректировка формулировок, фиксация доказательств и переписка до решения.",
    docs: [
      "ссылка на карточку и история изменений",
      "претензия или причина ограничения",
      "фото, маркировка, инструкции, состав, характеристики",
      "переписка с поддержкой"
    ],
    eta: "обычно 1–4 рабочих дня",
    price: "от 15 000 ₽"
  },
  block: {
    badge: "Ситуация",
    title: "Блокировка товара, кабинета или ограничение продаж",
    deliverable: "Позиция и пакет для разблокировки, электронные переговоры и фиксация нарушений процедуры со стороны площадки.",
    docs: [
      "уведомление о блокировке и основания (скрин, письмо)",
      "история обращений и ответы поддержки",
      "данные по товарам и спорным операциям",
      "документы по качеству и происхождению (если есть)"
    ],
    eta: "обычно 1–3 рабочих дня до первого пакета",
    price: "от 20 000 ₽"
  },
  ip: {
    badge: "Ситуация",
    title: "Интеллектуальные права: фото, бренд, контент",
    deliverable: "Ответ на претензию, переговоры, подготовка доказательств законности использования, при необходимости претензионный и судебный блок.",
    docs: [
      "претензия правообладателя или уведомление площадки",
      "материалы карточки (фото, текст, бренд, упаковка)",
      "договоры, лицензии, подтверждения происхождения",
      "переписка с поддержкой и решения по жалобам"
    ],
    eta: "обычно 2–6 рабочих дней",
    price: "от 25 000 ₽"
  },
  court: {
    badge: "Уровень",
    title: "Суд: иск или защита по уже поданному иску",
    deliverable: "Иск или возражения, процессуальная логика и доказательства. Если спор можно закрыть переговорами, предложим сначала этот маршрут.",
    docs: [
      "иск или претензии и приложенные материалы (если есть)",
      "договоры, документы по поставке и оплатам",
      "переписка, отчёты, скрины кабинета",
      "цель по результату (деньги, восстановление, отмена штрафа)"
    ],
    eta: "срок зависит от объёма материалов; первый план работ в течение 1–2 дней",
    price: "от 55 000 ₽"
  }
};

const els = {
  chips: document.getElementById("chips"),
  offerBadge: document.getElementById("offerBadge"),
  offerTitle: document.getElementById("offerTitle"),
  offerDeliverable: document.getElementById("offerDeliverable"),
  offerDocs: document.getElementById("offerDocs"),
  offerETA: document.getElementById("offerETA"),
  offerPrice: document.getElementById("offerPrice"),
  intake: document.getElementById("intake"),
  topic: document.getElementById("topic")
};

function renderOffer(key){
  const o = offers[key] || offers.fine;

  els.offerBadge.textContent = o.badge;
  els.offerTitle.textContent = o.title;
  els.offerDeliverable.textContent = o.deliverable;
  els.offerETA.textContent = o.eta;
  els.offerPrice.textContent = o.price;

  els.offerDocs.innerHTML = "";
  o.docs.forEach(t => {
    const li = document.createElement("li");
    li.textContent = t;
    els.offerDocs.appendChild(li);
  });

  if (els.topic && els.topic.value !== key) els.topic.value = key;
}

function setActiveChip(btn){
  [...els.chips.querySelectorAll(".chip")].forEach(b => b.classList.remove("is-active"));
  btn.classList.add("is-active");
}

els.chips.addEventListener("click", (e) => {
  const btn = e.target.closest(".chip");
  if (!btn) return;
  const key = btn.dataset.key;
  setActiveChip(btn);
  renderOffer(key);
});

els.topic.addEventListener("change", () => {
  const key = els.topic.value;
  const btn = els.chips.querySelector(`.chip[data-key="${key}"]`);
  if (btn) setActiveChip(btn);
  renderOffer(key);
});

function openTelegram(text){
  const url = "https://t.me/" + TG_HANDLE + "?text=" + encodeURIComponent(text);
  window.open(url, "_blank", "noopener,noreferrer");
}

els.intake.addEventListener("submit", (e) => {
  e.preventDefault();

  const name = document.getElementById("name").value.trim();
  const contact = document.getElementById("contactField").value.trim();
  const marketplace = document.getElementById("marketplace").value.trim();
  const topicKey = document.getElementById("topic").value;
  const desc = document.getElementById("desc").value.trim();

  const o = offers[topicKey] || offers.fine;

  const msg =
`Селлер.Право — запрос

Имя: ${name || "—"}
Контакт: ${contact || "—"}
Площадка: ${marketplace || "—"}
Ситуация: ${o.title}

Описание:
${desc || "—"}

Если удобно, пришлю скрины и документы ссылками.`;

  openTelegram(msg);
});

renderOffer("fine");
