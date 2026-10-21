// Нормализация блока «Проверочные вопросы».
//
// Курсы сгенерированы в разное время и хранят вопросы по-разному. Здесь всё
// приводится к одному виду { question, answer, options, explanation }:
//   1. пара            {question: "текст", answer: "текст"} или ["текст", "текст"];
//   2. цепочка полей   ["question", "…"], ["options", "…"], ["answer", "B"], ["explanation", "…"];
//   3. запись с типом  {question: "multiple_choice", answer: "вопрос + варианты + **Ответ:** …"}.
// Перед показом запись проверяется: нужен текст вопроса и ответ. Пустые записи,
// заглушки ("answer", "question", "TODO") и вопросы без ответа не показываются,
// о каждой пишется ошибка в консоль с id урока.

const PLACEHOLDERS = new Set(["question", "answer", "options", "todo", "tbd", "вопрос", "ответ"]);

// Название поля в цепочке -> каноническое имя.
const FIELD_ALIASES = {
  question: "question",
  options: "options",
  answer_options: "options",
  choices: "options",
  answer: "answer",
  correct_answer: "answer",
  correct: "answer",
  right_answer: "answer",
  explanation: "explanation",
  rationale: "explanation",
  feedback: "explanation",
  type: "type",
  question_type: "type",
};

const TYPE_TAGS = new Set([
  "multipart", "multiple_choice", "multiple-choice", "multiple", "multiple_select",
  "single", "single_choice", "single-choice", "true_false", "true-false", "matching",
  "case_scenario", "short_answer", "numeric", "detailed_answer", "quiz_question",
]);

const OPTION_LINE = /^(?:[A-Za-zА-Яа-я]|\d{1,2})[).]\s/u;
const OPTION_KEY = /^(?:[A-Za-zА-Яа-я]|\d{1,2})$/u;
const OPTIONS_LABEL = /^[*_\s]*(?:варианты(?:\s+ответов?)?|options)[*_\s]*:?[*_\s]*$/iu;
const ANSWER_WORDS = "(?:правильный\\s+ответ|верный\\s+ответ|ответ|correct\\s+answer|answer)";
// Подпись ответа в начале строки; markdown вокруг допускается: «**Ответ:** c) …».
const ANSWER_MARKER = new RegExp(`^[*_\\s]*${ANSWER_WORDS}[*_\\s]*[:：—–-][*_\\s]*`, "iu");
// Та же подпись в середине текста (только с двоеточием, чтобы не ловить слово «ответ» в прозе).
const INLINE_ANSWER_MARKER = new RegExp(`(?:^|\\n|[ \\t])[*_]*${ANSWER_WORDS}[*_]*\\s*[:：][*_\\s]*`, "giu");

const EXPLANATION_MARKER = /(?:^|\n)[*_\s]*(?:пояснени[ея]|объяснени[ея]|explanation|rationale)[*_\s]*[:：][*_\s]*/iu;
const CORRECT_INDEX = /[*_]*correct[_ ]index[*_]*\s*[:：]\s*[*_]*(\d{1,2})/iu;

const TRUE_FALSE = { true: "Верно", false: "Неверно" };

// «B + Пояснение: …» -> { answer: "B", explanation: "…" }.
const splitExplanation = (text) => {
  // «…|correct|Пояснение: …» — служебную метку между ответом и пояснением убираем.
  const value = String(text ?? "").replace(/\s*\|\s*(?:correct|incorrect|wrong)\s*\|\s*/giu, "\n");
  const match = EXPLANATION_MARKER.exec(value);
  if (!match) return { answer: value.trim(), explanation: "" };
  return {
    answer: value.slice(0, match.index).trim(),
    explanation: value.slice(match.index + match[0].length).trim(),
  };
};

