import os
import warnings
import argparse
import base64
import gc
import logging

import torch
import glob
from io import BytesIO
from PIL import Image
from pypdf import PdfReader
import re
from tqdm import tqdm
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

from olmocr.data.renderpdf import render_pdf_to_base64png
from olmocr.prompts import build_no_anchoring_v4_yaml_prompt
from olmocr.image_utils import is_jpeg, is_png

os.environ['HF_HOME'] = '/content/drive/MyDrive/hf_cache'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("olmOCR-Colab")

def clean_output(text):
    """
    Rimuove i metadati YAML iniziali e i delimitatori di codice (```) finali.
    """
    # 1. Rimuove il blocco YAML iniziale (--- ... ---)
    parts = re.split(r'^---', text, flags=re.MULTILINE)
    if len(parts) > 2:
        text = "---".join(parts[2:]).strip()
    
    # 2. Rimuove i triple backticks (```) all'inizio o alla fine
    text = text.replace("```markdown", "").replace("```", "")
    
    return text.strip()

def main():
    parser = argparse.ArgumentParser(description="Official-style olmOCR pipeline for Colab")
    
    # Workspace as optional with default
    parser.add_argument("--workspace", default="./workspace", help="Output directory")
    parser.add_argument("--pdfs", required=True, help="Path or glob for PDF/Images")
    parser.add_argument("--target_longest_image_dim", type=int, default=1024)    
    
    args = parser.parse_args()

    # Initialize the model
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        "allenai/olmOCR-2-7B-1025",
        torch_dtype=torch.float16,
        device_map="auto",
        load_in_4bit=True,
        low_cpu_mem_usage=True
    ).eval()
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    os.makedirs(args.workspace, exist_ok=True)

    # File Discovery using glob and official image utils
    all_files = glob.glob(args.pdfs)
    input_files = [f for f in all_files if f.lower().endswith(".pdf") or is_jpeg(f) or is_png(f)]
    
    if not input_files:
        logger.error(f"No valid files found for: {args.pdfs}")
        return

    for doc_path in tqdm(input_files, desc="Total Documents"):
        filename = os.path.basename(doc_path)
        base_name = os.path.splitext(filename)[0]
        is_pdf = doc_path.lower().endswith(".pdf")
        
        # Determine the pages
        pages = range(1, len(PdfReader(doc_path).pages) + 1) if is_pdf else [1]
        doc_markdown_content = []

        # Page-level progress bar
        for page_num in tqdm(pages, desc=f"  📄 {filename[:20]}", leave=False):
            try:
                # Render page 1 to n image
                if is_pdf:
                    image_base64 = render_pdf_to_base64png(doc_path, page_num, target_longest_image_dim=args.target_longest_image_dim)
                else:
                    with Image.open(doc_path) as img:
                        if img.mode != "RGB": img = img.convert("RGB")
                        buffered = BytesIO()
                        img.save(buffered, format="PNG")
                        image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            

                # Build the full prompt
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": build_no_anchoring_v4_yaml_prompt()},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                        ],
                    }
                ]

                # Apply the chat template and processor
                text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                main_image = Image.open(BytesIO(base64.b64decode(image_base64)))

                inputs = processor(
                    text=[text], 
                    images=[main_image], 
                    padding=True, 
                    return_tensors="pt"
                )
                inputs = {key: value.to(device) for (key, value) in inputs.items()}

                # Generate the output
                with torch.no_grad():
                    output = model.generate(
                        **inputs, 
                        temperature=0.1, 
                        max_new_tokens=2048, 
                        do_sample=True
                    )

                # Decode the output
                prompt_length = inputs["input_ids"].shape[1]
                new_tokens = output[:, prompt_length:]
                text_output = processor.tokenizer.batch_decode(new_tokens, skip_special_tokens=True)[0]
                text_output = clean_output(text_output)
                
                # Multipage management in the Markdown file
                page_header = f"## Page {page_num}\n\n" if len(pages) > 1 else ""
                doc_markdown_content.append(f"{page_header}{text_output}")

                # Explicit memory cleanup for Tesla T4 stability
                del inputs, output, main_image, image_base64
                torch.cuda.empty_cache()
                gc.collect()

            except Exception as e:
                logger.error(f"Error on {filename} p.{page_num}: {e}")

        # Final write: all pages into one .md file
        if doc_markdown_content:
            output_path = os.path.join(args.workspace, f"{base_name}.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n\n---\n\n".join(doc_markdown_content))
            logger.info(f"✅ Salvato: {output_path}")

if __name__ == "__main__":
    main()