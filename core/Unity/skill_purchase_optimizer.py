import json
import os
import sys
from difflib import SequenceMatcher
from core.Unity.skill_recognizer import scan_all_skills_with_scroll, deduplicate_skills
from utils.core.log import log_debug, log_info, log_warning, log_error
from utils.core.config_loader import load_main_config

# Fix Windows console encoding for Unicode support
if os.name == 'nt':  # Windows
    try:
        # Set console to UTF-8 mode
        os.system('chcp 65001 > nul')
        # Also try to set stdout encoding
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# debug_print is imported from utils.core.log

def load_skill_config(config_path=None):
    """
    Load skill configuration from JSON file.
    
    Args:
        config_path: Path to skills config file. If None, loads from config.json's skill_file setting.
    
    Returns:
        dict: Configuration with skill_priority and gold_skill_upgrades
    """
    # If no config_path provided, try to load from config.json
    if config_path is None:
        try:
            main_config = load_main_config()
            skills_config = main_config.get("skills", {})
            config_path = skills_config.get("skill_file", "template/skills/skills.json")
            log_debug(f"Loading skills from config file: {config_path}")
        except Exception as e:
            log_debug(f"Could not read config.json, using default template/skills/skills.json: {e}")
            config_path = "template/skills/skills.json"

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    config_path = _resolve_skill_path(config_path, project_root)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            log_debug(f"Successfully loaded skills config from: {config_path}")
            return config
    except FileNotFoundError:
        log_error(f"{config_path} not found. Creating default config")
        default_config = {
            "skill_priority": [],
            "gold_skill_upgrades": {}
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        return default_config
    except Exception as e:
        log_error(f"Error loading {config_path}: {e}")
        return {"skill_priority": [], "gold_skill_upgrades": {}}

def _resolve_skill_path(config_path, project_root):
    """Resolve skill config path, preferring files inside skills/."""
    if not config_path:
        return config_path
    if os.path.isabs(config_path):
        return config_path
    normalized = config_path.replace("\\", "/")
    candidates = [normalized]
    base_name = os.path.basename(normalized)
    if not normalized.startswith("template/skills/"):
        candidates.append(os.path.join("template", "skills", base_name))
    for candidate in candidates:
        absolute = os.path.join(project_root, candidate)
        if os.path.exists(absolute):
            return absolute
    return os.path.join(project_root, candidates[-1])

def clean_ocr_text(text):
    """
    Clean OCR text by removing common artifacts and normalizing.
    
    Args:
        text: Raw OCR text
    
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = ' '.join(text.split())
    return text.strip()

def _normalize(text):
    """Lowercase and strip punctuation/extra spaces for comparison."""
    if not text:
        return ""
    import re
    normalized = re.sub(r"[^\w\s]", "", text.lower())
    return " ".join(normalized.split())


def find_best_real_skill_match(ocr_skill_name, target_skill_name=None, threshold=0.85):
    """
    Lightweight matcher that compares OCR text directly to the target skill name.
    No external skill database is used.
    """
    clean_ocr = clean_ocr_text(ocr_skill_name).lower().strip()
    if not clean_ocr:
        return {
            'match': None,
            'confidence': 0.0,
            'exact_match': False,
            'is_target_match': False
        }
    
    if target_skill_name:
        target_clean = target_skill_name.lower().strip()
        similarity = SequenceMatcher(None, clean_ocr, target_clean).ratio()
        exact = clean_ocr == target_clean
        is_target = similarity >= threshold
        return {
            'match': target_skill_name if is_target else None,
            'confidence': similarity,
            'exact_match': exact,
            'is_target_match': is_target
        }
    
    # No target provided; return the cleaned OCR text as best effort
    return {
        'match': clean_ocr,
        'confidence': 1.0,
        'exact_match': True,
        'is_target_match': False
    }

def fuzzy_match_skill_name(skill_name, target_name, threshold=0.9):
    """
    Check if two skill names match directly using string similarity (no DB lookup).
    """
    if not skill_name or not target_name:
        return False
    similarity = SequenceMatcher(None, _normalize(skill_name), _normalize(target_name)).ratio()
    return similarity >= threshold

def find_matching_skill(skill_name, available_skills, excluded_skills=None):
    """
    Find a skill in available_skills that matches skill_name using precise real skill matching.
    
    Args:
        skill_name: Name to search for (from user config)
        available_skills: List of available skill dicts (from OCR)
        excluded_skills: Set of skill names (from OCR) that have already been matched and should be skipped
    
    Returns:
        dict or None: Matching skill dict, or None if not found
    """
    if excluded_skills is None:
        excluded_skills = set()
    
    # Try exact match first
    skill_name_clean = skill_name.lower().strip()
    for skill in available_skills:
        if skill['name'].lower().strip() == skill_name_clean:
            # Check if this skill is already matched
            if skill['name'] not in excluded_skills:
                log_debug(f"Exact match found: '{skill['name']}' matches '{skill_name}'")
                return skill
    
    # Use direct fuzzy matching against available skills (no DB)
    best_skill = None
    best_confidence = 0.0
    
    for skill in available_skills:
        # Skip skills that have already been matched
        if skill['name'] in excluded_skills:
            continue
            
        similarity = SequenceMatcher(None, _normalize(skill.get('name', '')), _normalize(skill_name)).ratio()
        if similarity >= 0.9 and similarity > best_confidence:
            best_skill = skill
            best_confidence = similarity
            log_debug(f"Match: '{skill['name']}' matches target '{skill_name}' (confidence: {similarity:.3f})")
    
    if best_skill:
        log_debug(f"Best match found: '{best_skill['name']}' for target '{skill_name}' (confidence: {best_confidence:.3f})")
        return best_skill
    
    log_debug(f"No match found for '{skill_name}' in available skills")
    return None

def _skill_price(skill, default=999999):
    """Return numeric skill price for planning sort order."""
    price = skill.get('price', default)
    if isinstance(price, int):
        return price
    if isinstance(price, str) and price.isdigit():
        return int(price)
    return default

def _reorder_end_career_gold_first(purchase_plan, gold_upgrades):
    """Move configured gold skills ahead of regular priority and fallback skills."""
    if not purchase_plan or not gold_upgrades:
        return purchase_plan

    reordered = []
    used_indexes = set()
    for gold_skill_name in gold_upgrades:
        for index, skill in enumerate(purchase_plan):
            if index in used_indexes:
                continue
            if fuzzy_match_skill_name(skill.get('name', ''), gold_skill_name):
                reordered.append(skill)
                used_indexes.add(index)
                break

    if not reordered:
        return purchase_plan

    reordered.extend(
        skill for index, skill in enumerate(purchase_plan)
        if index not in used_indexes
    )
    return reordered

def create_purchase_plan(available_skills, config, end_career=False):
    """
    Create optimized purchase plan based on available skills and config.
    
    Regular logic:
    - If gold skill appears → buy it
    - If gold skill not available but base skill appears → buy base skill
    
    End-career logic:
    - Buy as many skills as possible (cheapest first) to maximize skill points usage
    
    Args:
        available_skills: List of skill dicts with 'name' and 'price'
        config: Config dict from skills.json
        end_career: If True, buy all affordable skills instead of just priority skills
    
    Returns:
        List of skills to purchase in order
    """
    skill_priority = config.get("skill_priority", [])
    gold_upgrades = config.get("gold_skill_upgrades", {})
    
    # Deduplicate first to prevent buying the same skill twice from OCR noise
    deduped_skills = deduplicate_skills(available_skills, similarity_threshold=0.8)
    
    # Create lookup for available skills (exact match)
    available_by_name = {skill['name']: skill for skill in deduped_skills}
    
    purchase_plan = []
    matched_skills = set()  # Track skills that have already been matched to prevent duplicates
    
    log_info(f"Creating purchase plan (end_career: {end_career})")
    log_debug(f"Priority list: {len(skill_priority)} skills")
    log_debug(f"Gold upgrades: {len(gold_upgrades)} relationships")
    log_debug(f"Available skills: {len(available_skills)} skills")
    if len(deduped_skills) != len(available_skills):
        log_debug(f"Deduped skills: {len(deduped_skills)} skills (removed duplicates)")
    
    # End-career mode: prioritize skill list first, then buy remaining skills
    if end_career:
        log_info("End-career mode: priority skills first, then buy remaining skills")
    
    # Regular mode: follow priority list
    for priority_skill in skill_priority:
        # Check if this is a gold skill (key in gold_upgrades)
        if priority_skill in gold_upgrades:
            base_skill_name = gold_upgrades[priority_skill]
            
            # Rule 1: If gold skill appears → buy it (try exact then fuzzy match)
            skill = None
            if priority_skill in available_by_name and available_by_name[priority_skill]['name'] not in matched_skills:
                skill = available_by_name[priority_skill]
            else:
                skill = find_matching_skill(priority_skill, deduped_skills, excluded_skills=matched_skills)
            
            if skill:
                purchase_plan.append(skill)
                matched_skills.add(skill['name'])  # Mark as matched
                log_info(f"Gold skill found: {skill['name']} - {skill['price']}")
                
            # Rule 2: If gold not available but base skill appears → buy base
            else:
                base_skill = None
                if base_skill_name in available_by_name and available_by_name[base_skill_name]['name'] not in matched_skills:
                    base_skill = available_by_name[base_skill_name]
                else:
                    base_skill = find_matching_skill(base_skill_name, deduped_skills, excluded_skills=matched_skills)
                
                if base_skill:
                    purchase_plan.append(base_skill)
                    matched_skills.add(base_skill['name'])  # Mark as matched
                    log_info(f"Base skill found: {base_skill['name']} - {base_skill['price']} (for {priority_skill}")
                
        else:
            # Regular skill - just buy if available (try exact then fuzzy match)
            skill = None
            if priority_skill in available_by_name and available_by_name[priority_skill]['name'] not in matched_skills:
                skill = available_by_name[priority_skill]
            else:
                skill = find_matching_skill(priority_skill, deduped_skills, excluded_skills=matched_skills)
            
            if skill:
                purchase_plan.append(skill)
                matched_skills.add(skill['name'])  # Mark as matched
                log_info(f"Regular skill: {skill['name']} - {skill['price']}")
    
    # End-career mode: after priority skills, add configured gold skills, then fill cheapest first
    if end_career:
        # Get skills already selected for purchase
        purchased_skill_names = {skill['name'] for skill in purchase_plan}
        
        # Find remaining skills not yet selected
        remaining_skills = [
            skill for skill in deduped_skills 
            if skill['name'] not in purchased_skill_names
        ]
        
        promoted_gold_skills = []
        for gold_skill_name in gold_upgrades:
            gold_skill = None
            if gold_skill_name in available_by_name and available_by_name[gold_skill_name]['name'] not in purchased_skill_names:
                gold_skill = available_by_name[gold_skill_name]
            else:
                gold_skill = find_matching_skill(gold_skill_name, remaining_skills, excluded_skills=purchased_skill_names)

            if gold_skill:
                purchase_plan.append(gold_skill)
                purchased_skill_names.add(gold_skill['name'])
                promoted_gold_skills.append(gold_skill)
                log_info(f"End-career gold skill promoted: {gold_skill['name']} - {gold_skill['price']}")

        if promoted_gold_skills:
            remaining_skills = [
                skill for skill in remaining_skills
                if skill['name'] not in purchased_skill_names
            ]
            log_info(f"End-career: Promoted {len(promoted_gold_skills)} configured gold skills before cheapest-fill purchases")

        reordered_purchase_plan = _reorder_end_career_gold_first(purchase_plan, gold_upgrades)
        if reordered_purchase_plan != purchase_plan:
            purchase_plan = reordered_purchase_plan
            log_info("End-career: Configured gold skills moved before regular priority skills")

        if remaining_skills:
            log_info(f"End-career: Adding {len(remaining_skills)} remaining skills (cheapest first)")
            
            # Sort remaining skills by price (cheapest first) to maximize purchases
            try:
                sorted_remaining = sorted(
                    remaining_skills,
                    key=_skill_price
                )
            except:
                sorted_remaining = remaining_skills
            
            # Add remaining skills to purchase plan
            purchase_plan.extend(sorted_remaining)
            
            log_info(f"End-career plan: {len(purchase_plan)} total skills ({len(purchase_plan) - len(purchased_skill_names)} additional)")
            
            # Show some of the additional skills
            if len(sorted_remaining) > 0:
                log_info("Additional skills (cheapest first):")
                for i, skill in enumerate(sorted_remaining[:5], 1):  # Show first 5
                    log_info(f"  +{i}. {skill['name']} - {skill['price']} points")
                if len(sorted_remaining) > 5:
                    log_info(f"  ... and {len(sorted_remaining) - 5} more additional skills")
    
    return purchase_plan

def filter_affordable_skills(purchase_plan, available_points):
    """
    Filter purchase plan to only include skills that can be afforded.
    
    Args:
        purchase_plan: List of skills to purchase
        available_points: Available skill points
    
    Returns:
        tuple: (affordable_skills, total_cost, remaining_points)
    """
    affordable_skills = []
    total_cost = 0
    
    log_info(f"\n[INFO] Filtering skills by available points ({available_points})")
    log_info(f"=" * 60)
    
    for skill in purchase_plan:
        try:
            skill_cost = int(skill['price']) if skill['price'].isdigit() else 0
            
            if total_cost + skill_cost <= available_points:
                affordable_skills.append(skill)
                total_cost += skill_cost
                remaining_points = available_points - total_cost
                log_info(f"✅ {skill['name']:<30} | Cost: {skill_cost:<4} | Remaining: {remaining_points}")
            else:
                needed_points = skill_cost - (available_points - total_cost)
                log_info(f"❌ {skill['name']:<30} | Cost: {skill_cost:<4} | Need {needed_points} more points")
                
        except ValueError:
            log_info(f"⚠️  {skill['name']:<30} | Invalid price: {skill['price']}")
    
    remaining_points = available_points - total_cost
    
    log_info(f"=" * 60)
    log_info(f"Budget Summary:")
    log_info(f"   Available points: {available_points}")
    log_info(f"   Total cost: {total_cost}")
    log_info(f"   Remaining points: {remaining_points}")
    log_info(f"   Affordable skills: {len(affordable_skills)}/{len(purchase_plan)}")
    
    return affordable_skills, total_cost, remaining_points

def calculate_total_cost(purchase_plan):
    """Calculate total skill points needed for purchase plan."""
    total = sum(int(skill['price']) for skill in purchase_plan if skill['price'].isdigit())
    return total

def print_purchase_summary(purchase_plan):
    """Print a nice summary of the purchase plan."""
    if not purchase_plan:
        log_info(f"📋 No skills to purchase based on your priority list.")
        return
    
    log_info(f"\n📋 PURCHASE PLAN:")
    log_info(f"=" * 60)
    
    total_cost = 0
    for i, skill in enumerate(purchase_plan, 1):
        price = skill['price']
        if price.isdigit():
            total_cost += int(price)
        log_info(f"  {i:2d}. {skill['name']:<30} | Price: {price}")
    
    log_info(f"=" * 60)
    log_info(f"Total Cost: {total_cost} skill points")
    log_info(f"Skills to buy: {len(purchase_plan)}")

