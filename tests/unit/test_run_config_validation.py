"""Tests for canonical_import validation in run_config (P7A-01 G-01)."""

import pytest
from pathlib import Path

from launcher.io.run_config import _validate_canonical_import, ConfigError


class TestCanonicalImportValidation:
    """Tests for _validate_canonical_import() — Python platform-specific validation."""

    def test_dotted_import_for_python_raises_config_error(self, tmp_path):
        """canonical_import with dots (e.g. 'aspose.cells') raises ConfigError for python."""
        data = {"canonical_import": "aspose.cells", "family": "cells", "platform": "python"}
        with pytest.raises(ConfigError, match="canonical_import"):
            _validate_canonical_import(data, tmp_path)

    def test_correct_underscored_import_for_python_passes(self, tmp_path):
        """canonical_import matching 'aspose_{family}_foss' pattern passes for python."""
        data = {
            "canonical_import": "aspose_cells_foss",
            "family": "cells",
            "platform": "python",
        }
        _validate_canonical_import(data, tmp_path)  # should not raise

    def test_java_canonical_import_always_passes(self, tmp_path):
        """For platform=java, canonical_import is not validated (any format passes)."""
        data = {
            "canonical_import": "com.aspose.cells",
            "family": "cells",
            "platform": "java",
        }
        _validate_canonical_import(data, tmp_path)  # should not raise

    def test_no_canonical_import_passes(self, tmp_path):
        """When canonical_import is absent, validation is skipped."""
        data = {"family": "cells", "platform": "python"}
        _validate_canonical_import(data, tmp_path)  # should not raise

    def test_no_platform_passes(self, tmp_path):
        """When platform is absent, validation is skipped regardless of canonical_import."""
        data = {"canonical_import": "aspose.cells", "family": "cells"}
        _validate_canonical_import(data, tmp_path)  # should not raise (platform not set)
