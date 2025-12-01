"""LLM Interface for file renaming - focused module using OpenAI's GPT-5.1 model."""
import os
import json
import time
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI
from openai import RateLimitError, APIError

# Load environment variables from .env file
load_dotenv()

# Use OpenAI's GPT-5.1 model for JSON planning
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.1")  # Default to gpt-5.1

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an AI assistant that generates SAFE file rename plans based on user instructions.

You must ONLY return JSON in the following format:

{
  "renames": [
    { "old": "old_filename.ext", "new": "new_filename.ext" },
    ...
  ]
}

Core Rules:
1. Every "old" filename must exactly match one of the filenames in the provided files list (use the "name" field from file objects).
2. "new" filenames must be valid (no slashes, path separators, or illegal characters).
3. Do NOT invent files that do not exist in the provided list.
4. Find ALL files that match the user's criteria - be thorough and check every file.
5. If a warning says only some files are shown, apply the instruction pattern to ALL files in the directory (extrapolate the pattern).
6. Preserve file extensions unless the user explicitly asks to change them.
7. Preserve the exact format of numbers/patterns from original filenames (including leading zeros, underscores, etc.) unless the user wants them changed.
8. Each file object includes complete metadata: creation_time, modification_time, access_time, size, and size_human. 
   YOU must analyze the user's instruction and determine:
   - What sorting/ordering criteria to use (date, size, etc.)
   - Which metadata field to use (creation_time, modification_time, access_time, or size)
   - What order (ascending/descending, oldest/newest first, smallest/largest first)
   - Then sort the files accordingly and number them sequentially
9. When the user says "order X files by Y" or "sort by Y", analyze Y to determine:
   - If Y mentions "date", "time", "created", "modified", "access" → use the appropriate time field
   - If Y mentions "size", "largest", "smallest" → use the size field
   - Determine the direction (ascending/descending) from words like "oldest", "newest", "smallest", "largest", "reverse"
   - Sort ALL files by that criteria, then rename them sequentially (1, 2, 3, etc.) preserving the prefix/pattern
10. Example: "order Imagen_x files by date modified" means:
    - Sort all files by modification_time (oldest modified first, unless "newest" is mentioned)
    - Rename them to Imagen_1.jpg, Imagen_2.jpg, etc. in that sorted order
11. If the user's request is unclear or impossible, return an empty list: { "renames": [] }

Follow the user's instruction precisely and apply it to all matching files. Handle any edge cases, swaps, reversals, or complex operations as needed to fulfill the request.

Do NOT include explanations, comments, or any other text outside the JSON."""


# Maximum number of files to send to LLM in one request
MAX_FILES_FOR_LLM = 500

def build_user_prompt(directory: str, instruction: str, files: List) -> str:
    """
    Create a structured prompt that we send to the model.
    
    Args:
        directory: Directory path
        instruction: User's natural language instruction
        files: List of file info (dicts with 'name', 'creation_time', etc.) or just filenames
    
    Returns:
        JSON string containing the prompt data
    """
    # Handle both old format (list of strings) and new format (list of dicts)
    if files and isinstance(files[0], dict):
        # New format with metadata
        files_data = files
    else:
        # Old format - just filenames
        files_data = [{"name": f} for f in files]
    
    # Limit files sent to LLM to avoid token limits
    total_files = len(files_data)
    if total_files > MAX_FILES_FOR_LLM:
        files_data = files_data[:MAX_FILES_FOR_LLM]
        files_truncated = True
    else:
        files_truncated = False
    
    payload = {
        "directory": directory,
        "instruction": instruction,
        "files": files_data,
    }
    
    # Add warning if files were truncated
    if files_truncated:
        payload["warning"] = f"Only showing first {MAX_FILES_FOR_LLM} of {total_files} files. Apply the instruction pattern to ALL {total_files} files in the directory."
    
    # All metadata is already included in files_data - let the LLM analyze and decide how to sort/order
    
    return json.dumps(payload, indent=2)


def get_rename_plan_from_llm(
    directory: str,
    instruction: str,
    files: List
) -> Dict:
    """
    Call the LLM and return a Python dict like:
    { "renames": [ { "old": "...", "new": "..." }, ... ] }
    
    Args:
        directory: Directory path
        instruction: User's natural language instruction
        files: List of file info (dicts with 'name', 'creation_time', etc.) or just filenames
    
    Returns:
        Dictionary with 'renames' list containing old/new mappings
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    user_prompt = build_user_prompt(directory, instruction, files)

    # Retry logic for rate limiting and transient errors
    max_retries = 3
    base_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,  # keep it deterministic-ish
                response_format={"type": "json_object"},  # ask for valid JSON
            )

            content = response.choices[0].message.content
            # `content` should be a JSON string
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Fallback: if somehow it returns junk, fail safely
                return {"renames": []}

            # Ensure the shape is at least predictable
            if "renames" not in data or not isinstance(data["renames"], list):
                return {"renames": []}

            return data
        
        except RateLimitError as e:
            # Handle rate limiting with exponential backoff
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                time.sleep(delay)
                continue
            else:
                raise ValueError(f"Rate limit exceeded after {max_retries} attempts: {e}")
        
        except APIError as e:
            # Handle other API errors (may be transient)
            if attempt < max_retries - 1 and e.status_code and e.status_code >= 500:
                # Retry on server errors (5xx)
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
                continue
            else:
                raise ValueError(f"LLM API error: {e}")
    
    # Should not reach here, but just in case
    raise ValueError("Failed to get LLM response after retries")

