<!-- GOLDEN REFERENCE | Source: barcode/en/Aspose.BarCode.BarCodeRecognition.BarCodeReader.md | Original-Grade: A -->
---
linkTitle: "Class BarCodeReader"
title: "Class BarCodeReader"
description: "BarCodeReader encapsulates an image which may contain one or several barcodes, it then can perform ReadBarCodes operation to detect barcodes."
summary: "BarCodeReader encapsulates an image which may contain one or several barcodes, it then can perform ReadBarCodes operation to detect barcodes."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.BarCode.BarCodeRecognition](/barcode/aspose.barcode.barcoderecognition)
Assembly: Aspose.BarCode.dll (26.2.0)

BarCodeReader encapsulates an image which may contain one or several barcodes, it then can perform ReadBarCodes operation to detect barcodes.

```csharp
[XmlSerialization(Name = "Aspose.BarCode.Reader.Properties")]
public class BarCodeReader : IDisposable
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ←
[BarCodeReader](/barcode/aspose.barcode.barcoderecognition.barcodereader)

#### Implements

[IDisposable](https://learn.microsoft.com/dotnet/api/system.idisposable)

#### Inherited Members

[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype),
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone),
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring),
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)),
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)),
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals),
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Examples

This sample shows how to detect Code39 and Code128 barcodes.

```csharp
using (BarCodeReader reader = new BarCodeReader(@"c:\test.png", DecodeType.Code39, DecodeType.Code128))
{
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeTypeName);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
}
Using reader As New BarCodeReader("c:\test.png", DecodeType.Code39, DecodeType.Code128)
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode Type: " + result.CodeTypeName)
        Console.WriteLine("BarCode CodeText: " + result.CodeText)
    Next
End Using
```

## Constructors

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor"></a> BarCodeReader\(\)

Initializes a new instance of the Aspose.BarCode.BarCodeRecognition.BarCodeReader class with default values.
Requires to set image (SetBitmapImage()) before to call ReadBarCodes() method.

```csharp
public BarCodeReader()
```

#### Examples

This sample shows how to detect Code39 and Code128 barcodes.

```csharp
using (BarCodeReader reader = new BarCodeReader())
{
    reader.SetBarCodeReadType(DecodeType.Code39, DecodeType.Code128);
    reader.SetBarCodeImage(@"c:\test.png");
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeTypeName);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
}
Using reader As New BarCodeReader()
    reader.SetBarCodeReadType(DecodeType.Code39, DecodeType.Code128)
    reader.SetBarCodeImage("c:\test.png")
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode Type: " + result.CodeTypeName)
        Console.WriteLine("BarCode CodeText: " + result.CodeText)
    Next
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_Aspose_Drawing_Bitmap_"></a> BarCodeReader\(Bitmap\)

```csharp
public BarCodeReader(Bitmap image)
```

#### Parameters

`image` Bitmap

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_Aspose_Drawing_Bitmap_Aspose_BarCode_BarCodeRecognition_BaseDecodeType___"></a> BarCodeReader\(Bitmap, params BaseDecodeType\[\]\)

```csharp
public BarCodeReader(Bitmap image, params BaseDecodeType[] decodeTypes)
```

#### Parameters

`image` Bitmap

`decodeTypes` [BaseDecodeType](/barcode/aspose.barcode.barcoderecognition.basedecodetype)\[\]

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_Aspose_Drawing_Bitmap_Aspose_BarCode_BarCodeRecognition_BaseDecodeType_"></a> BarCodeReader\(Bitmap, BaseDecodeType\)

```csharp
public BarCodeReader(Bitmap image, BaseDecodeType type)
```

#### Parameters

`image` Bitmap

`type` [BaseDecodeType](/barcode/aspose.barcode.barcoderecognition.basedecodetype)

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_Aspose_Drawing_Bitmap_Aspose_Drawing_Rectangle_Aspose_BarCode_BarCodeRecognition_BaseDecodeType___"></a> BarCodeReader\(Bitmap, Rectangle, params BaseDecodeType\[\]\)

