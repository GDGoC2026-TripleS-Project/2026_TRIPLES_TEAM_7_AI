import re
import time
import io
import json
import pytesseract
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Tesseract 경로 설정 
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from extraction_ai.crawlers.base_crawler import BaseCrawler, JobPosting

class LinkareerCrawler(BaseCrawler):
    SITE_NAME = "linkareer"
    URL_PATTERNS = [
        r"https?://(www\.)?linkareer\.com/activity/\d+",
        r"https?://(www\.)?linkareer\.com/recruit/\d+",
        r"https?://(www\.)?linkareer\.com/list/recruit\?.+"
    ]

    def __init__(self, headless: bool = True, use_ocr: bool = False):
        super().__init__(headless=headless)
        self.use_ocr = use_ocr

    def _clean_html_text(self, html_content: str) -> str:
        if not html_content:
            return ""
        
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(separator="\n") 

        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()

    def is_valid_url(self, url: str) -> bool:
        return any(re.match(pattern, url) for pattern in self.URL_PATTERNS)

    def extract_job_posting(self, url: str) -> JobPosting:
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        summary_section = self.safe_find_element(By.CSS_SELECTOR, "div.activity-detail-content > section")
        summary_html = summary_section.get_attribute('innerHTML') if summary_section else ""
        summary_text = self._clean_html_text(summary_html)

        detail_section = self.safe_find_element(By.CSS_SELECTOR, "section[class*='ActivityDetailTabContent']")
        detail_html = detail_section.get_attribute('innerHTML') if detail_section else ""
        clean_detail_text = self._clean_html_text(detail_html)

        image_text_list = []
        if detail_section and self.use_ocr:
            images = detail_section.find_elements(By.TAG_NAME, "img")
            for idx, img in enumerate(images):
                try:
                    width = img.get_attribute("width") or img.value_of_css_property("width")
                    width_val = int(re.sub(r'[^0-9]', '', str(width or "0")))
                    
                    if width_val > 100:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", img)
                        time.sleep(1) 
                        raw_img_text = self._extract_with_ocr(img)
                        clean_img_text = self._clean_html_text(raw_img_text)
                        if clean_img_text:
                            image_text_list.append(clean_img_text)
                except: continue
        
        image_text = "\n\n".join(image_text_list)
        combined_content = f"[공고 요약]\n{summary_text}\n\n[상세 내용]\n{clean_detail_text}\n\n[이미지 텍스트]\n{image_text}"

        return JobPosting(
            original_url=url,
            raw_html="",
            site_name=self.SITE_NAME,
            role_text=combined_content,
            job_title=self._extract_simple_title(),
            company_name=self._extract_simple_company(),
        )

    def _extract_with_ocr(self, element) -> str:
        try:
            from PIL import Image
            img_data = element.screenshot_as_png
            image = Image.open(io.BytesIO(img_data))
            return pytesseract.image_to_string(image, lang='kor+eng', config='--psm 3')
        except:
            return ""

    def _extract_simple_title(self) -> str:
        for selector in ["h1", "[class*='title']", "[class*='Title']"]:
            elem = self.safe_find_element(By.CSS_SELECTOR, selector)
            if elem and elem.text.strip(): return elem.text.strip()
        return "Unknown Title"

    def _extract_simple_company(self) -> str:
        company_selectors = ["h2.organization-name", "article.organization-info h2", "div.organization-name"]
        for selector in company_selectors:
            elem = self.safe_find_element(By.CSS_SELECTOR, selector)
            if elem and elem.text.strip():
                name = elem.text.strip()
                if "링커리어" not in name: return name
        return "Unknown Company"

def crawl_linkareer_job(url: str, headless: bool = True, use_ocr: bool = False) -> Optional[JobPosting]:
    with LinkareerCrawler(headless=headless, use_ocr=use_ocr) as crawler:
        return crawler.crawl(url)

if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://linkareer.com/activity/300522"
    
    print(f"[PROCESS] Crawling: {test_url}")
    print("-" * 60)
    
    result = crawl_linkareer_job(test_url, headless=True, use_ocr=True)
    
    if result:
        file_path = "crawled_linkareer.jsonl"
        result_data = json.loads(result.to_json())
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result_data, ensure_ascii=False) + "\n")
    
        print(f"\n[SUCCESS] 데이터가 {file_path}에 저장!")
        print(f"직무: {result.job_title}")
        print(f"회사: {result.company_name}")
    else:
        print("\n[ERROR] 크롤링에 실패.")