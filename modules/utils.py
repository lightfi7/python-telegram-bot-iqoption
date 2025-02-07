import re
from Crypto import Random
from Crypto.Cipher import AES

key = b'7f24a1b5c9d2f4e6'
iv = Random.new().read(AES.block_size)


def is_hex(s):
    try:
        bytes.fromhex(s)
        return True
    except ValueError:
        return False


def is_number(str):
    return str.isdigit()


def is_valid_email(email):
    regex = r'^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w+$'
    if re.match(regex, email):
        return True
    else:
        return False


def generate_key(v):
    cipher = AES.new(key, AES.MODE_CFB, iv)
    return ''.join(f'{byte:02X}' for byte in cipher.encrypt(v.encode('utf-8')))


def verify_key(token):
    cipher = AES.new(key, AES.MODE_CFB, iv)
    decrypted_bytes = cipher.decrypt(token)
    return decrypted_bytes.decode('utf-8')
