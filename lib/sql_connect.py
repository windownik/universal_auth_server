import datetime
import os
import time
from hashlib import sha256

from fastapi_asyncpg import configure_asyncpg
from lib.app_init import app
from fastapi import Depends


password = os.environ.get("DATABASE_PASS")
host = os.environ.get("DATABASE_HOST")
port = os.environ.get("DATABASE_PORT")
db_name = os.environ.get("DATABASE_NAME")
secret = os.environ.get("SECRET")

password = 102015 if password is None else password
host = '127.0.0.1' if host is None else host
port = 5432 if port is None else port
db_name = 'tyre_app' if db_name is None else db_name
secret = 'secret12345' if secret is None else secret

# Создаем новую таблицу
data_b = configure_asyncpg(app, f'postgres://postgres:{password}@{host}:{port}/{db_name}')


# Создаем новую таблицу
async def create_token_table(db):
    await db.execute(f'''CREATE TABLE IF NOT EXISTS token (
 id SERIAL PRIMARY KEY,
 user_id BIGINT DEFAULT 0,
 token TEXT DEFAULT '0',
 token_type TEXT DEFAULT 'access',
 device_id TEXT DEFAULT '0',
 device_name TEXT DEFAULT '0',
 create_date timestamp,
 death_date timestamp
 )''')


# Создаем новую таблицу
async def create_sms_code_table(db):
    await db.execute(f'''CREATE TABLE IF NOT EXISTS sms_code (
 id SERIAL PRIMARY KEY,
 phone BIGINT DEFAULT 0,
 code INT DEFAULT 0,
 device_id TEXT DEFAULT '0',
 create_date timestamp
 )''')


# Создаем новую таблицу
async def create_auth_table(db):
    await db.execute(f'''CREATE TABLE IF NOT EXISTS auth (
 user_id SERIAL PRIMARY KEY,
 phone BIGINT UNIQUE,
 create_date timestamp
 )''')


# Создаем новый токен
async def create_token(db: Depends, user_id: int, token_type: str, device_id: str, device_name: str):
    create_date = datetime.datetime.now()
    if token_type == 'access':
        death_date = create_date + datetime.timedelta(minutes=10)
    else:
        death_date = create_date + datetime.timedelta(days=30)
    now = datetime.datetime.now()
    token = sha256(f"{user_id}.{now}.{secret}".encode('utf-8')).hexdigest()
    token = await db.fetch(f"INSERT INTO token (user_id, token, token_type, device_id, device_name, create_date, "
                           f"death_date) VALUES ($1, $2, $3, $4, $5, $6, $7) "
                           f"ON CONFLICT DO NOTHING RETURNING token;", user_id, token, token_type, device_id,
                           device_name, create_date, death_date)
    return token


# Создаем новый токен
async def save_sms_code(db: Depends, phone: int, code: int, device_id: str):
    create_date = datetime.datetime.now()
    token = await db.fetch(f"INSERT INTO sms_code (phone, code, device_id, create_date) "
                           f"VALUES ($1, $2, $3, $4) "
                           f"ON CONFLICT DO NOTHING RETURNING id;", phone, code, device_id,
                           create_date)
    return token


# Создаем новый токен
async def create_user_id(db: Depends, phone: int,):
    create_date = datetime.datetime.now()
    token = await db.fetch(f"INSERT INTO auth (phone, create_date) "
                           f"VALUES ($1, $2) "
                           f"ON CONFLICT DO NOTHING RETURNING user_id;", phone, create_date)
    return token


async def get_user_id(db: Depends, token_type: str, token: str, device_id: str):
    """Get user_id by token and device id"""
    now = datetime.datetime.now()
    data = await db.fetch(f"SELECT user_id, death_date FROM token "
                          f"WHERE token_type = $1 "
                          f"AND device_id = $2 "
                          f"AND token = $3 "
                          f"AND death_date > $4;",
                          token_type, device_id, token, now)
    return data


async def get_user_id_by_token(db: Depends, token_type: str, token: str):
    """Get user_id by token and device id"""
    now = datetime.datetime.now()
    data = await db.fetch(f"SELECT user_id, death_date FROM token "
                          f"WHERE token_type = $1 "
                          f"AND token = $2 "
                          f"AND death_date > $3;",
                          token_type, token, now)
    return data


# Обновляем информацию
async def update_user_active(db: Depends, user_id: int):
    now = datetime.datetime.now()
    await db.fetch(f"UPDATE all_users SET last_active=$1 WHERE user_id=$2;",
                   int(time.mktime(now.timetuple())), user_id)


async def read_data(db: Depends, table: str, id_name: str, id_data, order: str = '', name: str = '*'):
    """Получаем актуальные события"""
    data = await db.fetch(f"SELECT {name} FROM {table} WHERE {id_name} = $1{order};", id_data)
    return data


async def check_sms_code(db: Depends, phone: int, sms_code: int, device_id: str, ):
    """Получаем актуальные события"""
    data = await db.fetch(f"SELECT create_date FROM sms_code "
                          f"WHERE phone = $1 AND code = $2 AND device_id = $3;", phone, sms_code, device_id)
    return data


# Удаляем токены
async def delete_old_tokens(db: Depends):
    now = datetime.datetime.now()
    await db.execute(f"DELETE FROM token WHERE death_date < $1", now)


# Удаляем токены
async def delete_all_tokens_with_device_id(db: Depends, device_id: str):
    await db.execute(f"DELETE FROM token WHERE device_id = $1", device_id)


# Удаляем все записи из таблицы по ключу
async def delete_where(db: Depends, table: str, id_name: str, data):
    await db.execute(f"DELETE FROM {table} WHERE {id_name} = $1", data)


# Удаляем все записи из таблицы
async def delete_from_table(db: Depends, table: str):
    await db.execute(f"DELETE FROM {table};")
