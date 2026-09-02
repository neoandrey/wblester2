"""Blueprint registry."""

from .auth import bp as auth_bp
from .categories import bp as categories_bp
from .data import bp as data_bp
from .diagnostics import bp as diagnostics_bp
from .messages import bp as messages_bp
from .pages import bp as pages_bp
from .permissions import bp as permissions_bp
from .public import bp as public_bp
from .roles import bp as roles_bp
from .scheduler_admin import bp as scheduler_admin_bp
from .settings import bp as settings_bp
from .stats import bp as stats_bp
from .sync import bp as sync_bp
from .system_logs import bp as system_logs_bp
from .uploads import bp as uploads_bp
from .users import bp as users_bp

ALL_BLUEPRINTS = [
    auth_bp,
    sync_bp,
    data_bp,
    diagnostics_bp,
    pages_bp,
    categories_bp,
    settings_bp,
    users_bp,
    roles_bp,
    permissions_bp,
    messages_bp,
    uploads_bp,
    scheduler_admin_bp,
    system_logs_bp,
    stats_bp,
    public_bp,
]
