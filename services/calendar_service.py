# Googleカレンダーの操作ロジック
# services/calendar_service.py
from datetime import datetime, timedelta, time
from dateutil.parser import isoparse
import pytz

def fetch_free_times(service, start_date, end_date, day_start_hour, day_end_hour, exclude_holidays, exclude_keywords):
    free_times = {}
    current_date = start_date

    while current_date <= end_date:
        if exclude_holidays and is_holiday(current_date, service):
            current_date += timedelta(days=1)
            continue

        tz = pytz.timezone('Asia/Tokyo')
        day_start = tz.localize(datetime.combine(current_date, time(day_start_hour, 0, 0)))
        day_end = tz.localize(datetime.combine(current_date, time(day_end_hour, 0, 0)))

        # 当日のイベントを取得
        events_result = service.events().list(
            calendarId='primary',
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        # 無視するキーワードに一致するイベントを除外
        filtered_events = []
        for event in events:
            summary = event.get('summary', '')
            if not any(keyword in summary for keyword in exclude_keywords):
                filtered_events.append(event)

        available_start = day_start
        merged_free_times = []

        # イベントを開始時間順に並べ替え
        filtered_events.sort(key=lambda x: parse_event_time(x['start']))

        # 各イベントに基づき空き時間を計算
        for event in filtered_events:
            event_start = parse_event_time(event['start'])
            event_end = parse_event_time(event['end'])

            if available_start < event_start:
                merged_free_times.append((available_start, event_start))

            available_start = max(available_start, event_end)

        if available_start < day_end:
            merged_free_times.append((available_start, day_end))

        # 日付のフォーマット
        day_names = ["月", "火", "水", "木", "金", "土", "日"]
        date_str = current_date.strftime(f"%m月%d日（{day_names[current_date.weekday()]}）")

        # 日付ごとに空き時間を追加
        if merged_free_times:
            if date_str not in free_times:
                free_times[date_str] = []
            for start, end in merged_free_times:
                time_range = format_time_range(start, end)
                free_times[date_str].append(time_range)

        current_date += timedelta(days=1)

    return free_times


def parse_event_time(event_time):
    if 'dateTime' in event_time:
        return isoparse(event_time['dateTime'])
    else:
        return isoparse(event_time['date'])


def is_holiday(date, service):
    # 土曜日または日曜日ならTrueを返す
    if date.weekday() == 5 or date.weekday() == 6:  # 土曜日（5）、日曜日（6）
        return True

    # 祝日カレンダーID (GoogleカレンダーAPI)
    holidays_calendar_id = 'ja.japanese#holiday@group.v.calendar.google.com'
    
    # タイムゾーンを東京に設定
    tz = pytz.timezone('Asia/Tokyo')
    
    # その日の始まりと終わりの時間を設定
    day_start = tz.localize(datetime.combine(date, time(0, 0, 0)))
    day_end = tz.localize(datetime.combine(date, time(23, 59, 59)))

    # Googleカレンダーから当日のイベント（休日）を取得
    events_result = service.events().list(
        calendarId=holidays_calendar_id,
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    # 祝日イベントがあればTrueを返す
    holidays = events_result.get('items', [])
    return len(holidays) > 0


def format_time_range(start_time, end_time):
    formatted_start = start_time.astimezone(pytz.timezone('Asia/Tokyo')).strftime("%H:%M")
    formatted_end = end_time.astimezone(pytz.timezone('Asia/Tokyo')).strftime("%H:%M")
    return f"{formatted_start}～{formatted_end}"
