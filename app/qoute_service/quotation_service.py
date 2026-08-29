import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def generate_quote(cost_data: dict, labor_rate: float = 0.15, profit_rate: float = 0.10) -> dict:
    """
    Transforms cost data into a professional quote.
    Calculates labor on materials, and profit on the subtotal.
    """
    try:
        formatted_items = []
        calculated_material_cost = 0.0

        # 1. Process line items
        for item in cost_data.get("items", []):
            try:
                # Ensure we handle various input types safely
                qty = float(item.get("qty", 1))
                total = float(item.get("total", 0.0))
                
                unit_cost = total / qty if qty > 0 else 0.0
                calculated_material_cost += total

                formatted_items.append({
                    "item_name": str(item.get("item", "Unknown Part")),
                    "quantity": qty,
                    "unit_cost": round(unit_cost, 2),
                    "total_cost": round(total, 2),
                    "verified": item.get("price_found", False) # Pass through the warning flag
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed item: {item}. Error: {e}")

        # 2. Material Subtotal
        material_cost = float(cost_data.get("total_material_cost", calculated_material_cost))

        # 3. Apply Multi-Step Business Logic
        # Labor is usually a percentage of material handling/install
        labor_cost = round(material_cost * labor_rate, 2)
        
        # Subtotal includes materials and the work to handle them
        subtotal = material_cost + labor_cost
        
        # Profit is applied to the entire cost of doing business
        profit_amount = round(subtotal * profit_rate, 2)
        
        final_total = round(subtotal + profit_amount, 2)

        # 4. Return Structured Response
        return {
            "metadata": {
                "quote_id": f"RFQ-{uuid.uuid4().hex[:8].upper()}", # Unique tracking ID
                "generated_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                "currency": "USD",
                "status": "DRAFT",
                "version": "1.0"
            },
            "line_items": formatted_items,
            "summary": {
                "material_subtotal": round(material_cost, 2),
                "labor_cost": labor_cost,
                "profit_markup": profit_amount,
                "total_quote": final_total,
                "tax_estimate": round(final_total * 0.05, 2) # Adding a 5% placeholder for tax
            }
        }

    except Exception as e:
        logger.error(f"❌ Quote generation failed: {e}", exc_info=True)
        return {
            "error": "Failed to generate quotation",
            "status": "error"
        }