import jwt
import datetime
from flask import Blueprint, request, jsonify, current_app
from db import create_connection
# from ..models import Student, Teacher  <-- Removed

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password_input = data.get('password')

    conn = create_connection(current_app.config['SQLALCHEMY_DATABASE_URI'])
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503
    
    cursor = conn.cursor()

    try:
        user = None
        
        # 1. Tenta achar no banco de ALUNOS
        # Usamos ALIAS (AS) para padronizar os nomes das colunas (id, password_hash)
        query_student = """
            SELECT student_id AS id, username, type, password_hash 
            FROM student 
            WHERE username = %s
        """
        cursor.execute(query_student, (username,))
        user_student = cursor.fetchone()

        if user_student:
            user = user_student
        else:
            # 2. Se não achou, tenta achar no banco de PROFESSORES
            query_teacher = """
                SELECT teacher_id AS id, username, type, password_hash 
                FROM teacher 
                WHERE username = %s
            """
            cursor.execute(query_teacher, (username,))
            user_teacher = cursor.fetchone()
            
            if user_teacher:
                user = user_teacher

        # Fecha a conexão o quanto antes (já temos os dados na variável 'user')
        cursor.close()
        conn.close()

        # 3. Se não achou em nenhum dos dois
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # 4. Verificação de Senha
        # Como removemos o Model, perdemos o método user.check_password().
        # Aqui comparamos a senha do banco (user['password_hash']) com a entrada.
        # OBS: Se você usava hash (bcrypt/pbkdf2), troque a linha abaixo por:
        # if check_password_hash(user['password_hash'], password_input):
        
        stored_password = user['password_hash']

        if stored_password == password_input:
            token = jwt.encode({
                'id': user['id'],         # Acessando via chave de dicionário
                'type': user['type'],     # Acessando via chave de dicionário
                'username': user['username'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }, current_app.config['SECRET_KEY'], algorithm='HS256')
            
            return jsonify({'token': token})

        return jsonify({'error': 'Invalid credentials'}), 401

    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"error": str(e)}), 500
    
# import jwt
# import datetime
# from flask import Blueprint, request, jsonify, current_app
# from ..models import Student, Teacher

# auth_bp = Blueprint('auth_bp', __name__)

# @auth_bp.route('/login', methods=['POST'])
# def login():
#     data = request.get_json()
#     username = data.get('username')
#     password = data.get('password')

#     user_student = Student.query.filter_by(username=username).first()
#     user_teacher = Teacher.query.filter_by(username=username).first()
    
#     if user_student:
#         user = user_student
#     else:
#         user = user_teacher

#     if not user:
#         return jsonify({'error': 'User not found'}), 404
    
#     # print(f"User found: {user.username}, Type: {user.type}, password: {user.password_hash}")

#     if user and user.check_password(password):
#         token = jwt.encode({
#             'id': user.id,
#             'type': user.type,
#             'username': user.username,
#             'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
#         }, current_app.config['SECRET_KEY'], algorithm='HS256')
#         return jsonify({'token': token})

#     return jsonify({'error': 'Invalid credentials'}), 401
