"""Render manuscript pages for visual QA without modifying the PDF."""
from pathlib import Path
import json
import re
import subprocess
from PIL import Image, ImageDraw

paper = Path(__file__).resolve().parent
build = paper / 'build'
pdf = build / 'main.pdf'
text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], encoding='utf-8')
pages = text.split('\f')
if not pages[-1].strip():
    pages.pop()
appendix = next((i + 1 for i, page in enumerate(pages)
                 if re.search(r'支撑材料与复现说明', page)), len(pages) + 1)
selected = sorted(set(range(1, appendix + 1)) | {
    min(appendix + 10, len(pages)), min(appendix + 35, len(pages)), len(pages)})
folder = build / 'visual_qa'
folder.mkdir(exist_ok=True)
images = []
for page in selected:
    prefix = folder / f'page-{page:03d}'
    subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-singlefile',
                    '-scale-to', '1500', '-png', str(pdf), str(prefix)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    images.append(prefix.with_suffix('.png'))
for offset in range(0, len(images), 9):
    contact = Image.new('RGB', (1110, 1620), '#dddddd')
    draw = ImageDraw.Draw(contact)
    for k, file in enumerate(images[offset:offset+9]):
        im = Image.open(file).convert('RGB')
        im.thumbnail((350, 500))
        x, y = (k % 3) * 370 + 10, (k // 3) * 540 + 25
        contact.paste(im, (x, y))
        draw.text((x, y-20), file.stem, fill='black')
    contact.save(folder / f'contact-{offset//9+1}.png')
log = (build / 'main.log').read_text(encoding='utf-8', errors='replace')
report = {
    'pdf_size_bytes': pdf.stat().st_size,
    'total_pages': len(pages),
    'abstract_page_count': 1 if '问题重述与分析' not in pages[0] and '关键词' in pages[0] else None,
    'appendix_starts_page': appendix,
    'main_body_pages_including_references': appendix - 2,
    'rendered_pages': selected,
    'missing_characters': sorted(set(re.findall(r'Missing character:[^\n]*', log))),
    'overfull_boxes': re.findall(r'Overfull [^\n]*', log),
    'undefined_references': 'There were undefined references' in log,
    'placeholder_text': any(token in text[:text.find('支撑材料与复现说明')]
                            for token in ('TODO', '占位', '本文仅讨论问题一')),
}
(folder / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
