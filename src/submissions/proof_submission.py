import logging

import discord

from src.models import User
from src.database import (
    get_submissions_without_proof,
    update_submission_proof,
    get_categories,
)


logger = logging.getLogger(__name__)


def _format_proof_request_message(unprocessed_submission, categories):
    msgs = [
        f"Please provide proof (image) for {len(unprocessed_submission)} submissions"
    ]
        
    return "\n".join(msgs)


async def process_proofs(
    user: User,
    message: discord.Message,
):
    """ Processes proofs that we attached to a submission. """
    submissions = await get_submissions_without_proof(user.user_id)
    
    logger.info(f"Processing {len(message.attachments)} "
                f"proofs for user {user.user_id}")
    
    for attachment, submission in zip(message.attachments, submissions):
        logger.info(f"Updating proof for submission {submission.submission_id}")
        await update_submission_proof(submission.submission_id, attachment.url)
        
    categories = await get_categories()
    submissions_without_proof = submissions[len(message.attachments):]
    
    if submissions_without_proof:
        logger.info(
            f"Requesting {user.user_id} proof for "
            f"{len(submissions_without_proof)} submissions")
        msg = _format_proof_request_message(
            submissions_without_proof, categories)
        
        await message.reply(msg)
    else:
        await message.reply(f"Thank you for your submissions, {user.username}!")
