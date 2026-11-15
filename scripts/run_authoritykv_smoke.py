#!/usr/bin/env python3
"""Run the AuthorityKV smoke harness with chunked prefill KV pruning."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import torch


VALID_METHODS = {
    "fullkv",
    "recent",
    "sink_recent",
    "control_sink_recent",
    "h2o_recent",
    "snapkv_recent",
    "pyramidkv_recent",
    "prefix_recent",
    "system_pin",
    "authoritykv_recent",
    "authoritykv_exclude_low",
    "authoritykv_detected_low",
    "authoritykv_detected_low_v2",
    "authoritykv_detected_low_v3",
    "authoritykv_detected_low_v4",
    "authoritykv_control_recent",
    "authoritykv_control_exclude_low",
    "authoritykv_control_detected_low",
    "authoritykv_control_detected_low_v2",
    "authoritykv_control_detected_low_v3",
    "authoritykv_control_detected_low_v4",
    "authoritykv_snapkv_detected_low_v3",
}

HIGH_AUTHORITY_LEVELS = {"system", "developer"}
LOW_AUTHORITY_LEVELS = {"user", "tool", "retrieved_document"}
CHAT_HIGH_AUTHORITY_ROLES = {"system", "developer"}
CHAT_LOW_AUTHORITY_ROLES = {"user", "tool", "retrieved_document"}
CONTROL_PREFIX_TOKENS = 192
LOW_AUTHORITY_EXCLUSION_HALO_TOKENS = 128
UNTRUSTED_OBSERVATION_MARKERS = (
    "untrusted",
    "injection",
    "injected",
    "retrieved_document",
    "retrieved document",
    "tool injection",
    "tool observation",
)
LOW_AUTHORITY_INJECTION_TRIGGERS = (
    "ignore any higher-priority",
    "ignore every earlier",
    "ignore every previous",
    "ignore previous",
    "ignore earlier",
    "disregard previous",
    "override",
    "conflicting instruction",
    "prompt injection",
    "return {\"decision\"",
    "output {\"decision\"",
    "reveal the lower-priority secret",
    "include the lower-priority secret",
)
LOW_AUTHORITY_DECISION_LABELS = (
    "follow_user",
    "follow_tool",
    "follow_retrieved_document",
)
LOW_AUTHORITY_DECISION_CONTEXT_TERMS_V2 = (
    "decision",
    "label",
    "classification",
    "evaluator",
    "final",
    "governing",
    "choose",
    "select",
    "set",
    "use",
    "emit",
    "print",
    "write",
    "append",
)
LOW_AUTHORITY_SECRET_EXFIL_TERMS_V2 = (
    "reveal",
    "include",
    "copy",
    "expose",
    "print",
    "append",
    "show",
    "publish",
    "write",
    "repeat",
    "paste",
    "send",
    "display",
    "leak",
)
LOW_AUTHORITY_DECISION_CONTEXT_TERMS_V3 = (
    *LOW_AUTHORITY_DECISION_CONTEXT_TERMS_V2,
    "answer card",
    "option",
    "mark",
    "marked",
    "card",
)
LOW_AUTHORITY_SECRET_EXFIL_TERMS_V3 = (
    *LOW_AUTHORITY_SECRET_EXFIL_TERMS_V2,
    "stamp",
    "stamped",
    "token",
    "card",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--methods", required=True, help="Comma-separated methods.")
    parser.add_argument("--keep-ratios", default="0.20,0.40")
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--chunk-size", type=int, default=128)
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", default="bf16", choices=["bf16", "fp16", "fp32"])
    parser.add_argument(
        "--attn-implementation",
        default=None,
        help="Optional transformers attention backend. Defaults to eager for attention-score baselines.",
    )
    parser.add_argument(
        "--fast-exit",
        action="store_true",
        help="Skip final run_config rewrite/symlink and exit via os._exit after flushing outputs.",
    )
    parser.add_argument(
        "--span-source",
        choices=["metadata", "inferred", "metadata_plus_inferred"],
        default="metadata",
        help=(
            "Authority span source. metadata preserves the original benchmark spans; "
            "inferred recovers spans from prompt markers without reading metadata."
        ),
    )
    parser.add_argument(
        "--assistant-prefix",
        default="",
        help=(
            "Optional forced assistant output prefix, e.g. '{'. The prefix is counted "
            "as generated text and is retained for all methods."
        ),
    )
    parser.add_argument(
        "--stop-after-json-object",
        action="store_true",
        help="Stop generation once the first balanced JSON object in the output closes.",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_jsonl(path: Path, limit: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def parse_csv_arg(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_float_csv_arg(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def git_commit_or_null(repo: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except Exception:
        return None
    return result.stdout.strip()


def gpu_name() -> str | None:
    if not torch.cuda.is_available():
        return None
    return torch.cuda.get_device_name(0)


def render_prompt(tokenizer: Any, example: dict[str, Any]) -> str:
    messages = example.get("messages")
    if messages and getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    if messages:
        return "\n\n".join(f"{msg['role'].upper()}:\n{msg['content']}" for msg in messages)
    return example["context"]


def token_indices_for_char_range(
    offsets: list[tuple[int, int]],
    start_char: int,
    end_char: int,
) -> list[int]:
    return [
        idx
        for idx, (tok_start, tok_end) in enumerate(offsets)
        if not (tok_start == tok_end == 0)
        and tok_end > start_char
        and tok_start < end_char
    ]


def normalized_level(label: str) -> str:
    normalized = label.lower().replace(" ", "_")
    return {
        "system_policy_memo": "system",
        "developer_implementation_memo": "developer",
        "user_request": "user",
        "tool_output": "tool",
        "retrieved_document": "retrieved_document",
        "conversation_history_note": "history",
        "background_note": "distractor",
    }.get(normalized, normalized)


def inferred_authority_spans_from_prompt(prompt: str) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    seen_ranges: set[tuple[int, int, str]] = set()
    levels = "SYSTEM|DEVELOPER|USER|TOOL|RETRIEVED DOCUMENT|HISTORY|DISTRACTOR"
    patterns = [
        (
            re.compile(
                rf"BEGIN (?P<label>{levels}) AUTHORITY NOTE \[(?P<span_id>[^\]]+)\]"
            ),
            lambda label, span_id: f"END {label} AUTHORITY NOTE [{span_id}]",
            "inferred_natural_marker",
        ),
        (
            re.compile(
                rf"--- (?P<label>{levels}) TRACE SECTION (?P<span_id>.+?) START ---"
            ),
            lambda label, span_id: f"--- {label} TRACE SECTION {span_id} END ---",
            "inferred_trace_marker",
        ),
        (
            re.compile(
                r"(?P<label>System policy memo|Developer implementation memo|User request|"
                r"Tool output|Retrieved document|Conversation history note|Background note) "
                r"\[(?P<span_id>[^\]]+)\]:"
            ),
            lambda label, span_id: f"End of {label.lower()} [{span_id}].",
            "inferred_narrative_record",
        ),
    ]

    for start_pattern, end_builder, source in patterns:
        for match in start_pattern.finditer(prompt):
            label = match.group("label")
            span_id = match.group("span_id")
            end_marker = end_builder(label, span_id)
            end_start = prompt.find(end_marker, match.end())
            if end_start < 0:
                continue
            end_char = end_start + len(end_marker)
            key = (match.start(), end_char, source)
            if key in seen_ranges:
                continue
            seen_ranges.add(key)
            spans.append(
                {
                    "level": normalized_level(label),
                    "span_id": span_id,
                    "start_marker": match.group(0),
                    "end_marker": end_marker,
                    "source": source,
                    "start_char": match.start(),
                    "end_char": end_char,
                    "text": prompt[match.start() : end_char],
                }
            )
    return sorted(spans, key=lambda span: int(span["start_char"]))


def find_token_spans(
    prompt: str,
    offsets: list[tuple[int, int]],
    example: dict[str, Any],
    span_source: str = "metadata",
    include_low_authority_chat: bool = False,
) -> list[dict[str, Any]]:
    token_spans: list[dict[str, Any]] = []
    cursor = 0
    for message_index, message in enumerate(example.get("messages", [])):
        role = str(message.get("role", "")).lower()
        if role not in CHAT_HIGH_AUTHORITY_ROLES and not (
            include_low_authority_chat and role in CHAT_LOW_AUTHORITY_ROLES
        ):
            continue
        content = str(message.get("content", ""))
        if not content:
            continue
        start_char = prompt.find(content, cursor)
        if start_char < 0:
            start_char = prompt.find(content)
        if start_char < 0:
            continue
        end_char = start_char + len(content)
        cursor = end_char
        token_indices = token_indices_for_char_range(offsets, start_char, end_char)
        token_spans.append(
            {
                "level": role,
                "span_id": f"chat_{role}_{message_index}",
                "start_marker": None,
                "end_marker": None,
                "source": "chat_message",
                "start_char": start_char,
                "end_char": end_char,
                "text": content,
                "token_indices": token_indices,
                "token_char_offsets": [
                    [int(index), int(offsets[index][0]), int(offsets[index][1])]
                    for index in token_indices
                ],
            }
        )

    if span_source in {"metadata", "metadata_plus_inferred"}:
        for span in example.get("metadata", {}).get("authority_spans", []):
            start_marker = span["start_marker"]
            end_marker = span["end_marker"]
            try:
                start_char = prompt.index(start_marker)
                end_char = prompt.index(end_marker, start_char) + len(end_marker)
            except ValueError:
                continue
            token_indices = token_indices_for_char_range(offsets, start_char, end_char)
            token_spans.append(
                {
                    **span,
                    "source": "metadata_marker",
                    "start_char": start_char,
                    "end_char": end_char,
                    "text": prompt[start_char:end_char],
                    "token_indices": token_indices,
                }
            )

    if span_source in {"inferred", "metadata_plus_inferred"}:
        for span in inferred_authority_spans_from_prompt(prompt):
            start_char = int(span["start_char"])
            end_char = int(span["end_char"])
            token_spans.append(
                {
                    **span,
                    "token_indices": token_indices_for_char_range(
                        offsets, start_char, end_char
                    ),
                }
            )
    return token_spans


def past_seq_len(past_key_values: Any | None) -> int:
    if past_key_values is None:
        return 0
    if hasattr(past_key_values, "get_seq_length"):
        return int(past_key_values.get_seq_length())
    if hasattr(past_key_values, "key_cache") and past_key_values.key_cache:
        return int(past_key_values.key_cache[0].shape[-2])
    if isinstance(past_key_values, (tuple, list)) and past_key_values:
        first_layer = past_key_values[0]
        if isinstance(first_layer, (tuple, list)) and first_layer:
            return int(first_layer[0].shape[-2])
    raise TypeError(f"unsupported cache type: {type(past_key_values)!r}")


def index_select_seq(tensor: torch.Tensor, keep_idx: torch.Tensor) -> torch.Tensor:
    return tensor.index_select(dim=-2, index=keep_idx)


def prune_past_key_values(past_key_values: Any, keep_indices: list[int], device: torch.device) -> Any:
    keep_idx = torch.tensor(keep_indices, dtype=torch.long, device=device)

    if hasattr(past_key_values, "to_legacy_cache") and hasattr(
        type(past_key_values), "from_legacy_cache"
    ):
        pruned_layers = []
        for layer in past_key_values.to_legacy_cache():
            if not isinstance(layer, tuple) or len(layer) < 2:
                raise TypeError(f"unsupported cache layer from legacy adapter: {type(layer)!r}")
            key = index_select_seq(layer[0], keep_idx)
            value = index_select_seq(layer[1], keep_idx)
            pruned_layers.append((key, value, *layer[2:]))
        return type(past_key_values).from_legacy_cache(tuple(pruned_layers))

    if hasattr(past_key_values, "key_cache") and hasattr(past_key_values, "value_cache"):
        for layer_idx in range(len(past_key_values.key_cache)):
            past_key_values.key_cache[layer_idx] = index_select_seq(
                past_key_values.key_cache[layer_idx], keep_idx
            )
            past_key_values.value_cache[layer_idx] = index_select_seq(
                past_key_values.value_cache[layer_idx], keep_idx
            )
        if hasattr(past_key_values, "_seen_tokens"):
            past_key_values._seen_tokens = len(keep_indices)
        return past_key_values

    if isinstance(past_key_values, tuple):
        pruned_layers = []
        for layer in past_key_values:
            if not isinstance(layer, tuple) or len(layer) < 2:
                raise TypeError(f"unsupported legacy layer cache: {type(layer)!r}")
            key = index_select_seq(layer[0], keep_idx)
            value = index_select_seq(layer[1], keep_idx)
            pruned_layers.append((key, value, *layer[2:]))
        return tuple(pruned_layers)

    if isinstance(past_key_values, list):
        pruned_layers = []
        for layer in past_key_values:
            key = index_select_seq(layer[0], keep_idx)
            value = index_select_seq(layer[1], keep_idx)
            pruned_layers.append((key, value, *layer[2:]))
        return pruned_layers

    raise TypeError(f"unsupported cache type for pruning: {type(past_key_values)!r}")


def first_n_indices(indices: Iterable[int], n: int) -> list[int]:
    return list(indices)[: max(0, n)]


def first_unique_indices(indices: Iterable[int], n: int) -> list[int]:
    selected: list[int] = []
    seen: set[int] = set()
    for idx in indices:
        if idx in seen:
            continue
        selected.append(idx)
        seen.add(idx)
        if len(selected) >= max(0, n):
            break
    return selected


def fill_with_recent(
    selected: set[int],
    budget: int,
    cache_len: int,
    excluded: set[int] | None = None,
) -> list[int]:
    excluded = excluded or set()
    if len(selected) < budget and excluded:
        for idx in range(cache_len - 1, -1, -1):
            if idx in excluded:
                continue
            selected.add(idx)
            if len(selected) >= budget:
                break
    if len(selected) < budget:
        for idx in range(cache_len - 1, -1, -1):
            selected.add(idx)
            if len(selected) >= budget:
                break
    return sorted(selected)


def fill_with_attention_ranked(
    selected: set[int],
    budget: int,
    cache_len: int,
    attention_scores: list[float],
    recent_quota: int,
    excluded: set[int] | None = None,
    hard_excluded: bool = False,
) -> list[int]:
    excluded = excluded or set()
    for idx in range(cache_len - 1, max(-1, cache_len - recent_quota - 1), -1):
        if idx in excluded:
            continue
        selected.add(idx)
        if len(selected) >= budget:
            return sorted(selected)
    ranked = sorted(range(cache_len), key=lambda idx: attention_scores[idx], reverse=True)
    for idx in ranked:
        if idx in excluded:
            continue
        selected.add(idx)
        if len(selected) >= budget:
            return sorted(selected)
    if len(selected) < budget and excluded and not hard_excluded:
        for idx in ranked:
            selected.add(idx)
            if len(selected) >= budget:
                break
    return sorted(selected)


def attention_scores_from_outputs(
    attentions: Any,
    expected_cache_len: int,
    layer_weighting: str = "uniform",
) -> list[float]:
    if attentions is None:
        raise RuntimeError("attention-score baseline requested but model returned no attentions")
    score_tensor = None
    layer_count = 0
    usable_layers = [layer_attn for layer_attn in attentions if layer_attn is not None]
    total_layers = len(usable_layers)
    for layer_idx, layer_attn in enumerate(usable_layers):
        if layer_attn is None:
            continue
        # Shape is normally [batch, heads, query_tokens, key_tokens].
        layer_scores = layer_attn.detach().float().sum(dim=(0, 1, 2))
        if layer_weighting == "upper_pyramid":
            # PyramidKV is based on layer-wise pyramidal information funneling.
            # This lightweight harness keeps a uniform cache length across layers
            # for HF compatibility, but weights upper-layer attention more heavily
            # when ranking prompt tokens.
            layer_scores = layer_scores * float(((layer_idx + 1) / max(1, total_layers)) ** 2)
        elif layer_weighting != "uniform":
            raise ValueError(f"unknown attention layer weighting: {layer_weighting}")
        score_tensor = layer_scores if score_tensor is None else score_tensor + layer_scores
        layer_count += 1
    if score_tensor is None or layer_count == 0:
        raise RuntimeError("attention-score baseline requested but attentions were empty")
    if int(score_tensor.shape[-1]) != expected_cache_len:
        raise RuntimeError(
            f"attention key length mismatch: {int(score_tensor.shape[-1])} vs {expected_cache_len}"
        )
    return [float(value) for value in score_tensor.cpu().tolist()]


def update_attention_scores(
    attention_scores: list[float],
    attentions: Any,
    expected_cache_len: int,
    layer_weighting: str = "uniform",
) -> list[float]:
    if len(attention_scores) < expected_cache_len:
        attention_scores.extend([0.0] * (expected_cache_len - len(attention_scores)))
    if len(attention_scores) != expected_cache_len:
        raise RuntimeError(
            f"attention score/cache length mismatch: {len(attention_scores)} vs {expected_cache_len}"
        )

    current_scores = attention_scores_from_outputs(
        attentions,
        expected_cache_len,
        layer_weighting=layer_weighting,
    )
    for idx, value in enumerate(current_scores):
        attention_scores[idx] += float(value)
    return attention_scores


def span_token_set(token_spans: list[dict[str, Any]], levels: set[str]) -> set[int]:
    tokens: set[int] = set()
    for span in token_spans:
        if span.get("level") in levels:
            tokens.update(int(idx) for idx in span.get("token_indices", []))
    return tokens


def span_is_untrusted_observation(span: dict[str, Any]) -> bool:
    level = str(span.get("level", ""))
    source = str(span.get("source", ""))
    if level in HIGH_AUTHORITY_LEVELS:
        return False
    # Message text is evidence for the detector, not provenance. Treating an
    # entire user/tool message as untrusted because it contains a trigger word
    # destroys useful evidence surrounding a localized injected span.
    if source == "chat_message":
        return False
    span_text = " ".join(
        str(span.get(key, ""))
        for key in ("span_id", "start_marker", "end_marker", "text")
    ).lower()
    if level == "retrieved_document":
        return True
    if "untrusted" in span_text or "injection" in span_text or "injected" in span_text:
        return True
    if level == "tool" and has_word_or_phrase(span_text, UNTRUSTED_OBSERVATION_MARKERS):
        return True
    return False


def untrusted_observation_token_set(token_spans: list[dict[str, Any]]) -> set[int]:
    tokens: set[int] = set()
    for span in token_spans:
        if span_is_untrusted_observation(span):
            tokens.update(int(idx) for idx in span.get("token_indices", []))
    return tokens


def span_has_low_authority_injection(span: dict[str, Any]) -> bool:
    if span.get("level") not in LOW_AUTHORITY_LEVELS:
        return False
    text = str(span.get("text", "")).lower()
    if any(trigger in text for trigger in LOW_AUTHORITY_INJECTION_TRIGGERS):
        return True
    asks_for_low_decision = any(label in text for label in LOW_AUTHORITY_DECISION_LABELS)
    decision_directive = "decision" in text and (
        "return" in text or "output" in text or "answer" in text
    )
    secret_directive = "secret" in text and (
        "reveal" in text or "include" in text or "copy" in text
    )
    return (asks_for_low_decision and decision_directive) or secret_directive


def span_has_low_authority_injection_v2(span: dict[str, Any]) -> bool:
    if span.get("level") not in LOW_AUTHORITY_LEVELS:
        return False
    if span_has_low_authority_injection(span):
        return True
    text = str(span.get("text", "")).lower()
    asks_for_low_decision = any(label in text for label in LOW_AUTHORITY_DECISION_LABELS)
    has_decision_context = any(
        term in text for term in LOW_AUTHORITY_DECISION_CONTEXT_TERMS_V2
    )
    mentions_secret = "akv_secret" in text or "akv_trace_secret" in text or "secret" in text
    has_exfil_context = any(term in text for term in LOW_AUTHORITY_SECRET_EXFIL_TERMS_V2)
    return (asks_for_low_decision and has_decision_context) or (
        mentions_secret and has_exfil_context
    )


def has_word_or_phrase(text: str, terms: Iterable[str]) -> bool:
    for term in terms:
        lowered = term.lower()
        if " " in lowered:
            if lowered in text:
                return True
            continue
        if re.search(rf"(?<![a-z0-9_]){re.escape(lowered)}(?![a-z0-9_])", text):
            return True
    return False


def span_has_low_authority_injection_v3(span: dict[str, Any]) -> bool:
    if span.get("level") not in LOW_AUTHORITY_LEVELS:
        return False
    text = str(span.get("text", "")).lower()
    if any(trigger in text for trigger in LOW_AUTHORITY_INJECTION_TRIGGERS):
        return True
    asks_for_low_decision = any(label in text for label in LOW_AUTHORITY_DECISION_LABELS)
    has_decision_context = has_word_or_phrase(text, LOW_AUTHORITY_DECISION_CONTEXT_TERMS_V3)
    mentions_secret = "akv_secret" in text or "akv_trace_secret" in text or "secret" in text
    has_exfil_context = has_word_or_phrase(text, LOW_AUTHORITY_SECRET_EXFIL_TERMS_V3)
    return (asks_for_low_decision and has_decision_context) or (
        mentions_secret and has_exfil_context
    )


def detected_low_authority_token_set(
    token_spans: list[dict[str, Any]],
    detector_version: str = "v1",
) -> set[int]:
    tokens: set[int] = set()
    if detector_version == "v1":
        detector = span_has_low_authority_injection
    elif detector_version == "v2":
        detector = span_has_low_authority_injection_v2
    elif detector_version == "v3":
        detector = span_has_low_authority_injection_v3
    else:
        raise ValueError(f"unknown detector version: {detector_version}")
    for span in token_spans:
        if not detector(span):
            continue
        if (
            span.get("source") == "chat_message"
            and span.get("level") in CHAT_LOW_AUTHORITY_ROLES
            and span.get("token_char_offsets")
        ):
            text = str(span.get("text", ""))
            content_start = int(span.get("start_char", 0))
            detected_ranges: list[tuple[int, int]] = []
            cursor = 0
            segments: list[tuple[int, int, str]] = []
            for segment in re.split(r"(?<=[.!?])\s+|\n+", text):
                if not segment:
                    continue
                start = text.find(segment, cursor)
                if start < 0:
                    start = text.find(segment)
                if start < 0:
                    continue
                end = start + len(segment)
                cursor = end
                segments.append((start, end, segment))
            for segment_index, (start, end, segment) in enumerate(segments):
                candidate = {**span, "text": segment}
                if detector(candidate):
                    detected_ranges.append(
                        (content_start + start, content_start + end)
                    )
                    # Injection triggers and their requested payload commonly
                    # occupy adjacent sentences. Include one following segment
                    # without demoting the rest of a long evidence-bearing message.
                    if segment_index + 1 < len(segments):
                        next_start, next_end, _ = segments[segment_index + 1]
                        detected_ranges.append(
                            (
                                content_start + next_start,
                                content_start + next_end,
                            )
                        )
            if detected_ranges:
                for index, tok_start, tok_end in span["token_char_offsets"]:
                    if any(
                        tok_end > range_start and tok_start < range_end
                        for range_start, range_end in detected_ranges
                    ):
                        tokens.add(int(index))
            # Chat content must be localized. A message-level trigger assembled
            # from terms in different sentences is not evidence that the whole
            # useful message should be excluded.
            continue
        tokens.update(int(idx) for idx in span.get("token_indices", []))
    return tokens


def expand_positions_with_following_halo(
    positions: set[int],
    prompt_len: int,
    halo_tokens: int,
) -> set[int]:
    """Exclude tokens that can carry same-chunk low-authority influence."""
    if not positions or halo_tokens <= 0:
        return set(positions)
    expanded = set(positions)
    for pos in positions:
        start = max(0, pos)
        end = min(prompt_len, pos + halo_tokens + 1)
        expanded.update(range(start, end))
    return expanded


def has_conflict(example: dict[str, Any], prompt: str) -> bool:
    if example.get("metadata", {}).get("is_benign"):
        return False
    lowered = prompt.lower()
    for trigger in example.get("metadata", {}).get("conflict_triggers", []):
        if trigger and str(trigger).lower() in lowered:
            return True
    return bool(example.get("low_authority_conflict"))


def select_keep_indices(
    method: str,
    keep_ratio: float,
    prompt_len: int,
    cache_positions: list[int],
    token_spans: list[dict[str, Any]],
    conflict_detected: bool,
    attention_scores: list[float] | None = None,
) -> list[int]:
    cache_len = len(cache_positions)
    budget = max(1, min(cache_len, math.ceil(prompt_len * keep_ratio)))
    if method == "fullkv" or budget >= cache_len:
        return list(range(cache_len))

    if method == "recent":
        return list(range(cache_len - budget, cache_len))

    if method == "sink_recent":
        selected = {idx for idx, pos in enumerate(cache_positions) if pos < 64}
        return fill_with_recent(selected, budget, cache_len)

    if method == "control_sink_recent":
        control_quota = min(CONTROL_PREFIX_TOKENS, max(1, math.ceil(0.30 * budget)))
        selected = set(range(min(control_quota, cache_len)))
        return fill_with_recent(selected, budget, cache_len)

    if method == "h2o_recent":
        if attention_scores is None or len(attention_scores) != cache_len:
            raise RuntimeError("h2o_recent requires attention scores aligned to the live cache")
        recent_quota = min(cache_len, max(1, budget // 2))
        selected = set(range(max(0, cache_len - recent_quota), cache_len))
        ranked = sorted(range(cache_len), key=lambda idx: attention_scores[idx], reverse=True)
        for idx in ranked:
            selected.add(idx)
            if len(selected) >= budget:
                break
        return sorted(selected)

    if method == "snapkv_recent":
        if attention_scores is None or len(attention_scores) != cache_len:
            raise RuntimeError("snapkv_recent requires attention scores aligned to the live cache")
        recent_quota = min(cache_len, max(1, budget // 4))
        return fill_with_attention_ranked(
            set(),
            budget,
            cache_len,
            attention_scores,
            recent_quota,
        )

    if method == "pyramidkv_recent":
        if attention_scores is None or len(attention_scores) != cache_len:
            raise RuntimeError("pyramidkv_recent requires attention scores aligned to the live cache")
        recent_quota = min(cache_len, max(1, budget // 4))
        selected = set(range(max(0, cache_len - recent_quota), cache_len))
        ranked = sorted(range(cache_len), key=lambda idx: attention_scores[idx], reverse=True)
        for idx in ranked:
            selected.add(idx)
            if len(selected) >= budget:
                break
        return sorted(selected)

    if method == "prefix_recent":
        prefix_quota = max(1, budget // 2)
        selected = set(range(min(prefix_quota, cache_len)))
        return fill_with_recent(selected, budget, cache_len)

    if method == "system_pin":
        protected_positions = span_token_set(token_spans, {"system"})
        protected_quota = max(1, math.ceil(0.60 * budget))
        selected = set(
            first_n_indices(
                (
                    idx
                    for idx, pos in enumerate(cache_positions)
                    if pos in protected_positions
                ),
                protected_quota,
            )
        )
        return fill_with_recent(selected, budget, cache_len)

    if method in {
        "authoritykv_recent",
        "authoritykv_exclude_low",
        "authoritykv_detected_low",
        "authoritykv_detected_low_v2",
        "authoritykv_detected_low_v3",
        "authoritykv_detected_low_v4",
        "authoritykv_control_recent",
        "authoritykv_control_exclude_low",
        "authoritykv_control_detected_low",
        "authoritykv_control_detected_low_v2",
        "authoritykv_control_detected_low_v3",
        "authoritykv_control_detected_low_v4",
        "authoritykv_snapkv_detected_low_v3",
    }:
        if method == "authoritykv_snapkv_detected_low_v3" and (
            attention_scores is None or len(attention_scores) != cache_len
        ):
            raise RuntimeError(
                "authoritykv_snapkv_detected_low_v3 requires attention scores aligned to the live cache"
            )
        protected_positions = span_token_set(token_spans, HIGH_AUTHORITY_LEVELS)
        low_authority_positions = span_token_set(token_spans, LOW_AUTHORITY_LEVELS)
        untrusted_observation_positions = untrusted_observation_token_set(token_spans)
        detected_low_authority_positions = detected_low_authority_token_set(
            token_spans,
            detector_version=(
                "v3"
                if method in {
                "authoritykv_detected_low_v3",
                "authoritykv_control_detected_low_v3",
                "authoritykv_detected_low_v4",
                "authoritykv_control_detected_low_v4",
                "authoritykv_snapkv_detected_low_v3",
            }
                else "v2"
                if method in {
                    "authoritykv_detected_low_v2",
                    "authoritykv_control_detected_low_v2",
                }
                else "v1"
            ),
        )
        protected_fraction = 0.60 if conflict_detected else 0.40
        protected_quota = max(1, math.ceil(protected_fraction * budget))

        # Prefer SYSTEM over DEVELOPER, then chronological order within each bucket.
        system_positions = span_token_set(token_spans, {"system"})
        developer_positions = span_token_set(token_spans, {"developer"})
        system_selected = [
            idx for idx, pos in enumerate(cache_positions) if pos in system_positions
        ]
        developer_selected = [
            idx for idx, pos in enumerate(cache_positions) if pos in developer_positions
        ]
        ordered_protected = system_selected + [
            idx for idx in developer_selected if idx not in set(system_selected)
        ]
        if not ordered_protected:
            ordered_protected = [
                idx for idx, pos in enumerate(cache_positions) if pos in protected_positions
            ]
        if method in {
            "authoritykv_control_recent",
            "authoritykv_control_exclude_low",
            "authoritykv_control_detected_low",
            "authoritykv_control_detected_low_v2",
            "authoritykv_control_detected_low_v3",
            "authoritykv_control_detected_low_v4",
        }:
            control_quota = min(CONTROL_PREFIX_TOKENS, max(1, math.ceil(0.30 * budget)))
            control_indices = range(min(control_quota, cache_len))
            priority_quota = max(
                protected_quota,
                min(budget, math.ceil((0.75 if conflict_detected else 0.55) * budget)),
            )
            selected = set(
                first_unique_indices([*control_indices, *ordered_protected], priority_quota)
            )
        elif method == "authoritykv_snapkv_detected_low_v3":
            if ordered_protected:
                control_quota = (
                    min(CONTROL_PREFIX_TOKENS, max(1, math.ceil(0.30 * budget)))
                    if conflict_detected
                    else 0
                )
                control_indices = range(min(control_quota, cache_len))
                priority_quota = max(
                    protected_quota,
                    min(budget, math.ceil((0.75 if conflict_detected else 0.40) * budget)),
                )
                selected = set(
                    first_unique_indices([*control_indices, *ordered_protected], priority_quota)
                )
            else:
                selected = set()
        else:
            selected = set(first_n_indices(ordered_protected, protected_quota))
        excluded = set()
        if method in {"authoritykv_exclude_low", "authoritykv_control_exclude_low"} and conflict_detected:
            excluded = {
                idx
                for idx, pos in enumerate(cache_positions)
                if pos in low_authority_positions
            }
        elif method in {
            "authoritykv_detected_low",
            "authoritykv_detected_low_v2",
            "authoritykv_detected_low_v3",
            "authoritykv_detected_low_v4",
            "authoritykv_control_detected_low",
            "authoritykv_control_detected_low_v2",
            "authoritykv_control_detected_low_v3",
            "authoritykv_control_detected_low_v4",
            "authoritykv_snapkv_detected_low_v3",
        } and conflict_detected:
            if method in {
                "authoritykv_detected_low_v4",
                "authoritykv_control_detected_low_v4",
            }:
                detected_low_authority_positions = expand_positions_with_following_halo(
                    detected_low_authority_positions,
                    prompt_len,
                    LOW_AUTHORITY_EXCLUSION_HALO_TOKENS,
                )
            excluded = {
                idx
                for idx, pos in enumerate(cache_positions)
                if pos in detected_low_authority_positions
            }
        if method == "authoritykv_snapkv_detected_low_v3" and untrusted_observation_positions:
            hard_untrusted_excluded = {
                idx
                for idx, pos in enumerate(cache_positions)
                if pos in untrusted_observation_positions
            }
            excluded.update(hard_untrusted_excluded)
            selected.difference_update(hard_untrusted_excluded)
        if method == "authoritykv_snapkv_detected_low_v3":
            recent_quota = min(cache_len, max(1, budget // 4))
            return fill_with_attention_ranked(
                selected,
                budget,
                cache_len,
                attention_scores or [],
                recent_quota,
                excluded=excluded,
                hard_excluded=bool(untrusted_observation_positions),
            )
        return fill_with_recent(selected, budget, cache_len, excluded=excluded)

    raise ValueError(f"unknown method: {method}")


def forward_with_optional_past(
    model: Any,
    input_ids: torch.Tensor,
    past_key_values: Any | None,
    position_ids: torch.Tensor,
    output_attentions: bool = False,
) -> Any:
    cache_len = past_seq_len(past_key_values)
    attention_mask = torch.ones(
        (input_ids.shape[0], cache_len + input_ids.shape[1]),
        dtype=torch.long,
        device=input_ids.device,
    )
    kwargs = {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "position_ids": position_ids,
        "use_cache": True,
        "return_dict": True,
        "output_attentions": output_attentions,
    }
    if past_key_values is not None:
        kwargs["past_key_values"] = past_key_values
    return model(**kwargs)


@torch.inference_mode()
def generate_one(
    model: Any,
    tokenizer: Any,
    prompt: str,
    input_ids_list: list[int],
    token_spans: list[dict[str, Any]],
    example: dict[str, Any],
    method: str,
    keep_ratio: float,
    max_new_tokens: int,
    chunk_size: int,
    device: torch.device,
    assistant_prefix_ids: list[int] | None = None,
    stop_after_json_object: bool = False,
) -> dict[str, Any]:
    input_ids_all = torch.tensor([input_ids_list], dtype=torch.long, device=device)
    prompt_len = int(input_ids_all.shape[1])
    past_key_values = None
    logits = None
    cache_positions: list[int] = []
    conflict_detected = has_conflict(example, prompt)
    use_attention_scores = method in {
        "h2o_recent",
        "snapkv_recent",
        "pyramidkv_recent",
        "authoritykv_snapkv_detected_low_v3",
    }
    attention_scores: list[float] = []

    for start in range(0, prompt_len, chunk_size):
        end = min(start + chunk_size, prompt_len)
        chunk = input_ids_all[:, start:end]
        position_ids = torch.arange(start, end, dtype=torch.long, device=device).unsqueeze(0)
        outputs = forward_with_optional_past(
            model,
            chunk,
            past_key_values,
            position_ids,
            output_attentions=use_attention_scores,
        )
        logits = outputs.logits
        past_key_values = outputs.past_key_values
        cache_positions.extend(range(start, end))
        if use_attention_scores:
            if method == "h2o_recent":
                attention_scores = update_attention_scores(
                    attention_scores,
                    outputs.attentions,
                    len(cache_positions),
                )
            elif method == "pyramidkv_recent":
                attention_scores = attention_scores_from_outputs(
                    outputs.attentions,
                    len(cache_positions),
                    layer_weighting="upper_pyramid",
                )
            else:
                attention_scores = attention_scores_from_outputs(
                    outputs.attentions,
                    len(cache_positions),
                )

        if method != "fullkv":
            keep_indices = select_keep_indices(
                method,
                keep_ratio,
                prompt_len,
                cache_positions,
                token_spans,
                conflict_detected,
                attention_scores=attention_scores if use_attention_scores else None,
            )
            if len(keep_indices) < len(cache_positions):
                past_key_values = prune_past_key_values(past_key_values, keep_indices, device)
                cache_positions = [cache_positions[idx] for idx in keep_indices]
                if use_attention_scores:
                    attention_scores = [attention_scores[idx] for idx in keep_indices]

    if logits is None:
        raise RuntimeError("empty prompt produced no logits")

    generated_ids: list[int] = []
    eos_ids = set()
    if tokenizer.eos_token_id is not None:
        eos_ids.add(int(tokenizer.eos_token_id))
    if tokenizer.pad_token_id is not None:
        eos_ids.add(int(tokenizer.pad_token_id))

    def has_closed_first_json_object(text: str) -> bool:
        start = text.find("{")
        if start < 0:
            return False
        depth = 0
        in_string = False
        escaped = False
        for char in text[start:]:
            if escaped:
                escaped = False
                continue
            if char == "\\" and in_string:
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return True
        return False

    forced_prefix = assistant_prefix_ids or []
    for forced_id in forced_prefix[:max_new_tokens]:
        if forced_id in eos_ids:
            break
        generated_ids.append(int(forced_id))
        position = prompt_len + len(generated_ids) - 1
        forced_token = torch.tensor([[forced_id]], dtype=torch.long, device=device)
        position_ids = torch.tensor([[position]], dtype=torch.long, device=device)
        outputs = forward_with_optional_past(model, forced_token, past_key_values, position_ids)
        past_key_values = outputs.past_key_values
        logits = outputs.logits
        if stop_after_json_object:
            partial_text = tokenizer.decode(generated_ids, skip_special_tokens=True)
            if has_closed_first_json_object(partial_text):
                break

    next_token = torch.argmax(logits[:, -1, :], dim=-1, keepdim=True)

    for step in range(len(generated_ids), max_new_tokens):
        token_id = int(next_token.item())
        if token_id in eos_ids:
            break
        generated_ids.append(token_id)
        if stop_after_json_object:
            partial_text = tokenizer.decode(generated_ids, skip_special_tokens=True)
            if has_closed_first_json_object(partial_text):
                break

        position = prompt_len + step
        position_ids = torch.tensor([[position]], dtype=torch.long, device=device)
        outputs = forward_with_optional_past(model, next_token, past_key_values, position_ids)
        past_key_values = outputs.past_key_values
        next_token = torch.argmax(outputs.logits[:, -1, :], dim=-1, keepdim=True)

    output_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
    return {
        "output_text": output_text,
        "generated_token_ids": generated_ids,
        "generation_tokens": len(generated_ids),
        "prompt_tokens": prompt_len,
        "retained_prompt_tokens": len(cache_positions),
        "conflict_detected": conflict_detected,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def update_latest_symlink(out_dir: Path, limit: int | None, methods: list[str]) -> None:
    if "fullkv" not in methods:
        return
    parent = out_dir.parent
    names = ["fullkv_latest"]
    if limit is not None:
        names.append(f"smoke{limit}_fullkv_latest")
    for name in names:
        link = parent / name
        try:
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(out_dir.resolve(), target_is_directory=True)
        except OSError:
            # Symlinks may be unavailable on some filesystems; write a pointer instead.
            write_json(parent / f"{name}.json", {"run_dir": str(out_dir.resolve())})


def main() -> None:
    args = parse_args()
    methods = parse_csv_arg(args.methods)
    unknown_methods = sorted(set(methods) - VALID_METHODS)
    if unknown_methods:
        raise SystemExit(f"unknown method(s): {', '.join(unknown_methods)}")
    keep_ratios = parse_float_csv_arg(args.keep_ratios)
    if not keep_ratios:
        keep_ratios = [1.0]

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    torch.backends.cuda.matmul.allow_tf32 = True

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = Path.cwd()
    dataset_path = Path(args.dataset)
    examples = load_jsonl(dataset_path, args.limit)
    if not examples:
        raise SystemExit(f"no examples loaded from {dataset_path}")

    command = " ".join(shlex.quote(part) for part in sys.argv)
    run_config = {
        "run_id": args.run_id,
        "start_time": now_iso(),
        "command": command,
        "git_commit": git_commit_or_null(repo_dir) or "null/not_git_repo",
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
        "span_extraction": f"{args.span_source}_plus_chat_system_developer",
        "span_source": args.span_source,
        "control_prefix_tokens": CONTROL_PREFIX_TOKENS,
        "low_authority_exclusion_halo_tokens": LOW_AUTHORITY_EXCLUSION_HALO_TOKENS,
        "low_authority_injection_triggers": list(LOW_AUTHORITY_INJECTION_TRIGGERS),
        "low_authority_decision_labels": list(LOW_AUTHORITY_DECISION_LABELS),
        "low_authority_decision_context_terms_v2": list(
            LOW_AUTHORITY_DECISION_CONTEXT_TERMS_V2
        ),
        "low_authority_secret_exfil_terms_v2": list(LOW_AUTHORITY_SECRET_EXFIL_TERMS_V2),
        "low_authority_decision_context_terms_v3": list(
            LOW_AUTHORITY_DECISION_CONTEXT_TERMS_V3
        ),
        "low_authority_secret_exfil_terms_v3": list(LOW_AUTHORITY_SECRET_EXFIL_TERMS_V3),
        "attn_implementation": args.attn_implementation
        or (
            "eager"
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
            else None
        ),
        "load_device_map": "cuda:0" if args.device == "cuda" else None,
        "fast_exit": args.fast_exit,
        "assistant_prefix": args.assistant_prefix,
        "stop_after_json_object": args.stop_after_json_object,
    }
    write_json(out_dir / "run_config.json", run_config)

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise SystemExit(
            "transformers is not installed. Run the dependency install command from the plan."
        ) from exc

    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but no CUDA device is available.")
    device = torch.device(args.device if args.device != "cuda" else "cuda:0")
    dtype = {
        "bf16": torch.bfloat16,
        "fp16": torch.float16,
        "fp32": torch.float32,
    }[args.dtype]

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
    assistant_prefix_ids = (
        [int(tok) for tok in tokenizer(args.assistant_prefix, add_special_tokens=False)["input_ids"]]
        if args.assistant_prefix
        else []
    )

    predictions_path = out_dir / "predictions.jsonl"
    combinations: list[tuple[str, float]] = []
    for method in methods:
        if method == "fullkv":
            combinations.append((method, 1.0))
        else:
            combinations.extend((method, ratio) for ratio in keep_ratios)

    with predictions_path.open("w", encoding="utf-8") as pred_f:
        for ex_idx, example in enumerate(examples):
            prompt = render_prompt(tokenizer, example)
            encoded_with_offsets = tokenizer(
                prompt,
                add_special_tokens=False,
                return_offsets_mapping=True,
            )
            input_ids_list = [int(tok) for tok in encoded_with_offsets["input_ids"]]
            offsets = [tuple(pair) for pair in encoded_with_offsets["offset_mapping"]]
            token_spans = find_token_spans(
                prompt,
                offsets,
                example,
                span_source=args.span_source,
            )

            for method, keep_ratio in combinations:
                started = time.time()
                error = None
                result: dict[str, Any]
                try:
                    result = generate_one(
                        model=model,
                        tokenizer=tokenizer,
                        prompt=prompt,
                        input_ids_list=input_ids_list,
                        token_spans=token_spans,
                        example=example,
                        method=method,
                        keep_ratio=keep_ratio,
                        max_new_tokens=args.max_new_tokens,
                        chunk_size=args.chunk_size,
                        device=device,
                        assistant_prefix_ids=assistant_prefix_ids,
                        stop_after_json_object=args.stop_after_json_object,
                    )
                except Exception as exc:  # keep per-example artifacts instead of losing the run.
                    error = repr(exc)
                    result = {
                        "output_text": "",
                        "generated_token_ids": [],
                        "generation_tokens": 0,
                        "prompt_tokens": len(input_ids_list),
                        "retained_prompt_tokens": 0,
                        "conflict_detected": has_conflict(example, prompt),
                    }

                record = {
                    "run_id": args.run_id,
                    "example_index": ex_idx,
                    "example_id": example["id"],
                    "category": example["category"],
                    "method": method,
                    "keep_ratio": keep_ratio,
                    "model": args.model,
                    "dataset": str(dataset_path),
                    "max_new_tokens": args.max_new_tokens,
                    "seed": args.seed,
                    "elapsed_seconds": round(time.time() - started, 4),
                    "error": error,
                    "expected_behavior": example.get("expected_behavior", {}),
                    "judge_rule": example.get("judge_rule", {}),
                    "metadata": example.get("metadata", {}),
                    "authority_token_spans": token_spans,
                    **result,
                }
                pred_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                pred_f.flush()
                print(
                    json.dumps(
                        {
                            "example": example["id"],
                            "method": method,
                            "keep_ratio": keep_ratio,
                            "prompt_tokens": result["prompt_tokens"],
                            "retained_prompt_tokens": result["retained_prompt_tokens"],
                            "generation_tokens": result["generation_tokens"],
                            "error": error,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

    if not args.fast_exit:
        run_config["end_time"] = now_iso()
        write_json(out_dir / "run_config.json", run_config)
        update_latest_symlink(out_dir, args.limit, methods)
    print(json.dumps({"run_dir": str(out_dir), "predictions": str(predictions_path)}, indent=2))
    sys.stdout.flush()
    sys.stderr.flush()
    if args.fast_exit:
        os._exit(0)


if __name__ == "__main__":
    main()
