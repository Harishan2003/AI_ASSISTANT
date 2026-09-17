"""
Tests for Filesystem and Directory Management Tools.
"""

import os
import tempfile
import pytest
from app.tools.filesystem.file_ops import (
    ListFilesTool,
    SearchFilesTool,
    SearchContentTool,
    ReadTextFileTool,
    WriteTextFileTool,
    CreateFolderTool,
    MoveFileTool,
    DeleteFileTool,
    FindDuplicateFilesTool
)
from app.schemas.agent_schemas import PermissionLevel


def test_file_operations_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Create folder
        create_folder_tool = CreateFolderTool()
        res_folder = create_folder_tool.run(path=os.path.join(tmpdir, "test_dir"))
        assert res_folder.success is True

        # 2. Write file
        write_tool = WriteTextFileTool()
        test_file_path = os.path.join(tmpdir, "test_dir", "hello.txt")
        res_write = write_tool.run(path=test_file_path, content="Hello Friday AI Assistant!")
        assert res_write.success is True

        # 3. Read file
        read_tool = ReadTextFileTool()
        res_read = read_tool.run(path=test_file_path)
        assert res_read.success is True
        assert "Hello Friday AI Assistant!" in res_read.data["content"]

        # 4. Search files
        search_files_tool = SearchFilesTool()
        res_sf = search_files_tool.run(pattern="*.txt", directory=tmpdir)
        assert res_sf.success is True
        assert len(res_sf.data["matches"]) == 1

        # 5. Search content
        search_content_tool = SearchContentTool()
        res_sc = search_content_tool.run(query="Assistant", directory=tmpdir)
        assert res_sc.success is True
        assert len(res_sc.data["matches"]) >= 1

        # 6. Delete permission level
        delete_tool = DeleteFileTool()
        assert delete_tool.permission_level == PermissionLevel.CONFIRM

        # Execute delete
        res_del = delete_tool.run(path=test_file_path)
        assert res_del.success is True
        assert not os.path.exists(test_file_path)


def test_duplicate_finder():
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = WriteTextFileTool()
        p1 = os.path.join(tmpdir, "dup1.txt")
        p2 = os.path.join(tmpdir, "dup2.txt")
        p3 = os.path.join(tmpdir, "unique.txt")

        write_tool.run(path=p1, content="Duplicate Content 12345")
        write_tool.run(path=p2, content="Duplicate Content 12345")
        write_tool.run(path=p3, content="Completely unique text")

        dup_tool = FindDuplicateFilesTool()
        res = dup_tool.run(directory=tmpdir, min_size_kb=0)
        assert res.success is True
        assert res.data["total_duplicate_groups"] == 1
        assert len(res.data["duplicates"][0]["files"]) == 2
