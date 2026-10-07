#!/usr/bin/env python3
"""
Generate a sample PDF for the pipeline-builder demo.

The PDF must have a clean tabular layout so that pdf.js's text-extraction
+ the demo's detectPDFTable() heuristic can extract rows correctly.

The demo's table detector:
  1. Groups text items by Y coordinate (rounded to nearest 2px)
  2. Sorts each row's items by X
  3. Joins into cells split on 2+ space gaps
  4. Uses the first row as headers
  5. Coerces numeric-looking strings to numbers

For this to work, the PDF must:
  - Use a real table widget OR have text positioned in a grid
  - Have at least 3 rows × 2 cols
  - Have ≥60% of rows with ≥2 columns
  - Have 2+ space gaps between columns (so splitting works)

Using reportlab's `Table` flowable is the safest approach — it positions
text in a grid using actual coordinates (not a single text run with
spaces), so each cell is a separate text item with its own X/Y.

Output: /home/z/insight-analytics/data/sample-sales-report.pdf
"""
import random
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

OUT = '/home/z/insight-analytics/data/sample-sales-report.pdf'

# ─── Sample data: Q3 2026 regional sales report ────────────────────────────
# 30 rows. Same flavor as the Excel 'Regional Sales Q3' template so users
# can run the same kinds of summarize/sort/filter pipelines on it.

random.seed(42)  # deterministic so re-runs produce the same PDF

regions = ['Ontario', 'Quebec', 'BC', 'Alberta', 'Nova Scotia']
products = [
    ('Widget A', 25),
    ('Widget B', 45),
    ('Widget C', 12),
    ('Widget D', 85),
    ('Widget E', 120),
]
channels = ['Online', 'Retail', 'Partner']

rows = []
for i in range(30):
    # Generate a date in Q3 2026 (Jul-Sep)
    month = random.randint(7, 9)
    day = random.randint(1, 28)
    dt = datetime.date(2026, month, day)
    region = random.choice(regions)
    prod, price = random.choice(products)
    qty = random.randint(10, 200)
    # Ontario & Quebec overperform slightly (matches the Excel sample's pattern)
    if region in ('Ontario', 'Quebec'):
        qty = round(qty * 1.35)
    revenue = qty * price
    channel = random.choice(channels)
    rows.append({
        'date': dt.isoformat(),
        'region': region,
        'product': prod,
        'qty': qty,
        'revenue': revenue,
        'channel': channel,
    })

# Sort by date for a clean report feel
rows.sort(key=lambda r: r['date'])


def build():
    doc = SimpleDocTemplate(
        OUT, pagesize=letter,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        title='Q3 2026 Regional Sales Report',
        author='Insight Analytics',
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle('Body', parent=styles['BodyText'], fontSize=10, leading=14)
    h1 = styles['Heading1']
    h2 = styles['Heading2']

    story = []
    story.append(Paragraph('Q3 2026 Regional Sales Report', h1))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        'Prepared by Insight Analytics · October 7, 2026 · '
        'This sample report covers 30 sales transactions across five Canadian '
        'regions and five product lines for the third quarter of 2026.',
        body
    ))
    story.append(Spacer(1, 18))

    # ─── The main table ──────────────────────────────────────────────────
    # reportlab's Table positions each cell as a separate text item with its
    # own X/Y coordinate — pdf.js will extract each cell individually, and
    # the demo's detectPDFTable() will group them into rows by Y coordinate.
    header = ['Date', 'Region', 'Product', 'Qty', 'Revenue', 'Channel']
    table_data = [header]
    for r in rows:
        table_data.append([
            r['date'],
            r['region'],
            r['product'],
            str(r['qty']),
            '$' + format(r['revenue'], ','),
            r['channel'],
        ])

    # Column widths — total ~7.1 inches (letter width - 1.4" margins)
    col_widths = [0.85 * inch, 1.05 * inch, 1.05 * inch, 0.55 * inch, 1.0 * inch, 0.85 * inch]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 9),
        ('ALIGN',      (0, 0), (-1, 0), 'LEFT'),
        # Body rows
        ('FONTNAME',   (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',   (0, 1), (-1, -1), 9),
        ('ALIGN',      (3, 1), (4, -1), 'RIGHT'),  # Qty + Revenue right-aligned
        # Grid + alternating row colors
        ('GRID',       (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 18))

    # ─── Summary section ────────────────────────────────────────────────
    story.append(Paragraph('Summary', h2))
    story.append(Spacer(1, 4))
    total_revenue = sum(r['revenue'] for r in rows)
    total_qty = sum(r['qty'] for r in rows)
    avg_sale = total_revenue / len(rows)
    story.append(Paragraph(
        f'Total revenue (Q3 2026): <b>${total_revenue:,}</b> across <b>{len(rows)}</b> '
        f'transactions. Total units sold: <b>{total_qty:,}</b>. Average transaction '
        f'value: <b>${avg_sale:,.2f}</b>.',
        body
    ))
    story.append(Spacer(1, 6))

    # Region breakdown
    by_region = {}
    for r in rows:
        by_region.setdefault(r['region'], 0)
        by_region[r['region']] += r['revenue']
    region_rows = [['Region', 'Revenue']]
    for region in sorted(by_region.keys()):
        region_rows.append([region, '$' + format(by_region[region], ',')])
    region_tbl = Table(region_rows, colWidths=[2.0 * inch, 1.5 * inch], repeatRows=1)
    region_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0e7490')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 9),
        ('FONTNAME',   (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',   (0, 1), (-1, -1), 9),
        ('ALIGN',      (1, 1), (1, -1), 'RIGHT'),
        ('GRID',       (0, 0), (-1, -1), 0.25, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f5f9')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(Paragraph('Revenue by Region', body))
    story.append(Spacer(1, 4))
    story.append(region_tbl)
    story.append(Spacer(1, 18))

    story.append(Paragraph(
        'This report was generated as a sample for the Insight Analytics pipeline-builder '
        'demo. The data is synthetic. To try the demo: pick this sample, ask the AI '
        '"summarize revenue by product", and click Run pipeline.',
        body
    ))

    doc.build(story)
    print(f'Wrote {OUT}')
    # Show file size
    import os
    print(f'Size: {os.path.getsize(OUT)} bytes')


if __name__ == '__main__':
    build()
