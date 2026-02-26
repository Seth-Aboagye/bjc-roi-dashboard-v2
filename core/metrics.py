import pandas as pd
from core.utils import safe_div

def compute_kpis(donations: pd.DataFrame, costs: pd.DataFrame) -> dict:
    total_raised = float(donations["amount"].fillna(0).sum())
    total_costs = float(costs["cost_amount"].fillna(0).sum())
    net_raised = total_raised - total_costs

    roi = (net_raised / total_costs) if total_costs > 0 else 0.0
    cost_to_raise_1 = safe_div(total_costs, total_raised) if total_raised > 0 else 0.0

    donors = int(donations["donor_id"].nunique()) if len(donations) else 0
    gifts = int(len(donations))
    avg_gift = safe_div(total_raised, gifts) if gifts > 0 else 0.0

    return {
        "total_raised": total_raised,
        "total_costs": total_costs,
        "net_raised": net_raised,
        "roi": roi,
        "cost_to_raise_1": cost_to_raise_1,
        "donors": donors,
        "gifts": gifts,
        "avg_gift": avg_gift,
    }

def compute_rollups(donations: pd.DataFrame, costs: pd.DataFrame, by: str) -> pd.DataFrame:
    raised = donations.groupby(by)["amount"].sum().rename("raised")
    cost = costs.groupby(by)["cost_amount"].sum().rename("costs")
    out = pd.concat([raised, cost], axis=1).fillna(0)
    out["net"] = out["raised"] - out["costs"]
    out["roi"] = out.apply(lambda r: (r["net"] / r["costs"]) if r["costs"] > 0 else 0.0, axis=1)
    out["cost_to_raise_1"] = out.apply(lambda r: (r["costs"] / r["raised"]) if r["raised"] > 0 else 0.0, axis=1)
    return out.reset_index()
