"""A prompt rule is a request; these tests cover the guarantee."""

from __future__ import annotations

from dream_ai.identity import OWNER, leaks_contact, mask_contacts, privacy_clause


def test_every_contact_string_is_masked():
    text = (
        f"手机 {OWNER.phone}，微信 {OWNER.wechat}，QQ {OWNER.qq}，"
        f"邮箱 {OWNER.email_qq} / {OWNER.email_gmail} / {OWNER.email_foxmail}"
    )

    masked = mask_contacts(text)

    assert not leaks_contact(masked)
    for secret in (OWNER.phone, OWNER.qq, OWNER.email_qq, OWNER.email_gmail, OWNER.email_foxmail):
        assert secret not in masked


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
