import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { useLessonPracticeRequest } from "../hooks/useLessonPracticeRequest";

const PASSING_SCORE = 61;

function createAnswersPayload(questions, answers, testType) {
  return Object.fromEntries(
    questions.map((question, index) => {
      const answer = answers[index];
      const value =
        testType === "multiple_choice"
          ? (question.options?.[Number(answer)] ?? String(answer ?? ""))
          : String(answer ?? "").trim();
      return [question.id || question.text || String(index + 1), value];
    }),
  );
}

function ResultCard({
  result,
  passingScore = PASSING_SCORE,
  onViewed,
  onDone,
  isFinishing,
}) {
  const card = useRef(null);
  useEffect(() => {
    if (!result || !onViewed || !card.current) return;
    let acknowledged = false;
    const acknowledge = () => {
      const bounds = card.current?.getBoundingClientRect();
      if (
        !acknowledged &&
        document.visibilityState === "visible" &&
        bounds &&
        bounds.bottom > 0 &&
        bounds.top < window.innerHeight
      ) {
        acknowledged = true;
        onViewed();
      }
    };
    const observer = new IntersectionObserver(acknowledge);
    observer.observe(card.current);
    document.addEventListener("visibilitychange", acknowledge);
    acknowledge();
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", acknowledge);
    };
  }, [result, onViewed]);
  if (!result) return null;
  const passed = Number(result.score) >= passingScore;
  return (
    <article
      ref={card}
      className={`lesson-agent-result ${passed ? "is-passed" : "is-failed"}`}
    >
      <div>
        <span>Результат</span>
        <strong>{Number(result.score) || 0} баллов</strong>
      </div>
      <p>{passed ? "Пройдено" : "Не пройдено"}</p>
      {result.ai_feedback && (
        <div className="lesson-agent-feedback">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {result.ai_feedback}
          </ReactMarkdown>
        </div>
      )}
      {onDone && (
        <div className="lesson-agent-actions">
          <button
            type="button"
            className="btn btn-solid"
            onClick={onDone}
            disabled={isFinishing}
          >
            {isFinishing
              ? "Завершаем просмотр..."
              : "Завершить просмотр результата"}
          </button>
        </div>
      )}
    </article>
  );
}

function isWildcardExtensions(extensions) {
  return (
    !Array.isArray(extensions) ||
    extensions.length === 0 ||
    extensions.includes("*")
  );
}

function normalizeExtension(value) {
  const extension = String(value || "")
    .trim()
    .toLowerCase();
  return extension.startsWith(".") ? extension : `.${extension}`;
}

function normalizeAssignmentText(value) {
  return String(value || "")
    .replace(/\\n/g, "\n")
    .replace(/\n\s*[-•]\s*/g, "\n- ")
    .trim();
}

