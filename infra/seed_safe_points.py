"""Seed inspected historical listings locally; never change events or shop records."""
import json
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.config import load_settings
from api.destinations import SafePoint
from api.tools.emulators import loopback_endpoint
from api.tools.firestore import create_firestore_client


def run() -> None:
    host = os.environ.get('FIRESTORE_EMULATOR_HOST')
    if not host:
        raise ValueError('Hosting is deferred; set an explicit loopback Firestore emulator')
    loopback_endpoint(host)
    settings = load_settings()
    points = [SafePoint.model_validate(row) for row in json.loads((Path(__file__).parent/'data/safe_points.json').read_text())]
    client = create_firestore_client(settings)
    try:
        for point in points:
            # Explicit operator seed replaces only these two known registry records.
            client.collection('safe_points').document(point.safe_point_id).set(point.model_dump())
    finally:
        client.close()
    print(f'Seeded {len(points)} historical listings; current opening and parking floor remain unknown.')


if __name__ == '__main__':
    run()
