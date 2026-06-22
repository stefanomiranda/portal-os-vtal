# modules/os_instalacao.py
import requests
import os
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def buscar_slots(address_id, inventory_id, cp_selection, product_id, product_type, data_inicio, data_fim, access_token, subscriber_id=None, **kwargs):
    base_url = os.environ.get('BASE_URL', 'https://apitrg.vtal.com.br')
    url = f"{base_url}/api/appointment/v2/searchTimeSlot"

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    start_date = f"{data_inicio}T00:00:00Z" if len(data_inicio) == 10 else data_inicio
    finish_date = f"{data_fim}T23:59:59Z" if len(data_fim) == 10 else data_fim

    params = {
        "addressId": address_id,
        "inventoryId": inventory_id,
        "subscriberId": subscriber_id,
        "associatedDocument": subscriber_id,
        "startDate": start_date,
        "finishDate": finish_date,
        "orderType": "Instalacao",
        "changeAddressFlag": "false",
        "productType": product_type
    }

    logger.info(f"[AGENDAMENTO] Buscando slots (GET): {url} | Params: {params}")

    try:
        response = requests.get(url, headers=headers, params=params, verify=False)
        response.raise_for_status()

        data = response.json()
        slots = data.get('timeSlots', data.get('availableTimeSlots', [])) 

        return {"status": "sucesso", "message": "Slots encontrados", "data": slots}

    except Exception as e:
        logger.error(f"[AGENDAMENTO] Erro ao buscar slots: {e}")
        return {"status": "erro", "message": str(e)}


