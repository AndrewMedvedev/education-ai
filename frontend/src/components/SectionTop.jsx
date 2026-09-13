// Повторяемый заголовок секции с номером и заголовком
export default function SectionTop({ label, title }) {
  return (
    <div className="section-top">
      <span>{label}</span>
      <h2>{title}</h2>
    </div>
  );
}
