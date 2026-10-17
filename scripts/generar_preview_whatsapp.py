#!/usr/bin/env python3
"""Actualiza una única imagen de WhatsApp y la misma URL de campaña.

Nota: actualizar Open Graph NO fuerza a WhatsApp a refrescar una vista previa
que haya guardado. Este script no crea URLs adicionales ni páginas /share/.
"""
import argparse
import csv
import html
import io
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
INDEX = ROOT / 'index.html'
URL_BASE = 'https://plravelor.github.io/fondo-melany/'
GOAL = 3_000_000
CSV_URL = os.environ.get('SHEET_CSV_URL', '').strip()
MILESTONES = (500_000, 1_000_000, 2_000_000, GOAL)

def pesos(n):
    return '$' + format(n, ',').replace(',', '.')


def porcentaje(n, total):
    return format((100 * n / total) if total else 0, '.1f').replace('.', ',') + '%'


def sheet_amount():
    if not CSV_URL.startswith('https://'):
        raise RuntimeError('Configura SHEET_CSV_URL con el enlace CSV publicado de Google Sheets.')
    response = requests.get(CSV_URL, timeout=35, headers={'User-Agent': 'MelanyCampaignCard/2.0'})
    response.raise_for_status()
    content = response.content.decode('utf-8-sig')
    if content.lstrip().startswith('<!DOCTYPE html') or content.lstrip().startswith('<html'):
        raise RuntimeError('Google Sheets devolvió HTML, no CSV. Verifica Publicar en la Web → CSV.')
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        fields = {str(k or '').strip().lower(): str(v or '').strip() for k, v in row.items()}
        if fields.get('concepto', '').lower() == 'recaudado':
            amount = re.sub(r'[^0-9]', '', fields.get('valor', ''))
            if not amount:
                raise ValueError('El valor de Recaudado está vacío o no es numérico.')
            return int(amount)
    raise ValueError('El CSV no contiene la fila Concepto=Recaudado y la columna Valor.')


def font(size, bold=False):
    family = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    for p in [f'/usr/share/fonts/truetype/dejavu/{family}', f'/usr/local/share/fonts/{family}']:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.truetype(family, size)


def draw_card(amount):
    W, H = 1200, 630
    bg = '#081719'
    bright = '#55eab0'
    muted = '#a0babc'
    white = '#f5fbf9'
    img = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((25, 24, 1174, 606), 34, fill='#0b2426', outline='#1d4546', width=3)
    d.rounded_rectangle((55, 49, 353, 96), 23, fill='#1b4240')
    d.text((78, 61), 'FONDO DE MOVILIDAD', font=font(22, True), fill=white)
    d.text((1131, 60), '19–24 oct. 2026', font=font(24), fill='#daeae5', anchor='ra')
    d.text((60, 132), 'Apoyemos a Melany', font=font(47, True), fill=white)
    d.text((60, 189), 'a presentar su investigación en Brasil', font=font(35, True), fill=bright)

    # Indicador circular general, limitado a 100% visual aunque exceda el total.
    center = (174, 372)
    r = 105
    box = (center[0]-r, center[1]-r, center[0]+r, center[1]+r)
    d.arc(box, 0, 359.8, fill='#486a69', width=19)
    fraction = min(1.0, amount / GOAL) if GOAL else 0
    if fraction > 0:
        d.arc(box, -90, -90 + 359.7 * fraction, fill=bright, width=19)
    d.text((center[0], center[1]-12), porcentaje(amount, GOAL), font=font(39, True), fill=white, anchor='mm')
    d.text((center[0], center[1]+28), 'alcanzado', font=font(20), fill=muted, anchor='mm')

    d.text((330, 265), 'RECAUDADO', font=font(19, True), fill=muted)
    d.text((330, 302), pesos(amount), font=font(57, True), fill=bright)
    d.text((330, 394), 'Meta: ' + pesos(GOAL), font=font(31, True), fill=white)
    d.text((330, 441), 'Faltan ' + pesos(max(0, GOAL - amount)), font=font(28), fill=muted)

    # Siguiente meta pendiente, no un objetivo anterior ya cumplido.
    next_goal = next((x for x in MILESTONES if amount < x), None)
    d.rounded_rectangle((56, 517, 1143, 583), 19, fill='#173536')
    if next_goal:
        text_label = 'PRÓXIMO OBJETIVO: ' + pesos(next_goal)
        next_pct = min(1, amount / next_goal)
        note = porcentaje(amount, next_goal) + ' alcanzado'
    else:
        text_label = '¡META GENERAL ALCANZADA!'
        next_pct = 1
        note = '100%'
    d.text((76, 527), text_label, font=font(20, True), fill=white)
    d.text((1120, 527), note, font=font(19, True), fill=bright, anchor='ra')
    d.rounded_rectangle((77, 556, 1120, 569), 7, fill='#4c6867')
    width = round(1043 * next_pct)
    if width > 0:
        d.rounded_rectangle((77, 556, 77+max(width, 12), 569), 7, fill=bright)
    return img




