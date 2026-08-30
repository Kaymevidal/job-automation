# ==============================================================================
# Dockerfile - Job Automation Enterprise (PyQt6 + Ollama)
# Base: Python 3.14.7 slim (imagem leve)
# ==============================================================================

# Stage 1: Builder (instala dependências)
FROM python:3.14.7-slim as builder

WORKDIR /app

# Instala ferramentas de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements
COPY requirements.txt .

# Instala Python packages em diretório isolado
RUN pip install --user --no-cache-dir -r requirements.txt

# ==============================================================================
# Stage 2: Runtime (imagem final, menor)
FROM python:3.14.7-slim

WORKDIR /app

# Instala dependências de sistema necessárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libfontconfig1 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libgl1-mesa-glx \
    x11-xserver-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia Python packages do builder
COPY --from=builder /root/.local /root/.local

# Copia código da aplicação
COPY src/ /app/src/

# Cria diretórios de dados
RUN mkdir -p /app/data /app/personalized_cvs /app/logs

# Variáveis de ambiente
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    QT_QPA_PLATFORM=xcb \
    OLLAMA_HOST=http://ollama:11434

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:6000/health || exit 1

# Volume para dados persistentes
VOLUME ["/app/data", "/app/personalized_cvs", "/app/logs"]

# Expõe porta para comunicação interna (se necessário)
EXPOSE 6000

# Entry point
CMD ["python", "-m", "src.main"]