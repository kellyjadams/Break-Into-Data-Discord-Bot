import os
import csv

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

from src.models import Goal
from src.database import get_categories


load_dotenv()

openai_client = AsyncOpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)


@dataclass
class ParsedSubmissionItem:
    category: str
    goal_id: int
    value: Optional[int]
    submission_time: datetime


PROMPT = """You will be given a user's message and you task is to you extract all the metrics out of this and return as CSV? Only output CSV, no thoughts
We need to extract this data:

Make sure to use this schema:
<day shift>, <category>, <value>
Day shift is 0 for today's submission, -1 for yesterday's submission and so on.
If no time is mentioned, then it is 0.
Only provide metrics from the user's goals, ignore others

Possible categories: 
{categories}

Only output data that matches the categories (and the "specifically" part if present).
If no the user did not specify the value, but the category was submitted, then the value is "true" (meaning that the user completed the goal, but the value is unknown).
If the user says that they did not complete the goal, then the value is "false".
"""


def _format_category(category_name: str, goal_description: Optional[str], metric: str) -> str:
    if goal_description:
        category_speicialisation = f"  - specifically: {goal_description}\n"
    else:
        category_speicialisation = ""
    
    return f"- {category_name}:\n{category_speicialisation}  - value: {metric}"


def _parse_value(value: str) -> Optional[int]:
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


async def parse_submission_message(text: str, goals: list[Goal]) -> list[ParsedSubmissionItem]:
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
    csv_data = csv_data.strip('`\n')

    items = list(csv.reader(csv_data.split('\n')))

    parsed_submissions = []

    for day_shift, category, value in items:
        if category == 'category':
            # skip the header, if present
            continue

        if day_shift == '0':
            # today
            submission_time = datetime.now()
        elif day_shift == '-1':
            # yesterday
            submission_time = (datetime.now() - timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0)
        else:
            # skip old submissions
            continue

        category = category.strip()
        value = _parse_value(value)

        goal_id = category_name_to_goal_id.get(category, None)
        if goal_id is None:
            # skip the category that is not in the user's goals
            continue

        parsed_submissions.append(ParsedSubmissionItem(
            category=category,
            value=value,
            submission_time=submission_time,
            goal_id=goal_id,
        ))

    return parsed_submissions

    
