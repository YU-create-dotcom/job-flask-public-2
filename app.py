from datetime import date, datetime, timedelta
from decimal import Decimal
import hmac
import os
import secrets
import unicodedata

from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash


load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-before-production")
if os.getenv("RENDER") and app.config["SECRET_KEY"] == "change-this-before-production":
    raise RuntimeError("SECRET_KEY must be configured on Render")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(os.getenv("RENDER"))
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

database_url = os.getenv("DATABASE_URL", "sqlite:///service.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
if database_url.startswith("postgresql+"):
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 300}
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "ログインしてください。"

DEFAULT_CATEGORIES = [
    "学チカ", "自己PR", "強み", "弱み", "就活の軸", "苦しかった経験",
    "最も努力した経験", "チームで取り組んだ経験", "小中高の部活・習い事",
    "大学のサークル", "なりたい大人", "キャリアプラン",
    "若手のキャリアプラン", "留年の理由", "物理は続けないのか", "その他",
]

INDUSTRY_OPTIONS = [
    "IT", "SIer", "Webサービス", "ソフトウェア", "通信", "半導体", "電機", "電子部品",
    "メーカー", "自動車", "機械", "精密機器", "化学", "素材", "鉄鋼", "非鉄金属",
    "食品", "飲料", "医薬品", "医療機器", "化粧品", "日用品", "アパレル",
    "商社", "総合商社", "専門商社", "小売", "EC", "物流", "運輸", "鉄道", "航空",
    "海運", "倉庫", "不動産", "デベロッパー", "建設", "建築総合管理", "住宅",
    "金融", "銀行", "信託銀行", "証券", "保険", "リース", "カード", "FinTech",
    "コンサル", "戦略コンサル", "総合コンサル", "ITコンサル", "シンクタンク",
    "監査法人", "税理士法人", "人材", "教育", "広告", "PR", "メディア", "出版",
    "エンタメ", "ゲーム", "旅行", "ホテル", "ブライダル", "外食", "エネルギー",
    "電力", "ガス", "石油", "官公庁", "自治体", "独立行政法人", "大学職員",
    "農業", "水産", "林業", "環境", "宇宙", "防衛", "その他",
]

RESULT_OPTIONS = ["内定", "内々定", "保留", "不合格"]

STATUS_OPTIONS = [
    "メール待ち", "参加確定", "参加決定", "申し込み済み", "書類提出未完了",
    "全職種エントリー", "適性検査", "選考中", "辞退", "終了",
]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login_id = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    ai_balance = db.Column(db.Numeric(10, 6), default=Decimal("5.00"), nullable=False)
    ai_limit = db.Column(db.Numeric(10, 2), default=Decimal("5.00"), nullable=False)
    ai_model = db.Column(db.String(50), default="gpt-5.4-mini", nullable=False)
    sheet_id = db.Column(db.String(200))
    sheet_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.now)

    @property
    def is_active(self):
        return self.is_active_account


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    event_date = db.Column(db.Date, nullable=False, index=True)
    event_time = db.Column(db.Time)
    company = db.Column(db.String(200))
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    summary = db.Column(db.Text)
    incomplete = db.Column(db.Boolean, default=False, nullable=False)
    active_selection = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class SelectionCompany(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    company_name = db.Column(db.String(200), nullable=False)
    industry = db.Column(db.String(100))
    submitted = db.Column(db.Boolean, default=False, nullable=False)
    application_route = db.Column(db.String(200))
    current_status = db.Column(db.String(100))
    intern_summary = db.Column(db.String(300))
    deadline_at = db.Column(db.DateTime)
    join_start_at = db.Column(db.DateTime)
    join_end_at = db.Column(db.DateTime)
    result = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class GDLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    log_type = db.Column(db.String(20), nullable=False)
    company = db.Column(db.String(100))
    theme = db.Column(db.String(200))
    role = db.Column(db.String(100))
    situation = db.Column(db.Text)
    my_action = db.Column(db.Text)
    result = db.Column(db.Text)
    reflection = db.Column(db.Text)
    ai_feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)


class SelfProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class SelfProfileCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    __table_args__ = (db.UniqueConstraint("user_id", "name"),)


class CompanyResearch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    company_name = db.Column(db.String(200), nullable=False)
    industry = db.Column(db.String(200))
    business = db.Column(db.Text)
    history = db.Column(db.Text)
    details = db.Column(db.Text)
    features = db.Column(db.Text)
    motivation = db.Column(db.Text)
    career_plan = db.Column(db.Text)
    appeal = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def ensure_categories(user_id):
    if SelfProfileCategory.query.filter_by(user_id=user_id).count():
        return
    for position, name in enumerate(DEFAULT_CATEGORIES, 1):
        db.session.add(SelfProfileCategory(user_id=user_id, name=name, position=position))
    db.session.commit()


