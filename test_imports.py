#!/usr/bin/env python3
# ==============================================================================
# test_imports.py - Testa se todos os imports funcionam
# Execute na pasta job-automation
# ==============================================================================

import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("🧪 Testando Imports - Job Automation Pro")
print("=" * 60)

# ==============================================================================
# Teste 1: Core Config
# ==============================================================================

try:
    print("\n[1/6] Testando src.core.config...")
    from src.core.config import (
        APP_NAME, APP_VERSION, DATABASE_URL, OLLAMA_HOST, LOG_LEVEL
    )
    print(f"✓ APP_NAME: {APP_NAME}")
    print(f"✓ APP_VERSION: {APP_VERSION}")
    print(f"✓ DATABASE_URL: {DATABASE_URL}")
    print(f"✓ OLLAMA_HOST: {OLLAMA_HOST}")
except Exception as e:
    print(f"✗ Erro: {e}")
    sys.exit(1)

# ==============================================================================
# Teste 2: Core Constants
# ==============================================================================

try:
    print("\n[2/6] Testando src.core.constants...")
    from src.core.constants import (
        ApplicationStatus, ExperienceLevel, ScraperSource, MIN_COMPATIBILITY_SCORE
    )
    print(f"✓ ApplicationStatus.PENDING: {ApplicationStatus.PENDING}")
    print(f"✓ ExperienceLevel.JUNIOR: {ExperienceLevel.JUNIOR}")
    print(f"✓ ScraperSource.LINKEDIN: {ScraperSource.LINKEDIN}")
    print(f"✓ MIN_COMPATIBILITY_SCORE: {MIN_COMPATIBILITY_SCORE}")
except Exception as e:
    print(f"✗ Erro: {e}")
    sys.exit(1)

# ==============================================================================
# Teste 3: Core Logger
# ==============================================================================

try:
    print("\n[3/6] Testando src.core.logger...")
    from src.core.logger import logger, log_startup
    print("✓ Logger importado com sucesso")
    logger.info("✓ Test log message")
except Exception as e:
    print(f"✗ Erro: {e}")
    sys.exit(1)

# ==============================================================================
# Teste 4: Database Models
# ==============================================================================

try:
    print("\n[4/6] Testando src.database.models...")
    from src.database.models import User, Vacancy, Application, SchedulerJob, Base
    print(f"✓ User model: {User.__tablename__}")
    print(f"✓ Vacancy model: {Vacancy.__tablename__}")
    print(f"✓ Application model: {Application.__tablename__}")
    print(f"✓ SchedulerJob model: {SchedulerJob.__tablename__}")
except Exception as e:
    print(f"✗ Erro: {e}")
    sys.exit(1)

# ==============================================================================
# Teste 5: Database Connection
# ==============================================================================

try:
    print("\n[5/6] Testando src.database.database...")
    from src.database.database import get_session, check_connection
    print("✓ Database module importado")
    
    # Testa conexão
    is_connected = check_connection()
    if is_connected:
        print("✓ Conexão com banco de dados OK")
    else:
        print("⚠ Banco de dados não está acessível ainda (esperado)")
except Exception as e:
    print(f"✗ Erro: {e}")
    sys.exit(1)

# ==============================================================================
# Teste 6: Migrations
# ==============================================================================

try:
    print("\n[6/6] Testando src.database.migrations...")
    from src.database.migrations import run_migrations, check_database_status
    print("✓ Migrations module importado com sucesso")
except Exception as e:
    print(f"✗ Erro: {e}")
    sys.exit(1)

# ==============================================================================
# RESUMO
# ==============================================================================

print("\n" + "=" * 60)
print("✓ TODOS OS IMPORTS FUNCIONARAM COM SUCESSO!")
print("=" * 60)

print("\n📋 Próximos Passos:")
print("1. Instalar VcXsrv (X Server para Windows)")
print("2. Criar arquivo .env.example")
print("3. Criar arquivo .gitignore")
print("4. Rodar: docker-compose build")
print("5. Rodar: docker-compose up")
print("")