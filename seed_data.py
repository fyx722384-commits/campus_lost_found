import os
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from database import DB_PATH, db


def reset_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    db.init_db()


def users_table_empty():
    row = db.query_one("SELECT COUNT(*) AS count FROM users")
    return not row or row["count"] == 0


def add_user(username, password, role="user", phone=""):
    return db.insert(
        "INSERT INTO users (username, password, role, phone, created_at) VALUES (?, ?, ?, ?, ?)",
        (username, generate_password_hash(password), role, phone, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )


def add_item(user_id, title, item_type, category, location, days_ago, description, contact, status="待认领", archived=0):
    event_time = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M")
    return db.insert(
        """
        INSERT INTO items
        (user_id, title, item_type, category, location, event_time, description, contact, image_path, status, created_at, archived)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?)
        """,
        (
            user_id,
            title,
            item_type,
            category,
            location,
            event_time,
            description,
            contact,
            status,
            (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S"),
            archived,
        ),
    )


def add_claim(item_id, applicant_id, reason, contact, status="待审核"):
    reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status != "待审核" else None
    return db.insert(
        """
        INSERT INTO claims (item_id, applicant_id, reason, contact, status, created_at, reviewed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            applicant_id,
            reason,
            contact,
            status,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            reviewed_at,
        ),
    )


def add_priority(item_id, user_id, level, reason, fee_amount, pay_status, status="待审核", hours=24):
    now = datetime.now()
    reviewed_at = now.strftime("%Y-%m-%d %H:%M:%S") if status != "待审核" else None
    expire_at = (now + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S") if status == "已通过" else None
    return db.insert(
        """
        INSERT INTO priority_requests
        (item_id, user_id, level, reason, fee_amount, pay_status, status, created_at, reviewed_at, expire_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            user_id,
            level,
            reason,
            fee_amount,
            pay_status,
            status,
            now.strftime("%Y-%m-%d %H:%M:%S"),
            reviewed_at,
            expire_at,
        ),
    )


def add_notification(user_id, title, content, notification_type, is_read=0, related_type="", related_id=None):
    return db.insert(
        """
        INSERT INTO notifications
        (user_id, title, content, notification_type, is_read, related_type, related_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            title,
            content,
            notification_type,
            is_read,
            related_type,
            related_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )


def notifications_table_empty():
    row = db.query_one("SELECT COUNT(*) AS count FROM notifications")
    return not row or row["count"] == 0


def ensure_demo_notifications():
    if not notifications_table_empty():
        return False
    student = db.query_one("SELECT id FROM users WHERE username = ?", ("student",))
    alice = db.query_one("SELECT id FROM users WHERE username = ?", ("xiaolin",))
    admin = db.query_one("SELECT id FROM users WHERE username = ?", ("admin",))
    if not student or not alice or not admin:
        return False
    add_notification(
        student["id"],
        "认领申请已通过",
        "你提交的【蓝色校园卡】认领申请已通过，请及时联系管理员或发布者完成领取。",
        "认领审核",
        0,
        "claim",
        None,
    )
    add_notification(
        student["id"],
        "认领申请已驳回",
        "你提交的【身份证】认领申请未通过，请补充有效证明后再尝试。",
        "认领审核",
        0,
        "claim",
        None,
    )
    add_notification(
        student["id"],
        "加急寻物申请已通过",
        "你的【蓝色校园卡】加急寻物申请已通过，系统将优先展示并提高匹配排序。",
        "加急审核",
        0,
        "priority",
        None,
    )
    add_notification(
        admin["id"],
        "系统提醒",
        "管理员后台已启用待审核事项和未读通知提醒，可在首页快速进入处理。",
        "系统提醒",
        0,
        "system",
        None,
    )
    add_notification(
        alice["id"],
        "物品已完成归还",
        "你认领的【高等数学教材】已完成归还流程，感谢使用湖北汽车工业学院校园失物招领系统。",
        "认领审核",
        1,
        "claim",
        None,
    )
    return True


def seed_demo_data():
    admin = add_user("admin", "admin123", "admin", "13800000000")
    student = add_user("student", "student123", "user", "13900000001")
    alice = add_user("xiaolin", "123456", "user", "13900000002")
    bob = add_user("mingming", "123456", "user", "13900000003")
    cathy = add_user("xiaoyu", "123456", "user", "13900000004")
    david = add_user("haoran", "123456", "user", "13900000005")
    users = [student, alice, bob, cathy, david]

    item_specs = [
        (student, "蓝色校园卡", "失物", "校园卡", "图书馆二楼自习区", 0, "校园卡套是蓝色透明壳，卡面姓名被贴纸遮住一部分。", "13900000001"),
        (alice, "拾到蓝色校园卡", "招领", "校园卡", "图书馆二楼", 0, "在二楼靠窗座位捡到一张蓝色卡套校园卡。", "13900000002"),
        (bob, "黑色无线耳机", "失物", "电子产品", "第一教学楼 302", 1, "耳机盒有轻微划痕，品牌标志在正面。", "13900000003"),
        (cathy, "拾到无线耳机盒", "招领", "电子产品", "一教 302 教室", 1, "课后在桌洞里发现一个黑色无线耳机盒。", "13900000004"),
        (david, "透明雨伞", "失物", "生活用品", "食堂一楼", 2, "长柄透明雨伞，伞柄处贴有姓名缩写。", "13900000005"),
        (student, "食堂拾到透明雨伞", "招领", "生活用品", "一食堂门口", 2, "雨停后在食堂门口看到一把透明伞，已放到值班处。", "13900000001"),
        (alice, "高等数学教材", "失物", "书籍", "三号楼 105", 3, "教材内页夹了一张课程表，封面写有 2025 级。", "13900000002"),
        (bob, "拾到高数教材", "招领", "书籍", "三号教学楼 105", 3, "座位下捡到一本高等数学教材，里面有课程表。", "13900000003"),
        (cathy, "宿舍钥匙一串", "失物", "钥匙", "操场看台", 4, "钥匙圈上有一个绿色小挂件，共三把钥匙。", "13900000004"),
        (david, "拾到绿色挂件钥匙", "招领", "钥匙", "操场看台西侧", 4, "一串带绿色挂件的钥匙，交给体育部值班同学。", "13900000005"),
        (student, "身份证", "失物", "证件", "校医院门口", 1, "可能在排队缴费时遗失，证件套为灰色。", "13900000001"),
        (alice, "校医院拾到证件", "招领", "证件", "校医院大厅", 1, "大厅椅子旁边拾到一张身份证，已交前台。", "13900000002"),
        (bob, "白色充电宝", "失物", "电子产品", "图书馆四楼", 5, "10000mAh 白色充电宝，边角有贴纸残留。", "13900000003"),
        (cathy, "图书馆拾到充电宝", "招领", "电子产品", "图书馆四楼阅览区", 5, "白色移动电源，旁边没有同学认领。", "13900000004"),
        (david, "黑框眼镜", "失物", "生活用品", "实验楼 B204", 2, "黑色方框眼镜，镜盒是深蓝色。", "13900000005"),
        (student, "拾到黑框眼镜", "招领", "生活用品", "实验楼 B204", 2, "实验课后在靠门座位发现黑框眼镜。", "13900000001"),
        (alice, "银色 U 盘", "失物", "电子产品", "机房 506", 6, "银色金属 U 盘，里面有课程设计资料。", "13900000002"),
        (bob, "机房拾到 U 盘", "招领", "电子产品", "信息楼机房 506", 6, "一枚银色 U 盘，已交给机房管理员。", "13900000003"),
        (cathy, "粉色水杯", "失物", "生活用品", "二食堂二楼", 0, "粉色保温杯，杯盖有小贴纸。", "13900000004"),
        (david, "拾到粉色水杯", "招领", "生活用品", "二食堂二楼靠窗", 0, "午饭后桌上留下一个粉色保温杯。", "13900000005"),
        (student, "英语四级词汇书", "失物", "书籍", "图书馆三楼", 7, "书内有彩色便签和手写笔记。", "13900000001"),
        (alice, "拾到四级词汇书", "招领", "书籍", "图书馆三楼", 7, "靠走廊座位拾到一本四级词汇书。", "13900000002"),
        (bob, "黑色双肩包", "失物", "生活用品", "篮球场", 8, "包里有运动服和一瓶水。", "13900000003", "已归档", 1),
        (cathy, "拾到校园卡挂绳", "招领", "校园卡", "北门快递点", 1, "只有挂绳和卡套，没有卡片。", "13900000004"),
    ]

    item_ids = []
    for spec in item_specs:
        item_ids.append(add_item(*spec))

    claim_specs = [
        (item_ids[1], student, "我丢失的校园卡是蓝色透明卡套，卡套背面有贴纸。", "13900000001", "待审核"),
        (item_ids[3], bob, "耳机盒正面有划痕，我能说出连接设备名称。", "13900000003", "已通过"),
        (item_ids[5], david, "透明伞伞柄贴着我的姓名缩写。", "13900000005", "已完成"),
        (item_ids[7], alice, "书里夹着我的课程表，首页有笔记。", "13900000002", "待审核"),
        (item_ids[9], cathy, "钥匙圈有绿色挂件，三把钥匙分别是宿舍和柜子。", "13900000004", "已驳回"),
        (item_ids[11], student, "证件套是灰色，我能提供身份证后四位。", "13900000001", "待审核"),
        (item_ids[13], bob, "充电宝角落有贴纸残留，容量是 10000mAh。", "13900000003", "待审核"),
        (item_ids[17], alice, "U 盘里有课程设计资料和我的姓名文件夹。", "13900000002", "已通过"),
    ]
    for spec in claim_specs:
        add_claim(*spec)

    priority_specs = [
        (item_ids[0], student, "公益加急", "校园卡涉及门禁和饭卡消费，希望管理员优先审核。\n联系方式：13900000001", 0, "公益免支付", "已通过", 24),
        (item_ids[10], student, "公益加急", "身份证属于重要证件，补办麻烦，希望提高曝光。\n联系方式：13900000001", 0, "公益免支付", "待审核", 24),
        (item_ids[8], cathy, "重点加急", "宿舍钥匙影响当天回宿舍，已完成模拟支付。\n联系方式：13900000004", 6, "已模拟支付", "已通过", 72),
        (item_ids[2], bob, "普通加急", "耳机价值较高，希望在首页短时间置顶。\n联系方式：13900000003", 3, "已模拟支付", "待审核", 24),
        (item_ids[16], alice, "普通加急", "U 盘里有课程设计资料，申请提高匹配优先级。\n联系方式：13900000002", 3, "已模拟支付", "已驳回", 24),
    ]
    for spec in priority_specs:
        add_priority(*spec)

    for index, item_id in enumerate(item_ids[:12]):
        db.log(users[index % len(users)], "导入演示物品", "item", item_id)
    db.log(admin, "初始化演示数据", "system", None)
    ensure_demo_notifications()
    print("演示数据已生成。")
    print("管理员：admin / admin123")
    print("普通用户：student / student123")


def ensure_demo_data():
    db.init_db()
    if users_table_empty():
        seed_demo_data()
        return True
    ensure_demo_notifications()
    return False


def main():
    reset_database()
    seed_demo_data()


if __name__ == "__main__":
    main()
