import os
from flask import request, send_file, Blueprint, jsonify, current_app
from db import create_connection
from pypdf import PdfReader

agente_domain_bp = Blueprint('agente_domain_bp', __name__)


def get_db_connection():
    """Helper para conectar ao banco usando a config da app"""
    return create_connection(current_app.config['SQLALCHEMY_DATABASE_URI'])


@agente_domain_bp.route('/get_content/<int:id>', methods=['GET'])
def get_article_content(id):
    """
    Recupera o conteúdo de um PDF pelo ID usando armazenamento local.
    """
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 503

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT filename, description, path FROM rag_library WHERE id = %s", (id,))
        pdf = cursor.fetchone()

        if not pdf:
            return jsonify({"error": "PDF não encontrado no banco de dados."}), 404

        filename = pdf['filename']
        db_path = pdf['path']
        request_format = request.args.get('format', 'text')

        file_path = db_path
        if not file_path or not os.path.exists(file_path):
            possible_upload_path = os.path.join(current_app.root_path, 'uploads', filename)
            possible_shared_path = os.path.join(current_app.root_path, 'RAG_arquivos_compartilhados', filename)

            if os.path.exists(possible_upload_path):
                file_path = possible_upload_path
            elif os.path.exists(possible_shared_path):
                file_path = possible_shared_path

        if not file_path or not os.path.exists(file_path):
            return jsonify({"error": f"Arquivo físico não encontrado localmente: {filename}"}), 404

        if request_format == 'pdf':
            return send_file(file_path, as_attachment=False)

        try:
            reader = PdfReader(file_path)
            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text() + "\n"

            return jsonify({
                "id": id,
                "filename": filename,
                "description": pdf.get('description'),
                "content": text_content.strip(),
                "source": "local"
            })
        except Exception as e:
            return jsonify({"error": f"Erro ao ler o PDF local: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
