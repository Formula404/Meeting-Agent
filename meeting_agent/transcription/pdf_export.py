"""将会议纪要文本导出为 PDF 文件，支持纯文本和 HTML 格式输入。"""

import math
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
        text = data.strip()
        if not text:
            return
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


def _render_block(pdf: MeetingPDF, block: _Block, indent: int = 0):
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
        pdf.set_x(pdf.l_margin)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(6)
        return

    # Build text segments for this block
    segments = []
    for run in block.runs:
        style = "B" if (run.bold or bold) else ""
        segments.append((run.text, style))

    if not segments:
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

    if align == "left":
        # write() advances y only on line wrap; manual y calc after all segments
        y_start = pdf.get_y()
        pdf.set_x(left_x)
        for text, style in segments:
            pdf.set_font("CJK", style, font_size)
            pdf.write(line_h, text)
        # Calculate total height from total text width (CJK wraps per char)
        total_w = sum(pdf.get_string_width(t) for t, _ in segments)
        num_lines = max(1, math.ceil(total_w / avail_w))
        pdf.set_y(y_start + num_lines * line_h)
        pdf.ln(line_h * 0.15)
    else:
        # Center/right: concatenate, render with multi_cell
        full_text = "".join(t for t, _ in segments)
        first_style = segments[0][1] if segments else ""
        pdf.set_font("CJK", first_style, font_size)
        pdf.set_x(left_x)
        pdf.multi_cell(avail_w, line_h, full_text, align=align)
        pdf.ln(line_h * 0.15)


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

    pdf = MeetingPDF()
    pdf.add_page()

    lines = meeting_text.strip().split("\n")
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

    parser = _HtmlParser()
    parser.feed(html_text)

    pdf = MeetingPDF()
    pdf.add_page()

    for block in parser.blocks:
        indent = 5 if block.tag == "li" else 0
        _render_block(pdf, block, indent=indent)

    pdf.output(str(output_path))
    return output_path
