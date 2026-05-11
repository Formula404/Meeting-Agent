import json
from pathlib import Path
from meeting_agent.services.message_service import send_meeting_summary_from_result
from meeting_agent.services.schedule_service import create_meeting_schedules_from_result

result = json.loads(Path("data/output/自动发送测试会议_result.json").read_text(encoding="utf-8"))

# 1) 发消息（meeting -> touser/toparty）
# print(send_meeting_summary_from_result(result))

# 2) 建日程（schedules[].start_time/end_time 必须是时间戳）
print(create_meeting_schedules_from_result(result))
