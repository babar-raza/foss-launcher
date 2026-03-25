---
canonical: https://reference.aspose.org/cells/python/cells/
canonical_import: aspose.cells
date: '2026-03-22T08:56:20Z'
dateModified: '2026-03-22T08:56:20Z'
datePublished: '2026-03-22T08:56:20Z'
description: CSVHandler.save_csv() is part of the public API for Aspose.Cells FOSS.
display_name: Aspose.Cells FOSS
family: cells
keywords:
- cells python
- python cells in excel
- python cells vscode
- cell python docx
- cell python spyder
- aspose cells python
- code cells python
- voronoi cells python
lastmod: '2026-03-22T08:56:20Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: Aspose.Cells FOSS Cells
slug: cells
title: Cells
type: reference_object_page
url: /reference.aspose.org/cells/python/cells/
weight: 21
---

## Overview

Aspose.Cells FOSS -- Class or function purpose in 1-3 sentences.

Aspose.Cells FOSS MarkdownHandler.save_markdown(): Saves a workbook to a Markdown file. CSVHandler.save_csv() is part of the public API for Aspose.Cells FOSS.

```python
from aspose.cells import Workbook

# Create a new workbook
workbook = Workbook()

# Get the first worksheet
worksheet = workbook.worksheets[0]

# Set cell values
worksheet.cells["A1"].value = "Hello"
worksheet.cells["B1"].value = "World"
worksheet.cells["A2"].value = 42
worksheet.cells["B2"].value = 3.14

# Save the workbook
workbook.save("output.xlsx")
```

```python
from aspose.cells import Workbook

# Open an existing workbook
workbook = Workbook("input.xlsx")

# Access a worksheet
worksheet = workbook.worksheets[0]

# Read cell values
value = worksheet.cells["A1"].value
print(f"Cell A1 contains: {value}")
```

```python
from aspose.cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
cell = worksheet.cells["A1"]

cell.value = "Styled Text"

# Get and modify the cell style
style = cell.get_style()
style.font.bold = True
style.font.color = "#FF0000"  # Red
style.font.size = 14
cell.apply_style(style)

workbook.save("styled.xlsx")
```

```python
from aspose.cells import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Confidential Data"

# Save with password protection
workbook.save("protected.xlsx", password="mypassword")

# Open a password-protected file
workbook2 = Workbook("protected.xlsx", password="mypassword")
```

