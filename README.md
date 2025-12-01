# AI File Renaming Agent

An intelligent AI agent that uses Large Language Models (LLMs) to interpret natural language instructions and perform file renaming operations. The agent receives LLM output, parses it into actionable commands, and executes file renames with comprehensive safety checks and validation.

## Features

- **LLM Integration**: Connects to OpenAI API (GPT-5.1) for intelligent planning
- **Action Interpreter/Executor**: Parses LLM JSON responses and executes file rename operations
- **Terminal-Based UI**: Clean, user-friendly command-line interface
- **Safety & Error Handling**: Validates all renames before execution, requires confirmations, and handles errors gracefully
- **Comprehensive Logging**: All actions are logged to timestamped files for auditability
- **Advanced File Renaming Capabilities**:
  - Date-based ordering (oldest/newest first)
  - Pattern preservation (leading zeros, underscores, etc.)
  - Large directory support (500+ files)
  - Automatic file type filtering
  - Swap/reversal handling with temporary names

## Project Structure

```
CS4680Project2/
├── ai_file_renamer.py   # Main entry point - file renaming agent
├── llm_interface.py     # LLM interface for OpenAI API integration
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment variables
└── README.md            # This file
```

## Installation

1. **Clone or navigate to the project directory**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key**:
   
   **Option 1: Using .env file (Recommended)**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your API key
   OPENAI_API_KEY=your_actual_api_key_here
   ```
   
   **Option 2: Using environment variables**
   ```bash
   # Windows (PowerShell)
   $env:OPENAI_API_KEY="your_actual_api_key_here"
   
   # Linux/Mac
   export OPENAI_API_KEY="your_actual_api_key_here"
   ```
   
   **Getting an API Key:**
   - **OpenAI**: Get your key from https://platform.openai.com/api-keys
   
   **Note**: The `.env` file is already in `.gitignore` and will not be committed to git.

## Usage

Run the file renaming agent:
```bash
python ai_file_renamer.py
```

This agent uses **OpenAI's `gpt-5.1` model** for intelligent file rename planning. The model receives your natural language instruction, analyzes the files in the directory, and generates a structured rename plan.

**Setup:**
1. Set your OpenAI API key (see Installation section above for detailed instructions)
   - **Easiest**: Create a `.env` file with `OPENAI_API_KEY=your_key_here`
   - **Alternative**: Set environment variable `OPENAI_API_KEY`

2. The agent uses `gpt-5.1` by default (configurable via `OPENAI_MODEL` in `.env`)

**Workflow:**
1. Asks for a directory to analyze
2. Asks for a natural-language rename instruction
3. Calls the LLM (gpt-5.1) to generate a structured rename plan as JSON
4. Validates the plan (checks file existence, prevents collisions, etc.)
5. Shows a preview of planned renames
6. Asks for confirmation before executing
7. Executes renames and logs results

**Example usage:**
```bash
$ python ai_file_renamer.py

Enter directory to analyze:
> ./photos

Enter your rename instruction:
> Rename all .jpg files to vacation_###.jpg ordered by creation date.

Contacting LLM to generate rename plan...

Planned actions:

  1. IMG_1234.jpg        → vacation_001.jpg
  2. IMG_5678.jpg        → vacation_002.jpg
  3. DSC_0001.jpg        → vacation_003.jpg

Proceed with these 3 renames? [y/N]:
> y

Renaming...
[OK] IMG_1234.jpg → vacation_001.jpg
[OK] IMG_5678.jpg → vacation_002.jpg
[OK] DSC_0001.jpg → vacation_003.jpg

