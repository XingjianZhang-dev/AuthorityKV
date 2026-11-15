#!/usr/bin/env python3
"""Run generic external utility JSONL tasks with KV pruning methods."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import string
import sys
from collections import defaultdict
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from run_authoritykv_smoke import (
    VALID_METHODS,
    generate_one,
    git_commit_or_null,
    gpu_name,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--methods", required=True)
    parser.add_argument("--keep-ratios", default="0.20,0.40")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    parser.add_argument("--chunk-size", type=int, default=128)
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", default="bf16", choices=["bf16", "fp16", "fp32"])
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--use-chat-template",
        action="store_true",
        help="Wrap each prompt as a single user message with the tokenizer chat template.",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_float_csv(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_jsonl(path: Path, limit: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
                if limit is not None and len(rows) >= limit:
                    break
    return rows


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.split())


def answers_for(record: dict[str, Any]) -> list[str]:
    value = record.get("answers", record.get("answer"))
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, list):
                out.extend(str(x) for x in item)
            else:
                out.append(str(item))
        return out
    return [str(value)]


def judge_output(output_text: str, answers: list[str], judge_mode: str = "contains_any") -> dict[str, Any]:
    normalized_output = normalize_text(output_text)
    normalized_answers = [normalize_text(answer) for answer in answers if answer]
    match_fraction = (
        sum(
            1.0
            for answer in normalized_answers
            if answer
            and normalized_output
            and answer in normalized_output
        )
        / len(normalized_answers)
        if normalized_answers
        else 0.0
    )
    contains = any(
        answer
        and normalized_output
        and answer in normalized_output
        for answer in normalized_answers
    )
    if judge_mode == "ruler_string_match_all":
        contains = bool(normalized_answers) and match_fraction == 1.0
    exact = any(answer and normalized_output == answer for answer in normalized_answers)
    return {
        "correct": bool(contains),
        "exact_match": bool(exact),
        "answer_match_fraction": match_fraction,
        "normalized_output": normalized_output,
    }


def qa_f1_score(prediction: str, ground_truth: str) -> float:
    prediction_tokens = normalize_text(prediction).split()
    ground_truth_tokens = normalize_text(ground_truth).split()
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0 or not prediction_tokens or not ground_truth_tokens:
        return 0.0
    precision = num_same / len(prediction_tokens)
    recall = num_same / len(ground_truth_tokens)
    return 2 * precision * recall / (precision + recall)


def retrieval_score(prediction: str, ground_truth: str) -> float:
    match = re.findall(r"Paragraph\s+(\d+)", ground_truth, flags=re.IGNORECASE)
    if not match:
        return 0.0
    ground_truth_id = match[0]
    numbers = re.findall(r"\d+", prediction)
    if not numbers:
        return 0.0
    return sum(number == ground_truth_id for number in numbers) / len(numbers)


def count_score(prediction: str, ground_truth: str) -> float:
    numbers = re.findall(r"\d+", prediction)
    if not numbers:
        return 0.0
    return sum(number == str(ground_truth) for number in numbers) / len(numbers)


def official_longbench_score(task: str, output_text: str, answers: list[str]) -> float | None:
    if not answers:
        return None
    if task in {"hotpotqa", "2wikimqa", "musique", "triviaqa", "narrativeqa", "qasper", "multifieldqa_en"}:
        return max(qa_f1_score(output_text, answer) for answer in answers)
    if task == "passage_retrieval_en":
        return max(retrieval_score(output_text, answer) for answer in answers)
    if task == "passage_count":
        return max(count_score(output_text, answer) for answer in answers)
    return None


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[f"{record['method']}@{record['keep_ratio']:.2f}"].append(record)
    by_method: dict[str, Any] = {}
    for key, rows in sorted(grouped.items()):
        correct = sum(row["correct"] for row in rows)
        exact = sum(row["exact_match"] for row in rows)
        score_rows = [row for row in rows if row.get("longbench_score") is not None]
        score_sum = sum(row["longbench_score"] for row in score_rows)
        match_rows = [row for row in rows if row.get("answer_match_fraction") is not None]
        match_sum = sum(row["answer_match_fraction"] for row in match_rows)
        by_task: dict[str, Any] = {}
        for task in sorted({row.get("task", "unknown") for row in rows}):
            task_rows = [row for row in rows if row.get("task", "unknown") == task]
            task_score_rows = [row for row in task_rows if row.get("longbench_score") is not None]
            task_match_rows = [row for row in task_rows if row.get("answer_match_fraction") is not None]
            by_task[task] = {
                "correct_num": sum(row["correct"] for row in task_rows),
                "correct_den": len(task_rows),
                "exact_num": sum(row["exact_match"] for row in task_rows),
                "exact_den": len(task_rows),
                "answer_match_fraction": (
                    sum(row["answer_match_fraction"] for row in task_match_rows) / len(task_match_rows)
                    if task_match_rows
                    else None
                ),
                "answer_match_fraction_den": len(task_match_rows),
                "longbench_score": (
                    sum(row["longbench_score"] for row in task_score_rows) / len(task_score_rows)
                    if task_score_rows
                    else None
                ),
                "longbench_score_den": len(task_score_rows),
            }
        by_method[key] = {
            "method": rows[0]["method"],
            "keep_ratio": rows[0]["keep_ratio"],
            "num_examples": len(rows),
            "utility_accuracy": correct / len(rows) if rows else None,
            "utility_accuracy_num": correct,
            "utility_accuracy_den": len(rows),
            "exact_match": exact / len(rows) if rows else None,
            "exact_match_num": exact,
            "exact_match_den": len(rows),
            "answer_match_fraction": match_sum / len(match_rows) if match_rows else None,
            "answer_match_fraction_den": len(match_rows),
            "longbench_score": score_sum / len(score_rows) if score_rows else None,
            "longbench_score_den": len(score_rows),
            "by_task": by_task,
        }
    return {"by_method": by_method}


def main() -> None:
    args = parse_args()
    methods = parse_csv(args.methods)
    unknown_methods = sorted(set(methods) - VALID_METHODS)
    if unknown_methods:
        raise SystemExit(f"unknown method(s): {', '.join(unknown_methods)}")
    keep_ratios = parse_float_csv(args.keep_ratios)

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = True

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise SystemExit("transformers is not installed in the active environment") from exc

    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but no CUDA device is available")
    device = torch.device(args.device if args.device != "cuda" else "cuda:0")
    dtype = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}[args.dtype]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = Path(args.dataset)
    examples = load_jsonl(dataset_path, args.limit)
    command = " ".join(shlex.quote(part) for part in sys.argv)
    run_config = {
        "run_id": args.run_id,
        "start_time": now_iso(),
        "command": command,
        "git_commit": git_commit_or_null(Path.cwd()) or "null/not_git_repo",
        "model": args.model,
        "dataset": str(dataset_path),
        "limit": args.limit,
        "methods": methods,
        "keep_ratios": keep_ratios,
        "max_new_tokens": args.max_new_tokens,
        "chunk_size": args.chunk_size,
        "seed": args.seed,
        "gpu": gpu_name(),
        "torch_version": torch.__version__,
        "dtype": args.dtype,
        "use_chat_template": args.use_chat_template,
        "attn_implementation": "eager"
        if any(
            method
            in {
                "h2o_recent",
                "snapkv_recent",
                "pyramidkv_recent",
                "authoritykv_snapkv_detected_low_v3",
            }
            for method in methods
        )
        else None,
    }
    write_json(out_dir / "run_config.json", run_config)

    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    model_kwargs: dict[str, Any] = {"torch_dtype": dtype}
    if run_config["attn_implementation"]:
        model_kwargs["attn_implementation"] = run_config["attn_implementation"]
    if args.device == "cuda":
        model_kwargs["device_map"] = {"": 0}
    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
    if args.device != "cuda":
        model.to(device)
    model.eval()

    combinations: list[tuple[str, float]] = []
    for method in methods:
        if method == "fullkv":
            combinations.append((method, 1.0))
        else:
            combinations.extend((method, ratio) for ratio in keep_ratios)

    records: list[dict[str, Any]] = []
    with (out_dir / "predictions.jsonl").open("w", encoding="utf-8") as pred_f:
        for example in examples:
            prompt = example["prompt"]
            if args.use_chat_template and getattr(tokenizer, "chat_template", None):
                prompt = tokenizer.apply_chat_template(
                    [{"role": "user", "content": prompt}],
                    tokenize=False,
                    add_generation_prompt=True,
                )
            input_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
            answers = answers_for(example)
            judge_mode = str(example.get("metadata", {}).get("utility_judge", "contains_any"))
            for method, keep_ratio in combinations:
                result = generate_one(
                    model=model,
                    tokenizer=tokenizer,
                    prompt=prompt,
                    input_ids_list=input_ids,
                    token_spans=[],
                    example={"metadata": {"is_benign": True}},
                    method=method,
                    keep_ratio=keep_ratio,
                    max_new_tokens=args.max_new_tokens,
                    chunk_size=args.chunk_size,
                    device=device,
                )
                judged = judge_output(result["output_text"], answers, judge_mode=judge_mode)
                lb_score = official_longbench_score(
                    str(example.get("task", "unknown")),
                    result["output_text"],
                    answers,
                )
                record = {
                    "example_id": example.get("id"),
                    "source": example.get("source"),
                    "task": example.get("task", "unknown"),
                    "method": method,
                    "keep_ratio": keep_ratio,
                    "answers": answers,
                    "judge_mode": judge_mode,
                    "output_text": result["output_text"],
                    "prompt_tokens": result["prompt_tokens"],
                    "retained_prompt_tokens": result["retained_prompt_tokens"],
                    "generation_tokens": result["generation_tokens"],
                    "error": result.get("error"),
                    "longbench_score": lb_score,
                    **judged,
                }
                records.append(record)
                pred_f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                pred_f.flush()
                if not args.quiet:
                    print(
                        json.dumps(
                            {
                                "example": record["example_id"],
                                "task": record["task"],
                                "method": method,
                                "keep_ratio": keep_ratio,
                                "correct": record["correct"],
                            },
                            sort_keys=True,
                        ),
                        flush=True,
                    )

    metrics = summarize(records)
    metrics["run_id"] = args.run_id
    metrics["end_time"] = now_iso()
    write_json(out_dir / "metrics.json", metrics)
    run_config["end_time"] = metrics["end_time"]
    write_json(out_dir / "run_config.json", run_config)
    print(json.dumps({"run_dir": str(out_dir), "metrics": str(out_dir / "metrics.json")}, sort_keys=True))
    if not args.quiet:
        print(json.dumps(metrics["by_method"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