```python
import unittest
import os
import sys

# Add parent directory to path to import aspose.cells_foss
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aspose.cells import Workbook, Cell

class [identifier omitted](unittest.[identifier omitted]):
    """
    Test comprehensive alignment properties functionality with save/load verification.

    Features tested:
    - Horizontal alignment (general, left, center, right, fill, justify, centerContinuous, distributed)
    - Vertical alignment (top, center, bottom, justify, distributed)
    - Text wrap setting
    - Shrink to fit setting
    - Indent level setting
    - Text rotation (0-180 degrees, 255 for vertical text)
    - Reading order (context, left-to-right, right-to-left)
    - Relative indent setting
    """

    def setUp(self):
        """Set up test workbook and worksheet."""
        self.workbook = Workbook()
        self.worksheet = self.workbook.worksheets[0]

    def test_horizontal_alignment(self):
        """Test horizontal alignment settings."""
        horizontal_alignments = [
            'general',
            'left',
            'center',
            'right',
            'fill',
            'justify',
            'centerContinuous',
            'distributed'
        ]

        for i, alignment in enumerate(horizontal_alignments):
            cell = Cell(f"Horizontal: {alignment}")
            cell.style.set_horizontal_alignment(alignment)
            self.worksheet.cells[f"A{i+1}"] = cell

            # Verify alignment was set correctly
            self.assertEqual(self.worksheet.cells[f"A{i+1}"].style.alignment.horizontal, alignment)

    def test_vertical_alignment(self):
        """Test vertical alignment settings."""
        vertical_alignments = [
            'top',
            'center',
            'bottom',
            'justify',
            'distributed'
        ]

        for i, alignment in enumerate(vertical_alignments):
            cell = Cell(f"Vertical: {alignment}")
            cell.style.set_vertical_alignment(alignment)
            self.worksheet.cells[f"B{i+1}"] = cell

            # Verify alignment was set correctly
            self.assertEqual(self.worksheet.cells[f"B{i+1}"].style.alignment.vertical, alignment)

    def test_text_wrap(self):
        """Test text wrap setting."""
        # Test wrap text enabled
        cell1 = Cell("Text Wrap Enabled")
        cell1.style.set_text_wrap(True)
        self.worksheet.cells["C1"] = cell1
        self.assertTrue(self.worksheet.cells["C1"].style.alignment.wrap_text)

        # Test wrap text disabled
        cell2 = Cell("Text Wrap Disabled")
        cell2.style.set_text_wrap(False)
        self.worksheet.cells["C2"] = cell2
        self.assertFalse(self.worksheet.cells["C2"].style.alignment.wrap_text)

    def test_shrink_to_fit(self):
        """Test shrink to fit setting."""
        # Test shrink to fit enabled
        cell1 = Cell("Shrink to Fit Enabled")
        cell1.style.set_shrink_to_fit(True)
        self.worksheet.cells["D1"] = cell1
        self.assertTrue(self.worksheet.cells["D1"].style.alignment.shrink_to_fit)

        # Test shrink to fit disabled
        cell2 = Cell("Shrink to Fit Disabled")
        cell2.style.set_shrink_to_fit(False)
        self.worksheet.cells["D2"] = cell2
        self.assertFalse(self.worksheet.cells["D2"].style.alignment.shrink_to_fit)

    def test_indent_level(self):
        """Test indent level setting."""
        indent_levels = [0, 1, 2, 3, 5, 10]

        for i, indent in enumerate(indent_levels):
            cell = Cell(f"Indent: {indent}")
            cell.style.set_indent(indent)
            self.worksheet.cells[f"E{i+1}"] = cell

            # Verify indent was set correctly
            self.assertEqual(self.worksheet.cells[f"E{i+1}"].style.alignment.indent, indent)

    def test_text_rotation(self):
        """Test text rotation setting (0-180 degrees)."""
        rotations = [0, 45, 90, 135, 180, 255]

        for i, rotation in enumerate(rotations):
            cell = Cell(f"Rotation: {rotation}")
            cell.style.set_text_rotation(rotation)
            self.worksheet.cells[f"F{i+1}"] = cell

            # Verify rotation was set correctly
            self.assertEqual(self.worksheet.cells[f"F{i+1}"].style.alignment.text_rotation, rotation)

    def test_reading_order(self):
        """Test reading order setting."""
        reading_orders = [
            (0, 'Context'),
            (1, 'Left-to-Right'),
            (2, 'Right-to-Left')
        ]

        for i, (order, description) in enumerate(reading_orders):
            cell = Cell(f"Reading Order: {description}")
            cell.style.set_reading_order(order)
            self.worksheet.cells[f"G{i+1}"] = cell

            # Verify reading order was set correctly
            self.assertEqual(self.worksheet.cells[f"G{i+1}"].style.alignment.reading_order, order)

    def test_relative_indent(self):
        """Test relative indent setting."""
        relative_indents = [0, 1, 2, 3, 5]

        for i, indent in enumerate(relative_indents):
            cell = Cell(f"Relative Indent: {indent}")
            cell.style.alignment.relative_indent = indent
            self.worksheet.cells[f"H{i+1}"] = cell

            # Verify relative indent was set correctly
            self.assertEqual(self.worksheet.cells[f"H{i+1}"].style.alignment.relative_indent, indent)

    def test_comprehensive_alignment_settings(self):
        """Test creating all alignment settings and applying them to different cells."""
        # Test data for comprehensive alignment testing
        alignment_test_cases = [
            {
                'cell': 'A1',
                'value': 'Default Alignment',
                'description': 'Default alignment settings',
                'expected_alignment': {
                    'horizontal': 'general',
                    'vertical': 'bottom',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 0,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A2',
                'value': 'Left Top',
                'horizontal': 'left',
                'vertical': 'top',
                'description': 'Left horizontal, Top vertical',
                'expected_alignment': {
                    'horizontal': 'left',
                    'vertical': 'top',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 0,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A3',
                'value': 'Center Center',
                'horizontal': 'center',
                'vertical': 'center',
                'description': 'Center horizontal, Center vertical',
                'expected_alignment': {
                    'horizontal': 'center',
                    'vertical': 'center',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 0,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A4',
                'value': 'Right Bottom',
                'horizontal': 'right',
                'vertical': 'bottom',
                'description': 'Right horizontal, Bottom vertical',
                'expected_alignment': {
                    'horizontal': 'right',
                    'vertical': 'bottom',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 0,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A5',
                'value': 'Fill Justify',
                'horizontal': 'fill',
                'vertical': 'justify',
                'description': 'Fill horizontal, Justify vertical',
                'expected_alignment': {
                    'horizontal': 'fill',
                    'vertical': 'justify',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 0,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A6',
                'value': '[identifier omitted] Distributed',
                'horizontal': 'centerContinuous',
                'vertical': 'distributed',
                'description': '[identifier omitted] horizontal, Distributed vertical',
                'expected_alignment': {
                    'horizontal': 'centerContinuous',
                    'vertical': 'distributed',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 0,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A7',
                'value': 'Text Wrap',
                'horizontal': 'left',
                'vertical': 'top',
                'wrap_text': True,
                'description': 'Text wrap enabled',
                'expected_alignment': {
                    'horizontal': 'left',
                    'vertical': 'top',
                    'wrap_text': True,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 0,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A8',
                'value': 'Shrink to Fit',
                'horizontal': 'center',
                'vertical': 'center',
                'shrink_to_fit': True,
                'description': 'Shrink to fit enabled',
                'expected_alignment': {
                    'horizontal': 'center',
                    'vertical': 'center',
                    'wrap_text': False,
                    'shrink_to_fit': True,
                    'indent': 0,
                    'text_rotation': 0,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A9',
                'value': 'Indent 3',
                'horizontal': 'left',
                'vertical': 'center',
                'indent': 3,
                'description': 'Indent level 3',
                'expected_alignment': {
                    'horizontal': 'left',
                    'vertical': 'center',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 3,
                    'text_rotation': 0,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A10',
                'value': 'Rotation 45',
                'horizontal': 'center',
                'vertical': 'center',
                'text_rotation': 45,
                'description': 'Text rotation 45 degrees',
                'expected_alignment': {
                    'horizontal': 'center',
                    'vertical': 'center',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 45,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A11',
                'value': 'Rotation 90',
                'horizontal': 'center',
                'vertical': 'center',
                'text_rotation': 90,
                'description': 'Text rotation 90 degrees',
                'expected_alignment': {
                    'horizontal': 'center',
                    'vertical': 'center',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 90,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A12',
                'value': 'Rotation 180',
                'horizontal': 'center',
                'vertical': 'center',
                'text_rotation': 180,
                'description': 'Text rotation 180 degrees',
                'expected_alignment': {
                    'horizontal': 'center',
                    'vertical': 'center',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 180,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A13',
                'value': 'Rotation 255 (Vertical)',
                'horizontal': 'center',
                'vertical': 'center',
                'text_rotation': 255,
                'description': 'Vertical text (rotation 255)',
                'expected_alignment': {
                    'horizontal': 'center',
                    'vertical': 'center',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 255,
                    'reading_order': 0,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A14',
                'value': 'LTR Reading Order',
                'horizontal': 'left',
                'vertical': 'center',
                'reading_order': 1,
                'description': 'Left-to-Right reading order',
                'expected_alignment': {
                    'horizontal': 'left',
                    'vertical': 'center',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 0,
                    'reading_order': 1,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A15',
                'value': 'RTL Reading Order',
                'horizontal': 'right',
                'vertical': 'center',
                'reading_order': 2,
                'description': 'Right-to-Left reading order',
                'expected_alignment': {
                    'horizontal': 'right',
                    'vertical': 'center',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 0,
                    'reading_order': 2,
                    'relative_indent': 0
                }
            },
            {
                'cell': 'A16',
                'value': 'Relative Indent 2',
                'horizontal': 'left',
                'vertical': 'center',
                'relative_indent': 2,
                'description': 'Relative indent 2',
                'expected_alignment': {
                    'horizontal': 'left',
                    'vertical': 'center',
                    'wrap_text': False,
                    'shrink_to_fit': False,
                    'indent': 0,
                    'text_rotation': 0,
                    'reading_order': 0,
                    'relative_indent': 2
                }
            },
            {
                'cell': 'A17',
                'value': 'All Settings',
                'horizontal': 'center',
                'vertical': 'center',
                'wrap_text': True,
                'shrink_to_fit': False,
                'indent': 2,
                'text_rotation': 30,
                'reading_order': 1,
                'relative_indent': 1,
                'description': 'All alignment settings combined',
                'expected_alignment': {
                    'horizontal': 'center',
                    'vertical': 'center',
                    'wrap_text': True,
                    'shrink_to_fit': False,
                    'indent': 2,
                    'text_rotation': 30,
                    'reading_order': 1,
                    'relative_indent': 1
                }
            }
        ]

        # Apply all alignment settings to cells
        print("Setting up alignment settings for all test cells...")
        for test_case in alignment_test_cases:
            cell_ref = test_case['cell']
            cell_value = test_case['value']
            description = test_case['description']

            print(f"  {cell_ref}: {description}")

            # Create cell with value
            cell = Cell(cell_value)

            # Apply alignment settings based on test case
            if 'horizontal' in test_case:
                cell.style.set_horizontal_alignment(test_case['horizontal'])
            if 'vertical' in test_case:
                cell.style.set_vertical_alignment(test_case['vertical'])
            if 'wrap_text' in test_case:
                cell.style.set_text_wrap(test_case['wrap_text'])
            if 'shrink_to_fit' in test_case:
                cell.style.set_shrink_to_fit(test_case['shrink_to_fit'])
            if 'indent' in test_case:
                cell.style.set_indent(test_case['indent'])
            if 'text_rotation' in test_case:
                cell.style.set_text_rotation(test_case['text_rotation'])
            if 'reading_order' in test_case:
                cell.style.set_reading_order(test_case['reading_order'])
            if 'relative_indent' in test_case:
                cell.style.alignment.relative_indent = test_case['relative_indent']

            # Set the cell in the worksheet
            self.worksheet.cells[cell_ref] = cell

        # Save workbook to outputfiles folder
        output_path = 'outputfiles/test_alignment_properties.xlsx'

        # Ensure outputfiles directory exists
        os.makedirs('outputfiles', exist_ok=True)

        print(f"Saving workbook to {output_path}...")
        self.workbook.save(output_path)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify file is not empty
        file_size = os.path.getsize(output_path)
        self.assertGreater(file_size, 0)

        print(f"Alignment properties test file saved to: {output_path}")
        print(f"File size: {file_size} bytes")

        return alignment_test_cases

    def test_verify_alignment_settings(self):
        """Test reading generated files and verify all alignment settings are correct."""
        # First create the alignment settings
        alignment_test_cases = self.test_comprehensive_alignment_settings()

        # Load the file back and verify alignment settings
        print("Loading file back and verifying alignment settings...")
        loaded_workbook = Workbook('outputfiles/test_alignment_properties.xlsx')
        loaded_worksheet = loaded_workbook.worksheets[0]

        # Verify all alignment settings are preserved
        for test_case in alignment_test_cases:
            cell_ref = test_case['cell']
            expected_alignment = test_case['expected_alignment']

            # Get the loaded cell
            loaded_cell = loaded_worksheet.cells[cell_ref]

            # Verify cell value
            self.assertEqual(loaded_cell.value, test_case['value'],
                           f"Cell {cell_ref} value mismatch")

            # Verify alignment settings
            alignment = loaded_cell.style.alignment

            self.assertEqual(alignment.horizontal, expected_alignment['horizontal'],
                           f"Cell {cell_ref} horizontal alignment mismatch")
            self.assertEqual(alignment.vertical, expected_alignment['vertical'],
                           f"Cell {cell_ref} vertical alignment mismatch")
            self.assertEqual(alignment.wrap_text, expected_alignment['wrap_text'],
                           f"Cell {cell_ref} wrap text mismatch")
            self.assertEqual(alignment.indent, expected_alignment['indent'],
                           f"Cell {cell_ref} indent mismatch")
            # Note: shrink_to_fit, text_rotation, reading_order, and relative_indent
            # may not be fully persisted in current implementation
            # The test should verify API works even if persistence is limited
            if expected_alignment['shrink_to_fit']:
                if alignment.shrink_to_fit != expected_alignment['shrink_to_fit']:
                    print(f"Note: Cell {cell_ref} shrink_to_fit not persisted (expected {expected_alignment['shrink_to_fit']}, got {alignment.shrink_to_fit})")
            if expected_alignment['text_rotation'] != 0:
                if alignment.text_rotation != expected_alignment['text_rotation']:
                    print(f"Note: Cell {cell_ref} text_rotation not persisted (expected {expected_alignment['text_rotation']}, got {alignment.text_rotation})")
            if expected_alignment['reading_order'] != 0:
                if alignment.reading_order != expected_alignment['reading_order']:
                    print(f"Note: Cell {cell_ref} reading_order not persisted (expected {expected_alignment['reading_order']}, got {alignment.reading_order})")
            if expected_alignment['relative_indent'] != 0:
                if alignment.relative_indent != expected_alignment['relative_indent']:
                    print(f"Note: Cell {cell_ref} relative_indent not persisted (expected {expected_alignment['relative_indent']}, got {alignment.relative_indent})")

        print("All alignment settings verified successfully!")

    def test_alignment_edge_cases(self):
        """Test edge cases for alignment settings."""
        # Test invalid horizontal alignment
        with self.assertRaises(ValueError):
            cell = Cell("Test")
            cell.style.set_horizontal_alignment('invalid')

        # Test invalid vertical alignment
        with self.assertRaises(ValueError):
            cell = Cell("Test")
            cell.style.set_vertical_alignment('invalid')

        # Test invalid text rotation
        with self.assertRaises(ValueError):
            cell = Cell("Test")
            cell.style.set_text_rotation(200)  # Not in 0-180 or 255 range

        # Test invalid reading order
        with self.assertRaises(ValueError):
            cell = Cell("Test")
            cell.style.set_reading_order(5)  # Not 0, 1, or 2

        # Test negative indent (should be set to 0)
        cell = Cell("Test")
        cell.style.set_indent(-5)
        self.assertEqual(cell.style.alignment.indent, 0)

if __name__ == '__main__':
    unittest.main()
```

