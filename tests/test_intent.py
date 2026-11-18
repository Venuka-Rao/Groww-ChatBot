from src.config import load_settings
from src.guardrails.intent import classify

SCHEMES = load_settings().schemes


def test_buy_question_is_a_refusal_for_the_named_scheme():
    intent = classify("Should I buy HDFC Small Cap?", SCHEMES)
    assert intent.label == "refuse_advice"
    assert intent.scheme_slug == "hdfc-small-cap-fund-direct-growth"


def test_performance_comparison_redirects_to_the_factsheet():
    intent = classify(
        "Which of these two funds performed better, HDFC Large Cap or HDFC Liquid Fund?",
        SCHEMES,
    )
    assert intent.label == "redirect_factsheet"
    assert intent.scheme_slug == "hdfc-large-cap-fund-direct-growth"
    assert intent.second_scheme_slug == "hdfc-liquid-fund-direct-growth"


def test_other_amc_is_out_of_corpus():
    intent = classify("Expense ratio of Axis Bluechip Fund?", SCHEMES)
    assert intent.label == "out_of_corpus"


def test_elss_lock_in_is_an_answer():
    intent = classify("What is the ELSS lock-in for HDFC ELSS Tax Saver Fund?", SCHEMES)
    assert intent.label == "answer"
    assert intent.scheme_slug == "hdfc-elss-tax-saver-fund-direct-plan-growth"


def test_return_questions_redirect_without_a_number():
    assert classify("Which fund returned more?", SCHEMES).label == "redirect_factsheet"
    assert classify("Is this beating the benchmark?", SCHEMES).label == "redirect_factsheet"


def test_sbi_is_out_of_corpus():
    intent = classify("Expense ratio of SBI Bluechip Fund?", SCHEMES)
    assert intent.label == "out_of_corpus"
    assert intent.scheme_slug == ""


def test_expense_ratio_without_a_scheme_stays_unanswered():
    intent = classify("What is the expense ratio?", SCHEMES)
    assert intent.label == "answer"
    assert intent.scheme_slug == ""
    assert intent.fact_type == "expense_ratio"


def test_statement_download_is_a_how_to():
    intent = classify("How do I download a capital-gains statement?", SCHEMES)
    assert intent.label == "how_to"
    assert intent.scheme_slug == ""
