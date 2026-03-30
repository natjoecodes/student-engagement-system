from datetime import datetime
from io import BytesIO
from math import sqrt
import os
from pathlib import Path

MPL_CACHE_DIR = Path("/tmp/student-engagement-matplotlib-cache")
MPL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE_DIR))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


LOGO_PATH = (
    Path(__file__).resolve().parent.parent
    / "dashboard-server"
    / "static"
    / "assets"
    / "logo.png"
)

PAGE_WIDTH, PAGE_HEIGHT = A4
PAGE_MARGIN_X = 0.72 * inch
CONTENT_WIDTH = PAGE_WIDTH - (2 * PAGE_MARGIN_X)
GRID_GUTTER = 0.12 * inch
HALF_WIDTH = (CONTENT_WIDTH - GRID_GUTTER) / 2
QUARTER_WIDTH = (CONTENT_WIDTH - (3 * GRID_GUTTER)) / 4
REPORT_TITLE = "Session Attentiveness Report"

NAVY = colors.HexColor("#14324A")
SLATE = colors.HexColor("#4D6273")
SOFT_TEXT = colors.HexColor("#738596")
PANEL_BG = colors.HexColor("#F8FAFC")
PANEL_BORDER = colors.HexColor("#DBE4EC")
ACCENT = colors.HexColor("#117E7D")
SKY = colors.HexColor("#3F7CAC")
AMBER = colors.HexColor("#D9A441")
RED = colors.HexColor("#CC5A5A")
LIGHT_BLUE = colors.HexColor("#EEF5FA")
WHITE = colors.white


def format_dt(value):
    if not value:
        return "N/A"
    return datetime.fromisoformat(value).strftime("%d %b %Y, %I:%M %p")


def compute_duration_minutes(start_time, end_time):
    if not start_time or not end_time:
        return 0
    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time)
    return max(0, round((end_dt - start_dt).total_seconds() / 60, 1))


def engagement_band(score):
    if score >= 75:
        return "High"
    if score >= 50:
        return "Moderate"
    return "Low"


def stability_label(std_dev):
    if std_dev <= 10:
        return "Very Stable"
    if std_dev <= 18:
        return "Stable"
    if std_dev <= 28:
        return "Variable"
    return "High Variability"


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="Kicker",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=SOFT_TEXT,
        spaceAfter=2,
        uppercase=True,
    ))
    styles.add(ParagraphStyle(
        name="HeroChip",
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=10,
        textColor=ACCENT,
    ))
    styles.add(ParagraphStyle(
        name="CollegeTitle",
        fontName="Helvetica-Bold",
        fontSize=13.5,
        leading=17,
        textColor=NAVY,
    ))
    styles.add(ParagraphStyle(
        name="CollegeSub",
        fontName="Helvetica",
        fontSize=9.2,
        leading=12,
        textColor=SLATE,
    ))
    styles.add(ParagraphStyle(
        name="ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=NAVY,
    ))
    styles.add(ParagraphStyle(
        name="Lead",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=SLATE,
    ))
    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=12.2,
        leading=15,
        textColor=NAVY,
    ))
    styles.add(ParagraphStyle(
        name="Body",
        fontName="Helvetica",
        fontSize=9.2,
        leading=13.5,
        textColor=SLATE,
        wordWrap="CJK",
    ))
    styles.add(ParagraphStyle(
        name="Muted",
        fontName="Helvetica",
        fontSize=8.3,
        leading=10.8,
        textColor=SOFT_TEXT,
        wordWrap="CJK",
    ))
    styles.add(ParagraphStyle(
        name="MetricLabel",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=SOFT_TEXT,
    ))
    styles.add(ParagraphStyle(
        name="MetricValue",
        fontName="Helvetica-Bold",
        fontSize=16.5,
        leading=18,
        textColor=NAVY,
    ))
    styles.add(ParagraphStyle(
        name="MetricNote",
        fontName="Helvetica",
        fontSize=7.8,
        leading=9.5,
        textColor=SOFT_TEXT,
    ))
    styles.add(ParagraphStyle(
        name="MetaLabel",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=SOFT_TEXT,
    ))
    styles.add(ParagraphStyle(
        name="MetaValue",
        fontName="Helvetica",
        fontSize=9.2,
        leading=11.8,
        textColor=NAVY,
        wordWrap="CJK",
    ))
    return styles


