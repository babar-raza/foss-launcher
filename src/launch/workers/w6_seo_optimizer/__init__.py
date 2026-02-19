"""W10 SEO Optimizer: Post-processing worker for on-page SEO optimization.

Pipeline position: After W6 (LinkerPatcher), before W7 (Validator).
Modeled after content-generator SEO module patterns.

Phases:
1. Keyword Research -- Google Trends + Suggest + heuristic
2. Keyword Extraction & Injection -- density-controlled natural insertion
3. SEO Metadata -- frontmatter optimization (seoTitle, description, keywords, canonical)
"""

from .worker import execute_seo_optimizer

__all__ = ['execute_seo_optimizer']
