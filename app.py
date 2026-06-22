# app.py
from flask import Flask, request, jsonify, session, render_template, url_for, redirect, send_file
import os
import requests
import logging
from modules.viabilidade import verificar_viabilidade, buscar_endereco, buscar_slots, buscar_complementos
from core.auth import get_token_for_cp
from clients import CLIENTS
from modules.os_instalacao import criar_ordem_instalacao
import pandas as pd
import io
from flask import request, send_file, jsonify, render_template
import http.client as http_client
import json
# Importa o novo módulo bolsao
from modules.bolsao import init_db, add_os_to_bolsao, get_all_os_from_bolsao, delete_expired_os, delete_all_os


# Configuração do Logger
logger = logging.getLogger(__name__)

# Ativa o debug no nível da conexão HTTP (mostra headers e raw data)
http_client.HTTPConnection.debuglevel = 1

# Garante que os logs do requests apareçam no terminal
requests_log = logging.getLogger("urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False

# Desabilitar InsecureRequestWarning para ambientes de teste/desenvolvimento
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

# Configuração de logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Definir URLs das APIs
os.environ['BASE_HOST'] = 'https://apitrg.vtal.com.br'
os.environ['TOKEN_URL'] = f"{os.environ.get('BASE_HOST')}/auth/oauth/v2/token"
os.environ['BASE_ADDRESS_URL'] = f"{os.environ.get('BASE_HOST')}/api/geographicAddressManagement/v1/geographicAddress"
os.environ['BASE_ADDRESS_COMPLEMENTS_URL'] = f"{os.environ.get('BASE_HOST')}/api/geographicAddressManagement/v1/addressComplements"
os.environ['BASE_AVAILABILITY_URL'] = f"{os.environ.get('BASE_HOST')}/api/resourcePoolManagement/v2/availabilityCheck"
os.environ['BASE_APPOINTMENT_URL'] = f"{os.environ.get('BASE_HOST')}/api/appointment/v2/searchTimeSlot"
os.environ['BASE_APPOINTMENT_URL_V2'] = f"{os.environ.get('BASE_HOST')}/api/appointment/v2/appointment"
os.environ['BASE_PRODUCT_ORDER_URL'] = f"{os.environ.get('BASE_HOST')}/api/productOrdering/v2/productOrder"

# Inicializa o banco de dados do bolsão ao iniciar a aplicação
with app.app_context():
    init_db()

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y %H:%M:%S'):
    if not value:
        return ""
    from datetime import datetime
    try:
        # Tenta parsear do formato ISO (que é como salvamos)
        dt_object = datetime.fromisoformat(value)
        return dt_object.strftime(format)
    except ValueError:
        return value # Retorna o valor original se não conseguir formatar

app.secret_key = os.urandom(24)

@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/viabilidade_individual', methods=['GET', 'POST'])
def viabilidade_individual():
    session.clear()
    return redirect(url_for('abertura_os_instalacao'))

@app.route('/abertura_os', methods=['GET'])
def abertura_os_instalacao():
    os_data = session.get('os_data', {
        'cep': '', 'fachada': '', 'cp_selection': '', 'companyId': '', 'complemento_manual_input': '',
        'addressId': None, 'address_description': '', 'inventoryId': None,
        'subscriberId': None, 'associatedDocument': None, 'produtos_viaveis': [],
        'status': '', 'message': '', 'complements_found': []
    })
    available_cps = list(CLIENTS.keys())
    return render_template('abertura_os.html', os_data=os_data, available_cps=available_cps)

@app.route('/api/buscar_endereco_e_complementos', methods=['POST'])
def api_buscar_endereco_e_complementos():
    try:
        data = request.get_json()
        cep = data.get('cep')
        fachada = data.get('fachada')
        cp_selection = data.get('cp_selection')
        complemento_viabilidade = data.get('complemento_viabilidade')

        if not all([cep, fachada, cp_selection]):
            return jsonify({"status": "erro", "message": "CEP, Fachada e CP são obrigatórios."}), 400

                # Busca o token
        token_data = get_token_for_cp(cp_selection, CLIENTS)

        # Extrai apenas a string de forma segura
        access_token = token_data.get('access_token') if isinstance(token_data, dict) else token_data

        if not access_token:
            return jsonify({'error': 'Falha ao extrair o token de autenticação'}), 500
        endereco_result = buscar_endereco(cep, fachada, access_token)

        if endereco_result['status'] == 'sucesso':
            address_id = endereco_result['data']['addressId']
            address_description = endereco_result['data']['address_description']

            # --- BUSCA DE COMPLEMENTOS ---
            complements_found = []
            app.logger.info(f"[APP] Buscando complementos para ID {address_id}")
            complementos_result = buscar_complementos(address_id, access_token)

            if complementos_result['status'] == 'sucesso':
                complements_found = complementos_result['data']
            # ---------------------------------------------------

            # Captura o companyId dinamicamente do dicionário CLIENTS
            company_id = CLIENTS.get(cp_selection, {}).get('companyId', '')

            session['os_data'] = {
                'cep': cep,
                'fachada': fachada,
                'cp_selection': cp_selection,
                'companyId': company_id,
                'addressId': address_id,
                'address_description': address_description,
                'complements_found': complements_found,
                'access_token': access_token,
                'complemento_manual': complemento_viabilidade,
                'inventoryId': None,
                'subscriberId': None,
                'associatedDocument': None,
                'produtos_viaveis': []
            }
            app.logger.info(f"[APP] Endereço encontrado: ID={address_id}. Complementos: {len(complements_found)}")
            return jsonify({"status": "sucesso", "message": "Endereço encontrado com sucesso.", "os_data": session['os_data']}), 200
        else:
            app.logger.error(f"[APP] Erro ao buscar endereço: {endereco_result['message']}")
            return jsonify(endereco_result), 400

    except Exception as e:
        app.logger.exception(f"[APP] Erro inesperado na busca de endereço: {e}")
        return jsonify({"status": "erro", "message": f"Erro interno: {e}"}), 500

@app.route('/verificar_viabilidade_com_complemento', methods=['POST'])
def verificar_viabilidade_com_complemento():
    try:
        data = request.get_json()
        complemento_selecionado = data.get('complemento_selecionado')

        os_data = session.get('os_data', {})
        address_id = os_data.get('addressId')
        cp_selecionado = os_data.get('cp_selection')
        address_description = os_data.get('address_description')
        access_token = os_data.get('access_token')

        if not address_id:
            return jsonify({"status": "erro", "message": "ID do endereço não encontrado na sessão."}), 400

        # --- AJUSTE AQUI: Gerar subscriberId e associatedDocument com o complemento ---
        # Certifique-se que complemento_selecionado é um dicionário ou string que pode ser convertida
        complemento_str_para_id = ""
        if complemento_selecionado:
            try:
                # Tenta carregar como JSON se for string, senão usa direto
                comp_obj = json.loads(complemento_selecionado) if isinstance(complemento_selecionado, str) else complemento_selecionado
                if isinstance(comp_obj, dict) and 'value' in comp_obj:
                    complemento_str_para_id = comp_obj['value']
                else:
                    complemento_str_para_id = str(complemento_selecionado)
            except (json.JSONDecodeError, TypeError):
                complemento_str_para_id = str(complemento_selecionado)

        # Limpa o complemento para usar no ID (remove espaços, caracteres especiais)
        cleaned_complemento = "".join(filter(str.isalnum, complemento_str_para_id)).upper()

        # Gera subscriberId e associatedDocument únicos
        # Se o complemento for vazio ou "NA", o sufixo será vazio.
        # Adicione um fallback para evitar IDs duplicados se o complemento for "NA" ou vazio.
        if not cleaned_complemento or cleaned_complemento == "NA":
            subscriber_id_base = f"SUB-{address_id}"
        else:
            subscriber_id_base = f"SUB-{address_id}-{cleaned_complemento}"

        subscriber_id = subscriber_id_base
        associated_document = subscriber_id_base
        # --- FIM DO AJUSTE ---

        viabilidade_result = verificar_viabilidade(
            address_id,
            cp_selecionado,
            complemento_selecionado, # Passa o complemento selecionado para a viabilidade
            access_token,
            address_description,
            subscriber_id # Passa o subscriber_id gerado com o complemento
        )

        if viabilidade_result['status'] == 'sucesso':
            viabilidade_data = viabilidade_result['data']
            session['os_data'].update({
                'inventoryId': viabilidade_data.get('inventoryId'),
                'subscriberId': subscriber_id, # Salva o subscriberId único na sessão
                'associatedDocument': associated_document, # Salva o associatedDocument único na sessão
                'produtos_viaveis': viabilidade_data['produtos_viaveis'],
                'status': 'viabilidade_ok',
                'message': viabilidade_result['message'],
                'complemento_selecionado_viabilidade': complemento_selecionado # Salva o complemento selecionado aqui
            })

            session.modified = True

            return jsonify({"status": "sucesso", "message": viabilidade_result['message'], "os_data": session['os_data']}), 200
        else:
            return jsonify({"status": "erro", "message": viabilidade_result.get('message', 'Erro na viabilidade')}), 400

    except Exception as e:
        app.logger.exception(f"[APP] Erro inesperado na viabilidade: {e}")
        return jsonify({"status": "erro", "message": f"Erro interno: {e}"}), 500

@app.route('/buscar_slots_os', methods=['POST'])
def buscar_slots_os_route():
    try:
        data = request.json

        # 1. Extrai os dados que vieram do frontend
        product_id = data.get('product_id')
        product_type = data.get('product_type', 'Banda Larga')
        product_name = data.get('product_name', 'Banda Larga')
        data_inicio = data.get('data_inicio')
        data_fim = data.get('data_fim')

        if not all([product_id, product_type, data_inicio, data_fim]):
            return jsonify({"status": "erro", "message": "Produto e datas são obrigatórios para buscar slots."}), 400

        # 2. Resgata os dados vitais que foram salvos na viabilidade
        os_data = session.get('os_data', {})
        address_id = os_data.get('addressId')
        inventory_id = os_data.get('inventoryId')
        subscriber_id = os_data.get('subscriberId') # <-- Agora virá da sessão, já com o complemento
        associated_document = os_data.get('associatedDocument') # <-- Agora virá da sessão, já com o complemento
        cp_selection = os_data.get('cp_selection')
        company_id = os_data.get('companyId')
        access_token = os_data.get('access_token')
        complemento_selecionado_viabilidade = os_data.get('complemento_selecionado_viabilidade') # <-- PEGA O COMPLEMENTO AQUI

        if not all([address_id, inventory_id, cp_selection, access_token, subscriber_id, associated_document]):
            return jsonify({"status": "erro", "message": "Dados de viabilidade ausentes na sessão. Refaça a viabilidade."}), 400

        # 3. Salva TUDO na raiz da sessão para a rota de confirmação achar fácil
        session['address_id'] = address_id
        session['inventory_id'] = inventory_id
        session['subscriber_id'] = subscriber_id # Salva o subscriberId único
        session['product_id'] = product_id
        session['product_type'] = product_type
        session['product_name'] = product_name
        session['associated_document'] = associated_document # Salva o associatedDocument único
        session['access_token'] = access_token # Garante que o token estará acessível
        session['complemento_selecionado_viabilidade'] = complemento_selecionado_viabilidade # <-- SALVA O COMPLEMENTO AQUI
        session.modified = True

        # 4. Busca os slots na V.tal
        slots_result = buscar_slots(
            address_id=address_id,
            inventory_id=inventory_id,
            cp_selection=cp_selection,
            company_id=company_id,
            product_id=product_id,
            product_type=product_type,
            data_inicio=data_inicio,
            data_fim=data_fim,
            access_token=access_token,
            subscriber_id=subscriber_id
        )

        if slots_result and slots_result.get('status') == 'sucesso':
            session['os_data']['slots_disponiveis'] = slots_result['data']
            session.modified = True
            return jsonify({"status": "sucesso", "message": slots_result['message'], "slots": slots_result['data']}), 200
        else:
            erro_msg = slots_result.get('message', 'Erro ao buscar slots') if slots_result else 'Erro desconhecido'
            return jsonify({"status": "erro", "message": erro_msg}), 400

    except Exception as e:
        app.logger.exception(f"[APP] Erro inesperado ao buscar slots: {e}")
        return jsonify({"status": "erro", "message": f"Erro interno: {e}"}), 500

@app.route('/abertura_os_confirmar', methods=['POST'])
def abertura_os_confirmar():
    data = request.json
    selected_slot = data.get('selected_slot')
    # O campo 'complemento_manual' do frontend será ignorado, usaremos o da sessão
    # complemento_manual_frontend = data.get('complemento_manual')

    # Resgata os dados da sessão
    address_id = session.get('address_id')
    inventory_id = session.get('inventory_id')
    subscriber_id = session.get('subscriber_id')
    associated_document = session.get('associated_document')
    product_id = session.get('product_id')
    product_name = session.get('product_name', 'Banda Larga')
    product_type = session.get('product_type', 'Banda Larga')
    access_token = session.get('access_token')
    complemento_selecionado_viabilidade = session.get('complemento_selecionado_viabilidade') # <-- PEGA O COMPLEMENTO AQUI
    cep = session.get('os_data', {}).get('cep')
    fachada = session.get('os_data', {}).get('fachada')
    cp_selection = session.get('os_data', {}).get('cp_selection')


    app.logger.info(f"[DEBUG CONFIRMAÇÃO] Address: {address_id} | Inv: {inventory_id} | Sub: {subscriber_id} | Slot: {selected_slot} | Complemento: {complemento_selecionado_viabilidade}")

    # Validação dos dados essenciais
    if not all([address_id, inventory_id, subscriber_id, associated_document, product_id, selected_slot, access_token]):
        app.logger.error("[APP] Dados essenciais ausentes na sessão ou no request para confirmação da OS.")
        return jsonify({"status": "erro", "message": "Dados essenciais da sessão incompletos para confirmar a OS."}), 400

    # Chama a função de criação de OS
    from modules.os_instalacao import criar_ordem_instalacao

    resultado = criar_ordem_instalacao(
        address_id=address_id,
        inventory_id=inventory_id,
        subscriber_id=subscriber_id,
        associated_document=associated_document,
        access_token=access_token,
        selected_slot=selected_slot,
        product_id=product_id,
        product_name=product_name,
        product_type=product_type,
        complemento_manual=complemento_selecionado_viabilidade # <-- PASSA O COMPLEMENTO DA SESSÃO
    )

    # Se a OS foi criada com sucesso, adiciona ao bolsão
    if resultado.get('status') == 'sucesso':
        order_data = resultado.get('data', {})
        add_os_to_bolsao(
            order_id=order_data.get('order_id', 'N/A'),
            appointment_id=order_data.get('appointment_id', 'N/A'),
            associated_document=order_data.get('associated_document', 'N/A'),
            cp_selection=cp_selection,
            cep=cep,
            fachada=fachada,
            complemento=complemento_selecionado_viabilidade,
            product_name=product_name
        )

    return jsonify(resultado)

# ==========================================
# ROTAS DE VIABILIDADE EM LOTE
# ==========================================

@app.route('/viabilidade_lote')
def viabilidade_lote_page():
    # Pega as CPs dinamicamente do arquivo clients.py
    available_cps = list(CLIENTS.keys())
    return render_template('viabilidade_lote.html', available_cps=available_cps)

@app.route('/api/viabilidade_lote', methods=['POST'])
def processar_viabilidade_lote():
    from flask import request as flask_request, jsonify as flask_jsonify, send_file as flask_send_file
    import pandas as pd
    import io
    import json
    from datetime import datetime, timedelta
    from modules.viabilidade import buscar_endereco, verificar_viabilidade
    from modules.os_instalacao import buscar_slots
    from core.auth import get_token_for_cp

    try:
        if 'file' not in flask_request.files:
            return flask_jsonify({'error': 'Nenhum arquivo enviado'}), 400

        file = flask_request.files['file']
        if file.filename == '':
            return flask_jsonify({'error': 'Nenhum arquivo selecionado'}), 400

        cp_selection = flask_request.form.get('cp_selection')

        if file.filename.endswith('.csv'):
            df = pd.read_csv(file, sep=';', dtype=str)
        else:
            df = pd.read_excel(file, dtype=str)

        if 'Viabilidade' not in df.columns:
            df['Viabilidade'] = ""
        if 'Slot' not in df.columns:
            df['Slot'] = ""

        # Pega o token bruto
        token_raw = get_token_for_cp(cp_selection, CLIENTS)

        # Garante que vamos usar apenas a string do token, e não o dicionário inteiro
        if isinstance(token_raw, dict):
            token = token_raw.get('access_token', '')
        else:
            token = token_raw

        for index, row in df.iterrows():
            cep = str(row.get('CEP', '')).strip().replace('-', '')
            numero = str(row.get('Nº fachada', '')).strip()
            complemento = str(row.get('Complemento 1', '')).strip()

            if not cep or not numero or cep == 'nan' or numero == 'nan':
                df.at[index, 'Viabilidade'] = "CEP ou Número ausentes"
                continue

            endereco_data = buscar_endereco(cep, numero, token)
            if endereco_data.get('status') != 'sucesso':
                df.at[index, 'Viabilidade'] = "Endereço não encontrado"
                continue

            dados_endereco = endereco_data.get('data', {})
            address_id = dados_endereco.get('addressId')
            address_description = dados_endereco.get('address_description', '')

            if not address_id:
                df.at[index, 'Viabilidade'] = "ID do endereço não retornado"
                continue

            subscriber_id = f"SUB-LOTE-{index}"

            # Chama a viabilidade
            viabilidade_result = verificar_viabilidade(
                address_id=address_id,
                cp_selecionado=cp_selection,
                complemento_selecionado=complemento if complemento and complemento != '"' and complemento != 'nan' else None,
                access_token=token,
                address_description=address_description,
                subscriber_id=subscriber_id

            )

            if viabilidade_result.get('status') == 'sucesso':
                df.at[index, 'Viabilidade'] = "Viável"

                viabilidade_data = viabilidade_result.get('data', {})

                # AJUSTE 1: Extração correta do inventoryId (buscando dentro de 'resource' como a V.tal manda)
                inventory_id = viabilidade_data.get('resource', {}).get('inventoryId')
                if not inventory_id:
                    inventory_id = viabilidade_data.get('inventoryId')

                # Se mesmo assim não achar, avisa na planilha e pula para a próxima linha
                if not inventory_id:
                    df.at[index, 'Slot'] = "Erro: inventoryId não encontrado"
                    continue

                # AJUSTE 2: Indentação corrigida (estava presa dentro de um if falso)
                # Datas com limite de 7 dias para evitar o Erro 400 da V.tal
                amanha = datetime.now() + timedelta(days=1)
                data_inicio = amanha.strftime('%Y-%m-%dT00:00:00')
                data_fim = (amanha + timedelta(days=14)).strftime('%Y-%m-%dT23:59:59')

                import requests
                slots_url = "https://apitrg.vtal.com.br/api/appointment/v2/searchTimeSlot"
                slots_params = {
                        'addressId': address_id,
                        'inventoryId': inventory_id,
                        'subscriberId': subscriber_id,
                        'associatedDocument': subscriber_id,
                        'startDate': data_inicio,
                        'finishDate': data_fim,
                        'orderType': 'Instalacao',
                        'changeAddressFlag': 'false',
                        'productType': 'Banda Larga'
                    }
                slots_headers = {
                        'Authorization': f"Bearer {token}",
                        'Content-Type': 'application/json'
                    }

                try:
                        slots_req = requests.get(slots_url, params=slots_params, headers=slots_headers)
                        if slots_req.status_code == 200:
                            slots_data = slots_req.json()
                            slots_list = slots_data.get('slots', [])

                            if slots_list and len(slots_list) > 0:
                                slots_formatados = []
                                # Pega os 3 primeiros slots e formata igualzinho à sua UI
                                for s in slots_list[:3]:
                                    dt_in = s.get('startDate', '')
                                    dt_out = s.get('finishDate', '')
                                    if len(dt_in) >= 16 and len(dt_out) >= 16:
                                        dia, mes, ano = dt_in[8:10], dt_in[5:7], dt_in[0:4]
                                        h_in, h_out = dt_in[11:16], dt_out[11:16]
                                        slots_formatados.append(f"{dia}/{mes}/{ano} {h_in} às {h_out}")

                                df.at[index, 'Slot'] = " | ".join(slots_formatados)
                            else:
                                df.at[index, 'Slot'] = "Sem slots disponíveis"
                        else:
                            df.at[index, 'Slot'] = f"Erro API: {slots_req.status_code}"
                except Exception as e:
                        df.at[index, 'Slot'] = f"Erro requisição: {e}"
                    # --- FIM DA BUSCA DE SLOTS DIRETA ---

            else:
                df.at[index, 'Viabilidade'] = "Inviável"
                df.at[index, 'Slot'] = "-"

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Resultados')
        output.seek(0)

        return flask_send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='Resultado_Viabilidade_Lote.xlsx'
        )

    except Exception as e:
        print(f"Erro crítico no processamento do lote: {e}")
        return flask_jsonify({'error': str(e)}), 500

# ==========================================
# ROTAS DO BOLSÃO DE OS
# ==========================================
@app.route('/bolsao_os')
def bolsao_os_page():
    ordens = get_all_os_from_bolsao()
    return render_template('bolsao_os.html', ordens=ordens)

@app.route('/bolsao_os/limpar_expiradas', methods=['POST'])
def bolsao_os_limpar_expiradas():
    deleted_count = delete_expired_os()
    return jsonify({"status": "sucesso", "message": f"{deleted_count} ordens de serviço expiradas foram removidas."})

@app.route('/bolsao_os/limpar_tudo', methods=['POST'])
def bolsao_os_limpar_tudo():
    deleted_count = delete_all_os()
    return jsonify({"status": "sucesso", "message": f"{deleted_count} ordens de serviço foram removidas."})


if __name__ == '__main__':
    app.run(debug=True)