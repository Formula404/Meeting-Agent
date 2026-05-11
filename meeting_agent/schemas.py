from typing import List
from pydantic import BaseModel, Field


class ScheduleItem(BaseModel):
    title: str = Field(default="", description="日程或待办标题")
    owner: List[str] = Field(default="", description="负责人")
    start_time: str = Field(default="", description="开始时间，没有则为空字符串")
    end_time: str = Field(default="", description="结束时间，没有则为空字符串")
    description: str = Field(default="", description="事项说明")


class MeetingOutput(BaseModel):
    meeting_date: str = Field(default="", description="会议时间")
    push_dept: List[str] = Field(default_factory=list, description="需要推送会议纪要的部门")
    push_user: List[str] = Field(default_factory=list, description="需要推送会议纪要的用户")
    schedules: List[ScheduleItem] = Field(default_factory=list, description="需要创建的日程或待办")
    meeting: str = Field(default="", description="整理后的正式会议纪要")