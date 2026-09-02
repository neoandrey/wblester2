"""MongoEngine documents mirroring the drift tables.

Every document carries the BasicColumns equivalent:
``created_datetime``, ``last_modified_date``, ``current_version``.
Field names are snake_case; the sync contract converts to/from the
camelCase used by the Flutter drift layer.
"""

from datetime import datetime, timezone

from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    Document,
    EmailField,
    IntField,
    ListField,
    StringField,
)
from werkzeug.security import check_password_hash, generate_password_hash


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BaseDocument(Document):
    """Common columns shared by every synced collection."""

    meta = {
        "abstract": True,
        "allow_inheritance": True,
    }

    created_datetime = DateTimeField(default=utcnow)
    last_modified_date = DateTimeField(default=utcnow)
    current_version = IntField(default=0)

    def bump_version(self):
        self.current_version = (self.current_version or 0) + 1
        self.last_modified_date = utcnow()

    meta_options = None


class AuditTrail(BaseDocument):
    description = StringField()
    old_data = DictField(default=dict)
    new_data = DictField(default=dict)
    change_time = DateTimeField(default=utcnow)
    change_type = StringField()
    affected_table = StringField()
    username = StringField()
    user_id = StringField()

    meta = {
        "collection": "audit_trail",
        "indexes": ["change_time", "change_type", "affected_table", "username"],
    }


class FrontendLog(BaseDocument):
    """Browser-side log events reported by the Flutter admin panel.

    Kept out of TABLE_REGISTRY so it is never synced to the drift database;
    it only backs the SIEM-style consolidated /cpanel/jwt/logs endpoint.
    """

    level = StringField(default="INFO")
    message = StringField()
    page = StringField()
    source = StringField(default="frontend")
    username = StringField()
    context = DictField(default=dict)
    created_at = DateTimeField(default=utcnow)

    meta = {
        "collection": "frontend_logs",
        "indexes": ["level", "created_at", "page"],
    }


class Users(BaseDocument):
    ADMIN = 0
    USER = 1
    GROUP_ADMIN = 2
    ACTIVE = 1
    DISABLED = 0

    user_id = IntField(unique=True, required=True)
    status = IntField(default=0)
    username = StringField(unique=True, required=True)
    password_hash = StringField()
    locked = BooleanField(default=False)
    role_id = IntField(default=0)
    connection_status = BooleanField(default=False)
    active = BooleanField(default=False)
    must_change_password = BooleanField(default=False)
    login_count = IntField(default=0)
    login_attempts = IntField(default=0)
    token = StringField()
    token_expiration = DateTimeField()
    email = EmailField(unique=True, required=True)
    password_history = ListField(StringField(), default=list)

    meta = {
        "collection": "users",
        "indexes": ["user_id", "username", "email", "locked", "active"],
    }

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class Roles(BaseDocument):
    role_id = IntField(unique=True, required=True)
    role_name = StringField(unique=True, required=True)
    description = StringField()

    meta = {"collection": "roles", "indexes": ["role_id", "role_name"]}


class Permissions(BaseDocument):
    permission_id = IntField(unique=True, required=True)
    permission_name = StringField(unique=True, required=True)
    description = StringField()

    meta = {
        "collection": "permissions",
        "indexes": ["permission_id", "permission_name"],
    }


class RolePermissions(BaseDocument):
    """Join table mapping roles to permissions with an access level.

    Access levels: 0 = read-only (guest), 1 = read + modify (superuser,
    admin), 2 = create + delete (admin).
    """

    role_id = IntField(required=True)
    permission_id = IntField(required=True)
    access_level = IntField(default=0)

    meta = {
        "collection": "role_permissions",
        "indexes": ["role_id", "permission_id"],
    }


class Images(BaseDocument):
    image_id = IntField(unique=True, required=True)
    image_name = StringField(unique=True, required=True)
    file_name = StringField(required=True)
    file_path = StringField(required=True)
    image_type = StringField()
    file_size = StringField()
    image_dimensions = StringField()
    image_width = IntField()
    image_height = IntField()
    variants = DictField(default=dict)
    image_format = StringField()
    file_type = StringField()
    image_url = StringField(unique=True, required=True)
    webkit_relative_path = StringField()
    google_file_id = StringField()
    google_url = StringField()
    image_last_modified = StringField()
    transparent_background = BooleanField(default=False)
    creator_id = IntField()

    meta = {"collection": "images", "indexes": ["image_id", "image_url"]}


class Files(BaseDocument):
    file_id = IntField(unique=True, required=True)
    file_name = StringField(required=True)
    file_path = StringField(unique=True, required=True)
    file_size = StringField()
    file_type = StringField()
    actual_file_name = StringField(unique=True, required=True)
    file_format = StringField()
    file_url = StringField(unique=True, required=True)
    google_id = StringField()
    google_url = StringField()
    file_last_modified = StringField()
    creator_id = IntField()

    meta = {"collection": "files", "indexes": ["file_id", "file_url"]}


class GMailAccounts(BaseDocument):
    account_id = IntField(unique=True, required=True)
    account_name = StringField(unique=True, required=True)
    email_address = EmailField(required=True)
    api_key = StringField()
    servers = StringField(required=True)
    credential_file = StringField()
    token_file = StringField()

    meta = {"collection": "gmail_accounts", "indexes": ["account_id"]}


