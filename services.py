import re
from datetime import datetime, timedelta

from database import db
from models import ClaimRequest, Item, Notification, PriorityRequest, SupportMessage


CATEGORIES = ["证件", "电子产品", "书籍", "生活用品", "钥匙", "校园卡", "其他"]
ITEM_STATUSES = ["待认领", "认领中", "已归还", "已归档"]
CLAIM_STATUSES = ["待审核", "已通过", "已驳回", "已完成"]
PRIORITY_LEVELS = {
    "普通加急": {"fee": 3, "hours": 24},
    "重点加急": {"fee": 6, "hours": 72},
    "公益加急": {"fee": 0, "hours": 24},
}
PRIORITY_STATUSES = ["待审核", "已通过", "已驳回", "已结束"]
SUPPORT_STATUSES = ["待回复", "已回复"]
PUBLIC_PRIORITY_CATEGORIES = ["校园卡", "证件", "钥匙"]


def active_priority_join():
    return """
        LEFT JOIN (
            SELECT item_id, level AS priority_level, expire_at AS priority_expire_at, status AS priority_status
            FROM priority_requests
            WHERE status = '已通过'
              AND expire_at IS NOT NULL
              AND datetime(expire_at) > datetime('now', 'localtime')
        ) active_priority ON active_priority.item_id = items.id
    """


