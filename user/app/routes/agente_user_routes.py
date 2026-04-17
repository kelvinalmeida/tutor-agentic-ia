import json
import logging
import os
from flask import Blueprint, request, jsonify, current_app
from google import genai
from openai import OpenAI
from config import Config

try:
    from db import create_connection
except ImportError:
    from ...db import create_connection

agente_user_bp = Blueprint('agente_user_bp', __name__)

logging.basicConfig(level=logging.INFO)

def ensure_tutor_chat_table(conn):
    """Garante que a tabela de histórico do tutor existe."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tutor_chat_history (
                id SERIAL PRIMARY KEY,
                student_username VARCHAR(100) NOT NULL,
                sender VARCHAR(20) NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

@agente_user_bp.route('/students/summarize_preferences', methods=['POST'])
def summarize_preferences():
    """
    Agente User: Recebe IDs, busca via SQL Direto (psycopg2) e resume com Gemini.
    """
    data = request.get_json()
    student_ids = data.get('student_ids', [])

    if not student_ids:
        return jsonify({"summary": "Nenhum estudante selecionado."}), 200

    conn = None
    try:
        db_url = getattr(Config, 'SQLALCHEMY_DATABASE_URI', os.getenv('DATABASE_URL'))
        conn = create_connection(db_url)
        
        if not conn:
             return jsonify({"error": "Falha na conexão com o banco de dados"}), 500

        students_data = []
        
        with conn.cursor() as cur:
            try:
                clean_ids = [int(x) for x in student_ids]
            except ValueError:
                clean_ids = student_ids

            query = """
                SELECT name, pref_content_type, pref_communication, pref_receive_email
                FROM student 
                WHERE student_id = ANY(%s)
            """
            cur.execute(query, (clean_ids,))
            students_data = cur.fetchall()

        if not students_data:
            return jsonify({"summary": "Estudantes não encontrados na base de dados."}), 404

        profiles_text = []
        for s in students_data:
            name = s.get('name', 'Aluno')
            p_type = s.get('pref_content_type') or 'Não informado'
            p_comm = s.get('pref_communication') or 'Não informado'
            recebe_email = s.get('pref_receive_email')
            txt_email = "Aceita receber emails" if recebe_email else "NÃO aceita emails"
            
            profiles_text.append(f"- Aluno {name}: Prefere '{p_type}' via '{p_comm}'. {txt_email}.")
        
        profiles_joined = "\n".join(profiles_text)
        

        prompt = f"""
        Atue como um Especialista Pedagógico.
        Analise estas preferências de aprendizado reais:
        {profiles_joined}
        
        OBJETIVO:
        Escreva um parágrafo único e conciso resumindo o perfil da turma.
        Destaque a mídia e o canal mais efetivos.
        Diga explicitamente se o e-mail é um canal viável para a maioria.

        FORMATO DE SAÍDA:
        Apenas o texto corrido, sem formatação JSON, sem markdown e sem títulos.
        """

        logging.info(f"Prompt para Agente User: {prompt}")

        client = OpenAI(
            api_key=Config.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Você é um assistente pedagógico conciso."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2 
        )

        content_text = response.choices[0].message.content
        
        try:
            summary_dict = json.loads(content_text)
        except json.JSONDecodeError:
            summary_dict = {
                "resumo": content_text,
                "perfil_turma": {},
                "uso_email": "Indeterminado"
            }

        return jsonify({
            "summary": summary_dict,
            "student_count": len(students_data)
        }), 200
    
    except Exception as e:
        logging.error(f"Erro no Agente User: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@agente_user_bp.route('/agent/generate_student_feedback', methods=['POST'])
def generate_student_feedback():
    """
    Gera um feedback ou resposta para o aluno baseada no prompt e contexto agregado.
    Salva o histórico da conversa.
    """
    data = request.get_json() or {}
    conn = None

    try:
        # 1. Extração de Dados do Payload Agregado
        username = data.get('student_username')
        user_prompt = data.get('user_prompt')
        study_context = data.get('study_context', {})

        if not username:
            return jsonify({"error": "student_username é obrigatório"}), 400

        # 2. Conectar ao Banco
        db_url = getattr(Config, 'SQLALCHEMY_DATABASE_URI', os.getenv('DATABASE_URL'))
        conn = create_connection(db_url)

        prefs = {}
        if conn:
            ensure_tutor_chat_table(conn)

            # Busca perfil
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT pref_content_type, pref_communication, pref_receive_email
                    FROM student WHERE username = %s
                """, (username,))
                row = cur.fetchone()
                if row:
                    prefs = dict(row)

            # SALVA MENSAGEM DO USUÁRIO
            if user_prompt:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO tutor_chat_history (student_username, sender, message)
                        VALUES (%s, 'user', %s)
                    """, (username, str(user_prompt)))
                    conn.commit()

        # 3. Configuração LLM
        if not Config.GROQ_API_KEY:
             return jsonify({"error": "GROQ_API_KEY não configurada"}), 500

        client = OpenAI(
            api_key=Config.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )

        # 4. Construção do Contexto para o Prompt
        context_str = "CONTEXTO DE ESTUDO RECENTE:\n"
        last_session_id = None
        last_domain_name = None

        if not study_context:
            context_str += "Nenhum histórico recente encontrado.\n"
        else:
            for d_name, d_info in study_context.items():
                context_str += f"\n=== Domínio: {d_name} ===\n"
                context_str += f"Descrição: {d_info.get('description', '')}\n"

                # Materiais (PDF apenas, Videos removidos)
                mats = d_info.get('material_complementar', {})
                pdfs = mats.get('pdfs', [])

                if pdfs:
                    context_str += "Materiais de Apoio (PDFs):\n"
                    for p in pdfs:
                        fname = p.get('filename', 'arquivo.pdf')
                        preview = p.get('pdf_content', '')
                        if len(preview) > 200:
                            preview = preview[:200] + "..."

                        context_str += f"  - Arquivo: {fname}\n"
                        if preview:
                             context_str += f"    Trecho Inicial: {preview}\n"

                # ANÁLISE DO AGENTE (Substitui histórico detalhado)
                analysis = d_info.get('session_analysis', {})
                if analysis:
                    last_domain_name = d_name
                    context_str += "ANÁLISE DE DESEMPENHO E ENGAJAMENTO:\n"
                    context_str += f"  - Performance: {analysis.get('performance', 'N/A')}\n"
                    context_str += f"  - Engajamento: {analysis.get('engagement', 'N/A')}\n"

        # 5. Prompt Final
        system_prompt = f"""
        Você é um Mentor Pedagógico Pessoal e Inteligente.
        O aluno {username} entrou em contato.

        PERFIL DO ALUNO:
        - Prefere conteúdo: {prefs.get('pref_content_type', 'Não informado')}
        - Comunicação: {prefs.get('pref_communication', 'Não informado')}
        - Email: {'Sim' if prefs.get('pref_receive_email') else 'Não'}

        {context_str}

        SUA TAREFA:
        Responda ao PROMPT DO USUÁRIO abaixo.
        1. Se for uma dúvida, responda usando o contexto (especialmente trechos de PDF se houver).
        2. Se for um pedido de feedback, analise o desempenho nas sessões listadas.
        3. Adapte a resposta ao perfil do aluno.
        4. Seja encorajador e direto.
        """

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(user_prompt)}
            ],
            temperature=0.5,
            max_tokens=600
        )

        feedback_text = response.choices[0].message.content

        # 6. Salvar no Banco (Feedback + Mensagem Chat)
        new_id = None
        if conn and feedback_text:
            try:
                # Salva na tabela chat history
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO tutor_chat_history (student_username, sender, message)
                        VALUES (%s, 'agent', %s)
                    """, (username, feedback_text))
                    conn.commit()

                # Salva na tabela student_feedback (Legacy/Structured) se tiver dados
                # Nota: session_id não está mais disponível no payload simplificado
                sid_to_save = None

                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO student_feedback
                        (student_username, session_id, domain_name, feedback_content)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id
                    """, (username, sid_to_save, last_domain_name, feedback_text))

                    new_row = cur.fetchone()
                    if new_row:
                        if isinstance(new_row, dict):
                            new_id = new_row['id']
                        else:
                            new_id = new_row[0]
                    conn.commit()
            except Exception as db_err:
                logging.warning(f"Erro ao salvar no banco: {db_err}")

        return jsonify({
            "status": "success",
            "student": username,
            "response": feedback_text,
            "feedback_id": new_id
        }), 200

    except Exception as e:
        logging.error(f"Erro ao gerar feedback: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@agente_user_bp.route('/agent/chat_history', methods=['GET'])
def get_chat_history():
    """Retorna o histórico de conversas do tutor."""
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username required"}), 400

    conn = None
    try:
        db_url = getattr(Config, 'SQLALCHEMY_DATABASE_URI', os.getenv('DATABASE_URL'))
        conn = create_connection(db_url)
        if not conn:
             return jsonify({"error": "DB Error"}), 500

        ensure_tutor_chat_table(conn)

        history = []
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sender, message, created_at
                FROM tutor_chat_history
                WHERE student_username = %s
                ORDER BY created_at ASC
            """, (username,))
            rows = cur.fetchall()
            for r in rows:
                history.append({
                    "sender": r['sender'],
                    "message": r['message'],
                    "timestamp": r['created_at'].isoformat() if r['created_at'] else None
                })

        return jsonify(history), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

