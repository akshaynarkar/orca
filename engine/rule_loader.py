"""
engine/rule_loader.py
Loads and validates rules.yaml into Rule dataclass objects.
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

import yaml

from engine.signal_report import Rule

logger = logging.getLogger(__name__)

VALID_COLORS = {"GREEN", "RED", "BLUE", "AMBER", "PURPLE"}
VALID_CATEGORIES = {"insider", "filing", "fundamental", "price", "macro", "composite"}
REQUIRED_FIELDS = {"id", "name", "category", "color", "base_strength", "rarity",
                   "condition", "description"}


class RuleLoader:
    """Loads, validates, and returns all rules from rules.yaml."""

    def __init__(self, path: str | Path = "rules.yaml"):
        self.path = Path(path)
        self._rules: list[Rule] = []

    def load(self) -> list[Rule]:
        """Load rules.yaml and return list of validated Rule objects."""
        if not self.path.exists():
            raise FileNotFoundError(f"rules.yaml not found at {self.path}")

        with open(self.path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, list):
            raise ValueError("rules.yaml must be a YAML list of rule objects")

        rules = []
        for i, item in enumerate(raw):
            try:
                rule = self._validate_and_build(item, i)
                rules.append(rule)
            except (ValueError, KeyError) as e:
                logger.error(f"Rule #{i} invalid: {e}")
                raise

        self._rules = rules
        logger.info(f"Loaded {len(rules)} rules from {self.path}")
        return rules

    def _validate_and_build(self, item: dict, index: int) -> Rule:
        """Validate a single rule dict and return a Rule dataclass."""
        # Check required fields
        missing = REQUIRED_FIELDS - set(item.keys())
        if missing:
            raise ValueError(
                f"Rule #{index} (id={item.get('id', '?')}) missing fields: {missing}"
            )

        rule_id: str = item["id"]

        # Validate color
        color = str(item["color"]).upper()
        if color not in VALID_COLORS:
            raise ValueError(
                f"Rule {rule_id}: invalid color '{color}'. "
                f"Must be one of {VALID_COLORS}"
            )

        # Validate category
        category = str(item["category"]).lower()
        if category not in VALID_CATEGORIES:
            raise ValueError(
                f"Rule {rule_id}: invalid category '{category}'. "
                f"Must be one of {VALID_CATEGORIES}"
            )

        # Validate numeric ranges
        base_strength = int(item["base_strength"])
        rarity = int(item["rarity"])
        if not (0 <= base_strength <= 100):
            raise ValueError(f"Rule {rule_id}: base_strength must be 0–100")
        if not (0 <= rarity <= 100):
            raise ValueError(f"Rule {rule_id}: rarity must be 0–100")

        # Validate sic_overrides format
        sic_overrides = item.get("sic_overrides", {}) or {}
        self._validate_sic_overrides(rule_id, sic_overrides)

        return Rule(
            id=rule_id,
            name=str(item["name"]),
            category=category,
            color=color,
            base_strength=base_strength,
            rarity=rarity,
            condition=str(item["condition"]),
            description=str(item["description"]),
            enabled=bool(item.get("enabled", True)),
            sic_overrides=sic_overrides,
            validity_period=int(item.get("validity_period", 30)),
        )

    def _validate_sic_overrides(self, rule_id: str, overrides: dict) -> None:
        """Validate SIC override entries."""
        for sic_range, value in overrides.items():
            # Key must be a string like "6020-6099" or a single "1311"
            sic_str = str(sic_range)
            if "-" in sic_str:
                parts = sic_str.split("-")
                if len(parts) != 2:
                    raise ValueError(
                        f"Rule {rule_id}: invalid SIC range '{sic_range}'"
                    )
                try:
                    lo, hi = int(parts[0]), int(parts[1])
                    if lo >= hi:
                        raise ValueError(
                            f"Rule {rule_id}: SIC range '{sic_range}' lo >= hi"
                        )
                except ValueError as e:
                    if "lo >= hi" in str(e):
                        raise
                    raise ValueError(
                        f"Rule {rule_id}: SIC range '{sic_range}' not numeric"
                    ) from e
            else:
                try:
                    int(sic_str)
                except ValueError:
                    raise ValueError(
                        f"Rule {rule_id}: SIC key '{sic_range}' must be numeric or range"
                    )

            # Value must be "skip" or a dict with "condition" key
            if value != "skip":
                if not isinstance(value, dict) or "condition" not in value:
                    raise ValueError(
                        f"Rule {rule_id}: SIC override value must be 'skip' "
                        f"or {{condition: '...'}} — got {value!r}"
                    )

    @property
    def rules(self) -> list[Rule]:
        return self._rules

    def get_enabled(self) -> list[Rule]:
        return [r for r in self._rules if r.enabled]

    def get_by_id(self, rule_id: str) -> Optional[Rule]:
        for r in self._rules:
            if r.id == rule_id:
                return r
        return None

    def count(self) -> int:
        return len(self._rules)
