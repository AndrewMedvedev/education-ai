## Установка утилиты `make`

```bash
sudo apt update && sudo apt install make
```

## Запуск последнего бекапа

```bash
make restore
```

## Запуск конкретного бекапа

```bash
make restore RESTORE_TIMESTAMP=20260505_020000
```

Бекапы создаются в 2:00 ночи
