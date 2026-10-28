#!/usr/bin/env python3
"""Repara nombres de organismos en el historico local sin alterar ids ni favoritos."""
import argparse
import json
import os
from pathlib import Path
from shutil import copy2
from scan import entity_from_title


def repair(path: Path) -> int:
    payload = json.loads(path.read_text(encoding='utf-8'))
    notices = payload.get('notices')
    if not isinstance(notices, list):
        raise ValueError('El JSON no contiene la lista notices esperada')
    changes = []
    for record in notices:
        if not isinstance(record, dict) or not record.get('title'):
            continue
        new = entity_from_title(record['title'])
        old = record.get('entity')
        if new != old and not new.startswith('Administración pública (sin identificar)'):
            record['entity'] = new
            changes.append((record.get('id'), old, new))
    if not changes:
        print('No hay organismos que corregir.')
        return 0
    backup = path.with_name(path.name + '.bak')
    if not backup.exists():
        copy2(path, backup)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)
    for id, old, new in changes:
        print(f'{id}: {old} => {new}')
    print(f'Corregidos {len(changes)} organismos. Copia de seguridad: {backup}')
    return len(changes)


if __name__ == '__main__':
    arg = argparse.ArgumentParser()
    arg.add_argument('--file', type=Path, default=Path('data/convocatorias.json'))
    args = arg.parse_args()
    if not args.file.is_file():
        raise SystemExit(f'No existe el archivo {args.file}. No se ha modificado nada.')
    repair(args.file)
