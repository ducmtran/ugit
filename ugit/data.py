import os
import hashlib

GIT_DIR = '.ugit'
TYPE_BLOB = 'blob'
TYPE_TREE = 'tree'
TYPE_COMMIT = 'commit'

NULL_BYTE = b'\x00'


def init():
    os.makedirs(GIT_DIR)
    os.makedirs(f'{GIT_DIR}/objects')


def hash_object(file, type_=TYPE_BLOB):
    obj = type_.encode() + NULL_BYTE + file
    oid = hashlib.sha1(obj).hexdigest()

    with open(f'{GIT_DIR}/objects/{oid}', 'wb') as f:
        f.write(obj)
    return oid


def get_object(oid, expected=TYPE_BLOB):
    with open(f'{GIT_DIR}/objects/{oid}', 'rb') as f:
        data = f.read()

    type_, content = data.split(NULL_BYTE)
    if expected is not None:
        assert type_.decode() == expected, f'Expected {expected}, got {type_}'

    return content


def set_head(oid):
    update_ref('HEAD', oid)


def get_head():
    return get_ref('HEAD')


def update_ref(ref, oid):
    ref_path = f'{GIT_DIR}/{ref}'
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, 'w') as f:
        f.write(oid)


def get_ref(ref):
    ref_path = f'{GIT_DIR}/{ref}'
    if os.path.isfile(ref_path):
        with open(ref_path) as f:
            return f.read().strip()
