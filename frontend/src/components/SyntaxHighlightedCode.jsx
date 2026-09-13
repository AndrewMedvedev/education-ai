import { Fragment } from "react";

const languageAliases = {
  py: "python",
  python3: "python",
  js: "javascript",
  jsx: "javascript",
  ts: "typescript",
  tsx: "typescript",
  cplusplus: "cpp",
  "c++": "cpp",
  cs: "csharp",
  "c#": "csharp",
  "1c": "bsl",
  oscript: "bsl",
};

const keywords = new Set(
  [
    "and", "as", "assert", "async", "await", "break", "case", "catch", "class",
    "const", "continue", "def", "default", "delete", "do", "else", "elif",
    "enum", "except", "export", "extends", "finally", "for", "foreach", "from",
    "function", "goto", "if", "implements", "import", "in", "instanceof",
    "interface", "is", "lambda", "let", "namespace", "new", "of", "package",
    "pass", "private", "protected", "public", "raise", "readonly", "return",
    "sizeof", "static", "struct", "super", "switch", "throw", "throws", "try",
    "typedef", "typeof", "using", "var", "virtual", "volatile", "while",
    "with", "yield", "select", "insert", "update", "create", "drop", "alter",
    "where", "join", "inner", "left", "right", "group", "order", "having",
    "limit", "values", "into", "table", "database", "procedure",
    "если", "тогда", "иначе", "иначеесли", "конецесли", "для", "каждого",
    "из", "цикл", "конеццикла", "пока", "процедура", "конецпроцедуры",
    "функция", "конецфункции", "возврат", "попытка", "исключение",
    "конецпопытки", "вызватьисключение", "перем", "экспорт", "новый",
    "знач", "выполнить", "продолжить", "прервать",
  ].map((word) => word.toLowerCase()),
);

const types = new Set(
  [
    "bool", "boolean", "byte", "char", "date", "datetime", "decimal", "dict",
    "double", "dynamic", "float", "int", "integer", "list", "long", "map",
    "number", "object", "set", "short", "string", "tuple", "unsigned",
    "array", "promise", "record", "variant", "void", "строка", "число", "дата",
    "булево", "массив", "структура", "соответствие", "таблицазначений",
  ].map((word) => word.toLowerCase()),
);

const literals = new Set(
  [
    "true", "false", "null", "none", "undefined", "nan", "inf", "истина",
    "ложь", "неопределено", "null",
  ].map((word) => word.toLowerCase()),
);

const builtins = new Set(
  [
    "print", "len", "range", "open", "input", "sum", "min", "max", "map",
    "filter", "zip", "enumerate", "console", "document", "window", "json",
    "printf", "scanf", "malloc", "free", "sizeof", "std", "vector", "cout",
    "cin", "сообщить", "предупреждение", "вопрос", "формат", "стрдлина",
    "лев", "прав", "сред", "текущаядата", "типзнч", "заполнитьзначениясвойств",
  ].map((word) => word.toLowerCase()),
);

const tokenPattern =
  /\/\*[\s\S]*?\*\/|\/\/[^\n]*|#[^\n]*|"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*'|`(?:\\[\s\S]|[^`\\])*`|@[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё0-9_]*|\b(?:0x[\da-f]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b|[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё0-9_]*|[+\-*/%=&|!<>^~?:]+|[{}[\]();,.]/gi;

export function getCodeLanguage(className = "") {
  const match = /(?:^|\s)language-([^\s]+)/i.exec(className);
  const rawLanguage = match?.[1]?.toLowerCase() || "";
  return languageAliases[rawLanguage] || rawLanguage;
}

function getTokenKind(token, source, index, language) {
  if (token.startsWith("/*") || token.startsWith("//")) {
    return "comment";
  }
  if (token.startsWith("#")) {
    return ["c", "cpp", "csharp", "java"].includes(language)
      ? "preprocessor"
      : "comment";
  }
  if (/^["'`]/.test(token)) {
    return "string";
  }
  if (token.startsWith("@")) {
    return "decorator";
  }
  if (/^(?:0x[\da-f]+|\d)/i.test(token)) {
    return "number";
  }
  if (/^[+\-*/%=&|!<>^~?:]+$/.test(token)) {
    return "operator";
  }
  if (/^[{}[\]()]$/.test(token)) {
    return "bracket";
  }
  if (/^[;,.]$/.test(token)) {
    return "punctuation";
  }

  const normalized = token.toLowerCase();
  if (keywords.has(normalized)) {
    return "keyword";
  }
  if (types.has(normalized)) {
    return "type";
  }
  if (literals.has(normalized)) {
    return "literal";
  }
  if (builtins.has(normalized)) {
    return "builtin";
  }
  const previousWord = /([A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё0-9_]*)\s*$/.exec(
    source.slice(0, index),
  )?.[1]?.toLowerCase();
  if (["class", "interface", "struct", "enum"].includes(previousWord)) {
    return "class";
  }
  if (/\.\s*$/.test(source.slice(0, index))) {
    return "property";
  }
  if (/^\s*\(/.test(source.slice(index + token.length))) {
    return "function";
  }
  if (/^[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё0-9_]*$/.test(token)) {
    return "class";
  }
  return "";
}

function highlight(source, language) {
  const parts = [];
  let cursor = 0;
  let match;

  tokenPattern.lastIndex = 0;
  while ((match = tokenPattern.exec(source)) !== null) {
    if (match.index > cursor) {
      parts.push(source.slice(cursor, match.index));
    }

    const token = match[0];
    const kind = getTokenKind(token, source, match.index, language);
    parts.push(
      kind ? (
        <span key={`${match.index}-${kind}`} className={`syntax-${kind}`}>
          {token}
        </span>
      ) : (
        <Fragment key={`${match.index}-plain`}>{token}</Fragment>
      ),
    );
    cursor = match.index + token.length;
  }

  if (cursor < source.length) {
    parts.push(source.slice(cursor));
  }
  return parts;
}

export default function SyntaxHighlightedCode({
  className = "",
  children,
  node: _node,
  ...props
}) {
  const language = getCodeLanguage(className);
  const source = String(children).replace(/\n$/, "");

  if (!language) {
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  }

  return (
    <code
      className={`${className} syntax-highlighted-code`}
      data-language={language}
      {...props}
    >
      {highlight(source, language)}
    </code>
  );
}
