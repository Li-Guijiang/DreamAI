"""Pick a model per question tier.

A site usually has one cheap model and one expensive one. Sending every greeting to
the expensive model wastes money; sending every architecture question to the cheap
one wastes the answer.

The mapping is configuration, not code: `DREAMAI_MODEL_BY_TIER=light=glm-4-flash,
deep=deepseek-reasoner`. Unknown tiers fall back to the site's default model, so a
typo degrades quality rather than breaking the site.

A `default=` entry sits between the two: tiers keep their own model, everything
else gets the configured default, and only a mapping with neither falls through
to the site setting.
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


DEFAULT_KEY = "default"


def choose_model(tier: str, default: str, mapping: dict[str, str]) -> str:
    """The model for a tier, then the mapping's default, then the site default."""
    key = (tier or "").strip().lower()
    chosen = mapping.get(key) or mapping.get(DEFAULT_KEY) or default
    return chosen or default


def describe_routing(mapping: dict[str, str], default: str) -> str:
    """One line for the startup log: what will actually be called, and for what."""
    if not mapping:
        return f"routing: every tier uses {default}"
    pairs = " ".join(f"{tier}={model}" for tier, model in sorted(mapping.items()))
    return f"routing: {default} unless overridden ({pairs})"


def unknown_targets(mapping: dict[str, str], known: set[str]) -> dict[str, str]:
    """Tier entries naming a model this site does not serve.

    Caught at startup rather than at the first deep question: a typo in the map
    only shows up when that tier is chosen, which may be hours later.
    """
    return {tier: model for tier, model in mapping.items() if model not in known}
