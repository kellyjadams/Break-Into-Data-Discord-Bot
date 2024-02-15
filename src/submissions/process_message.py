from src.models import Goal
from src.database import (
    get_user_goals, 
    new_submission,
)
from src.submissions.llm_submissions import (
    parse_submission_message,
    ParsedSubmissionItem,
)


def _format_parsed_submission_item(submission_item: ParsedSubmissionItem):
    value = submission_item.value
    if value is None:
        # value is unknown, the submission is boolean
        value = "✅"

    return f"{submission_item.category}: {submission_item.value}"


def _format_message(submission_items: list[ParsedSubmissionItem]):
    header = "Your submission:\n"
    return header + "\n".join(
        _format_parsed_submission_item(item)
        for item in submission_items
    )


async def process_submission_message(message):
    user_goals = await get_user_goals(message.author.id)

    if not user_goals:
        await message.reply("Please configre your goals first in `declare_your_goals_here` channel.")
        return

    submission_items = await parse_submission_message(
        message.content,
        user_goals,
    )

    if not submission_items:
        await message.reply("No submissions found.")
        return

    formatted_message = _format_message(submission_items)

    await message.reply(formatted_message)

    for item in submission_items:
        await new_submission(
            user_id=message.author.id,
            goal_id=item.goal_id,
            proof_url=None,
            amount=item.value,
        )
