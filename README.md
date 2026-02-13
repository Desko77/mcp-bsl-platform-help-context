# MCP BSL Platform Help Context

**MCP-сервер для доступа к документации API платформы 1С:Предприятие**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![MCP](https://img.shields.io/badge/MCP-Compatible-purple)

Python-порт [mcp-bsl-platform-context](https://github.com/alkoleft/mcp-bsl-platform-context) (Kotlin/Spring Boot).

---

## Возможности

- **Нечёткий поиск** по API платформы 1С (методы, свойства, типы)
- **Детальная информация** о функциях, методах, свойствах, конструкторах
- **Навигация по объектной модели** платформы
- **Два источника данных**: прямое чтение HBK файлов или pre-exported JSON
- **Три транспорта**: STDIO (для Claude Desktop, Cursor), SSE и Streamable HTTP

## MCP-инструменты

| Инструмент | Описание |
|------------|----------|
| `search` | Нечёткий поиск по API (query, type?, limit?) |
| `info` | Детальная информация об элементе API (name, type) |
| `get_member` | Метод/свойство конкретного типа (type_name, member_name) |
| `get_members` | Все методы и свойства типа (type_name) |
| `get_constructors` | Конструкторы типа (type_name) |

## Установка

```bash
pip install -e .
```

### Зависимости

- Python 3.10+
- fastmcp >= 2.0
- beautifulsoup4 >= 4.12
- lxml >= 5.0
- click >= 8.1

## Использование

### Из HBK файла (прямое чтение)

```bash
mcp-bsl-context -p /opt/1cv8/x86_64/8.3.25.1257
```

### Из pre-exported JSON

```bash
mcp-bsl-context -p /path --data-source json --json-path /path/to/json
```

### Параметры CLI

```
--platform-path, -p    Путь к каталогу установки 1С (обязателен для hbk)
--mode, -m             Транспорт: stdio (по умолчанию), sse или streamable-http
--port                 Порт для HTTP-сервера (по умолчанию: 8080)
--data-source          Источник данных: hbk или json
--json-path            Путь к каталогу с JSON-файлами
--verbose, -v          Включить отладочное логирование
```

### Переменные окружения

Все параметры CLI можно задать через переменные окружения. CLI-аргументы имеют приоритет.

| CLI-аргумент | Переменная окружения | По умолчанию |
|---|---|---|
| `--platform-path` | `MCP_BSL_PLATFORM_PATH` | (обязателен для hbk) |
| `--mode` | `MCP_BSL_MODE` | `stdio` |
| `--port` | `MCP_BSL_PORT` | `8080` |
| `--data-source` | `MCP_BSL_DATA_SOURCE` | `hbk` |
| `--json-path` | `MCP_BSL_JSON_PATH` | — |
| `--verbose` | `MCP_BSL_VERBOSE` | `false` |

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

### SSE-режим (сетевой доступ)

```bash
mcp-bsl-context -p /opt/1cv8/x86_64/8.3.25.1257 -m sse --port 8080
```

### Streamable HTTP (рекомендуется для новых интеграций)

[Streamable HTTP](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http) — актуальный HTTP-транспорт в спецификации MCP, заменяющий устаревший SSE. Основные отличия:

- **Единый эндпоинт** `/mcp` вместо двух (`/sse` + `/messages`) — проще настройка и проксирование
- **Stateless-режим** — каждый запрос самодостаточен, не требуется держать долгоживущее SSE-соединение
- **Совместимость** — по-прежнему может использовать SSE для стриминга ответов внутри HTTP-ответа
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

> **Примечание:** SSE-режим (`-m sse`) по-прежнему поддерживается для обратной совместимости с клиентами, которые ещё не обновились до Streamable HTTP.

## Docker

### Сборка образа

```bash
docker build -t mcp-bsl-context .
```

### Запуск с HBK-данными

```bash
docker run -d \
  -v /opt/1cv8/x86_64/8.3.25.1257:/data/platform:ro \
  -p 8080:8080 \
  mcp-bsl-context
```

### Запуск с JSON-данными

```bash
docker run -d \
  -e MCP_BSL_DATA_SOURCE=json \
  -v ./json-data:/data/json:ro \
  -p 8080:8080 \
  mcp-bsl-context
```

### Docker Compose

HBK-режим (поместите каталог платформы 1С в `./platform-data/`):

```bash
docker compose up -d
```

JSON-режим (поместите JSON-файлы в `./json-data/`):

```bash
docker compose --profile json up -d
```

### Проверка здоровья

```bash
docker inspect --format='{{.State.Health.Status}}' mcp-bsl-context
```

## Архитектура

```
mcp_bsl_context/
├── domain/                 # Доменный слой
│   ├── entities.py         # Definition, MethodDefinition, PropertyDefinition, ...
│   ├── enums.py            # ApiType (METHOD, PROPERTY, TYPE, CONSTRUCTOR)
│   ├── exceptions.py       # Иерархия исключений
│   ├── value_objects.py    # SearchQuery, SearchOptions
│   └── services.py         # ContextSearchService
│
├── infrastructure/
│   ├── hbk/                # Парсер бинарного формата HBK
│   │   ├── container_reader.py   # Бинарный контейнер
│   │   ├── content_reader.py     # ZIP-распаковка, TOC + FileStorage
│   │   ├── context_reader.py     # Оркестратор чтения
│   │   ├── pages_visitor.py      # Visitor: обход дерева страниц
│   │   ├── toc/                  # TOC: токенизатор, парсер, дерево
│   │   └── parsers/              # HTML-парсеры страниц (BeautifulSoup)
│   │
│   ├── json_loader/        # Альтернативный источник: JSON
│   ├── search/             # Поисковый движок
│   │   ├── indexes.py      # HashIndex, StartWithIndex
│   │   ├── strategies.py   # 4 стратегии поиска
│   │   └── engine.py       # SimpleSearchEngine
│   │
│   └── storage/            # Хранилище и репозиторий
│
├── presentation/
│   └── formatter.py        # Markdown-форматтер
│
├── server.py               # FastMCP сервер (5 инструментов)
└── __main__.py             # CLI (click)
```

### Поисковый движок

4 стратегии поиска с приоритетами:

1. **CompoundTypeSearch** — составные имена типов ("Справочник Объект" → "СправочникОбъект")
2. **TypeMemberSearch** — паттерн "Тип.Член" ("ТаблицаЗначений Добавить")
3. **RegularSearch** — прямой lookup по индексам (точное совпадение + префикс)
4. **WordOrderSearch** — поиск по вхождению отдельных слов

## Тестирование

```bash
pip install -e ".[dev]"
pytest -v
```

79 тестов покрывают: доменные сущности, токенизатор, индексы, поисковый движок, форматтер, сервис поиска, JSON-загрузчик.

## Источник данных

Оригинал читает файл `shcntx_ru.hbk` из каталога установки платформы 1С:Предприятие. Это бинарный контейнер содержащий:
- **PackBlock** — ZIP с оглавлением в bracket-формате
- **FileStorage** — ZIP с HTML-страницами документации

Альтернативно можно использовать pre-exported JSON (через [platform-context-exporter](https://github.com/alkoleft/platform-context-exporter)).

## Благодарности

- [alkoleft/mcp-bsl-platform-context](https://github.com/alkoleft/mcp-bsl-platform-context) — оригинальный Kotlin-проект
- [Model Context Protocol](https://modelcontextprotocol.io/) — спецификация MCP
- [FastMCP](https://github.com/jlowin/fastmcp) — Python MCP-фреймворк

## Лицензия

MIT
