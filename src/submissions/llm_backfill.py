import csv
import os

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
    value: None | int | bool
    submission_time: datetime


PROMPT = """Objective: Extract specific metrics from a user's message and format the output as CSV. This process aims to analyze user-submitted data related to their goals, focusing only on predefined categories.

Possible categories: 
{categories}

Instructions:

Input Analysis: Identify metrics in the user's message that correspond to the predefined categories.
Time Frame Identification: Assign a day shift value based on the submission time mentioned in the message (-1 for yesterday, 0 for today, etc.). Assume day shift 0 if unspecified.
Data Extraction Schema: Follow the CSV format schema: <day shift>, <category>, <value>.
Day Shift: 0 (today), -1 (yesterday), etc.
Category: Only include data matching the specified categories.
Value: If a goal is mentioned as completed without a specific value, use "true". Use "false" if the goal is stated as not completed.
Output: Generate a CSV string without additional commentary or analysis.
Example:

User Message: "I did 2 SQL questions and 15 minutes of yoga today."
Expected CSV Output:
0, Coding, 2
0, Fitness, 15
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


def _process_submission_item(day_shift: str, category: str, value: str, category_name_to_goal_id: dict[str, int], created_at: datetime) -> Optional[ParsedSubmissionItem]:
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


def _process_csv_submission(csv_data: str, category_name_to_goal_id: dict[str, int], created_at: datetime) -> list[ParsedSubmissionItem]:
    csv_data = csv_data.strip('`\n').strip()

    items = list(csv.reader(csv_data.split('\n')))
    items = [item for item in items if len(item) == 3]

    parsed_submissions = []

    for day_shift, category, value in items:
        submission_item = _process_submission_item(
            day_shift, category, value, category_name_to_goal_id, created_at
        )

        if submission_item:
            parsed_submissions.append(submission_item)

    return parsed_submissions


async def parse_submission_message(text: str, goals: list[Goal], created_at: datetime) -> list[ParsedSubmissionItem]:
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
        model="gpt-3.5-turbo",
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
    # print(response)
    print(response.choices[0].message.content)

    return _process_csv_submission(csv_data, category_name_to_goal_id, created_at)
