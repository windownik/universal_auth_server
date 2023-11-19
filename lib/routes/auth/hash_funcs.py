import bcrypt
import secrets


def generate_salt(length=16):
    return secrets.token_hex(length // 2)


def hash_password(password: str, salt: str):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt=salt.encode('utf-8'))

    return hashed_password


def check_password(input_password: str, stored_hashed_password: str, salt: str):
    hashed_input_password = bcrypt.hashpw(input_password.encode('utf-8'), salt.encode('utf-8'))
    return hashed_input_password == stored_hashed_password
