import requests
import os
import logging
import json
import urllib.parse

from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def buscar_endereco(cep, fachada, access_token):
    address_search_url = os.environ.get('BASE_ADDRESS_URL')

    if not address_search_url:
        return {"status": "erro", "message": "Configuração de URL ausente."}

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Algumas versões da API usam postcode/streetNr, outras address/number. 
    # Vamos enviar os dois pares para garantir que a API entenda a busca.
    params = {
        'address': cep, 
        'number': fachada,
        'postcode': cep,
        'streetNr': fachada
    }

    try:
        response = requests.get(address_search_url, headers=headers, params=params, verify=False)
        response.raise_for_status()
        result = response.json()

        # LOG IMPORTANTE: Vai imprimir no terminal exatamente o que a V.tal respondeu
        logger.info(f"[VIABILIDADE] Resposta da API para CEP {cep}, Num {fachada}: {result}")

        address_id = None
        address_description = None

        # Cenário 1: A API retornou uma lista (Padrão TMF673 moderno)
        if isinstance(result, list):
            if len(result) > 0:
                address_info = result[0]
                address_id = address_info.get('id')
                address_description = address_info.get('name') or address_info.get('streetName')

        # Cenário 2: A API retornou um dicionário
        elif isinstance(result, dict):
            # Formato legado (o que estava no seu código original)
            if result.get('control', {}).get('type') == 'S' and result.get('addresses', {}).get('address'):
                address_info = result['addresses']['address'][0]
                address_id = address_info.get('id')
                address_description = address_info.get('description')
            # Formato paginado
            elif 'items' in result and len(result['items']) > 0:
                address_info = result['items'][0]
                address_id = address_info.get('id')
                address_description = address_info.get('name') or address_info.get('description')
            # Retorno direto de um único objeto
            elif 'id' in result:
                address_id = result.get('id')
                address_description = result.get('name') or result.get('description')

        if address_id:
            return {
                "status": "sucesso",
                "data": {
                    "addressId": address_id,
                    "address_description": address_description or f"CEP {cep}, Num {fachada}"
                }
            }
        else:
            return {"status": "erro", "message": "Endereço não encontrado na base da V.tal."}

    except Exception as e:
        logger.exception(f"[VIABILIDADE] Erro inesperado: {e}")
        return {"status": "erro", "message": f"Erro inesperado: {e}"}

def buscar_complementos(address_id, access_token):
    """
    Busca os complementos de um endereço específico na V.tal.
    """
    url = f"{os.environ.get('BASE_ADDRESS_COMPLEMENTS_URL')}/{address_id}"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    logger.info(f"[VIABILIDADE] Buscando complementos para addressId {address_id}")

    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        result = response.json()

        complements_list = []
        if result.get('control', {}).get('type') == 'S' and result.get('complementList'):
            for comp_item in result['complementList']:
                if comp_item.get('complement') and comp_item['complement'].get('complements'):
                    for comp_detail in comp_item['complement']['complements']:
                        complements_list.append({
                            "type": comp_detail.get('type'),
                            "value": comp_detail.get('value'),
                            "description": comp_detail.get('description', comp_detail.get('type'))
                        })

        logger.info(f"[VIABILIDADE] {len(complements_list)} complementos encontrados.")
        return {"status": "sucesso", "data": complements_list}

    except Exception as e:
        logger.error(f"[VIABILIDADE] Erro ao buscar complementos: {e}")
        return {"status": "erro", "message": str(e), "data": []}

