# config.py
"""
Arquivo de configuração para o Liferay API Collector
Versão com suporte a SSL desabilitado
"""

# ========================================
# CONFIGURAÇÕES PRINCIPAIS
# ========================================

# URL base do Liferay
BASE_URL = "https://10.242.0.138:8443"

# ID do site (altere conforme necessário)
SITE_ID = "37101"

# ========================================
# CREDENCIAIS DE ACESSO
# ========================================

# Usuário e senha para autenticação
USERNAME = "nicollas.pereira@seatecnologia.com.br"
PASSWORD = "N1c0ll4s@22005"

# Token CSRF (opcional - será obtido automaticamente após login)
CSRF_TOKEN = None  # Deixe None para obter automaticamente

# Diretório onde serão salvos os dados
OUTPUT_DIR = "liferay_data"

# ========================================
# CONFIGURAÇÕES DE SEGURANÇA SSL
# ========================================

# Verificação SSL - IMPORTANTE PARA CERTIFICADOS AUTO-ASSINADOS
# False = Desabilita verificação SSL (use para certificados auto-assinados)
# True = Habilita verificação SSL (use para certificados válidos)
VERIFY_SSL = False

# ========================================
# CONFIGURAÇÕES AVANÇADAS
# ========================================

# Configurações de requisição
REQUEST_TIMEOUT = 30  # segundos
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 0.5  # segundos entre requisições

# Tamanhos de página para cada endpoint
PAGE_SIZES = {
    'structured_contents': 20,
    'content_folders': 10,
    'site_pages': 10,
    'document_folders': 20,
    'documents': 20
}

# Configurações de log
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE = True
LOG_FILE = "liferay_collector.log"

# ========================================
# CONFIGURAÇÕES ESPECÍFICAS DE COLETA
# ========================================

# Quais dados coletar (True/False)
COLLECT_OPTIONS = {
    'structured_contents': True,
    'content_folders': True, 
    'site_pages': True,
    'document_folders': True,
    'documents': True,
    'save_individual_folder_documents': True  # Salvar docs de cada pasta separadamente
}

# ========================================
# HEADERS PERSONALIZADOS (OPCIONAL)
# ========================================

CUSTOM_HEADERS = {
    'User-Agent': 'Liferay-API-Collector/1.0',
    # Adicione outros headers se necessário
    # 'Authorization': 'Bearer your_token_here',
}