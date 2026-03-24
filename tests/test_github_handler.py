import pytest

from app.handlers.github import handle_pull_request, handle_push
from app.models.github import (
    Commit,
    GitHubLabel,
    GitHubRepo,
    GitHubUser,
    PullRequest,
    PullRequestEvent,
    PushEvent,
)


def _make_user(login: str = "octocat") -> GitHubUser:
    return GitHubUser(login=login, html_url=f"https://github.com/{login}")


def _make_repo(name: str = "octocat/Hello-World") -> GitHubRepo:
    return GitHubRepo(
        full_name=name,
        html_url=f"https://github.com/{name}",
    )


def _make_pr(**kwargs) -> PullRequest:
    defaults = dict(
        number=42,
        title="Add feature X",
        html_url="https://github.com/octocat/Hello-World/pull/42",
        state="open",
        merged=False,
        user=_make_user(),
        body="This PR adds feature X.",
        labels=[],
        additions=10,
        deletions=2,
        changed_files=3,
    )
    return PullRequest(**{**defaults, **kwargs})


class TestHandlePullRequest:

    def test_opened_pr_produces_slack_message(self):
        event = PullRequestEvent(
            action="opened",
            number=42,
            pull_request=_make_pr(),
            repository=_make_repo(),
            sender=_make_user(),
        )
        msg = handle_pull_request(event)
        assert msg is not None
        assert len(msg.blocks) > 0

    def test_merged_pr_shows_stats(self):
        event = PullRequestEvent(
            action="closed",
            number=42,
            pull_request=_make_pr(merged=True, state="closed"),
            repository=_make_repo(),
            sender=_make_user(),
        )
        msg = handle_pull_request(event)
        block_texts = " ".join(str(b) for b in msg.blocks)
        assert "10" in block_texts

    def test_closed_without_merge_uses_x_emoji(self):
        event = PullRequestEvent(
            action="closed",
            number=42,
            pull_request=_make_pr(merged=False, state="closed"),
            repository=_make_repo(),
            sender=_make_user(),
        )
        msg = handle_pull_request(event)
        assert ":x:" in msg.text

    def test_pr_with_labels_includes_label_block(self):
        pr = _make_pr(labels=[GitHubLabel(name="bug", color="d73a4a")])
        event = PullRequestEvent(
            action="labeled",
            number=42,
            pull_request=pr,
            repository=_make_repo(),
            sender=_make_user(),
        )
        msg = handle_pull_request(event)
        block_texts = " ".join(str(b) for b in msg.blocks)
        assert "bug" in block_texts

    def test_long_pr_body_is_truncated(self):
        long_body = "x" * 500
        event = PullRequestEvent(
            action="opened",
            number=42,
            pull_request=_make_pr(body=long_body),
            repository=_make_repo(),
            sender=_make_user(),
        )
        msg = handle_pull_request(event)
        block_texts = " ".join(str(b) for b in msg.blocks)
        assert "..." in block_texts


class TestHandlePush:

    def _make_commit(self, sha: str = "abc1234def5678") -> Commit:
        return Commit(
            id=sha,
            message="Fix a bug",
            url=f"https://github.com/octocat/Hello-World/commit/{sha}",
            author={"name": "octocat"},
        )

    def test_branch_push_produces_slack_message(self):
        event = PushEvent(
            ref="refs/heads/main",
            commits=[self._make_commit()],
            repository=_make_repo(),
            pusher={"name": "octocat"},
            compare="https://github.com/octocat/Hello-World/compare/abc...def",
        )
        msg = handle_push(event)
        assert msg is not None
        assert "1 commit" in msg.text

    def test_tag_push_returns_none(self):
        event = PushEvent(
            ref="refs/tags/v1.0.0",
            commits=[self._make_commit()],
            repository=_make_repo(),
            pusher={"name": "octocat"},
            compare="https://github.com/octocat/Hello-World/compare/abc...def",
        )
        assert handle_push(event) is None

    def test_push_with_no_commits_returns_none(self):
        event = PushEvent(
            ref="refs/heads/main",
            commits=[],
            repository=_make_repo(),
            pusher={"name": "octocat"},
            compare="https://github.com/octocat/Hello-World/compare/abc...def",
        )
        assert handle_push(event) is None

    def test_more_than_five_commits_shows_ellipsis(self):
        commits = [self._make_commit(sha=f"abc123{i}xxxxxxx") for i in range(8)]
        event = PushEvent(
            ref="refs/heads/main",
            commits=commits,
            repository=_make_repo(),
            pusher={"name": "octocat"},
            compare="https://github.com/octocat/Hello-World/compare/abc...def",
        )
        msg = handle_push(event)
        assert msg is not None
        assert "more" in " ".join(str(b) for b in msg.blocks)
