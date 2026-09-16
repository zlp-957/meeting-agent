import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import init_db
from core.tools import (
    search_rooms, recommend_room, book_room, cancel_booking,
    list_bookings, modify_booking, list_minutes
)

init_db()

TEST_CASES = [
    {
        "name": "查询明天可用会议室",
        "func": lambda: search_rooms.invoke({
            "date": "明天", "start_time": "09:00", "end_time": "10:00", "min_capacity": 5
        }),
        "expect_contains": "可用会议室",
    },
    {
        "name": "智能推荐会议室（基础）",
        "func": lambda: recommend_room.invoke({
            "date": "明天", "start_time": "14:00", "end_time": "16:00",
            "num_people": 10
        }),
        "expect_contains": "推荐",
    },
    {
        "name": "智能推荐会议室（带设备和位置偏好）",
        "func": lambda: recommend_room.invoke({
            "date": "2026-09-20", "start_time": "09:00", "end_time": "11:00",
            "num_people": 15, "required_equipment": "投影仪,视频会议",
            "location_preference": "A座"
        }),
        "expect_contains": "推荐",
    },
    {
        "name": "智能推荐会议室（人数过多无结果）",
        "func": lambda: recommend_room.invoke({
            "date": "明天", "start_time": "14:00", "end_time": "16:00",
            "num_people": 200
        }),
        "expect_contains": "没有",
    },
    {
        "name": "预约会议室（按名称）",
        "func": lambda: book_room.invoke({
            "room_name": "D401", "user_name": "测试用户", "date": "后天",
            "start_time": "10:00", "end_time": "11:00", "title": "单元测试会议"
        }),
        "expect_contains": "预约成功",
    },
    {
        "name": "预约不存在的会议室",
        "func": lambda: book_room.invoke({
            "room_name": "Z999", "user_name": "测试用户", "date": "后天",
            "start_time": "10:00", "end_time": "11:00"
        }),
        "expect_contains": "未找到",
    },
    {
        "name": "查看用户预约列表",
        "func": lambda: list_bookings.invoke({"user_name": "测试用户"}),
        "expect_contains": "有效预约",
    },
    {
        "name": "取消预约",
        "func": lambda: cancel_booking.invoke({"booking_id": 1, "user_name": "测试用户"}),
        "expect_contains": "取消",
    },
    {
        "name": "查询容量不足的会议室",
        "func": lambda: search_rooms.invoke({
            "date": "明天", "start_time": "09:00", "end_time": "10:00", "min_capacity": 100
        }),
        "expect_contains": "没有可用",
    },
    {
        "name": "查看会议纪要列表（空）",
        "func": lambda: list_minutes.invoke({}),
        "expect_contains": "暂无",
    },
]


def run_tests():
    passed = 0
    failed = 0

    for tc in TEST_CASES:
        print(f"\n{'='*50}")
        print(f"测试：{tc['name']}")
        try:
            result = tc["func"]()
            preview = result[:120].replace("\n", " ")
            print(f"结果：{preview}…")

            if tc["expect_contains"] in result:
                print("✅ 通过")
                passed += 1
            else:
                print(f"❌ 失败 - 期望包含「{tc['expect_contains']}」")
                failed += 1
        except Exception as e:
            print(f"❌ 出错 - {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"测试完成：{passed} 通过，{failed} 失败")


if __name__ == "__main__":
    run_tests()