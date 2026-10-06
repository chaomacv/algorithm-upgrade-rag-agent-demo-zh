from typing import Iterable, List

from algo_rag_demo.case_pipeline.schema import EngineeringCase, KnowledgeChunk


def chunk_case(case: EngineeringCase) -> List[KnowledgeChunk]:
    """Create task, constraint, and solution chunks from one structured case."""
    # Each chunk is a schema-aligned retrieval view of the same case.
    chunks = [
        KnowledgeChunk(
            chunk_id=f"{case.case_id}_task",
            case_id=case.case_id,
            chunk_type="task",
            module=case.module,
            final_status=case.final_status,
            source=case.source_conversation_id,
            text=(
                f"Module: {case.module}. Task: {case.task}. "
                f"Replace {case.old_algorithm} with {case.new_algorithm}."
            ),
        ),
        KnowledgeChunk(
            chunk_id=f"{case.case_id}_constraint",
            case_id=case.case_id,
            chunk_type="constraint",
            module=case.module,
            final_status=case.final_status,
            source=case.source_conversation_id,
            text=" ".join(
                item
                for group in case.constraints.values()
                for item in group
            ),
        ),
        KnowledgeChunk(
            chunk_id=f"{case.case_id}_solution",
            case_id=case.case_id,
            chunk_type="solution",
            module=case.module,
            final_status=case.final_status,
            source=case.source_conversation_id,
            text=" ".join(
                [p.get("symptom", "") + " " + p.get("root_cause", "") for p in case.problems]
                + [s.get("solution", "") for s in case.solutions]
                + case.reusable_experience
            ),
        ),
    ]
    return chunks


def chunk_cases(cases: Iterable[EngineeringCase]) -> List[KnowledgeChunk]:
    """Create retrieval chunks for every structured case."""
    # Flatten per-case chunks so the vector index can store one row per chunk.
    chunks: List[KnowledgeChunk] = []
    for case in cases:
        chunks.extend(chunk_case(case))
    return chunks

