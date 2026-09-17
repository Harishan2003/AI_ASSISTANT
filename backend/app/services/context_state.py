"""
Friday Universal Context State Manager
Maintains cross-application context (selected files, contacts, drafts, pending actions)
without wiping state when switching active windows.
"""

from __future__ import annotations
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class UniversalContextState:
    selected_contact: Optional[str] = None
    selected_file: Optional[str] = None
    selected_folder: Optional[str] = None
    selected_item: Optional[str] = None
    current_draft: Optional[str] = None
    draft_type: Optional[str] = None  # 'whatsapp', 'email', 'notepad'
    pending_action: Optional[str] = None

    def set_selected_file(self, file_path: str):
        if file_path and Path(file_path).exists():
            self.selected_file = str(file_path)
            print(f"[ContextState] Selected File set to: {self.selected_file}")

    def set_selected_contact(self, contact_name: str):
        if contact_name:
            self.selected_contact = contact_name.strip().title()
            print(f"[ContextState] Selected Contact set to: {self.selected_contact}")

    def set_draft(self, draft_text: str, draft_type: str = "whatsapp"):
        self.current_draft = draft_text.strip()
        self.draft_type = draft_type
        print(f"[ContextState] Draft ({draft_type}) set: '{self.current_draft}'")

    def clear_draft(self):
        self.current_draft = None
        self.draft_type = None

    def clear_all(self):
        self.selected_contact = None
        self.selected_file = None
        self.selected_folder = None
        self.selected_item = None
        self.current_draft = None
        self.draft_type = None
        self.pending_action = None


# Global Persistent Singleton Instance
context_state = UniversalContextState()