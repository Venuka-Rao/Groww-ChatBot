"""Detect personal identifiers. Returns only a boolean so the match is never logged."""

from __future__ import annotations

import re

_PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
_AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?:\+91[\s-]?|0)?[6-9]\d{9}\b")
_ACCOUNT = re.compile(r"\b\d{9,18}\b")
_OTP = re.compile(r"\botp\b[:\s-]*\d{4,8}\b|\b\d{4,8}\b[:\s-]*\botp\b", re.IGNORECASE)

PII_RESEND = (
    "Please resend your question without personal details such as PAN, Aadhaar, "
    "account numbers, OTPs, email, or phone."
)


def find_pii(text: str) -> bool:
    return any(
        pattern.search(text)
        for pattern in (_PAN, _AADHAAR, _EMAIL, _PHONE, _ACCOUNT, _OTP)
    )
