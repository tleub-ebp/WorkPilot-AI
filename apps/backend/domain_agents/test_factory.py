"""Tests for the Domain-Specific Agent Factory."""

from __future__ import annotations

import pytest
from domain_agents import (
    AgentRole,
    DomainAgentBundle,
    DomainAgentFactory,
    DomainTag,
)


class TestCatalogue:
    def test_list_domains_returns_all_tags(self) -> None:
        domains = DomainAgentFactory().list_domains()
        tags = {d["tag"] for d in domains}
        assert tags == {t.value for t in DomainTag}

    def test_each_entry_has_label_and_description(self) -> None:
        for d in DomainAgentFactory().list_domains():
            assert d["label"]
            assert d["description"]

    def test_get_profile_by_string(self) -> None:
        p = DomainAgentFactory().get_profile("fintech")
        assert p.tag == DomainTag.FINTECH

    def test_get_profile_by_enum(self) -> None:
        p = DomainAgentFactory().get_profile(DomainTag.HEALTHCARE)
        assert p.label == "Healthcare"

    def test_unknown_domain_raises(self) -> None:
        with pytest.raises(ValueError):
            DomainAgentFactory().get_profile("not-a-domain")


class TestBundleComposition:
    def test_generic_bundle_has_no_addendum(self) -> None:
        bundle = DomainAgentFactory().build("generic", "coder")
        assert bundle.prompt_addendum == ""
        assert bundle.required_skills == []

    def test_fintech_coder_includes_guardrails_and_forbidden(self) -> None:
        bundle = DomainAgentFactory().build("fintech", "coder")
        assert "double-entry" in bundle.prompt_addendum.lower()
        assert any(
            "PAN" in g or "SSN" in g or "Decimal" in g for g in bundle.guardrails
        )
        # The coder role should inherit forbidden patterns.
        assert bundle.forbidden_patterns
        # But not validation rules — those are for the reviewer specifically.
        # Wait — the role narrowing also surfaces validation_rules to coders
        # so they know what they'll be checked against. That's intentional.
        assert bundle.validation_rules

    def test_healthcare_planner_lists_required_skills(self) -> None:
        bundle = DomainAgentFactory().build("healthcare", "planner")
        assert "phi-encryption" in bundle.required_skills
        assert "Required skills" in bundle.prompt_addendum

    def test_documenter_role_skips_skills_and_forbidden(self) -> None:
        # Documenter doesn't write code or approve PRs — narrow surface.
        bundle = DomainAgentFactory().build("ecommerce", "documenter")
        assert bundle.required_skills == []
        assert bundle.forbidden_patterns == []
        assert bundle.validation_rules == []

    def test_reviewer_includes_validation_rules(self) -> None:
        bundle = DomainAgentFactory().build("saas", "reviewer")
        assert bundle.validation_rules
        assert "Validation rules" in bundle.prompt_addendum

    def test_planner_does_not_include_forbidden_patterns(self) -> None:
        # Forbidden patterns are about code — planners don't write code.
        bundle = DomainAgentFactory().build("fintech", "planner")
        assert bundle.forbidden_patterns == []

    def test_string_or_enum_inputs_equivalent(self) -> None:
        a = DomainAgentFactory().build("ecommerce", "coder")
        b = DomainAgentFactory().build(DomainTag.ECOMMERCE, AgentRole.CODER)
        assert a.to_dict() == b.to_dict()

    def test_invalid_role_raises(self) -> None:
        with pytest.raises(ValueError):
            DomainAgentFactory().build("fintech", "ghost-role")

    def test_to_dict_serialisable(self) -> None:
        import json

        bundle = DomainAgentFactory().build("iot", "coder")
        decoded = json.loads(json.dumps(bundle.to_dict()))
        assert decoded["domain"] == "iot"
        assert decoded["role"] == "coder"
        assert "profile" in decoded


class TestPromptAddendum:
    def test_addendum_mentions_domain_label(self) -> None:
        bundle = DomainAgentFactory().build("gaming", "coder")
        assert "Gaming" in bundle.prompt_addendum

    def test_suggested_libraries_present(self) -> None:
        bundle = DomainAgentFactory().build("ecommerce", "coder")
        assert "stripe" in bundle.prompt_addendum

    def test_no_forbidden_section_when_empty(self) -> None:
        # govtech has no forbidden_patterns — no section should appear.
        bundle = DomainAgentFactory().build("govtech", "coder")
        assert "Forbidden patterns" not in bundle.prompt_addendum

    def test_addendum_length_is_reasonable(self) -> None:
        # Should fit comfortably in a system prompt — under 4 KB.
        for tag in DomainTag:
            for role in AgentRole:
                if tag == DomainTag.GENERIC:
                    continue
                bundle = DomainAgentFactory().build(tag, role)
                assert len(bundle.prompt_addendum) < 4_000


class TestRoleNarrowing:
    def test_coder_gets_forbidden_patterns(self) -> None:
        bundle = DomainAgentFactory().build("fintech", "coder")
        assert any("float" in fp.lower() for fp in bundle.forbidden_patterns)

    def test_reviewer_gets_validation_rules(self) -> None:
        bundle = DomainAgentFactory().build("fintech", "reviewer")
        assert any("ledger" in vr.lower() for vr in bundle.validation_rules)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
