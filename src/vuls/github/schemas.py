from pydantic import BaseModel, ConfigDict, Field

from vuls.llm.schemas import GeneratedProjectManifest


class GitHubRepository(BaseModel):
    model_config = ConfigDict(frozen=True)

    owner: str = Field(min_length=1)
    repo_name: str = Field(min_length=1)
    html_url: str = Field(min_length=1)
    default_branch: str = Field(default="main", min_length=1)


class GitHubExportRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_id: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    repo_name: str = Field(min_length=1, max_length=100)
    manifest: GeneratedProjectManifest
    private: bool = True
    description: str | None = None
    default_branch: str = Field(default="main", min_length=1)


class GitHubExportResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_id: str
    owner: str
    repo_name: str
    html_url: str
    default_branch: str
    committed_files: list[str]

    @property
    def commit_count(self) -> int:
        return len(self.committed_files)
