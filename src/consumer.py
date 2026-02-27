#!/usr/bin/env python3
import boto3
import psycopg2
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración actualizada
QUEUE_URL = "aws_queue_url"
DB_HOST = "aws_rds_db"
DB_PORT = "db_port"
DB_NAME = "postgres"
DB_USER = "cafeteria_user"
DB_PASSWORD = "password"

sqs = boto3.client('sqs', region_name='us-east-1')

def parse_message(body):
    try:
        coffee_type, timestamp_str = body.strip().split('|')
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        return coffee_type, timestamp
    except:
        return None, None

def insert_order(conn, coffee_type, timestamp):
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO coffee_orders (timestamp, coffee_type, order_status) VALUES (%s, %s, 'created')",
                (timestamp, coffee_type)
            )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"DB error: {e}")
        conn.rollback()
        return False

def main():
    conn = None
    while True:
        if conn is None or conn.closed:
            try:
                conn = psycopg2.connect(
                    host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                    user=DB_USER, password=DB_PASSWORD
                )
                logger.info("Conectado a RDS")
            except Exception as e:
                logger.error(f"Error conectando a RDS: {e}")
                time.sleep(10)
                continue

        try:
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
                VisibilityTimeout=30
            )
            messages = response.get('Messages', [])
            for msg in messages:
                receipt = msg['ReceiptHandle']
                body = msg['Body']
                logger.info(f"Recibido: {body}")

                coffee, ts = parse_message(body)
                if not coffee:
                    logger.warning(f"Formato inválido, eliminando: {body}")
                    sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt)
                    continue

                if insert_order(conn, coffee, ts):
                    sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt)
                    logger.info("Mensaje procesado y eliminado")
                else:
                    logger.error("Fallo inserción, mensaje retenido")
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            time.sleep(5)

        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Detenido por usuario")
