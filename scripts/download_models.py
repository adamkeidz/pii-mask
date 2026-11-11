"""One-time, ONLINE download of the GLiNER checkpoints into ./hf-cache. Masking itself runs offline.
Run it before you block the network:  .venv\\Scripts\\python scripts\\download_models.py [model ...]"""
import os
import sys

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["HF_HOME"] = os.environ.get("PII_MASK_MODELS", os.path.join(TOOL_DIR, "hf-cache"))
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
from gliner import GLiNER  # noqa: E402  (must come after HF_HOME is set)

MODELS = sys.argv[1:] or ["urchade/gliner_multi-v2.1", "knowledgator/gliner-pii-base-v1.0"]
for m in MODELS:
    g = GLiNER.from_pretrained(m)  # also fetches the backbone tokenizer
    g.predict_entities("Demo Person lives at Jalan Demo 1.", ["person", "address"])
    print("ready:", m)
