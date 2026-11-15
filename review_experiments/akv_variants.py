r"""P / D construction for the variants of the review-period experiments. Frozen functions are imported (never copied); new variants are
independent functions with their names recorded in config.json.

Variant catalogue (method name = f"authority_{scorer}_{variant}" unless noted):
  base            official press (method f"kvpress_{scorer}") or "fullkv"           label: none
  full            frozen make_press(f"authority_{scorer}_detected_provenance")   label: DETECTOR (annotated boundaries) [IH]
  rp              frozen make_press(f"authority_{scorer}_provenance")            label: DETECTOR (lexical tool gating)
  pin / system_pin / all_control_pin / detected  frozen make_press names
  rpstrict        P = level∈{system,developer}; D = level∈{tool,retrieved_document} (all sources; no text rule; no detector)
                  label: DEPLOYABLE (typed roles + provenance; boundaries from the benchmark annotation)
  e3bdet          rpstrict + D_extra = sentences of user/tool chat messages flagged by span_has_low_authority_injection_v3
                  (each sentence judged alone; fixed splitter)                    label: DETECTOR (annotation-free)
  e3bclfdeberta / e3bclfpg2   rpstrict + D_extra = sentences flagged by the classifier   label: DETECTOR (annotation-free)
  e4det / e4clfdeberta / e4clfpg2   mixed-evidence: P = chat system/developer; D = flagged sentences inside the retrieved
                  region only ("Passage" .. last "Question:"); metadata.authority_spans NOT used
Sentence splitter (PREREG-05/06): re.split(r"(?<=[.!?])\s+|\n+", text) — the frozen detector's regex.
"""

from __future__ import annotations

import re
from typing import Any, Callable

SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
LOW_CHAT_ROLES = {"user", "tool", "retrieved_document"}


def sentences_with_offsets(text: str) -> list[tuple[int, int, str]]:
    """Return (start, end, sentence) for the fixed splitter, offsets relative to `text` (same walk as the frozen code)."""

    segments: list[tuple[int, int, str]] = []
    cursor = 0
    for segment in SPLIT_RE.split(text):
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
    return segments


def tokens_for_ranges(offsets: list[tuple[int, int]], ranges: list[tuple[int, int]]) -> set[int]:
    out: set[int] = set()
    if not ranges:
        return out
    for idx, (ts, te) in enumerate(offsets):
        if ts == te == 0:
            continue
        for rs, re_ in ranges:
            if te > rs and ts < re_:
                out.add(idx)
                break
    return out


def chat_message_ranges(context_text: str, example: dict[str, Any], roles: set[str]) -> list[dict[str, Any]]:
    """Locate chat messages of the given roles in the rendered prompt (same search as frozen find_token_spans)."""

    found = []
    cursor = 0
    for i, m in enumerate(example.get("messages", [])):
        role = str(m.get("role", "")).lower()
        content = str(m.get("content", ""))
        if not content:
            continue
        start = context_text.find(content, cursor)
        if start < 0:
            start = context_text.find(content)
        if start < 0:
            continue
        cursor = start + len(content)
        if role in roles:
            found.append({"role": role, "index": i, "start": start, "end": start + len(content), "text": content})
    return found


def retrieved_region(user_text: str) -> tuple[int, int] | None:
    """Mixed-evidence retrieved source: from the first 'Passage' heading to the last 'Question:' (PREREG-06)."""

    m = re.search(r"Passage( \d+)?:\n", user_text)
    q = user_text.rfind("Question:")
    if not m or q < 0 or q <= m.start():
        return None
    return m.start(), q


def flagged_sentence_tokens(
    context_text: str,
    offsets: list[tuple[int, int]],
    example: dict[str, Any],
    judge: Callable[[str], bool],
    *,
    roles: set[str],
    region: str = "message",
) -> tuple[set[int], dict[str, Any]]:
    """Annotation-free D: split each chat message of `roles` (or only its retrieved region) into sentences; judge each
    sentence alone; D = tokens covered by flagged sentences. Returns (token set, audit)."""

    audit = {"messages": 0, "sentences": 0, "flagged": 0, "flagged_sentences": [], "region_missing": 0}
    ranges: list[tuple[int, int]] = []
    for msg in chat_message_ranges(context_text, example, roles):
        audit["messages"] += 1
        text = msg["text"]
        base = msg["start"]
        lo, hi = 0, len(text)
        if region == "retrieved":
            rr = retrieved_region(text)
            if rr is None:
                audit["region_missing"] += 1
                continue
            lo, hi = rr
        sub = text[lo:hi]
        for s, e, sent in sentences_with_offsets(sub):
            audit["sentences"] += 1
            if judge(sent):
                audit["flagged"] += 1
                if len(audit["flagged_sentences"]) < 12:
                    audit["flagged_sentences"].append(sent[:160])
                ranges.append((base + lo + s, base + lo + e))
    return tokens_for_ranges(offsets, ranges), audit


