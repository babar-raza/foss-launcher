---
canonical: https://reference.aspose.org/cells/python/workbook/
canonical_import: aspose.cells
date: '2026-03-22T08:56:20Z'
dateModified: '2026-03-22T08:56:20Z'
datePublished: '2026-03-22T08:56:20Z'
description: 'JsonHandler.save_json(): Saves a workbook to a JSON file.'
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
seoTitle: Aspose.Cells FOSS Workbook
slug: workbook
title: Workbook
type: reference_object_page
url: /reference.aspose.org/cells/python/workbook/
weight: 20
---

## Overview

Aspose.Cells FOSS -- Class or function purpose in 1-3 sentences.

Aspose.Cells FOSS CSVHandler: Handles CSV import and export operations for workbooks. JsonHandler.save_json(): Saves a workbook to a JSON file.

```python
"""
Test cases for workbook document properties persistence.

Tests roundtrip persistence of document properties according to ECMA-376 specification.
Document properties are stored in docProps/core.xml and docProps/app.xml files.
"""

import os
import sys
import unittest
import zipfile
import xml.etree.[identifier omitted] as ET
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aspose.cells import Workbook

class [identifier omitted](unittest.[identifier omitted]):
    """Test cases for document properties persistence."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputfiles')
        os.makedirs(self.test_dir, exist_ok=True)
        self.ns = {
            'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'dcterms': 'http://purl.org/dc/terms/'
        }

    def test_core_properties_basic(self):
        """Test that basic core properties persist correctly."""
        wb = Workbook()

        # Set core properties
        wb.document_properties.core.title = "Test Document"
        wb.document_properties.core.subject = "Test Subject"
        wb.document_properties.core.creator = "Test Author"
        wb.document_properties.core.keywords = "test, keywords"
        wb.document_properties.core.description = "Test description"

        # Save and reload
        path = os.path.join(self.test_dir, "core_properties_basic.xlsx")
        wb.save(path)

        # Verify XML structure
        with zipfile.[identifier omitted](path, 'r') as zf:
            core_xml = zf.read('docProps/core.xml').decode('utf-8')
            root = ET.fromstring(core_xml)

            title = root.find('dc:title', self.ns)
            self.assertIsNotNone(title)
            self.assertEqual(title.text, "Test Document")

            subject = root.find('dc:subject', self.ns)
            self.assertIsNotNone(subject)
            self.assertEqual(subject.text, "Test Subject")

            creator = root.find('dc:creator', self.ns)
            self.assertIsNotNone(creator)
            self.assertEqual(creator.text, "Test Author")

            keywords = root.find('cp:keywords', self.ns)
            self.assertIsNotNone(keywords)
            self.assertEqual(keywords.text, "test, keywords")

            description = root.find('dc:description', self.ns)
            self.assertIsNotNone(description)
            self.assertEqual(description.text, "Test description")

        # Reload and verify
        wb2 = Workbook(path)
        self.assertEqual(wb2.document_properties.core.title, "Test Document")
        self.assertEqual(wb2.document_properties.core.subject, "Test Subject")
        self.assertEqual(wb2.document_properties.core.creator, "Test Author")
        self.assertEqual(wb2.document_properties.core.keywords, "test, keywords")
        self.assertEqual(wb2.document_properties.core.description, "Test description")

    def test_core_properties_extended(self):
        """Test that extended core properties persist correctly."""
        wb = Workbook()

        # Set extended core properties
        wb.document_properties.core.last_modified_by = "Second Author"
        wb.document_properties.core.revision = "2"
        wb.document_properties.core.category = "Reports"
        wb.document_properties.core.content_status = "Draft"

        # Save and reload
        path = os.path.join(self.test_dir, "core_properties_extended.xlsx")
        wb.save(path)

        # Verify XML structure
        with zipfile.[identifier omitted](path, 'r') as zf:
            core_xml = zf.read('docProps/core.xml').decode('utf-8')
            root = ET.fromstring(core_xml)

            last_modified_by = root.find('cp:lastModifiedBy', self.ns)
            self.assertIsNotNone(last_modified_by)
            self.assertEqual(last_modified_by.text, "Second Author")

            revision = root.find('cp:revision', self.ns)
            self.assertIsNotNone(revision)
            self.assertEqual(revision.text, "2")

            category = root.find('cp:category', self.ns)
            self.assertIsNotNone(category)
            self.assertEqual(category.text, "Reports")

            content_status = root.find('cp:contentStatus', self.ns)
            self.assertIsNotNone(content_status)
            self.assertEqual(content_status.text, "Draft")

        # Reload and verify
        wb2 = Workbook(path)
        self.assertEqual(wb2.document_properties.core.last_modified_by, "Second Author")
        self.assertEqual(wb2.document_properties.core.revision, "2")
        self.assertEqual(wb2.document_properties.core.category, "Reports")
        self.assertEqual(wb2.document_properties.core.content_status, "Draft")

    def test_core_properties_dates(self):
        """Test that date properties persist correctly."""
        wb = Workbook()

        # Set date properties
        test_created = datetime(2024, 1, 15, 10, 30)
        test_modified = datetime(2024, 1, 20, 14, 45, 0)
        wb.document_properties.core.created = test_created
        wb.document_properties.core.modified = test_modified

        # Save and reload
        path = os.path.join(self.test_dir, "core_properties_dates.xlsx")
        wb.save(path)

        # Verify XML structure
        with zipfile.[identifier omitted](path, 'r') as zf:
            core_xml = zf.read('docProps/core.xml').decode('utf-8')
            root = ET.fromstring(core_xml)

            created = root.find('dcterms:created', self.ns)
            self.assertIsNotNone(created)
            self.assertIn('2024-01-15T10:30:00', created.text)

            modified = root.find('dcterms:modified', self.ns)
            self.assertIsNotNone(modified)
            self.assertIn('2024-01-20T14:45:00', modified.text)

        # Reload and verify
        wb2 = Workbook(path)
        self.assertIsNotNone(wb2.document_properties.core.created)
        self.assertIsNotNone(wb2.document_properties.core.modified)

    def test_extended_properties_basic(self):
        """Test that basic extended properties persist correctly."""
        wb = Workbook()

        # Set extended properties
        wb.document_properties.extended.application = "Aspose.Cells for Python"
        wb.document_properties.extended.app_version = "16.0.0"
        wb.document_properties.extended.company = "Test Company"
        wb.document_properties.extended.manager = "Test Manager"

        # Save and reload
        path = os.path.join(self.test_dir, "extended_properties_basic.xlsx")
        wb.save(path)

        # Verify XML structure
        with zipfile.[identifier omitted](path, 'r') as zf:
            app_xml = zf.read('docProps/app.xml').decode('utf-8')
            root = ET.fromstring(app_xml)

            application = root.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Application')
            self.assertIsNotNone(application)
            self.assertEqual(application.text, "Aspose.Cells for Python")

            app_version = root.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}[identifier omitted]')
            self.assertIsNotNone(app_version)
            self.assertEqual(app_version.text, "16.0.0")

            company = root.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Company')
            self.assertIsNotNone(company)
            self.assertEqual(company.text, "Test Company")

            manager = root.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Manager')
            self.assertIsNotNone(manager)
            self.assertEqual(manager.text, "Test Manager")

        # Reload and verify
        wb2 = Workbook(path)
        self.assertEqual(wb2.document_properties.extended.application, "Aspose.Cells for Python")
        self.assertEqual(wb2.document_properties.extended.app_version, "16.0.0")
        self.assertEqual(wb2.document_properties.extended.company, "Test Company")
        self.assertEqual(wb2.document_properties.extended.manager, "Test Manager")

    def test_extended_properties_flags(self):
        """Test that extended property flags persist correctly."""
        wb = Workbook()

        # Set extended property flags
        wb.document_properties.extended.scale_crop = True
        wb.document_properties.extended.links_up_to_date = True
        wb.document_properties.extended.shared_doc = True
        wb.document_properties.extended.doc_security = 1

        # Save and reload
        path = os.path.join(self.test_dir, "extended_properties_flags.xlsx")
        wb.save(path)

        # Verify XML structure
        with zipfile.[identifier omitted](path, 'r') as zf:
            app_xml = zf.read('docProps/app.xml').decode('utf-8')
            root = ET.fromstring(app_xml)

            scale_crop = root.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}[identifier omitted]')
            self.assertIsNotNone(scale_crop)
            self.assertEqual(scale_crop.text, "true")

            links_up_to_date = root.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}[identifier omitted]')
            self.assertIsNotNone(links_up_to_date)
            self.assertEqual(links_up_to_date.text, "true")

            shared_doc = root.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}[identifier omitted]')
            self.assertIsNotNone(shared_doc)
            self.assertEqual(shared_doc.text, "true")

            doc_security = root.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}[identifier omitted]')
            self.assertIsNotNone(doc_security)
            self.assertEqual(doc_security.text, "1")

        # Reload and verify
        wb2 = Workbook(path)
        self.assertTrue(wb2.document_properties.extended.scale_crop)
        self.assertTrue(wb2.document_properties.extended.links_up_to_date)
        self.assertTrue(wb2.document_properties.extended.shared_doc)
        self.assertEqual(wb2.document_properties.extended.doc_security, 1)

    def test_extended_properties_hyperlink_base(self):
        """Test that hyperlink base property persists correctly."""
        wb = Workbook()

        # Set hyperlink base
        wb.document_properties.extended.hyperlink_base = "https://example.com/docs/"

        # Save and reload
        path = os.path.join(self.test_dir, "extended_properties_hyperlink.xlsx")
        wb.save(path)

        # Verify XML structure
        with zipfile.[identifier omitted](path, 'r') as zf:
            app_xml = zf.read('docProps/app.xml').decode('utf-8')
            root = ET.fromstring(app_xml)

            hyperlink_base = root.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}[identifier omitted]')
            self.assertIsNotNone(hyperlink_base)
            self.assertEqual(hyperlink_base.text, "https://example.com/docs/")

        # Reload and verify
        wb2 = Workbook(path)
        self.assertEqual(wb2.document_properties.extended.hyperlink_base, "https://example.com/docs/")

    def test_convenience_properties(self):
        """Test that convenience properties work correctly."""
        wb = Workbook()

        # Set convenience properties
        wb.document_properties.title = "Convenience Title"
        wb.document_properties.subject = "Convenience Subject"
        wb.document_properties.author = "Convenience Author"
        wb.document_properties.creator = "Creator Name"
        wb.document_properties.keywords = "convenience, test"
        wb.document_properties.comments = "Convenience comments"
        wb.document_properties.category = "Convenience Category"
        wb.document_properties.company = "Convenience Company"
        wb.document_properties.manager = "Convenience Manager"

        # Save and reload
        path = os.path.join(self.test_dir, "convenience_properties.xlsx")
        wb.save(path)

        # Reload and verify
        wb2 = Workbook(path)
        self.assertEqual(wb2.document_properties.title, "Convenience Title")
        self.assertEqual(wb2.document_properties.subject, "Convenience Subject")
        self.assertEqual(wb2.document_properties.author, "Creator Name")
        self.assertEqual(wb2.document_properties.creator, "Creator Name")
        self.assertEqual(wb2.document_properties.keywords, "convenience, test")
        self.assertEqual(wb2.document_properties.comments, "Convenience comments")
        self.assertEqual(wb2.document_properties.category, "Convenience Category")
        self.assertEqual(wb2.document_properties.company, "Convenience Company")
        self.assertEqual(wb2.document_properties.manager, "Convenience Manager")

    def test_comprehensive_document_properties(self):
        """Test comprehensive roundtrip of all document properties."""
        wb = Workbook()

        # Set all core properties
        wb.document_properties.core.title = "Comprehensive Test"
        wb.document_properties.core.subject = "Testing All Properties"
        wb.document_properties.core.creator = "Test Creator"
        wb.document_properties.core.keywords = "comprehensive, test, all"
        wb.document_properties.core.description = "Testing all document properties"
        wb.document_properties.core.last_modified_by = "Second Creator"
        wb.document_properties.core.revision = "3"
        wb.document_properties.core.category = "Test Reports"
        wb.document_properties.core.content_status = "Final"

        # Set all extended properties
        wb.document_properties.extended.application = "Test Application"
        wb.document_properties.extended.app_version = "1.0.0"
        wb.document_properties.extended.company = "Test Company Inc."
        wb.document_properties.extended.manager = "Test Manager"
        wb.document_properties.extended.hyperlink_base = "https://test.com/"
        wb.document_properties.extended.scale_crop = False
        wb.document_properties.extended.links_up_to_date = False
        wb.document_properties.extended.shared_doc = False
        wb.document_properties.extended.doc_security = 0

        # Add some data
        ws = wb.worksheets[0]
        ws.cells["A1"].value = "Test"
        ws.cells["A2"].value = 123

        # Save and reload
        path = os.path.join(self.test_dir, "comprehensive_document_properties.xlsx")
        wb.save(path)

        # Reload and verify
        wb2 = Workbook(path)
        ws2 = wb2.worksheets[0]

        # Verify core properties
        self.assertEqual(wb2.document_properties.core.title, "Comprehensive Test")
        self.assertEqual(wb2.document_properties.core.subject, "Testing All Properties")
        self.assertEqual(wb2.document_properties.core.creator, "Test Creator")
        self.assertEqual(wb2.document_properties.core.keywords, "comprehensive, test, all")
        self.assertEqual(wb2.document_properties.core.description, "Testing all document properties")
        self.assertEqual(wb2.document_properties.core.last_modified_by, "Second Creator")
        self.assertEqual(wb2.document_properties.core.revision, "3")
        self.assertEqual(wb2.document_properties.core.category, "Test Reports")
        self.assertEqual(wb2.document_properties.core.content_status, "Final")

        # Verify extended properties
        self.assertEqual(wb2.document_properties.extended.application, "Test Application")
        self.assertEqual(wb2.document_properties.extended.app_version, "1.0.0")
        self.assertEqual(wb2.document_properties.extended.company, "Test Company Inc.")
        self.assertEqual(wb2.document_properties.extended.manager, "Test Manager")
        self.assertEqual(wb2.document_properties.extended.hyperlink_base, "https://test.com/")
        self.assertFalse(wb2.document_properties.extended.scale_crop)
        self.assertFalse(wb2.document_properties.extended.links_up_to_date)
        self.assertFalse(wb2.document_properties.extended.shared_doc)
        self.assertEqual(wb2.document_properties.extended.doc_security, 0)

        # Verify data
        self.assertEqual(ws2.cells["A1"].value, "Test")
        self.assertEqual(ws2.cells["A2"].value, 123)

    def test_document_properties_with_special_characters(self):
        """Test that special characters in properties are handled correctly."""
        wb = Workbook()

        # Set properties with special characters
        wb.document_properties.core.title = "Test <Special> & Characters"
        wb.document_properties.core.description = "Description with 'quotes' and \"double quotes\""
        wb.document_properties.core.keywords = "test & special, <chars>"

        # Save and reload
        path = os.path.join(self.test_dir, "special_characters_properties.xlsx")
        wb.save(path)

        # Reload and verify
        wb2 = Workbook(path)
        self.assertEqual(wb2.document_properties.core.title, "Test <Special> & Characters")
        self.assertEqual(wb2.document_properties.core.description, "Description with 'quotes' and \"double quotes\"")
        self.assertEqual(wb2.document_properties.core.keywords, "test & special, <chars>")

    def test_document_properties_with_unicode(self):
        """Test that Unicode characters in properties are handled correctly."""
        wb = Workbook()

        # Set properties with Unicode characters
        wb.document_properties.core.title = "测试文档"
        wb.document_properties.core.creator = "作者"
        wb.document_properties.core.description = "这是一份测试文档，包含Unicode字符"

        # Save and reload
        path = os.path.join(self.test_dir, "unicode_properties.xlsx")
        wb.save(path)

        # Reload and verify
        wb2 = Workbook(path)
        self.assertEqual(wb2.document_properties.core.title, "测试文档")
        self.assertEqual(wb2.document_properties.core.creator, "作者")
        self.assertEqual(wb2.document_properties.core.description, "这是一份测试文档，包含Unicode字符")

    def test_document_properties_default_values(self):
        """Test that default properties are set correctly when not explicitly set."""
        wb = Workbook()

        # Add some data
        ws = wb.worksheets[0]
        ws.cells["A1"].value = "Test"

        # Save and reload
        path = os.path.join(self.test_dir, "default_properties.xlsx")
        wb.save(path)

        # Reload and verify defaults
        wb2 = Workbook(path)

        # Core properties should be None or have default values
        self.assertIsNone(wb2.document_properties.core.title)
        self.assertIsNone(wb2.document_properties.core.subject)
        self.assertIsNone(wb2.document_properties.core.creator)

        # Extended properties should have defaults
        self.assertEqual(wb2.document_properties.extended.application, "Microsoft Excel")
        self.assertEqual(wb2.document_properties.extended.doc_security, 0)
        self.assertFalse(wb2.document_properties.extended.scale_crop)
        self.assertFalse(wb2.document_properties.extended.links_up_to_date)
        self.assertFalse(wb2.document_properties.extended.shared_doc)

    def test_document_properties_multiple_workbooks(self):
        """Test that properties work correctly with multiple workbooks."""
        # Create first workbook with properties
        wb1 = Workbook()
        wb1.document_properties.core.title = "Workbook 1"
        wb1.document_properties.core.creator = "Author 1"
        wb1.document_properties.extended.company = "Company 1"
        path1 = os.path.join(self.test_dir, "workbook1_properties.xlsx")
        wb1.save(path1)

        # Create second workbook with different properties
        wb2 = Workbook()
        wb2.document_properties.core.title = "Workbook 2"
        wb2.document_properties.core.creator = "Author 2"
        wb2.document_properties.extended.company = "Company 2"
        path2 = os.path.join(self.test_dir, "workbook2_properties.xlsx")
        wb2.save(path2)

        # Verify first workbook
        wb1_reloaded = Workbook(path1)
        self.assertEqual(wb1_reloaded.document_properties.core.title, "Workbook 1")
        self.assertEqual(wb1_reloaded.document_properties.core.creator, "Author 1")
        self.assertEqual(wb1_reloaded.document_properties.extended.company, "Company 1")

        # Verify second workbook
        wb2_reloaded = Workbook(path2)
        self.assertEqual(wb2_reloaded.document_properties.core.title, "Workbook 2")
        self.assertEqual(wb2_reloaded.document_properties.core.creator, "Author 2")
        self.assertEqual(wb2_reloaded.document_properties.extended.company, "Company 2")

    def test_document_properties_xml_structure(self):
        """Test that the XML structure of document properties is correct."""
        wb = Workbook()

        # Set some properties
        wb.document_properties.core.title = "XML Structure Test"
        wb.document_properties.extended.company = "Test Company"

        # Save
        path = os.path.join(self.test_dir, "xml_structure_properties.xlsx")
        wb.save(path)

        # Verify core.xml structure
        with zipfile.[identifier omitted](path, 'r') as zf:
            core_xml = zf.read('docProps/core.xml').decode('utf-8')
            self.assertIn('cp:coreProperties', core_xml)
            self.assertIn('xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"', core_xml)
            self.assertIn('xmlns:dc="http://purl.org/dc/elements/1.1/"', core_xml)
            self.assertIn('xmlns:dcterms="http://purl.org/dc/terms/"', core_xml)

        # Verify app.xml structure
        with zipfile.[identifier omitted](path, 'r') as zf:
            app_xml = zf.read('docProps/app.xml').decode('utf-8')
            self.assertIn('Properties', app_xml)
            self.assertIn('xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"', app_xml)
            self.assertIn('xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"', app_xml)

if __name__ == '__main__':
    unittest.main()
```

