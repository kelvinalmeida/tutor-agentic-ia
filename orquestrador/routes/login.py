from flask import Blueprint, render_template, request, redirect, url_for, make_response
from requests.exceptions import RequestException
from .auth import token_required
import requests

from .auth import verificar_cookie
from .services_routs import USER_URL

login_bp = Blueprint("login", __name__)

@login_bp.route("/")
def home_page():
    print("Entrou na home")
    current_user = verificar_cookie()

    if current_user:
        # Se o usuário estiver autenticado, redireciona para a página de inicial
        return render_template("dashboard.html", current_user=current_user)
    
    return render_template("start.html")

@login_bp.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            response = requests.post(f"{USER_URL}/login", json={"username": username, "password": password})
            if response.status_code == 200:
                token = response.json().get("token") 
                
                # Criar resposta com cookie
                resp = make_response(redirect(url_for('login.home_page')))  # exemplo
                resp.set_cookie('access_token', token, httponly=True, max_age=3600)  # 1 hora
                return resp
            else:
                return render_template("login.html", error="Login failed.")
        except RequestException as e:
            return render_template("login.html", error="User service unavailable.")
    
    return render_template("login.html")

@login_bp.route('/logout')
def logout():
    # Criar uma resposta redirecionando para a tela de login
    resp = make_response(redirect(url_for('login.home_page')))
    
    # Remover o cookie do token
    resp.set_cookie('access_token', '', expires=0)
    
    return resp

@login_bp.route('/perfil')
@token_required
def perfil(current_user=None):
    # print(current_user)
    if current_user["type"] == "student":
        user_id = current_user['id']
        url = f"{USER_URL}/students/{user_id}"
    else:
        user_id = current_user['id']
        url = f"{USER_URL}/teachers/{user_id}"

    response = requests.get(url)
    user = response.json()
    return render_template('perfil.html', user=user)