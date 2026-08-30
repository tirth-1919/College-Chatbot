'''Student-facing response-depth policy for the AIT assistant.

This module is deliberately provider-agnostic: routing and factual grounding stay
in SourceResolver while this policy only selects how much explanation to request.
'''
from enum import Enum
import re
class ResponseDepth(str, Enum):
    SHORT = "short"
    NORMAL = "normal"
    DETAILED = "detailed"
    DEEP = "deep"

_EXPLICIT = (
    (ResponseDepth.SHORT, ("one line", "briefly", "short answer", "keep it short")),
    (ResponseDepth.DEEP, ("step by step", "explain everything")),
    (ResponseDepth.DETAILED, ("explain in detail", "give detailed answer", "with examples", "with example")),
    (ResponseDepth.NORMAL, ("explain clearly", "explain")),
)


def select_response_depth(query: str, previous_depth: ResponseDepth | None = None) -> ResponseDepth:
    # Explicit wording takes precedence over automatic complexity heuristics.""
    text = re.sub(r"\s+", " ", (query or "").strip().lower())
    if "tell me more" in text:
        return ResponseDepth.DETAILED if previous_depth in (None, ResponseDepth.SHORT, ResponseDepth.NORMAL) else ResponseDepth.DEEP
    for depth, phrases in _EXPLICIT:
        if any(phrase in text for phrase in phrases):
            return depth
    if any(word in text for word in ("compare", "subjects", "documents", "examples")):
        return ResponseDepth.DETAILED
    if any(word in text for word in ("admission", "process", "eligibility")):
        return ResponseDepth.DETAILED
    if len(text.split()) <= 8 and any(word in text for word in ("name", "who", "when", "where", "fee")):
        return ResponseDepth.SHORT
    return ResponseDepth.NORMAL

def depth_instruction(depth: ResponseDepth) -> str:
    return {
        ResponseDepth.SHORT: "Be concise: answer directly in one or two sentences unless a list is essential.",
        ResponseDepth.NORMAL: "Give a clear, useful answer with enough explanation for a student; avoid unnecessary length.",
        ResponseDepth.DETAILED: "Give a structured explanation with useful details and a brief example where helpful.",
        ResponseDepth.DEEP: "Give a thorough step-by-step explanation, including prerequisites, examples, and practical guidance where relevant.",
    }[depth]
