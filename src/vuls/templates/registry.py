import json
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from vuls.templates.schemas import (
    TemplateDefinition,
    TemplateFileBlueprint,
    TemplateManifest,
    TemplateSelection,
    TemplateValidationIssue,
)

EXPECTED_TEMPLATE_KEYS = ("crm", "saas", "marketplace", "ai_agent", "dashboard")
CATALOG_DIR = Path(__file__).resolve().parent / "catalog"
CLARIFICATION_QUESTION = (
    "Which product type fits best: CRM, SaaS, Marketplace, AI Agent or Dashboard?"
)
MIN_SELECTION_CONFIDENCE = 0.5


class TemplateRegistry:
    def __init__(self, catalog_dir: Path | None = None) -> None:
        self._catalog_dir = catalog_dir or CATALOG_DIR
        self._templates: dict[str, TemplateDefinition] | None = None

    def load_all(self) -> list[TemplateDefinition]:
        templates = self._load_catalog()
        return [templates[key] for key in EXPECTED_TEMPLATE_KEYS]

    def get(self, key: str) -> TemplateDefinition:
        templates = self._load_catalog()
        try:
            return templates[key]
        except KeyError as exc:
            raise KeyError(f"Unknown template key: {key}") from exc

    def validate_catalog(self) -> list[TemplateValidationIssue]:
        issues: list[TemplateValidationIssue] = []
        for key in EXPECTED_TEMPLATE_KEYS:
            try:
                self._load_template(key)
            except (OSError, ValueError, ValidationError) as exc:
                issues.append(
                    TemplateValidationIssue(
                        template_key=key,
                        path=str(self._catalog_dir / key),
                        message=str(exc),
                    )
                )
        return issues

    def select_template(self, user_intent: str) -> TemplateSelection:
        intent_tokens = _tokenize(user_intent)
        scores = {
            template.key: _score_template(intent_tokens, template)
            for template in self.load_all()
        }
        selected_key, selected_score = max(scores.items(), key=lambda item: item[1])
        confidence = min(selected_score / 4.0, 1.0)

        if confidence < MIN_SELECTION_CONFIDENCE:
            return TemplateSelection(
                selected_key=None,
                confidence=confidence,
                needs_clarification=True,
                clarification_question=CLARIFICATION_QUESTION,
                scores=scores,
            )

        return TemplateSelection(
            selected_key=selected_key,
            confidence=confidence,
            needs_clarification=False,
            clarification_question=None,
            scores=scores,
        )

    def _load_catalog(self) -> dict[str, TemplateDefinition]:
        if self._templates is None:
            self._templates = {
                key: self._load_template(key)
                for key in EXPECTED_TEMPLATE_KEYS
            }
        return self._templates

    def _load_template(self, key: str) -> TemplateDefinition:
        template_dir = self._catalog_dir / key
        manifest = TemplateManifest.model_validate(
            _load_json_document(template_dir / "template.yaml")
        )
        if manifest.key != key:
            raise ValueError(f"Template key mismatch: expected {key}, got {manifest.key}.")

        blueprint = TemplateFileBlueprint.model_validate(
            _load_json_document(template_dir / "files.yaml")
        )
        prompt_markdown = (template_dir / "prompts.md").read_text(encoding="utf-8").strip()

        return TemplateDefinition(
            **manifest.model_dump(),
            prompt_markdown=prompt_markdown,
            file_blueprint=blueprint,
        )


def _load_json_document(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _score_template(intent_tokens: set[str], template: TemplateDefinition) -> float:
    keyword_tokens = {_normalize_token(keyword) for keyword in template.keywords}
    entity_tokens = {_normalize_token(entity) for entity in template.default_entities}
    page_tokens = {_normalize_token(page) for page in template.default_pages}
    role_tokens = {_normalize_token(role) for role in template.default_roles}

    score = 0.0
    score += 2.0 * len(intent_tokens & keyword_tokens)
    score += 1.0 * len(intent_tokens & entity_tokens)
    score += 0.75 * len(intent_tokens & page_tokens)
    score += 0.5 * len(intent_tokens & role_tokens)
    return score


def _tokenize(text: str) -> set[str]:
    return {
        _normalize_token(token)
        for token in re.findall(r"[a-zA-Z0-9_]+", text.lower())
        if _normalize_token(token)
    }


def _normalize_token(text: str) -> str:
    return text.lower().replace("-", "_").strip()
