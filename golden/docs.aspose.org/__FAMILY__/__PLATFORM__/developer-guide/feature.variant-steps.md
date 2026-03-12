<!-- GOLDEN REFERENCE | Source: cells/en/developer-guide/spreadsheet-locker/_index.md | Original-Grade: A- -->
---
description: Lock Microsoft Excel spreadsheets like XLS, XLSX, XLTM, and XLSM with user-specified passwords and settings.
title: Aspose.Cells Spreadsheet Locker for .NET
type: docs
---


Aspose.Cells Spreadsheet Locker for .NET allows developers to programmatically lock Excel workbooks and protect worksheets, ranges, and overall document structures with user-defined passwords and granular permission settings. Whether you want to prevent unauthorized edits, enforce workbook-level encryption, or restrict access to specific sheet regions, this plugin delivers streamlined protection for XLS, XLSX, XLTM, and [XLSM](https://docs.aspose.net/file-formats/xlsm/) files.

## Installation and Setup

To add Aspose.Cells Spreadsheet Locker for .NET to your project:

1. Install the NuGet package. See the [Installation](https://docs.aspose.net/cells/getting-started/installation/) guide for details.
2. Configure metered licensing before using any API calls to avoid evaluation mode. Refer to the [Metered Licensing](https://docs.aspose.net/cells/getting-started/metered-licensing/) documentation.

## Features and Functionalities

### Supported File Formats

Applies protection to major Excel formats including legacy [BIFF](https://docs.aspose.net/file-formats/biff/) (XLS) and modern Open [XML](https://docs.aspose.net/file-formats/xml/) (XLSX, XLSM, XLTM). Protection settings remain intact across format conversions.

### Workbook-Level Encryption

Apply a password to encrypt the entire workbook stream. This uses standard Office encryption so the file cannot be opened without the correct password. Multiple encryption algorithms are supported for compatibility and security.

### Stream-Based Processing

* **Memory Stream Support**: Lock files directly in memory without disk I/O.
* **Zero File System Access**: Complete protection workflow using streams.
* **Web Integration**: Process uploaded files and return protected versions instantly.
* **In-Memory Validation**: Verify password protection immediately after applying.

### Password Verification and Validation

* **Built-in Password Testing**: Verify that protection was applied correctly.
* **Exception-Based Validation**: Confirm files cannot be opened without correct password.
* **Programmatic Checks**: Use `FileFormatUtil.VerifyPassword()` for password validation.
* **Security Testing**: Ensure protection mechanisms work as expected.

### Worksheet Protection

Restrict editing at the sheet level with options such as:

* Locking cell contents
* Preventing row or column insertions/deletions
* Disabling sorting, filtering, or pivot table edits

### Range-Level Protection

Define editable ranges while keeping formulas or sensitive data locked. Assign distinct passwords per range to grant limited access to specific user groups.

### Structure and Window Protection

Prevent workbook-wide changes like adding, renaming, or deleting worksheets. Lock window settings such as frozen panes or zoom levels to keep the user view consistent.

### Encryption Algorithms and Strength

Choose between AES-256 for high-security or legacy RC4 for compatibility. Algorithm selection is exposed via simple API settings.

### Protection Exceptions and Permissions

Fine-tune permissions by allowing certain actions (e.g., formatting cells or sorting) while keeping other features locked.

### Lock Management and Removal

Unlock sheets, ranges, or entire workbooks programmatically with the correct password. APIs mirror the locking process, and protection status can be queried at runtime.

---

## Usage Examples

### Basic Workbook Protection with LowCode API

The simplest way to protect an Excel file with a password:

```csharp
using Aspose.Cells.LowCode;
using Aspose.Cells;

string src = "template.xlsx";

LowCodeLoadOptions lclopts = new LowCodeLoadOptions();
lclopts.InputFile = src;

LowCodeSaveOptions lcsopts = new LowCodeSaveOptions();
lcsopts.SaveFormat = SaveFormat.Xlsx;
lcsopts.OutputFile = "protected.xlsx";

SpreadsheetLocker.Process(lclopts, lcsopts, "123", null);
```

### Advanced: Stream-Based Protection with Validation

Process files entirely in memory and verify protection was applied correctly:

```csharp
using Aspose.Cells.LowCode;
using Aspose.Cells;
using System.IO;

string src = "template.xlsx";

// Configure load options
LowCodeLoadOptions lclopts = new LowCodeLoadOptions();
lclopts.InputFile = src;

// Configure save options
LowCodeSaveOptions lcsopts = new LowCodeSaveOptions();
lcsopts.SaveFormat = SaveFormat.Xlsx;

// Output to memory stream
MemoryStream ms = new MemoryStream();
lcsopts.OutputStream = ms;

// Apply password protection (password: "123", unprotect password: null)
SpreadsheetLocker.Process(lclopts, lcsopts, "123", null);

// Reset stream position for reading
ms.Seek(0, SeekOrigin.Begin);

// Verify password is correct
FileFormatUtil.VerifyPassword(ms, "123");

// Test that file is actually locked (should fail without password)
ms.Seek(0, SeekOrigin.Begin);
bool fail = false;
try
{
    new Workbook(ms);
    fail = true;  // Should not reach here
}
catch (CellsException e)
{
    if (ExceptionType.IncorrectPassword != e.Code)
    {
        Console.WriteLine("Exception: " + e.Message);
    }
    else
    {
        Console.WriteLine("✓ File is properly locked (cannot open without password)");
    }
}

if (fail)
{
    Console.WriteLine("✗ The resultant file should be locked with password but is not");
}

// Open with correct password (should succeed)
ms.Seek(0, SeekOrigin.Begin);
Workbook protectedWorkbook = new Workbook(ms, new LoadOptions() { Password = "123" });
Console.WriteLine("✓ File opened successfully with correct password");
```

### Feature Breakdown: Password Protection Parameters

The `SpreadsheetLocker.Process()` method accepts four parameters:

```csharp
SpreadsheetLocker.Process(
    loadOptions,      // Load configuration
    saveOptions,      // Save configuration and output destination
    "protect123",     // Password to protect the workbook
    null              // Unprotect password (optional, for removing existing protection)
);
```

**Parameter Details:**
- **Load Options**: Configures input file location and loading behavior
- **Save Options**: Configures output format, destination (file or stream)
- **Protection Password**: Password required to open the workbook
- **Unprotection Password**: Password to remove existing protection (use `null` if not needed)

### Feature Breakdown: Password Verification

Validate that protection was applied successfully:

```csharp
// Method 1: Use FileFormatUtil.VerifyPassword()
ms.Seek(0, SeekOrigin.Begin);
bool isValid = FileFormatUtil.VerifyPassword(ms, "123");
Console.WriteLine($"Password verification: {isValid}");

// Method 2: Try opening without password (should fail)
ms.Seek(0, SeekOrigin.Begin);
try
{
    new Workbook(ms);
    Console.WriteLine("✗ File is not properly protected");
}
catch (CellsException e)
{
    if (e.Code == ExceptionType.IncorrectPassword)
    {
        Console.WriteLine("✓ File is properly protected");
    }
}

// Method 3: Open with correct password (should succeed)
ms.Seek(0, SeekOrigin.Begin);
Workbook wb = new Workbook(ms, new LoadOptions() { Password = "123" });
Console.WriteLine("✓ Correct password works");
```

### Feature Breakdown: Stream Position Management

When working with streams, proper positioning is critical:

```csharp
// After writing to stream
SpreadsheetLocker.Process(lclopts, lcsopts, "123", null);

// MUST reset position before reading
ms.Seek(0, SeekOrigin.Begin);  // Move to start of stream

// Now can read/verify
FileFormatUtil.VerifyPassword(ms, "123");

// Reset again for next operation
ms.Seek(0, SeekOrigin.Begin);
new Workbook(ms, new LoadOptions() { Password = "123" });
```

**Stream Position Best Practices:**
- Always `Seek(0, SeekOrigin.Begin)` before reading from a stream you just wrote to
- Reset position between multiple read operations
- Use `SeekOrigin.Begin` (not `Current` or `End`) for consistency

### Feature Breakdown: Exception Handling for Protection

Handle different error scenarios when working with protected files:

```csharp
ms.Seek(0, SeekOrigin.Begin);

try
{
    // Try to open without password
    Workbook wb = new Workbook(ms);
    Console.WriteLine("Warning: File opened without password!");
}
catch (CellsException e)
{
    switch (e.Code)
    {
        case ExceptionType.IncorrectPassword:
            Console.WriteLine("✓ Password protection is active");
            break;

        case ExceptionType.InvalidFileFormat:
            Console.WriteLine("✗ File format is corrupted");
            break;

        case ExceptionType.FileCorrupted:
            Console.WriteLine("✗ File is corrupted");
            break;

        default:
            Console.WriteLine($"✗ Unexpected error: {e.Message}");
            break;
    }
}
```

### Traditional API: Granular Protection Control

For detailed protection scenarios, use the traditional Workbook API:

```csharp
using Aspose.Cells;

// Load a workbook
Workbook workbook = new Workbook("Workbook.xlsx");

// Protect the entire workbook with a password
workbook.Protect(ProtectionType.All, "password123");

// Protect a specific worksheet
Worksheet sheet = workbook.Worksheets[0];
sheet.Protect(ProtectionType.All, "sheetPass", null);

// Protect workbook structure
workbook.Settings.WriteProtection.Password = "structurePass";

// Save the protected file
workbook.Save("LockedWorkbook.xlsx");
```

### Web API Integration Example

Protect uploaded Excel files in an ASP.NET Core application:

```csharp
using Aspose.Cells;
using Aspose.Cells.LowCode;
using System.IO;

public class AdvancedProtectionService
{
    public void ApplyMultiLevelProtection(string inputPath, string outputPath,
                                         string filePassword, string sheetPassword)
    {
        // Protect the file with Spreadsheet Locker
        LowCodeLoadOptions loadOptions = new LowCodeLoadOptions { InputFile = inputPath };

        // Use memory stream for intermediate processing
        using (MemoryStream ms = new MemoryStream())
        {
            LowCodeSaveOptions saveOptions = new LowCodeSaveOptions
            {
                SaveFormat = SaveFormat.Xlsx,
                OutputStream = ms
            };

            // Apply file-level protection
            SpreadsheetLocker.Process(loadOptions, saveOptions, filePassword, null);

            // Now apply worksheet-level protection
            ms.Position = 0;
            LoadOptions wbLoadOptions = new LoadOptions { Password = filePassword };
            Workbook workbook = new Workbook(ms, wbLoadOptions);

            // Protect all worksheets
            foreach (Worksheet worksheet in workbook.Worksheets)
            {
                // Configure protection options as needed
                ProtectionType protectionType = ProtectionType.All;
                protectionType ^= ProtectionType.Objects;
                protectionType ^= ProtectionType.Scenarios;

                // Apply sheet-level protection
                worksheet.Protect(protectionType, sheetPassword, null);
            }

            // Save the document with both levels of protection
            workbook.Save(outputPath);
        }
    }
}
```

### Batch Protection with Validation

Protect multiple files and verify each one:

```csharp
string[] files = Directory.GetFiles("input", "*.xlsx");
string password = "SecurePass123!";

foreach (string file in files)
{
    try
    {
        LowCodeLoadOptions loadOpts = new LowCodeLoadOptions();
        loadOpts.InputFile = file;

        LowCodeSaveOptions saveOpts = new LowCodeSaveOptions();
        saveOpts.SaveFormat = SaveFormat.Xlsx;

        MemoryStream ms = new MemoryStream();
        saveOpts.OutputStream = ms;

        // Apply protection
        SpreadsheetLocker.Process(loadOpts, saveOpts, password, null);

        // Verify protection
        ms.Seek(0, SeekOrigin.Begin);
        bool isProtected = false;

        try
        {
            new Workbook(ms);  // Should fail
        }
        catch (CellsException e)
        {
            if (e.Code == ExceptionType.IncorrectPassword)
            {
                isProtected = true;
            }
        }

        if (isProtected)
        {
            // Save to output directory
            string outputFile = Path.Combine("output",
                Path.GetFileNameWithoutExtension(file) + "_protected.xlsx");
            File.WriteAllBytes(outputFile, ms.ToArray());
            Console.WriteLine($"✓ Protected: {Path.GetFileName(file)}");
        }
        else
        {
            Console.WriteLine($"✗ Failed to protect: {Path.GetFileName(file)}");
        }
    }
    catch (Exception ex)
    {
        Console.WriteLine($"✗ Error processing {file}: {ex.Message}");
    }
}
```

### Removing Protection

Unlock protected workbooks programmatically:

```csharp
LowCodeLoadOptions loadOpts = new LowCodeLoadOptions();
loadOpts.InputFile = "protected.xlsx";
loadOpts.Password = "123";  // Original password

LowCodeSaveOptions saveOpts = new LowCodeSaveOptions();
saveOpts.SaveFormat = SaveFormat.Xlsx;
saveOpts.OutputFile = "unprotected.xlsx";

// Pass empty string or null for both passwords to remove protection
SpreadsheetLocker.Process(loadOpts, saveOpts, "", "");
```

---

## Tips and Best Practices

### Security Best Practices

* **Strong Passwords**: Use long, complex passwords with AES-256 for sensitive files.
* **Password Rotation**: Rotate passwords regularly in line with security policies.
* **Validation**: Always verify protection was applied using `FileFormatUtil.VerifyPassword()` or exception testing.
* **Testing**: Test that files cannot be opened without the correct password.

### Stream Management

* **Position Reset**: Always call `ms.Seek(0, SeekOrigin.Begin)` before reading from a stream you wrote to.
* **Disposal**: Dispose of streams promptly to free memory.
* **Reuse**: Reset and reuse streams for batch processing to reduce memory pressure.

### Performance Optimization

* **LowCode API**: Use `SpreadsheetLocker.Process()` for optimized performance.
* **Batch Processing**: Process multiple files in parallel for high-throughput scenarios.
* **Memory Streams**: Use streams for web applications to avoid disk I/O overhead.

### Protection Strategies

* **Layered Protection**: Combine worksheet and range protections with workbook-level passwords.
* **Metadata Storage**: Persist protection settings in configuration for automation tasks.
* **Format Preservation**: Reapply protection after format conversions to ensure encryption integrity.
* **Permission Checks**: Use `IsProtected` checks before performing operations to avoid exceptions.

### Production Deployment

* **Initialize Once**: Initialize licensing at startup to avoid evaluation warnings.
* **Error Handling**: Implement comprehensive exception handling for `CellsException` types.
* **Logging**: Log protection operations and validation results for audit trails.
* **Cleanup**: Delete temporary files after processing in web applications.

---

## Common Issues and Resolutions

| Issue | Resolution |
|-------|------------|
| **File not properly protected** | Verify password is not empty string; check `FileFormatUtil.VerifyPassword()` result |
| **Cannot open protected file** | Ensure you're using `LoadOptions` with correct `Password` property |
| **Stream read fails** | Call `ms.Seek(0, SeekOrigin.Begin)` to reset stream position before reading |
| **Exception: IncorrectPassword** | This is expected when testing protection; catch and handle `ExceptionType.IncorrectPassword` |
| **Memory stream is empty** | Ensure `SpreadsheetLocker.Process()` completed successfully before reading stream |
| **File opens without password** | Check that protection was applied; may need to use traditional API for specific protection types |
| **Cannot verify password** | Stream position may be at end; reset with `Seek(0, SeekOrigin.Begin)` |
| **Workbook.Protect() not working** | LowCode API uses different protection mechanism; use appropriate API for your needs |

---

## Frequently Asked Questions

**What is Aspose.Cells Spreadsheet Locker for .NET?**
A specialized tool for applying password protection and encryption to Excel workbooks programmatically in .NET applications.

**How does it differ from Aspose.Cells for .NET?**
Aspose.Cells for .NET is a comprehensive library. The Spreadsheet Locker provides streamlined APIs focused specifically on protection and encryption workflows.

**What types of protection are supported?**
Workbook-level encryption (requires password to open), worksheet protection, range protection, and structure protection.

**Can I protect files in memory without saving to disk?**
Yes! Use `MemoryStream` with `LowCodeSaveOptions.OutputStream` for complete in-memory processing.

**How do I verify protection was applied correctly?**
Use `FileFormatUtil.VerifyPassword()` or try opening the file without a password (should throw `IncorrectPassword` exception).

**What do the four parameters of SpreadsheetLocker.Process() mean?**
1. Load options (input configuration)
2. Save options (output configuration)
3. Protection password (to lock the file)
4. Unprotection password (to remove existing locks, use `null` if not needed)

**Why do I need to call Seek() on the stream?**
After writing to a stream, the position is at the end. You must reset to the beginning with `Seek(0, SeekOrigin.Begin)` before reading.

**Can I use different passwords for different sheets?**
Yes, but you'll need to use the traditional `Workbook` API's per-sheet protection methods rather than the LowCode API.

**How do I remove password protection?**
Pass empty strings or null for both password parameters, or use the traditional API's `Unprotect()` method.

**What encryption algorithms are supported?**
Standard Office encryption including AES-128, AES-256, and legacy RC4 for compatibility.

---

## API Reference Summary

### Key Classes

- **`SpreadsheetLocker`**: Static class providing simplified protection methods
- **`LowCodeLoadOptions`**: Configuration for loading Excel files
- **`LowCodeSaveOptions`**: Configuration for output (file or stream)
- **`FileFormatUtil`**: Utility class for password verification
- **`LoadOptions`**: Options for opening protected workbooks

### Essential Properties

- **`InputFile`**: Source Excel file path
- **`OutputFile`**: Target file path (file-based output)
- **`OutputStream`**: Target stream (stream-based output)
- **`SaveFormat`**: Output file format
- **`Password`**: Password for opening protected workbooks (in `LoadOptions`)

### Key Methods

- **`SpreadsheetLocker.Process(loadOpts, saveOpts, password, unprotectPassword)`**: Apply password protection
- **`FileFormatUtil.VerifyPassword(stream, password)`**: Verify a password is correct
- **`MemoryStream.Seek(offset, origin)`**: Reset stream position for reading
- **`Workbook.Protect(type, password)`**: Traditional API protection method
- **`Workbook.Unprotect(password)`**: Remove protection from workbook

### Exception Types

- **`ExceptionType.IncorrectPassword`**: Thrown when opening protected file without correct password
- **`ExceptionType.InvalidFileFormat`**: File format is not recognized
- **`ExceptionType.FileCorrupted`**: File structure is damaged