class ClassifierJudge:
    """Sequence classifier wrapper: injection iff argmax == injection_index (PREREG-05/06 + amendments A/B/C)."""

    def __init__(self, model_id: str, revision: str, injection_index: int, device: str = "cuda", max_length: int = 512):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.model_id, self.revision, self.injection_index, self.max_length = model_id, revision, injection_index, max_length
        self.tok = AutoTokenizer.from_pretrained(model_id, revision=revision)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id, revision=revision, dtype=torch.float32).to(device).eval()
        self.device = device
        self.id2label = dict(getattr(self.model.config, "id2label", {}) or {})
        self.n_calls = 0
        self.n_truncated = 0
        self.cache: dict[str, bool] = {}

    def __call__(self, sentence: str) -> bool:
        import torch

        if sentence in self.cache:
            return self.cache[sentence]
        enc_full = self.tok(sentence, return_tensors="pt", truncation=False)
        if enc_full["input_ids"].shape[1] > self.max_length:
            self.n_truncated += 1
        enc = self.tok(sentence, return_tensors="pt", truncation=True, max_length=self.max_length).to(self.device)
        with torch.no_grad():
            logits = self.model(**enc).logits[0]
        self.n_calls += 1
        flag = int(logits.argmax()) == self.injection_index
        self.cache[sentence] = flag
        return flag

    def audit(self) -> dict[str, Any]:
        return {"model": self.model_id, "revision": self.revision, "id2label_from_config": self.id2label, "injection_index": self.injection_index,
                "rule": "argmax == injection_index", "max_length": self.max_length, "n_calls": self.n_calls, "n_truncated": self.n_truncated}


CLASSIFIERS = {
    "deberta": {"model": "protectai/deberta-v3-base-prompt-injection-v2", "revision": "90c9989b1a342275dd0d1a95aad283c04e075671", "injection_index": 1,
                "label_note": "id2label {0: SAFE, 1: INJECTION} from local config (PREREG-05/06 amendment A)"},
    "pg2": {"model": "meta-llama/Llama-Prompt-Guard-2-86M", "revision": "a8ded8e697ce7c355e395a0df51f94adb4a2fd27", "injection_index": 1,
            "label_note": "label index set by pre-registered probe; local config has no id2label (PREREG-05/06 amendments B/C)"},
}


def detector_v3_judge(smoke_module) -> Callable[[str], bool]:
    def judge(sentence: str) -> bool:
        return bool(smoke_module.span_has_low_authority_injection_v3({"level": "user", "text": sentence}))
    return judge


def build_sets(
    variant: str,
    scorer: str,
    token_spans: list[dict[str, Any]],
    context_text: str,
    offsets: list[tuple[int, int]],
    example: dict[str, Any],
    smoke_module,
    judges: dict[str, Callable[[str], bool]],
) -> tuple[set[int], set[int], dict[str, Any]]:
    """Return (P, D, audit) for the new variants. Frozen-name variants are handled by the caller via make_press."""

    P = set(smoke_module.span_token_set(token_spans, {"system", "developer"}))
    audit: dict[str, Any] = {"variant": variant}
    if variant == "rpstrict":
        D = set(smoke_module.span_token_set(token_spans, {"tool", "retrieved_document"}))
        audit["D_rule"] = "level in {tool, retrieved_document}, any source, no text rule, no detector"
    elif variant in ("e3bdet", "e3bclfdeberta", "e3bclfpg2"):
        D = set(smoke_module.span_token_set(token_spans, {"tool", "retrieved_document"}))
        key = {"e3bdet": "detv3", "e3bclfdeberta": "deberta", "e3bclfpg2": "pg2"}[variant]
        extra, a = flagged_sentence_tokens(context_text, offsets, example, judges[key], roles={"user", "tool"}, region="message")
        audit.update({"D_rule": "rpstrict + flagged sentences of user/tool chat messages", "judge": key, "sentence_audit": a, "D_extra_tokens": len(extra)})
        D |= extra
    elif variant in ("e4det", "e4clfdeberta", "e4clfpg2"):
        key = {"e4det": "detv3", "e4clfdeberta": "deberta", "e4clfpg2": "pg2"}[variant]
        extra, a = flagged_sentence_tokens(context_text, offsets, example, judges[key], roles={"user"}, region="retrieved")
        audit.update({"D_rule": "flagged sentences inside the retrieved region of the user message; metadata.authority_spans not used", "judge": key, "sentence_audit": a, "D_extra_tokens": len(extra)})
        D = extra
        # P from chat roles only (mixed-evidence has no system/developer metadata spans, so identical to make_press's P)
        P = {i for s in token_spans if s.get("source") == "chat_message" and s.get("level") in ("system", "developer") for i in s["token_indices"]}
    else:
        raise ValueError(f"unknown new variant {variant}")
    D -= P
    audit["P_size"] = len(P)
    audit["D_size"] = len(D)
    return P, D, audit
