# docs-agent — Техническое задание

**Дата:** 2026-05-14  
**Статус:** Draft

---

## 1. Цель

Инструмент `docs-agent` — Python CLI-пакет для автоматического создания и поддержки документации (README, wiki) в каждом репозитории проекта. Агент анализирует изменения в коде и обновляет только те части документации, которых коснулся diff. При первом запуске — генерирует документацию с нуля.

---

## 2. Область применения

- Работает **внутри каждого репо независимо** — устанавливается как dev-зависимость
- Подходит для Python (pyproject.toml), Node.js (package.json), PHP (composer.json) проектов
- Поддерживает монорепо и отдельные репозитории
- Не зависит от конкретного git-хостинга (GitHub, GitLab, Gitea)

---

## 3. Команды CLI

### `docs-agent install`
Bootstraps репо: создаёт конфиг, добавляет Makefile-таргеты, добавляет CI workflow.

```
docs-agent install          # интерактивный режим (2-3 вопроса)
docs-agent install --auto   # полностью автоматический режим
```

**Автодетект в `--auto`:**
- Язык/фреймворк: наличие `pyproject.toml` / `package.json` / `composer.json`
- CI система: наличие `.github/workflows/` или `.gitlab-ci.yml`
- Git remote URL: для регистрации в реестре
- Название сервиса: из `pyproject.toml[tool.poetry.name]` или `package.json[name]`

**Создаёт:**
- `.docs-agent/docs-agent.yml` — конфиг с разумными дефолтами
- Таргеты в `Makefile`: `docs`, `docs-sync`, `docs-check`
- CI workflow файл: `.github/workflows/docs.yml` или блок в `.gitlab-ci.yml`

---

### `docs-agent init`
Первый запуск — генерирует документацию с нуля.

- Сканирует репо: структуру каталогов, код, зависимости, существующие доки
- Если документ уже существует — актуализирует его по шаблону (не перезаписывает MANUAL-секции)
- Если документа нет — создаёт с нуля, заполняет все AUTO-секции полностью
- Регистрирует репо в центральном реестре (`registry.yml`)
- Ставит маркер `.docs-agent/.initialized`

---

### `docs-agent run`
Инкрементальное обновление — основной режим CI.

- Если маркер `.docs-agent/.initialized` отсутствует — автоматически вызывает `init` и завершается
- Определяет diff: `git diff HEAD~1..HEAD` локально; в CI использует env `DOCS_AGENT_BASE_SHA` если задан (полезно для PR: `github.event.pull_request.base.sha`), иначе `HEAD~1`
- Фильтрует по `triggers.paths` из конфига
- Если нет релевантных изменений — выходит с `exit 0`
- Для каждого затронутого документа:
  - Определяет, какие AUTO-секции нужно обновить исходя из diff
  - Отправляет в LLM: `[diff] + [текущий документ] + [секция шаблона]`
  - Получает обновлённый текст секции
  - Патчит файл — заменяет содержимое между маркерами
- Применяет output-режим (direct commit или PR)

---

### `docs-agent sync`
Принудительная актуализация по шаблону.

- Прогоняет все документы из конфига через LLM независимо от diff
- Используется после: обновления шаблона, добавления нового документа в конфиг, ручного запуска `make docs-sync`
- Не трогает MANUAL-секции

---

### `docs-agent dashboard`
Выводит таблицу в терминал.

```
PROJECT                    STATUS     LAST UPDATED   DOCUMENTS
ai-platform-core           ✓ synced   2026-05-14     README.md, architecture.md
ai-platform-knowledge      ✓ synced   2026-05-13     README.md, api-contracts.md
marketplace-backend        ✗ stale    2026-04-28     README.md
```

---

### `docs-agent report`
Генерирует статичный HTML-файл `docs-agent-report.html`.

- Таблица всех зарегистрированных проектов со статусами
- Ссылки на документы
- Дата последнего обновления каждого документа
- Никакого сервера — просто открыть в браузере или опубликовать как GitHub Pages

---

## 4. Конфигурация репо (`.docs-agent/docs-agent.yml`)

```yaml
provider:
  type: claude              # claude | openai | ollama
  model: claude-sonnet-4-6
  api_key_env: ANTHROPIC_API_KEY
  # base_url: http://localhost:11434  # для ollama

output:
  mode: pr                  # direct | pr
  pr_title: "docs: auto-update documentation"
  branch_prefix: docs/auto-

templates:
  source: builtin           # builtin | local
  # local_path: .docs-agent/templates  # если source: local

triggers:
  paths:
    - "app/**"
    - "src/**"
    - "pyproject.toml"
    - "package.json"
  ignore:
    - "tests/**"
    - "**/*.md"

documents:
  - type: readme
    template: readme/default
    target: README.md

  - type: wiki
    template: wiki/architecture
    target: ../my-service.wiki/architecture.md

  - type: wiki
    template: wiki/api-contracts
    target: ../my-service.wiki/api-contracts.md

registry:
  path: ../.docs-agent/registry.yml   # путь к центральному реестру
```

---

## 5. Провайдеры LLM

Абстракция через базовый класс `LLMProvider`. Все провайдеры реализуют единый интерфейс:

```python
class LLMProvider:
    async def complete(self, system: str, user: str) -> str: ...
```

| Провайдер | Конфиг `type` | SDK |
|-----------|--------------|-----|
| Anthropic Claude | `claude` | `anthropic` |
| OpenAI | `openai` | `openai` |
| Ollama (локальный) | `ollama` | `httpx` → REST API |