def verificar_viabilidade(address_id, cp_selecionado, complemento_selecionado, access_token, address_description, subscriber_id):
    url = os.environ.get('BASE_AVAILABILITY_URL')
    if not url:
        logger.error("URL para viabilidade não configurada (BASE_AVAILABILITY_URL).")
        return {"status": "erro", "message": "Configuração de URL ausente."}

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    payload = {
        "customer": {
            "subscriberId": subscriber_id # <-- Agora enviamos o valor correto no payload!
        },
        "address": {
            "id": address_id
        }
    }

    if complemento_selecionado:
        try:
            comp_obj = json.loads(complemento_selecionado) if isinstance(complemento_selecionado, str) else complemento_selecionado
            payload['address']['complement'] = {
                "complements": [
                    {
                        "type": comp_obj.get('type', 'SL'),
                        "value": comp_obj.get('value')
                    }
                ]
            }
        except Exception as e:
            logger.warning(f"[VIABILIDADE] Erro ao processar complemento selecionado: {e}")

    try:
        logger.info(f"[VIABILIDADE] Chamando viabilidade: {url}")
        logger.debug(f"[VIABILIDADE] Payload enviado: {json.dumps(payload)}")
        response = requests.post(url, headers=headers, json=payload, verify=False)

        if not response.ok:
            erro_vtal = f"Erro HTTP {response.status_code}"
            try:
                err_json = response.json()
                if 'control' in err_json and 'message' in err_json['control']:
                    erro_vtal = err_json['control']['message']
            except:
                pass
            logger.error(f"[VIABILIDADE] Erro na API V.tal: {erro_vtal} - Detalhe: {response.text}")
            return {"status": "erro", "message": erro_vtal, "detalhe": response.text}

        result = response.json()
        logger.debug(f"[VIABILIDADE] Resposta da viabilidade: {json.dumps(result)}")

        if result.get('control', {}).get('type') == 'S':
            # Extrair APENAS o inventoryId (V.tal não devolve customer na resposta)
            inventory_id = result.get('resource', {}).get('inventoryId')

            produtos_api = result.get('resource', {}).get('products', {}).get('product', [])
            produtos_viaveis = []
            for p in produtos_api:
                produtos_viaveis.append({
                    "id": p.get('catalogId'),
                    "name": p.get('name'),
                    "productType": p.get('type')
                })

            return {
                "status": "sucesso",
                "message": "Viabilidade verificada com sucesso.",
                "data": {
                    "addressId": address_id,
                    "address_description": address_description,
                    "inventoryId": inventory_id,
                    "produtos_viaveis": produtos_viaveis
                    # Removemos subscriberId e associatedDocument daqui
                }
            }
        else:
            error_message = result.get('control', {}).get('message', 'Erro desconhecido na viabilidade.')
            return {"status": "erro", "message": error_message}

    except Exception as e:
        logger.exception(f"[VIABILIDADE] Erro inesperado ao verificar viabilidade: {e}")
        return {"status": "erro", "message": f"Erro inesperado: {e}"}

# CORREÇÃO: Adicionado valores padrão (None) para evitar quebra caso o app.py não envie
def buscar_slots(address_id, inventory_id, cp_selection, company_id, product_id, product_type, data_inicio, data_fim, access_token, subscriber_id=None, **kwargs):
    url = os.environ.get('BASE_APPOINTMENT_URL')

    # --- TRATAMENTO DE DATA INTELIGENTE ---
    def formatar_data(data_texto, is_fim=False):
        if not data_texto: return ""
        data_limpa = data_texto.split('T')[0].strip()

        try:
            if "/" in data_limpa:
                dt = datetime.strptime(data_limpa, "%d/%m/%Y")
            else:
                dt = datetime.strptime(data_limpa, "%Y-%m-%d")

            hoje = datetime.now()

            if is_fim:
                hora = "23:59:59"
            else:
                if dt.date() == hoje.date():
                    # Adiciona 10 min de margem e ZERA os segundos (exigência da API)
                    hora_futura = hoje + timedelta(minutes=10)
                    hora = hora_futura.strftime("%H:%M:00")
                else:
                    hora = "08:00:00"

            return f"{dt.strftime('%Y-%m-%d')}T{hora}"
        except Exception as e:
            logger.error(f"[AGENDAMENTO] Erro ao formatar data '{data_texto}': {e}")
            return data_texto
    # --------------------------------------------

    start_date = formatar_data(data_inicio, is_fim=False)
    finish_date = formatar_data(data_fim, is_fim=True)

    # Dicionário construído EXATAMENTE conforme a documentação oficial
    params = {
        "addressId": address_id,
        "startDate": start_date,
        "finishDate": finish_date,
        "orderType": "Instalacao",
        "productType": product_type,
        "addressChangeFlag": "false",
        "priorityFlag": "false"
    }

    # Usa o valor sequencial da sua massa de teste
    if subscriber_id:
        params["subscriberId"] = subscriber_id
        params["associatedDocument"] = subscriber_id
    else:
        params["associatedDocument"] = inventory_id

    # Codificação da URL (Protegendo os dois pontos da hora)
    query_string = urllib.parse.urlencode(params, safe=':', quote_via=urllib.parse.quote)
    url_final = f"{url}?{query_string}"

    # Headers limpos com Accept explícito
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }

    logger.info(f"[AGENDAMENTO] Buscando slots (GET): {url_final}")

    try:
        response = requests.get(url_final, headers=headers, verify=False)

        if response.status_code != 200:
            erro_vtal = response.text
            logger.error(f"[AGENDAMENTO] V.tal recusou a busca: {erro_vtal}")
            return {"status": "erro", "message": f"Erro da V.tal: {erro_vtal}"}

        data = response.json()
        slots = data.get('slots', data.get('timeSlots', [])) 

        return {"status": "sucesso", "message": "Slots encontrados", "data": slots}

    except Exception as e:
        logger.error(f"[AGENDAMENTO] Erro ao buscar slots: {e}")
        return {"status": "erro", "message": str(e)}