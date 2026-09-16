from datetime import datetime, timedelta
from langchain_core.tools import tool
from core.database import SessionLocal, Room, Booking, MeetingMinutes


def _parse_datetime(date_str: str, time_str: str = "00:00") -> datetime:
    date_str = date_str.strip()
    time_str = time_str.strip()

    today = datetime.now()
    low = date_str.lower()

    if low in ("today", "今天"):
        d = today
    elif low in ("tomorrow", "明天"):
        d = today + timedelta(days=1)
    elif low in ("后天",):
        d = today + timedelta(days=2)
    elif low.startswith("next week") or low == "下周":
        d = today + timedelta(days=7)
    else:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m-%d", "%m/%d"):
            try:
                parsed = datetime.strptime(date_str, fmt)
                if fmt in ("%m-%d", "%m/%d"):
                    parsed = parsed.replace(year=today.year)
                d = parsed
                break
            except ValueError:
                continue
        else:
            d = today

    hour, minute = 0, 0
    for tfmt in ("%H:%M", "%H%M", "%H"):
        try:
            t = datetime.strptime(time_str, tfmt)
            hour, minute = t.hour, t.minute
            break
        except ValueError:
            continue

    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _format_room(room: Room) -> str:
    return (f"会议室 {room.name} | 容纳{room.capacity}人 | 设备：{room.equipment} | "
            f"位置：{room.location} | 编号:{room.id}")


def _get_available_rooms(start: datetime, end: datetime, min_capacity: int = 1):
    """获取指定时间段内可用的会议室列表（内部方法）。"""
    db = SessionLocal()
    try:
        all_rooms = db.query(Room).filter(Room.is_active == True, Room.capacity >= min_capacity).all()

        booked_room_ids = set()
        for b in db.query(Booking).filter(Booking.status == "active").all():
            if start < b.end_time and end > b.start_time:
                booked_room_ids.add(b.room_id)

        available = [r for r in all_rooms if r.id not in booked_room_ids]
        return available
    finally:
        db.close()


@tool
def search_rooms(date: str, start_time: str, end_time: str, min_capacity: int = 1) -> str:
    """查询指定时间段内可用的会议室。

    参数:
        date: 日期，如"2026-09-15"、"明天"、"今天"
        start_time: 开始时间，如"14:00"
        end_time: 结束时间，如"16:00"
        min_capacity: 最少容纳人数，默认1

    返回: 可用会议室列表，包含会议室名称和编号
    """
    dt = _parse_datetime(date)
    start = _parse_datetime(date, start_time)
    end = _parse_datetime(date, end_time)

    if end <= start:
        return "错误：结束时间必须晚于开始时间。"

    available = _get_available_rooms(start, end, min_capacity)

    if not available:
        return (f"{dt.strftime('%m月%d日')} {start_time}-{end_time} 没有可用的会议室"
                f"（需容纳{min_capacity}人以上）。请尝试其他时间段或减少人数要求。")

    lines = [f"找到 {len(available)} 间可用会议室（{dt.strftime('%m月%d日')} {start_time}-{end_time}）："]
    for r in available:
        lines.append(f"  - {_format_room(r)}")
    lines.append("\n提示：如需预约，请使用预约工具，传入会议室名称（如 D402）。")
    return "\n".join(lines)


