"""Phrases shared by chunk labels and the intent gate.

Longer phrases are listed first so a later matcher can take the first hit.
"""

FACT_PHRASES: dict[str, tuple[str, ...]] = {
    "expense_ratio": ("expense ratio", "total expense", "ter"),
    "exit_load": ("exit load",),
    "min_sip": ("minimum sip", "sip minimum", "min sip", "minimum investment"),
    "lock_in": ("lock-in", "lock in", "elss"),
    "riskometer": ("riskometer",),
    "benchmark": ("benchmark",),
    "statement_howto": ("capital-gains", "capital gains", "capital gain", "statement", "download"),
}

ADVICE_PHRASES: tuple[str, ...] = (
    "which fund should i pick",
    "which fund should",
    "which one should",
    "should i",
    "recommend",
    "portfolio",
    "suitable",
    "buy",
    "sell",
    "hold",
)

PERFORMANCE_PHRASES: tuple[str, ...] = (
    "which fund did better",
    "which performed better",
    "which fund returned",
    "which of these",
    "beating the benchmark",
    "outperform",
    "performance",
    "performed",
    "returned",
    "returns",
    "beating",
    "cagr",
    "alpha",
)