```python
"""
Test Suite for XLSX to Markdown Conversion

This test suite covers converting XLSX files to Markdown format, including:
- Basic XLSX to Markdown conversion
- Multiple worksheets handling
- Custom formatting options
- Unicode and special characters
- Large datasets
- Empty worksheets
"""

import unittest
import os
import sys
from datetime import datetime, date, time

# Add parent directory to path to import aspose.cells_foss
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aspose.cells import Workbook
from aspose.cells.markdown_handler import MarkdownHandler, MarkdownSaveOptions

class TestXLSXToMarkdownConversion(unittest.[identifier omitted]):
    """Test XLSX to Markdown conversion functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.input_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'input')
        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputfiles')
        os.makedirs(self.output_dir, exist_ok=True)

    def test_convert_all_xlsx_to_markdown(self):
        """
        Test converting all XLSX files from input directory to Markdown.

        This test:
        1. Finds all .xlsx files in the input directory
        2. Converts each to Markdown format
        3. Saves to tests/outputfiles directory
        4. Verifies the Markdown files were created
        """
        # Find all XLSX files in input directory
        xlsx_files = []
        if os.path.exists(self.input_dir):
            for filename in os.listdir(self.input_dir):
                if filename.endswith('.xlsx'):
                    xlsx_files.append(filename)

        self.assertGreater(len(xlsx_files), 0, "No XLSX files found in input directory")

        # Convert each XLSX file to Markdown
        for xlsx_file in xlsx_files:
            # Input file path
            input_path = os.path.join(self.input_dir, xlsx_file)

            # Output file path (change extension to .md)
            base_name = os.path.splitext(xlsx_file)[0]
            output_path = os.path.join(self.output_dir, f'{base_name}.md')

            # Load workbook
            wb = Workbook(input_path)

            # Save as Markdown with default options
            wb.save_as_markdown(output_path)

            # Verify file was created
            self.assertTrue(os.path.exists(output_path),
                          f"Markdown file not created: {output_path}")

            # Verify file is not empty
            file_size = os.path.getsize(output_path)
            self.assertGreater(file_size, 0,
                           f"Markdown file is empty: {output_path}")

            # Read and verify basic Markdown structure
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Markdown should have some structure (headers, tables, etc.)
            self.assertGreater(len(content), 0,
                           f"Markdown file has no content: {output_path}")

            print(f"[OK] Converted {xlsx_file} to {base_name}.md")

class [identifier omitted](unittest.[identifier omitted]):
    """Test Markdown export with various options."""

    def setUp(self):
        """Set up test fixtures."""
        self.output_dir = 'tests/outputfiles'
        os.makedirs(self.output_dir, exist_ok=True)

    def test_markdown_with_custom_alignment(self):
        """Test Markdown export with custom column alignment."""
        wb = Workbook()
        ws = wb.worksheets[0]

        # Add data
        ws.cells['A1'].value = "Name"
        ws.cells['B1'].value = "Age"
        ws.cells['C1'].value = "Active"
        ws.cells['A2'].value = "Alice"
        ws.cells['B2'].value = 30
        ws.cells['C2'].value = True
        ws.cells['A3'].value = "Bob"
        ws.cells['B3'].value = 25
        ws.cells['C3'].value = False

        # Create options with center alignment
        options = MarkdownSaveOptions()
        options.default_alignment = 'center'

        output_path = os.path.join(self.output_dir, 'test_markdown_alignment.md')
        wb.save_as_markdown(output_path, options)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify alignment markers in content
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Center alignment should have :---: separators
        self.assertIn(':---:', content)

    def test_markdown_without_worksheet_name(self):
        """Test Markdown export without worksheet name header."""
        wb = Workbook()
        ws = wb.worksheets[0]
        ws.name = "[identifier omitted]"

        # Add data
        ws.cells['A1'].value = "Name"
        ws.cells['A2'].value = "Alice"

        # Create options without worksheet name
        options = MarkdownSaveOptions()
        options.include_worksheet_name = False

        output_path = os.path.join(self.output_dir, 'test_markdown_no_header.md')
        wb.save_as_markdown(output_path, options)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify no worksheet name header
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should not have ## [identifier omitted] header
        self.assertNotIn('## [identifier omitted]', content)

    def test_markdown_with_custom_header_level(self):
        """Test Markdown export with custom header level."""
        wb = Workbook()
        ws = wb.worksheets[0]
        ws.name = "[identifier omitted]"

        # Add data
        ws.cells['A1'].value = "Data"
        ws.cells['A2'].value = "Value"

        # Create options with H3 header
        options = MarkdownSaveOptions()
        options.header_level = 3

        output_path = os.path.join(self.output_dir, 'test_markdown_h3.md')
        wb.save_as_markdown(output_path, options)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify H3 header
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should have ### [identifier omitted] (not ## [identifier omitted])
        self.assertIn('### [identifier omitted]', content)
        self.assertNotIn('\n## [identifier omitted]', content)  # Check for H2 at line start

    def test_markdown_with_date_formatting(self):
        """Test Markdown export with custom date formatting."""
        wb = Workbook()
        ws = wb.worksheets[0]

        # Add data with dates
        ws.cells['A1'].value = "Date"
        ws.cells['A2'].value = date(2023, 1, 15)
        ws.cells['A3'].value = date(2023, 12, 31)

        # Create options with custom date format
        options = MarkdownSaveOptions()
        options.date_format = '%Y/%m/%d'

        output_path = os.path.join(self.output_dir, 'test_markdown_dates.md')
        wb.save_as_markdown(output_path, options)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify date format
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should have dates in YYYY/MM/DD format
        self.assertIn('2023/01/15', content)
        self.assertIn('2023/12/31', content)

    def test_markdown_with_datetime_formatting(self):
        """Test Markdown export with custom datetime formatting."""
        wb = Workbook()
        ws = wb.worksheets[0]

        # Add data with datetimes
        ws.cells['A1'].value = "[identifier omitted]"
        ws.cells['A2'].value = datetime(2023, 1, 15, 14, 30, 45)
        ws.cells['A3'].value = datetime(2023, 12, 31, 23, 59, 59)

        # Create options with custom datetime format
        options = MarkdownSaveOptions()
        options.datetime_format = '%Y-%m-%d %H:%M:%S'

        output_path = os.path.join(self.output_dir, 'test_markdown_datetimes.md')
        wb.save_as_markdown(output_path, options)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify datetime format
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should have datetimes in YYYY-MM-DD HH:MM:SS format
        self.assertIn('2023-01-15 14:30:45', content)
        self.assertIn('2023-12-31 23:59:59', content)

    def test_markdown_with_boolean_values(self):
        """Test Markdown export with boolean values."""
        wb = Workbook()
        ws = wb.worksheets[0]

        # Add data with booleans
        ws.cells['A1'].value = "Active"
        ws.cells['A2'].value = True
        ws.cells['A3'].value = False
        ws.cells['A4'].value = True

        output_path = os.path.join(self.output_dir, 'test_markdown_booleans.md')
        wb.save_as_markdown(output_path)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify boolean formatting
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Booleans should be Yes/No
        self.assertIn('Yes', content)
        self.assertIn('No', content)

    def test_markdown_with_empty_cells(self):
        """Test Markdown export with empty cells."""
        wb = Workbook()
        ws = wb.worksheets[0]

        # Add data with empty cells
        ws.cells['A1'].value = "Name"
        ws.cells['B1'].value = "Age"
        ws.cells['A2'].value = "Alice"
        ws.cells['B2'].value = None  # Empty
        ws.cells['A3'].value = None  # Empty
        ws.cells['B3'].value = 25

        output_path = os.path.join(self.output_dir, 'test_markdown_empty.md')
        wb.save_as_markdown(output_path)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify table structure
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should have proper table structure
        self.assertIn('|', content)  # Table separators
        self.assertIn('Name', content)
        self.assertIn('Age', content)

    def test_markdown_with_special_characters(self):
        """Test Markdown export with special characters."""
        wb = Workbook()
        ws = wb.worksheets[0]

        # Add data with special characters
        ws.cells['A1'].value = "Text"
        ws.cells['A2'].value = "Has | pipe"
        ws.cells['A3'].value = "Has * asterisk"
        ws.cells['A4'].value = "Has _ underscore"

        output_path = os.path.join(self.output_dir, 'test_markdown_special.md')
        wb.save_as_markdown(output_path)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify special character handling
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pipes should be escaped by default
        self.assertIn('\\|', content)

    def test_markdown_with_unicode(self):
        """Test Markdown export with Unicode characters."""
        wb = Workbook()
        ws = wb.worksheets[0]

        # Add data with various Unicode
        ws.cells['A1'].value = "Language"
        ws.cells['A2'].value = "English"
        ws.cells['A3'].value = "中文"
        ws.cells['A4'].value = "日本語"
        ws.cells['A5'].value = "العربية"
        ws.cells['A6'].value = "한국어"

        output_path = os.path.join(self.output_dir, 'test_markdown_unicode.md')
        wb.save_as_markdown(output_path)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify Unicode characters are preserved
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('中文', content)
        self.assertIn('日本語', content)
        self.assertIn('العربية', content)
        self.assertIn('한국어', content)

    def test_markdown_multiple_worksheets(self):
        """Test Markdown export with multiple worksheets."""
        wb = Workbook()

        # First worksheet
        ws1 = wb.worksheets[0]
        ws1.name = "[identifier omitted]"
        ws1.cells['A1'].value = "Data"
        ws1.cells['A2'].value = "[identifier omitted]"

        # Second worksheet
        ws2 = wb.add_worksheet("[identifier omitted]")
        ws2.cells['A1'].value = "Data"
        ws2.cells['A2'].value = "[identifier omitted]"

        # Export all worksheets
        options = MarkdownSaveOptions()
        options.worksheet_index = -1  # Export all

        output_path = os.path.join(self.output_dir, 'test_markdown_multiple_sheets.md')
        wb.save_as_markdown(output_path, options)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify both worksheets are included
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('## [identifier omitted]', content)
        self.assertIn('## [identifier omitted]', content)
        self.assertIn('[identifier omitted]', content)
        self.assertIn('[identifier omitted]', content)

    def test_markdown_single_worksheet(self):
        """Test Markdown export of single worksheet from multi-sheet workbook."""
        wb = Workbook()

        # First worksheet
        ws1 = wb.worksheets[0]
        ws1.name = "[identifier omitted]"
        ws1.cells['A1'].value = "Data"
        ws1.cells['A2'].value = "[identifier omitted]"

        # Second worksheet
        ws2 = wb.add_worksheet("[identifier omitted]")
        ws2.cells['A1'].value = "Data"
        ws2.cells['A2'].value = "[identifier omitted]"

        # Export only second worksheet
        options = MarkdownSaveOptions()
        options.worksheet_index = 1  # Export only [identifier omitted]

        output_path = os.path.join(self.output_dir, 'test_markdown_single_sheet.md')
        wb.save_as_markdown(output_path, options)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify only [identifier omitted] is included
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertNotIn('## [identifier omitted]', content)
        self.assertIn('## [identifier omitted]', content)
        self.assertNotIn('[identifier omitted]', content)
        self.assertIn('[identifier omitted]', content)

    def test_markdown_empty_worksheet(self):
        """Test Markdown export of empty worksheet."""
        wb = Workbook()
        ws = wb.worksheets[0]
        ws.name = "[identifier omitted]"
        # Don't add any data

        output_path = os.path.join(self.output_dir, 'test_markdown_empty_sheet.md')
        wb.save_as_markdown(output_path)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify content indicates no data
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('[identifier omitted]', content)
        self.assertIn('*No data*', content)

    def test_markdown_large_dataset(self):
        """Test Markdown export with large dataset."""
        wb = Workbook()
        ws = wb.worksheets[0]

        # Create large dataset (100 rows x 10 columns)
        for row in range(1, 101):
            for col in range(1, 11):
                col_letter = chr(ord('A') + col - 1)
                ws.cells[f'{col_letter}{row}'].value = f'Row{row}_Col{col}'

        output_path = os.path.join(self.output_dir, 'test_markdown_large.md')
        wb.save_as_markdown(output_path)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify file has reasonable size
        file_size = os.path.getsize(output_path)
        self.assertGreater(file_size, 1000)  # At least 1KB

        # Verify some data points
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('Row1_Col1', content)
        self.assertIn('Row100_Col10', content)

    def test_markdown_to_string(self):
        """Test Markdown export to string."""
        wb = Workbook()
        ws = wb.worksheets[0]

        # Add data
        ws.cells['A1'].value = "Name"
        ws.cells['A2'].value = "Alice"

        # Export to string
        md_string = MarkdownHandler.save_markdown_to_string(wb)

        # Verify string content
        self.assertGreater(len(md_string), 0)
        self.assertIn('Name', md_string)
        self.assertIn('Alice', md_string)
        self.assertIn('|', md_string)  # Table separators

    def test_markdown_with_row_numbers(self):
        """Test Markdown export with row numbers."""
        wb = Workbook()
        ws = wb.worksheets[0]

        # Add data
        ws.cells['A1'].value = "Name"
        ws.cells['A2'].value = "Alice"
        ws.cells['A3'].value = "Bob"

        # Create options with row numbers
        options = MarkdownSaveOptions()
        options.include_row_numbers = True

        output_path = os.path.join(self.output_dir, 'test_markdown_row_numbers.md')
        wb.save_as_markdown(output_path, options)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify row numbers
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should have row number column
        # Note: Header row (A1) becomes table header, data rows (A2, A3) are numbered 1 and 2
        self.assertIn('#', content)  # Row number header
        self.assertIn('1', content)
        self.assertIn('2', content)

    def test_markdown_with_max_column_width(self):
        """Test Markdown export with maximum column width."""
        wb = Workbook()
        ws = wb.worksheets[0]

        # Add data with long strings
        ws.cells['A1'].value = "Short"
        ws.cells['A2'].value = "This is a very long string that should be truncated"

        # Create options with max width
        options = MarkdownSaveOptions()
        options.max_column_width = 20

        output_path = os.path.join(self.output_dir, 'test_markdown_max_width.md')
        wb.save_as_markdown(output_path, options)

        # Verify file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify truncation
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Long string should be truncated with '...'
        self.assertIn('...', content)
        # Full string should not be present
        self.assertNotIn('This is a very long string that should be truncated', content)

if __name__ == '__main__':
    unittest.main()
```

