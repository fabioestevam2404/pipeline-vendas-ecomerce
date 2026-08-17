# Imagem do Airflow com as dependências que as DAGs do pipeline precisam
# além do que o Airflow já traz. Ver requirements-airflow.txt: NÃO fixa
# versão do SQLAlchemy — o Airflow já fixa 1.4.x como dependência própria, e
# forçar 2.0 aqui quebraria o metastore do próprio Airflow. O código do
# pipeline (src/) foi verificado como compatível com SQLAlchemy 1.4 (ver
# ADR-001 e CHANGELOG — bugs de compatibilidade reais foram encontrados e
# corrigidos rodando as DAGs de verdade sob esta combinação de versões).
FROM apache/airflow:2.9.3-python3.12

COPY requirements-airflow.txt /requirements-airflow.txt
RUN pip install --no-cache-dir -r /requirements-airflow.txt
