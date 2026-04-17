from flask import Flask
from flask_socketio import SocketIO

# from .routes import register_routes

socketio = SocketIO()

app = Flask(__name__)
app.secret_key = "sua_chave_super_secreta"
app.config['SECRET_KEY'] = "sua_chave_super_secreta"
socketio.init_app(app)

from routes.login import login_bp
from routes.student import student_bp
from routes.teacher import teacher_bp
from routes.session import session_bp
from routes.strategies import strategy_bp
from routes.domain import domain_bp
from routes.orchestrator.agente_strategies.agete_strategies_routes import agete_strategies_bp
from routes.orchestrator.agente_user.agente_user_routes import agete_user_bp

app.register_blueprint(login_bp)
app.register_blueprint(student_bp)
app.register_blueprint(teacher_bp)
app.register_blueprint(session_bp)
app.register_blueprint(strategy_bp)
app.register_blueprint(domain_bp)
app.register_blueprint(agete_strategies_bp)
app.register_blueprint(agete_user_bp)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

