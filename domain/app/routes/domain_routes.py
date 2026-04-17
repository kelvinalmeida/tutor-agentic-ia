import json
import logging
import sys
import os
import tempfile
from flask import request, redirect, url_for, render_template, send_file, Blueprint, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from db import create_connection
# Importação do SDK do Vercel Blob
from vercel import blob

domain_bp = Blueprint('domain_bp', __name__)

def get_db_connection():
    return create_connection(current_app.config['SQLALCHEMY_DATABASE_URI'])

def fetch_domains_with_children(conn, domain_ids=None):
    cursor = conn.cursor()
    
    # 1. Fetch domains
    if domain_ids is not None:
        if not domain_ids:
            return []
        query = "SELECT * FROM domain WHERE id IN %s"
        cursor.execute(query, (tuple(domain_ids),))
    else:
        cursor.execute("SELECT * FROM domain")
    
    domains = cursor.fetchall()
    if not domains:
        return []

    domain_map = {d['id']: d for d in domains}
    for d in domain_map.values():
        d['pdfs'] = []
        d['exercises'] = []
        d['videos_uploaded'] = []
        d['videos_youtube'] = []

    domain_ids_tuple = tuple(domain_map.keys())
    
    # 2. Fetch children
    cursor.execute("SELECT * FROM pdf WHERE domain_id IN %s", (domain_ids_tuple,))
    pdfs = cursor.fetchall()
    for pdf in pdfs:
        domain_map[pdf['domain_id']]['pdfs'].append(pdf)

    cursor.execute("SELECT * FROM exercise WHERE domain_id IN %s", (domain_ids_tuple,))
    exercises = cursor.fetchall()
    for ex in exercises:
        if isinstance(ex['options'], str):
             ex['options'] = json.loads(ex['options'])
        domain_map[ex['domain_id']]['exercises'].append(ex)

    cursor.execute("SELECT * FROM video_upload WHERE domain_id IN %s", (domain_ids_tuple,))
    vus = cursor.fetchall()
    for vu in vus:
        domain_map[vu['domain_id']]['videos_uploaded'].append(vu)

    cursor.execute("SELECT * FROM video_youtube WHERE domain_id IN %s", (domain_ids_tuple,))
    vys = cursor.fetchall()
    for vy in vys:
        domain_map[vy['domain_id']]['videos_youtube'].append(vy)

    return list(domain_map.values())

