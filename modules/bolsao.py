# modules/bolsao.py
import sqlite3
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

DATABASE_FILE = '/mnt/data/bolsao_os.db'

def init_db():
    """Inicializa o banco de dados e cria a tabela se ela não existir."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            appointment_id TEXT NOT NULL,
            associated_document TEXT NOT NULL,
            cp_selection TEXT,
            cep TEXT,
            fachada TEXT,
            complemento TEXT,
            product_name TEXT,
            data_criacao TEXT NOT NULL,
            data_expiracao TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    logger.info(f"Banco de dados '{DATABASE_FILE}' inicializado e tabela 'ordens_servico' verificada.")

def add_os_to_bolsao(order_id, appointment_id, associated_document, cp_selection, cep, fachada, complemento, product_name):
    """Adiciona uma ordem de serviço ao bolsão."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    data_criacao = datetime.now()
    data_expiracao = data_criacao + timedelta(days=7)

    cursor.execute('''
        INSERT INTO ordens_servico (order_id, appointment_id, associated_document, cp_selection, cep, fachada, complemento, product_name, data_criacao, data_expiracao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        order_id,
        appointment_id,
        associated_document,
        cp_selection,
        cep,
        fachada,
        complemento,
        product_name,
        data_criacao.isoformat(),
        data_expiracao.isoformat()
    ))
    conn.commit()
    conn.close()
    logger.info(f"OS '{order_id}' adicionada ao bolsão.")

def get_all_os_from_bolsao():
    """Retorna todas as ordens de serviço do bolsão, ordenadas pela data de criação."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ordens_servico ORDER BY data_criacao DESC')
    rows = cursor.fetchall()
    conn.close()

    # Converte as linhas para uma lista de dicionários para facilitar o uso no template
    columns = [description[0] for description in cursor.description]
    ordens = []
    for row in rows:
        ordens.append(dict(zip(columns, row)))
    logger.debug(f"Recuperadas {len(ordens)} OSs do bolsão.")
    return ordens

def delete_expired_os():
    """Remove ordens de serviço expiradas do bolsão."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('DELETE FROM ordens_servico WHERE data_expiracao < ?', (now,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted_count > 0:
        logger.info(f"{deleted_count} ordens de serviço expiradas foram removidas do bolsão.")
    return deleted_count

def delete_all_os():
    """Remove todas as ordens de serviço do bolsão."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM ordens_servico')
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    logger.info(f"{deleted_count} ordens de serviço foram removidas do bolsão (limpeza total).")
    return deleted_count

# Garante que o banco de dados seja inicializado quando o módulo é importado
init_db()
