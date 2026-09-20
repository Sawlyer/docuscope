import argparse
import json
from pathlib import Path

from .database import session_scope
from .evaluation import EvaluationCase, evaluate_cases
from .repositories import UserRepository
from .retrieval import dense_retriever
from .rag_runtime import initialize_rag


TITLE_ALIASES = {
    "01-organigramme.pdf": "doc-org",
    "02-politique-rh.pdf": "doc-rh",
    "03-teletravail.pdf": "doc-handbook",
    "04-securite.pdf": "doc-security",
    "05-architecture.pdf": "doc-architecture",
    "06-finance.pdf": "doc-finance",
    "07-commercial.pdf": "doc-pipeline",
    "08-contrat-confidentiel.pdf": "doc-contract",
}


def load_cases(path: Path) -> list[EvaluationCase]:
    return [EvaluationCase(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Évalue le retrieval dense et les ACL DocuScope.")
    parser.add_argument("--cases", default="/evaluation/cases.jsonl")
    parser.add_argument("--output")
    args = parser.parse_args()
    initialize_rag()
    cases = load_cases(Path(args.cases))
    with session_scope() as session:
        users = {user.id: user for user in UserRepository(session).list()}

    def search(query: str, user_id: str) -> list[str]:
        user = users[user_id]
        return [TITLE_ALIASES.get(hit.title, hit.document_id) for hit in dense_retriever.search(query, user)]

    report = evaluate_cases(cases, search)
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    if report["acl_leakage_count"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
