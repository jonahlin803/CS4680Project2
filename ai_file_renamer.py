"""AI File Renamer - An agent that uses LLM to plan and execute file renames."""
import os
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

# Import LLM interface for file renaming
from llm_interface import get_rename_plan_from_llm

# ------------- Logging setup -------------

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_logger() -> logging.Logger:
    """Set up logging for the file renamer."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = LOG_DIR / f"{timestamp}.log"

    logger = logging.getLogger("ai_file_renamer")
    logger.setLevel(logging.INFO)

    # Avoid adding multiple handlers if function is called again
    if not logger.handlers:
        fh = logging.FileHandler(log_path)
        fh.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    logger.info("=== New run started ===")
    logger.info(f"Logging to {log_path}")
    return logger


# ------------- Core functions -------------

def ask_directory() -> Path:
    """Prompt user for directory path and validate it."""
    while True:
        directory = input("Enter directory to analyze:\n> ").strip()
        path = Path(directory).expanduser().resolve()
        if path.is_dir():
            return path
        print("That path is not a valid directory. Please try again.\n")


def ask_instruction() -> str:
    """Prompt user for rename instruction."""
    print("\nEnter your rename instruction (natural language):")
    return input("> ").strip()


def list_files_in_directory(directory: Path, extensions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    List files in the directory with metadata, optionally filtered by extension.
    
    Args:
        directory: Directory to list files from
        extensions: Optional list of extensions to filter (e.g., ['.jpg', '.png'])
    
    Returns:
        List of file info dictionaries with 'name' and 'creation_time'
    """
    file_objects = [f for f in directory.iterdir() if f.is_file()]
    
    if extensions:
        # Normalize extensions (ensure they start with .)
        normalized_exts = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
        file_objects = [f for f in file_objects if f.suffix.lower() in normalized_exts]
    
    # Get file info with metadata
    files_info = []
    for f in file_objects:
        stat = f.stat()
        files_info.append({
            "name": f.name,
            "creation_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "size": stat.st_size
        })
    
    # Sort by name by default
    files_info.sort(key=lambda x: x["name"])
    
    return files_info


def call_llm_for_rename_plan(
    directory: Path,
    instruction: str,
    files: List[Dict[str, Any]]
) -> Dict:
    """
    Call LLM to generate a rename plan based on user instruction and file list.
    
    Args:
        directory: Target directory path
        instruction: User's natural language instruction
        files: List of file info dictionaries with 'name' and 'creation_time'
    
    Returns:
        Dictionary with 'renames' list containing old/new mappings
    """
    print("\nContacting LLM to generate rename plan...")
    
    # Check if instruction mentions date/time ordering
    instruction_lower = instruction.lower()
    date_keywords = ['date', 'time', 'created', 'creation', 'oldest', 'newest', 'chronological', 'order by']
    should_order_by_date = any(keyword in instruction_lower for keyword in date_keywords)
    is_reverse = 'reverse' in instruction_lower
    
    # Pre-sort files by creation_time if date ordering is requested
    if should_order_by_date:
        # Sort by creation_time (oldest first by default)
        files_sorted = sorted(files, key=lambda x: x.get("creation_time", ""))
        # Reverse if user wants reverse order
        if is_reverse:
            files_sorted = list(reversed(files_sorted))
        files = files_sorted
    
    try:
        # Use the focused LLM interface module
        plan = get_rename_plan_from_llm(str(directory), instruction, files)
        
        # If date ordering was requested, fix the numbering to match the sorted order
        if should_order_by_date and plan.get("renames"):
            plan = _fix_date_ordered_numbering(plan, files, instruction)
        
        return plan
    except ValueError as e:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        raise ValueError(f"Error calling LLM: {e}")


def _fix_date_ordered_numbering(plan: Dict, sorted_files: List[Dict[str, Any]], instruction: str) -> Dict:
    """
    Fix numbering in the rename plan to match the sorted file order.
    
    Args:
        plan: LLM-generated rename plan
        sorted_files: Files already sorted by date
        instruction: User's instruction (to extract the pattern)
    
    Returns:
        Fixed rename plan with correct numbering
    """
    import re
    
    if not plan.get("renames") or not sorted_files:
        return plan
    
    # Extract the pattern from the LLM's response (e.g., "j_1.jpg" -> "j_{}.jpg")
    first_rename = plan["renames"][0]
    new_name_template = first_rename.get("new", "")
    
    prefix = ""
    ext = ""
    
    # Try to extract prefix and extension from the new name
    # Pattern: "j_1.jpg" -> prefix="j", ext=".jpg"
    match = re.match(r'^(.+?)[_\-]?\d+(\..+)?$', new_name_template)
    if match:
        prefix = match.group(1).rstrip('_-')
        if match.group(2):
            ext = match.group(2)
        else:
            # Get extension from original file
            first_file = sorted_files[0]["name"]
            if "." in first_file:
                ext = "." + first_file.split(".")[-1]
    else:
        # Fallback: try to extract from instruction
        pattern_match = re.search(r'(\w+)[_\-]?#[\._]?(\w+)?', instruction, re.IGNORECASE)
        if pattern_match:
            prefix = pattern_match.group(1)
            if pattern_match.group(2):
                ext = "." + pattern_match.group(2)
            else:
                # Get extension from original file
                first_file = sorted_files[0]["name"]
                if "." in first_file:
                    ext = "." + first_file.split(".")[-1]
        else:
            # Last resort: extract from first file's extension
            first_file = sorted_files[0]["name"]
            if "." in first_file:
                parts = first_file.rsplit(".", 1)
                prefix = "file"  # Default prefix
                ext = "." + parts[1]
            else:
                # Can't extract pattern, return as-is
                return plan
    
    # Create new rename plan based on sorted order
    fixed_renames = []
    for i, file_info in enumerate(sorted_files, start=1):
        old_name = file_info["name"]
        # Only include files that were in the original plan
        if any(r["old"] == old_name for r in plan["renames"]):
            # Generate new name with correct number
            new_name = f"{prefix}_{i}{ext}"
            fixed_renames.append({"old": old_name, "new": new_name})
    
    return {"renames": fixed_renames}


