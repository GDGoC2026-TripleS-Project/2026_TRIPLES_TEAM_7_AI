import re
import time
import io
import json
import pytesseract
from datetime import datetime
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Tesseract 경로 설정 
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from crawlers.base_crawler import BaseCrawler, JobPosting

class WantedCrawler(BaseCrawler):    
    SITE_NAME = "wanted"
    URL_PATTERN = r"https?://(www\.)?wanted\.co\.kr/wd/\d+"
    
    def __init__(self, headless: bool = True, use_ocr: bool = True):
        super().__init__(headless=headless)
        self.use_ocr = use_ocr

    def is_valid_url(self, url: str) -> bool:
        return bool(re.match(self.URL_PATTERN, url))

    def extract_job_posting(self, url: str) -> JobPosting:
        time.sleep(2)

        self._expand_job_description()
        self.driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)

        content_wrapper = self._wait_for_content_wrapper()
        
        if not content_wrapper:
            print("[WARN] 핵심 영역을 찾지 못해 전체 페이지 수집.")
            content_wrapper = self.driver.find_element(By.TAG_NAME, "body")
        
        raw_text = content_wrapper.text
      
        image_text = ""
        if self.use_ocr:
            image_text = self._extract_text_from_images(content_wrapper)

        combined_content = f"""
[공고 원본 텍스트]
{raw_text}

[이미지 추출 텍스트 (OCR)]
{image_text}

[SOURCE_URL]: {url}
        """.strip()

        return JobPosting(
            original_url=url,
            raw_html="", 
            site_name=self.SITE_NAME,
            role_text=combined_content, 
            job_title=self._extract_job_title(),
            company_name=self._extract_company_name()
        )
    
    def _expand_job_description(self):
        expand_selectors = [
            "button[class*='JobDescription_expand']",
            "section[class*='JobDescription'] button",
            "//button[contains(text(), '상세 정보 더보기')]",
            "//span[contains(text(), '더 보기')]/.."
        ]
        
        for selector in expand_selectors:
            try:
                if selector.startswith("//"):
                    button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                else:
                    button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                
                # 버튼으로 스크롤 후 클릭
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", button)
                print("[INFO] '상세 정보 더보기' 버튼 클릭.")
                time.sleep(1) 
                return
            except:
                continue

    def _wait_for_content_wrapper(self, timeout: int = 10):
        selectors = ["section[class*='JobContent']"]
        for selector in selectors:
            try:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if element: return element
            except: continue
        return None

    def _extract_job_title(self) -> str:
        selectors = ["h1[class*='JobHeader']", "h2[class*='JobHeader']", "h1"]
        for s in selectors:
            elem = self.safe_find_element(By.CSS_SELECTOR, s)
            if elem and elem.text.strip(): return elem.text.strip()
        return "Unknown Title"

    def _extract_company_name(self) -> str:
        selectors = ["a[data-attribute-id='company__click']", "h1[class*='JobHeader'] + div a", "[class*='company-name']"]
        for s in selectors:
            elem = self.safe_find_element(By.CSS_SELECTOR, s)
            if elem and elem.text.strip(): return elem.text.strip()
        return "Unknown Company"

    def _extract_text_from_images(self, container) -> str:
        from PIL import Image
        texts = []
        try:
            images = container.find_elements(By.TAG_NAME, "img")
            for idx, img in enumerate(images):
                width = img.get_attribute("width") or img.value_of_css_property("width")
                try:
                    width_val = int(re.sub(r'[^0-9]', '', str(width or "0")))
                    if width_val > 200:
                        img_data = img.screenshot_as_png
                        image = Image.open(io.BytesIO(img_data))
                        text = pytesseract.image_to_string(image, lang='kor+eng')
                        if text.strip():
                            print(f"[SUCCESS] 이미지 {idx+1}번 추출 완료")
                            texts.append(text.strip())
                except: continue
        except Exception as e:
            print(f"[WARN] 이미지 OCR 실패: {e}")
        return "\n\n".join(texts)

def crawl_wanted_job(url: str, headless: bool = True, use_ocr: bool = True) -> Optional[JobPosting]:
    with WantedCrawler(headless=headless, use_ocr=use_ocr) as crawler:
        return crawler.crawl(url)

if __name__ == "__main__":
    test_url = "https://www.wanted.co.kr/wd/340708"
    print(f"[TEST] Wanted Crawling: {test_url}")
    
    result = crawl_wanted_job(test_url, headless=True, use_ocr=True)
    
    if result:
        file_path = "crawled_wanted.jsonl"
        result_data = json.loads(result.to_json())
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result_data, ensure_ascii=False) + "\n")
        print(f"\n[SUCCESS] '{result.job_title}' 데이터가 {file_path}에 저장!")
    else:
        print("[ERROR] 크롤링 실패")