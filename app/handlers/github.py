import logging
from app.models.github import PullRequestEvent, PushEvent
from app.models.slack import SlackMessage

logger = logging.getLogger(__name__)

# Maps PR actions to human-readable labels and Slack-compatible emoji
PR_ACTION_MAP: dict[str, tuple[str, str]] = {
    "opened":              ("opened",           ":sparkles:"),
    "closed":              ("merged",           ":merged:"),
    "reopened":            ("reopened",         ":recycle:"),
    "labeled":             ("labelled",         ":label:"),
    "review_requested":    ("review requested", ":eyes:"),
    "ready_for_review":    ("ready for review", ":white_check_mark:"),
    "converted_to_draft":  ("converted to draft", ":pencil:"),
}

def handle_pull_request(event: PullRequestEvent) -> SlackMessage:
    """
    Transform a GitHub pull_request webhook event into a formatted Slack message.

    Handles the most common PR lifecycle actions: opened, closed (merged or not),
    reopened, labelled, and review requested.
    """
    pr = event.pull_request
    repo = event.repository
    action = event.action

    # GitHub fires action="closed" for both merged and simply closed PRs
    if action == "closed":
        if pr.merged:
            label, emoji = "merged", ":merged:"
        else:
            label, emoji = "closed without merging", ":x:"
    else:
        label, emoji = PR_ACTION_MAP.get(action, (action, ":bell:"))

    title_text = f"{emoji} *PR {label}* in <{repo.html_url}|{repo.full_name}>"
    pr_link = f"<{pr.html_url}#{pr.number}: {pr.title}>"
    author_link = f"<{pr.user.html_url}|@{pr.user.login}>"

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} Pull Request {label.title()}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{pr_link}*\n{repo.full_name}"},
        },
    ]

    if pr.body:
        body_preview = pr.body[:280] + "..." if len(pr.body) > 280 else pr.body
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": body_preview},
        })
    if pr.labels:
        label_names = " ".join(f"`{lbl.name}`" for lbl in pr.labels)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Labels:* {label_names}"},
        })

    if pr.merged:
        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Files changed:*\n{pr.changed_files}"},
                {"type": "mrkdwn", "text": f"*Changes:*\n+{pr.additions} / -{pr.deletions}"},
            ],
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"Opened by {author_link}"}],
    })

    logger.info("Handled PR event: action=%s repo=%s pr=%s", action, repo.full_name, pr.number)

    return SlackMessage(text=title_text, blocks=blocks)

def handle_push(event: PushEvent) -> SlackMessage | None:
    """
    Transform a GitHub push webhook event into a formatted Slack message.

    Returns None for tag pushes or pushes with no commits (e.g. branch deletions),
    so the caller can decide to silently ignore them.
    """
    if not event.ref.startswith("refs/heads/"):
        logger.debug("Skipping push event for ref: %s", event.ref)
        return None

    if not event.commits:
        logger.debug("Skipping push event with no commits for ref: %s", event.ref)
        return None

    branch = event.ref.replace("refs/heads/", "")
    repo = event.repository
    pusher_name = event.pusher.get("name", "unknown")
    commit_count = len(event.commits)
    commit_word = "commit" if commit_count == 1 else "commits"

    header_text = f":arrow_up: {commit_count} {commit_word} pushed to `{branch}`"

    commit_lines = []
    for commit in event.commits[:5]:
        short_sha = commit.id[:7]
        first_line = commit.message.splitlines()[0]
        commit_lines.append(f"• <{commit.url}|`{short_sha}`> {first_line}")

    if commit_count > 5:
        commit_lines.append(f"_…and {commit_count - 5} more — <{event.compare}|view all>_")

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Push to {repo.full_name}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":arrow_up: *{commit_count} {commit_word}* pushed to `{branch}` by *{pusher_name}*",
            },
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(commit_lines)},
        },
        {"type": "divider"},
    ]

    logger.info(
        "Handled push event: repo=%s branch=%s commits=%d",
        repo.full_name, branch, commit_count,
    )

    return SlackMessage(text=header_text, blocks=blocks)