@tool
def recommend_room(date: str, start_time: str, end_time: str, num_people: int,
                   required_equipment: str = "", location_preference: str = "") -> str:
    """智能推荐最合适的会议室。根据人数、设备需求、位置偏好等多维度综合评分排序。
    当用户没有指定具体会议室、只说需求时，使用此工具推荐最优选择。

    参数:
        date: 日期，如"明天"、"2026-09-15"
        start_time: 开始时间，如"14:00"
        end_time: 结束时间，如"16:00"
        num_people: 参会人数
        required_equipment: 必需的设备，多个用逗号分隔，如"投影仪,视频会议"，可选
        location_preference: 位置偏好，如"A座"、"靠近电梯"，可选

    返回: 按推荐度排序的会议室列表（Top3），包含评分和推荐理由
    """
    start = _parse_datetime(date, start_time)
    end = _parse_datetime(date, end_time)

    if end <= start:
        return "错误：结束时间必须晚于开始时间。"

    if num_people <= 0:
        return "错误：参会人数必须大于0。"

    available = _get_available_rooms(start, end, num_people)

    if not available:
        return (f"{start.strftime('%m月%d日')} {start_time}-{end_time} 没有能容纳{num_people}人的会议室。"
                f"建议尝试其他时间段，或使用查询工具看看有没有稍小的会议室可以加座。")

    # 解析必需设备
    required = [e.strip() for e in required_equipment.split(",") if e.strip()] if required_equipment else []

    # 多维度评分
    scored = []
    for room in available:
        score = 0.0
        reasons = []

        # 1. 容量匹配度（40分）：人数刚好略大于需求最佳，过大浪费扣分
        capacity_ratio = room.capacity / max(num_people, 1)
        if 1.0 <= capacity_ratio <= 1.3:
            score += 40
            reasons.append("容量刚好合适")
        elif 1.3 < capacity_ratio <= 2.0:
            score += 30
            reasons.append("容量稍大但不浪费")
        elif capacity_ratio > 2.0:
            score += 15
            reasons.append("容量偏大")
        else:
            score += 0
            reasons.append("容量不足")

        # 2. 设备匹配度（30分）
        room_equip = [e.strip() for e in room.equipment.split(",") if e.strip()]
        if required:
            matched = sum(1 for e in required if e in room_equip)
            equip_score = int(30 * matched / len(required))
            score += equip_score
            if matched == len(required):
                reasons.append("设备完全满足需求")
            elif matched > 0:
                reasons.append(f"满足{matched}/{len(required)}项设备需求")
            else:
                reasons.append("设备不满足需求")
        else:
            score += 15  # 无特殊设备需求时，设备齐全的加基础分
            if len(room_equip) >= 3:
                score += 10
                reasons.append("设备齐全")
            elif len(room_equip) >= 2:
                score += 5
                reasons.append("设备较齐全")

        # 3. 位置偏好（20分）
        if location_preference:
            if location_preference in room.location:
                score += 20
                reasons.append("位置符合偏好")
            elif room.location.startswith(location_preference[0]):
                score += 10
                reasons.append("位置接近偏好")
            else:
                score += 0
                reasons.append("位置不符偏好")
        else:
            score += 10  # 无偏好时给中间分

        # 4. 楼层便利性（10分）：楼层越低越方便（假设）
        try:
            floor_num = int(''.join(c for c in room.name if c.isdigit())[:1])
            # 3-4楼适中，2楼次之，越高越不方便
            if 2 <= floor_num <= 3:
                score += 10
                reasons.append("楼层适中")
            elif floor_num <= 1:
                score += 8
                reasons.append("低楼层便利")
            else:
                score += 5
                reasons.append("高楼层")
        except (ValueError, IndexError):
            score += 5

        scored.append((score, room, reasons))

    # 按分数降序排列
    scored.sort(key=lambda x: x[0], reverse=True)
    top3 = scored[:3]

    lines = [f"为你推荐以下 {len(top3)} 间会议室（{start.strftime('%m月%d日')} {start_time}-{end_time}，"
             f"{num_people}人）："]
    lines.append("")

    for i, (score, room, reasons) in enumerate(top3, 1):
        stars = "★" * int(round(score / 20))  # 5星制
        lines.append(f"  第{i}名：{room.name}  {stars}（综合评分：{score:.0f}/100）")
        lines.append(f"        容量：{room.capacity}人  |  设备：{room.equipment}")
        lines.append(f"        位置：{room.location}")
        lines.append(f"        推荐理由：{'、'.join(reasons[:3])}")
        lines.append("")

    best = top3[0][1]
    lines.append(f"💡 最推荐：{best.name}（{best.capacity}人，{best.location}）")
    lines.append("   如需预约，直接告诉我「预约{best.name}」即可。".format(best=best))

    return "\n".join(lines)