export function LessonTestAgent({ moduleId, lessonId, onChecked }) {
  const {
    assignment: test,
    practiceId,
    answers,
    setAnswers,
    isLoading,
    isChecking,
    isRestoring,
    error,
    result,
    generate: startTest,
    check,
    markViewed,
    finish,
  } = useLessonPracticeRequest(moduleId, lessonId, "test");

  const questions = Array.isArray(test?.questions) ? test.questions : [];
  const isSubmitted = Boolean(result);
  const isPassed = Number(result?.score) >= PASSING_SCORE;
  const canSubmit =
    questions.length > 0 &&
    questions.every((_, index) => {
      const answer = answers[index];
      return answer !== undefined && String(answer).trim().length > 0;
    });

  const submitTest = async () => {
    if (!test || !practiceId || !canSubmit || isChecking || isSubmitted) return;
    const payload = {
      practice: test,
      answers: createAnswersPayload(questions, answers, test?.test_type),
    };

    const response = await check(payload);
    if (response) onChecked?.(response);
  };

  if (!test) {
    return (
      <section className="lesson-agent-panel lesson-agent-start">
        <div className="lesson-agent-head">
          <p className="course-category">Проверочные вопросы</p>
          <h2>Проверка знаний</h2>
          <span>
            {isLoading
              ? "Запрос уже отправлен. Можно обновлять страницу — вопросы появятся здесь автоматически."
              : isRestoring
                ? "Восстанавливаем сохранённое состояние теста…"
                : "Когда будете готовы, запустите генерацию тестовых вопросов."}
          </span>
        </div>
        {error && (
          <p className="lesson-ai-error" role="alert">
            {error}
          </p>
        )}
        <div className="lesson-agent-actions">
          <button
            type="button"
            className="btn btn-solid"
            onClick={startTest}
            disabled={isLoading || isRestoring || !moduleId || !lessonId}
          >
            {isRestoring
              ? "Восстанавливаем тест..."
              : isLoading
                ? "Готовим вопросы..."
                : "Пройти тест"}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="lesson-agent-panel">
      <div className="lesson-agent-head">
        <p className="course-category">Проверочные вопросы</p>
        <h2>{test?.title || "Проверка знаний"}</h2>
        {test?.estimated_time_minutes && (
          <span>Ориентировочное время: {test.estimated_time_minutes} мин.</span>
        )}
      </div>

      {error && (
        <p className="lesson-ai-error" role="alert">
          {error}
        </p>
      )}

      <div className="lesson-agent-question-list">
        {questions.map((question, index) => (
          <article
            className="lesson-agent-question"
            key={`${question.text}-${index}`}
          >
            <div className="lesson-agent-question-title">
              <span>{index + 1}</span>
              <h3>{question.text}</h3>
              {question.points && <small>{question.points} балл.</small>}
            </div>

            {test?.test_type === "multiple_choice" ? (
              <div className="lesson-agent-options">
                {(Array.isArray(question.options) ? question.options : []).map(
                  (option, optionIndex) => (
                    <label key={`${option}-${optionIndex}`}>
                      <input
                        type="radio"
                        name={`lesson-test-${lessonId}-${index}`}
                        value={optionIndex}
                        disabled={isSubmitted || isChecking}
                        checked={
                          String(answers[index] ?? "") === String(optionIndex)
                        }
                        onChange={() =>
                          setAnswers((prev) => ({
                            ...prev,
                            [index]: optionIndex,
                          }))
                        }
                      />
                      <span>{option}</span>
                    </label>
                  ),
                )}
              </div>
            ) : (
              <div className="lesson-agent-detailed-answer">
                {question.hint && (
                  <details>
                    <summary>Подсказка</summary>
                    <p>{question.hint}</p>
                  </details>
                )}
                <textarea
                  value={answers[index] || ""}
                  disabled={isSubmitted || isChecking}
                  onChange={(event) =>
                    setAnswers((prev) => ({
                      ...prev,
                      [index]: event.target.value,
                    }))
                  }
                  placeholder="Введите развёрнутый ответ"
                />
              </div>
            )}
          </article>
        ))}
      </div>

      <div className="lesson-agent-actions">
        <button
          type="button"
          className="btn btn-solid"
          onClick={submitTest}
          disabled={!practiceId || !canSubmit || isChecking || isSubmitted}
        >
          {isChecking
            ? "Проверяем..."
            : isSubmitted
              ? isPassed
                ? "Тест сдан"
                : "Тест не сдан"
              : "Завершить тест"}
        </button>
      </div>

      <ResultCard
        result={result}
        onViewed={markViewed}
        onDone={finish}
        isFinishing={isRestoring}
      />
    </section>
  );
}

export function LessonPracticeAgent({ moduleId, lessonId, onChecked }) {
  const {
    assignment,
    practiceId,
    result,
    error,
    isLoading,
    isChecking,
    isRestoring,
    generate,
    check,
    markViewed,
    finish,
  } = useLessonPracticeRequest(moduleId, lessonId);
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState("");

  const startPractice = async () => {
    setFile(null);
    setFileError("");
    await generate();
  };

  const allowedExtensions = useMemo(
    () =>
      Array.isArray(assignment?.allowed_extensions)
        ? assignment.allowed_extensions
        : [],
    [assignment?.allowed_extensions],
  );
  const acceptsAnyFile = isWildcardExtensions(allowedExtensions);
  const accept = acceptsAnyFile
    ? undefined
    : allowedExtensions.map(normalizeExtension).join(",");

  const pickFile = (event) => {
    const nextFile = event.target.files?.[0] || null;
    setFile(null);
    setFileError("");
    if (!nextFile) return;

    if (!acceptsAnyFile) {
      const fileName = (nextFile.name || "").toLowerCase();
      const isAllowed = allowedExtensions
        .map(normalizeExtension)
        .some((extension) => fileName.endsWith(extension));
      if (!isAllowed) {
        setFileError(
          `Недопустимый тип файла. Разрешены: ${allowedExtensions.join(", ")}.`,
        );
        event.target.value = "";
        return;
      }
    }
    setFile(nextFile);
  };

  const submitPractice = async () => {
    if (!file || !practiceId || fileError || isChecking || result) return;
    const response = await check(file);
    if (response) onChecked?.(response);
  };

  if (!assignment) {
    return (
      <section className="lesson-agent-panel lesson-agent-start">
        <div className="lesson-agent-head">
          <p className="course-category">Практика</p>
          <h2>Практическое задание</h2>
          <span>
            {isLoading
              ? "Запрос уже отправлен. Можно обновлять страницу — результат появится здесь автоматически."
              : isRestoring
                ? "Восстанавливаем сохранённое состояние практики…"
                : "Когда будете готовы, запустите подготовку практического задания."}
          </span>
        </div>
        {error && (
          <p className="lesson-ai-error" role="alert">
            {error}
          </p>
        )}
        <div className="lesson-agent-actions">
          <button
            type="button"
            className="btn btn-solid"
            onClick={startPractice}
            disabled={isLoading || isRestoring || !moduleId || !lessonId}
          >
            {isRestoring
              ? "Восстанавливаем практику..."
              : isLoading
                ? "Готовим задание..."
                : "Выполнить практическое задание"}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="lesson-agent-panel">
      <div className="lesson-agent-head">
        <p className="course-category">Практика</p>
        <h2>{assignment?.title || "Практическое задание"}</h2>
      </div>

      {error && (
        <p className="lesson-ai-error" role="alert">
          {error}
        </p>
      )}

      {assignment?.description && (
        <div className="lesson-markdown lesson-agent-description">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {normalizeAssignmentText(assignment.description)}
          </ReactMarkdown>
        </div>
      )}

      {Array.isArray(assignment?.evaluation_criteria) &&
        assignment.evaluation_criteria.length > 0 && (
          <div className="lesson-agent-meta-card">
            <h3>Критерии оценки</h3>
            <ul>
              {assignment.evaluation_criteria.map((item) => (
                <li key={item}>{normalizeAssignmentText(item)}</li>
              ))}
            </ul>
          </div>
        )}

      <div className="lesson-agent-meta-grid">
        <div>
          <span>Проходной балл</span>
          <strong>{assignment?.passing_score ?? PASSING_SCORE}</strong>
        </div>
        <div>
          <span>Форматы</span>
          <strong>
            {acceptsAnyFile ? "Любой файл" : allowedExtensions.join(", ")}
          </strong>
        </div>
      </div>

      {assignment?.submission_instructions && (
        <div className="lesson-markdown lesson-agent-instructions">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {normalizeAssignmentText(assignment.submission_instructions)}
          </ReactMarkdown>
        </div>
      )}

      <label className="lesson-agent-file-picker">
        <span>Файл решения</span>
        <input
          type="file"
          accept={accept}
          disabled={isChecking || Boolean(result)}
          onChange={pickFile}
        />
        {file && <strong>{file.name}</strong>}
      </label>
      {fileError && (
        <p className="lesson-ai-error" role="alert">
          {fileError}
        </p>
      )}

      <div className="lesson-agent-actions">
        <button
          type="button"
          className="btn btn-solid"
          onClick={submitPractice}
          disabled={
            !practiceId ||
            !file ||
            Boolean(fileError) ||
            isChecking ||
            Boolean(result)
          }
        >
          {isChecking
            ? "Отправляем..."
            : result
              ? "Отправлено"
              : "Отправить на проверку"}
        </button>
      </div>

      <ResultCard
        result={result}
        passingScore={assignment?.passing_score ?? PASSING_SCORE}
        onViewed={markViewed}
        onDone={async () => {
          await finish();
          setFile(null);
          setFileError("");
        }}
        isFinishing={isRestoring}
      />
    </section>
  );
}
