---
canonical: https://reference.aspose.org/cells/python/chart/
canonical_import: aspose.cells_foss
date: '2026-03-19T15:07:33Z'
dateModified: '2026-03-19T15:07:33Z'
datePublished: '2026-03-19T15:07:33Z'
description: 'Aspose.Cells FOSS: Cells.cell(): Accesses a cell by row and column (1-based).'
display_name: Aspose.Cells FOSS
family: cells
keywords:
- chart
- worksheet
- adds
- spreadsheets
lastmod: '2026-03-19T15:07:33Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: 'Aspose.Cells FOSS Chart: Represents a chart in a worksheet'
slug: chart
title: 'Chart: Represents a chart in a worksheet'
type: reference_object_page
url: /reference.aspose.org/cells/python/chart/
weight: 3
---

## Overview

Represents a chart in a worksheet.

## Properties

| Name | Type | Read-only | Description |
| --- | --- | --- | --- |
| type |  | Yes |  |
| title |  | No |  |
| category_data |  | No |  |
| show_legend |  | No |  |
| legend_position |  | No |  |
| smooth |  | No |  |
| n_series |  | Yes |  |
| NSeries |  | Yes | PascalCase alias of n_series. |
| grouping |  | No |  |
| bar_direction |  | No |  |
| gap_width |  | No |  |
| overlap |  | No |  |
| vary_colors |  | No |  |
| first_slice_angle |  | No |  |
| is_of_pie |  | No |  |
| of_pie_type |  | No |  |
| second_pie_size |  | No |  |
| quartile_method |  | No |  |
| box_show_mean_line |  | No |  |
| box_show_mean_marker |  | No |  |
| box_show_inner_points |  | No |  |
| box_show_outlier_points |  | No |  |
| box_gap_width |  | No |  |
| is_3d |  | No |  |
| gap_depth |  | No |  |
| view_3d |  | Yes |  |
| View3D |  | Yes | PascalCase alias of view_3d. |
| show_connector_lines |  | No |  |
| has_subtotals |  | No |  |
| sub_charts |  | Yes | List of sub-chart descriptors for combo charts. |
| axes |  | Yes | List of ChartAxis objects defining all axes for the chart. |
| scatter_style |  | No |  |
| wireframe |  | No | Whether the surface chart uses wireframe display mode (<c:wireframe val='1'/>). |
| radar_style |  | No | Radar chart style: 'standard', 'marker', or 'filled'. |
| histogram_bin_count |  | No | Number of bins for count-based binning (int or None for auto/size-based). |
| histogram_bin_size |  | No | Bin width for size-based binning (float or None for auto/count-based). |
| histogram_interval_closed |  | No | Which side of each bin interval is closed: 'r' (right) or 'l' (left). |
| histogram_overflow |  | No | Overflow bin boundary value (float or None). |
| histogram_underflow |  | No | Underflow bin boundary value (float or None). |
| disp_blanks_as |  | No |  |
| stock_style |  | No |  |

## Methods

**add_series**(values, category_data, name, chart_type, x_values)

Convenience method to add a series.

**add_axis**(axis_type, axis_id) → ChartAxis

Adds an axis to the chart and returns it.

**copy**()

## See Also

- [Aspose.Cells FOSS API reference](/reference.aspose.org/cells/python/api-overview/)
- [Workbook class overview](/blog.aspose.org/cells/python/introducing-cells-foss-python/)
- [Hyperlink support details](/blog.aspose.org/cells/python/testcreateallcharts-spreadsheets/)
- [Formula handling guide](/docs.aspose.org/cells/python/developer-guide/formula-calculation/)
- [Spreadsheet operations](/docs.aspose.org/cells/python/developer-guide/spreadsheet-operations/)
