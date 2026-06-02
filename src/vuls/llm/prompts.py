import json

from vuls.llm.schemas import BriefNormalizationRequest, LLMMessage, LLMRole, ProjectManifestRequest
from vuls.templates.renderer import render_template_context


def build_brief_normalization_prompt(request: BriefNormalizationRequest) -> list[LLMMessage]:
    payload = {
        "user_idea": request.user_idea,
        "language_code": request.language_code,
        "memory_context": request.memory_context,
        "expected_schema": {
            "title": "short product title",
            "goal": "clear project goal",
            "target_users": ["primary user roles"],
            "must_have_features": ["core MVP features"],
            "language_code": request.language_code,
        },
    }

    return [
        LLMMessage(
            role=LLMRole.SYSTEM,
            content=(
                "You are Vuls, an AI Product Builder. You normalize raw product ideas "
                "into concise implementation briefs."
            ),
        ),
        LLMMessage(
            role=LLMRole.USER,
            content=(
                "Normalize this product idea for planning. Return only JSON matching "
                "the expected schema.\n"
                f"{_json(payload)}"
            ),
        ),
    ]


def build_project_manifest_prompt(request: ProjectManifestRequest) -> list[LLMMessage]:
    template_context = render_template_context(
        request.template,
        user_intent=request.brief.goal,
        project_memory=_flatten_memory(request.memory_context),
    )
    payload = {
        "brief": request.brief.model_dump(mode="json"),
        "template": template_context,
        "output_shape": {
            "project_name": "kebab-case project name",
            "readme_summary": "README-ready summary",
            "tech_stack": ["frameworks and main libraries"],
            "files": [
                {
                    "path": "relative/path",
                    "content": "complete file content",
                    "purpose": "why this file exists",
                }
            ],
            "env_vars": [
                {
                    "name": "ENV_VAR_NAME",
                    "description": "why this variable exists",
                    "required": True,
                }
            ],
        },
    }

    return [
        LLMMessage(
            role=LLMRole.SYSTEM,
            content=(
                "You are Vuls, an AI Product Builder. You generate complete project "
                "file manifests from approved templates and briefs."
            ),
        ),
        LLMMessage(
            role=LLMRole.USER,
            content=(
                "Generate the project manifest. Return only JSON matching output_shape. "
                "Include complete file paths, file contents, README summary and env_vars.\n"
                f"{_json(payload)}"
            ),
        ),
    ]


def _flatten_memory(memory_context: dict[str, list[str]]) -> list[str]:
    return [
        memory_item
        for memory_items in memory_context.values()
        for memory_item in memory_items
    ]


def _json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
