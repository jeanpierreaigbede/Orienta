"""Chatbot model adapter. RodiumAI (OpenAI-compatible gateway) in real use, a scripted fake for rehearsals and tests."""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ValidationError

from app.config import get_settings

logger = logging.getLogger("orienta.llm")

SYSTEM_PROMPT_FR = (Path(__file__).parent / "prompts" / "triage_system_fr.txt").read_text(encoding="utf-8")


class LLMUnavailable(Exception):
    pass


class TriageOutput(BaseModel):
    reply: str
    decision: Literal["ASK_FOLLOW_UP", "ORIENT"]
    orientationLevel: Literal["EMERGENCY", "CONSULTATION_48H", "HOME_CARE"] | None = None


class ChatModel(Protocol):
    def complete(self, messages: list[dict]) -> str: ...


class RodiumAIModel:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.rodiumai_api_key:
            raise LLMUnavailable("RODIUMAI_API_KEY is not set")
        self.api_key = settings.rodiumai_api_key
        self.model = settings.rodiumai_model
        self.timeout = settings.llm_timeout_seconds

    async def _complete(self, messages: list[dict]) -> str:
        from rodiumai import RodiumAI, RodiumAIError

        client = RodiumAI(api_key=self.api_key, timeout=self.timeout, max_retries=1)
        try:
            response = await client.chat.completions.create(model=self.model, messages=messages, temperature=0.2)
        except RodiumAIError as exc:
            # The error type only: prompts are never logged.
            logger.warning("rodiumai_error type=%s", type(exc).__name__)
            raise LLMUnavailable(type(exc).__name__) from exc
        if not response.choices or not response.choices[0].message.content:
            raise LLMUnavailable("empty response")
        return response.choices[0].message.content

    def complete(self, messages: list[dict]) -> str:
        # Called from a sync FastAPI route (worker thread): run the async SDK in its own event loop.
        return asyncio.run(self._complete(messages))


class FakeModel:
    """Scripted answers, for rehearsals without an API key and for automated tests."""

    QUESTIONS = [
        "Depuis combien de temps avez-vous ces symptômes ?",
        "Sur une échelle de 1 à 10, quelle est l'intensité de la gêne ?",
        "Avez-vous du mal à respirer, une douleur dans la poitrine ou avez-vous perdu connaissance ?",
    ]
    EMERGENCY_WORDS = ("respir", "poitrine", "thorac", "connaissance", "saign", "convuls")
    CONSULT_WORDS = ("fièvre", "fievre", "vomi", "diarrh", "douleur", "toux")

    def complete(self, messages: list[dict]) -> str:
        patient_texts = [m["content"].lower() for m in messages if m["role"] == "user"]
        last = patient_texts[-1] if patient_texts else ""
        everything = " ".join(patient_texts)
        if any(w in last for w in self.EMERGENCY_WORDS) and not last.startswith("non"):
            return json.dumps({"reply": "Ces signes nécessitent une prise en charge immédiate. Rendez-vous aux urgences "
                               "les plus proches ou appelez les secours. Un agent de santé va aussi vous rappeler.",
                               "decision": "ORIENT", "orientationLevel": "EMERGENCY"}, ensure_ascii=False)
        asked = len(patient_texts) - 1
        if asked < len(self.QUESTIONS):
            return json.dumps({"reply": self.QUESTIONS[asked], "decision": "ASK_FOLLOW_UP", "orientationLevel": None},
                              ensure_ascii=False)
        level = "CONSULTATION_48H" if any(w in everything for w in self.CONSULT_WORDS) else "HOME_CARE"
        reply = ("Je vous conseille de consulter un centre de santé dans les 48 heures." if level == "CONSULTATION_48H"
                 else "Reposez-vous et hydratez-vous bien. Consultez si les symptômes persistent ou s'aggravent.")
        return json.dumps({"reply": reply, "decision": "ORIENT", "orientationLevel": level}, ensure_ascii=False)


def get_chat_model() -> ChatModel:
    if get_settings().llm_provider == "fake":
        return FakeModel()
    return RodiumAIModel()


def parse_output(text: str) -> TriageOutput:
    """Extract and validate the JSON object returned by the model."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in the model output")
    output = TriageOutput.model_validate(json.loads(match.group(0)))
    if output.decision == "ORIENT" and output.orientationLevel is None:
        raise ValueError("ORIENT without orientationLevel")
    if output.decision == "ASK_FOLLOW_UP":
        output.orientationLevel = None
    return output


def ask(model: ChatModel, messages: list[dict]) -> TriageOutput:
    """One call, one retry when the output is not valid JSON."""
    for attempt in range(2):
        text = model.complete(messages)
        try:
            return parse_output(text)
        except (ValueError, ValidationError, json.JSONDecodeError):
            logger.warning("llm_invalid_output attempt=%s", attempt + 1)
    raise LLMUnavailable("invalid output")
