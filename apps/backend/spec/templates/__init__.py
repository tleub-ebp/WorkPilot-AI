"""
Spec Templates Library
======================

Reusable spec templates for common development patterns.
Accelerates task creation by pre-filling requirements, files, and QA criteria.
"""

from .library import TemplateLibrary
from .models import SpecTemplate, TemplateCategory

__all__ = ["SpecTemplate", "TemplateCategory", "TemplateLibrary"]
