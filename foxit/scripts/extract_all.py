"""Extract from ALL CUAD PDFs with Nutrient — runs in background."""
import httpx, json, os, time

EXTRACTION_KEY = os.environ.get('NUTRIENT_API_KEY', '')
PDF_DIR = "proofdesk/data/datasets/pdfs"
OUTPUT = "/tmp/proofdesk/nutrient_extraction"
os.makedirs(OUTPUT, exist_ok=True)

pdfs = sorted([f for f in os.listdir(PDF_DIR) if f.endswith('.pdf')])
print(f"Found {len(pdfs)} PDFs", flush=True)

all_results = []
errors = 0

for i, pdf_name in enumerate(pdfs):
    pdf_path = f"{PDF_DIR}/{pdf_name}"
    
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    try:
        response = httpx.post(
            "https://api.nutrient.io/extraction/parse",
            headers={"Authorization": f"Bearer {EXTRACTION_KEY}"},
            files={"file": (pdf_name, pdf_bytes, "application/pdf")},
            data={"instructions": json.dumps({"mode": "structure", "output": {"format": "spatial"}})},
            timeout=60.0,
        )
        
        if response.status_code == 200:
            result = response.json()
            elements = result.get('output', {}).get('elements', [])
            
            confidences = [e.get('confidence', 0) for e in elements if 'confidence' in e]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            min_conf = min(confidences) if confidences else 0
            max_conf = max(confidences) if confidences else 0
            
            all_results.append({
                'pdf_name': pdf_name,
                'field_count': len(elements),
                'avg_confidence': avg_conf,
                'min_confidence': min_conf,
                'max_confidence': max_conf,
                'text_length': sum(len(e.get('text', '')) for e in elements),
            })
        else:
            errors += 1
    except Exception as e:
        errors += 1
    
    # Save progress every 50 docs
    if (i + 1) % 50 == 0:
        with open(f"{OUTPUT}/cuad_progress.json", 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"  Progress: {i+1}/{len(pdfs)} extracted, {errors} errors", flush=True)
    
    time.sleep(0.3)  # Rate limiting

# Final save
with open(f"{OUTPUT}/cuad_extraction.json", 'w') as f:
    json.dump(all_results, f, indent=2)

print(f"\nDone: {len(all_results)} extracted, {errors} errors")
print(f"Avg confidence: {sum(r['avg_confidence'] for r in all_results)/len(all_results):.3f}")
