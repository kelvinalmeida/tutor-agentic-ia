from flask import Blueprint, request, jsonify
import requests
import logging
import json
import sys
import os
from ...services_routs import STRATEGIES_URL, DOMAIN_URL, CONTROL_URL, USER_URL

# Importação robusta das variáveis de serviço (STRATEGIES_URL, DOMAIN_URL)
# Tenta importar relativo, se falhar (devido à profundidade da pasta), ajusta o path.
# try:
#     from routes.services_routs import STRATEGIES_URL, DOMAIN_URL
# except ImportError:
#     # Adiciona o diretório raiz do gateway ao path
#     sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
#     from services_routs import STRATEGIES_URL, DOMAIN_URL

agete_strategies_bp = Blueprint('agete_strategies_bp', __name__)

@agete_strategies_bp.route('/strategies/orchestrate_validation', methods=['POST'])
def orchestrate_validation():
    """
    Agente Orquestrador.
    Fluxo:
    1. Recebe dados do Front.
    2. Busca o conteúdo do Artigo no serviço de Domínio (Memória).
    3. Envia Artigo + Estratégia para o serviço Strategies (Worker com Gemini).
    4. Devolve a resposta para o Front.
    """
    try:
        data = request.json
        strategy_name = data.get('name')
        tactics_names = data.get('tactics', [])
        
        # ID do artigo fixo para este cenário (Padrão Pedagógico)
        article_id = 1 
        
        # ---------------------------------------------------------
        # 1. Passo: Buscar Memória (Call Domain Service)
        # ---------------------------------------------------------
        article_content = ""
        try:
            # O Orquestrador pede ao Domain o texto extraído do PDF
            domain_response = requests.get(f"{DOMAIN_URL}/get_content/1", timeout=10)
            
            if domain_response.status_code == 200:
                article_content = domain_response.json().get('content', "")
                if not article_content:
                    logging.warning("Conteúdo do artigo veio vazio do Domain.")
                    article_content = "Conteúdo não disponível. Avalie apenas com base nas boas práticas gerais."
            else:
                logging.warning(f"Domain Service retornou erro: {domain_response.status_code}")
                article_content = "Erro ao recuperar contexto pedagógico. Avalie genericamente."

        except Exception as e:
             logging.error(f"Erro ao conectar com Domain: {e}")
             article_content = "Sistema de memória indisponível."

        # ---------------------------------------------------------
        # 2. Passo: Chamar o Agente Worker (Call Strategies Service)
        # ---------------------------------------------------------
        worker_payload = {
            "name": strategy_name,
            "tactics": tactics_names,
            "context": article_content
        }

        # logging.warning(f"Payload enviado ao Strategies Agent: {worker_payload}")

        logging.warning(f"Domain Service retornou erro: {domain_response.status_code}")
        
        try:
            # Envia para o serviço Strategies onde o Gemini processará
            agent_response = requests.post(f"{STRATEGIES_URL}/agent/critique", json=worker_payload, timeout=30)
            
            if agent_response.status_code == 200:
                return jsonify(agent_response.json())
            else:
                return jsonify({
                    "grade": 0, 
                    "feedback": f"O Agente de Estratégia falhou. Código: {agent_response.status_code}", 
                    "status": "error"
                }), agent_response.status_code

        except Exception as e:
            logging.error(f"Erro ao conectar com Strategies Agent: {e}")
            return jsonify({
                "grade": 0, 
                "feedback": "Erro de comunicação com o Agente Especialista.", 
                "status": "error"
            }), 503

    except Exception as e:
        return jsonify({"error": "Orchestration failed", "details": str(e)}), 500


