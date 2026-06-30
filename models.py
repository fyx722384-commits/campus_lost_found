from datetime import datetime
from werkzeug.security import check_password_hash


class User:
    def __init__(self, id=None, username="", password="", role="user", phone="", created_at=None):
        self.id = id
        self.username = username
        self.password = password
        self.role = role
        self.phone = phone
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls(row["id"], row["username"], row["password"], row["role"], row["phone"], row["created_at"])

    def is_admin(self):
        return self.role == "admin"

    def check_password(self, raw_password):
        try:
            return check_password_hash(self.password, raw_password)
        except ValueError:
            return self.password == raw_password


class Item:
    def __init__(
        self,
        id=None,
        user_id=None,
        title="",
        item_type="失物",
        category="其他",
        location="",
        event_time="",
        description="",
        contact="",
        image_path="",
        status="待认领",
        created_at=None,
        archived=0,
        owner_name="",
        priority_level="",
        priority_expire_at="",
        priority_status="",
    ):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.item_type = item_type
        self.category = category
        self.location = location
        self.event_time = event_time
        self.description = description
        self.contact = contact
        self.image_path = image_path
        self.status = status
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.archived = archived
        self.owner_name = owner_name
        self.priority_level = priority_level or ""
        self.priority_expire_at = priority_expire_at or ""
        self.priority_status = priority_status or ""

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        item_cls = LostItem if row["item_type"] == "失物" else FoundItem
        return item_cls(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            item_type=row["item_type"],
            category=row["category"],
            location=row["location"],
            event_time=row["event_time"],
            description=row["description"],
            contact=row["contact"],
            image_path=row["image_path"],
            status=row["status"],
            created_at=row["created_at"],
            archived=row["archived"],
            owner_name=row["owner_name"] if "owner_name" in row.keys() else "",
            priority_level=row["priority_level"] if "priority_level" in row.keys() else "",
            priority_expire_at=row["priority_expire_at"] if "priority_expire_at" in row.keys() else "",
            priority_status=row["priority_status"] if "priority_status" in row.keys() else "",
        )

    def is_lost(self):
        return self.item_type == "失物"

    def is_found(self):
        return self.item_type == "招领"

    def can_claim(self):
        return self.status == "待认领" and not self.archived

    def archive(self):
        self.archived = 1
        self.status = "已归档"

    def has_active_priority(self):
        return bool(self.priority_level and self.priority_status == "已通过")


class LostItem(Item):
    def __init__(self, **kwargs):
        kwargs["item_type"] = "失物"
        super().__init__(**kwargs)


class FoundItem(Item):
    def __init__(self, **kwargs):
        kwargs["item_type"] = "招领"
        super().__init__(**kwargs)


class ClaimRequest:
    def __init__(
        self,
        id=None,
        item_id=None,
        applicant_id=None,
        reason="",
        contact="",
        status="待审核",
        created_at=None,
        reviewed_at=None,
        item_title="",
        applicant_name="",
    ):
        self.id = id
        self.item_id = item_id
        self.applicant_id = applicant_id
        self.reason = reason
        self.contact = contact
        self.status = status
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.reviewed_at = reviewed_at
        self.item_title = item_title
        self.applicant_name = applicant_name

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls(
            id=row["id"],
            item_id=row["item_id"],
            applicant_id=row["applicant_id"],
            reason=row["reason"],
            contact=row["contact"],
            status=row["status"],
            created_at=row["created_at"],
            reviewed_at=row["reviewed_at"],
            item_title=row["item_title"] if "item_title" in row.keys() else "",
            applicant_name=row["applicant_name"] if "applicant_name" in row.keys() else "",
        )

    def approve(self):
        self.status = "已通过"
        self.reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def reject(self):
        self.status = "已驳回"
        self.reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def complete(self):
        self.status = "已完成"
        self.reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class PriorityRequest:
    def __init__(
        self,
        id=None,
        item_id=None,
        user_id=None,
        level="普通加急",
        reason="",
        fee_amount=0,
        pay_status="未支付",
        status="待审核",
        created_at=None,
        reviewed_at=None,
        expire_at=None,
        item_title="",
        item_category="",
        applicant_name="",
    ):
        self.id = id
        self.item_id = item_id
        self.user_id = user_id
        self.level = level
        self.reason = reason
        self.fee_amount = fee_amount
        self.pay_status = pay_status
        self.status = status
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.reviewed_at = reviewed_at
        self.expire_at = expire_at
        self.item_title = item_title
        self.item_category = item_category
        self.applicant_name = applicant_name

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls(
            id=row["id"],
            item_id=row["item_id"],
            user_id=row["user_id"],
            level=row["level"],
            reason=row["reason"],
            fee_amount=row["fee_amount"],
            pay_status=row["pay_status"],
            status=row["status"],
            created_at=row["created_at"],
            reviewed_at=row["reviewed_at"],
            expire_at=row["expire_at"],
            item_title=row["item_title"] if "item_title" in row.keys() else "",
            item_category=row["item_category"] if "item_category" in row.keys() else "",
            applicant_name=row["applicant_name"] if "applicant_name" in row.keys() else "",
        )

    def approve(self):
        self.status = "已通过"
        self.reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def reject(self):
        self.status = "已驳回"
        self.reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def finish(self):
        self.status = "已结束"
        self.reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def is_active(self):
        if self.status != "已通过" or not self.expire_at:
            return False
        try:
            return datetime.strptime(self.expire_at, "%Y-%m-%d %H:%M:%S") > datetime.now()
        except ValueError:
            return False


class Notification:
    def __init__(
        self,
        id=None,
        user_id=None,
        title="",
        content="",
        notification_type="系统提醒",
        is_read=0,
        related_type="",
        related_id=None,
        created_at=None,
    ):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.content = content
        self.notification_type = notification_type
        self.is_read = int(is_read or 0)
        self.related_type = related_type or ""
        self.related_id = related_id
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            content=row["content"],
            notification_type=row["notification_type"],
            is_read=row["is_read"],
            related_type=row["related_type"],
            related_id=row["related_id"],
            created_at=row["created_at"],
        )

    def mark_read(self):
        self.is_read = 1

    def is_unread(self):
        return self.is_read == 0