def compute_metrics(session_row, log_rows):
    sid, subject, faculty, start_time, end_time, avg_attention, peak_attention = session_row
    attentions = [float(row[1] or 0) for row in log_rows]

    if attentions:
        avg = round(sum(attentions) / len(attentions), 1)
        peak = round(max(attentions), 1)
        minimum = round(min(attentions), 1)
        variance = sum((x - avg) ** 2 for x in attentions) / len(attentions)
        std_dev = round(sqrt(variance), 1)
    else:
        avg = round(avg_attention or 0, 1)
        peak = round(peak_attention or 0, 1)
        minimum = 0.0
        std_dev = 0.0

    duration_minutes = compute_duration_minutes(start_time, end_time)

    high_count = sum(1 for x in attentions if x >= 70)
    medium_count = sum(1 for x in attentions if 40 <= x < 70)
    low_count = sum(1 for x in attentions if x < 40)
    total_count = len(attentions) or 1

    phase_names = ["Opening", "Development", "Late Session", "Closing"]
    phase_labels = []
    phase_values = []
    if attentions:
        phase_count = 4 if len(attentions) >= 8 else max(1, min(3, len(attentions)))
        phase_size = max(1, len(attentions) // phase_count)
        for idx in range(phase_count):
            if idx < phase_count - 1:
                chunk = attentions[idx * phase_size:(idx + 1) * phase_size]
            else:
                chunk = attentions[idx * phase_size:]
            if chunk:
                phase_labels.append(phase_names[idx])
                phase_values.append(round(sum(chunk) / len(chunk), 1))

    longest_low_streak = 0
    streak = 0
    for value in attentions:
        if value < 40:
            streak += 1
            longest_low_streak = max(longest_low_streak, streak)
        else:
            streak = 0

    trend_delta = 0
    if len(attentions) >= 6:
        band = max(3, len(attentions) // 3)
        start_avg = sum(attentions[:band]) / band
        end_avg = sum(attentions[-band:]) / band
        trend_delta = round(end_avg - start_avg, 1)

    return {
        "session_id": sid,
        "subject": subject or "N/A",
        "faculty": faculty or "N/A",
        "start_time": start_time,
        "end_time": end_time,
        "duration_minutes": duration_minutes,
        "avg_attention": avg,
        "peak_attention": peak,
        "min_attention": minimum,
        "std_dev": std_dev,
        "stability": stability_label(std_dev),
        "engagement_label": engagement_band(avg),
        "attentions": attentions,
        "distribution": [high_count, medium_count, low_count],
        "distribution_pct": [
            round((high_count / total_count) * 100),
            round((medium_count / total_count) * 100),
            round((low_count / total_count) * 100),
        ],
        "phase_labels": phase_labels,
        "phase_values": phase_values,
        "sample_count": len(attentions),
        "longest_low_streak": longest_low_streak,
        "trend_delta": trend_delta,
    }


def build_observations(metrics):
    observations = []

    if metrics["engagement_label"] == "High":
        observations.append(
            "The session maintained a strong engagement baseline, which suggests that the structure and delivery held student attention effectively."
        )
    elif metrics["engagement_label"] == "Moderate":
        observations.append(
            "The session achieved moderate engagement, indicating that the class was effective overall but had room for stronger consistency."
        )
    else:
        observations.append(
            "The session remained in the low engagement range for long stretches, which suggests the lecture flow may need more active student involvement."
        )

    if metrics["trend_delta"] <= -12:
        observations.append(
            "Attention decreased significantly toward the end of the session, which may indicate fatigue, dense explanation, or reduced interactivity."
        )
    elif metrics["trend_delta"] >= 8:
        observations.append(
            "Engagement improved in the latter stages of the class, suggesting that later explanations or activities re-captured student focus."
        )
    else:
        observations.append(
            "The engagement trend remained relatively balanced across the session without a severe upward or downward swing."
        )

    if metrics["std_dev"] >= 20:
        observations.append(
            "Attention varied sharply between segments, so some portions of the class appear to have been much more effective than others."
        )
    else:
        observations.append(
            "Attention stayed reasonably stable throughout the class, indicating a consistent instructional rhythm."
        )

    if metrics["distribution_pct"][2] >= 30:
        observations.append(
            "A considerable share of the session fell in the low-attention band, which is worth reviewing alongside the teaching method used in those moments."
        )

    return observations[:4]


def build_recommendations(metrics):
    recommendations = []

    if metrics["trend_delta"] <= -12 or metrics["distribution_pct"][2] >= 25:
        recommendations.append(
            "Introduce a short interaction, concept check, or recap around the midpoint to reduce late-session drop-off."
        )

    if metrics["std_dev"] >= 20:
        recommendations.append(
            "Review the least effective phase of the lecture and break dense stretches into shorter explanatory blocks."
        )

    if metrics["engagement_label"] == "Low":
        recommendations.append(
            "Use more worked examples, questioning, or guided discussion to make the class more participatory."
        )
    elif metrics["engagement_label"] == "Moderate":
        recommendations.append(
            "Retain the current teaching flow, but add one or two planned re-engagement points for better consistency."
        )
    else:
        recommendations.append(
            "Preserve the strongest-performing teaching segment as a reference pattern for future sessions."
        )

    recommendations.append(
        "Compare the phase-wise chart against your lesson plan to identify where engagement improved or weakened."
    )

    return recommendations[:4]


def chart_image(fig, width, height):
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    img = Image(buffer, width=width, height=height)
    img.hAlign = "CENTER"
    return img


def build_trend_chart(metrics):
    values = metrics["attentions"] or [0]
    x_values = list(range(1, len(values) + 1))

    fig, ax = plt.subplots(figsize=(7.0, 2.7))
    ax.axhspan(0, 40, color="#FBE9E7")
    ax.axhspan(40, 70, color="#FFF4DE")
    ax.axhspan(70, 100, color="#E8F5F0")
    ax.plot(x_values, values, color="#255E91", linewidth=2.8)
    ax.fill_between(x_values, values, color="#C9DFF1", alpha=0.5)
    ax.set_xlim(1, max(x_values))
    ax.set_ylim(0, 100)
    ax.set_title("Attention Trend Across the Session", fontsize=11, fontweight="bold", color="#14324A", pad=10)
    ax.set_xlabel("Sample Progress", fontsize=8.5, color="#4D6273")
    ax.set_ylabel("Attention Score", fontsize=8.5, color="#4D6273")
    ax.tick_params(labelsize=8, colors="#4D6273")
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#D5E0E8")
    ax.spines["bottom"].set_color("#D5E0E8")
    return chart_image(fig, 5.75 * inch, 1.95 * inch)


def build_phase_chart(metrics):
    labels = metrics["phase_labels"] or ["Session"]
    values = metrics["phase_values"] or [metrics["avg_attention"]]

    fig, ax = plt.subplots(figsize=(3.6, 2.55))
    bars = ax.bar(labels, values, color=["#1D7A73", "#3F7CAC", "#D9A441", "#CC5A5A"][:len(labels)], width=0.58)
    ax.set_ylim(0, 100)
    ax.set_title("Phase-wise Average Attention", fontsize=10.5, fontweight="bold", color="#14324A", pad=10)
    ax.tick_params(axis="x", labelrotation=0, labelsize=7.6, colors="#4D6273")
    ax.tick_params(axis="y", labelsize=7.6, colors="#4D6273")
    ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#D5E0E8")
    ax.spines["bottom"].set_color("#D5E0E8")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 2, f"{value:.0f}", ha="center", va="bottom", fontsize=7.5, color="#14324A")
    return chart_image(fig, 2.55 * inch, 1.9 * inch)


def build_distribution_chart(metrics):
    values = metrics["distribution"] or [1, 0, 0]
    labels = [
        f"High  {metrics['distribution_pct'][0]}%",
        f"Medium  {metrics['distribution_pct'][1]}%",
        f"Low  {metrics['distribution_pct'][2]}%",
    ]

    fig, ax = plt.subplots(figsize=(3.3, 2.55))
    wedges, _ = ax.pie(
        values,
        startangle=90,
        colors=["#1D7A73", "#D9A441", "#CC5A5A"],
        wedgeprops={"width": 0.42, "edgecolor": "white"},
    )
    ax.set_title("Attention Distribution", fontsize=10.5, fontweight="bold", color="#14324A", pad=10)
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7.5, frameon=False)
    return chart_image(fig, 2.55 * inch, 1.9 * inch)


