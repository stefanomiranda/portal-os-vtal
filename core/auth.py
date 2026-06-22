# core/auth.py
import requests
import os
import logging

app_logger = logging.getLogger(__name__)

def get_token_for_cp(cp_id: str, clients_config: dict) -> dict | None:
    """
    Obtém um token de acesso para um Client Partner (CP) específico.

    Args:
        cp_id (str): O ID do Client Partner.
        clients_config (dict): Dicionário contendo as configurações de todos os CPs.

    Returns:
        dict | None: Um dicionário com as informações do token (access_token, token_type, expires_in)
                     ou None em caso de falha.
    """
    cp_info = clients_config.get(cp_id)
    if not cp_info:
        app_logger.error(f"[AUTH] Configurações não encontradas para o CP: {cp_id}")
        return None

    client_id = cp_info.get("client_id")
    client_secret = cp_info.get("client_secret")

    if not client_id or not client_secret:
        app_logger.error(f"[AUTH] client_id ou client_secret ausentes para o CP: {cp_id}")
        return None

    token_url = os.environ.get('TOKEN_URL')
    if not token_url:
        app_logger.error("[AUTH] Variável de ambiente TOKEN_URL não configurada.")
        return None

    # Parâmetros de query conforme o Postman
    params = {
        'grant_type': 'client_credentials',
        'scope': 'fttx'
    }

    app_logger.info(f"[AUTH] Tentando obter token para CP: {cp_id}")
    try:
        # Usando auth=(client_id, client_secret) para Basic Auth
        # e params para os query parameters
        response = requests.post(
            token_url,
            auth=(client_id, client_secret),
            params=params, # <--- Adicionado aqui
            verify=False # Usar False apenas em ambientes de desenvolvimento/teste
        )
        response.raise_for_status() # Levanta um HTTPError para respostas de erro (4xx ou 5xx)

        token_info = response.json()
        app_logger.info(f"[AUTH] Token obtido com sucesso para CP: {cp_id}")
        return token_info

    except requests.exceptions.HTTPError as http_err:
        app_logger.error(f"[AUTH] Erro na requisição de token para CP {cp_id}: {http_err}")
        app_logger.error(f"[AUTH] Resposta de erro: {response.text}") # Logar a resposta de erro completa
        return None
    except requests.exceptions.ConnectionError as conn_err:
        app_logger.error(f"[AUTH] Erro de conexão ao tentar obter token para CP {cp_id}: {conn_err}")
        return None
    except requests.exceptions.Timeout as timeout_err:
        app_logger.error(f"[AUTH] Timeout ao tentar obter token para CP {cp_id}: {timeout_err}")
        return None
    except requests.exceptions.RequestException as req_err:
        app_logger.error(f"[AUTH] Erro inesperado na requisição de token para CP {cp_id}: {req_err}")
        return None
    except Exception as e:
        app_logger.error(f"[AUTH] Erro genérico ao obter token para CP {cp_id}: {e}")
        return None
