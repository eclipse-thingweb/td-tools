"""Tests for analyze-proto.py"""

import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent.parent
TOOL_PATH = TOOLS_DIR / "analyze-proto.py"


def test_self_test():
    """Run the tool's built-in self-test."""
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--self-test"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Self-test failed: {result.stderr}"
    assert "[PASS]" in result.stdout


def test_help():
    """Test that --help works."""
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "analyze" in result.stdout.lower() or "proto" in result.stdout.lower()


def test_parse_simple_proto(tmp_path):
    """Test parsing a simple proto file."""
    proto_file = tmp_path / "test.proto"
    proto_file.write_text("""
syntax = "proto3";
package test;

message TestMessage {
    uint32 id = 1;
    string name = 2;
}

enum Status {
    UNKNOWN = 0;
    OK = 1;
}
""")
    
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), str(proto_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "TestMessage" in result.stdout
    assert "Status" in result.stdout


def test_json_output(tmp_path):
    """Test JSON output mode."""
    proto_file = tmp_path / "test.proto"
    proto_file.write_text("""
syntax = "proto3";
message Simple {
    uint32 id = 1;
}
""")
    
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), str(proto_file), "--json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert '"messages"' in result.stdout
    assert '"Simple"' in result.stdout


def test_output_file(tmp_path):
    """Test writing output to a file."""
    proto_file = tmp_path / "test.proto"
    proto_file.write_text("""
syntax = "proto3";
message Output {
    string data = 1;
}
""")
    
    output_file = tmp_path / "report.md"
    
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), str(proto_file), "-o", str(output_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert output_file.exists()
    content = output_file.read_text()
    assert "Output" in content
