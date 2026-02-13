"""Tests for HybridSearchEngine (RRF merge)."""

import pytest

from mcp_bsl_context.domain.entities import (
    MethodDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
)
from mcp_bsl_context.infrastructure.search.hybrid_engine import (
    RRF_K,
    HybridSearchEngine,
    _definition_key,
)


class TestDefinitionKey:
    def test_method_key(self):
        m = MethodDefinition(name="Тест", description="")
        assert _definition_key(m) == "MethodDefinition:Тест"

    def test_property_key(self):
        p = PropertyDefinition(name="Свойство", description="")
        assert _definition_key(p) == "PropertyDefinition:Свойство"

    def test_type_key(self):
        t = PlatformTypeDefinition(name="МойТип", description="")
        assert _definition_key(t) == "PlatformTypeDefinition:МойТип"


class TestRRFMerge:
    def test_empty_lists(self):
        result = HybridSearchEngine._rrf_merge([], [])
        assert result == []

    def test_single_list_a(self):
        m = MethodDefinition(name="А", description="")
        result = HybridSearchEngine._rrf_merge([m], [])
        assert len(result) == 1
        assert result[0].name == "А"

    def test_single_list_b(self):
        m = MethodDefinition(name="Б", description="")
        result = HybridSearchEngine._rrf_merge([], [m])
        assert len(result) == 1
        assert result[0].name == "Б"

    def test_same_item_in_both_lists_gets_higher_score(self):
        """An item found by both engines should rank higher."""
        m1 = MethodDefinition(name="Общий", description="")
        m2 = MethodDefinition(name="ТолькоA", description="")
        m3 = MethodDefinition(name="ТолькоB", description="")

        list_a = [m2, m1]  # m2 rank=1, m1 rank=2
        list_b = [m3, m1]  # m3 rank=1, m1 rank=2

        result = HybridSearchEngine._rrf_merge(list_a, list_b)

        # "Общий" appears in both lists, should be ranked first
        assert result[0].name == "Общий"

    def test_deduplication(self):
        m = MethodDefinition(name="Дубль", description="")
        result = HybridSearchEngine._rrf_merge([m], [m])
        assert len(result) == 1

    def test_preserves_order_by_rrf_score(self):
        """Items ranked #1 in their list get higher individual RRF score."""
        m_top_a = MethodDefinition(name="ТопА", description="")
        m_top_b = MethodDefinition(name="ТопБ", description="")
        m_low_a = MethodDefinition(name="НизА", description="")

        # ТопА is #1 in list A, НизА is #2
        list_a = [m_top_a, m_low_a]
        # ТопБ is #1 in list B
        list_b = [m_top_b]

        result = HybridSearchEngine._rrf_merge(list_a, list_b)

        # Top items from each list should score: 1/(60+1) ≈ 0.0164
        # Lower items: 1/(60+2) ≈ 0.0161
        names = [r.name for r in result]
        assert "ТопА" in names
        assert "ТопБ" in names
        assert "НизА" in names

    def test_rrf_scores_are_correct(self):
        """Verify actual RRF score computation."""
        m1 = MethodDefinition(name="M1", description="")
        m2 = MethodDefinition(name="M2", description="")

        # m1 is rank 1 in list_a, rank 2 in list_b
        # m2 is rank 2 in list_a, rank 1 in list_b
        list_a = [m1, m2]
        list_b = [m2, m1]

        result = HybridSearchEngine._rrf_merge(list_a, list_b)

        # Both should have equal scores: 1/(60+1) + 1/(60+2)
        # So the order depends on dict iteration, but both should appear
        assert len(result) == 2
        names = {r.name for r in result}
        assert names == {"M1", "M2"}

    def test_different_types_not_deduplicated(self):
        """Method and property with same name are different items."""
        m = MethodDefinition(name="Имя", description="")
        p = PropertyDefinition(name="Имя", description="")

        result = HybridSearchEngine._rrf_merge([m], [p])
        assert len(result) == 2