@tool
def book_room(room_name: str, user_name: str, date: str, start_time: str, end_time: str,
              title: str = "会议") -> str:
    """预约指定会议室。用户说出会议室名称即可，无需使用数字编号。

    参数:
        room_name: 会议室名称（如 A301、B202、D402），直接使用名称，不要用数字编号
        user_name: 预约人姓名
        date: 日期，如"2026-09-15"、"明天"
        start_time: 开始时间，如"14:00"
        end_time: 结束时间，如"16:00"
        title: 会议主题，默认"会议"

    返回: 预约结果
    """
    start = _parse_datetime(date, start_time)
    end = _parse_datetime(date, end_time)

    if end <= start:
        return "错误：结束时间必须晚于开始时间。"

    if (end - start).total_seconds() > 4 * 3600:
        return "错误：单次预约不得超过4小时。"

    db = SessionLocal()
    try:
        room = db.query(Room).filter(
            Room.name == room_name.strip(),
            Room.is_active == True
        ).first()

        if not room:
            all_rooms = db.query(Room).filter(Room.is_active == True).all()
            names = "、".join([r.name for r in all_rooms])
            return f"错误：未找到名为「{room_name}」的会议室。可用会议室有：{names}"

        conflict = db.query(Booking).filter(
            Booking.room_id == room.id,
            Booking.status == "active",
            Booking.start_time < end,
            Booking.end_time > start
        ).first()

        if conflict:
            return (f"预约失败：{room.name} 在 {start.strftime('%m月%d日 %H:%M')}-{end.strftime('%H:%M')} "
                    f"已被「{conflict.title}」占用（预约人：{conflict.user_name}）。"
                    f"请选择其他时间段或其他会议室。")

        booking = Booking(
            room_id=room.id,
            user_name=user_name,
            title=title,
            start_time=start,
            end_time=end,
            status="active"
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)

        return (f"预约成功！\n"
                f"  会议室：{room.name}（{room.capacity}人，{room.equipment}）\n"
                f"  时间：{start.strftime('%Y年%m月%d日 %H:%M')}-{end.strftime('%H:%M')}\n"
                f"  主题：{title}\n"
                f"  预约号：#{booking.id:06d}")
    finally:
        db.close()


@tool
def cancel_booking(booking_id: int, user_name: str) -> str:
    """取消预约。需提供预约号和预约人姓名验证身份。

    参数:
        booking_id: 预约编号
        user_name: 预约人姓名

    返回: 取消结果
    """
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return f"错误：未找到预约号为#{booking_id:06d}的预约记录。"

        if booking.status == "cancelled":
            return f"预约#{booking_id:06d}已经被取消了，无需重复操作。"

        if booking.user_name != user_name:
            return f"错误：预约人姓名不匹配，无法取消他人的预约。"

        now = datetime.now()
        is_late_cancel = booking.start_time - now < timedelta(hours=2)

        booking.status = "cancelled"
        db.commit()

        if is_late_cancel:
            return (f"已取消预约 #{booking_id:06d}。\n"
                    f"  会议：{booking.title}\n"
                    f"  时间：{booking.start_time.strftime('%m月%d日 %H:%M')}-"
                    f"{booking.end_time.strftime('%H:%M')}\n"
                    f"  注意：距开始时间不足2小时，属于「迟取消」。"
                    f"累计3次迟取消将暂停预约权限1周。")
        else:
            return (f"已成功取消预约 #{booking_id:06d}。\n"
                    f"  会议：{booking.title}\n"
                    f"  时间：{booking.start_time.strftime('%m月%d日 %H:%M')}-"
                    f"{booking.end_time.strftime('%H:%M')}")
    finally:
        db.close()


@tool
def list_bookings(user_name: str) -> str:
    """查看指定用户的所有有效预约。

    参数:
        user_name: 用户姓名

    返回: 预约列表
    """
    db = SessionLocal()
    try:
        bookings = db.query(Booking).filter(
            Booking.user_name == user_name,
            Booking.status == "active"
        ).order_by(Booking.start_time).all()

        if not bookings:
            return f"{user_name} 当前没有有效预约。"

        lines = [f"{user_name} 的有效预约（共{len(bookings)}条）："]
        for b in bookings:
            room = db.query(Room).filter(Room.id == b.room_id).first()
            room_name = room.name if room else "未知"
            lines.append(
                f"  #{b.id:06d} | {room_name} | "
                f"{b.start_time.strftime('%m月%d日 %H:%M')}-{b.end_time.strftime('%H:%M')} | "
                f"{b.title}"
            )
        return "\n".join(lines)
    finally:
        db.close()