def safe_logo():
    if not LOGO_PATH.exists():
        return None
    logo = Image(str(LOGO_PATH), width=0.72 * inch, height=0.72 * inch)
    logo.hAlign = "LEFT"
    return logo


def info_cell(label, value, styles):
    return [
        Paragraph(label, styles["MetaLabel"]),
        Paragraph(value, styles["MetaValue"]),
    ]


def stat_card(label, value, note, styles):
    value_style = styles["MetricValue"]
    if len(str(value)) > 10:
        value_style = ParagraphStyle(
            "MetricValueCompact",
            parent=styles["MetricValue"],
            fontSize=12.5,
            leading=14,
        )

    card = Table(
        [
            [Paragraph(label, styles["MetricLabel"])],
            [Paragraph(value, value_style)],
            [Paragraph(note, styles["MetricNote"])],
        ],
        colWidths=[QUARTER_WIDTH],
    )
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.8, PANEL_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 12),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return card


def snapshot_panel(metrics, styles):
    trend_line = (
        "Engagement improved over time."
        if metrics["trend_delta"] > 6
        else "Engagement weakened toward the end."
        if metrics["trend_delta"] < -6
        else "Engagement remained broadly steady."
    )
    risk_line = (
        "Low-attention periods were limited."
        if metrics["distribution_pct"][2] < 15
        else "Some low-attention periods were present."
        if metrics["distribution_pct"][2] < 30
        else "Low-attention periods occupied a notable share of the session."
    )

    panel = Table(
        [[
            Paragraph("<b>Session Snapshot</b><br/>%s" % trend_line, styles["Body"]),
            Paragraph("<b>Stability</b><br/>%s" % metrics["stability"], styles["Body"]),
            Paragraph("<b>Attention Risk</b><br/>%s" % risk_line, styles["Body"]),
        ]],
        colWidths=[2.2 * inch, 1.45 * inch, CONTENT_WIDTH - 3.65 * inch],
    )
    panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, PANEL_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return panel


