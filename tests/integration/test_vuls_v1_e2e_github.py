import json
from pathlib import Path

from tests.integration.test_vuls_v1_e2e_zip import (
    FailingArtifactRepository,
    FakeCallback,
    FakeChat,
    FakeGitHubClient,
    FakeLLMClient,
    FakeMessage,
    FakeUser,
    VulsMvpE2EService,
    fitness_club_brief_payload,
    project_brief_payload,
    project_manifest_payload,
)
from vuls.bot.dispatcher import TelegramDispatcher
from vuls.db.models import ArtifactType
from vuls.llm.schemas import LLMClientResponse


def test_vuls_v1_e2e_github_flow_validates_complete_mvp_path(tmp_path: Path) -> None:
    github_client = FakeGitHubClient()
    llm_client = FakeLLMClient(
        [
            LLMClientResponse(content=json.dumps(project_brief_payload())),
            LLMClientResponse(content=json.dumps(project_manifest_payload())),
        ]
    )
    service = VulsMvpE2EService(
        tmp_path=tmp_path,
        llm_client=llm_client,
        github_client=github_client,
    )
    dispatcher = TelegramDispatcher(service)
    user = FakeUser(id=123, username="artel", full_name="Artel User", language_code="en")
    chat = FakeChat(id=456)

    dispatcher.dispatch_message(
        FakeMessage("/new Create a CRM for a coffee shop with customers and orders", user, chat)
    )
    github_reply = dispatcher.dispatch_callback(
        FakeCallback(
            data="export:github:project-1",
            from_user=user,
            message=FakeMessage("", user, chat),
        )
    )
    status_reply = dispatcher.dispatch_message(FakeMessage("/status", user, chat))

    assert github_reply.text == "\n".join(
        [
            "Project project-1 completed.",
            "Template: crm",
            "GitHub repository: https://github.com/acme/coffee-crm",
        ]
    )
    assert {
        "README.md",
        "package.json",
        "tsconfig.json",
        "tailwind.config.ts",
        "schema.sql",
        "env.example",
        "src/app/dashboard/page.tsx",
        "src/app/customers/actions.ts",
        "src/app/customers/page.tsx",
        "src/app/orders/actions.ts",
        "src/app/orders/page.tsx",
        "src/app/tasks/actions.ts",
        "src/app/tasks/page.tsx",
        "src/lib/database.types.ts",
        "src/lib/supabase.ts",
    }.issubset(github_client.files)
    assert "Add customer" in github_client.files["src/app/customers/page.tsx"]
    tsconfig = json.loads(github_client.files["tsconfig.json"])
    assert tsconfig["compilerOptions"]["paths"] == {"@/*": ["./src/*"]}
    assert "listCustomers" in github_client.files["src/app/customers/page.tsx"]
    assert "createCustomer" in github_client.files["src/app/customers/page.tsx"]
    assert "Total Customers" in github_client.files["src/app/dashboard/page.tsx"]
    assert "Open Orders" in github_client.files["src/app/dashboard/page.tsx"]
    assert "listOrders" in github_client.files["src/app/orders/page.tsx"]
    assert "order.status" in github_client.files["src/app/orders/page.tsx"]
    assert "listTasks" in github_client.files["src/app/tasks/page.tsx"]
    assert "task.status" in github_client.files["src/app/tasks/page.tsx"]
    assert "public.customers" in github_client.files["schema.sql"]
    assert "createClient" in github_client.files["src/lib/supabase.ts"]
    assert service.github_metadata.records == [
        {
            "project_id": "project-1",
            "owner": "acme",
            "repo_name": "coffee-crm",
            "html_url": "https://github.com/acme/coffee-crm",
            "default_branch": "main",
        }
    ]
    assert service.artifacts.records[0]["artifact_type"] == ArtifactType.MANIFEST
    assert service.artifacts.records[1]["artifact_type"] == ArtifactType.ZIP
    assert "Export: github" in status_reply.text
    assert "URL: https://github.com/acme/coffee-crm" in status_reply.text


def test_vuls_v1_e2e_github_flow_survives_artifact_persistence_failure_for_fitness_club(
    tmp_path: Path,
) -> None:
    artifact_repository = FailingArtifactRepository()
    github_client = FakeGitHubClient()
    llm_client = FakeLLMClient(
        [
            LLMClientResponse(content=json.dumps(fitness_club_brief_payload())),
            LLMClientResponse(content=json.dumps(project_manifest_payload())),
        ]
    )
    service = VulsMvpE2EService(
        tmp_path=tmp_path,
        llm_client=llm_client,
        github_client=github_client,
        artifact_repository=artifact_repository,
    )
    dispatcher = TelegramDispatcher(service)
    user = FakeUser(id=123, username="artel", full_name="Artel User", language_code="en")
    chat = FakeChat(id=456)

    dispatcher.dispatch_message(
        FakeMessage(
            "/new Create a CRM for a fitness club with members and subscriptions",
            user,
            chat,
        )
    )
    github_reply = dispatcher.dispatch_callback(
        FakeCallback(
            data="export:github:project-1",
            from_user=user,
            message=FakeMessage("", user, chat),
        )
    )

    assert github_reply.text == "\n".join(
        [
            "Project project-1 completed.",
            "Template: crm",
            "GitHub repository: https://github.com/acme/coffee-crm",
        ]
    )
    assert "Traceback" not in github_reply.text
    assert "Supabase artifacts insert failed" not in github_reply.text
    assert service.projects["project-1"].status == "completed"
    assert service.projects["project-1"].zip_artifact_id is None
    assert artifact_repository.calls[0]["artifact_type"] == ArtifactType.MANIFEST
    assert artifact_repository.calls[1]["artifact_type"] == ArtifactType.ZIP
    assert "schema.sql" in github_client.files
    assert "src/lib/supabase.ts" in github_client.files


def test_vuls_v1_e2e_github_failure_path_returns_user_safe_telegram_error(
    tmp_path: Path,
) -> None:
    github_client = FakeGitHubClient(fail_put_file=True)
    llm_client = FakeLLMClient(
        [
            LLMClientResponse(content=json.dumps(project_brief_payload())),
            LLMClientResponse(content=json.dumps(project_manifest_payload())),
        ]
    )
    service = VulsMvpE2EService(
        tmp_path=tmp_path,
        llm_client=llm_client,
        github_client=github_client,
    )
    dispatcher = TelegramDispatcher(service)
    user = FakeUser(id=123, username="artel", full_name="Artel User", language_code="en")
    chat = FakeChat(id=456)

    dispatcher.dispatch_message(
        FakeMessage("/new Create a CRM for a coffee shop with customers and orders", user, chat)
    )
    failure_reply = dispatcher.dispatch_callback(
        FakeCallback(
            data="export:github:project-1",
            from_user=user,
            message=FakeMessage("", user, chat),
        )
    )

    assert failure_reply.text == "\n".join(
        [
            "Project project-1 could not be completed safely. "
            "Please try again or refine the request.",
            "Template: crm",
        ]
    )
    assert "provider detail" not in failure_reply.text
    assert service.github_metadata.records == []
    assert service.projects["project-1"].status == "failed"