@tool
def modify_booking(booking_id: int, user_name: str, new_date: str,
                    new_start_time: str, new_end_time: str) -> str:
    """修改已有预约的时间。需验证预约人身份。注意：此工具只能修改时间，不能更换会议室。

    参数:
        booking_id: 预约编号
        user_name: 预约人姓名
        new_date: 新日期
        new_start_time: 新开始时间
        new_end_time: 新结束时间

    返回: 修改结果
    """
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return f"错误：未找到预约号为#{booking_id:06d}的记录。"

        if booking.status != "active":
            return f"错误：预约#{booking_id:06d}不是有效预约，无法修改。"

        if booking.user_name != user_name:
            return f"错误：预约人姓名不匹配，无法修改他人的预约。"

        new_start = _parse_datetime(new_date, new_start_time)
        new_end = _parse_datetime(new_date, new_end_time)

        if new_end <= new_start:
            return "错误：结束时间必须晚于开始时间。"

        if (new_end - new_start).total_seconds() > 4 * 3600:
            return "错误：单次预约不得超过4小时。"

        conflict = db.query(Booking).filter(
            Booking.room_id == booking.room_id,
            Booking.status == "active",
            Booking.id != booking_id,
            Booking.start_time < new_end,
            Booking.end_time > new_start
        ).first()

        if conflict:
            room = db.query(Room).filter(Room.id == booking.room_id).first()
            room_name = room.name if room else "未知"
            return (f"修改失败：{room_name} 在 {new_start.strftime('%m月%d日 %H:%M')}-"
                    f"{new_end.strftime('%H:%M')} 已被「{conflict.title}」占用。"
                    f"请选择其他时间段。")

        old_time = f"{booking.start_time.strftime('%m月%d日 %H:%M')}-{booking.end_time.strftime('%H:%M')}"
        booking.start_time = new_start
        booking.end_time = new_end
        db.commit()

        room = db.query(Room).filter(Room.id == booking.room_id).first()
        room_name = room.name if room else "未知"
        return (f"预约#{booking_id:06d}已成功修改！\n"
                f"  会议室：{room_name}\n"
                f"  原时间：{old_time}\n"
                f"  新时间：{new_start.strftime('%m月%d日 %H:%M')}-{new_end.strftime('%H:%M')}\n"
                f"  主题：{booking.title}")
    finally:
        db.close()