```python
"""
Test Hyperlinks Feature

This test verifies that hyperlinks are correctly created, saved to,
and loaded from XLSX files according to ECMA-376 specification.
"""

import unittest
import os
import sys
import zipfile
import xml.etree.[identifier omitted] as ET

# Add parent directory to path to import aspose.cells_foss
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aspose.cells import Workbook

class [identifier omitted](unittest.[identifier omitted]):
    """Test cases for hyperlinks feature."""

    def setUp(self):
        """Set up test fixtures."""
        self.ns = {
            'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        }
        self.rels_ns = {
            'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'
        }

    def test_add_external_hyperlink(self):
        """Test adding an external web hyperlink."""
        print("\n" + "="*70)
        print("Test: Add External Hyperlink")
        print("="*70)

        # Create workbook
        wb = Workbook()
        ws = wb.worksheets[0]
        ws.name = "Hyperlinks"

        # Add external hyperlink
        print("\nAdding external hyperlink to A1...")
        link = ws.hyperlinks.add("A1", "https://www.example.com")
        link.text_to_display = "Visit Example"
        link.screen_tip = "Click to visit example.com"

        # Add cell value for display
        ws.cells['A1'].value = "Visit Example"

        # Verify hyperlink properties
        self.assertEqual(link.range, "A1")
        self.assertEqual(link.address, "https://www.example.com")
        self.assertEqual(link.text_to_display, "Visit Example")
        self.assertEqual(link.screen_tip, "Click to visit example.com")
        self.assertEqual(link.type, "External")
        print("  [OK] Hyperlink created successfully")

        # Verify collection
        self.assertEqual(ws.hyperlinks.count, 1)
        print(f"  [OK] Collection has {ws.hyperlinks.count} hyperlink(s)")

        # Save to file
        output_file = "outputfiles/test_hyperlink_external.xlsx"
        print(f"\nSaving to {output_file}...")
        wb.save(output_file)
        self.assertTrue(os.path.exists(output_file))
        print(f"  [OK] File saved successfully")

        print("="*70 + "\n")

    def test_add_internal_hyperlink(self):
        """Test adding an internal hyperlink to another sheet."""
        print("\n" + "="*70)
        print("Test: Add Internal Hyperlink")
        print("="*70)

        # Create workbook with two sheets
        wb = Workbook()
        ws1 = wb.worksheets[0]
        ws1.name = "[identifier omitted]"
        from aspose.cells import Worksheet
        ws2 = Worksheet("[identifier omitted]")
        wb.worksheets.append(ws2)

        # Add internal hyperlink
        print("\nAdding internal hyperlink to A1...")
        link = ws1.hyperlinks.add("A1", sub_address="[identifier omitted]!A1")
        link.text_to_display = "Go to [identifier omitted]"
        link.screen_tip = "Navigate to [identifier omitted]"

        # Add cell values for display
        ws1.cells['A1'].value = "Go to [identifier omitted]"
        ws2.cells['A1'].value = "Welcome to [identifier omitted]!"

        # Verify hyperlink properties
        self.assertEqual(link.range, "A1")
        self.assertEqual(link.sub_address, "[identifier omitted]!A1")
        self.assertEqual(link.text_to_display, "Go to [identifier omitted]")
        self.assertEqual(link.type, "Internal")
        print("  [OK] Internal hyperlink created")

        # Save to file
        output_file = "outputfiles/test_hyperlink_internal.xlsx"
        print(f"\nSaving to {output_file}...")
        wb.save(output_file)
        self.assertTrue(os.path.exists(output_file))
        print(f"  [OK] File saved successfully")

        print("="*70 + "\n")

    def test_hyperlink_roundtrip(self):
        """Test that hyperlinks survive save/load roundtrip."""
        print("\n" + "="*70)
        print("Test: Hyperlink Roundtrip (Save/Load)")
        print("="*70)

        # Create workbook with hyperlinks
        wb = Workbook()
        ws = wb.worksheets[0]
        ws.name = "Links"

        # Add different types of hyperlinks
        print("\nAdding various hyperlink types...")
        link1 = ws.hyperlinks.add("A1", "https://www.example.com")
        link1.text_to_display = "Example Website"
        link1.screen_tip = "Visit example.com"
        print("  Added: External HTTPS link at A1")

        link2 = ws.hyperlinks.add("A2", "mailto:user@example.com")
        link2.text_to_display = "Email Us"
        link2.screen_tip = "Send us an email"
        print("  Added: Email link at A2")

        link3 = ws.hyperlinks.add("A3", "ftp://ftp.example.com/files")
        link3.text_to_display = "FTP Server"
        print("  Added: FTP link at A3")

        link4 = ws.hyperlinks.add("A4", sub_address="Links!A1")
        link4.text_to_display = "Go to Top"
        link4.screen_tip = "Jump to cell A1"
        print("  Added: Internal link at A4")

        # Add cell values
        ws.cells['A1'].value = "Example Website"
        ws.cells['A2'].value = "Email Us"
        ws.cells['A3'].value = "FTP Server"
        ws.cells['A4'].value = "Go to Top"

        # Save
        output_file = "outputfiles/test_hyperlinks_roundtrip.xlsx"
        print(f"\nSaving to {output_file}...")
        wb.save(output_file)
        self.assertTrue(os.path.exists(output_file))

        # Verify XML structure
        print("\nVerifying XML structure...")
        with zipfile.[identifier omitted](output_file, 'r') as zf:
            # Check worksheet XML
            sheet_xml = zf.read('xl/worksheets/sheet1.xml').decode('utf-8')
            print(f"  Worksheet XML length: {len(sheet_xml)} bytes")

            # Parse and verify hyperlinks element
            root = ET.fromstring(sheet_xml)
            hyperlinks_elem = root.find('main:hyperlinks', self.ns)
            self.assertIsNotNone(hyperlinks_elem, "hyperlinks element should exist")

            hyperlink_elems = hyperlinks_elem.findall('main:hyperlink', self.ns)
            self.assertEqual(len(hyperlink_elems), 4, "Should have 4 hyperlinks")
            print(f"  [OK] Found {len(hyperlink_elems)} hyperlink elements")

            # Verify first hyperlink (external HTTPS)
            link1_elem = hyperlink_elems[0]
            self.assertEqual(link1_elem.get('ref'), 'A1')
            self.assertIsNotNone(link1_elem.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'))
            self.assertEqual(link1_elem.get('display'), 'Example Website')
            self.assertEqual(link1_elem.get('tooltip'), 'Visit example.com')
            print("  [OK] First hyperlink (HTTPS) attributes correct")

            # Verify internal hyperlink (A4)
            link4_elem = hyperlink_elems[3]
            self.assertEqual(link4_elem.get('ref'), 'A4')
            self.assertEqual(link4_elem.get('location'), 'Links!A1')
            self.assertEqual(link4_elem.get('display'), 'Go to Top')
            self.assertEqual(link4_elem.get('tooltip'), 'Jump to cell A1')
            print("  [OK] Internal hyperlink attributes correct")

            # Check relationships file
            rels_xml = zf.read('xl/worksheets/_rels/sheet1.xml.rels').decode('utf-8')
            rels_root = ET.fromstring(rels_xml)
            rel_elems = rels_root.findall('rel:Relationship', self.rels_ns)

            hyperlink_rels = [rel for rel in rel_elems
                            if 'hyperlink' in rel.get('Type', '')]
            self.assertEqual(len(hyperlink_rels), 3, "Should have 3 external hyperlink relationships")
            print(f"  [OK] Found {len(hyperlink_rels)} external hyperlink relationships")

            # Verify relationship targets
            targets = [rel.get('Target') for rel in hyperlink_rels]
            self.assertIn('https://www.example.com', targets)
            self.assertIn('mailto:user@example.com', targets)
            self.assertIn('ftp://ftp.example.com/files', targets)
            print("  [OK] Relationship targets correct (https, mailto, ftp)")

        # Load back
        print("\nLoading workbook back...")
        wb_loaded = Workbook(output_file)
        ws_loaded = wb_loaded.worksheets[0]

        # Verify hyperlinks loaded correctly
        print("Verifying loaded hyperlinks...")
        self.assertEqual(ws_loaded.hyperlinks.count, 4, "Should load 4 hyperlinks")

        # Find hyperlinks by range
        loaded_links = list(ws_loaded.hyperlinks)
        link1_loaded = next((l for l in loaded_links if l.range == 'A1'), None)
        link2_loaded = next((l for l in loaded_links if l.range == 'A2'), None)
        link3_loaded = next((l for l in loaded_links if l.range == 'A3'), None)
        link4_loaded = next((l for l in loaded_links if l.range == 'A4'), None)

        self.assertIsNotNone(link1_loaded)
        self.assertIsNotNone(link2_loaded)
        self.assertIsNotNone(link3_loaded)
        self.assertIsNotNone(link4_loaded)

        # Verify link1 (HTTPS)
        self.assertEqual(link1_loaded.address, 'https://www.example.com')
        self.assertEqual(link1_loaded.text_to_display, 'Example Website')
        self.assertEqual(link1_loaded.screen_tip, 'Visit example.com')
        self.assertEqual(link1_loaded.type, 'External')
        print("  [OK] Link 1 (HTTPS) loaded correctly")

        # Verify link2 (Email)
        self.assertEqual(link2_loaded.address, 'mailto:user@example.com')
        self.assertEqual(link2_loaded.text_to_display, 'Email Us')
        self.assertEqual(link2_loaded.screen_tip, 'Send us an email')
        self.assertEqual(link2_loaded.type, 'External')
        print("  [OK] Link 2 (Email) loaded correctly")

        # Verify link3 (FTP)
        self.assertEqual(link3_loaded.address, 'ftp://ftp.example.com/files')
        self.assertEqual(link3_loaded.text_to_display, 'FTP Server')
        self.assertEqual(link3_loaded.type, 'External')
        print("  [OK] Link 3 (FTP) loaded correctly")

        # Verify link4 (Internal)
        self.assertEqual(link4_loaded.sub_address, 'Links!A1')
        self.assertEqual(link4_loaded.text_to_display, 'Go to Top')
        self.assertEqual(link4_loaded.screen_tip, 'Jump to cell A1')
        self.assertEqual(link4_loaded.type, 'Internal')
        print("  [OK] Link 4 (Internal) loaded correctly")

        print("\n[OK] All 4 hyperlink types preserved through roundtrip!")
        print("="*70 + "\n")

    def test_multiple_hyperlinks(self):
        """Test adding multiple hyperlinks to a worksheet."""
        print("\n" + "="*70)
        print("Test: Multiple Hyperlinks")
        print("="*70)

        wb = Workbook()
        ws = wb.worksheets[0]
        ws.name = "Links"

        # Add multiple hyperlinks
        print("\nAdding 5 hyperlinks...")
        ws.hyperlinks.add("A1", "https://www.google.com", text_to_display="Google")
        ws.hyperlinks.add("A2", "https://www.github.com", text_to_display="GitHub")
        ws.hyperlinks.add("A3", "https://www.python.org", text_to_display="Python")
        ws.hyperlinks.add("B1", "mailto:info@example.com", text_to_display="Contact")
        ws.hyperlinks.add("B2", sub_address="[identifier omitted]!A1", text_to_display="Top")

        # Add cell values for display
        ws.cells['A1'].value = "Google"
        ws.cells['A2'].value = "GitHub"
        ws.cells['A3'].value = "Python"
        ws.cells['B1'].value = "Contact"
        ws.cells['B2'].value = "Top"

        self.assertEqual(ws.hyperlinks.count, 5)
        print(f"  [OK] Added {ws.hyperlinks.count} hyperlinks")

        # Iterate over hyperlinks
        print("\nHyperlinks:")
        for i, link in enumerate(ws.hyperlinks):
            print(f"  {i+1}. {link.range}: {link.text_to_display or '(no display)'}")

        # Save to file
        output_file = "outputfiles/test_hyperlinks_multiple.xlsx"
        print(f"\nSaving to {output_file}...")
        wb.save(output_file)
        self.assertTrue(os.path.exists(output_file))
        print(f"  [OK] File saved successfully")

        print("="*70 + "\n")

    def test_delete_hyperlink(self):
        """Test deleting hyperlinks."""
        print("\n" + "="*70)
        print("Test: Delete Hyperlink")
        print("="*70)

        wb = Workbook()
        ws = wb.worksheets[0]
        ws.name = "[identifier omitted]"

        # Add hyperlinks
        ws.hyperlinks.add("A1", "https://www.example1.com", text_to_display="Link 1")
        ws.hyperlinks.add("A2", "https://www.example2.com", text_to_display="Link 2")
        ws.hyperlinks.add("A3", "https://www.example3.com", text_to_display="Link 3")
        ws.hyperlinks.add("A4", "https://www.example4.com", text_to_display="Link 4")

        # Add cell values
        ws.cells['A1'].value = "Link 1"
        ws.cells['A2'].value = "Link 2"
        ws.cells['A3'].value = "Link 3"
        ws.cells['A4'].value = "Link 4 (will remain)"

        self.assertEqual(ws.hyperlinks.count, 4)
        print(f"Initial count: {ws.hyperlinks.count}")

        # Delete by index (delete second link - A2)
        ws.hyperlinks.delete(index=1)
        self.assertEqual(ws.hyperlinks.count, 3)
        print(f"After delete by index: {ws.hyperlinks.count}")

        # Delete by object (delete first remaining link - A1)
        link = ws.hyperlinks[0]
        ws.hyperlinks.delete(hyperlink=link)
        self.assertEqual(ws.hyperlinks.count, 2)
        print(f"After delete by object: {ws.hyperlinks.count}")

        # Delete one more (delete A3)
        ws.hyperlinks.delete(index=0)
        self.assertEqual(ws.hyperlinks.count, 1)
        print(f"After another delete: {ws.hyperlinks.count}")

        # Save file with remaining hyperlink (A4)
        output_file = "outputfiles/test_hyperlinks_delete.xlsx"
        print(f"\nSaving to {output_file} (1 hyperlink remaining)...")
        wb.save(output_file)
        self.assertTrue(os.path.exists(output_file))
        print(f"  [OK] File saved successfully")
        print(f"  Remaining hyperlink: {ws.hyperlinks[0].range} - {ws.hyperlinks[0].text_to_display}")

        # Test clear all on a new workbook
        wb2 = Workbook()
        ws2 = wb2.worksheets[0]
        ws2.hyperlinks.add("B1", "https://www.test.com")
        ws2.hyperlinks.clear()
        self.assertEqual(ws2.hyperlinks.count, 0)
        print(f"\nAfter clear on new workbook: {ws2.hyperlinks.count}")

        print("="*70 + "\n")

    def test_hyperlink_validation(self):
        """Test hyperlink validation."""
        print("\n" + "="*70)
        print("Test: Hyperlink Validation")
        print("="*70)

        wb = Workbook()
        ws = wb.worksheets[0]

        # Test: Cannot specify both address and sub_address
        print("\nTest: Cannot specify both address and sub_address...")
        with self.assertRaises(ValueError) as context:
            ws.hyperlinks.add("A1", "https://www.example.com", "[identifier omitted]!A1")
        print(f"  [OK] Raised ValueError: {context.exception}")

        # Test: Must specify either address or sub_address
        print("\nTest: Must specify either address or sub_address...")
        with self.assertRaises(ValueError) as context:
            ws.hyperlinks.add("A1")
        print(f"  [OK] Raised ValueError: {context.exception}")

        print("="*70 + "\n")

    def test_hyperlink_element_order(self):
        """Test that hyperlinks appear in correct order in XML."""
        print("\n" + "="*70)
        print("Test: Hyperlink Element Order (ECMA-376)")
        print("="*70)

        wb = Workbook()
        ws = wb.worksheets[0]

        # Add some data and features
        ws.cells['A1'].value = "Data"
        ws.hyperlinks.add("B1", "https://www.example.com")

        # Save
        output_file = "outputfiles/test_hyperlink_order.xlsx"
        print(f"\nSaving to {output_file}...")
        wb.save(output_file)

        # Verify element order
        print("Verifying element order...")
        with zipfile.[identifier omitted](output_file, 'r') as zf:
            sheet_xml = zf.read('xl/worksheets/sheet1.xml').decode('utf-8')
            root = ET.fromstring(sheet_xml)

            # Get all child elements
            children = list(root)
            element_names = [child.tag.split('}')[-1] for child in children]

            print(f"\nElement order: {element_names}")

            # Verify hyperlinks comes after sheetData
            if 'sheetData' in element_names and 'hyperlinks' in element_names:
                data_index = element_names.index('sheetData')
                hyperlinks_index = element_names.index('hyperlinks')
                self.assertLess(data_index, hyperlinks_index,
                              "sheetData must come before hyperlinks")
                print(f"  sheetData at index {data_index}")
                print(f"  hyperlinks at index {hyperlinks_index}")
                print("  [OK] Order is correct")

        print("\n[OK] Element order complies with ECMA-376")
        print("="*70 + "\n")

    def test_file_and_unc_hyperlinks(self):
        """Test file path and UNC path hyperlinks."""
        print("\n" + "="*70)
        print("Test: File and UNC Path Hyperlinks")
        print("="*70)

        wb = Workbook()
        ws = wb.worksheets[0]
        ws.name = "[identifier omitted]"

        # Add file path hyperlinks (Windows style)
        print("\nAdding file path hyperlinks...")
        link1 = ws.hyperlinks.add("A1", "file:///C:/Documents/report.pdf")
        link1.text_to_display = "Monthly Report"
        link1.screen_tip = "Open report in PDF viewer"
        print("  Added: Local file path (C:) at A1")

        link2 = ws.hyperlinks.add("A2", "file:///C:/Users/Documents/data.xlsx")
        link2.text_to_display = "Data File"
        print("  Added: Local Excel file at A2")

        # Add UNC path hyperlink
        link3 = ws.hyperlinks.add("A3", "file://server/share/document.docx")
        link3.text_to_display = "Network Document"
        link3.screen_tip = "Access network share"
        print("  Added: UNC network path at A3")

        # Add relative file path
        link4 = ws.hyperlinks.add("A4", "file:///./resources/config.json")
        link4.text_to_display = "Config File"
        print("  Added: Relative file path at A4")

        # Add cell values
        ws.cells['A1'].value = "Monthly Report"
        ws.cells['A2'].value = "Data File"
        ws.cells['A3'].value = "Network Document"
        ws.cells['A4'].value = "Config File"

        self.assertEqual(ws.hyperlinks.count, 4)
        print(f"\n[OK] Added {ws.hyperlinks.count} file/UNC hyperlinks")

        # Save to file
        output_file = "outputfiles/test_hyperlinks_files.xlsx"
        print(f"\nSaving to {output_file}...")
        wb.save(output_file)
        self.assertTrue(os.path.exists(output_file))
        print(f"  [OK] File saved successfully")

        # Load and verify
        print("\nLoading back to verify...")
        wb_loaded = Workbook(output_file)
        ws_loaded = wb_loaded.worksheets[0]
        self.assertEqual(ws_loaded.hyperlinks.count, 4)

        # Verify each link type
        loaded_links = list(ws_loaded.hyperlinks)
        for link in loaded_links:
            self.assertTrue(link.address.startswith("file://"))
            print(f"  [OK] {link.range}: {link.text_to_display}")

        print("\n[OK] All file path hyperlinks working correctly!")
        print("="*70 + "\n")

    def test_comprehensive_mixed_hyperlinks(self):
        """Test a worksheet with all hyperlink types mixed together."""
        print("\n" + "="*70)
        print("Test: Comprehensive Mixed Hyperlink Types")
        print("="*70)

        wb = Workbook()
        ws = wb.worksheets[0]
        ws.name = "[identifier omitted]"

        # Add a variety of hyperlinks in a realistic scenario
        print("\nCreating comprehensive hyperlink test sheet...")

        # Header
        ws.cells['A1'].value = "Hyperlink Type"
        ws.cells['B1'].value = "Link"
        ws.cells['C1'].value = "Description"

        # Web links (HTTPS, HTTP)
        ws.cells['A2'].value = "Web (HTTPS)"
        ws.hyperlinks.add("B2", "https://www.example.com", text_to_display="Example Site")
        ws.cells['B2'].value = "Example Site"
        ws.cells['C2'].value = "Secure website link"

        ws.cells['A3'].value = "Web (HTTP)"
        ws.hyperlinks.add("B3", "http://legacy.example.com", text_to_display="Legacy Site")
        ws.cells['B3'].value = "Legacy Site"
        ws.cells['C3'].value = "Non-secure legacy site"

        # Email links
        ws.cells['A4'].value = "Email (Simple)"
        ws.hyperlinks.add("B4", "mailto:contact@example.com", text_to_display="Contact Email")
        ws.cells['B4'].value = "Contact Email"
        ws.cells['C4'].value = "Send email to contact"

        ws.cells['A5'].value = "Email (Subject)"
        ws.hyperlinks.add("B5", "mailto:support@example.com?subject=Help%20Request",
                          text_to_display="Support Email")
        ws.cells['B5'].value = "Support Email"
        ws.cells['C5'].value = "Email with preset subject"

        # File links
        ws.cells['A6'].value = "Local File"
        ws.hyperlinks.add("B6", "file:///C:/Reports/annual.pdf", text_to_display="Annual Report")
        ws.cells['B6'].value = "Annual Report"
        ws.cells['C6'].value = "Open local PDF file"

        ws.cells['A7'].value = "Network File"
        ws.hyperlinks.add("B7", "file://server/shared/data.xlsx", text_to_display="Shared Data")
        ws.cells['B7'].value = "Shared Data"
        ws.cells['C7'].value = "Access network share"

        # FTP link
        ws.cells['A8'].value = "FTP Server"
        ws.hyperlinks.add("B8", "ftp://ftp.example.com/files/", text_to_display="FTP Files")
        ws.cells['B8'].value = "FTP Files"
        ws.cells['C8'].value = "Browse FTP directory"

        # Internal links
        ws.cells['A9'].value = "Internal (Same Sheet)"
        ws.hyperlinks.add("B9", sub_address="[identifier omitted]!A1", text_to_display="Go to Top")
        ws.cells['B9'].value = "Go to Top"
        ws.cells['C9'].value = "Jump to cell A1"

        ws.cells['A10'].value = "Internal (Named Range)"
        ws.hyperlinks.add("B10", sub_address="[identifier omitted]!B2:B9",
                          text_to_display="View All Links")
        ws.cells['B10'].value = "View All Links"
        ws.cells['C10'].value = "Select range of links"

        total_links = ws.hyperlinks.count
        self.assertEqual(total_links, 9)
        print(f"  [OK] Created {total_links} hyperlinks of various types")

        # List all hyperlinks
        print("\nHyperlink Summary:")
        for i, link in enumerate(ws.hyperlinks, 1):
            link_type = link.type
            target = link.address if link.address else link.sub_address
            print(f"  {i}. {link.range}: {link_type} -> {target[:50]}...")

        # Save to file
        output_file = "outputfiles/test_hyperlinks_comprehensive.xlsx"
        print(f"\nSaving to {output_file}...")
        wb.save(output_file)
        self.assertTrue(os.path.exists(output_file))
        file_size = os.path.getsize(output_file)
        print(f"  [OK] File saved ({file_size} bytes)")

        # Load and verify all hyperlinks
        print("\nVerifying roundtrip...")
        wb_loaded = Workbook(output_file)
        ws_loaded = wb_loaded.worksheets[0]
        self.assertEqual(ws_loaded.hyperlinks.count, total_links)
        print(f"  [OK] All {ws_loaded.hyperlinks.count} hyperlinks loaded successfully")

        # Verify each type is present
        loaded_links = list(ws_loaded.hyperlinks)
        external_count = sum(1 for l in loaded_links if l.type == "External")
        internal_count = sum(1 for l in loaded_links if l.type == "Internal")
        self.assertEqual(external_count, 7, "Should have 7 external hyperlinks")
        self.assertEqual(internal_count, 2, "Should have 2 internal hyperlinks")
        print(f"  [OK] External: {external_count}, Internal: {internal_count}")

        print("\n[OK] Comprehensive mixed hyperlink test completed!")
        print("="*70 + "\n")

if __name__ == '__main__':
    # Create output directory if it doesn't exist
    os.makedirs('outputfiles', exist_ok=True)

    # Run tests
    unittest.main(verbosity=2)
```

