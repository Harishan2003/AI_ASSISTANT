"""
Safe Windows Filesystem Tools for Friday AI PC Agent.
Supports natural path resolution (Desktop, Documents, Downloads), content search,
safe operations, duplicate detection, and deletion confirmation guards.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.tool_base import BaseTool
from app.schemas.agent_schemas import PermissionLevel, ToolResult


def resolve_natural_path(path_str: str) -> Path:
    """Resolves natural language paths like 'Desktop', 'Downloads', 'Documents', '~'."""
    clean = path_str.strip().strip('"').strip("'")
    user_home = Path.home()
    
    mapping = {
        "desktop": user_home / "Desktop",
        "downloads": user_home / "Downloads",
        "download": user_home / "Downloads",
        "documents": user_home / "Documents",
        "document": user_home / "Documents",
        "pictures": user_home / "Pictures",
        "picture": user_home / "Pictures",
        "photos": user_home / "Pictures",
        "videos": user_home / "Videos",
        "video": user_home / "Videos",
        "music": user_home / "Music",
        "home": user_home,
        "~": user_home,
        "c:": Path("C:/"),
        "d:": Path("D:/"),
    }

    lower = clean.lower()
    if lower in mapping:
        return mapping[lower]

    for prefix, target_dir in mapping.items():
        if lower.startswith(f"{prefix}/") or lower.startswith(f"{prefix}\\"):
            remainder = clean[len(prefix) + 1:]
            return target_dir / remainder

    # Expand user ~
    expanded = os.path.expanduser(clean)
    p = Path(expanded)
    if not p.is_absolute():
        p = user_home / p
    return p


# ============================================================
# 1. LIST & SEARCH FILES
# ============================================================

class ListFilesArgs(BaseModel):
    path: str = Field("Desktop", description="Directory path (e.g. Desktop, Downloads, C:/Projects)")
    pattern: Optional[str] = Field(None, description="Glob pattern (e.g. *.pdf, *.py)")
    recursive: bool = Field(False, description="Whether to search recursively")


class ListFilesTool(BaseTool):
    name = "list_files"
    description = "List files in a directory with file sizes, modified dates, and extensions. Supports natural paths like 'Desktop' or 'Downloads'."
    permission_level = PermissionLevel.SAFE
    category = "filesystem"
    args_schema = ListFilesArgs

    async def execute(self, path: str = "Desktop", pattern: Optional[str] = None, recursive: bool = False, **kwargs: Any) -> ToolResult:
        try:
            target_path = resolve_natural_path(path)
            if not target_path.exists():
                return ToolResult(success=False, error=f"Directory '{path}' does not exist.", code="PATH_NOT_FOUND")
            if not target_path.is_dir():
                return ToolResult(success=False, error=f"Path '{path}' is a file, not a directory.", code="NOT_A_DIRECTORY")

            entries: List[Dict[str, Any]] = []
            iterator = target_path.rglob(pattern or "*") if recursive else target_path.glob(pattern or "*")

            count = 0
            for item in iterator:
                if count >= 200:
                    break
                try:
                    stat = item.stat()
                    entries.append({
                        "name": item.name,
                        "path": str(item.resolve()),
                        "is_dir": item.is_dir(),
                        "size_bytes": stat.st_size if item.is_file() else 0,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2) if item.is_file() else 0,
                        "modified_ts": stat.st_mtime
                    })
                    count += 1
                except (PermissionError, OSError):
                    continue

            return ToolResult(
                success=True,
                data={"total": len(entries), "path": str(target_path), "entries": entries},
                metadata={"summary": f"Found {len(entries)} items in '{target_path.name}'."}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to list files: {str(e)}")


class SearchFilesArgs(BaseModel):
    query: str = Field(..., description="File name or extension search query")
    search_dir: str = Field("Desktop", description="Root search directory (e.g. Desktop, Downloads, Documents)")
    max_results: int = Field(20, description="Max matching files to return")


class SearchFilesTool(BaseTool):
    name = "search_files"
    description = "Search for files by name or extension across Windows directories."
    permission_level = PermissionLevel.SAFE
    category = "filesystem"
    args_schema = SearchFilesArgs

    async def execute(
        self,
        query: str = "",
        search_dir: str = "Desktop",
        max_results: int = 20,
        pattern: Optional[str] = None,
        directory: Optional[str] = None,
        **kwargs: Any
    ) -> ToolResult:
        try:
            effective_q = pattern or query or ""
            effective_dir = directory or search_dir or "Desktop"
            root = resolve_natural_path(effective_dir)
            if not root.exists():
                return ToolResult(tool_name=self.name, success=False, error=f"Directory '{effective_dir}' not found.")

            results: List[Dict[str, Any]] = []
            clean_q = effective_q.lower().strip().replace("*", "")

            for item in root.rglob("*"):
                if not clean_q or clean_q in item.name.lower():
                    try:
                        stat = item.stat()
                        results.append({
                            "name": item.name,
                            "path": str(item.resolve()),
                            "is_dir": item.is_dir(),
                            "size_mb": round(stat.st_size / (1024 * 1024), 2) if item.is_file() else 0,
                        })
                        if len(results) >= max_results:
                            break
                    except (PermissionError, OSError):
                        continue

            return ToolResult(
                tool_name=self.name,
                success=True,
                data={"total": len(results), "query": effective_q, "matches": results, "results": results},
                metadata={"summary": f"Found {len(results)} files matching '{effective_q}' in {root.name}."}
            )
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, error=f"Search failed: {str(e)}")


class SearchContentArgs(BaseModel):
    query: str = Field(..., description="Text content to search for inside files")
    search_dir: str = Field("Desktop", description="Root directory to search inside")
    file_extensions: Optional[List[str]] = Field(None, description="Filter extensions (e.g. ['.txt', '.py', '.md'])")


class SearchContentTool(BaseTool):
    name = "search_content"
    description = "Search for specific text content inside files (e.g. searching code, notes, logs)."
    permission_level = PermissionLevel.SAFE
    category = "filesystem"
    args_schema = SearchContentArgs

    async def execute(
        self,
        query: str,
        search_dir: str = "Desktop",
        file_extensions: Optional[List[str]] = None,
        directory: Optional[str] = None,
        **kwargs: Any
    ) -> ToolResult:
        try:
            effective_dir = directory or search_dir or "Desktop"
            root = resolve_natural_path(effective_dir)
            exts = [e.lower() for e in file_extensions] if file_extensions else [".txt", ".py", ".md", ".json", ".csv", ".log", ".js", ".ts", ".html", ".css", ".env", ".yaml", ".yml"]
            matches: List[Dict[str, Any]] = []
            clean_q = query.lower()

            for item in root.rglob("*"):
                if item.is_file() and item.suffix.lower() in exts:
                    try:
                        text = item.read_text(encoding="utf-8", errors="ignore")
                        if clean_q in text.lower():
                            # Find matching lines
                            matching_lines = []
                            for idx, line in enumerate(text.splitlines()):
                                if clean_q in line.lower():
                                    matching_lines.append({"line": idx + 1, "snippet": line.strip()[:150]})
                                    if len(matching_lines) >= 3:
                                        break
                            matches.append({
                                "file": str(item.resolve()),
                                "matches": matching_lines
                            })
                            if len(matches) >= 15:
                                break
                    except Exception:
                        continue

            return ToolResult(
                success=True,
                data={"total_files": len(matches), "query": query, "matches": matches},
                metadata={"summary": f"Found text '{query}' in {len(matches)} files."}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Content search error: {str(e)}")


# ============================================================
# 2. READ & WRITE & GET INFO
# ============================================================

class ReadFileArgs(BaseModel):
    path: str = Field(..., description="Path to the file to read")
    max_lines: int = Field(200, description="Max lines to read")
    offset: int = Field(0, description="Line offset to start reading from")


class ReadTextFileTool(BaseTool):
    name = "read_text_file"
    description = "Read the text contents of a file (source code, configuration, text notes, logs, markdown)."
    permission_level = PermissionLevel.SAFE
    category = "filesystem"
    args_schema = ReadFileArgs

    async def execute(self, path: str, max_lines: int = 200, offset: int = 0, **kwargs: Any) -> ToolResult:
        try:
            target = resolve_natural_path(path)
            if not target.exists() or not target.is_file():
                return ToolResult(success=False, error=f"File '{path}' does not exist.", code="FILE_NOT_FOUND")

            lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
            total_lines = len(lines)
            selected_lines = lines[offset:offset + max_lines]
            content = "\n".join(selected_lines)

            return ToolResult(
                success=True,
                data={"path": str(target), "total_lines": total_lines, "offset": offset, "content": content},
                metadata={"summary": f"Read {len(selected_lines)}/{total_lines} lines from '{target.name}'."}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to read file: {str(e)}")


class WriteFileArgs(BaseModel):
    path: str = Field(..., description="Path to the file")
    content: str = Field(..., description="Text content to write")
    append: bool = Field(False, description="Whether to append instead of overwriting")


class WriteTextFileTool(BaseTool):
    name = "write_text_file"
    description = "Create or write text content to a file. Supports appending or overwriting."
    permission_level = PermissionLevel.SAFE
    category = "filesystem"
    args_schema = WriteFileArgs

    async def execute(self, path: str, content: str, append: bool = False, **kwargs: Any) -> ToolResult:
        try:
            target = resolve_natural_path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(target, mode, encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                success=True,
                data={"path": str(target), "bytes_written": len(content.encode("utf-8")), "appended": append},
                metadata={"summary": f"Successfully wrote to '{target.name}'."}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to write file: {str(e)}")


# ============================================================
# 3. CREATE, MOVE, COPY, DELETE, DUPLICATES
# ============================================================

class CreateFolderArgs(BaseModel):
    path: str = Field(..., description="Path of the directory to create (e.g. Desktop/Projects)")


class CreateFolderTool(BaseTool):
    name = "create_folder"
    description = "Create a new directory / folder."
    permission_level = PermissionLevel.SAFE
    category = "filesystem"
    args_schema = CreateFolderArgs

    async def execute(self, path: str, **kwargs: Any) -> ToolResult:
        try:
            target = resolve_natural_path(path)
            target.mkdir(parents=True, exist_ok=True)
            return ToolResult(
                success=True,
                data={"created_path": str(target)},
                metadata={"summary": f"Created folder '{target.name}' at {target}."}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to create folder: {str(e)}")


class MoveFileArgs(BaseModel):
    source: str = Field(..., description="Source file/folder path")
    destination: str = Field(..., description="Destination file/folder path")


class MoveFileTool(BaseTool):
    name = "move_file"
    description = "Move or rename a file or folder."
    permission_level = PermissionLevel.SAFE
    category = "filesystem"
    args_schema = MoveFileArgs

    async def execute(self, source: str, destination: str, **kwargs: Any) -> ToolResult:
        try:
            src = resolve_natural_path(source)
            dst = resolve_natural_path(destination)
            if not src.exists():
                return ToolResult(success=False, error=f"Source '{source}' does not exist.")

            dst.parent.mkdir(parents=True, exist_ok=True)
            res_dst = shutil.move(str(src), str(dst))
            return ToolResult(
                success=True,
                data={"source": str(src), "destination": str(res_dst)},
                metadata={"summary": f"Moved '{src.name}' to '{dst}'."}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to move: {str(e)}")


class DeleteFileArgs(BaseModel):
    path: str = Field(..., description="Path of file or folder to delete")


class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Permanently delete a file or folder. Requires human confirmation before execution."
    permission_level = PermissionLevel.CONFIRM
    category = "filesystem"
    args_schema = DeleteFileArgs

    async def execute(self, path: str, **kwargs: Any) -> ToolResult:
        try:
            target = resolve_natural_path(path)
            if not target.exists():
                return ToolResult(success=False, error=f"Target '{path}' does not exist.")

            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

            return ToolResult(
                success=True,
                data={"deleted_path": str(target)},
                metadata={"summary": f"Deleted '{target.name}'."}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to delete: {str(e)}")


class FindDuplicateFilesArgs(BaseModel):
    directory: str = Field("Downloads", description="Directory to scan for duplicate files")
    min_size_kb: int = Field(50, description="Minimum file size in KB to inspect")


class FindDuplicateFilesTool(BaseTool):
    name = "find_duplicate_files"
    description = "Find identical duplicate files in a directory using SHA-256 content hashing."
    permission_level = PermissionLevel.SAFE
    category = "filesystem"
    args_schema = FindDuplicateFilesArgs

    async def execute(self, directory: str = "Downloads", min_size_kb: int = 50, **kwargs: Any) -> ToolResult:
        try:
            root = resolve_natural_path(directory)
            if not root.exists():
                return ToolResult(success=False, error=f"Directory '{directory}' does not exist.")

            size_map: Dict[int, List[Path]] = {}
            for item in root.rglob("*"):
                if item.is_file():
                    try:
                        sz = item.stat().st_size
                        if sz >= min_size_kb * 1024:
                            size_map.setdefault(sz, []).append(item)
                    except Exception:
                        continue

            duplicates: List[Dict[str, Any]] = []
            for sz, files in size_map.items():
                if len(files) > 1:
                    hash_map: Dict[str, List[Path]] = {}
                    for f in files:
                        try:
                            h = hashlib.sha256(f.read_bytes()).hexdigest()
                            hash_map.setdefault(h, []).append(f)
                        except Exception:
                            continue
                    for h, dup_list in hash_map.items():
                        if len(dup_list) > 1:
                            duplicates.append({
                                "hash": h,
                                "size_mb": round(sz / (1024 * 1024), 2),
                                "files": [str(p.resolve()) for p in dup_list]
                            })

            return ToolResult(
                success=True,
                data={"total_duplicate_groups": len(duplicates), "duplicates": duplicates},
                metadata={"summary": f"Found {len(duplicates)} duplicate file groups in {root.name}."}
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Duplicate search error: {str(e)}")