```csharp
public BarCodeReader(Bitmap image, Rectangle area, params BaseDecodeType[] decodeTypes)
```

#### Parameters

`image` Bitmap

`area` Rectangle

`decodeTypes` [BaseDecodeType](/barcode/aspose.barcode.barcoderecognition.basedecodetype)\[\]

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_Aspose_Drawing_Bitmap_Aspose_Drawing_Rectangle_Aspose_BarCode_BarCodeRecognition_BaseDecodeType_"></a> BarCodeReader\(Bitmap, Rectangle, BaseDecodeType\)

```csharp
public BarCodeReader(Bitmap image, Rectangle area, BaseDecodeType type)
```

#### Parameters

`image` Bitmap

`area` Rectangle

`type` [BaseDecodeType](/barcode/aspose.barcode.barcoderecognition.basedecodetype)

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_Aspose_Drawing_Bitmap_Aspose_Drawing_Rectangle___Aspose_BarCode_BarCodeRecognition_BaseDecodeType___"></a> BarCodeReader\(Bitmap, Rectangle\[\], params BaseDecodeType\[\]\)

```csharp
public BarCodeReader(Bitmap image, Rectangle[] areas, params BaseDecodeType[] decodeTypes)
```

#### Parameters

`image` Bitmap

`areas` Rectangle\[\]

`decodeTypes` [BaseDecodeType](/barcode/aspose.barcode.barcoderecognition.basedecodetype)\[\]

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_Aspose_Drawing_Bitmap_Aspose_Drawing_Rectangle___Aspose_BarCode_BarCodeRecognition_BaseDecodeType_"></a> BarCodeReader\(Bitmap, Rectangle\[\], BaseDecodeType\)

```csharp
public BarCodeReader(Bitmap image, Rectangle[] areas, BaseDecodeType type)
```

#### Parameters

`image` Bitmap

`areas` Rectangle\[\]

`type` [BaseDecodeType](/barcode/aspose.barcode.barcoderecognition.basedecodetype)

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_System_String_"></a> BarCodeReader\(string\)

Initializes a new instance of the Aspose.BarCode.BarCodeRecognition.BarCodeReader class from file.

```csharp
public BarCodeReader(string filename)
```

#### Parameters

`filename` [string](https://learn.microsoft.com/dotnet/api/system.string)

The filename.

#### Examples

This sample shows how to detect Code39 and Code128 barcodes.

```csharp
using (BarCodeReader reader = new BarCodeReader(@"c:\test.png"))
{
    reader.SetBarCodeReadType(DecodeType.Code39, DecodeType.Code128);
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeTypeName);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
}
Using reader As New BarCodeReader("c:\test.png")
    reader.SetBarCodeReadType(DecodeType.Code39, DecodeType.Code128)
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode Type: " + result.CodeTypeName)
        Console.WriteLine("BarCode CodeText: " + result.CodeText)
    Next
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_System_String_Aspose_BarCode_BarCodeRecognition_BaseDecodeType___"></a> BarCodeReader\(string, params BaseDecodeType\[\]\)

Initializes a new instance of the Aspose.BarCode.BarCodeRecognition.BarCodeReader class.

```csharp
public BarCodeReader(string filename, params BaseDecodeType[] decodeTypes)
```

#### Parameters

`filename` [string](https://learn.microsoft.com/dotnet/api/system.string)

The filename.

`decodeTypes` [BaseDecodeType](/barcode/aspose.barcode.barcoderecognition.basedecodetype)\[\]

Decode types.

#### Examples

This sample shows how to detect Code39 and Code128 barcodes.

```csharp
using (BarCodeReader reader = new BarCodeReader(@"c:\test.png", DecodeType.Code39, DecodeType.Code128))
{
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeTypeName);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
}
Using reader As New BarCodeReader("c:\test.png", DecodeType.Code39, DecodeType.Code128)
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode Type: " + result.CodeTypeName)
        Console.WriteLine("BarCode CodeText: " + result.CodeText)
    Next
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_System_String_Aspose_BarCode_BarCodeRecognition_BaseDecodeType_"></a> BarCodeReader\(string, BaseDecodeType\)