```python
"""
Test Suite for XLSX to JSON Conversion

This test suite covers converting Excel files to JSON format including:
- Basic XLSX to JSON conversion
- Loading comprehensive sales report data
- Exporting to JSON format
"""

import unittest
import os
import sys
import json

# Add parent directory to path to import aspose.cells_foss
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aspose.cells import Workbook, SaveFormat
from aspose.cells.json_handler import JsonHandler, JsonSaveOptions

class TestXLSXToJSONConversion(unittest.[identifier omitted]):
    """Test XLSX to JSON conversion functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = 'outputfiles'
        os.makedirs(self.test_dir, exist_ok=True)

    def test_sales_report_to_json(self):
        """Test converting comprehensive sales report to JSON."""
        # Load Excel file
        input_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'input/sales_report_comprehensive.xlsx')
        self.assertTrue(os.path.exists(input_path),
                       f"Input file {input_path} does not exist")

        wb = Workbook(input_path)

        # Verify workbook loaded
        self.assertGreater(len(wb.worksheets), 0,
                          "Workbook should have at least one worksheet")

        # Export to JSON
        output_path = os.path.join(self.test_dir, 'sales_report_comprehensive.json')
        wb.save_as_json(output_path)

        # Verify JSON file was created
        self.assertTrue(os.path.exists(output_path),
                       f"JSON file {output_path} was not created")

        # Verify JSON file is valid
        with open(output_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # Verify JSON structure
        self.assertIn('worksheets', json_data,
                     "JSON should contain 'worksheets' key")
        self.assertIsInstance(json_data['worksheets'], list,
                          "'worksheets' should be a list")

        # Verify each worksheet has expected structure
        for sheet in json_data['worksheets']:
            self.assertIn('name', sheet,
                         "Each worksheet should have 'name'")
            self.assertIn('data', sheet,
                         "Each worksheet should have 'data'")
            self.assertIsInstance(sheet['data'], list,
                              "'data' should be a list")

        # Print summary
        print(f"\nSuccessfully converted {input_path} to {output_path}")
        print(f"Number of worksheets: {len(wb.worksheets)}")
        for i, ws in enumerate(wb.worksheets):
            print(f"  Worksheet {i}: {ws.name}")
        print(f"JSON file size: {os.path.getsize(output_path)} bytes")

    def test_sales_report_to_json_with_options(self):
        """Test converting sales report to JSON with custom options."""
        # Load Excel file
        input_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'input/sales_report_comprehensive.xlsx')
        wb = Workbook(input_path)

        # Create custom options
        options = JsonSaveOptions()
        options.include_worksheet_name = True
        options.indent = 4
        options.skip_empty_rows = True
        options.empty_cell_value = ""

        # Export to JSON with options
        output_path = os.path.join(self.test_dir, 'sales_report_comprehensive_custom.json')
        wb.save_as_json(output_path, options)

        # Verify JSON file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify JSON file is valid and has proper indentation
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            json_data = json.loads(content)

        # Verify indentation (4 spaces)
        self.assertIn('    ', content,
                     "JSON should be indented with 4 spaces")

        # Verify structure
        self.assertIn('worksheets', json_data)

        print(f"\nSuccessfully converted with custom options to {output_path}")
        print(f"JSON file size: {os.path.getsize(output_path)} bytes")

    def test_sales_report_to_json_single_worksheet(self):
        """Test converting only first worksheet to JSON."""
        # Load Excel file
        input_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'input/sales_report_comprehensive.xlsx')
        wb = Workbook(input_path)

        # Create options to export only first worksheet
        options = JsonSaveOptions()
        options.worksheet_index = 0

        # Export to JSON
        output_path = os.path.join(self.test_dir, 'sales_report_sheet0.json')
        wb.save_as_json(output_path, options)

        # Verify JSON file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify only one worksheet is exported
        with open(output_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        self.assertEqual(len(json_data['worksheets']), 1,
                        "Only one worksheet should be exported")
        self.assertEqual(json_data['worksheets'][0]['name'],
                        wb.worksheets[0].name,
                        "First worksheet name should match")

        print(f"\nSuccessfully exported first worksheet to {output_path}")

    def test_sales_report_to_json_using_save_format(self):
        """Test converting using SaveFormat.JSON."""
        # Load Excel file
        input_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'input/sales_report_comprehensive.xlsx')
        wb = Workbook(input_path)

        # Export to JSON using SaveFormat
        output_path = os.path.join(self.test_dir, 'sales_report_using_save_format.json')
        wb.save(output_path, SaveFormat.JSON)

        # Verify JSON file was created
        self.assertTrue(os.path.exists(output_path))

        # Verify JSON file is valid
        with open(output_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        self.assertIn('worksheets', json_data)

        print(f"\nSuccessfully converted using SaveFormat.JSON to {output_path}")

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

The `Workbook` class in Aspose.Cells FOSS represents an Excel workbook and provides methods to load, create, and manipulate spreadsheet data. It supports loading from files or streams and initializing new workbooks with default `worksheets`.

| Constructor | Description |
|-------------|-------------|
| `Workbook()` | Initializes a new instance of the `Workbook` class with one default worksheet. |
| `Workbook(file_path: str)` | Loads an existing Excel file from the specified path. |
| `Workbook(stream)` | Loads an Excel workbook from a file-like stream object. |
| `Workbook(template_file: str, load_options)` | Loads a workbook using specified load options. |
| `Workbook(load_data_options)` | Initializes a new workbook with custom data loading behavior. |
| `Workbook(template_file: str)` | Loads a workbook from a template file. |
| `Workbook(file_path: str, load_options)` | Loads a workbook from a file with custom load options. |
| `Workbook(stream, load_options)` | Loads a workbook from a stream with custom load options. |

```python
import aspose.cells

