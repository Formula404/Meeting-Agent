"""将会议纪要文本导出为 PDF 文件，支持纯文本和 HTML 格式输入。"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from html import escape
from html.parser import HTMLParser
from pathlib import Path

from fpdf import FPDF


def _find_cjk_font_pair() -> tuple[str, str]:
    """查找系统中可用的中文字体对 (regular, bold)。

    Returns:
        (regular_font_path, bold_font_path) — bold 找不到时复用 regular。
    """
    # 已知的 regular / bold 配对
    pairs = [
        ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc"),
        ("C:/Windows/Fonts/dengl.ttf", None),
        ("C:/Windows/Fonts/simsun.ttc", None),
        ("C:/Windows/Fonts/simhei.ttf", None),
        ("/System/Library/Fonts/PingFang.ttc", None),
        ("/System/Library/Fonts/STHeiti Light.ttc", None),
        ("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", None),
        ("/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",
         "/usr/share/fonts/noto/NotoSansCJK-Bold.ttc"),
    ]
    for regular, bold in pairs:
        if Path(regular).exists():
            bold_path = bold if bold and Path(bold).exists() else regular
            return regular, bold_path

    # Fallback: local fonts directory
    local_fonts = Path(__file__).resolve().parent / "fonts"
    fonts = sorted(local_fonts.glob("*"))
    regular = None
    bold = None
    for f in fonts:
        if f.suffix.lower() not in (".ttf", ".ttc", ".otf"):
            continue
        if "bold" in f.stem.lower() or "bd" in f.stem.lower():
            bold = str(f)
        elif regular is None:
            regular = str(f)
    if regular:
        return regular, bold or regular

    raise RuntimeError(
        "未找到中文字体。请确保系统已安装 Microsoft YaHei 或 Noto Sans CJK。"
    )


class MeetingPDF(FPDF):
    """支持中文字体与基本排版的 PDF 生成器。"""

    def __init__(self) -> None:
        super().__init__()
        regular_path, bold_path = _find_cjk_font_pair()
        self.add_font("CJK", "", regular_path)
        self.add_font("CJK", "B", bold_path)
        self.add_font("CJK", "I", regular_path)  # CJK has no italic variant
        self.add_font("CJK", "BI", bold_path)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self) -> None:
        if self.page_no() > 1:
            self.set_font("CJK", "", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, "会议纪要", align="C")
            self.ln(12)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("CJK", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"第 {self.page_no()} 页", align="C")


# ── HTML 解析 & 渲染 ──────────────────────────────────────────────────

class _TextRun:
    """一段连续的同样式文本。"""
    def __init__(self, text: str, bold: bool = False, italic: bool = False, underline: bool = False):
        self.text = text
        self.bold = bold
        self.italic = italic
        self.underline = underline


class _Block:
    """一个块级元素。"""
    def __init__(self, tag: str, align: str = "left"):
        self.tag = tag
        self.align = align
        self.runs: list[_TextRun] = []
        self.children: list["_Block"] = []  # for list items


def _collapse_html_whitespace(text: str) -> str:
    """Match browser-style whitespace collapsing for parsed HTML text nodes."""
    return re.sub(r"\s+", " ", text).strip()


class _HtmlParser(HTMLParser):
    """解析 Tiptap 输出的 HTML 子集为块级结构。"""
    def __init__(self):
        super().__init__()
        self.blocks: list[_Block] = []
        self._current_block: _Block | None = None
        self._current_run: _TextRun | None = None
        self._bold = False
        self._italic = False
        self._underline = False
        self._in_li = False
        self._list_type: str | None = None  # "ul" or "ol"
        self._list_counter = 0

    def _push_run(self):
        if self._current_run and self._current_run.text:
            if self._current_block is not None:
                self._current_block.runs.append(self._current_run)
        self._current_run = None

    def _push_block(self):
        self._push_run()
        if self._current_block is not None and (
            self._current_block.runs or self._current_block.children
        ):
            self.blocks.append(self._current_block)
        self._current_block = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        align = "left"
        style = attrs_dict.get("style", "")
        if "text-align:center" in style or "text-align: center" in style:
            align = "center"
        elif "text-align:right" in style or "text-align: right" in style:
            align = "right"

        # Inside <li>, Tiptap nests <p> — ignore block tags to keep text in li
        if self._in_li and tag in ("h1", "h2", "h3", "p"):
            return
        if tag in ("h1", "h2", "h3", "p"):
            self._push_block()
            self._current_block = _Block(tag, align)
        elif tag == "hr":
            self._push_block()
            self._current_block = _Block("hr")
        elif tag in ("ul", "ol"):
            self._list_type = tag
            self._list_counter = 0
        elif tag == "li":
            self._push_block()
            self._in_li = True
            self._list_counter += 1
            self._current_block = _Block("li")
            self._current_block.list_type = self._list_type
            self._current_block.list_index = self._list_counter
        elif tag in ("strong", "b"):
            self._push_run()
            self._bold = True
        elif tag in ("em", "i"):
            self._push_run()
            self._italic = True
        elif tag == "u":
            self._push_run()
            self._underline = True

    def handle_endtag(self, tag):
        if self._in_li and tag in ("h1", "h2", "h3", "p"):
            return
        if tag in ("h1", "h2", "h3", "p", "hr", "li"):
            self._push_block()
            if tag == "li":
                self._in_li = False
        elif tag in ("ul", "ol"):
            self._list_type = None
            self._list_counter = 0
        elif tag in ("strong", "b"):
            self._push_run()
            self._bold = False
        elif tag in ("em", "i"):
            self._push_run()
            self._italic = False
        elif tag == "u":
            self._push_run()
            self._underline = False

    def handle_data(self, data):
        if not data.strip():
            return
        text = data
        if self._current_block is None:
            # Text outside block (shouldn't happen with Tiptap output, but fallback)
            self._push_block()
            self._current_block = _Block("p")
        if self._current_run is None:
            self._current_run = _TextRun(
                text, bold=self._bold, italic=self._italic, underline=self._underline
            )
        else:
            # Merge if same style
            if (self._current_run.bold == self._bold
                    and self._current_run.italic == self._italic
                    and self._current_run.underline == self._underline):
                self._current_run.text += text
            else:
                self._push_run()
                self._current_run = _TextRun(
                    text, bold=self._bold, italic=self._italic, underline=self._underline
                )


def _render_block_legacy(pdf: MeetingPDF, block: _Block, indent: int = 0):
    """渲染一个块级元素到 PDF。"""
    # Set font size based on tag
    if block.tag == "h1":
        font_size = 16
        line_h = 8
        bold = True
    elif block.tag == "h2":
        font_size = 14
        line_h = 7
        bold = True
    elif block.tag == "h3":
        font_size = 12
        line_h = 6.5
        bold = True
    elif block.tag == "li":
        font_size = 11
        line_h = 6.5
        bold = False
    else:
        font_size = 11
        line_h = 6.5
        bold = False

    align = block.align

    if block.tag == "hr":
        if pdf.get_y() + 8 > pdf.page_break_trigger:
            pdf.add_page()
        pdf.set_x(pdf.l_margin)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(6)
        return

    # Build text segments for this block
    segments = []
    has_bold = bold
    has_italic = False
    has_underline = False
    for run in block.runs:
        style_parts = []
        if run.bold or bold:
            style_parts.append("B")
            has_bold = True
        if run.italic:
            style_parts.append("I")
            has_italic = True
        if run.underline:
            style_parts.append("U")
            has_underline = True
        style = "".join(style_parts)
        segments.append((run.text, style))

    if not segments:
        if pdf.get_y() + line_h > pdf.page_break_trigger:
            pdf.add_page()
        pdf.ln(line_h * 0.6)
        return

    # For list items, add bullet/number prefix as first segment
    if block.tag == "li":
        prefix = ""
        if getattr(block, "list_type", None) == "ol":
            prefix = f"{getattr(block, 'list_index', 1)}. "
        else:
            prefix = "• "
        if segments:
            segments[0] = (prefix + segments[0][0], segments[0][1])
        else:
            segments.insert(0, (prefix, "B"))

    left_x = pdf.l_margin + indent
    avail_w = pdf.epw - indent
    pdf.set_x(left_x)

    full_text = _collapse_html_whitespace("".join(t for t, _ in segments))
    if not full_text:
        if pdf.get_y() + line_h > pdf.page_break_trigger:
            pdf.add_page()
        pdf.ln(line_h * 0.6)
        return
    style = ""
    if has_bold:
        style += "B"
    if has_italic:
        style += "I"
    if has_underline:
        style += "U"

    if pdf.get_y() + line_h > pdf.page_break_trigger:
        pdf.add_page()
    pdf.set_font("CJK", style, font_size)
    pdf.set_x(left_x)
    pdf.multi_cell(avail_w, line_h, full_text, align=align)
    pdf.ln(line_h * 0.15)


def _wrap_pdf_text(pdf: MeetingPDF, text: str, max_width: float) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and pdf.get_string_width(candidate) > max_width:
            lines.append(current.rstrip())
            current = char.lstrip()
        else:
            current = candidate
    if current:
        lines.append(current.rstrip())
    return lines or [""]


def _block_text(block: _Block) -> str:
    return _collapse_html_whitespace("".join(run.text for run in block.runs))


def _merge_standalone_order_markers(blocks: list[_Block]) -> list[_Block]:
    merged: list[_Block] = []
    i = 0
    marker_re = re.compile(r"^\d+\s*[.)．、]$")
    while i < len(blocks):
        block = blocks[i]
        text = _block_text(block)
        if (
            block.tag != "li"
            and marker_re.match(text)
            and i + 1 < len(blocks)
            and blocks[i + 1].tag not in ("hr", "li")
        ):
            next_block = blocks[i + 1]
            next_block.runs.insert(0, _TextRun(f"{text} "))
            merged.append(next_block)
            i += 2
            continue
        merged.append(block)
        i += 1
    return merged


def _merge_standalone_order_markers(blocks: list[_Block]) -> list[_Block]:
    merged: list[_Block] = []
    marker_re = re.compile(r"^\d+\s*(?:[.)]|\uff0e|\u3001)$")
    i = 0
    while i < len(blocks):
        block = blocks[i]
        text = _block_text(block)
        if (
            block.tag != "li"
            and marker_re.match(text)
            and i + 1 < len(blocks)
            and blocks[i + 1].tag not in ("hr", "li")
        ):
            next_block = blocks[i + 1]
            next_block.runs.insert(0, _TextRun(f"{text} "))
            merged.append(next_block)
            i += 2
            continue
        merged.append(block)
        i += 1
    return merged


def _merge_standalone_order_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    marker_re = re.compile(r"^\d+\s*(?:[.)]|\uff0e|\u3001)$")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if marker_re.match(line):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                merged.append(f"{line} {lines[j].strip()}")
                i = j + 1
                continue
        merged.append(line)
        i += 1
    return merged


def _browser_candidates() -> list[str]:
    candidates = [
        "msedge",
        "chrome",
        "chromium",
        "google-chrome",
        "chromium-browser",
    ]
    paths = []
    for name in candidates:
        found = shutil.which(name)
        if found:
            paths.append(found)

    roots = [
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    relative_paths = [
        ("Microsoft", "Edge", "Application", "msedge.exe"),
        ("Google", "Chrome", "Application", "chrome.exe"),
    ]
    for root in filter(None, roots):
        for parts in relative_paths:
            path = Path(root, *parts)
            if path.exists():
                paths.append(str(path))

    return list(dict.fromkeys(paths))


def _build_print_html(html_text: str) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="script-src 'none'; object-src 'none';">
  <style>
    @page {{
      size: A4;
      margin: 18mm 16mm;
    }}
    * {{
      box-sizing: border-box;
    }}
    html, body {{
      margin: 0;
      padding: 0;
      background: #fff;
      color: #111827;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", "Noto Sans SC", "PingFang SC", sans-serif;
      font-size: 12pt;
      line-height: 1.65;
    }}
    h1, h2, h3 {{
      break-after: avoid;
      page-break-after: avoid;
      line-height: 1.35;
      margin: 0 0 8pt;
      font-weight: 700;
    }}
    h1 {{ font-size: 18pt; text-align: center; margin-bottom: 12pt; }}
    h2 {{ font-size: 15pt; margin-top: 12pt; }}
    h3 {{ font-size: 13pt; margin-top: 10pt; }}
    p {{
      margin: 0 0 6pt;
      white-space: normal;
    }}
    ol, ul {{
      margin: 4pt 0 8pt;
      padding-left: 1.7em;
    }}
    li {{
      margin: 3pt 0;
      padding-left: 0.15em;
    }}
    li > p {{
      display: inline;
      margin: 0;
    }}
    li > p + p {{
      display: block;
      margin-top: 4pt;
    }}
    hr {{
      border: 0;
      border-top: 1px solid #d1d5db;
      margin: 10pt 0;
    }}
    strong, b {{ font-weight: 700; }}
    em, i {{ font-style: italic; }}
    u {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <main>{html_text}</main>
</body>
</html>"""