def criar_ordem_instalacao(address_id, inventory_id, subscriber_id, associated_document, access_token, selected_slot, product_id, product_name, product_type, complemento_manual=None):
    base_appointment_url = os.environ.get('BASE_APPOINTMENT_URL_V2')
    base_product_order_url = os.environ.get('BASE_PRODUCT_ORDER_URL')

    if not base_appointment_url or not base_product_order_url:
        logger.error("URLs para Appointment ou Product Order não configuradas.")
        return {"status": "erro", "message": "Erro de configuração de URL."}

    # Headers limpos e padronizados, incluindo Accept para o Appointment
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json' # Adicionado para resolver o 406 no Appointment
    }

    try:
        # ==========================================
        # 1. CRIAR APPOINTMENT (Padrão V.tal v2 Simplificado)
        # ==========================================
        import ast

        req_start_tmf = ""
        slot_id = None

        # Extrai os dados do slot selecionado
        if isinstance(selected_slot, dict):
            req_start_tmf = selected_slot.get('startDate')
            slot_id = selected_slot.get('id')
        else:
            try:
                # Tenta converter string para dicionário
                slot_dict = ast.literal_eval(str(selected_slot))
                req_start_tmf = slot_dict.get('startDate')
                slot_id = slot_dict.get('id')
            except Exception as e:
                logger.error(f"[OS_INSTALACAO] Erro ao fazer parse do slot: {e}")
                return {"status": "erro", "message": "Erro ao processar slot selecionado."}

        # Variável para usar na Product Order depois (sem o Z)
        appointment_date_str_for_product_order = req_start_tmf.replace(".000Z", "") if ".000Z" in req_start_tmf else req_start_tmf

        # PAYLOAD EXATO CONFORME O EXEMPLO DE SUCESSO
        appointment_payload = {
            "appointment": {
                "slot": {
                    "id": str(slot_id)
                },
                "reason": "Agendamento para Instalacao"
            }
        }

        logger.info(f"[OS_INSTALACAO] Chamando POST Appointment: {base_appointment_url}")
        logger.debug(f"[OS_INSTALACAO] Payload Appointment: {json.dumps(appointment_payload)}")

        app_response = requests.post(base_appointment_url, headers=headers, json=appointment_payload, verify=False)

        app_response.raise_for_status() # Isso vai levantar um erro para 4xx/5xx
        app_result = app_response.json()

        # Captura o ID gerado
        appointment_id = app_result.get('id') or app_result.get('appointment', {}).get('id')

        if not appointment_id:
            logger.error(f"[OS_INSTALACAO] Appointment ID não retornado. Resposta: {app_response.text}")
            return {"status": "erro", "message": "Appointment ID não retornado."}

        logger.info(f"[OS_INSTALACAO] Appointment criado com sucesso. ID: {appointment_id}")

        # ==========================================
        # 2. CRIAR PRODUCT ORDER (Formato Proprietário V.tal)
        # ==========================================

        # Formatação de datas exigidas pelo novo payload
        current_date_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
        # A data do appointment para o payload da Product Order deve ser sem o fuso horário 'Z'
        appointment_date_str = appointment_date_str_for_product_order.replace("Z", "")

        # Garantir que os IDs sejam inteiros conforme o modelo fornecido
        try:
            addr_id_int = int(address_id)
            inv_id_int = int(inventory_id)
        except ValueError:
            addr_id_int = address_id
            inv_id_int = inventory_id

        # Prepara o objeto de complemento
        complement_obj_list = []
        complemento_ref_str = "Sem complemento" # Valor padrão para o campo 'reference'

        if complemento_manual:
            try:
                # O complemento_manual pode vir como string JSON ou como dict
                comp_data = json.loads(complemento_manual) if isinstance(complemento_manual, str) else complemento_manual
                if isinstance(comp_data, dict) and 'type' in comp_data and 'value' in comp_data:
                    complement_obj_list.append({
                        "type": comp_data['type'],
                        "value": comp_data['value']
                    })
                    complemento_ref_str = comp_data['value'] # Usa o valor do complemento para a referência
                else:
                    # Se não for um dict com type/value, trata como um valor simples
                    complement_obj_list.append({
                        "type": "SL", # Tipo padrão para complemento simples
                        "value": str(complemento_manual)
                    })
                    complemento_ref_str = str(complemento_manual)
            except json.JSONDecodeError:
                # Se não for JSON válido, trata como um valor simples
                complement_obj_list.append({
                    "type": "SL",
                    "value": str(complemento_manual)
                })
                complemento_ref_str = str(complemento_manual)
            except Exception as e:
                logger.warning(f"[OS_INSTALACAO] Erro ao processar complemento_manual para Product Order: {e}. Usando valor bruto.")
                complement_obj_list.append({
                    "type": "SL",
                    "value": str(complemento_manual)
                })
                complemento_ref_str = str(complemento_manual)

        # Se não houver complemento, ou se o processamento falhar, adiciona um complemento padrão
        if not complement_obj_list:
             complement_obj_list.append({
                "type": "SL",
                "value": "NA"
            })
             complemento_ref_str = "NA" # Atualiza a referência para "NA" se não houver complemento


        product_order_payload = {
            "order": {
                "correlationOrder": 1,
                "associatedDocument": str(associated_document),
                "associatedDocumentDate": current_date_str,
                "type": "Instalacao",
                "infraType": "FTTH",
                "customer": {
                    "name": "Cliente V.tal",
                    "subscriberId": str(subscriber_id),
                    "businessUnity": "varejo",
                    "fantasyName": "Cliente V.tal",
                    "phoneNumber": {
                        "phoneNumbers": ["000000000", "", ""]
                    },
                    "workContact": {
                        "name": "Contato Vtal",
                        "email": "contato@vtal.com",
                        "phone": "00000000000"
                    }
                },
                "appointment": {
                    "hasSlot": True,
                    "date": appointment_date_str,
                    "mandatoryType": "Obrigatorio",
                    "workOrderId": str(appointment_id)
                },
                "addresses": {
                    "address": {
                        "id": addr_id_int,
                        "inventoryId": inv_id_int,
                        "reference": complemento_ref_str, # Usa a string de referência processada
                        "complement": {
                            "complements": complement_obj_list # Usa a lista de objetos de complemento processada
                        }
                    }
                },
                "products": {
                    "product": [
                        {
                            "catalogId": str(product_id),
                            "action": "adicionar"
                        }
                    ]
                }
            }
        }

        logger.info(f"[OS_INSTALACAO] Chamando POST Product Order: {base_product_order_url}")
        logger.debug(f"[OS_INSTALACAO] Payload Product Order: {json.dumps(product_order_payload)}")

        # Envio limpo, usando o json= nativo do requests
        product_order_response = requests.post(base_product_order_url, headers=headers, json=product_order_payload, verify=False)
        product_order_response.raise_for_status()

        # Como o payload mudou, a resposta também pode ter mudado.
        # Vamos tentar pegar o ID de forma segura.
        product_order_result = product_order_response.json()
        order_id = product_order_result.get('id') or product_order_result.get('orderId') or "Gerado com Sucesso"

        logger.info(f"[OS_INSTALACAO] Product Order criada com sucesso. ID: {order_id}")

        # Montamos uma mensagem amigável e completa para o frontend
        mensagem_sucesso = (
            f"Ordem de Instalação solicitada com sucesso!\n\n"
            f"📄 Documento Associado: {associated_document}\n"
            f"📅 Agendamento: {appointment_id}"
        )

        return {
            "status": "sucesso",
            "message": mensagem_sucesso,
            "data": {
                "order_id": order_id,
                "appointment_id": appointment_id,
                "associated_document": associated_document
            }
        }

    except requests.exceptions.HTTPError as e:
        logger.error(f"[OS_INSTALACAO] Erro HTTP Product Order: {e.response.status_code} - {e.response.text}")
        return {"status": "erro", "message": f"Erro {e.response.status_code} na API", "detalhe": e.response.text}
    except Exception as e:
        logger.error(f"[OS_INSTALACAO] Erro interno: {str(e)}")
        return {"status": "erro", "message": str(e)}