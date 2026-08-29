import logging
from app.qoute_service.price_service import get_price

logger = logging.getLogger(__name__)

def estimate_cost(
    material_cost: float = None, 
    machining_hours: float = None, 
    labor_rate: float = None, 
    boq_items: list[dict] = None
) -> dict:
    """
    Unified cost calculation function with rounding safety.
    """

    # ==========================================
    # 1. BOQ COST MODE
    # ==========================================
    if boq_items is not None:
        total = 0.0
        details = []

        for item in boq_items:
            name = item.get("item", "Unknown Item")
            
            # 🛡️ Cast quantity safely
            try:
                raw_qty = item.get("quantity")
                qty = float(raw_qty) if raw_qty not in [None, ""] else 0.0
            except (ValueError, TypeError):
                qty = 0.0

            # Fetch price from your DB/Cache
            price = get_price(name)

            if price is None:
                logger.warning(f"No price found for '{name}'. Flagging for review.")
                price = 0.0
                price_found = False
            else:
                price_found = True

            # 🛡️ Use rounding to prevent floating point drift
            item_cost = round(price * qty, 2)
            total += item_cost

            details.append({
                "item": name,
                "qty": qty,
                "unit_price": round(price, 2),
                "total": item_cost,
                "price_found": price_found 
            })

        return {
            "items": details,
            "total_material_cost": round(total, 2)
        }

    # ==========================================
    # 2. MANUAL COST MODE
    # ==========================================
    # Ensure all manual parameters are present and are numbers
    params = [material_cost, machining_hours, labor_rate]
    if all(isinstance(p, (int, float)) for p in params):
        
        machining_cost = round(machining_hours * labor_rate, 2)
        base_cost = round(material_cost + machining_cost, 2)

        return {
            "machining_cost": machining_cost,
            "base_cost": base_cost
        }

    # If inputs don't match either mode, raise a clear error
    raise ValueError(
        "Invalid input. Provide 'boq_items' list OR "
        "numerical 'material_cost', 'machining_hours', and 'labor_rate'."
    )