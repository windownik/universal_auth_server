import datetime
import os
import random

import starlette.status as _status
from fastapi import Depends
from starlette.responses import JSONResponse, HTMLResponse

from lib import sql_connect as conn
from lib.response_examples import *
from lib.routes.auth.check_sms import send_sms_code
from lib.routes.auth.hash_funcs import check_password, hash_password
from lib.sql_connect import data_b, app

ip_server = os.environ.get("IP_SERVER")
ip_port = os.environ.get("PORT_SERVER")

ip_port = 80 if ip_port is None else ip_port
ip_server = "127.0.0.1" if ip_server is None else ip_server


@data_b.on_init
async def initialization(connect):
    # you can run your db initialization code here
    await connect.execute("SELECT 1")
    await conn.create_auth_table(db=connect)
    await conn.create_token_table(db=connect)
    await conn.create_sms_code_table(db=connect)
    print('Create all tables')


def generate_html_response():
    html_content = """
    <html>
        <head>
            <title>Start page</title>
        </head>
        <body>
            <h2>Documentation for Universal auth API</h2>
            <p><a href="/docs">Documentation Swager</a></p>
            <p><a href="/redoc">Documentation from reDoc</a></p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.get('/', response_class=HTMLResponse, tags=['Auth'])
async def main_page():
    """main page"""
    return generate_html_response()


@app.post(path='/create_access_token', tags=['Auth'], responses=access_token_res)
async def create_new_access_token(refresh_token: str, device_id: str, device_name: str, app_name: str,
                                  db=Depends(data_b.connection)):
    """Use it for create new access token and new refresh if it too old\n
    refresh_token: This is refresh token.
    You can get it when create account or login."""
    user_id = await conn.get_user_id(db=db, token_type='refresh', token=refresh_token, device_id=device_id)
    if not user_id:
        return JSONResponse(content={"ok": False,
                                     'description': "bad refresh token or device_id, please login"},
                            status_code=_status.HTTP_401_UNAUTHORIZED)
    await conn.delete_old_tokens(db=db)
    now = datetime.datetime.now()
    less_3 = now - datetime.timedelta(days=3)

    if user_id[0][1] < less_3:
        refresh = await conn.create_token(db=db, user_id=user_id[0][0], token_type='refresh', device_id=device_id,
                                          device_name=device_name, app_name=app_name)
        refresh_token = refresh[0][0]
    access = await conn.create_token(db=db, user_id=user_id[0][0], token_type='access', device_id=device_id,
                                     device_name=device_name, app_name=app_name)

    # This code for update users active statistic
    # await conn.update_user_active(db=db, user_id=user_id[0][0])
    return {"ok": True,
            'user_id': user_id[0][0],
            'access_token': access[0][0],
            'refresh_token': refresh_token}


@app.get(path='/user_id', tags=['Auth'], responses=get_user_id_res)
async def get_user_id_by_token(access_token: str, db=Depends(data_b.connection)):
    """access_token: This is access token. You can get it when create account or login."""
    user_id = await conn.get_user_id_by_token(db=db, token_type='access', token=access_token)
    if not user_id:
        return JSONResponse(content={"ok": False,
                                     'description': "bad access token or device_id, please login"},
                            status_code=_status.HTTP_401_UNAUTHORIZED)
    await conn.update_user_active(db=db, user_id=user_id[0][0])
    return {"ok": True,
            'user_id': user_id[0][0]}


@app.get(path='/admin_delete_tokens', tags=['Auth'], responses=get_user_id_res)
async def get_user_id_by_token(access_token: str, user_id: int, db=Depends(data_b.connection)):
    """access_token: This is access token. You can get it when create account or login."""
    res = await check_admin(access_token=access_token, db=db)
    if type(res) != int:
        return res
    await conn.delete_old_tokens(db)
    await conn.delete_where(db, table="token", id_name="user_id", data=user_id)

    return JSONResponse(content={"ok": True,
                                 'description': 'Users tokens was deleted'
                                 },
                        status_code=_status.HTTP_200_OK)


@app.get(path='/devices', tags=['Devices'], responses=get_devices_res)
async def get_all_users_device_list(access_token: str, device_id: str, db=Depends(data_b.connection)):
    """refresh_token: This is refresh token, use it for create new access token.
    You can get it when create account or login."""
    user_id = await conn.get_user_id(db=db, token_type='access', token=access_token, device_id=device_id)
    if not user_id:
        return JSONResponse(content={"ok": False,
                                     'description': "bad access token or device_id, please login"},
                            status_code=_status.HTTP_401_UNAUTHORIZED)

    device_dict = {}
    device_data = await conn.read_data(db=db, name='device_id, device_name, create_date', table='token',
                                       id_name='user_id', id_data=user_id[0][0])
    for one in device_data:
        if one[0] in device_dict.keys():
            old_date = device_dict[one[0]][2]
            if one[2] > old_date:
                device_dict[one[0]] = [one[0], one[1], one[2]]
        else:
            device_dict[one[0]] = [one[0], one[1], one[2]]

    device_list = []
    for one in device_dict.keys():
        device_list.append({
            'name': device_dict[one][1],
            'device_id': device_dict[one][0],
            'last_date': device_dict[one][2]
        })
    return {"ok": True,
            'devices': device_list}


@app.delete(path='/device', tags=['Devices'], responses=access_token_res)
async def delete_device(access_token: str, device_id: str, delete_device_id: str, db=Depends(data_b.connection)):
    """refresh_token: This is refresh token, use it for create new access token.
    You can get it when create account or login."""
    user_id = await conn.get_user_id(db=db, token_type='access', token=access_token, device_id=device_id)
    if not user_id:
        return JSONResponse(content={"ok": False,
                                     'description': "bad access token or device_id, please login"},
                            status_code=_status.HTTP_401_UNAUTHORIZED)

    await conn.delete_where(db=db, table='token', id_name='device_id', data=delete_device_id)
    await conn.delete_where(db=db, table='sms_code', id_name='device_id', data=delete_device_id)
    return {"ok": True,
            'description': 'Device was deleted'}


@app.get(path='/log_out', tags=['Auth'], responses=get_logout_res)
async def login_user(access_token: str, device_id: str, app_name: str, db=Depends(data_b.connection)):
    user_id = await conn.get_user_id(db=db, token_type='access', token=access_token, device_id=device_id)
    if not user_id:
        return JSONResponse(content={"ok": False,
                                     'description': "bad refresh token or device_id, please login"},
                            status_code=_status.HTTP_401_UNAUTHORIZED)
    await conn.delete_old_tokens(db)
    await conn.delete_all_tokens_with_device_id(db=db, device_id=device_id, user_id=user_id[0][0], app_name=app_name)
    return JSONResponse(content={"ok": True,
                                 'description': 'You successful logout'
                                 },
                        status_code=_status.HTTP_200_OK)


@app.post(path='/check_sms', tags=['Auth'], responses=post_create_account_res)
async def check_sms_code(phone: int, sms_code: int, device_id: str, device_name: str, app_name: str,
                         db=Depends(data_b.connection)):
    """Create new account in service with phone number, device_id and device_name"""

    code_date = await conn.check_sms_code(db=db, phone=phone, sms_code=sms_code, device_id=device_id)
    if not code_date:
        return JSONResponse(content={"ok": False,
                                     'description': 'No user with this phone number, device_id or bad sms_cod'},
                            status_code=_status.HTTP_401_UNAUTHORIZED)
    if datetime.datetime.now() - datetime.timedelta(minutes=5) > code_date[0][0]:
        return JSONResponse(content={"ok": False,
                                     'description': 'SMS code is too old'},
                            status_code=_status.HTTP_400_BAD_REQUEST)

    user_data = await conn.read_data(db=db, name='*', table='auth', id_name='phone', id_data=phone)
    if user_data:
        user_id = user_data[0][0]
        await conn.delete_old_tokens(db)
        await conn.delete_all_tokens_with_device_id(db=db, device_id=device_id, user_id=user_id, app_name=app_name)

        access = (await conn.create_token(db=db, user_id=user_id, token_type='access', device_id=device_id,
                                          device_name=device_name, app_name=app_name))[0][0]
        refresh = (await conn.create_token(db=db, user_id=user_id, token_type='refresh', device_id=device_id,
                                           device_name=device_name, app_name=app_name))[0][0]
    else:
        user_id = 0
        access = '0'
        refresh = '0'

    return JSONResponse(content={"ok": True,
                                 'user_id': user_id,
                                 'access_token': access,
                                 'refresh_token': refresh
                                 },
                        status_code=_status.HTTP_200_OK)


@app.post(path='/login', tags=['Worker Auth'], responses=post_create_account_res)
async def login_worker(login: str, password: str, device_id: str, device_name: str, app_name: str,
                       db=Depends(data_b.connection)):
    """Login worker in service with login, password, device_id and device_name"""

    user_date = await conn.read_data(db=db, table="auth", id_name="login", id_data=login)
    if not user_date:
        return JSONResponse(content={"ok": False,
                                     'description': 'No user with this login and password'},
                            status_code=_status.HTTP_401_UNAUTHORIZED)

    status = check_password(input_password=password, stored_hashed_password=user_date[0]["hash_code"])

    if not status:
        return JSONResponse(content={"ok": False,
                                     'description': 'No user with this login and password'},
                            status_code=_status.HTTP_401_UNAUTHORIZED)
    user_id = user_date[0][0]
    await conn.delete_old_tokens(db)
    await conn.delete_all_tokens_with_device_id(db=db, device_id=device_id, user_id=user_id, app_name=app_name)

    access = (await conn.create_token(db=db, user_id=user_id, token_type='access', device_id=device_id,
                                      device_name=device_name, app_name=app_name))[0][0]
    refresh = (await conn.create_token(db=db, user_id=user_id, token_type='refresh', device_id=device_id,
                                       device_name=device_name, app_name=app_name))[0][0]
    await conn.update_user_active(db=db, user_id=user_id)
    return JSONResponse(content={"ok": True,
                                 'user_id': user_id,
                                 'access_token': access,
                                 'refresh_token': refresh
                                 },
                        status_code=_status.HTTP_200_OK)


@app.post(path='/create_account', tags=['Auth'], responses=post_create_account_res)
async def create_account_user(phone: int, device_id: str, device_name: str, app_name: str,
                              db=Depends(data_b.connection)):
    """Create new account in service with phone number, device_id and device_name"""

    user_data = await conn.read_data(db=db, name='*', table='auth', id_name='phone', id_data=phone)
    if user_data:
        return JSONResponse(content={"ok": False,
                                     'description': 'Have user with this phone number please login'},
                            status_code=_status.HTTP_400_BAD_REQUEST)

    user_id = (await conn.create_user_id(db=db, phone=phone))[0][0]

    access = await conn.create_token(db=db, user_id=user_id, token_type='access', device_id=device_id,
                                     device_name=device_name, app_name=app_name)
    refresh = await conn.create_token(db=db, user_id=user_id, token_type='refresh', device_id=device_id,
                                      device_name=device_name, app_name=app_name)

    return JSONResponse(content={"ok": True,
                                 'user_id': user_id,
                                 'access_token': access[0][0],
                                 'refresh_token': refresh[0][0]
                                 },
                        status_code=_status.HTTP_200_OK)


@app.post(path='/create_account_login', tags=['Admin Auth'], responses=post_create_account_res)
async def create_account_user_with_login(login: str, password: str, app_name: str, owner_id: int = 0,
                                         db=Depends(data_b.connection)):
    """Create new worker account in service with login and password"""

    user_data = await conn.read_data(db=db, name='*', table='auth', id_name='login', id_data=login)
    if user_data:
        return JSONResponse(content={"ok": False,
                                     'description': 'Have user with this login please login'},
                            status_code=_status.HTTP_400_BAD_REQUEST)

    if owner_id != 0:
        await conn.update_user_id_login(db=db, login=login, password=password, user_id=owner_id)
        user_id = owner_id
    else:
        user_id = (await conn.create_user_id_login(db=db, login=login, password=password))[0][0]

    access = await conn.create_token(db=db, user_id=user_id, token_type='access', device_id="no",
                                     device_name="no", app_name=app_name)
    refresh = await conn.create_token(db=db, user_id=user_id, token_type='refresh', device_id="no",
                                      device_name="no", app_name=app_name)

    return JSONResponse(content={"ok": True,
                                 'user_id': user_id,
                                 'access_token': access[0][0],
                                 'refresh_token': refresh[0][0]
                                 },
                        status_code=_status.HTTP_200_OK)


@app.post(path='/change_password', tags=['Admin Auth'], responses=post_create_account_res)
async def change_password_for_worker(access_token: str, login: str, password: str, app_name: str,
                                     db=Depends(data_b.connection)):
    """Create new account in service with phone number, device_id and device_name"""
    res = await check_admin(access_token=access_token, db=db)
    if type(res) != int:
        return res

    user_data = await conn.read_data(db=db, name='*', table='auth', id_name='login', id_data=login)
    if not user_data:
        return JSONResponse(content={"ok": False,
                                     'description': "Haven't user with this login please check login"},
                            status_code=_status.HTTP_400_BAD_REQUEST)
    user_id = user_data[0][0]
    hash_code = hash_password(password=password)
    await conn.update_inform(db=db, table="auth", name="hash_code", data=hash_code, id_name="user_id", id_data=user_id)
    access = await conn.create_token(db=db, user_id=user_id, token_type='access', device_id="no",
                                     device_name="no", app_name=app_name)
    refresh = await conn.create_token(db=db, user_id=user_id, token_type='refresh', device_id="no",
                                      device_name="no", app_name=app_name)

    return JSONResponse(content={"ok": True,
                                 'user_id': user_id,
                                 'access_token': access[0][0],
                                 'refresh_token': refresh[0][0]
                                 },
                        status_code=_status.HTTP_200_OK)


@app.get(path='/check_phone', tags=['Auth'], responses=check_phone_res)
async def check_phone(phone: int, db=Depends(data_b.connection), ):
    """You can check if such a phone number is in the database. Phone number is unique\n
    phone: int phone for check it in db"""

    user_data = await conn.read_data(db=db, name='*', table='auth', id_name='phone', id_data=phone)
    if not user_data:
        return JSONResponse(content={"ok": True,
                                     'description': 'This phone is not in database', },
                            status_code=_status.HTTP_200_OK,
                            headers={'content-type': 'application/json; charset=utf-8'})
    return JSONResponse(content={"ok": False,
                                 'description': 'This phone is in database', },
                        status_code=_status.HTTP_400_BAD_REQUEST)


@app.get(path='/check_login', tags=['Admin Auth'], responses=check_phone_res)
async def check_login_in_db(login: str, db=Depends(data_b.connection), ):
    """You can check if such a login is in the database. Login is unique\n
    login: str login for check it in db"""

    user_data = await conn.read_data(db=db, name='*', table='auth', id_name='login', id_data=login)
    if not user_data:
        return JSONResponse(content={"ok": True,
                                     'description': 'This login is not in database', },
                            status_code=_status.HTTP_200_OK,
                            headers={'content-type': 'application/json; charset=utf-8'})
    return JSONResponse(content={"ok": False,
                                 'description': 'This login is in database', },
                        status_code=_status.HTTP_400_BAD_REQUEST)


@app.get(path='/create_code', tags=['Auth'], responses=get_create_code_res)
async def send_sms_code_to_phone(phone: int, device_id: str, db=Depends(data_b.connection), ):
    """Here you can send sms code to your phone number\n
    phone: int phone for check it in db"""
    code: int = random.randrange(1009, 9999)
    if str(phone).startswith("3"):
        code = 1111
    else:
        send_sms_code(check_code=code, phone=phone)
    await conn.delete_where(db=db, table='sms_code', id_name='phone', data=phone)
    data = await conn.save_sms_code(db=db, phone=phone, code=code, device_id=device_id)
    if data:
        return JSONResponse(content={"ok": True,
                                     'description': 'Check your phone number', },
                            status_code=_status.HTTP_200_OK,
                            headers={'content-type': 'application/json; charset=utf-8'})
    else:
        return JSONResponse(content={"ok": False,
                                     'description': 'Cant create, write to the admin.', },
                            status_code=_status.HTTP_400_BAD_REQUEST00_OK,
                            headers={'content-type': 'application/json; charset=utf-8'})


async def check_admin(access_token: str, db: Depends):
    """Check services access token for admin"""
    _user_id = await conn.get_user_id_by_token(db=db, token_type='access', token=access_token)
    if not _user_id:
        return JSONResponse(content={"ok": False,
                                     'description': "bad access token or device_id, please login"},
                            status_code=_status.HTTP_401_UNAUTHORIZED)

    user_data = await conn.read_data(db=db, table='users', id_name='user_id', id_data=_user_id[0]["user_id"])

    if user_data[0]["user_type"] != 'admin':
        return JSONResponse(content={"ok": False,
                                     'description': "Not enough rights"},
                            status_code=500)
    return _user_id[0]["user_id"]
