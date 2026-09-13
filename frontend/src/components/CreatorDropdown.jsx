// Выпадающий селект для формы создания курса в режиме генерации
import { useEffect, useRef } from "react";

export default function CreatorDropdown({
  label,
  value,
  options,
  isOpen,
  onToggle,
  onSelect,
  menuDirection = "down",
}) {
  const dropdownRef = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handleOutsideClick = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        onToggle(false);
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [isOpen, onToggle]);

  return (
    <div className="creator-field creator-dropdown" ref={dropdownRef}>
      <span>{label}</span>
      <button
        type="button"
        className={`creator-select-btn ${isOpen ? "is-open" : ""}`}
        onClick={() => onToggle(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span>{value}</span>
        <span className="creator-select-caret" aria-hidden="true" />
      </button>
      {isOpen && (
        <div
          className={`creator-select-menu ${menuDirection === "up" ? "is-up" : ""}`}
          role="listbox"
          aria-label={label}
        >
          {options.map((option) => (
            <button
              key={option}
              type="button"
              className={`creator-select-option ${option === value ? "is-active" : ""}`}
              onClick={() => {
                onSelect(option);
                onToggle(false);
              }}
            >
              {option}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