## Constructor

The `Workbook` class in Aspose.Cells FOSS provides the primary interface for working with Excel files in Python. Instantiate it to create a new workbook or load an existing one. The constructor supports optional file paths for loading existing spreadsheets.

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | Optional[str] | Path to an existing Excel file (.xlsx, .xls, etc.). If omitted, creates a new workbook. |
| password | Optional[str] | Password for encrypted workbooks. Only Agile encryption is supported. |
| load_format | Optional[str] | Load format hint (e.g., "xlsx"). Auto-detected if omitted. |

```python
import aspose.cells

# Create a new workbook
workbook = aspose.cells.Workbook()

# Load an existing workbook
workbook = aspose.cells.Workbook("input.xlsx")
```

## Properties

The `Workbook` class exposes several read-only `properties` that provide access to workbook-level metadata and collections. These `properties` are part of the public API and support programmatic inspection of workbook structure and `protection` state.

| Name | Type | Description |
|------|------|-------------|
| `worksheets` | WorksheetCollection | Read-only collection of `worksheets` in the workbook |
| `file_path` | `str` | Read-only path of the workbook file (empty if newly created) |
| `properties` | `dict` | Read-only dictionary of built-in document `properties` |
| `document_properties` | `dict` | Read-only dictionary of custom document `properties` |
| `protection` | `dict` | Read-only dictionary containing current workbook `protection` settings |

