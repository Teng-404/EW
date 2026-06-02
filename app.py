"""
app.py — Election Web : Application Factory

สร้าง Flask app ผ่าน create_app() เพื่อรองรับ:
- หลาย environment (dev/prod/test)
- Blueprint registration
- Extension initialization
"""

from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import ActiveConfig
from db import init_pool, close_db

# ── Extensions (init ที่นี่ ผูก app ใน create_app) ─────────
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(ActiveConfig)

    # ── Database pool ──────────────────────────────────────
    init_pool()
    app.teardown_appcontext(close_db)   # คืน connection อัตโนมัติ

    # ── Extensions ────────────────────────────────────────
    _init_login_manager(app)
    csrf.init_app(app)

    # ── Blueprints ────────────────────────────────────────
    _register_blueprints(app)

    return app


# ── Login Manager ──────────────────────────────────────────
def _init_login_manager(app: Flask) -> None:
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"           # redirect เมื่อยังไม่ login
    login_manager.login_message = "กรุณาเข้าสู่ระบบก่อน"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id: str):
        from models.user import User
        return User.get_by_id(int(user_id))


# ── Blueprint Registration ─────────────────────────────────
def _register_blueprints(app: Flask) -> None:
    from routes.auth       import auth_bp
    from routes.vote       import vote_bp
    from routes.candidates import candidates_bp
    from routes.admin      import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(vote_bp)
    app.register_blueprint(candidates_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")


# ── Entry point ────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    app.run(debug=ActiveConfig.DEBUG, host="0.0.0.0", port=5000)