@domain_bp.route('/domains/create', methods=['POST'])
def create_domain():
    # CORREÇÃO: Define a pasta temporária de acordo com o sistema
    # Se estiver no Vercel (Linux), usa /tmp. Se for local (Windows/Mac), usa a pasta temp do sistema.
    if os.environ.get('VERCEL'):
        TEMP_FOLDER = '/tmp'
    else:
        TEMP_FOLDER = tempfile.gettempdir()
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503
    
    cursor = conn.cursor()

    try:
        # 1. Coleta dados do formulário
        name = request.form.get('name')
        description = request.form.get('description')
        exercises_raw = request.form.get('exercises')
        
        youtube_links = request.form.getlist('youtube_link')
        pdf_files = request.files.getlist("pdfs")
        video_files = request.files.getlist("video")

        # 2. Criação do domínio
        query_domain = """
            INSERT INTO domain (name, description) 
            VALUES (%s, %s) 
            RETURNING id;
        """
        cursor.execute(query_domain, (name, description))
        domain_row = cursor.fetchone()
        new_domain_id = domain_row['id']

        # 3. Salva PDFs no Vercel Blob
        for file in pdf_files:
            if file and file.filename.endswith('.pdf'):
                filename = secure_filename(file.filename)
                temp_path = os.path.join(TEMP_FOLDER, filename)
                
                # Salva no /tmp primeiro
                file.save(temp_path)
                
                try:
                    # Envia para o Vercel Blob
                    # access='public' torna o arquivo acessível via URL
                    blob_response = blob.upload_file(
                        local_path=temp_path, 
                        path=filename, 
                        access='public',
                        add_random_suffix=True
                    )
                    # A resposta deve conter a URL pública
                    file_url = blob_response.url 
                    
                    query_pdf = """
                        INSERT INTO pdf (filename, path, domain_id) 
                        VALUES (%s, %s, %s);
                    """
                    # Gravamos a URL no campo 'path' do banco
                    cursor.execute(query_pdf, (filename, file_url, new_domain_id))
                finally:
                    # Limpa o arquivo temporário
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

        # 4. Salva vídeos enviados no Vercel Blob
        for video_file in video_files:
            if video_file and video_file.filename.endswith('.mp4'):
                filename = secure_filename(video_file.filename)
                temp_path = os.path.join(TEMP_FOLDER, filename)
                
                video_file.save(temp_path)
                
                try:
                    blob_response = blob.upload_file(
                        local_path=temp_path, 
                        path=filename, 
                        access='public',
                        add_random_suffix=True
                    )
                    file_url = blob_response.url
                    
                    query_video_upload = """
                        INSERT INTO video_upload (filename, path, domain_id) 
                        VALUES (%s, %s, %s);
                    """
                    cursor.execute(query_video_upload, (filename, file_url, new_domain_id))
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

        # 5. Salva links do YouTube
        for yt_url in youtube_links:
            yt_url = yt_url.strip()
            if yt_url:
                query_video_yt = """
                    INSERT INTO video_youtube (url, domain_id) 
                    VALUES (%s, %s);
                """
                cursor.execute(query_video_yt, (yt_url, new_domain_id))

        # 6. Salva exercícios
        if exercises_raw:
            exercises = json.loads(exercises_raw)
            for ex in exercises:
                question = ex.get("question", "").strip()
                options = ex.get("options", [])
                correct = ex.get("correct", "").strip()

                if question and options and correct:
                    query_exercise = """
                        INSERT INTO exercise (question, options, correct, domain_id) 
                        VALUES (%s, %s, %s, %s);
                    """
                    cursor.execute(query_exercise, (
                        question, 
                        json.dumps(options), 
                        correct, 
                        new_domain_id
                    ))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"message": "Domain created successfully!"}), 200

    except Exception as e:
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        logging.error(f"Erro ao criar domínio: {str(e)}")
        return jsonify({"message": "Erro ao processar criação", "error": str(e)}), 400


@domain_bp.route('/domains', methods=['GET'])
def list_domains():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503
    try:
        domains = fetch_domains_with_children(conn)
        return jsonify(domains), 200
    finally:
        conn.close()

