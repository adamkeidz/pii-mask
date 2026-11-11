import os
import sys

os.environ.setdefault("TORCH_CPP_LOG_LEVEL", "ERROR")
from pii_mask.cli import main  # noqa: E402

sys.exit(main())
