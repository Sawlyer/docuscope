from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "demo-corpus" / "sources"
OUTPUT = ROOT / "demo-corpus" / "pdfs"


def footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7DFE8"))
    canvas.line(22 * mm, 16 * mm, 188 * mm, 16 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#65758B"))
    canvas.drawString(22 * mm, 10 * mm, "NovaSphere - entreprise fictive - données de démonstration")
    canvas.drawRightString(188 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def build(source: Path):
    lines = source.read_text(encoding="utf-8").splitlines()
    title = lines[0].removeprefix("# ").strip()
    output = OUTPUT / f"{source.stem}.pdf"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DocTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27, alignment=0, textColor=colors.HexColor("#102A43"), spaceAfter=8))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=colors.HexColor("#126E82"), spaceBefore=14, spaceAfter=7))
    styles.add(ParagraphStyle(name="BodyFr", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.5, leading=16, textColor=colors.HexColor("#243B53"), spaceAfter=8))
    styles.add(ParagraphStyle(name="Meta", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.HexColor("#65758B"), spaceAfter=7))
    story = [
        Paragraph("NOVASPHERE · RÉFÉRENTIEL INTERNE", styles["Meta"]),
        Paragraph(title, styles["DocTitle"]),
        Paragraph("Document fictif conçu pour démontrer recherche sémantique et contrôle d'accès.", styles["BodyFr"]),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D7DFE8"), spaceBefore=2, spaceAfter=8),
    ]
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 3 * mm))
        elif stripped.startswith("## "):
            story.append(Paragraph(stripped[3:], styles["Section"]))
        elif stripped.startswith("- "):
            story.append(Paragraph(f"• {stripped[2:]}", styles["BodyFr"]))
        else:
            story.append(Paragraph(stripped, styles["BodyFr"]))
    document = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=22 * mm, leftMargin=22 * mm, topMargin=22 * mm, bottomMargin=23 * mm, title=title, author="NovaSphere")
    document.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for source in sorted(SOURCES.glob("*.md")):
        build(source)
