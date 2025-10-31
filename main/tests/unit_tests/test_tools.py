"""Test cases for tools.py document management functions."""

import json
import os
import sys
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock

# Add src to path for imports
_test_dir = os.path.dirname(os.path.abspath(__file__))
_main_dir = os.path.dirname(os.path.dirname(_test_dir))
_src_dir = os.path.join(_main_dir, "src")
sys.path.insert(0, _src_dir)

from react_agent import tools


@pytest.fixture
def temp_dirs():
    """Create temporary directories for config, content, and output."""
    base_temp = tempfile.mkdtemp()
    config_dir = os.path.join(base_temp, "config")
    content_dir = os.path.join(base_temp, "content")
    output_dir = os.path.join(base_temp, "docx")
    
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(content_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    yield {
        "base": base_temp,
        "config": config_dir,
        "content": content_dir,
        "output": output_dir
    }
    
    # Cleanup
    shutil.rmtree(base_temp, ignore_errors=True)


@pytest.fixture
def mock_env_vars(temp_dirs, monkeypatch):
    """Set environment variables for test directories."""
    monkeypatch.setenv("DOCX_CONFIG_DIR", temp_dirs["config"])
    monkeypatch.setenv("DOCX_CONTENT_DIR", temp_dirs["content"])
    monkeypatch.setenv("DOCX_OUTPUT_DIR", temp_dirs["output"])
    
    # Reload module to pick up new env vars
    import importlib
    importlib.reload(tools)


@pytest.fixture
def sample_content_file(temp_dirs, mock_env_vars):
    """Create a sample content file with test data."""
    content = {
        "Introduction": [
            {"type": "heading", "text": "Introduction", "level": 1},
            {"type": "paragraph", "text": "This is the introduction section."}
        ],
        "Technical Details": [
            {"type": "heading", "text": "Technical Details", "level": 1},
            {"type": "paragraph", "text": "Technical information here."}
        ]
    }
    
    # Write versioned file using the module's directory
    import time
    timestamp = int(time.time())
    filepath = os.path.join(tools.CONTENT_DIR, f"content_{timestamp}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(content, f, indent=2)
    
    return filepath, content


@pytest.fixture
def sample_config_file(temp_dirs, mock_env_vars):
    """Create a sample config file with test data."""
    config = {
        "metadata": {
            "title": "Test Document",
            "author": "Test Author",
            "page_size": "A4",
            "orientation": "portrait",
            "margins": {"top": 2.54, "bottom": 2.54, "left": 2.54, "right": 2.54}
        },
        "styles": {
            "heading": [
                {"level": 1, "font": "Arial", "size": 18, "bold": True}
            ],
            "paragraph": {"font": "Arial", "size": 12}
        }
    }
    
    # Write versioned file using the module's directory
    import time
    timestamp = int(time.time())
    filepath = os.path.join(tools.CONFIG_DIR, f"config_{timestamp}.json")
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    
    return filepath, config


class TestCreateSection:
    """Test cases for create_section function."""
    
    def test_create_section_with_default_heading(self, mock_env_vars, sample_content_file):
        """Test creating a section without providing elements (auto-generates heading)."""
        result = tools.create_section("New Section")
        
        assert "Section 'New Section' created" in result
        assert "1 element(s)" in result
        
        # Verify section was created
        latest_content = tools._get_latest_versioned_file(tools.CONTENT_DIR, "content")
        with open(latest_content, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        assert "New Section" in content
        assert len(content["New Section"]) == 1
        assert content["New Section"][0]["type"] == "heading"
        assert content["New Section"][0]["text"] == "New Section"
    
    def test_create_section_with_custom_elements(self, mock_env_vars, sample_content_file):
        """Test creating a section with custom elements."""
        elements = [
            {"type": "heading", "text": "Executive Summary", "level": 1},
            {"type": "paragraph", "text": "This is a summary paragraph."}
        ]
        
        result = tools.create_section("Executive Summary", elements)
        
        assert "Section 'Executive Summary' created" in result
        assert "2 element(s)" in result
        
        # Verify section and elements
        latest_content = tools._get_latest_versioned_file(tools.CONTENT_DIR, "content")
        with open(latest_content, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        assert "Executive Summary" in content
        assert len(content["Executive Summary"]) == 2
        assert content["Executive Summary"][0]["type"] == "heading"
        assert content["Executive Summary"][1]["type"] == "paragraph"
    
    def test_create_section_already_exists(self, mock_env_vars, sample_content_file):
        """Test creating a section that already exists."""
        result = tools.create_section("Introduction")
        
        assert "Error" in result
        assert "already exists" in result
    
    def test_create_section_invalid_element_not_dict(self, mock_env_vars, sample_content_file):
        """Test creating section with invalid element (not a dictionary)."""
        elements = ["not a dict", {"type": "heading", "text": "Test", "level": 1}]
        
        result = tools.create_section("Test Section", elements)
        
        assert "Error" in result
        assert "must be a dictionary" in result
    
    def test_create_section_missing_type_field(self, mock_env_vars, sample_content_file):
        """Test creating section with element missing 'type' field."""
        elements = [{"text": "Missing type field"}]
        
        result = tools.create_section("Test Section", elements)
        
        assert "Error" in result
        assert "missing 'type' field" in result


class TestEditConfig:
    """Test cases for edit_config function."""
    
    def test_edit_config_update_metadata(self, mock_env_vars, sample_config_file):
        """Test updating config metadata."""
        updates = {
            "metadata": {
                "title": "Updated Title",
                "author": "Updated Author"
            }
        }
        
        result = tools.edit_config(updates)
        
        assert "Configuration updated successfully" in result
        
        # Verify updates were merged
        latest_config = tools._get_latest_versioned_file(tools.CONFIG_DIR, "config")
        with open(latest_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        assert config["metadata"]["title"] == "Updated Title"
        assert config["metadata"]["author"] == "Updated Author"
        # Verify existing fields are preserved
        assert config["metadata"]["page_size"] == "A4"
    
    def test_edit_config_add_new_style(self, mock_env_vars, sample_config_file):
        """Test adding new style configuration."""
        updates = {
            "styles": {
                "table": {"border": True, "cell_padding": 0.3}
            }
        }
        
        result = tools.edit_config(updates)
        
        assert "Configuration updated successfully" in result
        
        # Verify new style was added
        latest_config = tools._get_latest_versioned_file(tools.CONFIG_DIR, "config")
        with open(latest_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        assert "table" in config["styles"]
        assert config["styles"]["table"]["cell_padding"] == 0.3
    
    def test_edit_config_deep_merge(self, mock_env_vars, sample_config_file):
        """Test that nested dictionaries are properly merged."""
        updates = {
            "metadata": {
                "margins": {
                    "top": 3.0,
                    "bottom": 2.54,
                    "left": 2.54,
                    "right": 2.54
                }
            }
        }
        
        result = tools.edit_config(updates)
        
        assert "Configuration updated successfully" in result
        
        # Verify deep merge worked
        latest_config = tools._get_latest_versioned_file(tools.CONFIG_DIR, "config")
        with open(latest_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        assert config["metadata"]["margins"]["top"] == 3.0
        assert config["metadata"]["margins"]["bottom"] == 2.54
        assert config["metadata"]["margins"]["left"] == 2.54


class TestUpdateContent:
    """Test cases for update_content function."""
    
    def test_update_content_success(self, mock_env_vars, sample_content_file):
        """Test successfully updating an element in a section."""
        updated_element = {
            "type": "paragraph",
            "text": "Updated paragraph text"
        }
        
        result = tools.update_content("Introduction", 1, updated_element)
        
        assert "updated successfully" in result
        
        # Verify update
        latest_content = tools._get_latest_versioned_file(tools.CONTENT_DIR, "content")
        with open(latest_content, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        assert content["Introduction"][1]["text"] == "Updated paragraph text"
        assert content["Introduction"][1]["type"] == "paragraph"
    
    def test_update_content_section_not_found(self, mock_env_vars, sample_content_file):
        """Test updating content in non-existent section."""
        updated_element = {"type": "paragraph", "text": "Test"}
        
        result = tools.update_content("NonExistent", 0, updated_element)
        
        assert "Error" in result
        assert "not found" in result
    
    def test_update_content_invalid_index_negative(self, mock_env_vars, sample_content_file):
        """Test updating with negative index."""
        updated_element = {"type": "paragraph", "text": "Test"}
        
        result = tools.update_content("Introduction", -1, updated_element)
        
        assert "Error" in result
        assert "Invalid index" in result
    
    def test_update_content_invalid_index_too_large(self, mock_env_vars, sample_content_file):
        """Test updating with index beyond section length."""
        updated_element = {"type": "paragraph", "text": "Test"}
        
        result = tools.update_content("Introduction", 10, updated_element)
        
        assert "Error" in result
        assert "Invalid index" in result
    
    def test_update_content_element_not_dict(self, mock_env_vars, sample_content_file):
        """Test updating with element that's not a dictionary."""
        result = tools.update_content("Introduction", 0, "not a dict")
        
        assert "Error" in result
        assert "must be a dictionary" in result
    
    def test_update_content_missing_type(self, mock_env_vars, sample_content_file):
        """Test updating with element missing 'type' field."""
        updated_element = {"text": "Missing type"}
        
        result = tools.update_content("Introduction", 0, updated_element)
        
        assert "Error" in result
        assert "missing 'type' field" in result
    
    def test_update_content_section_not_list(self, mock_env_vars):
        """Test updating when section doesn't contain a list."""
        # Create malformed content
        content = {
            "BadSection": "not a list"
        }
        import time
        timestamp = int(time.time())
        filepath = os.path.join(tools.CONTENT_DIR, f"content_{timestamp}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f)
        
        updated_element = {"type": "paragraph", "text": "Test"}
        
        result = tools.update_content("BadSection", 0, updated_element)
        
        assert "Error" in result
        assert "does not contain a list" in result


class TestGetSections:
    """Test cases for get_sections function."""
    
    def test_get_sections_success(self, mock_env_vars, sample_content_file):
        """Test successfully getting all sections."""
        result = tools.get_sections()
        
        # Should return JSON string
        sections = json.loads(result)
        
        assert isinstance(sections, list)
        assert len(sections) >= 2
        
        # Check structure
        for section in sections:
            assert "section_name" in section
            assert "heading" in section
            assert "element_count" in section
        
        # Verify specific sections
        section_names = [s["section_name"] for s in sections]
        assert "Introduction" in section_names
        assert "Technical Details" in section_names
    
    def test_get_sections_no_heading(self, mock_env_vars):
        """Test getting sections when some have no heading."""
        content = {
            "Section1": [
                {"type": "paragraph", "text": "No heading here"}
            ],
            "Section2": [
                {"type": "heading", "text": "Has Heading", "level": 1}
            ]
        }
        
        import time
        timestamp = int(time.time())
        filepath = os.path.join(tools.CONTENT_DIR, f"content_{timestamp}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f)
        
        result = tools.get_sections()
        sections = json.loads(result)
        
        assert len(sections) == 2
        section1 = next(s for s in sections if s["section_name"] == "Section1")
        assert section1["heading"] == "No heading"


class TestGetContent:
    """Test cases for get_content function."""
    
    def test_get_content_success(self, mock_env_vars, sample_content_file):
        """Test successfully getting content from a section."""
        result = tools.get_content("Introduction")
        
        # Should return JSON string
        content = json.loads(result)
        
        assert isinstance(content, list)
        assert len(content) == 2
        assert content[0]["type"] == "heading"
        assert content[1]["type"] == "paragraph"
    
    def test_get_content_section_not_found(self, mock_env_vars, sample_content_file):
        """Test getting content from non-existent section."""
        result = tools.get_content("NonExistentSection")
        
        assert "Error" in result
        assert "Section not found" in result or "not found" in result
    
    def test_get_content_by_heading_match(self, mock_env_vars, sample_content_file):
        """Test getting content by matching heading text."""
        result = tools.get_content("Introduction")
        
        # Should find by heading match
        content = json.loads(result)
        assert len(content) > 0


class TestGetContentByHeading:
    """Test cases for get_content_by_heading function."""
    
    def test_get_content_by_heading_exact_match(self, mock_env_vars, sample_content_file):
        """Test finding content by exact heading match."""
        result = tools.get_content_by_heading("Introduction")
        
        data = json.loads(result)
        
        assert "section_name" in data
        assert "content" in data
        assert data["section_name"] == "Introduction"
        assert isinstance(data["content"], list)
    
    def test_get_content_by_heading_partial_match(self, mock_env_vars, sample_content_file):
        """Test finding content by partial heading match."""
        result = tools.get_content_by_heading("Technical")
        
        data = json.loads(result)
        
        assert data["section_name"] == "Technical Details"
        assert "Technical Details" in data["content"][0]["text"]
    
    def test_get_content_by_heading_case_insensitive(self, mock_env_vars, sample_content_file):
        """Test case-insensitive heading search."""
        result = tools.get_content_by_heading("introduction")
        
        data = json.loads(result)
        
        assert data["section_name"] == "Introduction"
    
    def test_get_content_by_heading_not_found(self, mock_env_vars, sample_content_file):
        """Test when heading is not found."""
        result = tools.get_content_by_heading("NonExistentHeading")
        
        assert "Error" in result
        assert "No section found" in result


class TestInsertContentAfterHeading:
    """Test cases for insert_content_after_heading function."""
    
    def test_insert_content_after_heading_success(self, mock_env_vars, sample_content_file):
        """Test successfully inserting content after a heading."""
        new_element = {
            "type": "paragraph",
            "text": "New paragraph inserted here"
        }
        
        result = tools.insert_content_after_heading("Introduction", new_element)
        
        assert "Element inserted" in result
        
        # Verify insertion
        latest_content = tools._get_latest_versioned_file(tools.CONTENT_DIR, "content")
        with open(latest_content, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        # Should have 3 elements now (heading, new paragraph, original paragraph)
        assert len(content["Introduction"]) == 3
        assert content["Introduction"][1]["type"] == "paragraph"
        assert content["Introduction"][1]["text"] == "New paragraph inserted here"
    
    def test_insert_content_after_heading_partial_match(self, mock_env_vars, sample_content_file):
        """Test inserting with partial heading match."""
        new_element = {
            "type": "paragraph",
            "text": "Inserted after Technical"
        }
        
        result = tools.insert_content_after_heading("Technical", new_element)
        
        assert "Element inserted" in result
        
        latest_content = tools._get_latest_versioned_file(tools.CONTENT_DIR, "content")
        with open(latest_content, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        # Verify insertion in Technical Details section
        assert len(content["Technical Details"]) == 3
        assert content["Technical Details"][1]["text"] == "Inserted after Technical"
    
    def test_insert_content_after_heading_case_insensitive(self, mock_env_vars, sample_content_file):
        """Test case-insensitive heading search."""
        new_element = {
            "type": "paragraph",
            "text": "Case insensitive test"
        }
        
        result = tools.insert_content_after_heading("introduction", new_element)
        
        assert "Element inserted" in result
    
    def test_insert_content_after_heading_not_found(self, mock_env_vars, sample_content_file):
        """Test inserting when heading is not found."""
        new_element = {
            "type": "paragraph",
            "text": "Test"
        }
        
        result = tools.insert_content_after_heading("NonExistentHeading", new_element)
        
        assert "Error" in result
        assert "No heading found" in result
    
    def test_insert_content_after_heading_invalid_element(self, mock_env_vars, sample_content_file):
        """Test inserting with invalid element (not a dict)."""
        result = tools.insert_content_after_heading("Introduction", "not a dict")
        
        assert "Error" in result
        assert "must be a dictionary" in result
    
    def test_insert_content_after_heading_missing_type(self, mock_env_vars, sample_content_file):
        """Test inserting element missing 'type' field."""
        new_element = {"text": "Missing type"}
        
        result = tools.insert_content_after_heading("Introduction", new_element)
        
        assert "Error" in result
        assert "missing 'type' field" in result
    
    def test_insert_content_after_heading_multiple_matches(self, mock_env_vars):
        """Test that insertion stops at first matching heading."""
        content = {
            "Section1": [
                {"type": "heading", "text": "Test Heading", "level": 1},
                {"type": "paragraph", "text": "First section"}
            ],
            "Section2": [
                {"type": "heading", "text": "Test Heading Different", "level": 1},
                {"type": "paragraph", "text": "Second section"}
            ]
        }
        
        import time
        timestamp = int(time.time())
        filepath = os.path.join(tools.CONTENT_DIR, f"content_{timestamp}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f)
        
        new_element = {"type": "paragraph", "text": "Inserted"}
        
        result = tools.insert_content_after_heading("Test Heading", new_element)
        
        assert "Element inserted" in result
        
        # Verify only first match was used
        latest_content = tools._get_latest_versioned_file(tools.CONTENT_DIR, "content")
        with open(latest_content, 'r', encoding='utf-8') as f:
            updated_content = json.load(f)
        
        # Section1 should have 3 elements (heading, inserted, paragraph)
        assert len(updated_content["Section1"]) == 3
        # Section2 should remain unchanged
        assert len(updated_content["Section2"]) == 2