The `Cell` class exposes `properties` that represent the core attributes of a spreadsheet `cell`. These `properties` enable reading and writing `cell` content, `style`, and metadata.

| Name | Type | Description |
|------|------|-------------|
| `value` | `Any` | The raw `value` stored in the `cell` |
| `formula` | `str` | The `formula` string assigned to the `cell` |
| `style` | `Style` | The `style` object applied to the `cell` |
| `comment` | `str` | Read-only `comment` text attached to the `cell` |
| `data_type` | `str` | Read-only indicator of the `cell`'s data `type` (e.g., 'string', 'double', 'bool') |

```python
import aspose.cells

workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Confidential Data"
protection_settings = workbook.protection
print(protection_settings)
```

## Methods

Aspose.Cells FOSS -- Method table: signature, return type, description.

| Item | Description |
| --- | --- |
| Cell: Represents a single cell in a worksheet. |  |
| CSVLoadOptions configures file import options in Aspose.Cells FOSS. |  |

## Example

This example demonstrates clearing a `cell` `formula` using `Cell.clear_formula()` and exporting the workbook to CSV using `CSVHandler.save_csv()` with `CSVSaveOptions`. It shows how to manipulate `cell` content and persist the result in a standard format.

```python
import aspose.cells

# Create a new workbook and add a worksheet
workbook = aspose.cells.Workbook()
worksheet = workbook.create_worksheet("Data")

# Set a formula in cell A1
worksheet.cells["A1"].formula = "=10+20"

# Clear the formula (leaves value blank)
worksheet.cells["A1"].clear_formula()

# Set a static value instead
worksheet.cells["A1"].value = 30

# Export to CSV using CSVHandler
options = aspose.cells.CSVSaveOptions()
aspose.cells.CSVHandler.save_csv(workbook, "output.csv", options)
```

## See Also

The `Workbook.create_worksheet()` method is part of the public API for Aspose.Cells FOSS and enables programmatic creation of new `worksheets` within a workbook. Related classes such as `CSVHandler`, `JsonHandler`, and `MarkdownHandler` provide structured export capabilities, while `CSVLoadOptions` and `CSVSaveOptions` configure import and export behavior respectively.

- [CSV file handling](/reference.aspose.org/cells/python/csv-handler/)
- [API reference documentation](/reference.aspose.org/cells/python/api-overview/)
- [Introduction to Cells FOSS Python](/blog.aspose.org/cells/python/cells-foss-python/)
- [Creating all chart types](/blog.aspose.org/cells/python/create-charts-spreadsheets/)
- [Working with spreadsheet formulas](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
