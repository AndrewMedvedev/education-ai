// Страница генерации курса с интерактивным чатом
import SectionTop from "../components/SectionTop";
import CreatorChatView from "../components/CreatorChatView";

export default function CreatorPage() {
  return (
    <section className="container section creator-view" id="creator-tab">
      <SectionTop label="Создание" title="Создание курса" />
      <CreatorChatView />
    </section>
  );
}