@domain_bp.route('/domains/delete/<int:domain_id>', methods=['DELETE'])
def delete_domain(domain_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM domain WHERE id = %s", (domain_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Domain not found"}), 404

        # Delete associated files from Blob Storage
        # PDFs
        cursor.execute("SELECT path FROM pdf WHERE domain_id = %s", (domain_id,))
        for row in cursor.fetchall():
            try:
                # O 'path' agora contém a URL completa do Blob
                blob.delete(row['path'])
            except Exception as e:
                logging.warning(f"Failed to delete blob {row['path']}: {e}")
        
        # Videos Uploaded
        cursor.execute("SELECT path FROM video_upload WHERE domain_id = %s", (domain_id,))
        for row in cursor.fetchall():
            try:
                blob.delete(row['path'])
            except Exception as e:
                logging.warning(f"Failed to delete blob {row['path']}: {e}")

        # Delete domain (CASCADE handles DB records)
        cursor.execute("DELETE FROM domain WHERE id = %s", (domain_id,))
        conn.commit()
        return jsonify({"message": "Domain deleted successfully!"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@domain_bp.route('/domains/<int:domain_id>', methods=['GET'])
def get_domain(domain_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503
    try:
        domains = fetch_domains_with_children(conn, [domain_id])
        if not domains:
            return jsonify({"error": "Domain not found"}), 404
        return jsonify(domains[0]), 200
    finally:
        conn.close()


@domain_bp.route('/pdfs', methods=['GET'])
def list_pdfs():
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM pdf")
        pdfs = cursor.fetchall()
        return jsonify(pdfs), 200
    finally:
        cursor.close()
        conn.close()


@domain_bp.route('/pdfs/<int:pdf_id>', methods=['GET'])
def download_pdf(pdf_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT path FROM pdf WHERE id = %s", (pdf_id,))
        pdf = cursor.fetchone()
        if not pdf:
            return jsonify({'error': 'File not found'}), 404
        
        # Como agora o path é uma URL do Blob, redirecionamos o usuário
        return redirect(pdf['path'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@domain_bp.route('/domains/ids_to_names', methods=['GET'])
def ids_to_names():
    ids = request.args.getlist('ids')
    if not ids:
        return jsonify([]), 200
    try:
        ids = list(map(int, ids))
    except ValueError:
        return jsonify({"error": "IDs must be integers"}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503
    try:
        domains = fetch_domains_with_children(conn, ids)
        if not domains:
            return jsonify({"error": "No domains found"}), 404
        return jsonify(domains), 200
    finally:
        conn.close()


@domain_bp.route('/domains/<int:domain_id>/exercises', methods=['GET'])
def get_domain_exercises(domain_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM domain WHERE id = %s", (domain_id,))
        if not cursor.fetchone():
             return jsonify({"error": "Domain not found"}), 404

        cursor.execute("SELECT * FROM exercise WHERE domain_id = %s", (domain_id,))
        exercises = cursor.fetchall()
        for ex in exercises:
            if isinstance(ex['options'], str):
                ex['options'] = json.loads(ex['options'])
        return jsonify(exercises), 200
    finally:
        cursor.close()
        conn.close()


@domain_bp.route('/domains/<int:domain_id>/videos', methods=['GET'])
def get_domain_videos(domain_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM domain WHERE id = %s", (domain_id,))
        if not cursor.fetchone():
             return jsonify({"error": "Domain not found"}), 404

        cursor.execute("SELECT * FROM video_upload WHERE domain_id = %s", (domain_id,))
        videos_uploaded = cursor.fetchall()

        cursor.execute("SELECT * FROM video_youtube WHERE domain_id = %s", (domain_id,))
        videos_youtube = cursor.fetchall()
        
        return jsonify({
            "videos_uploaded": videos_uploaded,
            "videos_youtube": videos_youtube,
        }), 200
    finally:
        cursor.close()
        conn.close()


@domain_bp.route('/video/uploaded/<int:video_id>', methods=['GET'])
def get_uploaded_video(video_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT path FROM video_upload WHERE id = %s", (video_id,))
        video = cursor.fetchone()
        
        if not video:
             return jsonify({'error': 'Video not found'}), 404
             
        # Redireciona para a URL do Blob
        return redirect(video['path'])
    finally:
        cursor.close()
        conn.close()


@domain_bp.route('/exerc/testscores', methods=['POST'])
def get_test_scores():
    request_data = request.json
    logging.basicConfig(level=logging.INFO)
    logging.info("🔍 Dados recebidos domain: %s", request_data)
    sys.stdout.flush()

    student_name = request_data.get('student_name')
    student_id = request_data.get('student_id')
    answers = request_data.get('answers')

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503
    cursor = conn.cursor()

    try:
        score = 0
        if answers:
            for answer in answers:
                cursor.execute("SELECT correct FROM exercise WHERE id = %s", (answer['exercise_id'],))
                exercise = cursor.fetchone()
                
                if not exercise:
                    answer['correct'] = False
                    continue

                try:
                    is_correct = int(answer['answer']) == int(exercise['correct'])
                except (ValueError, TypeError):
                    is_correct = str(answer['answer']) == str(exercise['correct'])
                    
                if is_correct:
                    answer['correct'] = True
                    score += 1
                else:
                    answer['correct'] = False
        
        payload = {
            "student_name": student_name,
            "student_id": student_id,
            "answers": answers,
            "score": score,
        }

        logging.info("🔍 Respostas verificadas: %s", payload)
        sys.stdout.flush()

        return jsonify(payload), 200

    finally:
        cursor.close()
        conn.close()