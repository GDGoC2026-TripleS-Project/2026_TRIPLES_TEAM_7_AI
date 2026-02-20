import re
import time
import io
import json
import pytesseract
from datetime import datetime
from typing import Optional, List
from PIL import Image

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Tesseract 경로 설정 
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from crawlers.base_crawler import BaseCrawler, JobPosting

class JobKoreaCrawler(BaseCrawler):
    
    SITE_NAME = "jobkorea"
    URL_PATTERN = r"https?://(www\.)?jobkorea\.co\.kr/Recruit/GI_Read/\d+"
    
    def __init__(self, headless: bool = True, use_ocr: bool = True):
        super().__init__(headless=headless)
        self.use_ocr = use_ocr

    def is_valid_url(self, url: str) -> bool:
        return bool(re.match(self.URL_PATTERN, url))

    def _wait_for_content_area(self, timeout: int = 5) -> List:
        final_elements = []
        
        blocks = self.driver.find_elements(By.CSS_SELECTOR, "div[data-sentry-element='Block']")[:15]
        
        print(f"[INFO] 발견된 Block 개수: {len(blocks)}개")

        for b_idx, block in enumerate(blocks):
            try:                
                # Block 안의 섹션들 (모집 요강, 지원자격)
                sections = block.find_elements(By.CSS_SELECTOR, "div.styles_mt_space60__dk46ts37")
                if sections:
                    for s in sections[:3]:
                        s.selector_name = f"Block{b_idx}_Section"
                        final_elements.append(s)
                
                # Block 안의 details-section (상세 요강)
                try:
                    detail = block.find_element(By.CSS_SELECTOR, "#details-section, [details-section]")
                    detail.selector_name = f"Block{b_idx}_Details"
                    final_elements.append(detail)
                except: pass
                
                # application-section (접수기간·방법)
                try:
                    app_section = block.find_element(By.CSS_SELECTOR, "#application-section, [data-sentry-component='ApplyBox']")
                    app_section.selector_name = f"Block{b_idx}_Application"
                    final_elements.append(app_section)
                    print(f"[INFO] Block{b_idx}에서 접수기간·방법 섹션 발견")
                except: pass
                
            except: continue

        # 우측 사이드바
        try:
            sticky = self.driver.find_element(By.CSS_SELECTOR, "aside[class*='styles_position_sticky'] > div:first-of-type")
            sticky.selector_name = "Sticky_Summary"
            final_elements.append(sticky)
        except: pass
        
        try:
            app_section_global = self.driver.find_element(By.CSS_SELECTOR, "#application-section")
            if not any(hasattr(elem, 'selector_name') and elem.selector_name.endswith('_Application') for elem in final_elements):
                app_section_global.selector_name = "Global_Application"
                final_elements.append(app_section_global)
                print(f"[INFO] 전역에서 접수기간·방법 섹션 발견")
        except: pass

        return final_elements

    def _extract_job_title(self) -> str:
        selectors = [
            "[data-sentry-component='TitleContent']",
            "h1.tit",
            "div[data-sentry-component='TitleContent']"
        ]
        for s in selectors:
            elem = self.safe_find_element(By.CSS_SELECTOR, s)
            if elem and elem.text.strip():
                return elem.text.strip()
        return "제목 없음"

    def _extract_company_name(self) -> str:

        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-sentry-component='CompanyName']"))
            )

            selector = "div[data-sentry-component='CompanyName'] h2"
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            
            if element and element.text.strip():
                name = element.text.strip()
                print(f"[DEBUG] 정밀 경로 추출 성공: {name}")
                return name
                    
        except Exception as e:
            print(f"[DEBUG] CSS 셀렉터 실패 ({e}), XPath로 시도")

        try:
            xpath = "//div[@data-sentry-component='CompanyName']//h2"
            element = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            if element:
                name = element.text.strip()
                print(f"[DEBUG] XPath 추출 성공: {name}")
                return name
        except Exception as e:
            print(f"[DEBUG] XPath도 실패: {e}")

        try:
            company_link = self.driver.find_element(
                By.XPATH, 
                "//a[contains(@href, '/Recruit/Co_Read/')]//h2"
            )
            if company_link:
                name = company_link.text.strip()
                print(f"[DEBUG] 링크 기반 추출: {name}")
                return name
        except:
            pass

        return "Unknown Company"

    def _extract_text_from_images(self, container) -> str:
        texts = []
        try:
            images = container.find_elements(By.TAG_NAME, "img")
            for idx, img in enumerate(images):
                width = img.get_attribute("width") or img.value_of_css_property("width")
                try:
                    width_val = int(re.sub(r'[^0-9]', '', str(width or "0")))
                    if width_val > 100:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", img)
                        time.sleep(1)
                        img_data = img.screenshot_as_png
                        image = Image.open(io.BytesIO(img_data))
                        text = pytesseract.image_to_string(image, lang='kor+eng')
                        if text.strip():
                            print(f"  [SUCCESS] 이미지 추출 성공 ({len(text)}자)")
                            texts.append(text.strip())
                except: continue
        except Exception as e:
            print(f"[WARN] OCR 처리 중 오류: {e}")
        return "\n\n".join(texts)
    
    def _extract_text_from_element(self, element, idx=0) -> str:
        from PIL import Image
        import io
        
        try:
            req_w = self.driver.execute_script("return arguments[0].parentNode.scrollWidth", element)
            req_h = self.driver.execute_script("return arguments[0].scrollHeight", element)

            self.driver.set_window_size(req_w + 100, req_h + 500)
            time.sleep(2) 
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'start'});", element)
            time.sleep(1)
            
            img_data = element.screenshot_as_png
           
            self.driver.set_window_size(1920, 1080)

            image = Image.open(io.BytesIO(img_data))
            return pytesseract.image_to_string(image, lang='kor+eng', config='--psm 6').strip()
            
        except Exception as e:
            self.driver.set_window_size(1920, 1080)
            print(f"  [WARN] 영역 캡처/OCR 실패: {e}")
            return ""
            
    def extract_job_posting(self, url: str) -> JobPosting:
        time.sleep(10)
        
        print("[INFO] 회사명 및 직무명 추출 중...")
        company_name = self._extract_company_name()
        job_title = self._extract_job_title()
        print(f"[INFO] 추출 완료 - 회사: {company_name}, 직무: {job_title}")
 
        core_elements = self._wait_for_content_area()
        if not core_elements:
            print("[WARN] 지정 영역 탐색 실패. 상세요강 컨테이너로 대체.")
            backup = self.safe_find_element(By.CSS_SELECTOR, "div.lib_container")
            core_elements = [backup] if backup else [self.driver.find_element(By.TAG_NAME, "body")]

        all_role_texts = []
        all_image_texts = []

        for idx, area in enumerate(core_elements):
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", area)
            time.sleep(10)
            
            all_role_texts.append(area.text)
            if self.use_ocr:
                img_text = self._extract_text_from_images(area) 
                if not img_text or len(img_text.strip()) < 10:
                    print(f"[INFO] {idx+1}번 영역을 통째로 캡처하여 분석.")
                    img_text = self._extract_text_from_element(area)
                if img_text:
                    all_image_texts.append(img_text)

        role_text_joined = "\n".join(all_role_texts)
        image_text_joined = "\n".join(all_image_texts)

        combined_content = f"""
    [잡코리아 지정 영역 데이터]
    {role_text_joined}

    [공고 이미지 추출 상세내용]
    {image_text_joined}
        """.strip()

        return JobPosting(
            original_url=url,
            raw_html="",  
            site_name=self.SITE_NAME,
            role_text=combined_content,
            job_title=job_title,
            company_name=company_name
        )

def crawl_jobkorea_job(url: str, headless: bool = True, use_ocr: bool = True) -> Optional[JobPosting]:
    with JobKoreaCrawler(headless=headless, use_ocr=use_ocr) as crawler:
        return crawler.crawl(url)

if __name__ == "__main__":
    test_url = "https://www.jobkorea.co.kr/Recruit/GI_Read/48499484?Oem_Code=C1&rPageCode=TL"
    print(f"[TEST] JobKorea Crawling: {test_url}")
    
    result = crawl_jobkorea_job(test_url, headless=True, use_ocr=True)
    
    if result:
        file_path = "crawled_jobkorea.jsonl"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(json.loads(result.to_json()), ensure_ascii=False) + "\n")
        print(f"\n[SUCCESS] '{result.job_title}' 데이터가 {file_path}에 저장!")
    else:
        print("[ERROR] 크롤링 실패")