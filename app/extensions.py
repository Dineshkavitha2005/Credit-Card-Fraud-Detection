from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from audit_logger import audit_logger, EventType

db = SQLAlchemy()
login_manager = LoginManager()
cors = CORS()