def validate_rename_plan(
    directory: Path,
    plan: Dict
) -> List[Dict]:
    """
    Validate the LLM's JSON and return a cleaned list of renames.
    
    Raises ValueError if something is invalid.
    """
    if "renames" not in plan or not isinstance(plan["renames"], list):
        raise ValueError("LLM response missing 'renames' list.")

    renames = plan["renames"]

    old_names = set()
    new_names = set()

    cleaned_plan = []

    # Illegal characters for filenames (Windows + Unix)
    illegal_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\x00']

    for item in renames:
        if not isinstance(item, dict):
            raise ValueError(f"Each rename entry must be an object. Got: {type(item)}")

        old = item.get("old")
        new = item.get("new")

        if not old or not new:
            raise ValueError(f"Invalid rename entry (missing 'old' or 'new'): {item!r}")

        # Check that old file exists
        old_path = directory / old
        if not old_path.is_file():
            raise ValueError(f"Old file does not exist: {old}")

        # Check for duplicates
        if old in old_names:
            raise ValueError(f"Duplicate 'old' filename in plan: {old}")
        if new in new_names:
            raise ValueError(f"Collision: multiple files want new name '{new}'")

        # Check for illegal characters
        for char in illegal_chars:
            if char in new:
                raise ValueError(f"Illegal character '{char}' in new filename: {new}")

        # Check that new name doesn't already exist (unless it's being renamed from something else)
        # This handles swaps/reversals where file1.txt → file2.txt and file2.txt → file1.txt
        new_path = directory / new
        
        # Check if this is part of a swap (circular rename)
        is_swap = False
        for other_item in renames:
            if other_item.get("old") == new and other_item.get("new") == old:
                is_swap = True
                break
        
        # Allow swaps, but block if target exists and isn't part of a swap
        if new_path.exists() and new not in old_names and not is_swap:
            raise ValueError(f"Target filename already exists: {new}")

        old_names.add(old)
        new_names.add(new)
        cleaned_plan.append({"old": old, "new": new})

    return cleaned_plan


def preview_renames(renames: List[Dict]) -> bool:
    """Display preview of planned renames and ask for confirmation."""
    print("\nPlanned actions:\n")
    if not renames:
        print("No files to rename.")
        return False

    width = max(len(item["old"]) for item in renames) + 2

    for i, item in enumerate(renames, start=1):
        old = item["old"]
        new = item["new"]
        print(f"{i:3}. {old.ljust(width)} → {new}")

    while True:
        choice = input(f"\nProceed with these {len(renames)} renames? [y/N]: ").strip().lower()
        if choice in ("y", "yes"):
            return True
        elif choice in ("n", "no", ""):
            return False
        else:
            print("Please answer 'y' or 'n'.")


