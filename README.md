# AI Agent

An intelligent AI agent that receives output from Large Language Models (LLMs) and performs concrete actions based on that output. The agent can interpret LLM responses and execute various tasks across different domains including file operations, system commands, API calls, and more.

## Features

- **Multi-Provider LLM Integration**: Supports OpenAI, Anthropic (Claude), and Google (Gemini) APIs
- **Action Interpreter/Executor**: Parses LLM outputs and executes actions across multiple domains
- **Terminal-Based UI**: Clean, user-friendly command-line interface with rich formatting
- **Safety & Error Handling**: Validates actions, requires confirmations for destructive operations, and handles errors gracefully
- **Comprehensive Logging**: All actions are logged for auditability
- **Focused File Renaming Agent**: Specialized agent for intelligent file renaming with:
  - Date-based ordering (oldest/newest first)
  - Pattern preservation (leading zeros, underscores, etc.)
  - Large directory support (500+ files)
  - Automatic file type filtering
  - Swap/reversal handling

## Project Structure

```
CS4680Project2/
├── main.py              # Main entry point (general AI agent)
├── ai_file_renamer.py   # Focused file renaming agent (uses gpt-4o-mini)
├── llm_interface.py     # Simple LLM interface for file renaming
├── config.py            # Configuration management (for general agent)
├── llm_integration.py   # LLM API integration (for general agent)
├── action_executor.py   # Action parsing and execution
├── ui.py                # User interface
├── safety.py            # Safety checks and validation
├── logger.py            # Logging module
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
   # For file renaming agent (ai_file_renamer.py), you only need:
   OPENAI_API_KEY=your_actual_api_key_here
   
   # For general agent (main.py), also set:
   LLM_PROVIDER=openai  # or anthropic, or google
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
   - **Anthropic**: Get your key from https://console.anthropic.com/
   - **Google**: Get your key from https://makersuite.google.com/app/apikey
   
   **Note**: The `.env` file is already in `.gitignore` and will not be committed to git.

## Usage

### General AI Agent

Run the general-purpose agent:
```bash
python main.py
```

The agent will start and display a welcome message. You can then interact with it using natural language:

### File Renaming Agent

For a focused file renaming use case, run:
```bash
python ai_file_renamer.py
```

This agent uses **OpenAI's `gpt-4o-mini` model** (a cost-effective "nano"-style model) specifically optimized for JSON planning tasks. It's perfect for this use case since we need fast, structured output rather than deep reasoning.

**Setup:**
1. Set your OpenAI API key (see Installation section above for detailed instructions)
   - **Easiest**: Create a `.env` file with `OPENAI_API_KEY=your_key_here`
   - **Alternative**: Set environment variable `OPENAI_API_KEY`

2. The agent uses `gpt-4o-mini` by default (configurable via `OPENAI_MODEL` in `.env`)

**Workflow:**
1. Asks for a directory to analyze
2. Asks for a natural-language rename instruction
3. Calls the LLM (gpt-4o-mini) to generate a structured rename plan as JSON
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

### General Agent Examples

The general agent supports various operations:

- **File Operations**:
  - "Create a file called test.txt with the content 'Hello World'"
  - "Read the contents of README.md"
  - "List all files in the current directory"
  - "Delete the file test.txt"

- **System Commands**:
  - "Execute the command 'python --version'"
  - "Run 'ls -la' to list files"

- **Information Requests**:
  - "What is Python?"
  - "Explain how file systems work"

- **Other Commands**:
  - `help` - Show help information
  - `exit` or `quit` - Exit the agent

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

### LLM Integration Modules

**`llm_interface.py`** (File Renaming Agent):
- Focused interface for file renaming using OpenAI's `gpt-4o-mini`
- Uses `response_format={"type": "json_object"}` for structured JSON output
- Simple, cost-effective approach optimized for JSON planning tasks

**`llm_integration.py`** (General Agent):
- Connects to LLM APIs (OpenAI, Anthropic, Google)
- Handles API errors and rate limiting with retry logic
- Provides structured prompts to guide LLM responses

### Action Executor (`action_executor.py`)
- Parses LLM JSON responses
- Executes actions across different domains:
  - File operations (read, write, create, delete, list)
  - System commands
  - API calls
  - Database operations (placeholder)
  - Information display

### User Interface (`ui.py`)
- Terminal-based interface using Rich library
- Displays actions, results, and information
- Handles user confirmations
- Provides help and guidance

### Safety Module (`safety.py`)
- Validates actions before execution
- Identifies dangerous patterns
- Determines when confirmation is required
- Sanitizes commands

### Logger (`logger.py`)
- Logs all actions, errors, and safety checks
- Writes to both console and log file
- Configurable log levels

## Configuration

Edit `.env` file to configure:

- **LLM Provider**: Choose `openai`, `anthropic`, or `google`
- **API Keys**: Set the appropriate API key for your chosen provider
- **Model**: Specify which model to use (defaults provided)
- **Logging**: Configure log file and log level

## Logging

All agent activities are logged to timestamped files in the `logs/` directory:
- **General Agent**: `logs/agent.log`
- **File Renamer**: `logs/YYYY-MM-DD_HH-MM-SS.log` (one per session)

Logs include:
- Actions taken
- LLM requests and responses
- Errors and exceptions
- Safety checks
- User confirmations
- File rename operations with before/after names

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

- Database operations are currently placeholders and not fully implemented
- API calls require proper authentication setup
- System commands are limited to basic operations for safety
- Very large directories (>500 files) may require pattern-based instructions for best results
- Some complex multi-step operations may require multiple interactions

## Requirements Compliance

This project fully meets all requirements for CS4680 Project 2:

✅ **LLM Integration Module**
- Connects to multiple LLM APIs (OpenAI, Anthropic, Google)
- Sends prompts and receives responses
- Handles API errors and rate limiting

✅ **Action Interpreter/Executor**
- Parses LLM output to extract actionable commands
- Converts LLM responses into executable operations
- Executes actions across different domains (file operations, system commands, API calls, database operations)

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

