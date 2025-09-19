# PDF to Text Libraries

## marker

```bash
uv init
uv add marker-pdf
uv run marker_single \
    --output_format markdown \
    --paginate_output \
    --use_llm \
    --disable_image_extraction \
    --llm_service marker.services.openai.OpenAIService \
    --openai_base_url your-base-url \
    --openai_api_key your-api-key \
    --openai_model gpt-5 \
    ./myfile.pdf
```

## poppler

```bash
sudo apt update && apt install poppler-utils
pdftotext -enc UTF-8 -eol unix -nopgbrk -layout input.pdf output.txt
```