def hero_panel(metrics, styles):
    logo = safe_logo() or Paragraph("GECK", styles["CollegeTitle"])

    chip = Table(
        [[Paragraph("Faculty Analytics Report", styles["HeroChip"])]],
        colWidths=[1.45 * inch],
    )
    chip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF8F4")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBEAE2")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    top_row = Table(
        [[
            logo,
            [
                Paragraph("Government Engineering College Kozhikode", styles["CollegeTitle"]),
                Paragraph("Student Engagement Analytics System (S8 AE&amp;I)", styles["CollegeSub"]),
            ],
            chip
        ]],
        colWidths=[0.82 * inch, CONTENT_WIDTH - 2.47 * inch, 1.65 * inch],
    )
    top_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    hero = Table(
        [[top_row],
         [Spacer(1, 4)],
         [Paragraph(REPORT_TITLE, styles["ReportTitle"])],
         [Spacer(1, 2)],
         [Paragraph(
            "A post-session analytics summary for faculty review, focused on engagement quality, session consistency, and actionable teaching insights.",
            styles["Lead"],
         )]],
        colWidths=[CONTENT_WIDTH],
    )
    hero.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, PANEL_BORDER),
        ("LINEABOVE", (0, 0), (-1, 0), 3, NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return hero


def subject_meta_panel(metrics, styles):
    panel = Table(
        [[
            Paragraph("<b>Subject</b><br/>%s" % metrics["subject"], styles["Body"]),
            Paragraph("<b>Faculty</b><br/>%s" % metrics["faculty"], styles["Body"]),
            Paragraph("<b>Date</b><br/>%s" % format_dt(metrics["start_time"]), styles["Body"]),
        ]],
        colWidths=[2.55 * inch, 1.9 * inch, CONTENT_WIDTH - 4.45 * inch],
    )
    panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.8, PANEL_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return panel


def session_meta_panel(metrics, styles):
    rows = [
        [
            Paragraph("Duration", styles["MetaLabel"]),
            Paragraph("Samples", styles["MetaLabel"]),
            Paragraph("Session ID", styles["MetaLabel"]),
        ],
        [
            Paragraph(f"{metrics['duration_minutes']} min", styles["MetaValue"]),
            Paragraph(str(metrics["sample_count"]), styles["MetaValue"]),
            Paragraph(metrics["session_id"], styles["MetaValue"]),
        ],
    ]
    panel = Table(rows, colWidths=[1.45 * inch, 1.05 * inch, CONTENT_WIDTH - 2.50 * inch])
    panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.8, PANEL_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
    ]))
    return panel


def build_observation_panel(title, items, styles):
    rows = [[Paragraph(title, styles["SectionTitle"])]]
    for item in items:
        rows.append([Paragraph(f"• {item}", styles["Body"])])

    panel = Table(rows, colWidths=[HALF_WIDTH])
    panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, PANEL_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (0, 0), 0.5, PANEL_BORDER),
    ]))
    return panel


