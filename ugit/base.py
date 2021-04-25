import os
import string
from . import data

SPACE = ' '
NEW_LINE = '\n'


def get_oid(name):
    if name == '@':
        name = 'HEAD'

    refs = [
        f'{name}',
        f'refs/{name}',
        f'refs/tags/{name}',
        f'refs/heads/{name}'
    ]

    for r in refs:
        ref = data.get_ref(r)
        if ref:
            return ref

    is_hex = all(c in string.hexdigits for c in name)
    if len(name) == 40 and is_hex:
        return name

    assert False, f'Unknown name {name}'

    return data.get_ref(name) or name


def write_tree(directory='.'):
    entries = []

    with os.scandir(directory) as d:
        for entry in d:
            path = directory + '/' + entry.name
            if is_ignored(path):
                continue
            if entry.is_file(follow_symlinks=False):
                with open(path, 'rb') as f:
                    oid = data.hash_object(f.read(), type_=data.TYPE_BLOB)
                entries.append((entry.name, data.TYPE_BLOB, oid))
            elif entry.is_dir(follow_symlinks=False):
                oid = write_tree(path)
                entries.append((entry.name, data.TYPE_TREE, oid))

    tree_data = ''
    for t, o, n in sorted(entries):
        tree_data += t + SPACE + o + SPACE + n + NEW_LINE

    return data.hash_object(tree_data.encode(), type_=data.TYPE_TREE)


def get_tree(oid, path):
    results = {}
    entries = _get_tree_entries(oid)
    for obj_path, obj_type, obj_oid in entries:
        assert '/' not in obj_path
        assert obj_path not in ('.', '..')
        if obj_type == data.TYPE_BLOB:
            results[path + '/' + obj_path] = obj_oid
        else:
            files = get_tree(obj_oid, path + '/' + obj_path)
            results.update(files)

    return results


def read_tree(tree_oid):
    _empty_current_directory()
    for path, oid in get_tree(tree_oid, '.').items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data.get_object(oid, data.TYPE_BLOB))


def commit(message, author='DEFAULT'):
    commit = f'tree {write_tree()}\n'
    head = data.get_head()
    if head is not None:
        commit += f'parent {data.get_head()}\n'
    commit += f'author {author}\n\n'
    commit += message
    oid = data.hash_object(commit.encode(), type_=data.TYPE_COMMIT)
    data.set_head(oid)
    return oid


def log(oid):
    output = ''

    if oid == '':
        return output

    while oid != '':
        _, parent, author, message = _get_commit(oid)
        output += f'commit {oid}\n'
        output += f'author: {author}\n\n'
        output += f'\t{message}\n\n'
        oid = parent

    return output.strip()


def checkout(oid):
    tree_oid, _, _, _ = _get_commit(oid)
    read_tree(tree_oid)
    data.set_head(oid)


def tag(name, oid=None):
    data.update_ref(f'refs/{name}', oid or data.get_head())


def is_ignored(path):
    ignored = ['.ugit', '.git']
    path = path.split('/')
    for i in ignored:
        if i in path:
            return True
    return False


def _get_tree_entries(oid):
    entries = data.get_object(oid, data.TYPE_TREE).decode()
    for line in entries.splitlines():
        name, type_, oid_ = line.split(SPACE)
        yield name, type_, oid_


def _get_commit(oid):
    commit_data = data.get_object(oid, expected=data.TYPE_COMMIT)
    tree, parent, author, _, message = commit_data.decode().splitlines()

    tree_oid = tree.split(SPACE)[1]
    parent_oid = parent.split(SPACE)[1]
    author = author.split(SPACE)[1]
    return tree_oid, parent_oid, author, message


def _empty_current_directory():
    for root, dirnames, filenames in os.walk('.', topdown=False):
        for filename in filenames:
            path = os.path.relpath(f'{root}/{filename}')
            if is_ignored(path) or not os.path.isfile(path):
                continue
            os.remove(path)
        for dirname in dirnames:
            path = os.path.relpath(f'{root}/{dirname}')
            if is_ignored(path):
                continue
            try:
                os.rmdir(path)
            except (FileNotFoundError, OSError):
                # Deletion might fail if the directory contains ignored files,
                # so it's OK
                pass
