---
# Template: platform root page (layout: "family")
# Source pattern: content/products.aspose.org/3d/{locale}/{platform}/_index.md
# Placeholders: __TOKEN__ (replace entire token; booleans -> true/false)
# This is the V2 platform-aware template for products platform root
layout: "family"
type: "_default"

# Head
head_title: "__HEAD_TITLE__"
head_description: "__HEAD_DESCRIPTION__"

# Header
title: "__PAGE_TITLE__"
description: "__PAGE_DESCRIPTION__"
button:
  enable: __BUTTON_ENABLE__

# Platform-specific configuration
platform: "__PLATFORM__"

# Overview
overview:
  enable: __OVERVIEW_ENABLE__
  content: |
    __OVERVIEW_CONTENT__

# Features section
features:
  enable: __FEATURES_ENABLE__
  title: "__FEATURES_TITLE__"
  items:
    __FEATURES_ITEMS__

# Code examples
code_examples:
  enable: __CODE_EXAMPLES_ENABLE__
  title: "__CODE_EXAMPLES_TITLE__"
  examples:
    __CODE_EXAMPLES__

# Supported formats
formats:
  enable: __FORMATS_ENABLE__
  title: "__FORMATS_TITLE__"
  content: |
    __FORMATS_CONTENT__

# Support
support:
  enable: __SUPPORT_ENABLE__

# Back to top
back_to_top:
  enable: __BACK_TO_TOP_ENABLE__
---
