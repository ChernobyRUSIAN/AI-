from vuls.workflows.schemas import GenerationRunCreate, GenerationRunStatus


def test_generation_run_create_defaults_to_empty_usage_and_no_template_version() -> None:
    request = GenerationRunCreate(
        project_id="project-1",
        provider="openrouter",
        model="openai/gpt-4o",
        input_summary="Generate CRM manifest.",
    )

    assert request.template_version_id is None
    assert request.usage == {}
    assert request.status == GenerationRunStatus.QUEUED


def test_generation_run_status_values_match_database_check_constraint() -> None:
    assert [status.value for status in GenerationRunStatus] == [
        "queued",
        "running",
        "completed",
        "failed",
        "cancelled",
    ]
