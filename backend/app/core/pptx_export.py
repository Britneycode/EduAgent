from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


@dataclass(frozen=True)
class ParsedSlide:
    title: str
    bullets: list[str]
    notes: str = ""


def parse_ppt_outline(content: str, fallback_title: str) -> list[ParsedSlide]:
    """Parse EduAgent PPT markdown into slide objects."""
    normalized = content.strip()
    if not normalized:
        return [ParsedSlide(title=fallback_title, bullets=["暂无内容"])]

    heading_pattern = re.compile(
        r"(?:^|\n)#{1,3}\s*第?\s*(\d+)\s*页[：:.]?\s*(.*)"
    )
    matches = list(heading_pattern.finditer(normalized))
    if len(matches) >= 2:
        slides: list[ParsedSlide] = []
        for index, match in enumerate(matches):
            title = match.group(2).strip() or f"第 {match.group(1)} 页"
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
            slides.append(_section_to_slide(title, normalized[start:end]))
        return slides

    sections = re.split(r"\n-{3,}\n", normalized)
    if len(sections) >= 2:
        return [_raw_section_to_slide(section, index) for index, section in enumerate(sections)]

    return [_section_to_slide(fallback_title, normalized)]


def build_pptx(title: str, content: str) -> bytes:
    """Build a small but valid .pptx deck from markdown outline content."""
    slides = parse_ppt_outline(content, fallback_title=title)
    buffer = BytesIO()

    with ZipFile(buffer, "w", ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", _content_types_xml(len(slides)))
        package.writestr("_rels/.rels", _root_rels_xml())
        package.writestr("ppt/presentation.xml", _presentation_xml(len(slides)))
        package.writestr("ppt/_rels/presentation.xml.rels", _presentation_rels_xml(len(slides)))
        package.writestr("ppt/theme/theme1.xml", _theme_xml())
        package.writestr("ppt/slideMasters/slideMaster1.xml", _slide_master_xml())
        package.writestr(
            "ppt/slideMasters/_rels/slideMaster1.xml.rels",
            _slide_master_rels_xml(),
        )
        package.writestr("ppt/slideLayouts/slideLayout1.xml", _slide_layout_xml())
        package.writestr(
            "ppt/slideLayouts/_rels/slideLayout1.xml.rels",
            _slide_layout_rels_xml(),
        )
        package.writestr("docProps/core.xml", _core_props_xml(title))
        package.writestr("docProps/app.xml", _app_props_xml(len(slides)))

        for index, slide in enumerate(slides, start=1):
            package.writestr(f"ppt/slides/slide{index}.xml", _slide_xml(slide, index))
            package.writestr(
                f"ppt/slides/_rels/slide{index}.xml.rels",
                _slide_rels_xml(),
            )

    return buffer.getvalue()


def _raw_section_to_slide(section: str, index: int) -> ParsedSlide:
    lines = [line.strip() for line in section.strip().splitlines() if line.strip()]
    if not lines:
        return ParsedSlide(title=f"第 {index + 1} 页", bullets=["暂无内容"])
    title = _clean_text(re.sub(r"^#+\s*", "", lines[0])) or f"第 {index + 1} 页"
    return _section_to_slide(title, "\n".join(lines[1:]))


def _section_to_slide(title: str, body: str) -> ParsedSlide:
    bullets: list[str] = []
    notes: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        cleaned = _clean_text(line)
        if not cleaned:
            continue
        if cleaned.startswith(("备注", "演讲备注", "讲者备注")):
            notes.append(cleaned)
            continue
        bullets.append(cleaned)

    return ParsedSlide(title=_clean_text(title), bullets=bullets[:7] or ["暂无内容"], notes="\n".join(notes))


def _clean_text(value: str) -> str:
    value = re.sub(r"^[-*+]\s+", "", value.strip())
    value = re.sub(r"^\d+[.)、]\s*", "", value)
    value = value.replace("**", "").replace("__", "").replace("`", "")
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    return value.strip()


def _safe_xml(value: str) -> str:
    return escape(value, {"'": "&apos;", '"': "&quot;"})


def _content_types_xml(slide_count: int) -> str:
    slide_overrides = "\n".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, slide_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  {slide_overrides}
</Types>'''


def _root_rels_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''


def _presentation_xml(slide_count: int) -> str:
    slide_ids = "\n".join(
        f'<p:sldId id="{255 + i}" r:id="rId{i}"/>' for i in range(1, slide_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId{slide_count + 1}"/></p:sldMasterIdLst>
  <p:sldIdLst>{slide_ids}</p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000" type="screen16x9"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>'''


def _presentation_rels_xml(slide_count: int) -> str:
    relationships = [
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, slide_count + 1)
    ]
    relationships.append(
        f'<Relationship Id="rId{slide_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
    )
    relationships.append(
        f'<Relationship Id="rId{slide_count + 2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>'
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {"".join(relationships)}
</Relationships>'''


def _slide_xml(slide: ParsedSlide, index: int) -> str:
    bg_color = "3D3529" if index == 1 else "FAF9F5"
    title_color = "FFFFFF" if index == 1 else "2A2820"
    body_color = "E8E0D4" if index == 1 else "5C5849"
    bullet_paragraphs = "\n".join(
        f'''<a:p><a:pPr marL="285750" indent="-171450"><a:buChar char="•"/><a:defRPr sz="2200"/></a:pPr><a:r><a:rPr lang="zh-CN" sz="2200"><a:solidFill><a:srgbClr val="{body_color}"/></a:solidFill></a:rPr><a:t>{_safe_xml(item)}</a:t></a:r></a:p>'''
        for item in slide.bullets
    )
    notes = f"EduAgent 教学演示 · 第 {index} 页"
    if slide.notes:
        notes = f"{notes} · {slide.notes[:60]}"
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="{bg_color}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="685800" y="548640"/><a:ext cx="10820400" cy="914400"/></a:xfrm></p:spPr>
        <p:txBody><a:bodyPr wrap="square"/><a:lstStyle/><a:p><a:r><a:rPr lang="zh-CN" sz="3600" b="1"><a:solidFill><a:srgbClr val="{title_color}"/></a:solidFill></a:rPr><a:t>{_safe_xml(slide.title)}</a:t></a:r></a:p></p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="3" name="Body"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="914400" y="1737360"/><a:ext cx="10058400" cy="4023360"/></a:xfrm></p:spPr>
        <p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>{bullet_paragraphs}</p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="4" name="Footer"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="685800" y="6217920"/><a:ext cx="10820400" cy="274320"/></a:xfrm></p:spPr>
        <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="zh-CN" sz="1100"><a:solidFill><a:srgbClr val="{body_color}"/></a:solidFill></a:rPr><a:t>{_safe_xml(notes)}</a:t></a:r></a:p></p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>'''


def _slide_rels_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>'''


def _slide_master_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
  <p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>
</p:sldMaster>'''


def _slide_master_rels_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>'''


def _slide_layout_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>'''


def _slide_layout_rels_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>'''


def _theme_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="EduAgent">
  <a:themeElements>
    <a:clrScheme name="EduAgent"><a:dk1><a:srgbClr val="2A2820"/></a:dk1><a:lt1><a:srgbClr val="FAF9F5"/></a:lt1><a:dk2><a:srgbClr val="3D3529"/></a:dk2><a:lt2><a:srgbClr val="F5F4ED"/></a:lt2><a:accent1><a:srgbClr val="C96442"/></a:accent1><a:accent2><a:srgbClr val="6B8E6B"/></a:accent2><a:accent3><a:srgbClr val="6B7A8E"/></a:accent3><a:accent4><a:srgbClr val="9B6B4A"/></a:accent4><a:accent5><a:srgbClr val="8E6B7A"/></a:accent5><a:accent6><a:srgbClr val="7A6E5D"/></a:accent6><a:hlink><a:srgbClr val="C96442"/></a:hlink><a:folHlink><a:srgbClr val="8E6B7A"/></a:folHlink></a:clrScheme>
    <a:fontScheme name="EduAgent"><a:majorFont><a:latin typeface="Georgia"/><a:ea typeface="Microsoft YaHei"/></a:majorFont><a:minorFont><a:latin typeface="Calibri"/><a:ea typeface="Microsoft YaHei"/></a:minorFont></a:fontScheme>
    <a:fmtScheme name="EduAgent"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
  </a:themeElements>
</a:theme>'''


def _core_props_xml(title: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{_safe_xml(title)}</dc:title>
  <dc:creator>EduAgent</dc:creator>
  <cp:lastModifiedBy>EduAgent</cp:lastModifiedBy>
</cp:coreProperties>'''


def _app_props_xml(slide_count: int) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>EduAgent</Application>
  <PresentationFormat>On-screen Show (16:9)</PresentationFormat>
  <Slides>{slide_count}</Slides>
  <Company>EduAgent</Company>
</Properties>'''
