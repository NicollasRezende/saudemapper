#!/usr/bin/env python3
"""
Liferay Headless API Data Collector - Versão com SSL Fix
Versão melhorada com opção de desabilitar verificação SSL
"""

import requests
import json
import os
import time
import base64
from datetime import datetime
from typing import Dict, List, Optional
import logging
import re
from urllib.parse import urlparse, urljoin
import urllib3

# Desabilitar warnings de SSL não verificado
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LiferayAPICollector:
    def __init__(self, base_url: str, site_id: str, username: str = None, password: str = None, 
                 csrf_token: str = None, output_dir: str = "liferay_data", verify_ssl: bool = False):
        self.base_url = base_url.rstrip('/')
        self.site_id = site_id
        self.username = username
        self.password = password
        self.csrf_token = csrf_token
        self.output_dir = output_dir
        self.verify_ssl = verify_ssl  # Nova opção para SSL
        self.session = requests.Session()
        
        # Configurar verificação SSL
        self.session.verify = self.verify_ssl
        
        # Configurar User-Agent mais realista
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })
        
        # Configurar logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('liferay_collector.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Log sobre SSL
        if not self.verify_ssl:
            self.logger.info("🔓 Verificação SSL desabilitada - conexões inseguras permitidas")
        else:
            self.logger.info("🔒 Verificação SSL habilitada")
        
        # Criar diretório de saída
        os.makedirs(output_dir, exist_ok=True)
        
        # Autenticar se credenciais foram fornecidas
        if username and password:
            self.authenticate_comprehensive()
        
        # Estatísticas
        self.stats = {
            'structured_contents': 0,
            'content_folders': 0,
            'site_pages': 0,
            'document_folders': 0,
            'documents': 0,
            'errors': 0,
            'start_time': datetime.now()
        }

    def debug_request(self, response):
        """Debug detalhado de uma resposta"""
        self.logger.debug(f"Status: {response.status_code}")
        self.logger.debug(f"Headers: {dict(response.headers)}")
        if response.status_code != 200:
            self.logger.debug(f"Response text: {response.text[:500]}...")

    def authenticate_comprehensive(self):
        """Autenticação abrangente com múltiplas estratégias"""
        self.logger.info("🔐 Iniciando autenticação abrangente...")
        
        # Estratégia 1: Basic Auth
        if self.try_basic_auth():
            self.logger.info("✅ Autenticação Basic Auth funcionou")
            return
        
        # Estratégia 2: Login via formulário web
        if self.try_web_login():
            self.logger.info("✅ Autenticação via login web funcionou")
            return
            
        # Estratégia 3: Login via API JSON-WS
        if self.try_jsonws_login():
            self.logger.info("✅ Autenticação via JSON-WS funcionou")
            return
        
        # Estratégia 4: OAuth2 (se disponível)
        if self.try_oauth2():
            self.logger.info("✅ Autenticação OAuth2 funcionou")
            return
        
        self.logger.warning("⚠️ Nenhuma estratégia de autenticação funcionou - tentando sem autenticação")

    def try_basic_auth(self):
        """Tenta autenticação Basic Auth"""
        try:
            self.logger.info("🔑 Tentando Basic Auth...")
            
            # Configurar Basic Auth
            auth_string = f"{self.username}:{self.password}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            self.session.headers['Authorization'] = f'Basic {auth_b64}'
            
            # Testar com endpoint simples
            test_url = f"{self.base_url}/api/jsonws/user/get-current-user"
            response = self.session.get(test_url, verify=self.verify_ssl)
            
            if response.status_code == 200:
                user_data = response.json()
                self.logger.info(f"✅ Basic Auth sucesso - Usuário: {user_data.get('screenName', 'N/A')}")
                return True
                
        except Exception as e:
            self.logger.debug(f"Basic Auth falhou: {e}")
        
        return False

    def try_web_login(self):
        """Tenta login via formulário web"""
        try:
            self.logger.info("🌐 Tentando login web...")
            
            # Obter página de login
            login_url = f"{self.base_url}/c/portal/login"
            response = self.session.get(login_url, verify=self.verify_ssl)
            
            if response.status_code != 200:
                return False
            
            # Extrair tokens necessários
            html = response.text
            
            # Buscar p_auth token
            p_auth_matches = re.findall(r'p_auth["\s]*[=:]["\s]*([^"&\s]+)', html)
            p_auth = p_auth_matches[0] if p_auth_matches else ""
            
            # Buscar CSRF token
            csrf_matches = re.findall(r'csrf["\s]*[=:]["\s]*([^"&\s]+)', html, re.IGNORECASE)
            csrf_token = csrf_matches[0] if csrf_matches else ""
            
            # Buscar authenticity token
            auth_matches = re.findall(r'authenticity_token["\s]*[=:]["\s]*([^"&\s]+)', html)
            auth_token = auth_matches[0] if auth_matches else ""
            
            self.logger.debug(f"Tokens encontrados - p_auth: {p_auth[:10]}..., csrf: {csrf_token[:10]}...")
            
            # Preparar dados de login
            login_data = {
                'login': self.username,
                'password': self.password,
                'rememberMe': 'false',
            }
            
            # Adicionar tokens se encontrados
            if p_auth:
                login_data['p_auth'] = p_auth
            if csrf_token:
                login_data['csrf_token'] = csrf_token
                self.csrf_token = csrf_token
            if auth_token:
                login_data['authenticity_token'] = auth_token
            
            # Headers para login
            login_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': login_url,
                'Origin': self.base_url
            }
            
            # Fazer login
            login_response = self.session.post(login_url, data=login_data, headers=login_headers, 
                                             allow_redirects=True, verify=self.verify_ssl)
            
            # Verificar se login funcionou
            if login_response.status_code == 200 and 'error' not in login_response.url:
                # Tentar obter informações do usuário para confirmar
                user_url = f"{self.base_url}/api/jsonws/user/get-current-user"
                user_response = self.session.get(user_url, verify=self.verify_ssl)
                
                if user_response.status_code == 200:
                    try:
                        user_data = user_response.json()
                        self.logger.info(f"✅ Login web sucesso - Usuário: {user_data.get('screenName', 'N/A')}")
                        return True
                    except:
                        pass
                        
                # Se JSON falhou, verificar se não tem "sign-in" na página
                if 'sign-in' not in login_response.text.lower() and 'login' not in login_response.text.lower():
                    self.logger.info("✅ Login web aparenta ter funcionado")
                    return True
                    
        except Exception as e:
            self.logger.debug(f"Login web falhou: {e}")
        
        return False

    def try_jsonws_login(self):
        """Tenta login via API JSON-WS"""
        try:
            self.logger.info("📡 Tentando login JSON-WS...")
            
            # URL da API de login
            login_url = f"{self.base_url}/api/jsonws/user/authenticate"
            
            login_data = {
                'companyId': '',  # Será preenchido automaticamente
                'login': self.username,
                'password': self.password,
                'remoteAddr': '',
                'remoteHost': '',
                'userAgent': self.session.headers.get('User-Agent', '')
            }
            
            response = self.session.post(login_url, data=login_data, verify=self.verify_ssl)
            
            if response.status_code == 200:
                self.logger.info("✅ Login JSON-WS sucesso")
                return True
                
        except Exception as e:
            self.logger.debug(f"Login JSON-WS falhou: {e}")
        
        return False

    def try_oauth2(self):
        """Tenta autenticação OAuth2"""
        try:
            self.logger.info("🔐 Verificando OAuth2...")
            # Implementação básica - pode ser expandida conforme necessário
            oauth_url = f"{self.base_url}/o/oauth2/token"
            
            oauth_data = {
                'grant_type': 'password',
                'username': self.username,
                'password': self.password,
                'client_id': 'headless-server',  # ID padrão do Liferay
            }
            
            response = self.session.post(oauth_url, data=oauth_data, verify=self.verify_ssl)
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get('access_token')
                
                if access_token:
                    self.session.headers['Authorization'] = f'Bearer {access_token}'
                    self.logger.info("✅ OAuth2 sucesso")
                    return True
                    
        except Exception as e:
            self.logger.debug(f"OAuth2 falhou: {e}")
        
        return False

    def find_csrf_token(self):
        """Busca token CSRF em várias fontes"""
        csrf_sources = [
            f"{self.base_url}/",
            f"{self.base_url}/web/guest",
            f"{self.base_url}/group/control_panel",
            f"{self.base_url}/api/jsonws"
        ]
        
        for url in csrf_sources:
            try:
                response = self.session.get(url, verify=self.verify_ssl)
                if response.status_code == 200:
                    # Buscar no cabeçalho
                    csrf_header = response.headers.get('X-CSRF-Token')
                    if csrf_header:
                        self.csrf_token = csrf_header
                        self.session.headers['X-CSRF-Token'] = csrf_header
                        self.logger.info(f"✅ CSRF token encontrado no header: {csrf_header[:10]}...")
                        return
                    
                    # Buscar no conteúdo
                    csrf_matches = re.findall(r'csrf["\s]*[=:]["\s]*([^"&\s<>]{10,})', response.text, re.IGNORECASE)
                    if csrf_matches:
                        self.csrf_token = csrf_matches[0]
                        self.session.headers['X-CSRF-Token'] = self.csrf_token
                        self.logger.info(f"✅ CSRF token extraído do conteúdo: {self.csrf_token[:10]}...")
                        return
                        
            except Exception as e:
                self.logger.debug(f"Erro ao buscar CSRF em {url}: {e}")
        
        self.logger.warning("⚠️ CSRF token não encontrado em nenhuma fonte")

    def make_request(self, url: str, params: Dict = None, max_retries: int = 3) -> Optional[Dict]:
        """Faz requisição HTTP com retry e debugging melhorado"""
        
        # Tentar encontrar CSRF token se não tiver
        if not self.csrf_token:
            self.find_csrf_token()
        
        for attempt in range(max_retries):
            try:
                # Headers específicos para API Headless
                api_headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
                
                # Adicionar CSRF token se disponível
                if self.csrf_token:
                    api_headers['X-CSRF-Token'] = self.csrf_token
                
                response = self.session.get(url, params=params, headers=api_headers, 
                                          timeout=30, verify=self.verify_ssl)
                
                # Debug detalhado no primeiro erro
                if response.status_code != 200 and attempt == 0:
                    self.logger.debug(f"🔍 DEBUG - URL: {url}")
                    self.logger.debug(f"🔍 DEBUG - Params: {params}")
                    self.logger.debug(f"🔍 DEBUG - Headers enviados: {api_headers}")
                    self.logger.debug(f"🔍 DEBUG - Status: {response.status_code}")
                    self.logger.debug(f"🔍 DEBUG - Response headers: {dict(response.headers)}")
                    self.logger.debug(f"🔍 DEBUG - Response preview: {response.text[:200]}...")
                
                response.raise_for_status()
                return response.json()
            
            except requests.exceptions.SSLError as e:
                self.logger.error(f"❌ Erro SSL: {e}")
                if self.verify_ssl:
                    self.logger.warning("💡 Dica: Tente executar com verify_ssl=False se estiver usando certificado auto-assinado")
                return None
            
            except requests.exceptions.HTTPError as e:
                if response.status_code == 403:
                    self.logger.warning(f"❌ Acesso negado (403) para {url}")
                    if attempt == 0:
                        self.logger.info("🔄 Tentando reautenticar...")
                        if self.username and self.password:
                            self.authenticate_comprehensive()
                elif response.status_code == 401:
                    self.logger.warning(f"❌ Não autorizado (401) para {url}")
                    if attempt == 0:
                        self.logger.info("🔄 Tentando reautenticar...")
                        if self.username and self.password:
                            self.authenticate_comprehensive()
                else:
                    self.logger.warning(f"❌ HTTP Error {response.status_code} para {url}")
                
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.stats['errors'] += 1
                    return None
            
            except Exception as e:
                self.logger.warning(f"❌ Erro na tentativa {attempt + 1} para {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    self.stats['errors'] += 1
                    return None

    def test_api_access(self):
        """Testa acesso à API antes de iniciar coleta"""
        self.logger.info("🧪 Testando acesso à API...")
        
        test_urls = [
            f"{self.base_url}/o/headless-delivery/v1.0/sites/{self.site_id}",
            f"{self.base_url}/o/headless-delivery/v1.0/sites",
            f"{self.base_url}/api/jsonws/user/get-current-user"
        ]
        
        for test_url in test_urls:
            response = self.make_request(test_url)
            if response:
                self.logger.info(f"✅ API acessível via: {test_url}")
                return True
        
        self.logger.error("❌ Nenhuma API acessível - verifique credenciais e permissões")
        return False

    def collect_paginated_data(self, endpoint: str, data_key: str, page_size: int = 20) -> List[Dict]:
        """Coleta dados paginados de um endpoint com melhor tratamento de erro"""
        all_data = []
        page = 1
        total_pages = None
        
        self.logger.info(f"📊 Iniciando coleta de {data_key}...")
        
        while True:
            url = f"{self.base_url}{endpoint}"
            params = {'page': page, 'pageSize': page_size}
            
            data = self.make_request(url, params)
            if not data:
                self.logger.error(f"❌ Falha ao obter dados de {data_key} na página {page}")
                break
                
            # Primeira página - obter informações totais
            if page == 1:
                total_count = data.get('totalCount', 0)
                total_pages = data.get('lastPage', 1)
                self.logger.info(f"📈 {data_key}: {total_count} registros em {total_pages} páginas")
                
                # Se não há dados, sair
                if total_count == 0:
                    self.logger.warning(f"⚠️ Nenhum registro encontrado para {data_key}")
                    break
            
            # Adicionar itens da página atual
            items = data.get('items', [])
            all_data.extend(items)
            
            self.logger.info(f"📄 Página {page}/{total_pages}: {len(items)} itens coletados")
            
            # Verificar se há mais páginas
            if page >= total_pages:
                break
                
            page += 1
            time.sleep(0.5)  # Rate limiting
        
        self.logger.info(f"✅ Coleta de {data_key} concluída: {len(all_data)} registros")
        return all_data

    # Métodos de coleta individuais (mesmos da versão anterior)
    def collect_structured_contents(self):
        """Coleta conteúdos estruturados"""
        endpoint = f"/o/headless-delivery/v1.0/sites/{self.site_id}/structured-contents"
        data = self.collect_paginated_data(endpoint, "conteúdos estruturados")
        
        if data:
            filename = os.path.join(self.output_dir, "structured_contents.json")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.stats['structured_contents'] = len(data)
            self.logger.info(f"💾 Salvos {len(data)} conteúdos estruturados em {filename}")

    def collect_content_folders(self):
        """Coleta pastas de conteúdo"""
        endpoint = f"/o/headless-delivery/v1.0/sites/{self.site_id}/structured-content-folders"
        data = self.collect_paginated_data(endpoint, "pastas de conteúdo", page_size=10)
        
        if data:
            filename = os.path.join(self.output_dir, "content_folders.json")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.stats['content_folders'] = len(data)
            self.logger.info(f"💾 Salvas {len(data)} pastas de conteúdo em {filename}")

    def collect_site_pages(self):
        """Coleta páginas do site"""
        endpoint = f"/o/headless-delivery/v1.0/sites/{self.site_id}/site-pages"
        data = self.collect_paginated_data(endpoint, "páginas do site", page_size=10)
        
        if data:
            filename = os.path.join(self.output_dir, "site_pages.json")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.stats['site_pages'] = len(data)
            self.logger.info(f"💾 Salvas {len(data)} páginas do site em {filename}")

    def collect_document_folders(self):
        """Coleta pastas de documentos"""
        endpoint = f"/o/headless-delivery/v1.0/sites/{self.site_id}/document-folders"
        folders = self.collect_paginated_data(endpoint, "pastas de documentos")
        
        if folders:
            filename = os.path.join(self.output_dir, "document_folders.json")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(folders, f, ensure_ascii=False, indent=2)
            self.stats['document_folders'] = len(folders)
            self.logger.info(f"💾 Salvas {len(folders)} pastas de documentos em {filename}")
            return folders
        return []

    def collect_documents_from_folders(self, folders: List[Dict]):
        """Coleta documentos de cada pasta"""
        all_documents = []
        
        for i, folder in enumerate(folders, 1):
            folder_id = folder.get('id')
            folder_name = folder.get('name', f'Pasta_{folder_id}')
            
            self.logger.info(f"📁 Coletando documentos da pasta {i}/{len(folders)}: {folder_name}")
            
            endpoint = f"/o/headless-delivery/v1.0/document-folders/{folder_id}/documents"
            documents = self.collect_paginated_data(endpoint, f"documentos da pasta {folder_name}")
            
            # Adicionar informação da pasta aos documentos
            for doc in documents:
                doc['source_folder'] = {
                    'id': folder_id,
                    'name': folder_name
                }
            
            all_documents.extend(documents)
            
            # Salvar documentos da pasta individualmente
            if documents:
                safe_folder_name = re.sub(r'[^\w\-_]', '_', folder_name)[:50]
                folder_filename = os.path.join(
                    self.output_dir, 
                    f"documents_folder_{folder_id}_{safe_folder_name}.json"
                )
                with open(folder_filename, 'w', encoding='utf-8') as f:
                    json.dump(documents, f, ensure_ascii=False, indent=2)
        
        # Salvar todos os documentos em um arquivo consolidado
        if all_documents:
            filename = os.path.join(self.output_dir, "all_documents.json")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(all_documents, f, ensure_ascii=False, indent=2)
            self.stats['documents'] = len(all_documents)
            self.logger.info(f"💾 Salvos {len(all_documents)} documentos em {filename}")

    def generate_summary_report(self):
        """Gera relatório resumo da coleta"""
        end_time = datetime.now()
        duration = end_time - self.stats['start_time']
        
        summary = {
            'coleta_realizada_em': end_time.isoformat(),
            'duracao_total': str(duration),
            'estatisticas': {
                'conteudos_estruturados': self.stats['structured_contents'],
                'pastas_de_conteudo': self.stats['content_folders'],
                'paginas_do_site': self.stats['site_pages'],
                'pastas_de_documentos': self.stats['document_folders'],
                'documentos': self.stats['documents'],
                'erros': self.stats['errors']
            },
            'configuracao': {
                'base_url': self.base_url,
                'site_id': self.site_id,
                'output_dir': self.output_dir,
                'username': self.username,
                'verify_ssl': self.verify_ssl,
                'csrf_token_obtido': bool(self.csrf_token)
            }
        }
        
        filename = os.path.join(self.output_dir, "summary_report.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # Log do resumo
        self.logger.info("=" * 50)
        self.logger.info("📊 RESUMO DA COLETA")
        self.logger.info("=" * 50)
        self.logger.info(f"✅ Conteúdos estruturados: {self.stats['structured_contents']}")
        self.logger.info(f"📁 Pastas de conteúdo: {self.stats['content_folders']}")
        self.logger.info(f"🌐 Páginas do site: {self.stats['site_pages']}")
        self.logger.info(f"📂 Pastas de documentos: {self.stats['document_folders']}")
        self.logger.info(f"📋 Documentos: {self.stats['documents']}")
        self.logger.info(f"❌ Erros: {self.stats['errors']}")
        self.logger.info(f"⏱️ Duração total: {duration}")
        self.logger.info(f"📄 Relatório salvo em: {filename}")

    def run_full_collection(self):
        """Executa coleta completa de todos os dados com testes prévios"""
        self.logger.info("🚀 Iniciando coleta completa da API Headless do Liferay")
        
        # Testar acesso à API primeiro
        if not self.test_api_access():
            self.logger.error("❌ Falha no teste de acesso - abortando coleta")
            return False
        
        try:
            # 1. Conteúdos estruturados
            self.collect_structured_contents()
            
            # 2. Pastas de conteúdo
            self.collect_content_folders()
            
            # 3. Páginas do site
            self.collect_site_pages()
            
            # 4. Pastas de documentos
            document_folders = self.collect_document_folders()
            
            # 5. Documentos (se houver pastas)
            if document_folders:
                self.collect_documents_from_folders(document_folders)
            
            # 6. Gerar relatório
            self.generate_summary_report()
            
            self.logger.info("🎉 Coleta completa finalizada!")
            return True
            
        except Exception as e:
            self.logger.error(f"💥 Erro durante a coleta: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return False


def main():
    """Função principal com SSL desabilitado"""
    
    # CONFIGURAÇÕES
    config = {
        'base_url': 'https://10.242.0.138:8443',
        'site_id': '37101',
        'username': 'nicollas.pereira@seatecnologia.com.br',
        'password': 'N1c0ll4s@22005',
        'output_dir': 'liferay_data_ssl_fixed',
        'verify_ssl': False  # ← DESABILITA VERIFICAÇÃO SSL
    }
    
    print("🔧 Liferay API Collector - Versão SSL Fix")
    print("=" * 60)
    print(f"🌐 URL: {config['base_url']}")
    print(f"🏢 Site ID: {config['site_id']}")
    print(f"👤 Usuário: {config['username']}")
    print(f"📁 Diretório: {config['output_dir']}")
    print(f"🔓 SSL Verify: {config['verify_ssl']}")
    print("=" * 60)
    
    try:
        collector = LiferayAPICollector(
            base_url=config['base_url'],
            site_id=config['site_id'],
            username=config['username'],
            password=config['password'],
            output_dir=config['output_dir'],
            verify_ssl=config['verify_ssl']  # ← PASSA O PARÂMETRO SSL
        )
        
        success = collector.run_full_collection()
        
        if success:
            print("\n" + "=" * 60)
            print("✅ COLETA FINALIZADA COM SUCESSO!")
            print(f"📂 Dados salvos em: {config['output_dir']}/")
            print(f"📊 Relatório: {config['output_dir']}/summary_report.json")
            print("📜 Logs detalhados: liferay_collector.log")
        else:
            print("\n" + "=" * 60)
            print("❌ COLETA FALHOU - Verifique os logs para detalhes")
            print("📜 Logs: liferay_collector.log")
        
    except KeyboardInterrupt:
        print("\n⚠️ Processo interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")


if __name__ == "__main__":
    main()