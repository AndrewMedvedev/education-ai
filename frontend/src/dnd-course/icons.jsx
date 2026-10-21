// Единый набор контурных иконок 24×24 (stroke), чтобы не тянуть иконочную библиотеку.
const PATHS = {
  upload: "M12 16V4m0 0-4 4m4-4 4 4M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2",
  file: "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Zm0 0v5h5",
  lesson: "M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5v-15ZM4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5",
  module: "m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5",
  course: "M3 9.5 12 5l9 4.5-9 4.5-9-4.5Zm3 2v5c0 1.5 2.7 3 6 3s6-1.5 6-3v-5",
  plus: "M12 5v14M5 12h14",
  trash: "M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13",
  sparkles: "M12 3v4m0 10v4M3 12h4m10 0h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6",
  eye: "M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
  settings: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7.4-3a7.4 7.4 0 0 0-.1-1.2l2-1.6-2-3.4-2.4 1a7.6 7.6 0 0 0-2-1.2L14.5 3h-5l-.4 2.6a7.6 7.6 0 0 0-2 1.2l-2.4-1-2 3.4 2 1.6a7.4 7.4 0 0 0 0 2.4l-2 1.6 2 3.4 2.4-1a7.6 7.6 0 0 0 2 1.2l.4 2.6h5l.4-2.6a7.6 7.6 0 0 0 2-1.2l2.4 1 2-3.4-2-1.6c.1-.4.1-.8.1-1.2Z",
  check: "m5 12.5 4.5 4.5L19 7.5",
  alert: "M12 9v4m0 3.5v.01M10.3 4.2 2.6 17.5A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0Z",
  info: "M12 11v5m0-8.5v.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  arrowUp: "M12 19V5m0 0-6 6m6-6 6 6",
  arrowDown: "M12 5v14m0 0 6-6m-6 6-6-6",
  arrowRight: "M5 12h14m0 0-6-6m6 6-6 6",
  arrowLeft: "M19 12H5m0 0 6 6m-6-6 6-6",
  close: "M6 6l12 12M18 6 6 18",
  help: "M9.1 9a3 3 0 1 1 4.2 2.7c-.8.4-1.3 1.1-1.3 2v.3m0 3.5v.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  fit: "M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5",
  target: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-5a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm0-3.5v-1",
  more: "M5 12h.01M12 12h.01M19 12h.01",
  list: "M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01",
  canvas: "M4 4h6v6H4V4Zm10 10h6v6h-6v-6ZM10 7h4a3 3 0 0 1 3 3v4",
  retry: "M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7",
  zoomIn: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm9 3-4-4M11 8v6M8 11h6",
  zoomOut: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm9 3-4-4M8 11h6",
  panel: "M4 4h16v16H4V4Zm5 0v16",
  panelRight: "M4 4h16v16H4V4Zm11 0v16",
  flag: "M5 21V4m0 0h11l-2 4 2 4H5",
  edit: "M4 20h4L19 9l-4-4L4 16v4Zm10-14 4 4",
  link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
  restart: "M3 12a9 9 0 1 0 3-6.7M3 4v5h5",
  clock: "M12 7v5l3 2m6-2a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  grip: "M9 6h.01M15 6h.01M9 12h.01M15 12h.01M9 18h.01M15 18h.01",
  chevronDown: "m6 9 6 6 6-6",
  maximize: "M8 3H3v5M21 8V3h-5M3 16v5h5M16 21h5v-5",
  minimize: "M3 8h5V3M16 3v5h5M8 21v-5H3M21 16h-5v5",
};

export default function Icon({ name, size = 18, className = "", title }) {
  const path = PATHS[name];
  if (!path) return null;
  return (
    <svg
      className={`dnd-icon ${name === "spinner" ? "is-spinning" : ""} ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={title ? undefined : "true"}
      role={title ? "img" : undefined}
      focusable="false"
    >
      {title ? <title>{title}</title> : null}
      <path d={path} />
    </svg>
  );
}

export function Spinner({ size = 16, label }) {
  return (
    <span className="dnd-spinner" style={{ width: size, height: size }} role={label ? "status" : undefined}>
      {label ? <span className="dnd-visually-hidden">{label}</span> : null}
    </span>
  );
}
