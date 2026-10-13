from datetime import UTC,datetime
from io import BytesIO
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from PIL import Image
from api.offline_card import CardContext,CardChoice,card_text
from api.card_renderer import render_offline_card,wrap,runs
from api.dispatch_models import LiftItem


def context(**changes):
    values=dict(card_id='a'*64,shop_id='synthetic',shop_name='Synthetic shop',language='en',lat=3.,lng=101.,prepared_at=datetime.now(UTC),is_demo=True,inventory_id='frozen-inventory',items=(LiftItem(item_name='Rice bags',qty=2.,value_rm=20.,lift_effort=1),),displayed_value_rm=20.)
    return CardContext(**(values|changes))


def test_card_uses_only_displayed_frozen_item_value_and_no_invented_destination():
    card=context();words=card_text(card)
    assert 'Rice bags' in '\n'.join(words.lift_lines) and 'RM20.00' in '\n'.join(words.lift_lines)
    assert 'No listed parking' in words.parking_line and 'No listed evacuation' in words.shelter_line
    assert '999' in words.emergency_line and '994' not in words.emergency_line
    with pytest.raises(ValidationError):context(displayed_value_rm=999.)
    with pytest.raises(ValidationError):CardChoice.model_validate({'title':'Invented advice','footer':'card_footer'})
    missing=card_text(context(items=(),inventory_id=None,displayed_value_rm=0.))
    assert 'unavailable' in missing.lift_lines[0] and 'RM0' not in missing.lift_lines[0]


def test_render_decodes_as_portrait_png_and_fails_clearly_without_shaping():
    card=context();data=render_offline_card(card,card_text(card))
    image=Image.open(BytesIO(data));image.load()
    assert image.format=='PNG' and image.size==(1080,1920) and len(data)<10_000_000
    assert image.getbbox()==(0,0,1080,1920) and len(image.getcolors(1080*1920))>50
    with patch('api.card_renderer.features.check',return_value=False),pytest.raises(ValueError,match='RAQM'):render_offline_card(card,card_text(card))


def test_complex_clusters_wrap_without_splitting_and_missing_glyph_fails():
    value='क्षत्रियक्षत्रियक्षत्रिय'
    lines=wrap(value,'ne',36,150)
    assert ''.join(lines)==value
    assert all(not line.startswith(('्','ि','ी')) for line in lines)
    with pytest.raises(ValueError,match='glyph'):runs('\U0010ffff','en',32)
