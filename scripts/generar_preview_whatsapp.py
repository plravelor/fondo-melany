import csv, io, json, math, os, re
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'index.html'
ASSETS = ROOT / 'assets'
ASSETS.mkdir(exist_ok=True, parents=True)

CSV_URL = os.environ.get('SHEET_CSV_URL', '').strip()
META_TOTAL = int(os.environ.get('META_TOTAL', '3000000'))
URL_BASE = os.environ.get('URL_BASE', 'https://plravelor.github.io/fondo-melany/')
SITIO_TITULO = os.environ.get('SITIO_TITULO', 'Apoyemos a Melany')
SITIO_DESCRIPCION = os.environ.get('SITIO_DESCRIPCION', 'Conoce cuánto llevamos recaudado')

def money(n:int)->str:
    return '$' + f"{n:,}".replace(',', '.')

def pct_str(v, total):
    p = (v / total * 100) if total else 0
    s = f"{p:.1f}".replace('.', ',')
    if s.endswith(',0'):
        s = s[:-2]
    return s

def read_recaudado():
    if not CSV_URL:
        raise RuntimeError('No existe la variable SHEET_CSV_URL en Secrets')
    r = requests.get(CSV_URL, timeout=30)
    r.raise_for_status()
    content = r.content.decode('utf-8-sig', errors='replace')
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        concepto = (row.get('Concepto') or row.get('concepto') or '').strip().lower()
        if concepto == 'recaudado':
            raw = str(row.get('Valor') or row.get('valor') or '').strip()
            raw = raw.replace('$','').replace('.','').replace(',','')
            return int(raw)
    raise RuntimeError('No se encontró la fila Concepto=Recaudado en la hoja PUBLICO')

def load_font(size, bold=False):
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/Library/Fonts/Arial Unicode.ttf'
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()

def draw_text(draw, xy, text, font, fill, anchor='la'):
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)

def generate_image(recaudado:int):
    W,H = 1200,630
    img = Image.new('RGB',(W,H),(7,18,20))
    d = ImageDraw.Draw(img)

    # soft panels
    d.rounded_rectangle((30,30,W-30,H-30), radius=30, fill=(9,22,24), outline=(26,59,61), width=2)
    # header tag
    d.rounded_rectangle((55,55,310,95), radius=18, fill=(24,54,56))

    c_green=(83,234,175)
    c_green2=(48,210,146)
    c_text=(236,243,244)
    c_muted=(163,180,181)
    c_panel=(18,33,35)

    font_sm=load_font(20, bold=True)
    font_md=load_font(28, bold=False)
    font_h1=load_font(40, bold=True)
    font_h2=load_font(30, bold=True)
    font_num=load_font(56, bold=True)
    font_num2=load_font(46, bold=True)
    font_bigpct=load_font(40, bold=True)
    font_small=load_font(18, bold=False)

    draw_text(d,(85,75),'FONDO DE MOVILIDAD',font_sm,c_text,'lm')
    draw_text(d,(1090,75),'19–24 oct. 2026',font_md,c_text,'rm')

    draw_text(d,(60,140),'Apoyemos a Melany',font_h1,c_text)
    draw_text(d,(60,192),'en Brasil',font_h1,c_green)

    # Donut
    cx,cy,r = 170,335,92
    d.ellipse((cx-r,cy-r,cx+r,cy+r), outline=(69,87,88), width=18)
    pct = max(0, min(1, recaudado / META_TOTAL if META_TOTAL else 0))
    start = -90
    end = start + 360*pct
    d.arc((cx-r,cy-r,cx+r,cy+r), start=start, end=end, fill=c_green, width=18)
    draw_text(d,(cx,cy-5), pct_str(recaudado,META_TOTAL)+' %', font_bigpct, c_text, 'mm')
    draw_text(d,(cx,cy+35), 'alcanzado', load_font(20,False), c_text, 'mm')

    # amounts
    draw_text(d,(330,250),'RECAUDADO',font_small,c_muted)
    draw_text(d,(330,285),money(recaudado),font_num,c_green)
    draw_text(d,(330,370),f'Meta: {money(META_TOTAL)}',font_h2,c_text)
    faltan=max(META_TOTAL-recaudado,0)
    draw_text(d,(330,420),f'Faltan {money(faltan)}',font_h2,c_muted)

    # progress bar first milestone
    first_goal=500000
    partial=min(recaudado/first_goal if first_goal else 0, 1)
    d.rounded_rectangle((55,500,1145,570), radius=24, fill=c_panel)
    draw_text(d,(80,523),'Primera meta: $500.000',font_small,c_text)
    draw_text(d,(965,523),f'{int(round(partial*100))} % alcanzado',font_small,c_text)
    d.rounded_rectangle((80,545,1120,560), radius=8, fill=(64,74,75))
    d.rounded_rectangle((80,545,80+int((1120-80)*partial),560), radius=8, fill=c_green2)

    return img

def replace_meta_content(html: str, attribute: str, name: str, value: str) -> str:
    """Sustituye solo el atributo content, conservando la etiqueta HTML completa."""
    pattern = rf'(<meta\s+{re.escape(attribute)}="{re.escape(name)}"\s+content=")[^"]*(">)'
    updated, count = re.subn(pattern, lambda m: m.group(1) + value + m.group(2), html, count=1)
    if count != 1:
        raise RuntimeError(f'No se encontró una etiqueta HTML válida: {attribute}={name}. No se modificó index.html.')
    return updated


def update_index(version: str):
    html = INDEX.read_text(encoding='utf-8')
    image_url = f"{URL_BASE}assets/og-portada-auto.png?v={version}"
    public_url = f"{URL_BASE}?v={version}"
    description = f"Hemos recaudado {money(RECAUDADO)} de {money(META_TOTAL)}. Consulta el avance y cómo aportar."
    for attribute, name, value in [
        ('name', 'description', description),
        ('property', 'og:description', description),
        ('property', 'og:image', image_url),
        ('property', 'og:url', public_url),
        ('name', 'twitter:image', image_url),
    ]:
        html = replace_meta_content(html, attribute, name, value)
    pattern = r'(<link\s+rel="canonical"\s+href=")[^"]*(">)'
    html, count = re.subn(pattern, lambda m: m.group(1) + URL_BASE + m.group(2), html, count=1)
    if count != 1:
        raise RuntimeError('Falta la etiqueta canonical. No se modificó index.html.')
    INDEX.write_text(html, encoding='utf-8')

RECAUDADO = read_recaudado()
VERSION = str(RECAUDADO)  # La misma cifra conserva la misma version
img = generate_image(RECAUDADO)
img.save(ASSETS/'og-portada-auto.png')
img.convert('RGB').save(ASSETS/'og-portada-auto.jpg', quality=92)
(ASSETS/'ultimo-dato.json').write_text(json.dumps({
    'recaudado': RECAUDADO,
    'meta': META_TOTAL,
    'faltante': max(META_TOTAL-RECAUDADO, 0),
    'porcentaje': round((RECAUDADO / META_TOTAL * 100) if META_TOTAL else 0, 2),
    'version': VERSION,
    'url_compartir_recomendada': f'{URL_BASE}?v={VERSION}'
}, ensure_ascii=False, indent=2), encoding='utf-8')
update_index(VERSION)
print('Recaudado leído:', RECAUDADO)
print('Versión:', VERSION)
print('Comparte preferiblemente:', f'{URL_BASE}?v={VERSION}')
