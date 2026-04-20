import json
import logging
import sys
import os
from flask import request, send_file, Blueprint, jsonify, current_app
from werkzeug.utils import secure_filename
from db import create_connection

domain_bp = Blueprint('domain_bp', __name__)

def get_db_connection():
    return create_connection(current_app.config['SQLALCHEMY_DATABASE_URI'])


def get_upload_folder():
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if not upload_folder:
        upload_folder = os.path.join(current_app.root_path, 'uploads')

    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder


def generate_unique_filename(upload_folder, filename):
    base, ext = os.path.splitext(filename)
    candidate = filename
    counter = 1

    while os.path.exists(os.path.join(upload_folder, candidate)):
        candidate = f"{base}_{counter}{ext}"
        counter += 1

    return candidate


def resolve_local_file_path(db_path, filename):
    if db_path and os.path.exists(db_path):
        return db_path

    candidates = []
    if db_path:
        candidates.append(db_path)
        candidates.append(os.path.join(current_app.root_path, db_path))
        candidates.append(os.path.join(get_upload_folder(), os.path.basename(db_path)))

    if filename:
        candidates.append(os.path.join(get_upload_folder(), filename))

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate

    return None

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
    upload_folder = get_upload_folder()

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

        # 3. Salva PDFs localmente em domain/app/uploads
        for file in pdf_files:
            if file and file.filename.endswith('.pdf'):
                filename = secure_filename(file.filename)
                filename = generate_unique_filename(upload_folder, filename)
                local_path = os.path.join(upload_folder, filename)
                file.save(local_path)

                query_pdf = """
                    INSERT INTO pdf (filename, path, domain_id) 
                    VALUES (%s, %s, %s);
                """
                cursor.execute(query_pdf, (filename, local_path, new_domain_id))

        # 4. Salva vídeos enviados localmente em domain/app/uploads
        for video_file in video_files:
            if video_file and video_file.filename.endswith('.mp4'):
                filename = secure_filename(video_file.filename)
                filename = generate_unique_filename(upload_folder, filename)
                local_path = os.path.join(upload_folder, filename)
                video_file.save(local_path)

                query_video_upload = """
                    INSERT INTO video_upload (filename, path, domain_id) 
                    VALUES (%s, %s, %s);
                """
                cursor.execute(query_video_upload, (filename, local_path, new_domain_id))

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

        # Remove arquivos locais associados (pdf/video_upload)
        cursor.execute("SELECT filename, path FROM pdf WHERE domain_id = %s", (domain_id,))
        for row in cursor.fetchall():
            file_path = resolve_local_file_path(row.get('path'), row.get('filename'))
            if file_path:
                try:
                    os.remove(file_path)
                except OSError as e:
                    logging.warning(f"Falha ao remover arquivo local {file_path}: {e}")

        cursor.execute("SELECT filename, path FROM video_upload WHERE domain_id = %s", (domain_id,))
        for row in cursor.fetchall():
            file_path = resolve_local_file_path(row.get('path'), row.get('filename'))
            if file_path:
                try:
                    os.remove(file_path)
                except OSError as e:
                    logging.warning(f"Falha ao remover arquivo local {file_path}: {e}")

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
        cursor.execute("SELECT filename, path FROM pdf WHERE id = %s", (pdf_id,))
        pdf = cursor.fetchone()
        if not pdf:
            return jsonify({'error': 'File not found'}), 404

        file_path = resolve_local_file_path(pdf.get('path'), pdf.get('filename'))
        if not file_path:
            return jsonify({'error': 'File not found locally'}), 404

        return send_file(file_path, as_attachment=False)
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
        cursor.execute("SELECT filename, path FROM video_upload WHERE id = %s", (video_id,))
        video = cursor.fetchone()

        if not video:
             return jsonify({'error': 'Video not found'}), 404

        file_path = resolve_local_file_path(video.get('path'), video.get('filename'))
        if not file_path:
            return jsonify({'error': 'Video file not found locally'}), 404

        return send_file(file_path, as_attachment=False)
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