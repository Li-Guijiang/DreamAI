"""Pick a model per question tier.

A site usually has one cheap model and one expensive one. Sending every greeting to
the expensive model wastes money; sending every architecture question to the cheap
one wastes the answer.

The mapping is configuration, not code: `DREAMAI_MODEL_BY_TIER=light=glm-4-flash,
deep=deepseek-reasoner`. Unknown tiers fall back to the site's default model, so a
typo degrades quality rather than breaking the site.
"""

from __future__ import annotations


def parse_tier_map(raw: str) -> dict[str, str]:
    """Parse ``light=a,deep=b`` into a dict; ignore empty or malformed pairs."""
    mapping: dict[str, str] = {}
    for item in (raw or "").split(","):
        item = item.strip()
        if not item or "=" not in item:
            continue
        tier, model = item.split("=", 1)
        tier, model = tier.strip().lower(), model.strip()
        if tier and model:
            mapping[tier] = model
    return mapping


def choose_model(tier: str, default: str, mapping: dict[str, str]) -> str:
    """The model for a tier, or the default when the tier is not mapped."""
    return mapping.get(tier, default) or default
