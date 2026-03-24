from pydantic import BaseModel

class SlackText(BaseModel):
    type: str = "mrkdwn"
    text: str

class SlackSelection(BaseModel):
    type: str = "section"
    text: SlackText

class SlackDivider(BaseModel):
    type: str = "divider"

class SlackHeader(BaseModel):
    type: str = "header"
    text: SlackText

class SlackContext(BaseModel):
    type: str = "context"
    elements: list[SlackText]

class SlackMessage(BaseModel):
    """
    A Slack Block Kit message.
    Blocks give far richer formatting than plain text and render
    consistently across all Slack clients.
    """
    text: str
    blocks: list[dict]