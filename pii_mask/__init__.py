"""pii-mask: local, reversible masking of Malaysian personal data."""
import os as _os

# Must run before huggingface_hub / transformers are imported: they read these at import time.
_TOOL_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_os.environ.setdefault("PII_MASK_MODELS", _os.path.join(_TOOL_DIR, "hf-cache"))
_os.environ["HF_HOME"] = _os.environ["PII_MASK_MODELS"]
_os.environ["HF_HUB_OFFLINE"] = "1"
_os.environ["TRANSFORMERS_OFFLINE"] = "1"
_os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
_os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
_os.environ["TOKENIZERS_PARALLELISM"] = "false"
_os.environ.setdefault("TORCH_CPP_LOG_LEVEL", "ERROR")

import logging as _logging

_logging.getLogger("torch.distributed.elastic.multiprocessing.redirects").setLevel(_logging.ERROR)

__version__ = "0.1.0"
