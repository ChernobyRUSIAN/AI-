from vuls.templates.schemas import TemplateDefinition


def render_template_context(
    template: TemplateDefinition,
    *,
    user_intent: str,
    project_memory: list[str] | None = None,
) -> dict[str, object]:
    return {
        "template_key": template.key,
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "default_pages": template.default_pages,
        "default_entities": template.default_entities,
        "default_roles": template.default_roles,
        "i18n_keys": template.i18n_keys,
        "readme_sections": template.readme_sections,
        "prompt_markdown": template.prompt_markdown,
        "file_blueprint": [
            file.model_dump(mode="json")
            for file in template.file_blueprint.files
        ],
        "user_intent": user_intent,
        "project_memory": project_memory or [],
    }
