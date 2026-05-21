#!/usr/bin/env bash
# Interrompe a execução se houver algum erro
set -o errexit

# Instala as dependências
pip install -r requirements.txt

# Coleta os arquivos estáticos
python manage.py collectstatic --no-input

# Executa as migrações do banco de dados
python manage.py migrate