@tool
def generate_minutes(booking_id: int, raw_notes: str, host: str = "",
                      attendees: str = "") -> str:
    """根据会议原始笔记生成结构化会议纪要。
    用户提供预约号和会议过程中记录的要点/速记，工具自动整理成规范的会议纪要。

    参数:
        booking_id: 预约编号（用于关联预约信息获取会议室、时间、主题等）
        raw_notes: 会议原始笔记/速记内容，越详细越好
        host: 主持人姓名，可选
        attendees: 参会人员名单，多个用顿号分隔，可选

    返回: 结构化的会议纪要
    """
    db = SessionLocal()
    try:
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            return f"错误：未找到预约号为#{booking_id:06d}的记录。"

        room = db.query(Room).filter(Room.id == booking.room_id).first()
        room_name = room.name if room else "未知"

        # 调用 LLM 生成结构化纪要
        from core.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=DEEPSEEK_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.3,
            max_tokens=1500,
        )

        prompt = f"""请根据以下会议信息和原始笔记，生成一份结构化的中文会议纪要。

【会议基本信息】
- 主题：{booking.title}
- 时间：{booking.start_time.strftime('%Y年%m月%d日 %H:%M')}-{booking.end_time.strftime('%H:%M')}
- 地点：{room_name}
- 主持人：{host or booking.user_name}
- 参会人员：{attendees or "（未提供）"}

【原始会议笔记】
{raw_notes}

请按以下格式输出会议纪要（不要使用Markdown代码块，直接输出文本）：

--- 会议纪要 ---
会议主题：...
会议时间：...
会议地点：...
主持人：...
参会人员：...

一、会议概述
（2-3句话总结会议的目的和主要内容）

二、讨论要点
1. 要点一：...
2. 要点二：...
3. 要点三：...
（根据内容提取主要讨论的议题和结论，3-6条）

三、待办事项
1. [负责人] 任务描述 - 截止时间
2. [负责人] 任务描述 - 截止时间
（从笔记中提取明确的行动项，如果没有明确负责人则标注"待确认"，3-8条）

四、下次会议安排
（如果提到了下次会议，写明时间和议题；如果没有提到则写"待定"）
--- 纪要结束 ---
"""
        response = llm.invoke(prompt)
        minutes_text = response.content.strip()

        # 解析纪要内容并存储到数据库
        summary = ""
        key_points = ""
        action_items = ""
        next_meeting = ""

        if "一、会议概述" in minutes_text and "二、讨论要点" in minutes_text:
            start_idx = minutes_text.index("一、会议概述") + len("一、会议概述")
            end_idx = minutes_text.index("二、讨论要点")
            summary = minutes_text[start_idx:end_idx].strip()

        if "二、讨论要点" in minutes_text and "三、待办事项" in minutes_text:
            start_idx = minutes_text.index("二、讨论要点") + len("二、讨论要点")
            end_idx = minutes_text.index("三、待办事项")
            key_points = minutes_text[start_idx:end_idx].strip()

        if "三、待办事项" in minutes_text and "四、下次会议安排" in minutes_text:
            start_idx = minutes_text.index("三、待办事项") + len("三、待办事项")
            end_idx = minutes_text.index("四、下次会议安排")
            action_items = minutes_text[start_idx:end_idx].strip()

        if "四、下次会议安排" in minutes_text:
            start_idx = minutes_text.index("四、下次会议安排") + len("四、下次会议安排")
            end_idx = minutes_text.find("--- 纪要结束 ---", start_idx)
            if end_idx == -1:
                end_idx = len(minutes_text)
            next_meeting = minutes_text[start_idx:end_idx].strip()

        minutes_record = MeetingMinutes(
            booking_id=booking_id,
            room_name=room_name,
            title=booking.title,
            host=host or booking.user_name,
            attendees=attendees,
            meeting_date=booking.start_time.date(),
            start_time=booking.start_time.strftime("%H:%M"),
            end_time=booking.end_time.strftime("%H:%M"),
            summary=summary,
            key_points=key_points,
            action_items=action_items,
            next_meeting=next_meeting,
            raw_notes=raw_notes,
        )
        db.add(minutes_record)
        db.commit()
        db.refresh(minutes_record)

        return minutes_text
    finally:
        db.close()


@tool
def list_minutes(user_name: str = "") -> str:
    """查看已生成的会议纪要列表。

    参数:
        user_name: 按主持人筛选，可选；不填则返回所有纪要

    返回: 会议纪要列表
    """
    db = SessionLocal()
    try:
        query = db.query(MeetingMinutes)
        if user_name:
            query = query.filter(MeetingMinutes.host == user_name)

        minutes_list = query.order_by(MeetingMinutes.meeting_date.desc()).all()

        if not minutes_list:
            return "暂无会议纪要记录。"

        lines = [f"会议纪要列表（共{len(minutes_list)}条，按时间倒序）："]
        for m in minutes_list:
            lines.append(
                f"  纪要#{m.id:03d} | {m.meeting_date.strftime('%m月%d日')} | "
                f"{m.title} | {m.room_name} | 主持人：{m.host}"
            )
        lines.append("\n提示：如需查看某条纪要详情，告诉我纪要编号即可。")
        return "\n".join(lines)
    finally:
        db.close()


ALL_TOOLS = [
    search_rooms,
    recommend_room,
    book_room,
    cancel_booking,
    list_bookings,
    modify_booking,
    generate_minutes,
    list_minutes,
]
