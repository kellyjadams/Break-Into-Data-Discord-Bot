import logging
from typing import Optional

from sqlalchemy import (
    delete, 
    insert, 
    select, 
    text, 
    update
    )
from sqlalchemy.ext.asyncio import (
    create_async_engine,
)
from sqlalchemy.orm import declarative_base


from async_lru import alru_cache

from src.models import (
    Category,
    User,
    Submission,
    Goal,
)

logger = logging.getLogger(__name__) #Setting up logger

Base = declarative_base()

DB_ENGINE = None


async def init_db(database_url: str):
    global DB_ENGINE

    try:
        DB_ENGINE = create_async_engine(
            database_url,
            echo=False,
        )
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

async def close_db():
    if DB_ENGINE is not None:
        await DB_ENGINE.dispose()


async def clean_database():
    if input("Are you sure you want to drop everything? (y/n) ") != 'y':
        print('Skipping')
        return

    async with DB_ENGINE.begin() as conn:
        print()
        print(await conn.execute(delete(Submission)))
        print(await conn.execute(delete(Goal)))
        print(await conn.execute(delete(User)))
        print()


async def new_user(user_id, username, email, name) -> User:
    try:
        user = await get_user(user_id)
        if user is None:
            async with DB_ENGINE.begin() as conn:
                cursor = await conn.execute(insert(User).values(
                    user_id=user_id,
                    username=username,
                    email=email,
                    name=name,
                ).returning(User))

                user = cursor.fetchone()
                logger.info(f"New user created: {username} with ID {user_id}")
                return user
        else:
            async with DB_ENGINE.begin() as conn:
                cursor = await conn.execute(update(User).where(
                    User.user_id==user_id, User.username==username).values(
                        email=email, name=name,
                ).returning(User))

                user = cursor.fetchone()
                logger.info(f"Updated user name and email for : {username} with ID {user_id}")
                return user
            
    except Exception as e:
        logger.error(f"Failed to create new user {username}: {e}")
        raise

async def new_submission(user_id, goal_id, proof_url, amount) -> Submission:
    try:
        async with DB_ENGINE.begin() as conn:
            cursor = await conn.execute(insert(Submission).values(
                user_id=user_id,
                goal_id=goal_id,
                proof_url=proof_url,
                amount=amount,
            ).returning(Submission))

            submission = cursor.fetchone()
            logger.info(f"Submission attempt for {user_id}")
            return submission
    except Exception as e:
        logger.error(f"Failed Submission for {user_id}: {e}")


async def new_goal(user_id, category_id,goal_description, metric, target, frequency) -> Goal:
    try:
        async with DB_ENGINE.begin() as conn:
            cursor = await conn.execute(insert(Goal).values(
                user_id=user_id,
                category_id=category_id,
                goal_description=goal_description,
                metric=metric,
                target=target,
                frequency=frequency,
            ).returning(Goal))

            goal = cursor.fetchone()
            logger.info(f"Attempt to set New Goal for {user_id}")
            return goal
    except Exception as e:
        logger.error(f"Failed setting New Goal for {user_id}: {e}")


@alru_cache(maxsize=1000)
async def get_category(text_channel) -> Optional[Category]:
    async with DB_ENGINE.begin() as conn:
        return (await conn.execute(select(Category).where(Category.text_channel == text_channel))).first()



@alru_cache(maxsize=1000)
async def get_category_by_name(name) -> Optional[Category]:
    async with DB_ENGINE.begin() as conn:
        return (await conn.execute(select(Category).where(Category.name == name))).first()


@alru_cache(maxsize=1000)
async def get_category_for_voice(voice_channel) -> Optional[Category]:
    async with DB_ENGINE.begin() as conn:
        return (await conn.execute(select(Category).where(Category.voice_channel == voice_channel))).first()


@alru_cache(maxsize=1000)
async def get_user(user_id) -> Optional[User]:
    async with DB_ENGINE.begin() as conn:
        return (await conn.execute(select(User).where(User.user_id == user_id))).first()


@alru_cache(maxsize=1000)
async def get_goal(category_id, user_id) -> Optional[Goal]:
    async with DB_ENGINE.begin() as conn:
        return (await conn.execute(
            select(Goal)
                .where(Goal.category_id == category_id)
                .where(Goal.user_id == user_id)
                .order_by(Goal.created_at.desc())
        )).first()
    

async def get_user_goals(user_id):
    async with DB_ENGINE.begin() as conn:
        all_goals = (await conn.execute(
            select(Goal)
                .where(Goal.user_id == user_id)
                .where(Goal.active == True)
                .order_by(Goal.created_at)
        )).fetchall()

        goals_by_category = {
            goal.category_id: goal
            for goal in all_goals
        }

        return list(goals_by_category.values())


async def ensure_user(discord_user) -> User:
    user = await get_user(discord_user.id)
    if user is None:
        user = await new_user(
            user_id=discord_user.id,
            username=discord_user.name,
        )
    return user


async def get_submission_leaderboard():
    return []


async def select_raw(query, **params):
    async with DB_ENGINE.begin() as conn:
        return (await conn.execute(text(query), params)).fetchall()


@alru_cache()
async def get_categories():
    async with DB_ENGINE.begin() as conn:
        return (await conn.execute(select(Category))).fetchall()
