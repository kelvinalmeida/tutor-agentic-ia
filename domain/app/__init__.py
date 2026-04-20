import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv  # 1. Importe o load_dotenv

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # 2. Carregue o config.env explicitamente
    # Isso garante que as variáveis sejam lidas antes de usar o os.getenv abaixo
    load_dotenv(os.path.join(os.getcwd(), 'config.env'))


    # --- BLOCO OBRIGATÓRIO PARA VERCEL ---
    # Verifica se está rodando no Vercel para mudar a pasta de instância
    if os.environ.get('VERCEL'):
        # No Vercel, definimos a pasta de instância para /tmp (único local gravável)
        app = Flask(__name__, instance_relative_config=True, instance_path='/tmp')
    else:
        # Localmente, mantém o comportamento padrão
        app = Flask(__name__, instance_relative_config=True)

    # Caminho para o banco dentro da pasta 'instance'
    # app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///../instance/sessions.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///../instance/users.db")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'sua_chave_super_secreta'

    # Inicializar extensões
    db.init_app(app)
    migrate.init_app(app, db)

    # Registrar blueprints
    from app.routes.domain_routes import domain_bp
    from app.routes.agente_domain_routes import agente_domain_bp


    app.register_blueprint(domain_bp)
    app.register_blueprint(agente_domain_bp)

    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    return app