# Create a new workbook
workbook = aspose.cells.Workbook()

# Load an existing workbook
workbook = aspose.cells.Workbook("input.xlsx")
```

## Properties

The `Workbook` class exposes several read-only `properties` that provide access to core workbook metadata and collections. These `properties` are initialized at construction and reflect the current state of the workbook instance.

| Name | Type | Description |
|------|------|-------------|
| `worksheets` | WorksheetCollection | Read-only collection of `worksheets` in the workbook. |
| `file_path` | `str` | Read-only path of the file from which the workbook was loaded; empty if newly created. |
| `properties` | `dict` | Read-only dictionary of built-in document `properties`. |
| `document_properties` | `dict` | Read-only dictionary of custom document `properties`. |
| `protection` | `dict` | Read-only dictionary containing current workbook `protection` settings. |
| default_style | `Style` | Read-only default `style` applied to new `cells`. |
| `is_protected` | `bool` | Read-only flag indicating whether the workbook structure is protected. |
| encryption_type | `str` | Read-only string indicating the encryption algorithm used (e.g., "AGILE"). |
| is_write_protected | `bool` | Read-only flag indicating whether the workbook is write-protected. |
| is_restricted | `bool` | Read-only flag indicating whether the workbook is restricted for editing. |

```python
from aspose.cells import Workbook

