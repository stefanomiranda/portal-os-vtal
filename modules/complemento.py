# Funções auxiliares de complementos (usado na viabilidade)
def processar_complementos(response_viabilidade):
    return response_viabilidade.get('resource', {}).get('products', {})