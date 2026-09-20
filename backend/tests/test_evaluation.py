from app.evaluation import EvaluationCase, evaluate_cases


def test_evaluation_reports_recall_rank_and_acl_leakage():
    cases = [
        EvaluationCase("question A", "u-a", ["doc-a"], ["doc-secret"]),
        EvaluationCase("question B", "u-b", ["doc-b", "doc-c"], ["doc-secret"]),
    ]
    results = {
        ("question A", "u-a"): ["doc-a"],
        ("question B", "u-b"): ["doc-x", "doc-c", "doc-secret"],
    }

    report = evaluate_cases(cases, lambda query, user_id: results[(query, user_id)])

    assert report == {"cases": 2, "recall_at_k": 0.75, "mrr": 0.75, "acl_leakage_count": 1}


def test_empty_evaluation_is_well_defined():
    assert evaluate_cases([], lambda *_: []) == {"cases": 0, "recall_at_k": 0.0, "mrr": 0.0, "acl_leakage_count": 0}
