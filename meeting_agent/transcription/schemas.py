"""转录输出数据结构 —— 与主流程 schemas.py 一致以便复用推送流程"""

from meeting_agent.schemas import MeetingOutput, ScheduleItem

__all__ = ["TranscriptionOutput", "ScheduleItem"]


class TranscriptionOutput(MeetingOutput):
    """转录处理输出，字段与 MeetingOutput 一致，可直接复用推送流程。"""
    pass
