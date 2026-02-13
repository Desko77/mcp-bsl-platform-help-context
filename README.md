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
- **Два транспорта**: STDIO (для Claude Desktop, Cursor) и SSE (HTTP)

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
--platform-path, -p    Путь к каталогу установки 1С (обязательный)
--mode, -m             Транспорт: stdio (по умолчанию) или sse
--port                 Порт для SSE-сервера (по умолчанию: 8080)
--data-source          Источник данных: hbk или json
--json-path            Путь к каталогу с JSON-файлами
--verbose, -v          Включить отладочное логирование
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

### SSE-режим (сетевой доступ)

```bash
mcp-bsl-context -p /opt/1cv8/x86_64/8.3.25.1257 -m sse --port 8080
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
