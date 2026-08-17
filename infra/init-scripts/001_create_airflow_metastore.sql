-- Cria um banco separado para o metastore do Airflow, no mesmo servidor
-- PostgreSQL do pipeline (schemas `staging`/`mart` ficam no banco principal,
-- definido por POSTGRES_DB — o metastore do Airflow é um banco à parte para
-- não misturar o controle interno de execuções do Airflow com os dados do
-- pipeline). Rodado uma única vez, na primeira inicialização do volume
-- (docker-entrypoint-initdb.d só executa em volume vazio).
CREATE DATABASE airflow_metastore;
