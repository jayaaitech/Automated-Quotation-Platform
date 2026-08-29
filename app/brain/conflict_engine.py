import difflib
import re
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def extract_numbers(text: str) -> set:
    """
    Helper function to extract all numbers (including decimals) from a string.
    Returns a set of strings to allow for easy comparison regardless of order.
    Example: "10mm bolt pack of 5" -> {"10", "5"}
    """
    # Regex explanation: \d* matches zero or more digits, \.? matches an optional decimal, 
    # \d+ matches one or more digits. This captures "10", "1.5", and ".25".
    return set(re.findall(r'\d*\.?\d+', text))


def detect_conflicts(all_extracted_items: list[dict]) -> dict:
    """
    Cross-references items from multiple files to find quantity mismatches.
    Includes safety checks to prevent merging items with different dimensions.
    """
    
    # defaultdict automatically initializes an empty list for any new key we add
    grouped_entities = defaultdict(list)
    
    # Acts as our single source of truth for established item names
    canonical_names = []

    # ==========================================
    # PHASE 1: SMART GROUPING & FUZZY MATCHING
    # ==========================================
    for entry in all_extracted_items:
        # Standardize string for comparison
        raw_name = str(entry["item"]).strip().lower()
        entry_numbers = extract_numbers(raw_name)
        
        # 1. Find potential fuzzy matches (at least 75% similarity) from already known items
        potential_matches = difflib.get_close_matches(raw_name, canonical_names, n=3, cutoff=0.75)
        
        # Assume the item is entirely new until proven otherwise
        canonical_name = raw_name 
        
        # 2. Safety Check: Only accept a fuzzy match if the extracted numbers match perfectly!
        # Why? "10mm steel pipe" and "12mm steel pipe" are 90% textually similar, 
        # but they are fundamentally different parts. This prevents disastrous merges.
        for match in potential_matches:
            match_numbers = extract_numbers(match)
            if entry_numbers == match_numbers:
                canonical_name = match # Safe to merge!
                break
        
        # If the item survived the checks and is truly new, register it as a known standard
        if canonical_name == raw_name and raw_name not in canonical_names:
            canonical_names.append(raw_name)

        # Append the quantity and source to our grouped list under the standardized name
        grouped_entities[canonical_name].append({
            "quantity": entry.get("quantity", 1),
            "source": entry.get("source", "Unknown")
        })

    conflict_report = []
    full_matrix = []

    # ==========================================
    # PHASE 2: AGGREGATION & CONFLICT DETECTION
    # ==========================================
    for entity, mentions in grouped_entities.items():
        
        # 3. Safely aggregate quantities from the SAME source
        # Example: If 'Doc A' lists "Valve: 2" on page 1 and "Valves: 3" on page 5,
        # we need to sum them to a total of 5 for 'Doc A' before comparing against 'Doc B'.
        source_totals = defaultdict(int)
        
        for m in mentions:
            # Defensive programming: Ensure quantity is a number, not a string, 
            # so `+=` does math (1+1=2) instead of string concatenation ("1"+"1"="11").
            try:
                # Handle both floats (1.5) and ints (5) seamlessly
                qty = float(m["quantity"]) if '.' in str(m["quantity"]) else int(m["quantity"])
            except ValueError:
                # Fallback if a parser accidentally grabbed a word like "TBD" as the quantity
                qty = 1 
                
            source_totals[m["source"]] += qty

        # Convert back to a standard dictionary so it can be safely sent as JSON to the frontend
        source_breakdown = dict(source_totals)

        # 4. Check for conflicts: Are there multiple DIFFERENT quantity totals across sources?
        # Creating a set of the values leaves us with only the unique numbers.
        # Example: {"Doc A": 5, "Doc B": 5} -> set yields {5}. Length is 1 (No conflict).
        # Example: {"Doc A": 5, "Doc B": 4} -> set yields {5, 4}. Length is 2 (Conflict!).
        unique_quantities = set(source_breakdown.values())
        
        # A conflict requires two conditions to be met:
        # A) The item exists in more than 1 document.
        # B) The documents disagree on the total number required.
        has_conflict = len(source_breakdown) > 1 and len(unique_quantities) > 1

        record = {
            "entity": entity.title(), # Capitalize for clean frontend UI presentation
            "sources_found": list(source_breakdown.keys()),
            "quantities": source_breakdown,
            "conflict_detected": has_conflict
        }

        # If they disagree, log it to the dedicated conflict report array
        if has_conflict:
            conflict_report.append(record)

        # Always add it to the full matrix for complete tracking
        full_matrix.append(record)

    # 5. Return the final structured payload
    return {
        "total_entities_checked": len(full_matrix),
        "conflicts_found": len(conflict_report),
        "conflict_details": conflict_report,
        "full_matrix": full_matrix
    }