# Third-party software and models

pii-mask is MIT licensed. It builds on these projects, each under its own licence. Nothing below
is bundled in this repository; the install steps download them.

| Component | Use here | Licence | Source |
|---|---|---|---|
| Presidio (presidio-analyzer, presidio-anonymizer) 2.2.366 | Recognizer framework, context scoring | MIT | https://github.com/data-privacy-stack/presidio |
| GLiNER 0.2.30 | Zero-shot detection of names, organisations, addresses | Apache-2.0 | https://github.com/urchade/GLiNER |
| urchade/gliner_multi-v2.1 | Multilingual GLiNER checkpoint (default, model 1) | Apache-2.0 | https://huggingface.co/urchade/gliner_multi-v2.1 |
| knowledgator/gliner-pii-base-v1.0 | PII GLiNER checkpoint (default, model 2) | Apache-2.0 | https://huggingface.co/knowledgator/gliner-pii-base-v1.0 |
| urchade/gliner_multi_pii-v1 | Optional checkpoint, compared in tests | Apache-2.0 | https://huggingface.co/urchade/gliner_multi_pii-v1 |
| microsoft/mdeberta-v3-base (tokenizer) | Backbone tokenizer used by the multilingual checkpoint | MIT | https://huggingface.co/microsoft/mdeberta-v3-base |
| Ollama | Optional local LLM runtime for `--llm-check` | MIT | https://github.com/ollama/ollama |
| Qwen3 8B (`qwen3:8b`) | Optional second-pass reviewer | Apache-2.0 | https://huggingface.co/Qwen/Qwen3-8B |
| spaCy 3.8 + en_core_web_sm 3.8.0 | Tokenisation for Presidio | MIT | https://github.com/explosion/spaCy |
| PyTorch 2.11 | Runs GLiNER (CPU or CUDA) | BSD-3-Clause | https://github.com/pytorch/pytorch |
| Hugging Face transformers, huggingface_hub, tokenizers | Model loading | Apache-2.0 | https://github.com/huggingface |
| openpyxl | .xlsx read/write | MIT | https://foss.heptapod.net/openpyxl/openpyxl |
| python-docx | .docx read/write | MIT | https://github.com/python-openxml/python-docx |
| pypdf | PDF text extraction | BSD-3-Clause | https://github.com/py-pdf/pypdf |
| sentencepiece, protobuf | Tokenizer support | Apache-2.0, BSD-3-Clause | https://github.com/google/sentencepiece |
