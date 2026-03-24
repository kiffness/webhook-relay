from pydantic import BaseModel, HttpUrl

class GithubUser(BaseModel):
    login: str
    html_url: HttpUrl

class GithubRepo(BaseModel):
    full_name: str
    html_url: HttpUrl

class GithubLabel(BaseModel):
    name: str
    color: str

class PullRequest(BaseModel):
    number: int
    title: str
    html_url: HttpUrl
    state: str
    merged: bool
    user: GithubUser
    body: str | None = None
    labels: list[GithubLabel] = []
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0

class PullRequestEvent(BaseModel):
    """Payload for pull_request webhook events."""
    action: str
    number: int
    pull_request: PullRequest
    repository: GithubRepo
    sender: GithubUser

class Commit(BaseModel):
    id: str
    message: str
    url: HttpUrl
    author: dict

class PushEvent(BaseModel):
    """Payload for push webhook events."""
    ref: str
    commits: list[Commit]
    repository: GithubRepo
    pusher: dict
    compare: HttpUrl
