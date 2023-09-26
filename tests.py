import random

import requests

phone_number: int = random.randrange(100000, 9999900)
device_id: str = f"device_id{random.randrange(1000, 9999)}"
device_name: str = f"ANDROID{random.randrange(1000, 9999)}"

user_id = 0
access_token = ''
refresh_token = ''

# phone_number = 6090855
# device_id = 'device_id5012'
# device_name = 'ANDROID2434'


url = 'http://127.0.0.1:8000'

# test_1


def send_sms_code() -> bool:
    params = {
        'phone': phone_number,
        'device_id': device_id
              }
    res = requests.get(url=f'{url}/create_code', params=params)
    return res.status_code == 200


def create_new_account() -> bool:
    # Bad code
    params = {
        'phone': phone_number,
        "sms_code": 1019,
        'device_id': device_id,
        'device_name': device_name
              }
    res = requests.post(url=f'{url}/create_account', params=params)

    if res.status_code != 401:
        return False

    # Good code, and bad Device id
    params = {
        'phone': phone_number,
        "sms_code": 1111,
        'device_id': '123',
        'device_name': device_name
    }
    res = requests.post(url=f'{url}/create_account', params=params)

    if res.status_code != 401:
        return False

    # Good code, and bad Device id
    params = {
        'phone': phone_number,
        "sms_code": 1111,
        'device_id': device_id,
        'device_name': device_name
    }
    res = requests.post(url=f'{url}/create_account', params=params)

    if res.status_code != 200:
        return False

    res = requests.post(url=f'{url}/create_account', params=params)

    if res.status_code != 400:
        return False
    return True


def create_account():
    print("Send sms code:", send_sms_code())
    print("Create new account:", create_new_account())
    print(user_id)


create_account()