@agete_strategies_bp.route('/sessions/<int:session_id>/execute_rules', methods=['POST'])
def execute_rules_logic(session_id):
    """
    Orquestrador da Tática de Regras.
    Agrega contexto de todos os serviços e consulta o Agente de Estratégia para decisão.
    """
    try:
        # 1. Agregação de Contexto (Data Fetching)

        # A. Do Serviço Control: Detalhes da Sessão
        try:
            session_response = requests.get(f"{CONTROL_URL}/sessions/{session_id}", timeout=10)
            if session_response.status_code != 200:
                return jsonify({"error": "Falha ao buscar sessão no Control"}), 502
            session_data = session_response.json()

            # Control retorna strategies como lista de strings/ints
            strategies_list = session_data.get('strategies', [])
            strategy_id = strategies_list[0] if strategies_list else None
            domain_id = int(session_data.get('domains', None)[0]) if session_data.get('domains') else None
            # return  jsonify(domain_id)
            current_tactic_index = session_data.get('current_tactic_index', 0)
            student_ids = session_data.get('students', [])
        except Exception as e:
            logging.error(f"Erro ao conectar com Control (Sessão): {e}")
            return jsonify({"error": "Control Service unavailable"}), 503

        # B. Do Serviço Control: Resumo do Agente (Performance)
        agent_summary_text = "Resumo indisponível."
        try:
            summary_response = requests.get(f"{CONTROL_URL}/sessions/{session_id}/agent_summary", timeout=15)
            if summary_response.status_code == 200:
                agent_summary_text = summary_response.json().get('summary', "")
        except Exception as e:
            logging.warning(f"Erro ao buscar agent_summary: {e}")

        # C. Do Serviço Strategies: Detalhes da Estratégia (para calcular executed_tactics)
        executed_tactics_ids = []
        strategy_tactics = []
        try:
            if strategy_id:
                strat_response = requests.get(f"{STRATEGIES_URL}/strategies/{strategy_id}", timeout=10)
                if strat_response.status_code == 200:
                    strategy_data = strat_response.json()
                    strategy_tactics = strategy_data.get('tatics', [])

                    # CORREÇÃO: Não inferir execução baseada apenas no índice (i < current_index).
                    # Se o agente pulou táticas (ex: foi da 1 para a 4), as táticas 2 e 3 não foram executadas.
                    # Como não temos log exato de navegação no MVP, enviamos lista vazia ou parcial
                    # para permitir que o agente escolha qualquer tática anterior se julgar necessário.
                    #
                    # OLD LOGIC:
                    # for i, tactic in enumerate(strategy_tactics):
                    #     if i < current_tactic_index:
                    #         executed_tactics_ids.append(tactic['id'])

                    # NOVO: Usar executed_indices do Control
                    executed_indices = session_data.get('executed_indices', [])

                    # Mapeia índices para IDs
                    for idx in executed_indices:
                        if 0 <= idx < len(strategy_tactics):
                            executed_tactics_ids.append(strategy_tactics[idx]['id'])

                    # Adiciona a atual (que acabou de finalizar/está em Regra)
                    if 0 <= current_tactic_index < len(strategy_tactics):
                        current_id = strategy_tactics[current_tactic_index]['id']
                        if current_id not in executed_tactics_ids:
                            executed_tactics_ids.append(current_id)

        except Exception as e:
            logging.error(f"Erro ao conectar com Strategies: {e}")
            return jsonify({"error": "Strategies Service unavailable"}), 503

        # D. Do Serviço User: Perfil da Turma
        student_profile_summary = "Perfil desconhecido."
        try:
            if student_ids:
                user_payload = {"student_ids": student_ids}
                user_response = requests.post(f"{USER_URL}/students/summarize_preferences", json=user_payload, timeout=10)
                if user_response.status_code == 200:
                    # O endpoint retorna { "summary": ... } onde summary pode ser dict ou string
                    summary_data = user_response.json().get('summary', "")
                    if isinstance(summary_data, dict):
                        student_profile_summary = json.dumps(summary_data, ensure_ascii=False)
                    else:
                        student_profile_summary = str(summary_data)
            
            # logging.info(f"Perfil resumido dos alunos para a tatica de regras: {student_profile_summary}")
        except Exception as e:
            logging.warning(f"Erro ao conectar com User: {e}")

        # E. Do Serviço Domain: Conteúdo da Aula
        article_text = ""
        try:
            # domain_response = requests.get(f"{DOMAIN_URL}/get_content/2", timeout=10)
            domain_response = requests.get(f"{DOMAIN_URL}/domains/{domain_id}", timeout=10)
            domain_name_and_description = {
                "Conteudo da aula": domain_response.json().get("name", ""),
                "description do conteúdo da aula": domain_response.json().get("description", "")
            }   
            # return jsonify(domain_name_and_description)



            if domain_response.status_code == 200:
                article_text = domain_response.json().get('content', "")
        except Exception as e:
             logging.warning(f"Erro ao conectar com Domain: {e}")

        # 2. Consulta à Tática de Regras (Decision Making)
        decision_payload = {
            "strategy_id": strategy_id,
            "executed_tactics": executed_tactics_ids,
            "performance_summary": agent_summary_text,
            "student_profile_summary": student_profile_summary,
            "article_text": domain_name_and_description
        }

        decision_data = {}
        try:
            agent_response = requests.post(f"{STRATEGIES_URL}/agent/decide_rules_logic", json=decision_payload, timeout=30)
            if agent_response.status_code == 200:
                decision_data = agent_response.json().get('rule_execution', {})
            else:
                logging.error(f"Strategies Agent retornou erro: {agent_response.status_code}")
                # Fallback seguro
                decision_data = {
                    "decision": "NEXT_STRATEGY", # Na dúvida, avança
                    "target_id": None,
                    "reasoning": "Agente indisponível. Avançando por segurança."
                }
        except Exception as e:
            logging.error(f"Erro ao chamar Strategies Agent: {e}")
            # Fallback seguro
            decision_data = {
                "decision": "NEXT_STRATEGY",
                "target_id": None,
                "reasoning": "Erro de conexão com Agente. Avançando."
            }

        decision = decision_data.get('decision')
        target_id = decision_data.get('target_id')
        reasoning = decision_data.get('reasoning', '')

        # 3. Execução da Ação (Actuation)
        action_taken = "Nenhuma ação automática."

        if decision == "REPEAT_TACTIC" and target_id:
            # Cenário A: Reuso -> Voltar para a tática específica
            # Precisamos achar o INDEX dessa tática na estratégia atual
            target_index = -1
            for i, tactic in enumerate(strategy_tactics):
                if tactic['id'] == target_id:
                    target_index = i
                    break

            if target_index >= 0:
                try:
                    requests.post(f"{CONTROL_URL}/sessions/tactic/set/{session_id}", json={"tactic_index": target_index}, timeout=5)
                    action_taken = f"Voltando para tática ID {target_id} (Index {target_index})"

                    # Definir flag para encerrar a sessão após essa tática
                    try:
                        requests.post(f"{CONTROL_URL}/sessions/{session_id}/set_end_flag", timeout=5)
                    except Exception as e:
                        logging.error(f"Erro ao setar flag de fim de sessão: {e}")

                except Exception as e:
                    logging.error(f"Erro ao setar tática no Control: {e}")
            else:
                logging.warning(f"Tática alvo ID {target_id} não encontrada na estratégia atual.")

        elif decision == "NEXT_STRATEGY":
            # Cenário B: Mudança -> Trocar estratégia
            if target_id:
                 try:
                    requests.post(f"{CONTROL_URL}/sessions/{session_id}/temp_switch_strategy", json={"strategy_id": target_id}, timeout=5)
                    action_taken = f"Trocando para estratégia ID {target_id}"
                    # NOTA: Não definimos 'set_end_flag' aqui.
                    # Requisito: Se mudar de estratégia, deve executar TODAS as táticas dela, não encerrar na primeira.

                 except Exception as e:
                    logging.error(f"Erro ao trocar estratégia no Control: {e}")
            else:
                 # Se não tiver ID alvo, provavelmente devemos manter o fluxo ou é fallback
                 pass

        return jsonify({
            "success": True,
            "decision": decision,
            "target_id": target_id,
            "reasoning": reasoning,
            "action_taken": action_taken
        })

    except Exception as e:
        logging.error(f"Erro crítico no execute_rules_logic: {e}")
        return jsonify({"error": "Internal Server Error"}), 500