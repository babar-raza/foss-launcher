---
# Template: family landing page (layout: "family")
# Source pattern: content/products.aspose.org/note/{locale}/_index.md
# Placeholders: __TOKEN__ (replace entire token; booleans -> true/false)
# Optional sections: overview, testimonialswrapper, support, back_to_top
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

# Overview
overview:
  enable: __OVERVIEW_ENABLE__
  content: |
    __OVERVIEW_CONTENT__

# Testimonials section
testimonialswrapper:
  enable: __TESTIMONIALS_ENABLE__
  title: "__TESTIMONIALS_TITLE__"
  subtitle: "__TESTIMONIALS_SUBTITLE__"
  caseStudiesLink: "__CASE_STUDIES_LINK__"
  tmessage: "__TESTIMONIAL_MESSAGE__"
  poster: "__TESTIMONIAL_POSTER__"

# Support
support:
  enable: __SUPPORT_ENABLE__

# Back to top
back_to_top:
  enable: __BACK_TO_TOP_ENABLE__
---