workbook = Workbook("input.xlsx")
print(f"File path: {workbook.file_path}")
print(f"Worksheets count: {len(workbook.worksheets)}")
print(f"Is protected: {workbook.is_protected}")
print(f"Protection settings: {workbook.protection}")
```

## Methods

The `Workbook` class provides core methods for managing `worksheets` and workbook-level operations. Methods include adding, removing, and retrieving `worksheets` by index or `name`. The `CSVHandler` and `JsonHandler` classes offer static methods for exporting workbook data to CSV and JSON formats, including in-memory string/dict representations. All methods listed below are part of the public API surface for Aspose.Cells FOSS.

| Method | Return Type | Description |
|--------|-------------|-------------|
| `add_worksheet(name)` | `Worksheet` | Adds a new worksheet with the specified `name`. |
| `get_worksheet(index_or_name)` | `Worksheet` | Returns the worksheet at the given 0-based index or with the given `name`. |
| `get_worksheet_by_name(name)` | `Worksheet` | Returns the worksheet with the given `name`, or `None` if not found. |
| `remove_worksheet(index_or_name)` | `None` | Removes the worksheet at the given index or with the given `name`. |
| `unprotect(password)` | `None` | Removes `protection` from the workbook using the specified password. |
| `create_worksheet(name)` | `Worksheet` | Creates and returns a new worksheet with the specified `name`. |
| `CSVHandler.save_csv(workbook, file_path, options)` | `None` | Saves the workbook to a CSV file at the specified path. |
| `CSVHandler.save_csv_to_string(workbook, options)` | `str` | Saves a workbook worksheet to a CSV string. |
| `CSVHandler.load_csv(workbook, file_path, options)` | `None` | Loads CSV data from a file into the workbook. |
| `CSVHandler.load_csv_from_string(workbook, csv_content, options)` | `None` | Loads CSV data from a string into the workbook. |
| `JsonHandler.save_json(workbook, file_path, options)` | `None` | Saves the workbook to a JSON file. |
| `JsonHandler.save_json_to_dict(workbook, options)` | `Dict[str, Any]` | Converts the workbook to a JSON-serializable dictionary. |
| `MarkdownHandler.save_markdown(workbook, file_path, options)` | `None` | Saves the workbook to a Markdown file. |
| `MarkdownHandler.save_markdown_to_string(workbook, options)` | `str` | Saves the workbook to a Markdown string. |

```python
from aspose.cells import Workbook, CSVHandler

