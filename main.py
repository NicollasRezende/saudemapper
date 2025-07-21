#!/usr/bin/env python3
"""
Script de execução do Liferay API Collector
Permite executar coletas específicas ou completa com suporte a SSL
"""

import argparse
import sys
from liferay_collector import LiferayAPICollector
import config

def main():
    parser = argparse.ArgumentParser(
        description="Liferay Headless API Data Collector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Coleta completa
  python main.py --all

  # Coleta apenas conteúdos estruturados
  python main.py --structured-contents

  # Coleta com SSL desabilitado (para certificados auto-assinados)
  python main.py --all --no-ssl

  # Coleta conteúdos e pastas
  python main.py --structured-contents --content-folders

  # Coleta com diretório personalizado
  python main.py --all --output-dir meus_dados

  # Coleta com configurações personalizadas
  python main.py --all --site-id 12345 --csrf-token novo_token
        """
    )
    
    # Argumentos de configuração
    parser.add_argument('--base-url', default=config.BASE_URL,
                       help=f'URL base do Liferay (padrão: {config.BASE_URL})')
    parser.add_argument('--site-id', default=config.SITE_ID,
                       help=f'ID do site (padrão: {config.SITE_ID})')
    parser.add_argument('--username', default=config.USERNAME,
                       help='Nome de usuário para autenticação')
    parser.add_argument('--password', default=config.PASSWORD,
                       help='Senha para autenticação')
    parser.add_argument('--csrf-token', default=config.CSRF_TOKEN,
                       help='Token CSRF (opcional - obtido automaticamente)')
    parser.add_argument('--output-dir', default=config.OUTPUT_DIR,
                       help=f'Diretório de saída (padrão: {config.OUTPUT_DIR})')
    
    # Configurações SSL
    parser.add_argument('--no-ssl', action='store_false', dest='verify_ssl',
                       help='Desabilitar verificação SSL (para certificados auto-assinados)')
    parser.add_argument('--verify-ssl', action='store_true', dest='verify_ssl',
                       help='Habilitar verificação SSL')
    parser.set_defaults(verify_ssl=config.VERIFY_SSL)
    
    # Argumentos de coleta
    parser.add_argument('--all', action='store_true',
                       help='Coletar todos os dados')
    parser.add_argument('--structured-contents', action='store_true',
                       help='Coletar conteúdos estruturados')
    parser.add_argument('--content-folders', action='store_true',
                       help='Coletar pastas de conteúdo')
    parser.add_argument('--site-pages', action='store_true',
                       help='Coletar páginas do site')
    parser.add_argument('--document-folders', action='store_true',
                       help='Coletar pastas de documentos')
    parser.add_argument('--documents', action='store_true',
                       help='Coletar documentos')
    
    # Argumentos adicionais
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Modo verboso (mais logs)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Simular execução (não fazer requisições)')
    
    args = parser.parse_args()
    
    # Validar credenciais
    if not args.username or not args.password:
        print("❌ Erro: Usuário e senha são obrigatórios!")
        print("   Configure no arquivo config.py ou use --username e --password")
        return
    
    print(f"🔐 Usando credenciais: {args.username}")
    if args.csrf_token:
        print(f"🎫 Token CSRF fornecido: {args.csrf_token[:10]}...")
    else:
        print("🎫 Token CSRF será obtido automaticamente após login")
    
    # Informar sobre SSL
    if args.verify_ssl:
        print("🔒 Verificação SSL habilitada")
    else:
        print("🔓 Verificação SSL desabilitada (certificados auto-assinados aceitos)")
    
    # Determinar o que coletar
    if args.all:
        collect_options = {
            'structured_contents': True,
            'content_folders': True,
            'site_pages': True,
            'document_folders': True,
            'documents': True
        }
    else:
        collect_options = {
            'structured_contents': args.structured_contents,
            'content_folders': args.content_folders,
            'site_pages': args.site_pages,
            'document_folders': args.document_folders,
            'documents': args.documents
        }
    
    # Verificar se pelo menos uma opção foi selecionada
    if not any(collect_options.values()):
        print("❌ Erro: Nenhuma opção de coleta selecionada!")
        print("   Use --all ou selecione dados específicos (--structured-contents, etc.)")
        print("   Use --help para ver todas as opções.")
        return
    
    # Modo dry-run
    if args.dry_run:
        print("🔍 MODO DRY-RUN - Simulando execução")
        print(f"Configurações:")
        print(f"  Base URL: {args.base_url}")
        print(f"  Site ID: {args.site_id}")
        print(f"  Usuário: {args.username}")
        print(f"  SSL Verify: {args.verify_ssl}")
        print(f"  Output: {args.output_dir}")
        print(f"  Coletas selecionadas:")
        for key, value in collect_options.items():
            if value:
                print(f"    ✓ {key}")
        print("\nSimulação concluída. Use sem --dry-run para executar de verdade.")
        return
    
    # Criar coletor
    try:
        collector = LiferayAPICollector(
            base_url=args.base_url,
            site_id=args.site_id,
            username=args.username,
            password=args.password,
            csrf_token=args.csrf_token,
            output_dir=args.output_dir,
            verify_ssl=args.verify_ssl  # ← NOVA OPÇÃO SSL
        )
        
        print("🚀 Iniciando coleta...")
        print(f"📊 Dados selecionados: {sum(collect_options.values())}/{len(collect_options)}")
        
        # Executar coletas selecionadas
        document_folders = []
        
        if collect_options['structured_contents']:
            print("\n📄 Coletando conteúdos estruturados...")
            collector.collect_structured_contents()
        
        if collect_options['content_folders']:
            print("\n📁 Coletando pastas de conteúdo...")
            collector.collect_content_folders()
        
        if collect_options['site_pages']:
            print("\n🌐 Coletando páginas do site...")
            collector.collect_site_pages()
        
        if collect_options['document_folders']:
            print("\n📂 Coletando pastas de documentos...")
            document_folders = collector.collect_document_folders()
        
        if collect_options['documents'] and document_folders:
            print("\n📋 Coletando documentos...")
            collector.collect_documents_from_folders(document_folders)
        elif collect_options['documents'] and not document_folders:
            print("⚠️  Aviso: Coleta de documentos solicitada, mas nenhuma pasta foi encontrada.")
            print("   Execute primeiro a coleta de pastas de documentos.")
        
        # Gerar relatório
        print("\n📈 Gerando relatório final...")
        collector.generate_summary_report()
        
        print(f"\n✅ Coleta finalizada com sucesso!")
        print(f"📁 Dados salvos em: {args.output_dir}/")
        print(f"📋 Relatório: {args.output_dir}/summary_report.json")
        print(f"📜 Logs: liferay_collector.log")
        
    except KeyboardInterrupt:
        print("\n⚠️  Coleta interrompida pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro durante a execução: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()