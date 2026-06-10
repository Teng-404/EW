"""
app.py — Election Web : Application Factory  (README v2)

เพิ่ม verify_bp blueprint
"""

from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import ActiveConfig
from db import init_pool, close_db

login_manager = LoginManager()
csrf = CSRFProtect()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(ActiveConfig)

    init_pool()
    app.teardown_appcontext(close_db)

    _init_login_manager(app)
    csrf.init_app(app)
    _register_blueprints(app)

    return app


def _init_login_manager(app: Flask) -> None:
    login_manager.init_app(app)
    login_manager.login_view    = "auth.login"
    login_manager.login_message = "กรุณาเข้าสู่ระบบก่อน"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id: str):
        from models.user import User
        return User.get_by_id(int(user_id))


def _register_blueprints(app: Flask) -> None:
    from routes.auth     import auth_bp
    from routes.verify   import verify_bp     
    from routes.vote     import vote_bp
    from routes.candidates import candidates_bp
    from routes.admin    import admin_bp
    from routes.pwa        import pwa_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(verify_bp)          # ← /verify, /verify/otp
    app.register_blueprint(vote_bp)            # ← /vote/*, /results/*
    app.register_blueprint(candidates_bp)      # ← /candidates/*
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(pwa_bp)

if __name__ == "__main__":
    app = create_app()
    app.run(debug=ActiveConfig.DEBUG, host="0.0.0.0", port=5000)