Initializes a new instance of the Aspose.BarCode.BarCodeRecognition.BarCodeReader class.

```csharp
public BarCodeReader(string filename, BaseDecodeType type)
```

#### Parameters

`filename` [string](https://learn.microsoft.com/dotnet/api/system.string)

The filename.

`type` [BaseDecodeType](/barcode/aspose.barcode.barcoderecognition.basedecodetype)

The decode type.

#### Examples

This sample shows how to detect Code39 and Code128 barcodes.

```csharp
using (BarCodeReader reader = new BarCodeReader(@"c:\test.png", new MultiDecodeType(DecodeType.Code39, DecodeType.Code128)))
{
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeTypeName);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
}
Using reader As New BarCodeReader("c:\test.png", New MultiDecodeType(DecodeType.Code39, DecodeType.Code128))
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode Type: " + result.CodeTypeName)
        Console.WriteLine("BarCode CodeText: " + result.CodeText)
    Next
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_System_IO_Stream_"></a> BarCodeReader\(Stream\)

Initializes a new instance of the Aspose.BarCode.BarCodeRecognition.BarCodeReader class.

```csharp
public BarCodeReader(Stream stream)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream.

#### Examples

This sample shows how to detect Code39 and Code128 barcodes.

```csharp
using (FileStream fstr = new FileStream(@"c:\test.png", FileMode.Open))
using (BarCodeReader reader = new BarCodeReader(fstr))
{
    reader.SetBarCodeReadType(DecodeType.Code39, DecodeType.Code128);
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeTypeName);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
}
Using fstr = New FileStream("c:\test.png", FileMode.Open)
    Using reader As New BarCodeReader(fstr)
        reader.SetBarCodeReadType(DecodeType.Code39, DecodeType.Code128)
        For Each result As BarCodeResult In reader.ReadBarCodes()
            Console.WriteLine("BarCode Type: " + result.CodeTypeName)
            Console.WriteLine("BarCode CodeText: " + result.CodeText)
        Next
    End Using
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_System_IO_Stream_Aspose_BarCode_BarCodeRecognition_BaseDecodeType_"></a> BarCodeReader\(Stream, BaseDecodeType\)

Initializes a new instance of the Aspose.BarCode.BarCodeRecognition.BarCodeReader class.

```csharp
public BarCodeReader(Stream stream, BaseDecodeType type)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream.

`type` [BaseDecodeType](/barcode/aspose.barcode.barcoderecognition.basedecodetype)

The decode type.

#### Examples

This sample shows how to detect Code39 and Code128 barcodes.

```csharp
using (FileStream fstr = new FileStream(@"c:\test.png", FileMode.Open))
using (BarCodeReader reader = new BarCodeReader(fstr, new MultiDecodeType(DecodeType.Code39, DecodeType.Code128)))
{
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeTypeName);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
}
Using fstr = New FileStream("c:\test.png", FileMode.Open)
    Using reader As New BarCodeReader(fstr, New MultiDecodeType(DecodeType.Code39, DecodeType.Code128))
        For Each result As BarCodeResult In reader.ReadBarCodes()
            Console.WriteLine("BarCode Type: " + result.CodeTypeName)
            Console.WriteLine("BarCode CodeText: " + result.CodeText)
        Next
    End Using
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader__ctor_System_IO_Stream_Aspose_BarCode_BarCodeRecognition_BaseDecodeType___"></a> BarCodeReader\(Stream, params BaseDecodeType\[\]\)

Initializes a new instance of the Aspose.BarCode.BarCodeRecognition.BarCodeReader class.

```csharp
public BarCodeReader(Stream stream, params BaseDecodeType[] decodeTypes)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The stream.

`decodeTypes` [BaseDecodeType](/barcode/aspose.barcode.barcoderecognition.basedecodetype)\[\]

Decode types.

#### Examples

This sample shows how to detect Code39 and Code128 barcodes.

```csharp
using (FileStream fstr = new FileStream(@"c:\test.png", FileMode.Open))
using (BarCodeReader reader = new BarCodeReader(fstr, DecodeType.Code39, DecodeType.Code128))
{
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeTypeName);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
}
Using fstr = New FileStream("c:\test.png", FileMode.Open)
    Using reader As New BarCodeReader(fstr, DecodeType.Code39, DecodeType.Code128)
        For Each result As BarCodeResult In reader.ReadBarCodes()
            Console.WriteLine("BarCode Type: " + result.CodeTypeName)
            Console.WriteLine("BarCode CodeText: " + result.CodeText)
        Next
    End Using
End Using
```

## Properties

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_BarCodeReadType"></a> BarCodeReadType

Gets or sets the barcode decode type used for recognition.
Must be set before calling Aspose.BarCode.BarCodeRecognition.BarCodeReader.ReadBarCodes.

```csharp
[XmlSerialization(Type = XmlSerializationType.Element)]
public BaseDecodeType BarCodeReadType { get; set; }
```

#### Property Value

 [BaseDecodeType](/barcode/aspose.barcode.barcoderecognition.basedecodetype)

#### Examples

This sample shows how to detect Code39 and Code128 barcodes.

```csharp
using (BarCodeReader reader = new BarCodeReader())
{
    reader.BarCodeReadType = new MultiDecodeType(DecodeType.Code39, DecodeType.Code128);
    reader.SetBarCodeImage(@"c:\test.png");
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeTypeName);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
    Console.WriteLine("BarCodeReadType: " + reader.BarCodeReadType.ToString());
}
Using reader As New BarCodeReader()
    reader.BarCodeReadType = New MultiDecodeType(DecodeType.Code39, DecodeType.Code128)
    reader.SetBarCodeImage("c:\test.png")
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode Type: " + result.CodeTypeName)
        Console.WriteLine("BarCode CodeText: " + result.CodeText)
    Next
    Console.WriteLine("BarCodeReadType: " + reader.BarCodeReadType.ToString())
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_BarcodeSettings"></a> BarcodeSettings

The main BarCode decoding parameters. Contains parameters which make influence on recognized data.

```csharp
[XmlSerialization(Type = XmlSerializationType.Element)]
public BarcodeSettings BarcodeSettings { get; }
```

#### Property Value

 [BarcodeSettings](/barcode/aspose.barcode.barcoderecognition.barcodesettings)

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_FoundBarCodes"></a> FoundBarCodes

Gets recognized Aspose.BarCode.BarCodeRecognition.BarCodeResults array

```csharp
public BarCodeResult[] FoundBarCodes { get; }
```

#### Property Value

 [BarCodeResult](/barcode/aspose.barcode.barcoderecognition.barcoderesult)\[\]

#### Examples

This sample shows how to read barcodes with BarCodeReader

```csharp
using (BarCodeReader reader = new BarCodeReader(@"c:\test.png", DecodeType.Code39, DecodeType.Code128))
{
    reader.ReadBarCodes();
    for(int i = 0; reader.FoundCount > i; ++i)
        Console.WriteLine("BarCode CodeText: " + reader.FoundBarCodes[i].CodeText);
}
Using reader As New BarCodeReader("c:\test.png", DecodeType.Code39, DecodeType.Code128)
    reader.ReadBarCodes()
    For i As Integer = 0 To reader.FoundCount - 1 Step 1
        Console.WriteLine("BarCode CodeText: " + reader.FoundBarCodes(i).CodeText)
    Next
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_FoundCount"></a> FoundCount

Gets recognized barcodes count

```csharp
public int FoundCount { get; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Examples

This sample shows how to read barcodes with BarCodeReader

```csharp
using (BarCodeReader reader = new BarCodeReader(@"c:\test.png", DecodeType.Code39, DecodeType.Code128))
{
    reader.ReadBarCodes();
    for(int i = 0; reader.FoundCount > i; ++i)
        Console.WriteLine("BarCode CodeText: " + reader.FoundBarCodes[i].CodeText);
}
Using reader As New BarCodeReader("c:\test.png", DecodeType.Code39, DecodeType.Code128)
    reader.ReadBarCodes()
    For i As Integer = 0 To reader.FoundCount - 1 Step 1
        Console.WriteLine("BarCode CodeText: " + reader.FoundBarCodes(i).CodeText)
    Next
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_ProcessorSettings"></a> ProcessorSettings

Gets a settings of using processor cores.

```csharp
public static ProcessorSettings ProcessorSettings { get; }
```

#### Property Value

 [ProcessorSettings](/barcode/aspose.barcode.common.processorsettings)

#### Examples

This sample shows how to use ProcessorSettings to add maximum multi-threaded performnce

```csharp
//this allows to use all cores for single BarCodeReader call
BarCodeReader.ProcessorSettings.UseAllCores = true;
//this allows to use current count of cores
BarCodeReader.ProcessorSettings.UseAllCores = false;
BarCodeReader.ProcessorSettings.UseOnlyThisCoresCount = Math.Max(1, Environment.ProcessorCount / 2);
'this allows to use all cores for single BarCodeReader call
BarCodeReader.ProcessorSettings.UseAllCores = True
'this allows to use current count of cores
BarCodeReader.ProcessorSettings.UseAllCores = False
BarCodeReader.ProcessorSettings.UseOnlyThisCoresCount = Math.Max(1, Environment.ProcessorCount / 2)
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_QualitySettings"></a> QualitySettings

QualitySettings allows to configure recognition quality and speed manually.
You can quickly set up QualitySettings by embedded presets: HighPerformance, NormalQuality,
HighQuality, MaxBarCodes or you can manually configure separate options.
Default value of QualitySettings is NormalQuality.

```csharp
[XmlSerialization(Type = XmlSerializationType.Element)]
public QualitySettings QualitySettings { get; set; }
```

#### Property Value

 [QualitySettings](/barcode/aspose.barcode.barcoderecognition.qualitysettings)

#### Examples

This sample shows how to use QualitySettings with BarCodeReader

```csharp
using (BarCodeReader reader = new BarCodeReader(@"c:\test.png", DecodeType.Code39, DecodeType.Code128))
{
   //set high performance mode
   reader.QualitySettings = QualitySettings.HighPerformance;
   foreach (BarCodeResult result in reader.ReadBarCodes())
      Console.WriteLine("BarCode CodeText: " + result.CodeText);
}
using (BarCodeReader reader = new BarCodeReader(@"c:\test.png", DecodeType.Code39, DecodeType.Code128))
{
   //normal quality mode is set by default
   foreach (BarCodeResult result in reader.ReadBarCodes())
      Console.WriteLine("BarCode CodeText: " + result.CodeText);
}
using (BarCodeReader reader = new BarCodeReader(@"c:\test.png", DecodeType.Code39, DecodeType.Code128))
{
   //set high performance mode
   reader.QualitySettings = QualitySettings.HighPerformance;
   //set separate options
   reader.QualitySettings.AllowMedianSmoothing = true;
   reader.QualitySettings.MedianSmoothingWindowSize = 5;
   foreach (BarCodeResult result in reader.ReadBarCodes())
      Console.WriteLine("BarCode CodeText: " + result.CodeText);
}
Using reader As New BarCodeReader("c:\test.png", DecodeType.Code39, DecodeType.Code128)
    'set high performance mode
    reader.QualitySettings = QualitySettings.HighPerformance
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode Type: " + result.CodeTypeName)
    Next
End Using
Using reader As New BarCodeReader("c:\test.png", DecodeType.Code39, DecodeType.Code128)
    'normal quality mode is set by default
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode Type: " + result.CodeTypeName)
    Next
End Using
Using reader As New BarCodeReader("c:\test.png", DecodeType.Code39, DecodeType.Code128)
   'set high performance mode
   reader.QualitySettings = QualitySettings.HighPerformance
   'set separate options
   reader.QualitySettings.AllowMedianSmoothing = True
   reader.QualitySettings.MedianSmoothingWindowSize = 5
   For Each result As BarCodeResult In reader.ReadBarCodes()
       Console.WriteLine("BarCode Type: " + result.CodeTypeName)
   Next
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_Timeout"></a> Timeout

Gets or sets the timeout of recognition process in milliseconds.

```csharp
[XmlSerialization(Type = XmlSerializationType.Element)]
public int Timeout { get; set; }
```

#### Property Value

 [int](https://learn.microsoft.com/dotnet/api/system.int32)

#### Examples

This sample shows how to avoid recogntion hungs with timeount on large images

```csharp
using (BarCodeReader reader = new BarCodeReader(@"c:\test.png"))
{
    reader.Timeout = 5000;
    foreach (BarCodeResult result in reader.ReadBarCodes())
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
}
Using reader As New BarCodeReader("c:\test.png")
    reader.Timeout = 5000
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode CodeText: " + result.CodeText)
    Next
End Using
```

## Methods

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_Abort"></a> Abort\(\)

Function requests termination of current recognition session from other thread. Abort is unblockable method and returns control just after calling.
The method should be used when recognition process is too long.

```csharp
public void Abort()
```

#### Examples

This sample shows how to call Abort function from other thread

```csharp
private static void ThreadRecognize(object readerObj)
{
    BarCodeReader reader = (BarCodeReader)readerObj;
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeType);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
}

BarCodeReader reader = new BarCodeReader(@"c:\test.png", DecodeType.Code39, DecodeType.Code128);
Thread thread1 = new Thread(ThreadRecognize);
thread1.Start(reader);
Thread.Sleep(100);
reader.Abort();
Private Shared Sub ThreadRecognize(readerObj As Object)
    Dim reader As BarCodeReader = readerObj
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode Type: " + result.CodeTypeName)
        Console.WriteLine("BarCode CodeText: " + result.CodeText)
    Next
End Sub

Dim reader As New BarCodeReader("c:\test.png", DecodeType.Code39, DecodeType.Code128)
Dim thread1 As New Thread(AddressOf ThreadRecognize)
thread1.Start(reader)
Thread.Sleep(100)
reader.Abort()
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_Dispose"></a> Dispose\(\)

```csharp
public void Dispose()
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_ExportToXml_System_String_"></a> ExportToXml\(string\)

Exports BarCode properties to the xml-file specified

```csharp
public bool ExportToXml(string xmlFile)
```

#### Parameters

`xmlFile` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name for the file

#### Returns

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether or not export completed successfully.
            <p>Returns <b>True</b> in case of success; <b>False</b> Otherwise </p>

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_ExportToXml_System_IO_Stream_"></a> ExportToXml\(Stream\)

Exports BarCode properties to the xml-stream specified

```csharp
public bool ExportToXml(Stream xmlStream)
```

#### Parameters

`xmlStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The xml-stream for saving

#### Returns

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

Whether or not export completed successfully.
            <p>Returns <b>True</b> in case of success; <b>False</b> Otherwise </p>

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_ImportFromXml_System_String_"></a> ImportFromXml\(string\)

Imports BarCode properties from the xml-file specified and applies them to the current BarCodeReader instance.

```csharp
public static BarCodeReader ImportFromXml(string xmlFile)
```

#### Parameters

`xmlFile` [string](https://learn.microsoft.com/dotnet/api/system.string)

The name for the file

#### Returns

 [BarCodeReader](/barcode/aspose.barcode.barcoderecognition.barcodereader)

Returns <b>True</b> in case of success; <p><b>False</b> Otherwise </p>

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_ImportFromXml_System_IO_Stream_"></a> ImportFromXml\(Stream\)

Imports BarCode properties from the xml-stream specified and applies them to the current BarCodeReader instance.

```csharp
public static BarCodeReader ImportFromXml(Stream xmlStream)
```

#### Parameters

`xmlStream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The xml-stream for loading

#### Returns

 [BarCodeReader](/barcode/aspose.barcode.barcoderecognition.barcodereader)

Returns <b>True</b> in case of success; <p><b>False</b> Otherwise </p>

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_ReadBarCodes"></a> ReadBarCodes\(\)

Reads Aspose.BarCode.BarCodeRecognition.BarCodeResults from the image.

```csharp
public BarCodeResult[] ReadBarCodes()
```

#### Returns

 [BarCodeResult](/barcode/aspose.barcode.barcoderecognition.barcoderesult)\[\]

Returns array of recognized Aspose.BarCode.BarCodeRecognition.BarCodeResults on the image. If nothing is recognized, zero array is returned.

#### Examples

This sample shows how to read barcodes with BarCodeReader

```csharp
using (BarCodeReader reader = new BarCodeReader(@"c:\test.png", DecodeType.Code39, DecodeType.Code128))
{
    foreach (BarCodeResult result in reader.ReadBarCodes())
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
}
using (BarCodeReader reader = new BarCodeReader(@"c:\test.png", DecodeType.Code39, DecodeType.Code128))
{
    reader.ReadBarCodes();
    for(int i = 0; reader.FoundCount > i; ++i)
        Console.WriteLine("BarCode CodeText: " + reader.FoundBarCodes[i].CodeText);
}
Using reader As New BarCodeReader("c:\test.png", DecodeType.Code39, DecodeType.Code128)
    reader.ReadBarCodes()
    For i As Integer = 0 To reader.FoundCount - 1 Step 1
        Console.WriteLine("BarCode CodeText: " + reader.FoundBarCodes(i).CodeText)
    Next
End Using

Using reader As New BarCodeReader("c:\test.png", DecodeType.Code39, DecodeType.Code128)
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode CodeText: " + result.CodeText)
    Next
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_SetBarCodeImage_Aspose_Drawing_Bitmap_"></a> SetBarCodeImage\(Bitmap\)

```csharp
public void SetBarCodeImage(Bitmap value)
```

#### Parameters

`value` Bitmap

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_SetBarCodeImage_Aspose_Drawing_Bitmap_Aspose_Drawing_Rectangle___"></a> SetBarCodeImage\(Bitmap, Rectangle\[\]\)

```csharp
public void SetBarCodeImage(Bitmap value, Rectangle[] areas)
```

#### Parameters

`value` Bitmap

`areas` Rectangle\[\]

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_SetBarCodeImage_Aspose_Drawing_Bitmap_Aspose_Drawing_Rectangle_"></a> SetBarCodeImage\(Bitmap, Rectangle\)

```csharp
public void SetBarCodeImage(Bitmap value, Rectangle area)
```

#### Parameters

`value` Bitmap

`area` Rectangle

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_SetBarCodeImage_System_String_"></a> SetBarCodeImage\(string\)

Sets image file for recognition.
Must be called before ReadBarCodes() method.

```csharp
public void SetBarCodeImage(string filename)
```

#### Parameters

`filename` [string](https://learn.microsoft.com/dotnet/api/system.string)

The image file for recogniton.

#### Examples

This sample shows how to detect Code39 and Code128 barcodes.

```csharp
using (BarCodeReader reader = new BarCodeReader())
{
    reader.SetBarCodeReadType(DecodeType.Code39, DecodeType.Code128);
    reader.SetBarCodeImage(@"c:\test.png");
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeTypeName);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
}
Using reader As New BarCodeReader()
    reader.SetBarCodeReadType(DecodeType.Code39, DecodeType.Code128)
    reader.SetBarCodeImage("c:\test.png")
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode Type: " + result.CodeTypeName)
        Console.WriteLine("BarCode CodeText: " + result.CodeText)
    Next
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_SetBarCodeImage_System_IO_Stream_"></a> SetBarCodeImage\(Stream\)

Sets image stream for recognition.
Must be called before ReadBarCodes() method.

```csharp
public void SetBarCodeImage(Stream stream)
```

#### Parameters

`stream` [Stream](https://learn.microsoft.com/dotnet/api/system.io.stream)

The image stream for recogniton.

#### Examples

This sample shows how to detect Code39 and Code128 barcodes.

```csharp
using (FileStream fstr = new FileStream(@"c:\test.png", FileMode.Open))
using (BarCodeReader reader = new BarCodeReader())
{
    reader.SetBarCodeReadType(DecodeType.Code39, DecodeType.Code128);
    reader.SetBarCodeImage(fstr);
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeTypeName);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
}
Using fstr = New FileStream("c:\test.png", FileMode.Open)
    Using reader As New BarCodeReader()
        reader.SetBarCodeReadType(DecodeType.Code39, DecodeType.Code128)
        reader.SetBarCodeImage(fstr)
        For Each result As BarCodeResult In reader.ReadBarCodes()
            Console.WriteLine("BarCode Type: " + result.CodeTypeName)
            Console.WriteLine("BarCode CodeText: " + result.CodeText)
        Next
    End Using
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_SetBarCodeReadType_Aspose_BarCode_BarCodeRecognition_SingleDecodeType___"></a> SetBarCodeReadType\(params SingleDecodeType\[\]\)

Sets Aspose.BarCode.BarCodeRecognition.SingleDecodeType type array for recognition.
Must be called before ReadBarCodes() method.

```csharp
public void SetBarCodeReadType(params SingleDecodeType[] barcodeTypes)
```

#### Parameters

`barcodeTypes` [SingleDecodeType](/barcode/aspose.barcode.barcoderecognition.singledecodetype)\[\]

The Aspose.BarCode.BarCodeRecognition.SingleDecodeType type array to read.

#### Examples

This sample shows how to detect Code39 and Code128 barcodes.

```csharp
using (BarCodeReader reader = new BarCodeReader())
{
    reader.SetBarCodeReadType(DecodeType.Code39, DecodeType.Code128);
    reader.SetBarCodeImage(@"c:\test.png");
    foreach (BarCodeResult result in reader.ReadBarCodes())
    {
        Console.WriteLine("BarCode Type: " + result.CodeTypeName);
        Console.WriteLine("BarCode CodeText: " + result.CodeText);
    }
}
Using reader As New BarCodeReader()
    reader.SetBarCodeReadType(DecodeType.Code39, DecodeType.Code128)
    reader.SetBarCodeImage("c:\test.png")
    For Each result As BarCodeResult In reader.ReadBarCodes()
        Console.WriteLine("BarCode Type: " + result.CodeTypeName)
        Console.WriteLine("BarCode CodeText: " + result.CodeText)
    Next
End Using
```

### <a id="Aspose_BarCode_BarCodeRecognition_BarCodeReader_SetBarCodeReadType_Aspose_BarCode_BarCodeRecognition_BaseDecodeType_"></a> SetBarCodeReadType\(BaseDecodeType\)

Sets decode type for recognition.
Deprecated. Use Aspose.BarCode.BarCodeRecognition.BarCodeReader.BarCodeReadType property instead.

```csharp
[Obsolete("SetBarCodeReadType is deprecated. Use the BarCodeReadType property instead.", false)]
public void SetBarCodeReadType(BaseDecodeType type)
```

#### Parameters

`type` [BaseDecodeType](/barcode/aspose.barcode.barcoderecognition.basedecodetype)

The type of barcode to read.