API-ключ читается из env-переменной, указанной в `api_key_env`.

---

## 6. Шаблоны документов

### Встроенные шаблоны (в пакете)

```
docs_agent/
└── built_in_templates/
    ├── readme/
    │   └── default.md.j2
    └── wiki/
        ├── architecture.md.j2
        ├── api-contracts.md.j2
        ├── development-guide.md.j2
        └── operations.md.j2
```

### Пользовательские шаблоны (в репо)

Если `templates.source: local` — агент берёт шаблоны из `.docs-agent/templates/` репо. Полезно для кастомного стиля или дополнительных секций.

### Маркеры секций

```markdown
<!-- AUTO:overview -->
Этот блок обновляется агентом автоматически.
<!-- /AUTO:overview -->

<!-- MANUAL -->
Этот блок никогда не трогается агентом.
<!-- /MANUAL -->
```

Содержимое без маркеров агент не трогает (backward compatibility со старой документацией).

**Поведение по режимам:**

| Режим | AUTO-секции | MANUAL-секции |
|-------|------------|--------------|
| `init` (нет файла) | Создаёт и заполняет полностью | Создаёт с placeholder-текстом |
| `init` (файл есть) | Актуализирует по шаблону | Не трогает |
| `run` | Обновляет только затронутые diff-ом | Не трогает |
| `sync` | Перепроверяет все | Не трогает |

---

## 7. Output-режимы

### `direct` — коммит напрямую
- Коммитит изменённые файлы в текущую ветку
- Сообщение коммита: `docs: auto-update [filename] via docs-agent`
- Требует push-доступа в CI (через `GITHUB_TOKEN` / `GITLAB_TOKEN`)

### `pr` — создание Pull Request
- Создаёт ветку `docs/auto-<short-hash>`
- Коммитит изменения в неё
- Открывает PR через GitHub/GitLab API
- В описании PR: список изменённых секций и краткое summary от LLM

---

## 8. Центральный реестр (`registry.yml`)

Хранится в главном репо (или любом указанном месте). Каждый проект пишет свою запись при `init`.

```yaml
projects:
  - name: ai-platform-knowledge
    path: ../ai-platform-knowledge
    remote: git@github.com:org/ai-platform-knowledge.git
    registered_at: "2026-05-14"
    last_updated: "2026-05-14"
    status: synced           # synced | stale | never
    documents:
      - target: README.md
        last_updated: "2026-05-14"
      - target: ../ai-platform-knowledge.wiki/architecture.md
        last_updated: "2026-05-14"
```

`status: stale` выставляется если `last_updated` старше порога (настраивается, дефолт 30 дней).

---

## 9. Makefile-таргеты (добавляются `install`)

```makefile
docs:        ## init если не инициализировано, иначе run (run сам детектирует)
	poetry run docs-agent run

docs-sync:   ## принудительно sync всех документов по шаблону
	poetry run docs-agent sync

docs-check:  ## dry-run: показать что изменится, не трогая файлы
	poetry run docs-agent run --dry-run
```

---

## 10. CI workflow (GitHub Actions)

```yaml
# .github/workflows/docs.yml
name: Update Documentation

on:
  push:
    branches: ["**"]
  pull_request:

jobs:
  docs:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2       # нужно для git diff HEAD~1
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install docs-agent
      - run: docs-agent run
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DOCS_AGENT_BASE_SHA: ${{ github.event.pull_request.base.sha || github.event.before }}
```

---

## 11. Структура пакета

```
docs-agent/
├── pyproject.toml
├── docs_agent/
│   ├── cli.py                  # Click CLI: install/init/run/sync/dashboard/report
│   ├── config.py               # Загрузка и валидация docs-agent.yml (Pydantic)
│   ├── analyzer.py             # git diff → список затронутых AUTO-секций
│   ├── renderer.py             # шаблон + данные → патч документа
│   ├── scaffolder.py           # install: автодетект + генерация файлов
│   ├── registry.py             # чтение/запись registry.yml
│   ├── providers/
│   │   ├── base.py
│   │   ├── claude.py
│   │   ├── openai.py
│   │   └── ollama.py
│   ├── outputs/
│   │   ├── direct.py
│   │   └── pull_request.py
│   ├── reporters/
│   │   ├── terminal.py         # dashboard
│   │   └── html.py             # report
│   └── built_in_templates/
│       ├── readme/
│       │   └── default.md.j2
│       └── wiki/
│           ├── architecture.md.j2
│           ├── api-contracts.md.j2
│           ├── development-guide.md.j2
│           └── operations.md.j2
└── tests/
    ├── test_analyzer.py
    ├── test_renderer.py
    ├── test_scaffolder.py
    ├── test_providers.py
    └── test_registry.py
```

---

## 12. Зависимости пакета

```toml
[tool.poetry.dependencies]
python = "^3.11"
click = "^8.1"
pydantic = "^2.0"
jinja2 = "^3.1"
httpx = "^0.27"
gitpython = "^3.1"
anthropic = "^0.28"
openai = "^1.30"
pyyaml = "^6.0"
rich = "^13.0"      # таблицы в терминале для dashboard
```

---

## 13. Out of scope (v1)

- Веб-интерфейс (dashboard только CLI + HTML)
- Поддержка не-Markdown форматов (AsciiDoc, RST)
- Генерация API-документации из кода (OpenAPI → docs)
- Мультиязычная документация
- Уведомления (Slack, email) о staleness