// Мусор генерации: длинные хвосты из повторяющихся символов (например сотни «*️⃣»),
// одиночные галочки и непарные звёздочки в конце. Такой хвост не несёт смысла,
// не переносится по словам и растягивает блок за пределы карточки.
const cleanQuizNoise = (value) => {
  let text = String(value ?? "")
    .replace(/[\u200B-\u200D\uFEFF]/g, "")
    .replace(/(?:[*#0-9]\uFE0F?\u20E3)+/g, " ")
    .replace(/([^\p{L}\p{N}\s]{1,4}?)\1{5,}/gu, "$1")
    .replace(/[\s*]*[\u2705\u2714\u2611]\uFE0F?[\s*]*$/u, "")
    .replace(/\\+$/gm, "")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
  if ((text.match(/\*\*/g) || []).length % 2 === 1) {
    const last = text.lastIndexOf("**");
    text = `${text.slice(0, last)}${text.slice(last + 2)}`.trim();
  }
  return text.replace(/(?<!\*)\*$/, "").trim();
};

const quizText = (value) => {
  if (Array.isArray(value)) value = value.map(quizText).filter(Boolean).join("\n");
  if (value && typeof value === "object") {
    value = value.text ?? value.value ?? value.content ?? value.parts ?? "";
    if (Array.isArray(value)) value = value.map(quizText).filter(Boolean).join("\n");
  }
  if (typeof value === "number") value = String(value);
  const text = typeof value === "string" ? cleanQuizNoise(value) : "";
  const key = text.toLowerCase();
  return PLACEHOLDERS.has(key) || TYPE_TAGS.has(key) ? "" : text;
};

const unwrapQuizRecord = (value) => {
  let record = value;
  while (true) {
    if (record && typeof record === "object" && !Array.isArray(record)) {
      const wrapper = [...TYPE_TAGS].find((tag) => tag in record);
      if (wrapper) {
        record = record[wrapper];
        continue;
      }
      if (TYPE_TAGS.has(String(record.type).toLowerCase())) {
        const payload = record.value ?? record.data ?? record.content ?? record.parts;
        if (payload !== undefined) {
          record = payload;
          continue;
        }
      }
    }
    return record;
  }
};

const normalizeQuizOptions = (value) => {
  if (Array.isArray(value)) return value.map(quizText).filter(Boolean);
  if (typeof value === "string") return value.split(/\r?\n/).map(quizText).filter(Boolean);
  return [];
};

// Забирает варианты ответа с конца списка строк: «A) …», «b. …», «1) …».
const takeTrailingOptions = (lines) => {
  const rest = [...lines];
  const options = [];
  while (rest.length && OPTION_LINE.test(rest[rest.length - 1])) options.unshift(rest.pop());
  if (options.length < 2) return { rest: lines, options: [] };
  while (rest.length && OPTIONS_LABEL.test(rest[rest.length - 1])) rest.pop();
  return { rest, options };
};

// Запись, где всё лежит одним текстом: «вопрос … варианты … **Ответ:** …».
const parseStandaloneBody = (body) => {
  const text = cleanQuizNoise(quizText(body) || "");
  const markers = [...text.matchAll(INLINE_ANSWER_MARKER)];
  const marker = markers[markers.length - 1];
  const head = marker ? text.slice(0, marker.index) : text;
  const answer = marker ? text.slice(marker.index + marker[0].length).trim() : "";
  const lines = head.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const { rest, options } = takeTrailingOptions(lines);
  return { question: rest.join("\n"), options, answer, explanation: "" };
};

// Поле ответа иногда содержит варианты вместе с ответом или вместо него:
//   «a) …\nb) …\nc) …\nОтвет: c) …»  -> варианты отдельно, ответ отдельно;
//   «A) …; B) …; C) …» без ответа       -> только варианты (ответа нет).
// Возвращает { options, answer } или null, если это обычный текст ответа.
const splitOptionsFromAnswer = (rawAnswer) => {
  const text = String(rawAnswer ?? "");
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  let optionCount = 0;
  while (optionCount < lines.length && OPTION_LINE.test(lines[optionCount])) optionCount += 1;

  if (optionCount >= 2) {
    const options = lines.slice(0, optionCount);
    // После вариантов может идти «Ответ: …», «correct_index: 1», «explanation: …» либо мусор.
    const tail = lines.slice(optionCount).join("\n");
    const { answer: tailAnswer, explanation } = splitExplanation(tail);
    const indexMatch = CORRECT_INDEX.exec(tailAnswer);
    let answer = "";
    if (ANSWER_MARKER.test(tailAnswer)) answer = tailAnswer;
    else if (indexMatch) answer = options[Number(indexMatch[1])] ?? "";
    return { options, answer, explanation };
  }

  const inline = text
    .split(/;\s*(?=(?:[A-Za-zА-Яа-я]|\d{1,2})[).]\s)/u)
    .map((part) => part.trim())
    .filter(Boolean);
  if (inline.length >= 3 && inline.every((part) => OPTION_LINE.test(part))) {
    return { options: inline, answer: "", explanation: "" };
  }

  return null;
};

// Короткий ответ («B», «2», «true») превращаем в понятный текст.
const resolveAnswer = (rawAnswer, options) => {
  const answer = String(rawAnswer ?? "").replace(ANSWER_MARKER, "").trim();
  const token = answer.replace(/[.)\s]+$/u, "");
  if (token.toLowerCase() in TRUE_FALSE) return TRUE_FALSE[token.toLowerCase()];
  if (!options.length || !OPTION_KEY.test(token)) return answer;

  const lowered = token.toLowerCase();
  const byLabel = options.find((option) => {
    const start = option.toLowerCase();
    return start.startsWith(`${lowered})`) || start.startsWith(`${lowered}.`);
  });
  if (byLabel) return byLabel;
  const index = Number.parseInt(token, 10);
  return Number.isInteger(index) && options[index] ? options[index] : answer;
};

// Приводит запись к паре [ключ, значение], если она так устроена.
const asPair = (entry) => {
  if (Array.isArray(entry) && entry.length === 2) return entry;
  if (
    entry && typeof entry === "object" && !Array.isArray(entry) &&
    typeof entry.question === "string" && "answer" in entry &&
    !("options" in entry) && !("choices" in entry)
  ) {
    return [entry.question, entry.answer];
  }
  return null;
};

export const normalizeQuizQuestions = (block, lessonId) => {
  const raw = Array.isArray(block?.questions) ? block.questions : [];
  const valid = [];
  let pending = null;

  // Единая проверка перед показом: нужен текст вопроса и ответ (или пояснение).
  const pushQuestion = (candidate, index) => {
    let options = candidate.options || [];
    let answer = candidate.answer;
    let explanation = quizText(candidate.explanation);
    const split = options.length ? null : splitOptionsFromAnswer(answer);
    if (split) {
      options = split.options;
      answer = split.answer;
      explanation = explanation || quizText(split.explanation);
    }
    const parts = splitExplanation(answer);
    answer = resolveAnswer(parts.answer, options);
    explanation = explanation || quizText(parts.explanation);
    const question = quizText(candidate.question);
    if (question && (answer || explanation)) {
      valid.push({ question, answer, options, explanation });
    } else {
      console.error("Некорректная запись Quiz: нет вопроса или ответа", { lessonId, index });
    }
  };

  const commitPending = (index) => {
    if (!pending) return;
    const options = [...normalizeQuizOptions(pending.options), ...pending.labelledOptions];
    pushQuestion(
      { question: pending.question, answer: quizText(pending.answer), options, explanation: pending.explanation },
      index,
    );
    pending = null;
  };

  raw.forEach((entry, index) => {
    const record = unwrapQuizRecord(entry);
    const pair = asPair(record);
    const key = pair && typeof pair[0] === "string" ? pair[0].trim().toLowerCase() : null;
    const field = key ? FIELD_ALIASES[key] : null;

    // 2. Цепочка «поле — значение».
    if (field === "question") {
      commitPending(index - 1);
      pending = { question: quizText(pair[1]), options: "", labelledOptions: [], answer: "", explanation: "" };
      if (!pending.question) {
        console.error("Некорректная запись Quiz: пустой вопрос", { lessonId, index });
        pending = null;
      }
      return;
    }
    if (field === "type") return;
    if (field) {
      if (pending) pending[field] = pair[1];
      return;
    }
    // Вариант ответа отдельной записью: ["B", "текст варианта"].
    if (pending && key && OPTION_KEY.test(key) && typeof pair[1] === "string") {
      pending.labelledOptions.push(`${pair[0].trim()}) ${quizText(pair[1])}`);
      return;
    }

    commitPending(index - 1);

    // 3. Запись с типом: весь вопрос лежит в значении одним текстом.
    if (key && TYPE_TAGS.has(key)) {
      pushQuestion(parseStandaloneBody(pair[1]), index);
      return;
    }

    // 1. Обычная пара или объект с отдельными полями.
    if (pair) {
      pushQuestion({ question: pair[0], answer: quizText(pair[1]), options: [], explanation: "" }, index);
      return;
    }
    const answerValue = unwrapQuizRecord(record?.answer ?? record?.correct_answer ?? record?.expected_answer);
    const options = normalizeQuizOptions(record?.options ?? record?.choices ?? answerValue?.options);
    const answer = typeof answerValue === "number"
      ? options[answerValue] ?? String(answerValue)
      : quizText(
          typeof answerValue === "string"
            ? answerValue
            : answerValue?.answer ?? answerValue?.correct_answer ?? answerValue?.expected_answer ?? answerValue?.text ?? answerValue?.value,
        );
    pushQuestion(
      {
        question: record?.question ?? record?.text ?? record?.prompt,
        answer,
        options,
        explanation: record?.explanation ?? record?.rationale ?? answerValue?.explanation ?? answerValue?.rationale,
      },
      index,
    );
  });
  commitPending(raw.length - 1);
  return valid;
};
