import os
import re
import io
import logging
from typing import Callable, Optional

from PIL import Image
import ebooklib
from ebooklib import epub

logger = logging.getLogger("EPUBBuilder")

class OCRToEpubBuilder:
    """
    캡처된 PNG 이미지들을 읽어서 EasyOCR로 한글/영어 텍스트를 추출하고,
    표준 EPUB (.epub) 전자책 파일 및 TXT (.txt) 문서로 변환 생성하는 모듈입니다.
    """

    def __init__(self):
        self._reader = None

    def _get_ocr_reader(self):
        """EasyOCR 인스턴스 지연 생성 (GPU/CPU 호환)"""
        if self._reader is None:
            import easyocr
            # 한국어(ko) 및 영어(en) 인식 지원
            self._reader = easyocr.Reader(['ko', 'en'], gpu=False)
        return self._reader

    def convert_images_to_epub(self, image_paths: list[str], title: str, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> tuple[str, str]:
        """
        :param image_paths: 사용자가 갤러리에서 선택한 PNG 이미지 파일들의 절대 경로 리스트
        :param title: 전자책 제목
        :param progress_callback: (현재 index, 전체 count, 메시지) 형태의 진행 상황 콜백
        :return: (생성된 epub 파일 절대 경로, 생성된 txt 파일 절대 경로)
        """
        if not image_paths:
            raise ValueError("선택된 이미지가 없습니다.")

        reader = self._get_ocr_reader()

        # EPUB 구조 생성
        book = epub.EpubBook()
        book.set_identifier(f"antigravity-{title}")
        book.set_title(title)
        book.set_language("ko")
        book.add_author("Antigravity Screen Capture")

        chapters = []
        full_text_list = []
        total_files = len(image_paths)

        # 기본 CSS 스타일 추가
        style = '''
        @namespace url('http://www.w3.org/1999/xhtml');
        body { font-family: 'Malgun Gothic', 'NanumGothic', sans-serif; line-height: 1.6; padding: 10px; }
        h1 { text-align: center; color: #1a202c; border-bottom: 2px solid #3182ce; padding-bottom: 10px; }
        .page-img { max-width: 100%; height: auto; display: block; margin: 15px auto; border: 1px solid #e2e8f0; border-radius: 4px; }
        .ocr-text { margin-top: 15px; font-size: 1.05em; color: #2d3748; text-align: justify; word-break: keep-all; }
        .page-num { text-align: right; color: #a0aec0; font-size: 0.85em; margin-top: 20px; }
        '''
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        book.add_item(nav_css)

        for i, img_path in enumerate(png_files, start=1):
            fname = os.path.basename(img_path)
            if progress_callback:
                progress_callback(i, total_files, f"OCR 텍스트 추출 중 ({i}/{total_files}): {fname}")

            # 1. PIL + numpy로 이미지 읽기 (한글 파일 경로 인코딩 문제 완벽 방지)
            try:
                import numpy as np
                with Image.open(img_path) as pil_img:
                    np_img = np.array(pil_img.convert("RGB"))
                results = reader.readtext(np_img, detail=0)
                extracted_text = "\n".join(results)
            except Exception as e:
                logger.error(f"OCR Error for {fname}: {e}")
                extracted_text = f"(OCR 인식 내용 없음)"

            full_text_list.append(f"=== Page {i} [{fname}] ===\n{extracted_text}\n")

            # 2. 이미지 EPUB 항목 등록
            img_item_filename = f"images/page_{i:03d}.png"
            with open(img_path, "rb") as f_img:
                img_data = f_img.read()
            epub_img = epub.EpubItem(
                uid=f"img_{i:03d}",
                file_name=img_item_filename,
                media_type="image/png",
                content=img_data
            )
            book.add_item(epub_img)

            # 3. EPUB HTML 챕터 생성
            c = epub.EpubHtml(title=f"Page {i}", file_name=f"page_{i:03d}.xhtml", lang="ko")
            
            # HTML 문단 구성
            paragraphs_html = "".join([f"<p class='ocr-text'>{p}</p>" for p in extracted_text.split("\n") if p.strip()])
            
            html_content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title} - Page {i}</title>
    <link rel="stylesheet" href="style/nav.css" type="text/css" />
</head>
<body>
    <div class="page-container">
        <h1>{title} - Page {i}</h1>
        <img class="page-img" src="{img_item_filename}" alt="Page {i}" />
        <hr/>
        <div class="text-container">
            {paragraphs_html}
        </div>
        <div class="page-num">- Page {i} -</div>
    </div>
</body>
</html>'''

            c.set_content(html_content.encode('utf-8'))
            c.add_item(nav_css)
            book.add_item(c)
            chapters.append(c)

        # 4. EPUB 목차 및 Spine 설정
        book.toc = tuple(chapters)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = ['nav'] + chapters

        # 5. 파일 저장 (.epub 및 .txt)
        epub_filename = f"{title}.epub"
        epub_filepath = os.path.join(folder_path, epub_filename)
        epub.write_epub(epub_filepath, book, {})

        txt_filename = f"{title}_extracted.txt"
        txt_filepath = os.path.join(folder_path, txt_filename)
        with open(txt_filepath, "w", encoding="utf-8") as f_txt:
            f_txt.write(f"[{title}] OCR Extracted Text Document\n")
            f_txt.write("=" * 60 + "\n\n")
            f_txt.write("\n".join(full_text_list))

        if progress_callback:
            progress_callback(total_files, total_files, f"EPUB 및 TXT 전자책 변환 완료! -> {epub_filename}")

        return epub_filepath, txt_filepath

    def convert_folder_to_epub(self, folder_path: str, title: str, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> tuple[str, str]:
        """
        :param folder_path: PNG 이미지들이 저장된 디렉토리 경로
        :param title: 전자책 제목
        :param progress_callback: 진행 상황 콜백
        """
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"지정된 폴더를 찾을 수 없습니다: {folder_path}")

        pattern = re.compile(rf"^{re.escape(title)}_(\d+)\.png$", re.IGNORECASE)
        png_files = []
        for fname in sorted(os.listdir(folder_path)):
            if pattern.match(fname) or fname.lower().endswith(".png"):
                png_files.append(os.path.join(folder_path, fname))

        if not png_files:
            raise ValueError(f"'{title}' 폴더에서 캡처된 PNG 이미지를 찾지 못했습니다.")

        return self.convert_images_to_epub(png_files, title, progress_callback)
