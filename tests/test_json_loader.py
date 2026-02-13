"""Tests for the JSON context loader."""

import json
import tempfile
from pathlib import Path

from mcp_bsl_context.infrastructure.json_loader.json_context_loader import JsonContextLoader


class TestJsonContextLoader:
    def test_load_methods(self, tmp_path):
        data = [
            {"name": "Найти", "description": "Поиск", "return_type": "Строка"},
            {"name": "Добавить", "description": "Добавление"},
        ]
        methods_file = tmp_path / "methods.json"
        methods_file.write_text(json.dumps(data), encoding="utf-8")

        loader = JsonContextLoader()
        methods = loader.load_methods(methods_file)
        assert len(methods) == 2
        assert methods[0].name == "Найти"
        assert methods[0].return_type == "Строка"

    def test_load_properties(self, tmp_path):
        data = [
            {"name": "Дата", "description": "Текущая дата", "type": "Дата", "readOnly": True},
        ]
        props_file = tmp_path / "properties.json"
        props_file.write_text(json.dumps(data), encoding="utf-8")

        loader = JsonContextLoader()
        props = loader.load_properties(props_file)
        assert len(props) == 1
        assert props[0].name == "Дата"
        assert props[0].is_read_only is True

    def test_load_types(self, tmp_path):
        data = [
            {
                "name": "Массив",
                "description": "Массив значений",
                "methods": [{"name": "Добавить", "description": "Добавить элемент"}],
                "properties": [],
                "constructors": [],
            }
        ]
        types_file = tmp_path / "types.json"
        types_file.write_text(json.dumps(data), encoding="utf-8")

        loader = JsonContextLoader()
        types = loader.load_types(types_file)
        assert len(types) == 1
        assert types[0].name == "Массив"
        assert len(types[0].methods) == 1

    def test_load_all(self, tmp_path):
        methods = [{"name": "M1", "description": ""}]
        props = [{"name": "P1", "description": "", "type": "Str"}]
        types = [{"name": "T1", "description": "", "methods": [], "properties": [], "constructors": []}]

        (tmp_path / "methods.json").write_text(json.dumps(methods), encoding="utf-8")
        (tmp_path / "properties.json").write_text(json.dumps(props), encoding="utf-8")
        (tmp_path / "types.json").write_text(json.dumps(types), encoding="utf-8")

        loader = JsonContextLoader()
        m, p, t = loader.load_all(tmp_path)
        assert len(m) == 1
        assert len(p) == 1
        assert len(t) == 1

    def test_load_combined_json(self, tmp_path):
        data = {
            "methods": [{"name": "M1", "description": ""}],
            "properties": [{"name": "P1", "description": "", "type": "T"}],
            "types": [{"name": "T1", "description": "", "methods": [], "properties": [], "constructors": []}],
        }
        (tmp_path / "context.json").write_text(json.dumps(data), encoding="utf-8")

        loader = JsonContextLoader()
        m, p, t = loader.load_all(tmp_path)
        assert len(m) == 1
        assert len(p) == 1
        assert len(t) == 1

    def test_load_with_signatures(self, tmp_path):
        data = [{
            "name": "Func",
            "description": "",
            "signatures": [{
                "name": "Func",
                "description": "",
                "parameters": [
                    {"name": "p1", "type": "Число", "description": "Параметр", "required": True}
                ],
            }],
        }]
        (tmp_path / "methods.json").write_text(json.dumps(data), encoding="utf-8")

        loader = JsonContextLoader()
        methods = loader.load_methods(tmp_path / "methods.json")
        assert len(methods[0].signatures) == 1
        assert methods[0].signatures[0].parameters[0].name == "p1"
        assert methods[0].signatures[0].parameters[0].required is True