def bootstrap_admin():
    login_id = os.getenv("ADMIN_LOGIN_ID")
    password = os.getenv("ADMIN_PASSWORD")
    if not login_id or not password or User.query.filter_by(login_id=login_id).first():
        return
    admin = User(
        login_id=login_id,
        password_hash=generate_password_hash(password),
        display_name=os.getenv("ADMIN_DISPLAY_NAME", "管理者"),
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()
    ensure_categories(admin.id)


@app.before_request
def validate_csrf():
    if current_user.is_authenticated and (
        not current_user.is_active_account or session.get("auth_version") != 1
    ):
        logout_user()
        session.clear()
        return redirect(url_for("login"))
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return
    submitted = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
    expected = session.get("csrf_token", "")
    if not expected or not hmac.compare_digest(submitted, expected):
        abort(400)


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.after_request
def secure_response(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_time(value):
    return datetime.strptime(value, "%H:%M").time() if value else None


def parse_datetime_local(value):
    value = str(value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def datetime_input_value(value):
    return value.strftime("%Y-%m-%dT%H:%M") if value else ""


def event_title(company_name, summary, category):
    parts = [company_name, summary, category]
    return "：".join(str(part).strip() for part in parts if str(part or "").strip())


def normalize_position(value):
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
    return int(normalized) if normalized.isdigit() else None


@app.context_processor
def global_template_values():
    return {"login_disabled": False}


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        user = User.query.filter_by(login_id=request.form.get("login_id", "").strip()).first()
        if user and user.is_active_account and check_password_hash(
            user.password_hash, request.form.get("password", "")
        ):
            session.clear()
            login_user(user)
            session["auth_version"] = 1
            ensure_categories(user.id)
            next_path = request.args.get("next", "")
            if not next_path.startswith("/") or next_path.startswith("//") or "\\" in next_path:
                next_path = url_for("index")
            return redirect(next_path)
        error = "IDまたはパスワードが正しくありません。"
    return render_template("login.html", error=error)


@app.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.get("/api/events")
@login_required
def api_events():
    companies = SelectionCompany.query.filter_by(user_id=current_user.id).order_by(
        SelectionCompany.deadline_at, SelectionCompany.join_start_at
    ).all()
    events = []
    for company in companies:
        if company.deadline_at:
            events.append({
                "id": f"deadline-{company.id}",
                "date": company.deadline_at.date().isoformat(),
                "time": company.deadline_at.strftime("%H:%M"),
                "company": company.company_name,
                "title": event_title(company.company_name, company.intern_summary, "ES締め切り"),
                "category": "ES締切",
                "summary": company.intern_summary or "",
                "incomplete": not company.submitted,
                "active_selection": True,
            })
        if company.join_start_at:
            end_at = company.join_end_at or company.join_start_at + timedelta(hours=1)
            if end_at <= company.join_start_at:
                end_at = company.join_start_at + timedelta(hours=1)
            events.append({
                "id": f"intern-{company.id}",
                "date": company.join_start_at.date().isoformat(),
                "time": company.join_start_at.strftime("%H:%M"),
                "end_date": end_at.date().isoformat(),
                "end_time": end_at.strftime("%H:%M"),
                "company": company.company_name,
                "title": event_title(company.company_name, company.intern_summary, "インターン"),
                "category": "インターン",
                "summary": company.intern_summary or "",
                "incomplete": False,
                "active_selection": True,
            })
    return jsonify(events)


@app.get("/api/selection-companies")
@login_required
def api_selection_companies():
    companies = SelectionCompany.query.filter_by(user_id=current_user.id).order_by(
        SelectionCompany.updated_at.desc(), SelectionCompany.created_at.desc()
    ).all()
    return jsonify([selection_company_payload(company) for company in companies])


@app.post("/events")
@login_required
def event_create():
    event = Event(
        user_id=current_user.id,
        event_date=parse_date(request.form["event_date"]),
        event_time=parse_time(request.form.get("event_time")),
        company=request.form.get("company", "").strip(),
        title=request.form.get("title", "").strip(),
        category=request.form.get("category", "その他").strip(),
        summary=request.form.get("summary", "").strip(),
        incomplete=request.form.get("incomplete") == "1",
        active_selection=request.form.get("active_selection") == "1",
    )
    if not event.title:
        return redirect(url_for("index"))
    db.session.add(event)
    db.session.commit()
    return redirect(url_for("index"))


@app.post("/events/delete/<int:event_id>")
@login_required
def event_delete(event_id):
    event = Event.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()
    db.session.delete(event)
    db.session.commit()
    return jsonify(ok=True)


def selection_company_from_form(company=None):
    company = company or SelectionCompany(user_id=current_user.id)
    company.company_name = request.form.get("company_name", "").strip()
    company.industry = request.form.get("industry", "").strip()
    company.submitted = request.form.get("submitted") == "1"
    company.application_route = request.form.get("application_route", "").strip()
    company.current_status = request.form.get("current_status", "").strip()
    company.intern_summary = request.form.get("intern_summary", "").strip()
    company.deadline_at = parse_datetime_local(request.form.get("deadline_at"))
    company.join_start_at = parse_datetime_local(request.form.get("join_start_at"))
    company.join_end_at = parse_datetime_local(request.form.get("join_end_at"))
    company.result = request.form.get("result", "").strip()
    return company


def selection_company_payload(company):
    return {
        "id": company.id,
        "company_name": company.company_name,
        "industry": company.industry or "",
        "submitted": company.submitted,
        "application_route": company.application_route or "",
        "current_status": company.current_status or "",
        "intern_summary": company.intern_summary or "",
        "deadline_at": datetime_input_value(company.deadline_at),
        "join_start_at": datetime_input_value(company.join_start_at),
        "join_end_at": datetime_input_value(company.join_end_at),
        "result": company.result or "",
        "created_at": company.created_at.strftime("%Y-%m-%d"),
    }


def maybe_create_embedded_gd_log():
    if request.form.get("gd_completed") != "1":
        return
    db.session.add(GDLog(
        user_id=current_user.id,
        log_type=request.form.get("gd_log_type", "GD"),
        company=request.form.get("company_name", "").strip(),
        theme=request.form.get("gd_theme", "").strip(),
        role=request.form.get("gd_role", "").strip(),
        situation=request.form.get("gd_situation", "").strip(),
        my_action=request.form.get("gd_my_action", "").strip(),
        result=request.form.get("gd_result", "").strip(),
        reflection=request.form.get("gd_reflection", "").strip(),
    ))


@app.get("/selection-companies")
@login_required
def selection_companies():
    companies = SelectionCompany.query.filter_by(user_id=current_user.id).order_by(
        SelectionCompany.updated_at.desc(), SelectionCompany.created_at.desc()
    ).all()
    return render_template(
        "selection_companies.html",
        companies=companies,
        companies_data=[selection_company_payload(company) for company in companies],
        industry_options=INDUSTRY_OPTIONS,
        result_options=RESULT_OPTIONS,
        status_options=STATUS_OPTIONS,
    )


@app.post("/selection-companies/new")
@login_required
def selection_company_new():
    company = selection_company_from_form()
    if company.company_name:
        db.session.add(company)
        maybe_create_embedded_gd_log()
        db.session.commit()
    return redirect(url_for("selection_companies"))


@app.post("/selection-companies/edit/<int:company_id>")
@login_required
def selection_company_edit(company_id):
    company = SelectionCompany.query.filter_by(id=company_id, user_id=current_user.id).first_or_404()
    selection_company_from_form(company)
    maybe_create_embedded_gd_log()
    db.session.commit()
    return redirect(url_for("selection_companies"))


@app.post("/selection-companies/delete/<int:company_id>")
@login_required
def selection_company_delete(company_id):
    company = SelectionCompany.query.filter_by(id=company_id, user_id=current_user.id).first_or_404()
    db.session.delete(company)
    db.session.commit()
    return redirect(url_for("selection_companies"))


@app.get("/api/mails")
@login_required
def api_mails():
    return jsonify([])


@app.get("/mail/details")
@login_required
def mail_details():
    return render_template("mail_details.html", mails=[], error=None)


@app.route("/gd/new", methods=["GET", "POST"])
@login_required
def gd_new():
    return redirect(url_for("selection_companies"))


@app.get("/gd/logs")
@login_required
def gd_logs():
    return redirect(url_for("selection_companies"))


@app.get("/gd/detail/<int:log_id>")
@login_required
def gd_detail(log_id):
    return redirect(url_for("selection_companies"))


@app.post("/gd/delete/<int:log_id>")
@login_required
def gd_delete(log_id):
    log = GDLog.query.filter_by(id=log_id, user_id=current_user.id).first_or_404()
    db.session.delete(log)
    db.session.commit()
    return redirect(url_for("gd_logs"))


@app.get("/gd/feedback/<int:log_id>")
@login_required
def gd_feedback(log_id):
    return redirect(url_for("selection_companies"))


@app.route("/self-profile", methods=["GET", "POST"])
@login_required
def self_profile():
    ensure_categories(current_user.id)
    if request.method == "POST":
        db.session.add(SelfProfile(
            user_id=current_user.id,
            category=request.form.get("category", ""),
            title=request.form.get("title", ""),
            content=request.form.get("content", ""),
        ))
        db.session.commit()
        return redirect(url_for("self_profile"))
    profiles = SelfProfile.query.filter_by(user_id=current_user.id).order_by(SelfProfile.created_at.desc()).all()
    records = SelfProfileCategory.query.filter_by(user_id=current_user.id).order_by(SelfProfileCategory.position).all()
    return render_template("self_profile.html", profiles=profiles, categories=[x.name for x in records], category_records=records)


@app.post("/self-profile/categories")
@login_required
def self_profile_categories():
    name = request.form.get("category_name", "").strip()
    raw_position = request.form.get("category_position", "").strip()
    delete_ids = {int(x) for x in request.form.getlist("delete_categories") if x.isdigit()}
    has_name, has_position = bool(name), bool(raw_position)
    if has_name != has_position or (not has_name and not delete_ids):
        return jsonify(ok=False, error="入力が適切ではありません"), 400
    records = SelfProfileCategory.query.filter_by(user_id=current_user.id).order_by(SelfProfileCategory.position).all()
    remaining = [x for x in records if x.id not in delete_ids]
    position = normalize_position(raw_position) if has_name else None
    if has_name and (
        position is None or position < 1 or position > len(remaining) + 1
        or len(name) > 50 or any(x.name == name for x in records)
    ):
        return jsonify(ok=False, error="入力が適切ではありません"), 400
    if not remaining and not has_name:
        return jsonify(ok=False, error="項目は1つ以上必要です"), 400
    for record in records:
        if record.id in delete_ids:
            db.session.delete(record)
    ordered = list(remaining)
    if has_name:
        new_record = SelfProfileCategory(user_id=current_user.id, name=name, position=position)
        db.session.add(new_record)
        ordered.insert(position - 1, new_record)
    for index, record in enumerate(ordered, 1):
        record.position = index
    db.session.commit()
    return jsonify(ok=True, redirect=url_for("self_profile"))


@app.post("/self-profile/delete/<int:profile_id>")
@login_required
def self_profile_delete(profile_id):
    profile = SelfProfile.query.filter_by(id=profile_id, user_id=current_user.id).first_or_404()
    db.session.delete(profile)
    db.session.commit()
    return redirect(url_for("self_profile"))


def company_from_form(company=None):
    company = company or CompanyResearch(user_id=current_user.id)
    for field in ("company_name", "industry", "business", "history", "details", "features", "motivation", "career_plan", "appeal"):
        setattr(company, field, request.form.get(field, "").strip())
    return company


def company_payload(companies):
    return [{
        "id": c.id, "company_name": c.company_name, "industry": c.industry or "",
        "business": c.business or "", "history": c.history or "", "details": c.details or "",
        "features": c.features or "", "motivation": c.motivation or "",
        "career_plan": c.career_plan or "", "appeal": c.appeal or "",
        "created_at": c.created_at.strftime("%Y-%m-%d"),
    } for c in companies]


@app.get("/company-research")
@login_required
def company_research():
    companies = CompanyResearch.query.filter_by(user_id=current_user.id).order_by(CompanyResearch.created_at.desc()).all()
    return render_template("company_research.html", companies=companies, companies_data=company_payload(companies))


@app.post("/company-research/new")
@login_required
def company_research_new():
    db.session.add(company_from_form())
    db.session.commit()
    return redirect(url_for("company_research"))


@app.post("/company-research/edit/<int:company_id>")
@login_required
def company_research_edit(company_id):
    company = CompanyResearch.query.filter_by(id=company_id, user_id=current_user.id).first_or_404()
    company_from_form(company)
    db.session.commit()
    return redirect(url_for("company_research"))


@app.post("/company-research/delete/<int:company_id>")
@login_required
def company_research_delete(company_id):
    company = CompanyResearch.query.filter_by(id=company_id, user_id=current_user.id).first_or_404()
    db.session.delete(company)
    db.session.commit()
    return redirect(url_for("company_research"))


with app.app_context():
    db.create_all()
    bootstrap_admin()


if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        use_reloader=False,
    )
