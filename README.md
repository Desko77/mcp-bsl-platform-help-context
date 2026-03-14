# MCP BSL Platform Help Context

**MCP-сервер для доступа к документации API платформы 1С:Предприятие**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![MCP](https://img.shields.io/badge/MCP-Compatible-purple)

Python-порт [mcp-bsl-platform-context](https://github.com/alkoleft/mcp-bsl-platform-context) (Kotlin/Spring Boot).

---

## Возможности

- **Три режима поиска**: keyword (нечёткий), semantic (embeddings + Qdrant), hybrid (оба + RRF-слияние + reranker)
- **Детальная информация** о типах, методах, свойствах, конструкторах платформы 1С
- **Навигация по объектной модели** платформы
- **Документация по строгой типизации** BSL и рекомендации по стилю кода
- **Два источника данных**: прямое чтение HBK файлов или pre-exported JSON
- **Три транспорта**: STDIO (для Claude Desktop, Cursor), SSE и Streamable HTTP
- **Мультиверсионность**: автоматическое обнаружение версий платформы с выбором ближайшей
- **YAML-конфигурация** с поддержкой переменных окружения и CLI-аргументов
- **Двуязычность**: русские и английские имена API, поиск регистронезависимый

## MCP-инструменты

### Поиск и навигация по API

| Инструмент | Описание | Параметры |
|------------|----------|-----------|
| `search` | Поиск по API платформы 1С. Поддерживает keyword, semantic и hybrid режимы. Используйте термины 1С (русские или английские) для лучших результатов | `query` (строка поиска), `mode?` (keyword/semantic/hybrid), `type?` (method/property/type), `limit?` (1–50, по умолчанию 10) |
| `info` | Детальная информация о конкретном элементе API по точному имени | `name` (точное имя, например `НайтиПоСсылке`), `type` (method/property/type) |
| `get_member` | Получить информацию о методе или свойстве конкретного типа | `type_name` (имя типа), `member_name` (имя метода/свойства) |
| `get_members` | Полный список методов и свойств типа | `type_name` (имя типа, например `ТаблицаЗначений`) |
| `get_constructors` | Сигнатуры конструкторов для создания экземпляров типа | `type_name` (имя типа) |
| `get_platform_info` | Информация о текущей версии платформы и список доступных версий | — |

### Документация и стандарты кода

| Инструмент | Описание | Параметры |
|------------|----------|-----------|
| `get_coding_guideline` | Рекомендации по стилю кода BSL (1С:Предприятие) | — |
| `get_strict_typing_info` | Документация по строгой типизации BSL. Используйте `topic='topics'` для списка тем | `topic` (название темы или `topics`) |
| `search_strict_typing` | Текстовый поиск по документации строгой типизации с контекстом | `query` (поисковый запрос) |

## Режимы поиска

Инструмент `search` поддерживает три режима (параметр `mode`, по умолчанию из конфигурации):

| Режим | Движок | Описание |
|-------|--------|----------|
| `keyword` | `SimpleSearchEngine` | 4-стратегийный поиск: точное совпадение, префикс, составные имена, порядок слов |
| `semantic` | `SemanticSearchEngine` | Векторный поиск: embedding запроса → ANN в Qdrant → опциональный cross-encoder rerank |
| `hybrid` | `HybridSearchEngine` | Keyword + semantic параллельно → RRF-слияние (k=60) → rerank |

**RAG-пайплайн:** `DocumentBuilder` → `EmbeddingProvider` → Qdrant embedded → `Reranker`

**Модели по умолчанию:**
- Embedder: `ai-forever/ru-en-RoSBERTa`
- Reranker: `DiTy/cross-encoder-russian-msmarco`

**Провайдеры:** `local` (sentence-transformers) или `openai-compatible` (любой API в формате OpenAI)

## Установка

```bash
pip install -e .                # Базовая установка (keyword search)
pip install -e ".[dev]"         # + pytest для разработки
pip install -e ".[local]"       # + sentence-transformers, torch (semantic/hybrid search)
```

### Зависимости

- Python 3.10+
- fastmcp >= 2.0
- beautifulsoup4 >= 4.12
- lxml >= 5.0
- click >= 8.1
- PyYAML >= 6.0

## Конфигурация

### YAML-файл (рекомендуется)

Скопируйте `config.example.yml` в `config.yml` и настройте под своё окружение:

```bash
cp config.example.yml config.yml
mcp-bsl-context -c config.yml
```

**Приоритет конфигурации:** YAML < переменные окружения (`MCP_BSL_*`) < CLI-аргументы.

Основные секции: `server`, `platform`, `search`, `embeddings`, `reranker`, `storage`, `index`, `docs`.

### Параметры CLI

```
--config, -c               Путь к YAML-файлу конфигурации
--platform-path, -p        Путь к каталогу установки 1С
--platform-version         Предпочтительная версия платформы (e.g., 8.3.20)
--mode, -m                 Транспорт: stdio (по умолчанию), sse или streamable-http
--port                     Порт для HTTP-сервера (по умолчанию: 8080)
--data-source              Источник данных: hbk или json
--json-path                Путь к каталогу с JSON-файлами
--verbose, -v              Включить отладочное логирование
```

### Переменные окружения

| CLI-аргумент | Переменная окружения | По умолчанию |
|---|---|---|
| `--platform-path` | `MCP_BSL_PLATFORM_PATH` | (обязателен для hbk) |
| `--platform-version` | `MCP_BSL_PLATFORM_VERSION` | null (авто — последняя) |
| `--mode` | `MCP_BSL_MODE` | `stdio` |
| `--port` | `MCP_BSL_PORT` | `8080` |
| `--data-source` | `MCP_BSL_DATA_SOURCE` | `hbk` |
| `--json-path` | `MCP_BSL_JSON_PATH` | — |
| `--verbose` | `MCP_BSL_VERBOSE` | `false` |
| `--host` | `MCP_BSL_HOST` | `127.0.0.1` |
| — | `MCP_BSL_DOCS_STRICT_TYPES_PATH` | null (встроенный) |
| — | `MCP_BSL_DOCS_GUIDELINE_PATH` | null (встроенный) |

## Использование

### YAML-конфигурация (рекомендуется)

```bash
mcp-bsl-context -c config.yml                                  # Полная конфигурация из YAML
mcp-bsl-context -c config.yml -p /opt/1cv8/x86_64              # YAML + CLI override
```

### CLI-параметры

```bash
mcp-bsl-context -p /opt/1cv8/x86_64                            # Автоопределение последней версии
mcp-bsl-context -p /opt/1cv8/x86_64 --platform-version 8.3.20  # Ближайшая к 8.3.20
mcp-bsl-context -p /path -m streamable-http --port 8080         # Streamable HTTP транспорт
mcp-bsl-context -p /path --data-source json --json-path /path   # JSON источник
```

## Интеграция

### Claude Desktop

Добавьте в `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bsl-context": {
      "command": "python",
      "args": ["-m", "mcp_bsl_context", "-p", "/opt/1cv8/x86_64/8.3.25.1257"]
    }
  }
}
```

### Cursor IDE

Добавьте в `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "bsl-context": {
      "command": "python",
      "args": ["-m", "mcp_bsl_context", "-p", "C:\\Program Files\\1cv8\\8.3.25.1257"]
    }
  }
}
```

### Мультиверсионный режим

Укажите путь к родительскому каталогу, и сервер автоматически найдёт все установленные версии:

```bash
# Linux: /opt/1cv8/x86_64 содержит 8.3.22.2838/, 8.3.25.1257/, ...
mcp-bsl-context -p /opt/1cv8/x86_64

# Выбрать конкретную версию (будет найдена ближайшая доступная)
mcp-bsl-context -p /opt/1cv8/x86_64 --platform-version 8.3.20
```

### Streamable HTTP (рекомендуется для сетевого доступа)

[Streamable HTTP](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http) — актуальный HTTP-транспорт в спецификации MCP, заменяющий устаревший SSE. Основные отличия:

- **Единый эндпоинт** `/mcp` вместо двух (`/sse` + `/messages`) — проще настройка и проксирование
- **Stateless-режим** — каждый запрос самодостаточен, не требуется держать долгоживущее SSE-соединение
- **Лучше для production** — корректно работает за reverse proxy, load balancer, в Kubernetes

```bash
mcp-bsl-context -p /opt/1cv8/x86_64/8.3.25.1257 -m streamable-http --port 8080
```

Подключение клиента:

```json
{
  "mcpServers": {
    "bsl-context": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

> **Примечание:** SSE-режим (`-m sse`) по-прежнему поддерживается для обратной совместимости.

## Docker

### Docker Compose

В `docker-compose.yml` нужно указать путь к каталогу установки платформы 1С, в котором находится файл `shcntx_ru.hbk`.

```yaml
volumes:
  # Linux:
  - /opt/1cv8/x86_64/8.3.25.1257:/data/platform:ro
  # Windows (Docker Desktop):
  # - "C:/Program Files/1cv8/8.3.25.1257:/data/platform:ro"
```

```bash
docker compose up -d                   # CPU + API providers
docker compose --profile gpu up -d     # GPU + локальные модели
docker compose --profile json up -d    # JSON data source
```

### Ручная сборка

```bash
docker build -t mcp-bsl-context .

# HBK-данные
docker run -d \
  -v /opt/1cv8/x86_64/8.3.25.1257:/data/platform:ro \
  -p 8080:8080 \
  mcp-bsl-context

# JSON-данные
docker run -d \
  -e MCP_BSL_DATA_SOURCE=json \
  -v ./json-data:/data/json:ro \
  -p 8080:8080 \
  mcp-bsl-context
```

### Проверка здоровья

```bash
docker inspect --format='{{.State.Health.Status}}' mcp-bsl-context
```

## Архитектура

```
mcp_bsl_context/
├── config.py                  # AppConfig — YAML + env + CLI merge
├── domain/                    # Доменный слой (все dataclasses frozen)
│   ├── entities.py            # Definition, MethodDefinition, PropertyDefinition, PlatformTypeDefinition
│   ├── enums.py               # ApiType (METHOD, PROPERTY, TYPE, CONSTRUCTOR)
│   ├── exceptions.py          # Иерархия исключений
│   ├── value_objects.py       # SearchQuery, SearchOptions, PlatformVersion
│   ├── services.py            # ContextSearchService
│   └── docs_service.py        # DocsInfoService (строгая типизация, guideline)
│
├── infrastructure/
│   ├── hbk/                   # Парсер бинарного формата HBK
│   │   ├── container_reader.py     # Бинарный контейнер
│   │   ├── content_reader.py       # ZIP-распаковка, TOC + FileStorage
│   │   ├── context_reader.py       # Оркестратор чтения
│   │   ├── pages_visitor.py        # Visitor: обход дерева страниц
│   │   ├── toc/                    # TOC: токенизатор, парсер, дерево
│   │   └── parsers/                # HTML-парсеры страниц (BeautifulSoup)
│   │
│   ├── json_loader/           # Альтернативный источник: JSON
│   ├── search/                # Поисковые движки
│   │   ├── indexes.py         # HashIndex, StartWithIndex
│   │   ├── strategies.py      # 4 стратегии keyword-поиска
│   │   ├── engine.py          # SimpleSearchEngine (keyword)
│   │   ├── semantic_engine.py # SemanticSearchEngine (Qdrant + embeddings)
│   │   └── hybrid_engine.py   # HybridSearchEngine (RRF + rerank)
│   │
│   ├── embeddings/            # ML-модели
│   │   ├── provider.py        # EmbeddingProvider (local/API)
│   │   ├── reranker.py        # Reranker (cross-encoder, local/API)
│   │   └── document_builder.py # Entities → embeddable text + Qdrant payload
│   │
│   └── storage/               # Хранилище и репозиторий
│       ├── storage.py         # PlatformContextStorage (thread-safe, lazy)
│       ├── repository.py      # PlatformRepository (фасад)
│       ├── loader.py          # PlatformContextLoader
│       ├── mapper.py          # Маппинг сущностей
│       └── version_discovery.py # VersionDiscovery (мультиверсионность)
│
├── presentation/
│   └── formatter.py           # Markdown-форматтер для MCP-ответов
│
├── docinfo/                   # Встроенная документация
│   ├── strict-types.md        # Строгая типизация BSL
│   └── guideline.md           # Рекомендации по стилю кода
│
├── server.py                  # FastMCP сервер (9 инструментов)
└── __main__.py                # CLI (click) + YAML config
```

### Поисковый движок (keyword)

4 стратегии с приоритетами:

1. **CompoundTypeSearch** — составные имена типов ("Справочник Объект" → "СправочникОбъект")
2. **TypeMemberSearch** — паттерн "Тип.Член" ("ТаблицаЗначений Добавить")
3. **RegularSearch** — прямой lookup по индексам (точное совпадение + префикс)
4. **WordOrderSearch** — поиск по вхождению отдельных слов

### Семантический поиск

- **Embedding** запроса через `ai-forever/ru-en-RoSBERTa` (или API-провайдер)
- **ANN-поиск** в Qdrant embedded (in-process, данные на диске)
- **Reranking** результатов cross-encoder (`DiTy/cross-encoder-russian-msmarco`)
- **Ленивая инициализация**: модели загружаются при первом semantic/hybrid запросе

## Инструкции для AI-ассистентов

При использовании этого MCP-сервера рекомендуется:

1. **Начинайте с `search`** для нахождения нужных элементов API. Используйте конкретные термины 1С, а не общие описания.

2. **Уточняйте через `info`** — после нахождения нужного элемента получите полную документацию по точному имени.

3. **Навигация по типам**: используйте `get_members` для обзора всех методов/свойств типа, затем `get_member` для конкретного.

4. **Конструкторы**: если нужно создать объект, используйте `get_constructors` для получения сигнатур.

5. **Строгая типизация**: для вопросов о типизации BSL используйте `get_strict_typing_info` (сначала `topic='topics'` для списка тем).

6. **Стиль кода**: `get_coding_guideline` содержит полные рекомендации по написанию кода 1С.

7. **Режимы поиска**:
   - `keyword` — быстрый, для точных имён API (НайтиПоСсылке, ValueTable)
   - `semantic` — для запросов на естественном языке ("как добавить строку в таблицу")
   - `hybrid` — лучшее качество, комбинирует оба подхода

8. **Версии платформы**: `get_platform_info` покажет текущую версию и доступные.

## Тестирование

```bash
pip install -e ".[dev]"
pytest -v                     # Все тесты (306)
pytest -v tests/test_search_engine.py           # Один модуль
pytest -v tests/test_search_engine.py::test_name  # Один тест
```

## Источник данных

Сервер читает файл `shcntx_ru.hbk` из каталога установки платформы 1С:Предприятие. Это бинарный контейнер, содержащий:
- **PackBlock** — ZIP с оглавлением в bracket-формате
- **FileStorage** — ZIP с HTML-страницами документации

Поддерживаются версии HBK до 8.3.27+ включительно (multi-page data chains, изменённые TOC-коды языков, CSS-классы `V8SH_heading`/`V8SH_chapter`).

Альтернативно можно использовать pre-exported JSON (через [platform-context-exporter](https://github.com/alkoleft/platform-context-exporter)).

## Благодарности

- [alkoleft/mcp-bsl-platform-context](https://github.com/alkoleft/mcp-bsl-platform-context) — оригинальный Kotlin-проект
- [Model Context Protocol](https://modelcontextprotocol.io/) — спецификация MCP
- [FastMCP](https://github.com/jlowin/fastmcp) — Python MCP-фреймворк

## Лицензия

MIT
