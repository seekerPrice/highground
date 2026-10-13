export interface ExampleItem {
 name: string; qty: number; est_unit_value_rm: number; height: string; lift_effort: number;
 condition: string; estimated_loss_rm: number; uncertainty: string;
}
export interface PublicExample {
 title: string; provenance: string; input_kind: string;
 baseline_confidence: number; assessment_confidence: number;
 baseline_uncertainty: string; assessment_uncertainty: string; items: ExampleItem[];
 assets: {phase: string; path: string; sha256: string; bytes: number}[];
 review_discrepancies: {item: string; generation_brief_qty: number; model_estimated_qty: number}[];
 review_note: string;
}
export const itemValue = (item: ExampleItem) => Math.round(item.qty * item.est_unit_value_rm * 100) / 100;
export function exampleCalculations(items: ExampleItem[]) {
 const ranked = items.filter(item => item.height === "floor" || item.height === "low")
  .map(item => ({...item, value: itemValue(item), score: item.qty * item.est_unit_value_rm / item.lift_effort}))
  .sort((a,b) => b.score-a.score || a.name.toLowerCase().localeCompare(b.name.toLowerCase())).slice(0,8);
 return {ranked, baseline: items.reduce((sum,item) => sum+itemValue(item),0),
  priorityValue: ranked.reduce((sum,item) => sum+item.value,0),
  loss: items.reduce((sum,item) => sum+item.estimated_loss_rm,0), assessed: items.length};
}