def execute_renames(
    directory: Path,
    renames: List[Dict],
    logger: logging.Logger
):
    """Execute the rename operations, handling swaps with temporary names."""
    print("\nRenaming...")
    success_count = 0
    error_count = 0
    
    # Detect swaps (circular renames) that need temp names
    # Build a mapping to detect cycles
    rename_map = {item["old"]: item["new"] for item in renames}
    needs_temp = False
    for old_name, new_name in rename_map.items():
        if rename_map.get(new_name) == old_name:
            needs_temp = True
            break
    
    if needs_temp:
        # Use temporary names for swaps
        import uuid
        temp_renames = []
        final_renames = []
        
        for item in renames:
            old = item["old"]
            new = item["new"]
            
            # Check if this is part of a swap
            if rename_map.get(new) == old:
                # This is a swap - use temp name
                temp_name = f".temp_{uuid.uuid4().hex[:8]}_{new}"
                temp_renames.append({"old": old, "new": temp_name})
                final_renames.append({"old": temp_name, "new": new})
            else:
                # Regular rename
                temp_renames.append(item)
        
        # Execute temp renames first
        for item in temp_renames:
            old = item["old"]
            new = item["new"]
            src = directory / old
            dst = directory / new
            try:
                src.rename(dst)
                logger.info(f"RENAMED (temp): {old} -> {new}")
            except Exception as e:
                print(f"[ERR] {old} → {new} ({e})")
                logger.error(f"FAILED: {old} -> {new}: {e}")
                error_count += 1
                return
        
        # Execute final renames
        for item in final_renames:
            old = item["old"]
            new = item["new"]
            src = directory / old
            dst = directory / new
            try:
                src.rename(dst)
                print(f"[OK] {old} → {new}")
                logger.info(f"RENAMED: {old} -> {new}")
                success_count += 1
            except Exception as e:
                print(f"[ERR] {old} → {new} ({e})")
                logger.error(f"FAILED: {old} -> {new}: {e}")
                error_count += 1
    else:
        # No swaps, execute normally
        for item in renames:
            old = item["old"]
            new = item["new"]
            src = directory / old
            dst = directory / new

            try:
                src.rename(dst)
                print(f"[OK] {old} → {new}")
                logger.info(f"RENAMED: {old} -> {new}")
                success_count += 1
            except Exception as e:
                print(f"[ERR] {old} → {new} ({e})")
                logger.error(f"FAILED: {old} -> {new}: {e}")
                error_count += 1

    print(f"\nDone. {success_count} successful, {error_count} failed.")
    logger.info(f"Rename operation completed: {success_count} successful, {error_count} failed")


# ------------- Main entry point -------------

def main():
    """Main entry point for the file renamer."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set it using:")
        print("  Windows (PowerShell): $env:OPENAI_API_KEY='your_key_here'")
        print("  Linux/Mac: export OPENAI_API_KEY='your_key_here'")
        sys.exit(1)
    
    logger = setup_logger()
    logger.info("Starting AI File Renamer")

    # Get directory
    directory = ask_directory()
    logger.info(f"Selected directory: {directory}")

    # Get instruction
    instruction = ask_instruction()
    logger.info(f"User instruction: {instruction}")

    # Try to extract file extension filter from instruction
    instruction_lower = instruction.lower()
    extensions_to_filter = None
    
    # Check for common file type mentions
    if '.jpg' in instruction_lower or 'jpg' in instruction_lower or 'jpeg' in instruction_lower:
        extensions_to_filter = ['.jpg', '.jpeg']
    elif '.png' in instruction_lower or 'png' in instruction_lower:
        extensions_to_filter = ['.png']
    elif '.txt' in instruction_lower or 'text' in instruction_lower:
        extensions_to_filter = ['.txt']
    elif '.pdf' in instruction_lower or 'pdf' in instruction_lower:
        extensions_to_filter = ['.pdf']
    # Add more as needed
    
    # List files (with optional extension filter)
    files_info = list_files_in_directory(directory, extensions_to_filter)
    file_count = len(files_info)
    logger.info(f"Found {file_count} files in directory" + (f" (filtered by extension: {extensions_to_filter})" if extensions_to_filter else ""))
    
    # Warn user if directory is very large
    if file_count > 500:
        print(f"\n⚠ Warning: Large directory detected ({file_count} files).")
        print("Processing all files, but the LLM will see a sample to avoid token limits.")
        print("The pattern will be applied to all matching files.")
        response = input("Continue? [Y/n]: ").strip().lower()
        if response == 'n':
            print("Aborted.")
            return
    
    # Extract just filenames for logging/display
    files = [f["name"] for f in files_info]

    if not files:
        print("No files found in that directory. Exiting.")
        return

    # Step 1: get plan from LLM
    try:
        raw_plan = call_llm_for_rename_plan(directory, instruction, files_info)
    except ValueError as e:
        print(f"\nError generating rename plan: {e}")
        logger.error(f"LLM plan generation failed: {e}")
        return
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        logger.error(f"Unexpected error in LLM call: {e}", exc_info=True)
        return

    # Step 2: validate plan
    try:
        renames = validate_rename_plan(directory, raw_plan)
        if not renames:
            print("\nNo files matched your criteria. The LLM returned an empty rename plan.")
            print(f"Files in directory: {', '.join(files[:10])}{'...' if len(files) > 10 else ''}")
            logger.info("LLM returned empty rename plan")
            return
    except ValueError as e:
        print(f"\nError in LLM plan: {e}")
        print(f"\nTip: If you're trying to swap/reverse files, make sure the LLM generates a complete plan.")
        logger.error(f"LLM plan validation failed: {e}")
        return

    # Step 3: preview & confirm
    if not preview_renames(renames):
        print("\nAborted by user. No changes made.")
        logger.info("User aborted rename operation.")
        return

    # Step 4: execute
    execute_renames(directory, renames, logger)
    
    # Show log file location
    log_file = logger.handlers[0].baseFilename if logger.handlers else "unknown"
    print(f"Actions logged to {log_file}")


if __name__ == "__main__":
    main()

