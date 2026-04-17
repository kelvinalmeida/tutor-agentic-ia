from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from config import Config
from dotenv import load_dotenv  # 1. Importe o load_dotenv
# from flask_socketio import SocketIO

db = SQLAlchemy()
migrate = Migrate()


# socketio = SocketIO()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # 2. Carregue o config.env explicitamente
    # Isso garante que as variáveis sejam lidas antes de usar o os.getenv abaixo
    load_dotenv(os.path.join(os.getcwd(), 'config.env'))

    app.config.from_object(Config)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///../instance/users.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config['SECRET_KEY'] = 'sua_chave_super_secreta'

    from app.routes.strategies_routes import strategies_bp
    from app.routes.agente_strategies_routes import agente_strategies_bp

    # colocar a variavel config.env no environment no flask



    # Registrar o blueprint
    app.register_blueprint(strategies_bp)
    app.register_blueprint(agente_strategies_bp)

    # Inicializar extensões
    db.init_app(app)
    migrate.init_app(app, db)
    # socketio.init_app(app)

    return app
