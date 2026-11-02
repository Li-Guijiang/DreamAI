"""A prompt rule is a request; these tests cover the guarantee."""

from __future__ import annotations

from dream_ai.identity import leaks_contact, mask_contacts, privacy_clause


def test_every_contact_string_is_masked():
    text = "手机 13800138000，邮箱 demo@example.com，另一个 demo2@example.org"

    masked = mask_contacts(text)

    assert not leaks_contact(masked)
    assert "13800138000" not in masked
    assert "demo@example.com" not in masked
    assert "demo2@example.org" not in masked


def test_ordinary_text_is_untouched():
    text = "把 README 里的版本号改成 1.3.0"

    assert mask_contacts(text) == text


def test_empty_input_is_safe():
    assert mask_contacts("") == ""
    assert leaks_contact("") is False


def test_clause_forbids_partial_disclosure():
    clause = privacy_clause()

    assert "私密" in clause
    assert "直接拒绝" in clause
    assert "只给个邮箱" not in clause
    assert "变相泄露" in clause, "partial answers are the usual leak"
    assert "未经本人同意我不能提供" in clause, "the refusal wording must be fixed"
