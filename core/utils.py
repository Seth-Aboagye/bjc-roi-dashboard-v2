import pandas as pd
import numpy as np

def normalize_columns(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    """
    Normalize raw uploads into the canonical schema the app expects.

    Donations canonical fields:
      - date, amount, donor_id, campaign_code, channel
      - plus optional extras if present: contribution_id, contact_name, designation,
        payment_method, remaining_amount, financial_batch

    Costs canonical fields:
      - date, cost_amount, campaign_code, channel, cost_type, notes
    """
    df = df.copy()

    # Keep original columns but build a normalized lookup (lower/trim)
    original_cols = list(df.columns)
    norm_cols = [str(c).strip().lower() for c in original_cols]
    df.columns = norm_cols  # work in normalized space

    if kind == "donations":
        aliases = {
            # Required/canonical
            "date": [
                "date", "giftdate", "contributiondate", "transactiondate", "receiveddate",
                "date received", "date rece"
            ],
            "amount": [
                "amount", "contributionamount", "giftamount", "total"
            ],
            "donor_id": [
                "donor_id", "vanid", "personid", "donorid", "contactid", "id"
            ],
            "campaign_code": [
                "campaign_code", "appealcode", "campaign", "sourcecode", "fundraisingcode",
                "appeal", "source code", "source co"
            ],
            # Practical default: treat Payment Method as channel if that's what you have
            "channel": [
                "channel", "source", "medium", "fundraisingsource",
                "payment method", "payment m"
            ],

            # Optional extras (kept if present)
            "contribution_id": ["contribution id", "contributi", "contributionid"],
            "contact_name": ["contact name", "contact n", "contactname"],
            "designation": ["designation", "designati"],
            "payment_method": ["payment method", "payment m", "paymentmethod"],
            "remaining_amount": ["remaining amount", "remaining", "remainingamount"],
            "financial_batch": ["financial batch", "financialbatch"],
        }
    else:
        aliases = {
            "date": ["date", "expensedate", "paiddate", "transactiondate"],
            "cost_amount": ["cost_amount", "amount", "expense", "cost", "total"],
            "campaign_code": ["campaign_code", "appealcode", "campaign", "sourcecode", "fundraisingcode", "appeal"],
            "channel": ["channel", "source", "medium"],
            "cost_type": ["cost_type", "type", "category"],
            "notes": ["notes", "memo", "description"],
        }

    def find_col(target: str):
        """Return the first matching source column name (already normalized), or None."""
        for c in aliases.get(target, []):
            c_norm = str(c).strip().lower()
            if c_norm in df.columns:
                return c_norm
        return None

    out = pd.DataFrame()

    # Build required outputs first
    for target in aliases:
        col = find_col(target)
        out[target] = df[col] if col else np.nan

    # Defaults
    if kind == "donations":
        out["campaign_code"] = out["campaign_code"].fillna("UNMAPPED")
        out["channel"] = out["channel"].fillna("UNMAPPED")

        # If payment_method exists but channel is UNMAPPED, populate channel from payment_method
        if "payment_method" in out.columns:
            mask = out["channel"].isna() | (out["channel"].astype(str).str.strip() == "") | (out["channel"] == "UNMAPPED")
            out.loc[mask, "channel"] = out.loc[mask, "payment_method"]

        # Keep the optional columns if present; otherwise leave them as-is (NaN)
        # (They are already in out if in aliases)

    else:
        out["campaign_code"] = out["campaign_code"].fillna("UNMAPPED")
        out["channel"] = out["channel"].fillna("UNMAPPED")
        out["cost_type"] = out["cost_type"].fillna("Direct")
        out["notes"] = out["notes"].fillna("")

    return out


def ensure_datetime(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df = df.copy()
    df[col] = pd.to_datetime(df[col], errors="coerce")
    df = df.dropna(subset=[col])
    return df


def month_floor(dt) -> str:
    return pd.to_datetime(dt).strftime("%Y-%m")


def segment_donors_basic(d: pd.DataFrame) -> pd.DataFrame:
    """
    Default segmentation:
    - New = first donation by donor_id within the uploaded dataset
    - Returning = otherwise
    (You can replace with a true 'prior-year retention' model later.)
    """
    d = d.copy()
    d = d.sort_values(["donor_id", "date"])
    first = d.groupby("donor_id")["date"].transform("min")
    d["donor_segment"] = (d["date"] == first).map({True: "New", False: "Returning"})
    return d


def safe_div(a: float, b: float) -> float:
    return float(a) / float(b) if b not in (0, None) else 0.0