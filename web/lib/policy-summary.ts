import type {PolicyAggregate} from "./contracts.ts";
import {money} from "./client.ts";

/** Present unknown policy scope separately from a genuine quantified zero. */
export function policySummary(value:PolicyAggregate|null){
 if(value===null)return {withoutCover:"Unavailable",stockEstimate:"Unavailable",estimateCoverage:"No policy aggregate is available."};
 return {
  withoutCover:value.without_cover_percent_of_known===null?"Unavailable — no known policy denominator":`${value.without_cover_percent_of_known}% (${value.explicit_no_flood_cover} of ${value.assessed_known_coverage} known policies)`,
  stockEstimate:value.uninsured_stock_estimate_rm===null?"Unavailable":`≈${money(value.uninsured_stock_estimate_rm)}`,
  estimateCoverage:`Quantified frozen estimates for ${value.registered_synthetic_shops-value.unknown_stock_estimates} of ${value.registered_synthetic_shops} synthetic shops; ${value.unknown_stock_estimates} amounts remain unknown.`
 };
}
