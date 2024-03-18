import discord
from datetime import (
    datetime, 
    timezone,
)

from src.database import (
    get_categories,
    get_user_goals, 
    ensure_user,
    new_submission,
    update_user_last_llm_submission,
)
from src.models import Goal
from src.submissions.entities import ParsedSubmissionItem
from src.submissions.llm_submissions import parse_submission_message
from src.submissions.proof_submission import process_proofs


def _format_parsed_submission_item(submission_item: ParsedSubmissionItem):
    value = submission_item.value
    if value is None:
        # value is unknown, the submission is boolean
        value = "✅"

    return f"{submission_item.category}: {value}"


def _format_message(user_goals: list[Goal], 
                    submission_items: list[ParsedSubmissionItem], 
                    categories: dict[int, str]):
    header = "Your submission:\n"
    msg_parts = []
    
    submissions_by_goal = {
        submission_item.goal_id: submission_item
        for submission_item in submission_items
    }
    
    for user_goal in user_goals:
        category_name = categories[user_goal.category_id]
        submission_item = submissions_by_goal.get(user_goal.goal_id)
        if submission_item is None:
            msg_parts.append(f"{category_name}: -")
        else:
            msg_parts.append(_format_parsed_submission_item(submission_item))
    
    return header + "\n".join(msg_parts)


async def _rate_limit_llm_calls(user, window_minutes=120):
    """ Rate limit LLM submissions to once per window 
    Returns True if the submission is allowed, False otherwise.
    """
    now = datetime.now(timezone.utc)
    if user.last_llm_submission is not None:
        time_since_last_submission = now - user.last_llm_submission
        if time_since_last_submission.total_seconds() < window_minutes * 60:
            return False

    await update_user_last_llm_submission(user.user_id, now)
    return True


async def process_submission_message(user, message, is_backfill=False):
    user_goals = await get_user_goals(user.user_id)

    if not user_goals:
        if not is_backfill:
            await message.reply("Please configure your goals first in `declare_your_goals_here` channel.")
        return False
    
    if not is_backfill and not await _rate_limit_llm_calls(user):
        # TODO: change the message
        await message.reply("Rate limit exceeded. Please try again later.")
        return False

    submission_items = await parse_submission_message(
        message.content,
        message.created_at,
        user_goals,
    )

    print(submission_items)

    if not submission_items:
        if not is_backfill:
            await message.reply("No submissions found.")
        return False

    categories = {
        category.category_id: category.name
        for category in await get_categories()
    }
    formatted_message = _format_message(user_goals, submission_items, categories)

    if not is_backfill:
        await message.reply(formatted_message)

    for item in submission_items:
        await new_submission(
            user_id=user.user_id,
            goal_id=item.goal_id,
            proof_url=None,
            amount=item.value or 0,
            created_at=item.submission_time,
        )

    return True


async def process_discord_message(message: discord.Message,  channel_id: str, is_backfill=False):
    user = await ensure_user(message.author)
    
    is_submission_channel = (
        str(message.channel.id) == channel_id 
        or is_backfill
    )
    
    if is_submission_channel:
        should_process_proofs = True
        
        if message.content:
            should_process_proofs = await process_submission_message(
                user, message, is_backfill=is_backfill)
    
        if should_process_proofs:
            await process_proofs(user, message)