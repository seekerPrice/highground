"""Only new static waste strings; committed Danger text stays fixed."""
import json
from pathlib import Path
from api.i18n import LANGUAGES,catalog,placeholders


def test_waste_catalog_keysets_buttons_and_unreviewed_provenance():
    source=catalog('en');keys={key for key in source if key.startswith('waste_')}
    assert len(keys)==8
    for language in LANGUAGES:
        localized=catalog(language)
        assert {k for k in localized if k.startswith('waste_')}==keys
        for key in keys:
            assert placeholders(localized[key])==placeholders(source[key])
            assert len(localized[key])<=1500
            if key.endswith('_button'):assert len(localized[key])<=64
        if language!='en':assert localized['_reviewed'] is False
