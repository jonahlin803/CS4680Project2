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

def ask_directory() -> Optional[Path]:
    """Prompt user for directory path and validate it. Returns None if user quits."""
    while True:
        directory = input("Enter directory to analyze (or 'q' to quit):\n> ").strip()
        if directory.lower() == 'q':
            return None
        path = Path(directory).expanduser().resolve()
        if path.is_dir():
            return path
        print("That path is not a valid directory. Please try again.\n")


def ask_instruction() -> Optional[str]:
    """Prompt user for rename instruction. Returns None if user quits."""
    print("\nEnter your rename instruction (natural language, or 'q' to quit):")
    instruction = input("> ").strip()
    if instruction.lower() == 'q':
        return None
    return instruction


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
    
    # Get file info with metadata (all available metadata)
    files_info = []
    for f in file_objects:
        stat = f.stat()
        files_info.append({
            "name": f.name,
            "creation_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "creation_timestamp": stat.st_ctime,  # Raw timestamp for sorting
            "modification_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "modification_timestamp": stat.st_mtime,  # Raw timestamp for sorting
            "access_time": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "access_timestamp": stat.st_atime,  # Raw timestamp for sorting
            "size": stat.st_size,
            "size_human": f"{stat.st_size:,} bytes"  # Human-readable size
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
        files: List of file info dictionaries with all metadata (name, creation_time, modification_time, access_time, size, etc.)
    
    Returns:
        Dictionary with 'renames' list containing old/new mappings
    """
    print("\nContacting LLM to generate rename plan...")
    
    try:
        # Use the focused LLM interface module - let LLM handle all sorting/ordering decisions
        plan = get_rename_plan_from_llm(str(directory), instruction, files)
        return plan
    except ValueError as e:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        raise ValueError(f"Error calling LLM: {e}")


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
        # This handles swaps/reversals and complex permutations
        new_path = directory / new
        
        # Check if target is also being renamed (part of a permutation)
        target_is_also_renamed = False
        is_swap = False
        for other_item in renames:
            if other_item.get("old") == new:
                target_is_also_renamed = True
                if other_item.get("new") == old:
                    is_swap = True  # Circular swap
                break
        
        # Allow if target is also being renamed (permutation) or is a swap
        # But block if target exists and isn't part of the rename operation
        if new_path.exists() and new not in old_names and not target_is_also_renamed:
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
    """Execute the rename operations, handling conflicts with temporary names."""
    print("\nRenaming...")
    success_count = 0
    error_count = 0
    
    # Build a mapping for quick lookup
    rename_map = {item["old"]: item["new"] for item in renames}
    
    # Check if we need temp names:
    # 1. Circular swaps (A→B, B→A)
    # 2. Target filename already exists (and is also being renamed - complex permutation)
    needs_temp = False
    existing_targets = set()
    
    for item in renames:
        old = item["old"]
        new = item["new"]
        new_path = directory / new
        
        # Check for circular swaps
        if rename_map.get(new) == old:
            needs_temp = True
            break
        
        # Check if target already exists
        if new_path.exists():
            existing_targets.add(new)
            # If target exists and is also being renamed, we need temp names
            if new in rename_map:
                needs_temp = True
                break
    
    if needs_temp or existing_targets:
        # Use temporary names for all renames to avoid conflicts
        import uuid
        temp_renames = []
        final_renames = []
        
        for item in renames:
            old = item["old"]
            new = item["new"]
            
            # Check if target exists or is part of a swap/permutation
            new_path = directory / new
            is_conflict = (
                new_path.exists() or  # Target exists
                new in rename_map  # Target is also being renamed (permutation)
            )
            
            if is_conflict:
                # Use temp name to avoid conflict
                temp_name = f".temp_{uuid.uuid4().hex[:8]}_{new}"
                temp_renames.append({"old": old, "new": temp_name})
                final_renames.append({"old": temp_name, "new": new})
            else:
                # No conflict, can rename directly
                temp_renames.append(item)
        
        # Execute temp renames first (move all conflicting files to temp names)
        for item in temp_renames:
            old = item["old"]
            new = item["new"]
            src = directory / old
            dst = directory / new
            try:
                src.rename(dst)
                if new.startswith(".temp_"):
                    logger.info(f"RENAMED (temp): {old} -> {new}")
                else:
                    print(f"[OK] {old} → {new}")
                    logger.info(f"RENAMED: {old} -> {new}")
                    success_count += 1
            except Exception as e:
                print(f"[ERR] {old} → {new} ({e})")
                logger.error(f"FAILED: {old} -> {new}: {e}")
                error_count += 1
                if new.startswith(".temp_"):
                    # If temp rename failed, abort to avoid leaving files in bad state
                    return
        
        # Execute final renames (move from temp names to final names)
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
        # No conflicts, execute normally
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
    
    print("=" * 60)
    print("AI File Renaming Agent")
    print("=" * 60)
    print("Type 'q' at any prompt to quit.\n")

    # Main loop - continue until user quits
    while True:
        # Get directory
        directory = ask_directory()
        if directory is None:
            print("\nGoodbye!")
            logger.info("User quit the program")
            break
        logger.info(f"Selected directory: {directory}")

        # Get instruction
        instruction = ask_instruction()
        if instruction is None:
            print("\nReturning to directory selection...")
            continue
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
        
        # List files (with optional extension filter) - includes all metadata
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
                print()  # Add blank line before next iteration
                continue
        
        # Extract just filenames for logging/display
        files = [f["name"] for f in files_info]

        if not files:
            print("No files found in that directory.")
            print()  # Add blank line before next iteration
            continue

        # Step 1: get plan from LLM
        try:
            raw_plan = call_llm_for_rename_plan(directory, instruction, files_info)
        except ValueError as e:
            print(f"\nError generating rename plan: {e}")
            logger.error(f"LLM plan generation failed: {e}")
            print()  # Add blank line before next iteration
            continue
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            logger.error(f"Unexpected error in LLM call: {e}", exc_info=True)
            print()  # Add blank line before next iteration
            continue

        # Step 2: validate plan
        try:
            renames = validate_rename_plan(directory, raw_plan)
            if not renames:
                print("\nNo files matched your criteria. The LLM returned an empty rename plan.")
                print(f"Files in directory: {', '.join(files[:10])}{'...' if len(files) > 10 else ''}")
                logger.info("LLM returned empty rename plan")
                print()  # Add blank line before next iteration
                continue
        except ValueError as e:
            print(f"\nError in LLM plan: {e}")
            print(f"\nTip: If you're trying to swap/reverse files, make sure the LLM generates a complete plan.")
            logger.error(f"LLM plan validation failed: {e}")
            print()  # Add blank line before next iteration
            continue

        # Step 3: preview & confirm
        if not preview_renames(renames):
            print("\nAborted by user. No changes made.")
            logger.info("User aborted rename operation.")
            print()  # Add blank line before next iteration
            continue

        # Step 4: execute
        execute_renames(directory, renames, logger)
        
        # Show log file location
        log_file = logger.handlers[0].baseFilename if logger.handlers else "unknown"
        print(f"Actions logged to {log_file}")
        print()  # Add blank line before next iteration


if __name__ == "__main__":
    main()

