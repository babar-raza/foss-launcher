"""Basic usage example for aspose-cells-foss."""
from aspose.cells import Workbook

wb = Workbook()
wb.load("input.xlsx")
ws = wb.get_worksheet(0)
ws.set_value("A1", "Hello, World!")
wb.save("output.xlsx")
