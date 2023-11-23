import bcrypt
import secrets


def generate_salt():
    salt = secrets.token_hex(16)
    return salt


def hash_password(password: str,):
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt=salt,)
    return hashed_password.decode('utf-8')


def check_password(input_password: str, stored_hashed_password: str,) -> bool:
    hashed_input_password = bcrypt.checkpw(input_password.encode('utf-8'), stored_hashed_password.encode('utf-8'))
    return hashed_input_password
