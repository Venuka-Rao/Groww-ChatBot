from dataclasses import replace

from src.config import load_settings
from src.guardrails.pii import find_pii
from src.pipeline.ask import ask


def test_pan_is_detected_and_not_echoed(tmp_path):
    settings = replace(load_settings(), root=tmp_path)
    answer = ask("My PAN is ABCDE1234F", settings=settings)
    assert answer.intent == "pii"
    assert "ABCDE1234F" not in answer.text
    assert not (tmp_path / "data" / "artifacts" / "retrieve").exists()
    assert not (tmp_path / "data" / "artifacts" / "generate").exists()


def test_email_and_mobile_are_detected():
    assert find_pii("mail me at user@example.com")
    assert find_pii("call 9876543210")


def test_aadhaar_account_and_otp_are_not_stored(tmp_path):
    settings = replace(load_settings(), root=tmp_path)
    samples = (
        "aadhaar 1111 2222 3333",
        "account 123456789",
        "otp 123456",
    )
    for sample in samples:
        answer = ask(sample, settings=settings)
        assert answer.intent == "pii"
        assert "1111" not in answer.text
        assert "123456789" not in answer.text
        assert "123456" not in answer.text
    assert not (tmp_path / "data").exists()


def test_fact_numbers_are_not_pii():
    assert not find_pii("Expense ratio is 0.99%")
    assert not find_pii("The fact was published in 2024")