# Create a new workbook and set a value
workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Test"

# Export to CSV string
csv_string = CSVHandler.save_csv_to_string(workbook, None)
print(csv_string)
```

## Example

The following example demonstrates creating a workbook, adding data, and exporting to JSON using the `JsonHandler` class. It also shows how to inspect workbook `protection` settings via the `protection` property.

```python
import aspose.cells

# Create a new workbook
workbook = aspose.cells.Workbook()
worksheet = workbook.worksheets[0]

# Add sample data
worksheet.cells["A1"].value = "Product"
worksheet.cells["B1"].value = "Sales"
worksheet.cells["A2"].value = "Widget"
worksheet.cells["B2"].value = 1250

# Export to JSON using JsonHandler
from aspose.cells import JsonHandler, JsonSaveOptions
options = JsonSaveOptions()
options.include_worksheet_name = True
output_dict = JsonHandler.save_json_to_dict(workbook, options)
print("JSON output keys:", list(output_dict.keys()))

# Check protection settings
protection_settings = workbook.protection
print("Workbook protection:", protection_settings)
```

## See Also

The `Workbook` class provides core spreadsheet functionality. Related handlers enable export to structured formats like JSON, CSV, and Markdown. Use `create_worksheet()` to `add` new sheets, and `get_worksheet()` methods to access existing ones.

```python
import aspose.cells

# Create a new workbook
wb = aspose.cells.Workbook()

# Add a new worksheet
ws = wb.create_worksheet("Data")

# Access a worksheet by index
sheet = wb.get_worksheet(0)

# Access a worksheet by name
sheet_by_name = wb.get_worksheet_by_name("Data")

# Save to XLSX
wb.save("output.xlsx")
```

- [Aspose.Cells FOSS API reference](/reference.aspose.org/cells/python/api-overview/)
- [Introduction to Cells Foss Python](/blog.aspose.org/cells/python/cells-foss-python/)
- [Create all chart types in spreadsheets](/blog.aspose.org/cells/python/create-charts-spreadsheets/)
- [Working with formulas in Aspose.Cells FOSS](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Essential spreadsheet operations guide](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