def _print_html_with_browser(html_text: str, output_path: Path) -> bool:
    browsers = _browser_candidates()
    if not browsers:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="meeting_pdf_") as tmp_dir:
        html_path = Path(tmp_dir) / "print.html"
        html_path.write_text(_build_print_html(html_text), encoding="utf-8")
        for browser in browsers:
            for headless_arg in ("--headless=new", "--headless"):
                cmd = [
                    browser,
                    headless_arg,
                    "--disable-gpu",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--no-pdf-header-footer",
                    "--print-to-pdf-no-header",
                    f"--print-to-pdf={output_path.resolve()}",
                    html_path.resolve().as_uri(),
                ]
                try:
                    subprocess.run(
                        cmd,
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=60,
                    )
                except Exception:
                    continue
                if output_path.exists() and output_path.stat().st_size > 0:
                    return True
    return False


def _plain_lines_to_html(lines: list[str]) -> str:
    parts = []
    for line in lines:
        text = line.strip()
        if text:
            parts.append(f"<p>{escape(text)}</p>")
        else:
            parts.append("<p><br></p>")
    return "".join(parts)


def export_to_pdf(meeting_text: str, output_path: str | Path) -> Path:
    """将纯文本会议纪要导出为 PDF。

    Args:
        meeting_text: 会议纪要纯文本全文。
        output_path: 输出 PDF 文件路径。

    Returns:
        生成的 PDF 文件路径。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = _merge_standalone_order_lines(meeting_text.strip().split("\n"))
    if _print_html_with_browser(_plain_lines_to_html(lines), output_path):
        return output_path

    pdf = MeetingPDF()
    pdf.add_page()

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            pdf.ln(4)
            continue

        if i == 0:
            pdf.set_font("CJK", "B", 16)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 8, line, align="C")
            pdf.ln(2)
        elif i < 5:
            pdf.set_font("CJK", "", 10)
            pdf.set_text_color(80, 80, 80)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 6, line, align="L")
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.set_font("CJK", "", 11)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 6.5, line)

    pdf.output(str(output_path))
    return output_path


def _render_block(pdf: MeetingPDF, block: _Block, indent: int = 0):
    if block.tag == "h1":
        font_size = 16
        line_h = 8
        bold = True
    elif block.tag == "h2":
        font_size = 14
        line_h = 7
        bold = True
    elif block.tag == "h3":
        font_size = 12
        line_h = 6.5
        bold = True
    else:
        font_size = 11
        line_h = 6.5
        bold = False

    if block.tag == "hr":
        if pdf.get_y() + 8 > pdf.page_break_trigger:
            pdf.add_page()
        pdf.set_x(pdf.l_margin)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(6)
        return

    has_bold = bold
    has_italic = False
    has_underline = False
    text_parts: list[str] = []
    for run in block.runs:
        has_bold = has_bold or run.bold
        has_italic = has_italic or run.italic
        has_underline = has_underline or run.underline
        text_parts.append(run.text)

    full_text = _collapse_html_whitespace("".join(text_parts))
    if not full_text:
        if pdf.get_y() + line_h > pdf.page_break_trigger:
            pdf.add_page()
        pdf.ln(line_h * 0.6)
        return

    style = ""
    if has_bold:
        style += "B"
    if has_italic:
        style += "I"
    if has_underline:
        style += "U"

    if pdf.get_y() + line_h > pdf.page_break_trigger:
        pdf.add_page()
    pdf.set_font("CJK", style, font_size)

    left_x = pdf.l_margin + indent
    avail_w = pdf.epw - indent
    align = block.align

    if block.tag == "li":
        if getattr(block, "list_type", None) == "ol":
            prefix = f"{getattr(block, 'list_index', 1)}."
        else:
            prefix = "-"
        prefix_w = max(8, pdf.get_string_width(prefix) + 3)
        body_x = left_x + prefix_w
        body_w = max(10, avail_w - prefix_w)
        for idx, line in enumerate(_wrap_pdf_text(pdf, full_text, body_w)):
            if pdf.get_y() + line_h > pdf.page_break_trigger:
                pdf.add_page()
            y = pdf.get_y()
            if idx == 0:
                pdf.set_xy(left_x, y)
                pdf.cell(prefix_w, line_h, prefix, align="R")
            pdf.set_xy(body_x, y)
            pdf.cell(body_w, line_h, line)
            pdf.set_y(y + line_h)
    else:
        pdf.set_x(left_x)
        pdf.multi_cell(avail_w, line_h, full_text, align=align)

    pdf.ln(line_h * 0.15)


def export_to_pdf_from_html(html_text: str, output_path: str | Path) -> Path:
    """将 HTML 格式的会议纪要导出为 PDF，保留富文本格式。

    支持 h1/h2/h3/p/hr/ul/ol/li 块级元素，
    以及 strong/b/em/i/u 内联样式，text-align 对齐。

    Args:
        html_text: Tiptap 输出的 HTML 全文。
        output_path: 输出 PDF 文件路径。

    Returns:
        生成的 PDF 文件路径。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if _print_html_with_browser(html_text, output_path):
        return output_path

    parser = _HtmlParser()
    parser.feed(html_text)
    blocks = _merge_standalone_order_markers(parser.blocks)

    pdf = MeetingPDF()
    pdf.add_page()

    for block in blocks:
        indent = 5 if block.tag == "li" else 0
        _render_block(pdf, block, indent=indent)

    pdf.output(str(output_path))
    return output_path