def replace_or_insert_meta(page: str, selector: str, key: str, value: str) -> str:
    """Sustituye el valor sin alterar la etiqueta, evitando referencias \1 en re.sub."""
    tag_re = rf'<meta\s+{selector}="{re.escape(key)}"\s+content="[^"]*"\s*/?>'
    tag = f'<meta {selector}="{key}" content="{html.escape(value, quote=True)}">'
    updated, n = re.subn(tag_re, lambda _: tag, page, count=1, flags=re.I)
    if not n:
        if '</head>' not in page:
            raise RuntimeError('index.html no contiene </head>; se cancela actualización')
        updated = page.replace('</head>', f'  {tag}\n</head>', 1)
    return updated


def update_index(amount: int):
    page = INDEX.read_text('utf-8')
    # URL y og:image FIJOS. No hay ?v=, /share/ ni rutas nuevas.
    img_url = URL_BASE + 'assets/og-portada-auto.jpg'
    desc = f'Hemos recaudado {pesos(amount)} de {pesos(GOAL)}. Consulta el avance y cómo aportar.'
    changes = [
        ('name','description',desc),
        ('property','og:description',desc),
        ('property','og:image',img_url),
        ('property','og:image:secure_url',img_url),
        ('property','og:image:type','image/jpeg'),
        ('property','og:image:width','1200'),
        ('property','og:image:height','630'),
        ('property','og:url',URL_BASE),
        ('name','twitter:image',img_url),
    ]
    for selector,key,value in changes:
        page=replace_or_insert_meta(page,selector,key,value)
    # La URL canónica también queda fija.
    canonical='<link rel="canonical" href="'+URL_BASE+'">'
    page,n=re.subn(r'<link\s+rel="canonical"\s+href="[^"]*"\s*/?>', lambda _: canonical, page, count=1)
    if n==0:
        page=page.replace('</head>', '  '+canonical+'\n</head>',1)
    if '\x01' in page or '\x02' in page:
        raise RuntimeError('HTML tiene caracteres de control: restaurar index.html')
    INDEX.write_text(page,encoding='utf-8')


def main(amount):
    if not (0 <= amount <= 100_000_000):
        raise ValueError('El recaudo parece incorrecto; no se publica.')
    ASSETS.mkdir(exist_ok=True, parents=True)
    card=draw_card(amount)
    path=ASSETS/'og-portada-auto.jpg'
    card.convert('RGB').save(path, 'JPEG', quality=82, optimize=True, progressive=False)
    update_index(amount)
    data={'recaudado':amount,'meta':GOAL,
          'porcentaje':round(amount/GOAL*100,2),
          'faltante':max(0,GOAL-amount),
          'url_compartir_recomendada':URL_BASE,
          'imagen_publica': URL_BASE+'assets/og-portada-auto.jpg'}
    (ASSETS/'ultimo-dato.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(f'Monto publicado: {pesos(amount)} de {pesos(GOAL)}')
    print(f'Imagen: {path} ({path.stat().st_size//1024} KB)')
    print('Compartir siempre: '+URL_BASE)
    print('Importante: WhatsApp puede conservar miniaturas anteriores en su caché.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--test-amount', type=int, help='Prueba local; NO usar en Github Actions')
    opts=p.parse_args()
    main(opts.test_amount if opts.test_amount is not None else sheet_amount())
