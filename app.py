import os
from functools import wraps
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from database import db
from models import User
from services import (
    CATEGORIES,
    CLAIM_STATUSES,
    ITEM_STATUSES,
    PRIORITY_LEVELS,
    PRIORITY_STATUSES,
    claim_service,
    item_service,
    match_service,
    priority_service,
    stats_service,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.secret_key = "campus-lost-found-course-design"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
db.init_db()
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file):
    if not file or file.filename == "" or not allowed_file(file.filename):
        return ""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    name, ext = os.path.splitext(secure_filename(file.filename))
    filename = f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return f"uploads/{filename}"


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.from_row(db.query_one("SELECT * FROM users WHERE id = ?", (user_id,)))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("请先登录后再访问该页面。", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash("请先登录管理员账号。", "warning")
            return redirect(url_for("login"))
        if not user.is_admin():
            flash("当前账号没有管理员权限。", "danger")
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped


@app.context_processor
def inject_globals():
    return {
        "current_user": current_user(),
        "categories": CATEGORIES,
        "item_statuses": ITEM_STATUSES,
        "claim_statuses": CLAIM_STATUSES,
        "priority_levels": PRIORITY_LEVELS,
        "priority_statuses": PRIORITY_STATUSES,
    }


@app.template_filter("status_class")
def status_class(value):
    return {
        "待认领": "status-blue",
        "认领中": "status-yellow",
        "已归还": "status-green",
        "已归档": "status-gray",
        "待审核": "status-blue",
        "已通过": "status-green",
        "已驳回": "status-red",
        "已完成": "status-green",
        "已结束": "status-gray",
        "已模拟支付": "status-green",
        "公益免支付": "status-green",
        "未支付": "status-yellow",
    }.get(value, "status-gray")


@app.template_filter("short_time")
def short_time(value):
    return (value or "").replace("T", " ")[:16]


@app.route("/")
@login_required
def index():
    keyword = request.args.get("keyword", "").strip()
    item_type = request.args.get("item_type", "")
    category = request.args.get("category", "")
    status = request.args.get("status", "")
    items = item_service.search_items(keyword, item_type, category, status, include_archived=False)
    stats = stats_service.dashboard_stats()
    return render_template("index.html", items=items, stats=stats, filters=request.args)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.from_row(db.query_one("SELECT * FROM users WHERE username = ?", (username,)))
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            db.log(user.id, "登录系统", "user", user.id)
            flash("登录成功，欢迎回来！", "success")
            return redirect(url_for("admin_dashboard" if user.is_admin() else "index"))
        flash("用户名或密码错误，请重新输入。", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        if not username or not password:
            flash("用户名和密码不能为空。", "warning")
            return render_template("register.html")
        exists = db.query_one("SELECT id FROM users WHERE username = ?", (username,))
        if exists:
            flash("该用户名已被注册。", "warning")
            return render_template("register.html")
        user_id = db.insert(
            "INSERT INTO users (username, password, role, phone, created_at) VALUES (?, ?, 'user', ?, ?)",
            (username, generate_password_hash(password), phone, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        db.log(user_id, "注册账号", "user", user_id)
        flash("注册成功，请登录。", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("你已退出登录。", "success")
    return redirect(url_for("login"))


@app.route("/publish", methods=["GET", "POST"])
@login_required
def publish():
    user = current_user()
    if request.method == "POST":
        data = {
            "item_type": request.form.get("item_type"),
            "title": request.form.get("title", "").strip(),
            "category": request.form.get("category"),
            "location": request.form.get("location", "").strip(),
            "event_time": request.form.get("event_time", ""),
            "description": request.form.get("description", "").strip(),
            "contact": request.form.get("contact", "").strip(),
            "image_path": save_upload(request.files.get("image")),
        }
        if not all([data["item_type"], data["title"], data["category"], data["location"], data["event_time"], data["description"], data["contact"]]):
            flash("请完整填写发布信息。", "warning")
            return render_template("publish.html", form=data)
        item_service.create_item(data, user.id)
        flash("发布成功，信息已展示在首页。", "success")
        return redirect(url_for("index"))
    return render_template("publish.html")


@app.route("/item/<int:item_id>", methods=["GET", "POST"])
@login_required
def item_detail(item_id):
    user = current_user()
    item = item_service.get_item(item_id)
    if not item:
        flash("物品信息不存在。", "warning")
        return redirect(url_for("index"))
    if request.method == "POST":
        reason = request.form.get("reason", "").strip()
        contact = request.form.get("contact", "").strip()
        if item.user_id == user.id:
            flash("不能认领自己发布的信息。", "warning")
            return redirect(url_for("item_detail", item_id=item.id))
        if not reason or not contact:
            flash("请填写认领说明和联系方式。", "warning")
            return redirect(url_for("item_detail", item_id=item.id))
        try:
            claim_service.submit_claim(item.id, user.id, reason, contact)
            flash("认领申请已提交，请等待管理员审核。", "success")
        except ValueError as exc:
            flash(str(exc), "warning")
        return redirect(url_for("my_claims"))
    priority_requests = priority_service.get_item_priority_requests(item.id) if item.user_id == user.id else []
    return render_template("item_detail.html", item=item, priority_requests=priority_requests)


@app.route("/match")
@login_required
def match():
    user = current_user()
    my_items = item_service.get_user_items(user.id)
    selected_id = request.args.get("item_id", type=int)
    selected_item = item_service.get_item(selected_id) if selected_id else None
    matches = match_service.recommend_matches(selected_id) if selected_id else []
    return render_template("match.html", my_items=my_items, selected_item=selected_item, matches=matches)


@app.route("/my-items")
@login_required
def my_items():
    user = current_user()
    return render_template("my_items.html", items=item_service.get_user_items(user.id))


@app.route("/priority/apply/<int:item_id>", methods=["GET", "POST"])
@login_required
def priority_apply(item_id):
    user = current_user()
    item = item_service.get_item(item_id)
    if not item:
        flash("物品信息不存在。", "warning")
        return redirect(url_for("my_items"))
    if item.user_id != user.id:
        flash("只能给自己发布的失物申请加急。", "danger")
        return redirect(url_for("item_detail", item_id=item.id))
    if not item.is_lost():
        flash("只有失物信息可以申请加急，招领信息不支持加急。", "warning")
        return redirect(url_for("item_detail", item_id=item.id))
    if request.method == "POST":
        level = request.form.get("level")
        reason = request.form.get("reason", "").strip()
        contact = request.form.get("contact", "").strip()
        if not level or not reason or not contact:
            flash("请完整填写加急等级、原因和联系方式。", "warning")
            return render_template("priority_apply.html", item=item)
        try:
            priority_service.create_priority_request(item.id, user.id, level, reason, contact)
            flash("加急申请已提交，模拟支付状态已记录，请等待管理员审核。", "success")
            return redirect(url_for("my_priority"))
        except ValueError as exc:
            flash(str(exc), "warning")
    return render_template("priority_apply.html", item=item)


@app.route("/my-priority")
@app.route("/my/priority")
@login_required
def my_priority():
    user = current_user()
    return render_template("my_priority.html", requests=priority_service.get_user_priority_requests(user.id))


@app.route("/my-claims")
@login_required
def my_claims():
    user = current_user()
    return render_template("my_claims.html", claims=claim_service.list_claims(applicant_id=user.id))


@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template(
        "admin_dashboard.html",
        stats=stats_service.dashboard_stats(),
        category_stats=stats_service.category_stats(),
        trend_stats=stats_service.trend_stats(),
        claims=claim_service.list_claims(),
        priority_requests=priority_service.get_admin_priority_requests("待审核"),
    )


@app.route("/admin/items", methods=["GET", "POST"])
@admin_required
def admin_items():
    user = current_user()
    if request.method == "POST":
        item_id = request.form.get("item_id", type=int)
        action = request.form.get("action")
        status = request.form.get("status")
        if action == "archive":
            item_service.archive_item(item_id, user.id)
            flash("物品信息已归档。", "success")
        elif status in ITEM_STATUSES:
            item_service.update_status(item_id, status, user.id)
            flash("物品状态已更新。", "success")
        return redirect(url_for("admin_items"))
    items = item_service.search_items(
        request.args.get("keyword", "").strip(),
        request.args.get("item_type", ""),
        request.args.get("category", ""),
        request.args.get("status", ""),
        include_archived=True,
    )
    return render_template("admin_items.html", items=items, filters=request.args)


@app.route("/admin/claims", methods=["GET", "POST"])
@admin_required
def admin_claims():
    user = current_user()
    if request.method == "POST":
        claim_id = request.form.get("claim_id", type=int)
        status = request.form.get("status")
        if status in CLAIM_STATUSES:
            claim_service.review_claim(claim_id, status, user.id)
            flash("认领申请审核状态已更新。", "success")
        return redirect(url_for("admin_claims"))
    return render_template("admin_claims.html", claims=claim_service.list_claims())


@app.route("/admin/priority", methods=["GET", "POST"])
@admin_required
def admin_priority():
    user = current_user()
    if request.method == "POST":
        request_id = request.form.get("request_id", type=int)
        action = request.form.get("action")
        try:
            if action == "approve":
                priority_service.approve_priority_request(request_id, user.id)
                flash("加急申请已通过，相关失物将在首页优先展示。", "success")
            elif action == "reject":
                priority_service.reject_priority_request(request_id, user.id)
                flash("加急申请已驳回。", "success")
            elif action == "finish":
                priority_service.finish_priority_request(request_id, user.id)
                flash("加急服务已手动结束。", "success")
        except ValueError as exc:
            flash(str(exc), "warning")
        return redirect(url_for("admin_priority", status=request.args.get("status", "")))
    status = request.args.get("status", "")
    requests = priority_service.get_admin_priority_requests(status)
    return render_template("admin_priority.html", requests=requests, current_status=status)


@app.route("/admin/users")
@admin_required
def admin_users():
    return render_template("admin_users.html", users=stats_service.users_with_counts())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