class ItemService:
    def create_item(self, data, user_id):
        item_id = db.insert(
            """
            INSERT INTO items
            (user_id, title, item_type, category, location, event_time, description, contact, image_path, status, created_at, archived)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '待认领', ?, 0)
            """,
            (
                user_id,
                data["title"],
                data["item_type"],
                data["category"],
                data["location"],
                data["event_time"],
                data["description"],
                data["contact"],
                data.get("image_path", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        db.log(user_id, "发布物品信息", "item", item_id)
        return item_id

    def search_items(
        self,
        keyword="",
        item_type="",
        category="",
        status="",
        include_archived=False,
        start_date="",
        end_date="",
        date_mode="",
    ):
        sql = """
            SELECT items.*, users.username AS owner_name,
                   active_priority.priority_level,
                   active_priority.priority_expire_at,
                   active_priority.priority_status
            FROM items
            JOIN users ON users.id = items.user_id
        """ + active_priority_join() + """
            WHERE 1=1
        """
        params = []
        if not include_archived:
            sql += " AND items.archived = 0"
        if keyword:
            sql += " AND (items.title LIKE ? OR items.description LIKE ? OR items.location LIKE ?)"
            like = f"%{keyword}%"
            params.extend([like, like, like])
        if item_type:
            sql += " AND items.item_type = ?"
            params.append(item_type)
        if category:
            sql += " AND items.category = ?"
            params.append(category)
        if status:
            sql += " AND items.status = ?"
            params.append(status)
        if date_mode == "today":
            sql += " AND date(items.created_at) = date('now', 'localtime')"
        else:
            if self._valid_date(start_date):
                sql += " AND date(items.event_time) >= date(?)"
                params.append(start_date)
            if self._valid_date(end_date):
                sql += " AND date(items.event_time) <= date(?)"
                params.append(end_date)
        sql += """
            ORDER BY
                CASE WHEN active_priority.priority_level IS NOT NULL THEN 1 ELSE 0 END DESC,
                datetime(active_priority.priority_expire_at) DESC,
                items.created_at DESC
        """
        return [Item.from_row(row) for row in db.query(sql, params)]

    def _valid_date(self, value):
        return bool(value and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))

    def get_item(self, item_id):
        row = db.query_one(
            """
            SELECT items.*, users.username AS owner_name,
                   active_priority.priority_level,
                   active_priority.priority_expire_at,
                   active_priority.priority_status
            FROM items
            JOIN users ON users.id = items.user_id
            """ + active_priority_join() + """
            WHERE items.id = ?
            """,
            (item_id,),
        )
        return Item.from_row(row)

    def get_user_items(self, user_id):
        rows = db.query(
            """
            SELECT items.*, users.username AS owner_name,
                   active_priority.priority_level,
                   active_priority.priority_expire_at,
                   active_priority.priority_status
            FROM items
            JOIN users ON users.id = items.user_id
            """ + active_priority_join() + """
            WHERE items.user_id = ?
            ORDER BY
                CASE WHEN active_priority.priority_level IS NOT NULL THEN 1 ELSE 0 END DESC,
                items.created_at DESC
            """,
            (user_id,),
        )
        return [Item.from_row(row) for row in rows]

    def update_status(self, item_id, status, user_id=None):
        archived = 1 if status == "已归档" else 0
        db.execute("UPDATE items SET status = ?, archived = ? WHERE id = ?", (status, archived, item_id))
        db.log(user_id, f"修改物品状态为{status}", "item", item_id)

    def archive_item(self, item_id, user_id=None):
        db.execute("UPDATE items SET status = '已归档', archived = 1 WHERE id = ?", (item_id,))
        db.log(user_id, "归档物品信息", "item", item_id)


class MatchService:
    def __init__(self):
        self.item_service = ItemService()
        self.priority_service = None

    def recommend_matches(self, item_id):
        source = self.item_service.get_item(item_id)
        if not source:
            return []
        target_type = "招领" if source.item_type == "失物" else "失物"
        candidates = self.item_service.search_items(item_type=target_type, include_archived=False)
        matches = []
        for candidate in candidates:
            if candidate.id == source.id:
                continue
            score, reasons = self.calculate_score(source, candidate)
            if score >= 25:
                priority_weight = priority_service.calculate_priority_weight(source, candidate)
                if priority_weight:
                    reasons = reasons + ["加急寻物优先处理"]
                matches.append(
                    {
                        "item": candidate,
                        "score": score,
                        "reasons": reasons,
                        "priority_weight": priority_weight,
                        "is_priority": candidate.has_active_priority() or source.has_active_priority(),
                        "priority_level": candidate.priority_level or source.priority_level,
                    }
                )
        return sorted(matches, key=lambda x: (x["priority_weight"], x["score"]), reverse=True)

    def calculate_score(self, a, b):
        score = 0
        reasons = []
        if a.item_type != b.item_type:
            score += 15
            reasons.append("类型互补")
        if a.category == b.category:
            score += 25
            reasons.append("分类一致")
        name_overlap = self._text_similarity(a.title, b.title)
        if name_overlap:
            score += min(20, 8 + name_overlap * 4)
            reasons.append("名称关键词相似")
        location_overlap = self._text_similarity(a.location, b.location)
        if location_overlap:
            score += min(18, 8 + location_overlap * 3)
            reasons.append("地点相同或相近")
        day_gap = self._day_gap(a.event_time, b.event_time)
        if day_gap is not None:
            if day_gap <= 1:
                score += 15
                reasons.append("时间非常接近")
            elif day_gap <= 3:
                score += 10
                reasons.append("时间较接近")
            elif day_gap <= 7:
                score += 5
                reasons.append("时间在一周内")
        desc_overlap = self._text_similarity(a.description, b.description)
        if desc_overlap:
            score += min(12, desc_overlap * 3)
            reasons.append("描述关键词有重合")
        if not reasons:
            reasons.append("基础条件符合")
        return min(99, int(score)), reasons

    def _tokens(self, text):
        text = (text or "").lower()
        words = set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", text))
        for char in re.findall(r"[\u4e00-\u9fff]", text):
            if char not in "的一是了在和有与及或":
                words.add(char)
        return words

    def _text_similarity(self, left, right):
        a = self._tokens(left)
        b = self._tokens(right)
        return len(a & b)

    def _day_gap(self, left, right):
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                d1 = datetime.strptime(left[: len(fmt)], fmt)
                d2 = datetime.strptime(right[: len(fmt)], fmt)
                return abs((d1.date() - d2.date()).days)
            except (ValueError, TypeError):
                continue
        return None


class NotificationService:
    def create_notification(
        self,
        user_id,
        title,
        content,
        notification_type="系统提醒",
        related_type="",
        related_id=None,
    ):
        if not user_id:
            return None
        return db.insert(
            """
            INSERT INTO notifications
            (user_id, title, content, notification_type, is_read, related_type, related_id, created_at)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                user_id,
                title,
                content,
                notification_type,
                related_type,
                related_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    def get_user_notifications(self, user_id):
        rows = db.query(
            """
            SELECT *
            FROM notifications
            WHERE user_id = ?
            ORDER BY is_read ASC, datetime(created_at) DESC, id DESC
            """,
            (user_id,),
        )
        return [Notification.from_row(row) for row in rows]

    def count_unread(self, user_id):
        row = db.query_one(
            "SELECT COUNT(*) AS count FROM notifications WHERE user_id = ? AND is_read = 0",
            (user_id,),
        )
        return row["count"] if row else 0

    def mark_as_read(self, notification_id, user_id):
        exists = db.query_one(
            "SELECT id FROM notifications WHERE id = ? AND user_id = ?",
            (notification_id, user_id),
        )
        if not exists:
            return False
        db.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notification_id, user_id))
        return True

    def mark_all_as_read(self, user_id):
        db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0", (user_id,))


class SupportService:
    def create_message(self, user_id, username, content):
        content = (content or "").strip()
        if not content:
            raise ValueError("请输入咨询内容。")
        if len(content) < 10:
            raise ValueError("请补充更详细的问题描述。")
        if len(content) > 300:
            raise ValueError("咨询内容不能超过 300 字。")
        message_id = db.insert(
            """
            INSERT INTO support_messages
            (user_id, username, content, reply, status, created_at, replied_at, admin_id)
            VALUES (?, ?, ?, '', '待回复', ?, NULL, NULL)
            """,
            (user_id, username, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        db.log(user_id, "提交咨询留言", "support_message", message_id)
        return message_id

    def get_user_messages(self, user_id):
        rows = db.query(
            """
            SELECT *
            FROM support_messages
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            """,
            (user_id,),
        )
        return [SupportMessage.from_row(row) for row in rows]

    def get_all_messages(self, status=None):
        sql = "SELECT * FROM support_messages WHERE 1=1"
        params = []
        if status in SUPPORT_STATUSES:
            sql += " AND status = ?"
            params.append(status)
        sql += """
            ORDER BY
                CASE status WHEN '待回复' THEN 1 ELSE 2 END,
                datetime(created_at) DESC,
                id DESC
        """
        return [SupportMessage.from_row(row) for row in db.query(sql, params)]

    def reply_message(self, message_id, admin_id, reply):
        reply = (reply or "").strip()
        if not reply:
            raise ValueError("请填写回复内容。")
        message = self.get_message(message_id)
        if not message:
            raise ValueError("咨询留言不存在。")
        replied_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            """
            UPDATE support_messages
            SET reply = ?, status = '已回复', replied_at = ?, admin_id = ?
            WHERE id = ?
            """,
            (reply, replied_at, admin_id, message_id),
        )
        notification_service.create_notification(
            message.user_id,
            "管理员已回复你的咨询",
            "你提交的咨询已收到管理员回复，请到“我的咨询”页面查看。",
            "咨询回复",
            "support",
            message_id,
        )
        db.log(admin_id, "回复咨询留言", "support_message", message_id)

    def get_message(self, message_id):
        row = db.query_one("SELECT * FROM support_messages WHERE id = ?", (message_id,))
        return SupportMessage.from_row(row)

    def count_pending(self):
        row = db.query_one("SELECT COUNT(*) AS count FROM support_messages WHERE status = '待回复'")
        return row["count"] if row else 0


class ClaimService:
    def submit_claim(self, item_id, applicant_id, reason, contact):
        exists = db.query_one(
            "SELECT id FROM claims WHERE item_id = ? AND applicant_id = ? AND status IN ('待审核', '已通过')",
            (item_id, applicant_id),
        )
        if exists:
            raise ValueError("你已经提交过该物品的认领申请，请等待管理员审核。")
        claim_id = db.insert(
            """
            INSERT INTO claims (item_id, applicant_id, reason, contact, status, created_at, reviewed_at)
            VALUES (?, ?, ?, ?, '待审核', ?, NULL)
            """,
            (item_id, applicant_id, reason, contact, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        db.execute("UPDATE items SET status = '认领中' WHERE id = ? AND status = '待认领'", (item_id,))
        db.log(applicant_id, "提交认领申请", "claim", claim_id)
        return claim_id

    def list_claims(self, applicant_id=None, status=""):
        sql = """
            SELECT claims.*, items.title AS item_title, users.username AS applicant_name
            FROM claims
            JOIN items ON items.id = claims.item_id
            JOIN users ON users.id = claims.applicant_id
            WHERE 1=1
        """
        params = []
        if applicant_id:
            sql += " AND claims.applicant_id = ?"
            params.append(applicant_id)
        if status in CLAIM_STATUSES:
            sql += " AND claims.status = ?"
            params.append(status)
        sql += " ORDER BY claims.created_at DESC"
        return [ClaimRequest.from_row(row) for row in db.query(sql, params)]

    def review_claim(self, claim_id, status, admin_id):
        claim_detail = db.query_one(
            """
            SELECT claims.*, items.title AS item_title
            FROM claims
            JOIN items ON items.id = claims.item_id
            WHERE claims.id = ?
            """,
            (claim_id,),
        )
        if not claim_detail:
            raise ValueError("认领申请不存在。")
        old_status = claim_detail["status"]
        reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute("UPDATE claims SET status = ?, reviewed_at = ? WHERE id = ?", (status, reviewed_at, claim_id))
        if status == "已通过":
            db.execute("UPDATE items SET status = '认领中' WHERE id = ?", (claim_detail["item_id"],))
        elif status == "已驳回":
            waiting = db.query_one(
                "SELECT COUNT(*) AS c FROM claims WHERE item_id = ? AND status IN ('待审核', '已通过')",
                (claim_detail["item_id"],),
            )
            if waiting["c"] == 0:
                db.execute("UPDATE items SET status = '待认领' WHERE id = ?", (claim_detail["item_id"],))
        elif status == "已完成":
            db.execute("UPDATE items SET status = '已归还' WHERE id = ?", (claim_detail["item_id"],))
        if old_status != status:
            self._notify_claim_review(claim_detail, status, claim_id)
        db.log(admin_id, f"审核认领申请为{status}", "claim", claim_id)

    def _notify_claim_review(self, claim_detail, status, claim_id):
        item_title = claim_detail["item_title"]
        messages = {
            "已通过": (
                "认领申请已通过",
                f"你提交的【{item_title}】认领申请已通过，请及时联系管理员或发布者完成领取。",
            ),
            "已驳回": (
                "认领申请已驳回",
                f"你提交的【{item_title}】认领申请未通过，请补充有效证明后再尝试。",
            ),
            "已完成": (
                "物品已完成归还",
                f"你认领的【{item_title}】已完成归还流程，感谢使用湖北汽车工业学院校园失物招领系统。",
            ),
        }
        if status in messages:
            title, content = messages[status]
            notification_service.create_notification(
                claim_detail["applicant_id"],
                title,
                content,
                "认领审核",
                "claim",
                claim_id,
            )


class PriorityService:
    def create_priority_request(self, item_id, user_id, level, reason, contact):
        item = ItemService().get_item(item_id)
        if not item:
            raise ValueError("物品信息不存在。")
        if item.user_id != user_id:
            raise ValueError("只能给自己发布的失物申请加急。")
        if not item.is_lost():
            raise ValueError("只有失物信息可以申请加急，招领信息不支持加急。")
        if level not in PRIORITY_LEVELS:
            raise ValueError("请选择正确的加急等级。")
        if level == "公益加急" and item.category not in PUBLIC_PRIORITY_CATEGORIES:
            raise ValueError("公益加急仅限校园卡、证件、钥匙等重要物品。")
        existing = db.query_one(
            """
            SELECT id FROM priority_requests
            WHERE item_id = ?
              AND status IN ('待审核', '已通过')
              AND (expire_at IS NULL OR datetime(expire_at) > datetime('now', 'localtime'))
            """,
            (item_id,),
        )
        if existing:
            raise ValueError("该失物已有待审核或进行中的加急申请。")

        config = PRIORITY_LEVELS[level]
        pay_status = "公益免支付" if level == "公益加急" else "已模拟支付"
        full_reason = f"{reason}\n联系方式：{contact}".strip()
        priority_id = db.insert(
            """
            INSERT INTO priority_requests
            (item_id, user_id, level, reason, fee_amount, pay_status, status, created_at, reviewed_at, expire_at)
            VALUES (?, ?, ?, ?, ?, ?, '待审核', ?, NULL, NULL)
            """,
            (
                item_id,
                user_id,
                level,
                full_reason,
                config["fee"],
                pay_status,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        db.log(user_id, f"提交{level}申请", "priority_request", priority_id)
        return priority_id

    def approve_priority_request(self, request_id, admin_id):
        request_obj = self.get_priority_request(request_id)
        if not request_obj:
            raise ValueError("加急申请不存在。")
        hours = PRIORITY_LEVELS.get(request_obj.level, PRIORITY_LEVELS["普通加急"])["hours"]
        reviewed_at = datetime.now()
        expire_at = reviewed_at + timedelta(hours=hours)
        db.execute(
            "UPDATE priority_requests SET status = '已通过', reviewed_at = ?, expire_at = ? WHERE id = ?",
            (
                reviewed_at.strftime("%Y-%m-%d %H:%M:%S"),
                expire_at.strftime("%Y-%m-%d %H:%M:%S"),
                request_id,
            ),
        )
        self._notify_priority_review(request_obj, "已通过", request_id)
        db.log(admin_id, "通过加急寻物申请", "priority_request", request_id)

    def reject_priority_request(self, request_id, admin_id):
        request_obj = self.get_priority_request(request_id)
        if not request_obj:
            raise ValueError("加急申请不存在。")
        db.execute(
            "UPDATE priority_requests SET status = '已驳回', reviewed_at = ? WHERE id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), request_id),
        )
        self._notify_priority_review(request_obj, "已驳回", request_id)
        db.log(admin_id, "驳回加急寻物申请", "priority_request", request_id)

    def finish_priority_request(self, request_id, admin_id):
        request_obj = self.get_priority_request(request_id)
        if not request_obj:
            raise ValueError("加急申请不存在。")
        db.execute(
            "UPDATE priority_requests SET status = '已结束', reviewed_at = ? WHERE id = ?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), request_id),
        )
        self._notify_priority_review(request_obj, "已结束", request_id)
        db.log(admin_id, "结束加急寻物服务", "priority_request", request_id)

    def get_priority_request(self, request_id):
        rows = self._query_priority_requests("priority_requests.id = ?", (request_id,))
        return rows[0] if rows else None

    def get_user_priority_requests(self, user_id):
        return self._query_priority_requests("priority_requests.user_id = ?", (user_id,))

    def get_admin_priority_requests(self, status=""):
        if status:
            return self._query_priority_requests("priority_requests.status = ?", (status,))
        return self._query_priority_requests("1=1", ())

    def get_item_priority_requests(self, item_id):
        return self._query_priority_requests("priority_requests.item_id = ?", (item_id,))

    def get_active_priority_items(self):
        rows = db.query(
            """
            SELECT items.*, users.username AS owner_name,
                   priority_requests.level AS priority_level,
                   priority_requests.expire_at AS priority_expire_at,
                   priority_requests.status AS priority_status
            FROM priority_requests
            JOIN items ON items.id = priority_requests.item_id
            JOIN users ON users.id = items.user_id
            WHERE priority_requests.status = '已通过'
              AND datetime(priority_requests.expire_at) > datetime('now', 'localtime')
              AND items.archived = 0
            ORDER BY datetime(priority_requests.expire_at) DESC
            """
        )
        return [Item.from_row(row) for row in rows]

    def calculate_priority_weight(self, source, candidate=None):
        weight = 0
        for item in (source, candidate):
            if item and item.has_active_priority():
                weight = max(weight, {"重点加急": 30, "普通加急": 20, "公益加急": 18}.get(item.priority_level, 10))
        return weight

    def _query_priority_requests(self, where_sql, params):
        rows = db.query(
            f"""
            SELECT priority_requests.*,
                   items.title AS item_title,
                   items.category AS item_category,
                   users.username AS applicant_name
            FROM priority_requests
            JOIN items ON items.id = priority_requests.item_id
            JOIN users ON users.id = priority_requests.user_id
            WHERE {where_sql}
            ORDER BY
                CASE priority_requests.status
                    WHEN '待审核' THEN 1
                    WHEN '已通过' THEN 2
                    WHEN '已驳回' THEN 3
                    ELSE 4
                END,
                priority_requests.created_at DESC
            """,
            params,
        )
        return [PriorityRequest.from_row(row) for row in rows]

    def _notify_priority_review(self, request_obj, status, request_id):
        item_title = request_obj.item_title
        messages = {
            "已通过": (
                "加急寻物申请已通过",
                f"你的【{item_title}】加急寻物申请已通过，系统将优先展示并提高匹配排序。",
            ),
            "已驳回": (
                "加急寻物申请已驳回",
                f"你的【{item_title}】加急寻物申请未通过，请检查申请原因是否充分。",
            ),
            "已结束": (
                "加急寻物服务已结束",
                f"你的【{item_title}】加急寻物服务已结束，物品信息仍可继续正常展示。",
            ),
        }
        if status in messages:
            title, content = messages[status]
            notification_service.create_notification(
                request_obj.user_id,
                title,
                content,
                "加急审核",
                "priority",
                request_id,
            )


class StatsService:
    def today_new_items(self):
        # 口径：统计 items 表中本地日期为今天的全部发布信息，包含已归档数据。
        try:
            row = db.query_one("SELECT COUNT(*) AS count FROM items WHERE date(created_at) = date('now', 'localtime')")
            return row["count"] if row else 0
        except Exception:
            return 0

    def dashboard_stats(self):
        def one(sql, params=()):
            row = db.query_one(sql, params)
            return row[0] if row else 0

        return {
            "total_items": one("SELECT COUNT(*) FROM items"),
            "lost_count": one("SELECT COUNT(*) FROM items WHERE item_type = '失物'"),
            "found_count": one("SELECT COUNT(*) FROM items WHERE item_type = '招领'"),
            "today_new_items": self.today_new_items(),
            "pending_claims": one("SELECT COUNT(*) FROM claims WHERE status = '待审核'"),
            "returned_count": one("SELECT COUNT(*) FROM items WHERE status = '已归还'"),
            "archived_count": one("SELECT COUNT(*) FROM items WHERE archived = 1"),
            "today_priority": one("SELECT COUNT(*) FROM priority_requests WHERE date(created_at) = date('now', 'localtime')"),
            "pending_priority": one("SELECT COUNT(*) FROM priority_requests WHERE status = '待审核'"),
            "active_priority": one(
                """
                SELECT COUNT(*) FROM priority_requests
                WHERE status = '已通过'
                  AND expire_at IS NOT NULL
                  AND datetime(expire_at) > datetime('now', 'localtime')
                """
            ),
            "finished_priority": one("SELECT COUNT(*) FROM priority_requests WHERE status = '已结束'"),
            "pending_support": one("SELECT COUNT(*) FROM support_messages WHERE status = '待回复'"),
        }

    def category_stats(self):
        rows = db.query("SELECT category, COUNT(*) AS count FROM items GROUP BY category ORDER BY count DESC")
        return [{"category": row["category"], "count": row["count"]} for row in rows]

    def trend_stats(self):
        rows = db.query(
            """
            SELECT date(created_at) AS day, COUNT(*) AS count
            FROM items
            WHERE date(created_at) >= date('now', '-6 day')
            GROUP BY date(created_at)
            ORDER BY day
            """
        )
        data = {row["day"]: row["count"] for row in rows}
        result = []
        for i in range(6, -1, -1):
            row = db.query_one("SELECT date('now', ?) AS day", (f"-{i} day",))
            day = row["day"]
            result.append({"day": day[5:], "count": data.get(day, 0)})
        return result

    def users_with_counts(self):
        rows = db.query(
            """
            SELECT users.id, users.username, users.role, users.phone, users.created_at,
                   COUNT(items.id) AS item_count
            FROM users
            LEFT JOIN items ON items.user_id = users.id
            GROUP BY users.id
            ORDER BY users.created_at DESC
            """
        )
        return rows


item_service = ItemService()
match_service = MatchService()
claim_service = ClaimService()
stats_service = StatsService()
priority_service = PriorityService()
notification_service = NotificationService()
support_service = SupportService()
