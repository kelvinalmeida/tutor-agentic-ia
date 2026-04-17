import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv  # 1. Importe o load_dotenv

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # 2. Carregue o config.env explicitamente
    # Isso garante que as variáveis sejam lidas antes de usar o os.getenv abaixo
    load_dotenv(os.path.join(os.getcwd(), 'config.env'))

    # Agora o DATABASE_URL será encontrado
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///../instance/users.db")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Registrar blueprints
    from app.routes.session_routes import session_bp
    from app.routes.agente_control_routes import agente_control_bp
    app.register_blueprint(session_bp)
    app.register_blueprint(agente_control_bp)

    return app