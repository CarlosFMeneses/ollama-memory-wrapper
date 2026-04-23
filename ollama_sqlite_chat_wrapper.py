"""
Ollama SQLite Chat Wrapper

A CLI-based local AI assistant powered by Ollama, featuring
SQLite-backed persistent conversation memory and dynamic model selection.

Copyright (C) 2026 Carlos F. Meneses

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "chat_memory.db"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
MAX_CONTEXT_MESSAGES = 20
SYSTEM_PROMPT = "You are a helpful local AI assistant. Be clear, practical, and concise."


class ChatStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
                """
            )
            conn.commit()

    def get_or_create_conversation(self, name: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM conversations WHERE name = ?",
                (name,),
            ).fetchone()

            if row:
                return int(row["id"])

            cursor = conn.execute(
                "INSERT INTO conversations (name, created_at) VALUES (?, ?)",
                (name, datetime.now().isoformat()),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def get_conversation_id_by_name(self, name: str) -> Optional[int]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM conversations WHERE name = ?",
                (name,),
            ).fetchone()

        if row:
            return int(row["id"])
        return None

    def save_message(self, conversation_id: int, role: str, content: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, content, datetime.now().isoformat()),
            )
            conn.commit()

    def load_recent_messages(
        self,
        conversation_id: int,
        limit: int = MAX_CONTEXT_MESSAGES,
    ) -> List[Dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, limit),
            ).fetchall()

        rows = list(reversed(rows))
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def list_conversations(self) -> List[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, created_at FROM conversations ORDER BY id ASC"
            ).fetchall()
        return list(rows)

    def delete_conversation(self, conversation_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            conn.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            conn.commit()


class OllamaClient:
    def __init__(self, chat_url: str = OLLAMA_CHAT_URL, model: Optional[str] = None) -> None:
        self.chat_url = chat_url
        self.model = model

    def list_models(self) -> List[str]:
        response = requests.get(OLLAMA_TAGS_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]

    def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.model:
            raise ValueError("No model selected.")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        response = requests.post(self.chat_url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]


class PersistentChatApp:
    def __init__(self, store: ChatStore, client: OllamaClient) -> None:
        self.store = store
        self.client = client

    def ensure_system_prompt(self, conversation_id: int) -> None:
        messages = self.store.load_recent_messages(conversation_id, limit=1)
        if messages:
            return

        self.store.save_message(conversation_id, "system", SYSTEM_PROMPT)

    def ask(self, conversation_name: str, user_text: str) -> str:
        conversation_id = self.store.get_or_create_conversation(conversation_name)
        self.ensure_system_prompt(conversation_id)

        self.store.save_message(conversation_id, "user", user_text)
        messages = self.store.load_recent_messages(conversation_id)

        assistant_text = self.client.chat(messages)
        self.store.save_message(conversation_id, "assistant", assistant_text)
        return assistant_text


def choose_model(client: OllamaClient) -> str:
    models = client.list_models()

    if not models:
        raise RuntimeError("No Ollama models are installed.")

    print("\nInstalled Ollama models:")
    for index, model_name in enumerate(models, start=1):
        print(f"  {index}. {model_name}")

    while True:
        choice = input("\nPick a model by number: ").strip()

        if not choice.isdigit():
            print("Please enter a number.")
            continue

        selected_index = int(choice) - 1
        if 0 <= selected_index < len(models):
            return models[selected_index]

        print("That number is out of range.")


def choose_conversation(store: ChatStore) -> str:
    while True:
        rows = store.list_conversations()

        print("\nConversation Manager")
        if rows:
            print("Existing conversations:")
            for index, row in enumerate(rows, start=1):
                print(f"  {index}. {row['name']}")
        else:
            print("No conversations yet.")

        print("\nOptions:")
        print("  [number] Open a conversation")
        print("  n        Start a new conversation")
        print("  d        Delete a conversation")

        choice = input("\nChoose an option: ").strip().lower()

        if choice == "n":
            name = input("Enter a new conversation name: ").strip()
            if name:
                return name
            print("Conversation name cannot be empty.")
            continue

        if choice == "d":
            if not rows:
                print("There are no conversations to delete.")
                continue

            delete_choice = input("Enter the number of the conversation to delete: ").strip()
            if not delete_choice.isdigit():
                print("Please enter a valid number.")
                continue

            delete_index = int(delete_choice) - 1
            if not (0 <= delete_index < len(rows)):
                print("That number is out of range.")
                continue

            row = rows[delete_index]
            confirm = input(
                f"Delete '{row['name']}'? (y/n): "
            ).strip().lower()

            if confirm == "y":
                store.delete_conversation(int(row["id"]))
                print(f"Conversation '{row['name']}' deleted.")
            else:
                print("Delete cancelled.")
            continue

        if choice.isdigit():
            selected_index = int(choice) - 1
            if 0 <= selected_index < len(rows):
                return str(rows[selected_index]["name"])
            print("That number is out of range.")
            continue

        print("Invalid option. Please choose a number, n, or d.")


def main() -> None:
    store = ChatStore(DB_PATH)
    client = OllamaClient()

    print("Persistent Ollama Chat")
    print("Type /exit to quit")
    print("Type /new to open or create a conversation")
    print("Type /delete to delete the current conversation")
    print("Type /model to switch models")

    try:
        selected_model = choose_model(client)
        client.model = selected_model
    except Exception as exc:
        print(f"Error selecting model: {exc}")
        return

    app = PersistentChatApp(store, client)
    conversation_name = choose_conversation(store)

    while True:
        user_text = input(f"\n[{conversation_name}] You: ").strip()

        if not user_text:
            continue

        if user_text == "/exit":
            print("Goodbye.")
            break

        if user_text == "/new":
            conversation_name = choose_conversation(store)
            continue

        if user_text == "/delete":
            current_id = store.get_conversation_id_by_name(conversation_name)
            if current_id is None:
                print("\nThat conversation does not exist.")
                conversation_name = choose_conversation(store)
                continue

            confirm = input(
                f"Delete '{conversation_name}'? (y/n): "
            ).strip().lower()

            if confirm == "y":
                store.delete_conversation(current_id)
                print(f"\nConversation '{conversation_name}' deleted.")
                conversation_name = choose_conversation(store)
            else:
                print("\nDelete cancelled.")
            continue

        if user_text == "/model":
            try:
                selected_model = choose_model(client)
                client.model = selected_model
                print(f"\nSwitched to model: {selected_model}")
            except Exception as exc:
                print(f"\nError selecting model: {exc}")
            continue

        try:
            reply = app.ask(conversation_name, user_text)
            print(f"\nAssistant ({client.model}): {reply}")
        except requests.exceptions.ConnectionError:
            print("\nError: Could not connect to Ollama. Is it running on localhost:11434?")
        except requests.HTTPError as exc:
            print(f"\nHTTP error from Ollama: {exc}")
        except Exception as exc:
            print(f"\nUnexpected error: {exc}")


if __name__ == "__main__":
    main()
