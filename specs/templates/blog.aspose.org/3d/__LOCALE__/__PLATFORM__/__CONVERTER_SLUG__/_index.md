---
# Template: V2 converter landing page (platform-aware, layout: "plugin")
# Source pattern: content/products.aspose.org/{family}/{locale}/{platform}/{converter}/_index.md
# Placeholders: __TOKEN__ (replace entire token; booleans -> true/false)
layout: "plugin"
cart_id: "__CART_ID__"

plugin_name: "__PLUGIN_NAME__"
plugin_description: "__PLUGIN_DESCRIPTION__"
plugin_platform: "__PLUGIN_PLATFORM__"

# Head
head_title: "__HEAD_TITLE__"
head_description: "__HEAD_DESCRIPTION__"

# Header
title: "__PAGE_TITLE__"
description: "__PAGE_DESCRIPTION__"

# SubMenu
submenu:
  enable: __SUBMENU_ENABLE__

# Overview
overview:
  enable: __OVERVIEW_ENABLE__
  title: "__OVERVIEW_TITLE__"
  content: |
    __OVERVIEW_CONTENT__

# Content
body:
  enable: __BODY_ENABLE__
  block:
    - title_left: "__BODY_BLOCK_TITLE_LEFT__"
      content_left: |
        __BODY_BLOCK_CONTENT_LEFT__
      title_right: "__BODY_BLOCK_TITLE_RIGHT__"
      content_right: |
        __BODY_BLOCK_CONTENT_RIGHT__
      gisthash: "__BODY_BLOCK_GIST_HASH__"
      gistfile: "__BODY_BLOCK_GIST_FILE__"
    # Repeat block entries as needed.

# FAQs
faq:
  enable: __FAQ_ENABLE__
  list:
    - question: "__FAQ_QUESTION__"
      answer: "__FAQ_ANSWER__"
    # Repeat FAQ items as needed.

# More Formats
more_formats:
  enable: __MORE_FORMATS_ENABLE__

# Support and Learning
supportandlearning:
  enable: __SUPPORT_AND_LEARNING_ENABLE__

# Back to top
back_to_top:
  enable: __BACK_TO_TOP_ENABLE__
---
