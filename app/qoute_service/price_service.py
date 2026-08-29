import os
import csv
import difflib
import re
import logging

logger = logging.getLogger(__name__)

PRICE_DB = "data/material_prices.csv"

# Global state
_price_cache = {} 
_db_loaded = False 

def extract_numbers(text: str) -> set:
    """Helper function to extract all numbers (including decimals) from a string."""
    return set(re.findall(r'\d*\.?\d+', text))

def load_price_db(force_reload: bool = False):
    """
    Loads the CSV into memory. 
    Use force_reload=True to refresh the cache from disk.
    """
    global _price_cache, _db_loaded
    
    if _db_loaded and not force_reload:
        return

    # Clear old cache if we are forcing a reload
    if force_reload:
        _price_cache.clear()
        logger.info("Refreshing price database from disk...")

    _db_loaded = True 
    
    if not os.path.exists(PRICE_DB):
        logger.warning(f"PRICE DATABASE NOT FOUND: {PRICE_DB}")
        return

    try:
        with open(PRICE_DB, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Use .get() with defaults to avoid KeyErrors
                name = row.get("item")
                price_str = row.get("price")
                
                if name and price_str:
                    item_name = str(name).strip().lower()
                    try:
                        _price_cache[item_name] = float(price_str)
                    except ValueError:
                        continue
                        
        logger.info(f"Successfully cached {len(_price_cache)} items.")
        
    except Exception as e:
        logger.error(f"Failed to read price database: {e}")

def get_price(item_name: str) -> float | None:
    """Fetches price with exact match -> dimension-safe fuzzy matching."""
    
    if not _db_loaded:
        load_price_db()
        
    if not _price_cache:
        return None
        
    clean_name = str(item_name).strip().lower()
    
    # 1. Exact Match (O(1) - Fast)
    if clean_name in _price_cache:
        return _price_cache[clean_name]
        
    # 2. Fuzzy Match
    # Limit the search space to the first 1000 keys if DB is massive for performance
    search_targets = list(_price_cache.keys())
    
    possible_matches = difflib.get_close_matches(
        clean_name, 
        search_targets, 
        n=5, 
        cutoff=0.7 # Slightly lower cutoff to catch more variations
    )
    
    if possible_matches:
        entry_numbers = extract_numbers(clean_name)
        
        for match in possible_matches:
            match_numbers = extract_numbers(match)
            # 🛡️ THE SAFETY SHIELD: Numbers must match exactly
            if entry_numbers == match_numbers:
                logger.info(f"Fuzzy Match: '{clean_name}' -> '{match}'")
                return _price_cache[match]
        
        logger.info(f"Rejected matches for '{clean_name}' due to number/dimension difference.")
        
    return None