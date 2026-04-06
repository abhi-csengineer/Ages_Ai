from __future__ import annotations

import importlib
from dataclasses import dataclass

from self_healing_observability.core.metrics import MODEL_FAITHFULNESS_SCORE_GAUGE


@dataclass
class FaithfulnessScorer:
    """
    Faithfulness scorer with optional HHEM-2.1-Open backend.

    If the model cannot be loaded in the runtime environment, fallback to a
    lexical overlap approximation to keep monitoring available.
    """

    model_name: str = "vectara/hhem-2.1-open"

    def score(self, context: str, answer: str) -> float:
        score = self._score_with_model(context, answer)
        MODEL_FAITHFULNESS_SCORE_GAUGE.set(score)
        return score

    def _score_with_model(self, context: str, answer: str) -> float:
        try:
            transformers_mod = importlib.import_module("transformers")
            torch_mod = importlib.import_module("torch")

            AutoModelForSequenceClassification = getattr(
                transformers_mod, "AutoModelForSequenceClassification"
            )
            AutoTokenizer = getattr(transformers_mod, "AutoTokenizer")

            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            inputs = tokenizer(context, answer, return_tensors="pt", truncation=True)
            with torch_mod.no_grad():
                logits = model(**inputs).logits
                prob = torch_mod.sigmoid(logits).mean().item()
            return float(max(0.0, min(1.0, prob)))
        except Exception:
            return self._fallback_lexical_overlap(context, answer)

    def _fallback_lexical_overlap(self, context: str, answer: str) -> float:
        c_tokens = {tok.lower() for tok in context.split() if tok.strip()}
        a_tokens = {tok.lower() for tok in answer.split() if tok.strip()}
        if not a_tokens:
            return 0.0
        overlap = len(c_tokens.intersection(a_tokens)) / len(a_tokens)
        return float(max(0.0, min(1.0, overlap)))
