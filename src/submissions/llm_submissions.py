import csv
import os

from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

from src.models import Goal
from src.database import get_categories
from src.submissions.entities import ParsedSubmissionItem


load_dotenv()

openai_client = AsyncOpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)


PROMPT = """You will be given a user's message and you task is to you extract all the metrics out of this and return as CSV? Only output CSV, no thoughts
We need to extract this data:

Make sure to use this schema:
<day shift>, <category>, <value>
Day shift is 0 for today's submission, -1 for yesterday's submission and so on.
If no time is mentioned, then it is 0.
Only provide metrics from the user's goals, ignore others.

Possible categories: 
{categories}

Only output data that matches the categories (and the "specifically" part if present).
If the user did not specify the value, but the category is mentioned as completed, then the value is "true" (meaning that the user completed the goal, but the value is unknown).
If the user says that they did not complete the goal, then the value is "false".
"""


def _format_category(category_name: str, goal_description: Optional[str], metric: str) -> str:
    if goal_description:
        category_speicialisation = f"  - specifically: {goal_description}\n"
    else:
        category_speicialisation = ""
    
    return f"- {category_name}:\n{category_speicialisation}  - value: {metric}"


def _parse_value(value: str) -> None | int | bool:
    """ Parse the value from the user's message.
    None - the value is unknown, used for boolean submission
    int - the value is a number
    False - the user did not complete the goal
    """
    value = value.strip().lower()

    if value == 'true':
        # the value is unknown
        return None
    elif value == 'false':
        return False
    
    try:
        return int(value)
    except ValueError:
        # TODO: log the error
        return None


def _process_submission_item(
        day_shift: str, category: str, value: str,
        category_name_to_goal_id: dict[str, int], 
        created_at: datetime) -> Optional[ParsedSubmissionItem]:
    if category == 'category':
        # skip the header, if present
        return None
    
    if value == "":
        return None

    if day_shift == '0':
        # today
        submission_time = created_at
    elif day_shift == '-1':
        # yesterday
        submission_time = (created_at - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0)
    else:
        # skip old submissions
        return None

    category = category.strip()
    value = _parse_value(value)

    if value is False:
        return None

    goal_id = category_name_to_goal_id.get(category, None)
    if goal_id is None:
        # skip the category that is not in the user's goals
        return None

    return ParsedSubmissionItem(
        category=category,
        value=value,
        submission_time=submission_time,
        goal_id=goal_id,
    )


def process_csv_submission(
        csv_data: str, 
        category_name_to_goal_id: dict[str, int],
        created_at: datetime) -> list[ParsedSubmissionItem]:
    csv_data = csv_data.strip('`\n').strip()

    items = list(csv.reader(csv_data.split('\n')))
    items = [item for item in items if len(item) == 3]

    parsed_submissions = []

    for day_shift, category, value in items:
        submission_item = _process_submission_item(
            day_shift, category, value, 
            category_name_to_goal_id, created_at
        )

        if submission_item:
            parsed_submissions.append(submission_item)

    return parsed_submissions


async def parse_submission_message(text: str, created_at: datetime, goals: list[Goal]) -> list[ParsedSubmissionItem]:
    categories = {
        category.category_id: category.name
        for category in await get_categories()
    }

    category_name_to_goal_id = {
        categories[goal.category_id]: goal.goal_id
        for goal in goals
    }

    category_info = [
        _format_category(
            category_name=categories[goal.category_id], 
            goal_description=goal.goal_description, 
            metric=goal.metric
        )
        for goal in goals
    ]

    prompt = PROMPT.format(
        categories="\n".join(category_info), 
    )

    response = await openai_client.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=[{
            "role": "system",
            "content": prompt,
        }, {
            "role": "user",
            "content": text,
        }],
        temperature=0.0,
        tool_choice=None
    )

    csv_data = response.choices[0].message.content

    return process_csv_submission(csv_data, category_name_to_goal_id, created_at)
