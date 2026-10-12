"""Deterministic ranking of visible floor/low replacement estimates."""
from api.inventory_models import InventoryAssessment
from api.dispatch_models import LiftItem

def rank_lift_first(inventory: InventoryAssessment) -> tuple[LiftItem,...]:
    eligible=[(index,item) for index,item in enumerate(inventory.items) if item.height in ('floor','low')]
    eligible.sort(key=lambda pair:(-(pair[1].qty*pair[1].est_unit_value_rm/pair[1].lift_effort),
                                   pair[1].name.casefold(),pair[1].timestamp_s,pair[0]))
    return tuple(LiftItem(item_name=item.name,qty=item.qty,value_rm=round(item.qty*item.est_unit_value_rm,2),
                          lift_effort=item.lift_effort) for _,item in eligible[:8])
