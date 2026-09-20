from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationCase:
    query: str
    user_id: str
    expected_document_ids: list[str]
    forbidden_document_ids: list[str]


def evaluate_cases(cases: list[EvaluationCase], search) -> dict[str, float | int]:
    recall_total = 0.0
    reciprocal_rank_total = 0.0
    leakage_count = 0
    for case in cases:
        result_ids = list(search(case.query, case.user_id))
        expected = set(case.expected_document_ids)
        recall_total += len(expected.intersection(result_ids)) / len(expected) if expected else 1.0
        ranks = [result_ids.index(document_id) + 1 for document_id in expected if document_id in result_ids]
        reciprocal_rank_total += 1 / min(ranks) if ranks else 0.0
        leakage_count += sum(document_id in set(case.forbidden_document_ids) for document_id in result_ids)
    count = len(cases)
    return {
        "cases": count,
        "recall_at_k": round(recall_total / count, 4) if count else 0.0,
        "mrr": round(reciprocal_rank_total / count, 4) if count else 0.0,
        "acl_leakage_count": leakage_count,
    }
