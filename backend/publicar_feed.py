#!/usr/bin/env python3
"""Copia al directorio web solo resultados auditados. Conserva feed anterior si falla."""
import argparse
import json
from pathlib import Path
from bop_full import safe_write_json, CoverageError
from validar_feed import validate_feed, FeedValidationError


def publicar(origen: Path, destino: Path, require_history: bool = False):
    content = json.loads(origen.read_text(encoding='utf-8'))
    if not content.get('coverage', {}).get('complete', False):
        raise CoverageError('El ultimo boletin no esta auditado')
    if require_history and not content.get('historyCoverage', {}).get('complete', False):
        raise CoverageError('El historico de fechas no esta auditado')
    if require_history:
        try:
            validate_feed(content)
        except FeedValidationError as exc:
            raise CoverageError('Feed historico incoherente: ' + str(exc)) from exc
    notices = content.get('notices', [])
    if not isinstance(notices, list):
        raise CoverageError('notices debe ser una lista')
    safe_write_json(destino, content)
    return len(notices)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=Path('data/convocatorias.json'))
    parser.add_argument('--output', type=Path, default=Path('docs/convocatorias.json'))
    parser.add_argument('--require-history', action='store_true')
    args = parser.parse_args()
    n = publicar(args.input, args.output, args.require_history)
    print(f'Publicado: {n} fichas -> {args.output}')


if __name__ == '__main__':
    main()