@agente_user_bp.route('/agent/chat_history', methods=['DELETE'])
def clear_chat_history():
    """Limpa o histórico de conversas."""
    username = request.args.get('username')
    if not username:
        return jsonify({"error": "Username required"}), 400

    conn = None
    try:
        db_url = getattr(Config, 'SQLALCHEMY_DATABASE_URI', os.getenv('DATABASE_URL'))
        conn = create_connection(db_url)
        if not conn:
             return jsonify({"error": "DB Error"}), 500

        ensure_tutor_chat_table(conn)

        with conn.cursor() as cur:
            cur.execute("DELETE FROM tutor_chat_history WHERE student_username = %s", (username,))
            conn.commit()

        return jsonify({"status": "cleared"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()


@agente_user_bp.route('/agent/help_student', methods=['POST'])
def help_student_agent():
    """
    Rota legada.
    """
    try:
        data = request.get_json()
        username = data.get('student_username')
        user_prompt = data.get('user_prompt')
        
        if not Config.GROQ_API_KEY:
             return jsonify({"error": "GROQ_API_KEY não configurada"}), 500

        client = OpenAI(
            api_key=Config.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tutor Inteligente."},
                {"role": "user", "content": str(user_prompt)}
            ],
            temperature=0.5
        )

        return jsonify({
            "status": "success",
            "response": response.choices[0].message.content
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