class IMAPAccounts(BaseDocument):
    account_id = IntField(unique=True, required=True)
    account_name = StringField(unique=True, required=True)
    imap_server_address = StringField()
    imap_username = StringField()
    imap_password = StringField()
    imap_security = StringField()
    imap_port = IntField()

    meta = {"collection": "imap_accounts", "indexes": ["account_id"]}


class MailTemplates(BaseDocument):
    template_id = IntField(unique=True, required=True)
    template_name = StringField(unique=True, required=True)
    description = StringField()
    contents = StringField()

    meta = {"collection": "mail_templates", "indexes": ["template_id"]}


class Jobs(BaseDocument):
    QUEUED = 0
    RUNNING = 1
    SUCCEEDED = 2
    FAILED = 3

    job_id = StringField(required=True, unique=True)
    name = StringField(required=True)
    parameters = DictField(default=dict)
    description = StringField()
    complete = BooleanField(default=False)
    start_time = DateTimeField(default=utcnow)
    end_time = DateTimeField()
    progress = IntField(default=0)
    job_status = IntField(default=QUEUED, choices=[0, 1, 2, 3])
    info = ListField(StringField(), default=list)
    schedule = StringField()
    errors = ListField(StringField(), default=list)

    meta = {"collection": "jobs", "indexes": ["job_id", "name", "job_status"]}


class SiteSettings(BaseDocument):
    ONLINE = 0
    LOCAL = 1

    settings_id = IntField(unique=True, required=True)
    site_name = StringField(unique=True, required=True)
    site_title = StringField(unique=True, required=True)
    site_description = StringField()
    site_logo = StringField()
    site_icon = StringField()
    login_image = StringField()
    site_keywords = StringField()
    startup_message = StringField()
    decryption_password = StringField()
    secret_key = StringField()
    address = StringField()
    email = StringField()
    mailing_list = ListField(EmailField(), default=list)
    phone_number = StringField()
    contact_us_message = StringField()
    google_map = StringField()
    social_media = DictField(default=dict)
    sync_mode = IntField(default=ONLINE, choices=[0, 1])
    time_out_minutes = IntField(default=0)
    overrides = DictField(default=dict)
    default_mailing_account = StringField()
    home_page_id = IntField()

    meta = {"collection": "site_settings", "indexes": ["settings_id"]}


class EventTypes(BaseDocument):
    type_id = IntField(unique=True, required=True)
    type_name = StringField(unique=True, required=True)
    description = StringField()
    handler = StringField()
    template = IntField()

    meta = {"collection": "event_types", "indexes": ["type_id"]}


class Events(BaseDocument):
    event_id = IntField(unique=True, required=True)
    event_name = StringField(unique=True, required=True)
    description = StringField()
    event_status = StringField(default="OPEN")
    notification_status = IntField()
    event_type = IntField(required=True)
    mail_template = IntField()
    job = StringField()
    parameters = DictField(default=dict)
    job_history = ListField(StringField(), default=list)

    meta = {"collection": "events", "indexes": ["event_id", "event_name"]}


class Schedules(BaseDocument):
    schedule_id = IntField(unique=True, required=True)
    name = StringField(unique=True, required=True)
    start_time = DateTimeField(default=utcnow)
    end_time = DateTimeField(default=utcnow)
    description = StringField()
    repeat = IntField()
    months = IntField(default=0)
    weeks = IntField(default=0)
    days = IntField(default=0)
    hours = IntField(default=0)
    minutes = IntField(default=0)
    seconds = IntField(default=0)
    schedule_status = IntField(default=0)

    meta = {"collection": "schedules", "indexes": ["schedule_id"]}


class EventTriggers(BaseDocument):
    trigger_id = IntField(unique=True, required=True)
    trigger_name = StringField(unique=True, required=True)
    description = StringField()
    trigger_count = IntField()
    event_type = IntField(required=True)
    schedule = IntField()
    parameters = DictField(default=dict)
    trigger_history = DictField(default=dict)

    meta = {"collection": "event_triggers", "indexes": ["trigger_id"]}


class Categories(BaseDocument):
    category_id = IntField(unique=True, required=True)
    parent_id = IntField()
    category_name = StringField(required=True)
    slug = StringField(unique=True, required=True)
    visible = BooleanField(default=True)
    sort_order = IntField(default=0)

    meta = {
        "collection": "categories",
        "indexes": ["category_id", "parent_id", "slug", "visible"],
    }


class Pages(BaseDocument):
    page_id = IntField(unique=True, required=True)
    category_id = IntField()
    parent_id = IntField()
    title = StringField(required=True)
    slug = StringField(unique=True, required=True)
    content_json = DictField(default=dict)
    visible = BooleanField(default=True)
    sort_order = IntField(default=0)
    seo_title = StringField()
    seo_description = StringField()

    meta = {
        "collection": "pages",
        "indexes": ["page_id", "category_id", "slug", "visible"],
    }


class Messages(BaseDocument):
    STATUS_NEW = 0
    STATUS_READ = 1
    STATUS_REPLIED = 2
    STATUS_ARCHIVED = 3
    STATUS_TRASHED = 4

    message_id = IntField(unique=True, required=True)
    from_name = StringField(required=True)
    from_email = EmailField(required=True)
    subject = StringField(required=True)
    body = StringField(required=True)
    status = IntField(default=STATUS_NEW)
    reply_to_id = IntField()
    sent_at = DateTimeField(default=utcnow)

    meta = {"collection": "messages", "indexes": ["message_id", "status"]}
