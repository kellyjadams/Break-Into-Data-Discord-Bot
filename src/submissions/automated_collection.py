import asyncio
import logging
import uuid

import aiohttp

from src.models import ExternalPlatformConnection
from src.database import list_external_platform_connections


logger = logging.getLogger(__name__)


async def _fetch_external_platform_data(
    session: aiohttp.ClientSession, 
    platform_connection: ExternalPlatformConnection
):
    try:
        result = await session.post("/graphql/", data={
            "query": "\\n    query userProfileUserQuestionProgressV2($userSlug: String!) {\\n  userProfileUserQuestionProgressV2(userSlug: $userSlug) {\\n    numAcceptedQuestions {\\n      count\\n      difficulty\\n    }\\n    numFailedQuestions {\\n      count\\n      difficulty\\n    }\\n    numUntouchedQuestions {\\n      count\\n      difficulty\\n    }\\n    userSessionBeatsPercentage {\\n      difficulty\\n      percentage\\n    }\\n  }\\n}\\n    ",
            "variables": {
                "userSlug": "MeriB"
            },
            "operationName":"userProfileUserQuestionProgressV2",
        })
    except aiohttp.ClientError:
        logger.exception("Failed to fetch data from external platform")
        return False
    
    # if result.status != 200:
    #     logger.error("Got unexpected status code %s", result.status)
    #     return
    
    data = await result.text()
    print(data)
    
    breakpoint()
    pass
        



async def collect_submissions_automatically():
    import asyncio

    cookies = {
        'csrftoken': 'M1SsgydRAwcfLxZZNSNcBuqaqYTQ3oRSZzNyOQtOMXbULB87VbCDFp99uJEcGsuV',
        '__stripe_mid': 'd18bfeda-10d2-4d62-9f27-0cafa6b7c158ed2e24',
        'INGRESSCOOKIE': 'daff9bd763fbd659375da78942f59d34|8e0876c7c1464cc0ac96bc2edceabd27',
        '__cf_bm': 'bSk.zmmHhriwesxGxkZ05a8AGAExthWRZ6L8NWIduQg-1717965810-1.0.1.1-VsiE0c6gv8sJbv0IovVUZDJk21QaPynW1XgjyMVbobDp7EYNwfWfh9xH416dFczox87tDuE0RxOFLQ1LVBkm3g',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': '',
        'content-type': 'application/json',
        'dnt': '1',
        'origin': 'https://leetcode.com',
        'priority': 'u=1, i',
        'random-uuid': '2db86894-ba38-76ba-b586-1894c58e2531',
        'referer': 'https://leetcode.com/u/MeriB/',
        'sec-ch-ua': '"Chromium";v="125", "Not.A/Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'x-csrftoken': 'M1SsgydRAwcfLxZZNSNcBuqaqYTQ3oRSZzNyOQtOMXbULB87VbCDFp99uJEcGsuV',
    }

    json_data = {
        'query': '''
            query getUserProfile($username: String!) {
                matchedUser(username: $username) {
                    activeBadge {
                        displayName
                        icon
                    }
                }
            }
        ''',
        'variables': {
            'username': 'MeriB',
        },
        'operationName': 'getUserProfile',
    }

    async with aiohttp.ClientSession() as session:
        async with session.post('https://leetcode.com/graphql/', cookies=cookies, headers=headers, json=json_data) as response:
            data = await response.json()


    
    
    
    while True:
        session = aiohttp.ClientSession(
            base_url="https://leetcode.com/",
            headers=headers,
            cookies=cookies,
        )
        
        external_connection = await list_external_platform_connections()
        
        async with session:            
            for external_connection in external_connection:
                await _fetch_external_platform_data(
                    session, external_connection
                )
        
        await asyncio.sleep(60 * 60 * 24)
