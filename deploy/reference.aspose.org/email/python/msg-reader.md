---
canonical: https://reference.aspose.org/email/python/msg-reader/
canonical_import: aspose.email_foss
date: '2026-03-19T15:03:00Z'
dateModified: '2026-03-19T15:03:00Z'
datePublished: '2026-03-19T15:03:00Z'
description: 'Aspose.Email FOSS: The MapiMessage class provides high-level APIs for
  creating, reading, editing, and saving Outlook MSG files.'
display_name: Aspose.Email FOSS
family: email
keywords:
- class
- mapimessage
- provides
lastmod: '2026-03-19T15:03:00Z'
page_role: reference_object_page
platform: python
reading_time: 1
robots: index, follow
seoTitle: The library provides low-level MSG parsing capabilities
slug: msg-reader
title: The library provides low-level MSG parsing capabilities through the MsgReader...
type: reference_object_page
url: /reference.aspose.org/email/python/msg-reader/
weight: 3
---

## Overview

Normative top-level MSG containment and stream requirements for container traversal.

## Properties

| Name | Type | Read-only | Description |
| --- | --- | --- | --- |
| cfb_reader | CFBReader | Yes |  |
| storage_layout | StorageLayout | Yes |  |
| strict | bool | Yes |  |
| validation_issues | Tuple[str, ...] | Yes |  |

## Methods

**from_file**(path) → 'MsgReader'

**close**() → None

**iter_top_level_fixed_length_properties**() → Iterator[PropertyEntryFixedLength]

**iter_recipient_storages**() → Iterator[DirectoryEntry]

**iter_attachment_storages**() → Iterator[DirectoryEntry]

**parse_message_property_stream**(storage_stream_id) → Tuple[PropertyStreamHeaderTopLevel, List[PropertyEntryFixedLength]]

Read the property stream in the top level or an embedded-message storage.

**parse_subobject_property_stream**(storage_stream_id) → Tuple[PropertyStreamHeaderSubobject, List[PropertyEntryFixedLength]]

Read the property stream in recipient/attachment storage and decode fixed-length

**parse_top_level_property_stream**(data) → Tuple[PropertyStreamHeaderTopLevel, List[PropertyEntryFixedLength]]

Decode top-level property stream header and fixed-length entries.

**parse_subobject_property_stream_data**(data) → Tuple[PropertyStreamHeaderSubobject, List[PropertyEntryFixedLength]]

Decode recipient/attachment property stream header and fixed-length entries.

## See Also

- [Explore CFB parsing with CFBReader](/reference.aspose.org/email/python/cfb-reader/)
- [Use MapiMessage for high-level operations](/reference.aspose.org/email/python/mapi-message/)
- [Browse the full API reference](/reference.aspose.org/email/python/api-overview/)
- [Learn how to load files](/kb.aspose.org/email/python/load-files-python/)
- [Optimize performance techniques](/kb.aspose.org/email/python/optimize-files/)
