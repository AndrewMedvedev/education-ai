import { useSessionStore } from "../stores/sessionStore";
import { reloadScope } from "./reloadPersistence";
import { useReloadStorageErrors } from "./reloadScope";

export default function ReloadStorageWarning({ names }) {
  const scope = useSessionStore(reloadScope);
  const failed = useReloadStorageErrors((state) =>
    Object.values(state.errors).some((item) => item.scope === scope &&
      names.some((name) => item.name.startsWith(name))),
  );
  return failed ? (
    <p role="alert" className="dnd-inline-error reload-storage-warning">
      Не удалось прочитать или сохранить локальный черновик: хранилище браузера
      недоступно или переполнено. Текущие правки остаются в памяти, но могут
      потеряться после перезагрузки. Освободите место или разрешите хранение данных
      и повторите изменение.
    </p>
  ) : null;
}