Done. 3 successful, 0 failed.
Actions logged to logs/2025-11-28_15-32-10.log
```

**Advanced Examples:**
- `"Rename all files that start with IMG and change it to image"` - Pattern matching with prefix replacement
- `"Rename all jpg files to j_#.jpg in order of dates created"` - Date-based ordering
- `"Rename all jpg files to j_#.jpg in reverse order of dates"` - Reverse date ordering
- `"Scan for all files with ordered numbering, group them by type, then reverse all the numbers"` - Complex pattern operations
- `"Rename file1.txt and file2.txt to file_1.txt and file_2.txt"` - Preserves exact numbering format

**How it works:**
- The LLM receives a structured prompt with the directory, user instruction, and file list
- Uses OpenAI's `response_format={"type": "json_object"}` to ensure valid JSON output
- The model returns a JSON object with `{"renames": [{"old": "...", "new": "..."}]}`
- The agent validates, previews, and executes the plan safely
- For date ordering, files are pre-sorted and numbered sequentially
- Pattern preservation ensures leading zeros and formatting are maintained

## Safety Features

The agent includes several safety mechanisms:

1. **Action Validation**: All actions are validated before execution
2. **Confirmation Prompts**: Destructive operations require user confirmation:
   - File deletions
   - Dangerous system commands (rm, format, shutdown, etc.)
   - Destructive API calls (DELETE, PUT, PATCH)
   - Database operations that modify data
3. **Command Sanitization**: System commands are sanitized to prevent injection attacks
4. **Error Handling**: Comprehensive error handling with graceful degradation
5. **Logging**: All actions are logged to `logs/agent.log` for auditability

## Components

### LLM Interface (`llm_interface.py`)
- Connects to OpenAI API using GPT-5.1 model
- Uses `response_format={"type": "json_object"}` for structured JSON output
- Handles API errors and rate limiting with retry logic
- Builds structured prompts with file metadata (creation dates, etc.)

### File Renaming Agent (`ai_file_renamer.py`)
- Main entry point for the application
- Parses LLM JSON responses to extract rename plans
- Validates all renames before execution (file existence, collisions, illegal characters)
- Handles complex operations (swaps, reversals) with temporary names
- Provides preview and confirmation before executing
- Comprehensive logging to timestamped files

## Configuration

Edit `.env` file to configure:

- **API Key**: Set your `OPENAI_API_KEY`
- **Model**: Optionally specify which model to use (defaults to `gpt-5.1`)
  - Example: `OPENAI_MODEL=gpt-5.1`

## Logging

All agent activities are logged to timestamped files in the `logs/` directory:
- Each session creates a new log file: `logs/YYYY-MM-DD_HH-MM-SS.log`

Logs include:
- All rename operations with before/after names
- LLM requests and responses
- Errors and exceptions
- Validation checks
- User confirmations and cancellations

## Error Handling

The agent handles various error scenarios:
- **API Errors**: Retries with exponential backoff for rate limits
- **Parsing Errors**: Falls back to information display if JSON parsing fails
- **Execution Errors**: Catches and reports errors gracefully
- **Validation Errors**: Prevents dangerous actions from executing

## File Renaming Agent Capabilities

The file renaming agent includes several advanced features:

### Pattern Preservation
- Preserves leading zeros (e.g., `IMG_001.jpg` → `image_001.jpg`, not `image_1.jpg`)
- Maintains exact numbering format from original filenames
- Handles underscores, dashes, and other separators

### Date-Based Ordering
- Automatically sorts files by creation date when requested
- Supports both chronological (oldest first) and reverse (newest first) ordering
- Ensures correct sequential numbering based on sorted order

### Large Directory Support
- Automatically filters by file type when mentioned in instruction (e.g., "jpg files")
- Handles directories with 500+ files efficiently
- Warns user and processes all files even if only a sample is shown to LLM

### Complex Operations
- Handles file swaps and reversals with temporary names
- Groups files by pattern for batch operations
- Validates all renames before execution to prevent collisions

## Limitations

- Focused on file renaming operations only (does not handle system commands, API calls, or database operations)
- Very large directories (>500 files) may require pattern-based instructions for best results
- Some complex multi-step operations may require multiple interactions

## Requirements Compliance

This project fully meets all requirements for CS4680 Project 2:

✅ **LLM Integration Module**
- Connects to OpenAI API (GPT-5.1)
- Sends prompts and receives responses
- Handles API errors and rate limiting with retry logic

✅ **Action Interpreter/Executor**
- Parses LLM output to extract actionable commands (file rename plans)
- Converts LLM responses into executable operations (file renames)
- Executes file rename operations with validation and safety checks

✅ **User Interface**
- Terminal-based interface
- Allows natural language input
- Displays results and execution status
- Provides feedback on actions taken

✅ **Error Handling & Safety**
- Validates LLM outputs before execution
- Handles errors gracefully
- Implements safety checks (confirmation for destructive operations)
- Logs all actions for auditability

## Future Enhancements

Potential improvements:
- Full database integration
- More sophisticated action planning
- Multi-step task execution
- Plugin system for custom actions
- Web-based UI option
- Action history and undo functionality
- Batch processing for very large directories (1000+ files)

## License

This project is created for educational purposes as part of CS4680 Project 2.

## Author

Created for CS4680 - AI Agent Project

