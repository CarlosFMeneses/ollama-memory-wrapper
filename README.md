**Author:** Carlos F. Meneses  
**Year:** 2026

# Ollama SQLite Chat Wrapper

A CLI-based local AI assistant powered by Ollama, featuring SQLite-backed persistent conversation memory and dynamic model selection.

## Features

- Persistent conversation memory via SQLite
- Multiple named conversation threads
- Dynamic Ollama model selection at runtime
- Human-readable timestamps ("just now", "3 mins ago", "yesterday")
- In-chat slash commands: `/new`, `/delete`, `/model`, `/exit`
- Clean object-oriented architecture with separation of concerns
- Full error handling for connection and HTTP failures

## Requirements

- Python 3.8+
- [Ollama](https://ollama.ai) running locally on port 11434
- At least one Ollama model installed (e.g. `ollama pull qwen2.5-coder:7b`)

## Installation

```bash
# Clone the repository
git clone https://github.com/CarlosFMeneses/ollama-memory-wrapper.git
cd ollama-memory-wrapper

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install requests
```

## Usage

```bash
python ollama_sqlite_chat_wrapper.py
```

On launch you will be prompted to select an installed Ollama model,
then open or create a named conversation.

## Chat Commands

| Command | Description |
|---|---|
| `/new` | Open or create a conversation |
| `/delete` | Delete current conversation |
| `/model` | Switch to a different model |
| `/exit` | Quit the application |

## Environment

This project was developed and tested on the following configuration:

| Component | Details |
|---|---|
| **Hardware** | Apple iMac M2 |
| **RAM** | 8GB Unified Memory |
| **OS** | macOS |
| **Package Manager** | Homebrew (brew) |
| **Python** | 3.13.3 |
| **Ollama** | 0.21.0 |
| **Models Tested** | qwen2.5:3b, qwen2.5:7b |
| **Model Storage** | External SSD |
| **IDE** | Xcode, Terminal |

> **Note:** Apple Silicon (M2) handles local LLM inference efficiently
> due to unified memory architecture. Models were stored and run from
> an external SSD. Performance may vary depending on storage type and
> speed — an external SSD with fast read speeds is recommended for
> smooth model loading. Both Python and Ollama were installed and
> managed via Homebrew. Ollama must be running locally on
> localhost:11434 before launching this application.
>
> **⚠️ Known Limitation:** This application uses a single shared
> SQLite database for all models. Conversation memory is not
> model-specific — retrieving memory across different models may
> produce erratic or inconsistent behavior. A future improvement
> would be to scope conversation memory per model. See Roadmap.

## Project Structure

    ollama-memory-wrapper/
    ├── ollama_sqlite_chat_wrapper.py  # Main application
    ├── chat_memory.db                 # SQLite database (auto-created, git-ignored)
    ├── README.md
    ├── LICENSE
    └── .gitignore

## Roadmap

- [ ] Long-term memory table for summarized knowledge
- [ ] Keyword search across conversation history
- [ ] Per-model conversation memory scoping to prevent cross-model memory conflicts
- [ ] Migration to Letta/MemGPT architecture
- [ ] Web interface for browser-based interaction
- [ ] macOS/iOS native app with local LLM inference and memory management

## License

Copyright (C) 2026 Carlos F. Meneses

This project is licensed under the GNU General Public License v3.0.
See [LICENSE](LICENSE) for details.
