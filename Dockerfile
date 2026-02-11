FROM python:3.11.9-slim

# Cria diretório da app
WORKDIR /barramento_de_mensagens

# Instalações básicas
RUN apt-get update && apt-get install -y curl build-essential

# Copia a aplicação
COPY . .

# Instala dependências
RUN pip install --upgrade pip
RUN pip install uv
RUN uv sync

# Adiciona o .venv/bin ao PATH do container
ENV PATH="/barramento_de_mensagens/.venv/bin:$PATH"
ENV PYTHONPATH=/barramento_de_mensagens

# Comando padrão
CMD ["uvicorn", "business_contexts.main:app", "--host", "0.0.0.0", "--port", "8000"]
