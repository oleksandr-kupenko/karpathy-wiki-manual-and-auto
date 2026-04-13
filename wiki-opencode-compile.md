# Wiki Compile via OpenCode — Проблема

**Дата:** 2026-04-13
**Статус:** Не решён — используем ручной запуск

## Проблема

`compile.py` использует Claude Agent SDK для создания вики-страниц, но он дорогой (~$2/компиляция) и имеет rate limits.

## Что пробовали

### 1. OpenCode run (не работает)

Команда:
```bash
/home/san/.opencode/bin/opencode run "ingest" --dir <vault> --dangerously-skip-permissions
```

**Проблемы:**
1. opencode запускается интерактивно — ждёт ввода пользователя
2. Не выходит автоматически после выполнения
3. Требует подтверждения пермишенов (без `--dangerously-skip-permissions`)
4. В headless режиме зависает, ожидая ответов

**Вывод:** `opencode run` не подходит для автоматизации через Python.

### 2. ACP Server

```bash
opencode acp --port 4096 --dir <vault>
```

Не тестировали до конца — процесс не запустился в фоне.

### 3. DeepSeek API

Технически работает, но:
- DeepSeek — простой LLM, не агент
- Не умеет создавать файлы через tools
- Требует парсинга вывода в Python
- Сложнее в реализации

## Решение — РАБОТАЕТ

Создал `COMPILE_INSTRUCTIONS.md` с полными инструкциями и добавил их в промпт compile.py.

Теперь `compile.py` автоматически:
1. Читает COMPILE_INSTRUCTIONS.md
2. Читает wiki-schema.md и index.md
3. Обрабатывает daily/ файлы
4. Создаёт wiki страницы
5. Обновляет index.md и log.md

## Конфигурация

- `compile-config.json`: `{"provider": "opencode"}`
- `flush-config.json`: `{"flush_provider": "deepseek"}`

## Как работает

```bash
cd /home/san/Desktop/PROJECTS/WIKI/youtube-summary/compiler/scripts
uv run python compile.py
```

Или автоматически через flush.py после 18:00.

## Конфигурация

- `compile-config.json`: `{"provider": "opencode"}`
- `flush-config.json`: `{"flush_provider": "deepseek"}` (для суммаризации)

## Что можно попробовать потом

1. ACP server + Python HTTP client
2. DeepSeek + парсинг вывода
3. Claude Code API (но дорого)