from meeting_agent.integrations.wecom_client import wecom_client


def create_meeting_schedule(
    userids: list[str],
    title: str,
    description: str,
    start_time: int,
    end_time: int,
    location: str = "",
) -> dict:
    return wecom_client.create_schedule(
        attendees=userids,
        summary=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        location=location,
        admins=userids[:1],
    )