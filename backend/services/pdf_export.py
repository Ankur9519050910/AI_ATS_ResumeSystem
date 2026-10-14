
import logging
from bs4 import BeautifulSoup
from weasyprint import HTML

logger = logging.getLogger("ats_resume_scorer")

REPORT_ORDER = [
    "summary",
    "skill_report",
    "jd_report",
    "recommendations",
]



def _scope_css(css_text: str, scope: str) -> str:
    import tinycss2

    rules = tinycss2.parse_stylesheet(
        css_text,
        skip_comments=True,
        skip_whitespace=True,
    )

    output = []

    for rule in rules:
        if rule.type == "qualified-rule":
            selector_text = tinycss2.serialize(rule.prelude).strip()
            declarations = tinycss2.serialize(rule.content)

            selectors = tinycss2.parse_component_value_list(selector_text)
            groups = []
            current = []

            for token in selectors:
                if token.type == "literal" and token.value == ",":
                    if current:
                        groups.append(tinycss2.serialize(current).strip())
                    current = []
                else:
                    current.append(token)

            if current:
                groups.append(tinycss2.serialize(current).strip())

            scoped_selectors = []

            for selector in groups:
                if selector == "body":
                    scoped_selectors.append(f".{scope}")
                elif selector == "html":
                    scoped_selectors.append(f".{scope}")
                else:
                    scoped_selectors.append(f".{scope} {selector}")

            output.append(
                f"{', '.join(scoped_selectors)} {{{declarations}}}"
            )

        else:
            # Preserve at-rules such as @page and @media.
            output.append(tinycss2.serialize([rule]))

    return "\n".join(output)



def generate_combined_pdf(html_docs: dict[str, str]) -> bytes:
    """Combine report HTML sections and render one continuous PDF."""

    if not html_docs:
        raise ValueError("No HTML documents provided for PDF generation.")

    try:
        styles = []
        sections = []

        ordered_names = [
            name for name in REPORT_ORDER if name in html_docs
        ]
        ordered_names += [
            name for name in html_docs if name not in ordered_names
        ]

        for index, name in enumerate(ordered_names, start=1):
            html_str = html_docs[name]

            if not html_str or not html_str.strip():
                logger.warning("Skipping empty HTML document: %s", name)
                continue

            soup = BeautifulSoup(html_str, "html.parser")
            scope = f"report-section-{index}"

            # Collect this template's styles.
            for style_tag in soup.find_all("style"):
                css_text = style_tag.string or style_tag.get_text()
                if css_text.strip():
                    styles.append(_scope_css(css_text, scope))

            # Keep body content, not the nested html/head/body wrappers.
            body = soup.body
            content = (
                "".join(str(child) for child in body.contents)
                if body
                else str(soup)
            )

            sections.append(
                f'<section class="{scope}">{content}</section>'
            )

        if not sections:
            raise ValueError("All HTML documents are empty.")

        combined_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>ATS Resume Analysis Report</title>
            <style>
                @page {{
                    size: A4;
                    margin: 14mm 15mm;
                }}

                html, body {{
                    margin: 0;
                    padding: 0;
                    font-family: Arial, sans-serif;
                    color: #1e293b;
                }}

                section {{
                    display: block;
                }}

                /* Do not force a new page between report sections. */
                .report-section-1,
                .report-section-2,
                .report-section-3,
                .report-section-4 {{
                    break-before: auto;
                    page-break-before: auto;
                }}

                h1, h2, .page-header, .score-section,
                .breakdown-row, .strength-item,
                .issue-card, .match-card, .stat-box,
                .validated-skill, .suggestion {{
                    break-inside: avoid;
                    page-break-inside: avoid;
                }}

                {''.join(styles)}
            </style>
        </head>
        <body>
            {''.join(sections)}
        </body>
        </html>
        """

        pdf_bytes = HTML(string=combined_html).write_pdf()

        logger.info(
            "Combined PDF generated successfully: %d bytes",
            len(pdf_bytes),
        )
        return pdf_bytes

    except Exception:
        logger.exception("Failed to generate combined PDF.")
        raise
