from dotenv import load_dotenv
import mysql.connector, mysql.connector.pooling
import os

load_dotenv()

pool = mysql.connector.pooling.MySQLConnectionPool(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    database=os.getenv("DB_NAME"),
    buffered=True,
    pool_size=3,
    pool_name="mypool",
)
