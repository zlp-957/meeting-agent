import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import engine, Base, SessionLocal, Room, Booking


TEST_ROOMS = [
    {"name": "A301", "capacity": 10, "equipment": "投影仪,白板", "location": "A座3层"},
    {"name": "A302", "capacity": 20, "equipment": "投影仪,白板,视频会议设备", "location": "A座3层"},
    {"name": "B201", "capacity": 8, "equipment": "电视屏,白板", "location": "B座2层"},
    {"name": "B202", "capacity": 15, "equipment": "投影仪,视频会议设备", "location": "B座2层"},
    {"name": "C108", "capacity": 6, "equipment": "电视屏", "location": "C座1层"},
    {"name": "C205", "capacity": 30, "equipment": "投影仪,白板,视频会议设备,音响系统", "location": "C座2层"},
    {"name": "D401", "capacity": 12, "equipment": "投影仪,白板", "location": "D座4层"},
    {"name": "D402", "capacity": 50, "equipment": "投影仪,白板,视频会议设备,音响系统,舞台灯光", "location": "D座4层"},
]


def create_test_data():
    Base.metadata.create_all(engine)

    db = SessionLocal()

    if db.query(Room).count() > 0:
        print("数据库已有数据，跳过初始化。如需重建请先删除 data/meeting.db")
        db.close()
        return

    for room_data in TEST_ROOMS:
        room = Room(**room_data)
        db.add(room)

    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    test_bookings = [
        {"room_id": 1, "user_name": "张三", "title": "产品周会",
         "start_time": now + timedelta(days=1, hours=9),
         "end_time": now + timedelta(days=1, hours=10, minutes=30)},
        {"room_id": 1, "user_name": "李四", "title": "设计评审",
         "start_time": now + timedelta(days=1, hours=14),
         "end_time": now + timedelta(days=1, hours=15)},
        {"room_id": 2, "user_name": "王五", "title": "全员大会",
         "start_time": now + timedelta(days=2, hours=10),
         "end_time": now + timedelta(days=2, hours=12)},
        {"room_id": 5, "user_name": "赵六", "title": "客户演示",
         "start_time": now + timedelta(days=1, hours=14),
         "end_time": now + timedelta(days=1, hours=15)},
        {"room_id": 6, "user_name": "钱七", "title": "技术分享",
         "start_time": now + timedelta(days=3, hours=15),
         "end_time": now + timedelta(days=3, hours=17)},
    ]

    for booking_data in test_bookings:
        booking = Booking(**booking_data, status="active")
        db.add(booking)

    db.commit()
    db.close()

    print("数据库初始化完成！")
    print(f"  - 会议室：{len(TEST_ROOMS)} 间")
    print(f"  - 测试预约：{len(test_bookings)} 条")
    print(f"  - 数据库路径：{os.path.join(os.path.dirname(__file__), 'meeting.db')}")


if __name__ == "__main__":
    create_test_data()