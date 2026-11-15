#!/usr/bin/env python3
"""Create a small LongBench-style JSONL subset for KV utility pilots."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Iterable


DEFAULT_TASKS = [
    "hotpotqa",
    "2wikimqa",
    "narrativeqa",
    "qasper",
    "gov_report",
    "passage_retrieval_en",
]

OFFICIAL_PROMPTS = {
    "narrativeqa": "You are given a story, which can be either a novel or a movie script, and a question. Answer the question asconcisely as you can, using a single phrase if possible. Do not provide any explanation.\n\nStory: {context}\n\nNow, answer the question based on the story asconcisely as you can, using a single phrase if possible. Do not provide any explanation.\n\nQuestion: {input}\n\nAnswer:",
    "qasper": "You are given a scientific article and a question. Answer the question as concisely as you can, using a single phrase or sentence if possible. If the question cannot be answered based on the information in the article, write \"unanswerable\". If the question is a yes/no question, answer \"yes\", \"no\", or \"unanswerable\". Do not provide any explanation.\n\nArticle: {context}\n\n Answer the question based on the above article as concisely as you can, using a single phrase or sentence if possible. If the question cannot be answered based on the information in the article, write \"unanswerable\". If the question is a yes/no question, answer \"yes\", \"no\", or \"unanswerable\". Do not provide any explanation.\n\nQuestion: {input}\n\nAnswer:",
    "multifieldqa_en": "Read the following text and answer briefly.\n\n{context}\n\nNow, answer the following question based on the above text, only give me the answer and do not output any other words.\n\nQuestion: {input}\nAnswer:",
    "hotpotqa": "Answer the question based on the given passages. Only give me the answer and do not output any other words.\n\nThe following are given passages.\n{context}\n\nAnswer the question based on the given passages. Only give me the answer and do not output any other words.\n\nQuestion: {input}\nAnswer:",
    "2wikimqa": "Answer the question based on the given passages. Only give me the answer and do not output any other words.\n\nThe following are given passages.\n{context}\n\nAnswer the question based on the given passages. Only give me the answer and do not output any other words.\n\nQuestion: {input}\nAnswer:",
    "musique": "Answer the question based on the given passages. Only give me the answer and do not output any other words.\n\nThe following are given passages.\n{context}\n\nAnswer the question based on the given passages. Only give me the answer and do not output any other words.\n\nQuestion: {input}\nAnswer:",
    "triviaqa": "Answer the question based on the given passage. Only give me the answer and do not output any other words. The following are some examples.\n\n{context}\n\n{input}",
    "passage_count": "There are some paragraphs below sourced from Wikipedia. Some of them may be duplicates. Please carefully read these paragraphs and determine how many unique paragraphs there are after removing duplicates. In other words, how many non-repeating paragraphs are there in total?\n\n{context}\n\nPlease enter the final count of unique paragraphs after removing duplicates. The output format should only contain the number, such as 1, 2, 3, and so on.\n\nThe final answer is: ",
    "passage_retrieval_en": "Here are 30 paragraphs from Wikipedia, along with an abstract. Please determine which paragraph the abstract is from.\n\n{context}\n\nThe following is an abstract.\n\n{input}\n\nPlease enter the number of the paragraph that the abstract is from. The answer format must be like \"Paragraph 1\", \"Paragraph 2\", etc.\n\nThe answer is: ",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--tasks", default=",".join(DEFAULT_TASKS))
    parser.add_argument("--examples-per-task", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument(
        "--max-context-chars",
        type=int,
        default=24000,
        help="Truncate contexts for pilot runs. Use 0 to disable truncation.",
    )
    parser.add_argument(
        "--trust-remote-code",
        action="store_true",
        help="Required by THUDM/LongBench on Hugging Face datasets.",
    )
    parser.add_argument(
        "--official-prompts",
        action="store_true",
        help="Use the official LongBench v1 prompt templates for supported tasks.",
    )
    return parser.parse_args()


def parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def normalize_answers(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            out.extend(normalize_answers(item))
        return out
    return [str(value)]


def truncate_context(context: str, max_chars: int) -> str:
    if max_chars <= 0 or len(context) <= max_chars:
        return context
    half = max_chars // 2
    return (
        context[:half]
        + "\n\n[... middle context truncated for pilot budget ...]\n\n"
        + context[-half:]
    )


def build_prompt(task: str, question: str, context: str, official_prompts: bool) -> str:
    if official_prompts and task in OFFICIAL_PROMPTS:
        return OFFICIAL_PROMPTS[task].format(context=context, input=question)
    task_hint = ""
    if task == "passage_retrieval_en":
        task_hint = (
            "This is a passage retrieval task. The correct answer is a paragraph "
            "identifier such as \"Paragraph 7\". Return only that identifier.\n"
        )
    elif task in {"hotpotqa", "2wikimqa", "musique"}:
        task_hint = "This is a multi-hop QA task. Return only the short answer entity or phrase.\n"
    return (
        "You are evaluating long-context utility under KV cache compression.\n"
        "Answer the question using only the provided context. Return a concise answer; "
        "do not include reasoning.\n\n"
        f"Dataset: LongBench/{task}\n\n"
        f"{task_hint}"
        f"Context:\n{context}\n\n"
        f"Question:\n{question}\n\n"
        "Answer:"
    )


def iter_task_rows(task: str, trust_remote_code: bool) -> Iterable[dict[str, Any]]:
    from datasets import load_dataset

    dataset = load_dataset(
        "THUDM/LongBench",
        task,
        split="test",
        streaming=True,
        trust_remote_code=trust_remote_code,
    )
    for row in dataset:
        yield dict(row)


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    tasks = parse_csv(args.tasks)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for task in tasks:
        task_rows = list(iter_task_rows(task, args.trust_remote_code))
        rng.shuffle(task_rows)
        selected = task_rows[: args.examples_per_task]
        for idx, row in enumerate(selected):
            question = str(row.get("input") or row.get("question") or row.get("query") or "")
            context = str(row.get("context") or row.get("document") or row.get("passage") or "")
            answers = normalize_answers(row.get("answers") or row.get("answer"))
            context = truncate_context(context, args.max_context_chars)
            prompt = build_prompt(task, question, context, args.official_prompts)
            records.append(
                {
                    "id": f"longbench_{task}_{idx:04d}",
                    "source": "LongBench",
                    "task": task,
                    "prompt": prompt,
                    "question": question,
                    "answers": answers,
                    "metadata": {
                        "length": row.get("length"),
                        "all_classes": row.get("all_classes"),
                        "max_context_chars": args.max_context_chars,
                        "prompt_source": "official_longbench_v1" if args.official_prompts else "authoritykv_pilot",
                    },
                }
            )

    with out_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"out": str(out_path), "num_records": len(records), "tasks": tasks}, indent=2))


if __name__ == "__main__":
    main()
