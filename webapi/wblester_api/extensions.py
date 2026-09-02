"""Flask extension singletons initialized in create_app."""

from flask_cors import CORS
from flask_jwt_extended import JWTManager

jwt = JWTManager()
cors = CORS()