def generate_session_report(session_row, log_rows):
    metrics = compute_metrics(session_row, log_rows)
    observations = build_observations(metrics)
    recommendations = build_recommendations(metrics)
    styles = build_styles()

    doc_buffer = BytesIO()
    doc = SimpleDocTemplate(
        doc_buffer,
        pagesize=A4,
        leftMargin=PAGE_MARGIN_X,
        rightMargin=PAGE_MARGIN_X,
        topMargin=0.9 * inch,
        bottomMargin=0.7 * inch,
    )

    story = []
    story.append(hero_panel(metrics, styles))
    story.append(Spacer(1, 8))
    story.append(subject_meta_panel(metrics, styles))
    story.append(Spacer(1, 8))
    story.append(session_meta_panel(metrics, styles))
    story.append(Spacer(1, 10))

    cards = [
        stat_card("Average Attention", f"{metrics['avg_attention']:.0f}", metrics["engagement_label"], styles),
        stat_card("Peak Attention", f"{metrics['peak_attention']:.0f}", "Highest point", styles),
        stat_card("Lowest Attention", f"{metrics['min_attention']:.0f}", "Review area", styles),
        stat_card("Stability", metrics["stability"], f"Std. dev. {metrics['std_dev']:.1f}", styles),
    ]
    summary_grid = Table(
        [[cards[0], "", cards[1], "", cards[2], "", cards[3]]],
        colWidths=[
            QUARTER_WIDTH, GRID_GUTTER,
            QUARTER_WIDTH, GRID_GUTTER,
            QUARTER_WIDTH, GRID_GUTTER,
            QUARTER_WIDTH,
        ],
        rowHeights=[1.26 * inch],
    )
    summary_grid.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("BACKGROUND", (1, 0), (1, 0), WHITE),
        ("BACKGROUND", (3, 0), (3, 0), WHITE),
        ("BACKGROUND", (5, 0), (5, 0), WHITE),
    ]))
    story.append(summary_grid)
    story.append(Spacer(1, 10))

    trend_panel = Table(
        [[
            Paragraph("Engagement Trend", styles["SectionTitle"])
        ], [
            Paragraph(
                "The chart shows how student attentiveness changed across the session.",
                styles["Body"],
            )
        ], [
            build_trend_chart(metrics)
        ]],
        colWidths=[CONTENT_WIDTH],
    )
    trend_panel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.8, PANEL_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.append(KeepTogether([trend_panel]))
    story.append(Spacer(1, 12))
    story.append(snapshot_panel(metrics, styles))
    story.append(Spacer(1, 12))

    chart_left = Table(
        [[Paragraph("Phase Breakdown", styles["SectionTitle"])], [build_phase_chart(metrics)]],
        colWidths=[HALF_WIDTH],
    )
    chart_left.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.8, PANEL_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    chart_right = Table(
        [[Paragraph("Distribution Snapshot", styles["SectionTitle"])], [build_distribution_chart(metrics)]],
        colWidths=[HALF_WIDTH],
    )
    chart_right.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.8, PANEL_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))

    lower_charts = Table([[chart_left, "", chart_right]], colWidths=[HALF_WIDTH, GRID_GUTTER, HALF_WIDTH])
    lower_charts.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (1, 0), (1, 0), WHITE),
    ]))
    story.append(lower_charts)
    story.append(Spacer(1, 12))

    notes = Table(
        [[
            build_observation_panel("Key Observations", observations, styles),
            "",
            build_observation_panel("Recommendations for Faculty", recommendations, styles),
        ]],
        colWidths=[HALF_WIDTH, GRID_GUTTER, HALF_WIDTH],
    )
    notes.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (1, 0), (1, 0), WHITE),
    ]))
    story.append(notes)
    story.append(Spacer(1, 12))

    footer_text = [
        Paragraph(
            "Prepared automatically by the Student Engagement Analytics System for post-session faculty review.",
            styles["Muted"],
        ),
        Spacer(1, 4),
        Paragraph("Developed by:", styles["Muted"]),
        Paragraph("&bull; Nathan Jose V", styles["Muted"]),
        Paragraph("&bull; Nivedhya K", styles["Muted"]),
        Paragraph("&bull; Bhuvaneswari A", styles["Muted"]),
        Paragraph("&bull; Stephin Joseph", styles["Muted"]),
        Spacer(1, 4),
        Paragraph(
            "Applied Electronics & Instrumentation Engineering, Government Engineering College Kozhikode.",
            styles["Muted"],
        ),
        Spacer(1, 4),
        Paragraph("© 2026 Multimodal Edge AI System for Real Time Student Engagement Analytics. All Rights Reserved", styles["Muted"]),
    ]

    footer = Table(
        [[footer_text]],
        colWidths=[CONTENT_WIDTH],
    )
    footer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, PANEL_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(footer)

    doc.build(story)
    doc_buffer.seek(0)
    return doc_buffer
