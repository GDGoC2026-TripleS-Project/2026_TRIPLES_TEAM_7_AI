from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime
import json
import time
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


@dataclass
class JobPosting:

    original_url: str                    # 원본 URL
    site_name: str                       # 사이트명 (wanted, jobkorea, linkareer)
    raw_html: str                        # 원본 HTML

    job_title: Optional[str] = None              # 직무명
    company_name: Optional[str] = None           # 회사명
    employment_type: Optional[str] = None        # 고용형태
    role_text: Optional[str] = None              # 업무 설명 요약
    necessary_stack: Optional[List[str]] = None  # 필요 스킬
    prefer_stack: Optional[List[str]] = None     # 우대 스킬
    experience_level: Optional[str] = None       # 경력 요구사항
    salary_text: Optional[str] = None            # 연봉
    work_day: Optional[str] = None               # 근무일
    location_text: Optional[str] = None          # 주소
    deadline_at: Optional[str] = None            # 마감일
    
    def to_dict(self):
        return asdict(self)
    
    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class BaseCrawler(ABC):
    
    SITE_NAME: str = "base"
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        options = Options()
        
        if self.headless:
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        self.driver = webdriver.Chrome(options=options) # 경로/Service 지정 불필요
        self.wait = WebDriverWait(self.driver, 10)
        self.wait = WebDriverWait(self.driver, 10)
        
    def close_driver(self):
        if self.driver:
            self.driver.quit()
            
    def __enter__(self):
        self.setup_driver()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_driver()
        
    @abstractmethod
    def is_valid_url(self, url: str) -> bool:
        pass
    
    @abstractmethod
    def extract_job_posting(self, url: str) -> JobPosting:
        pass
    
    def crawl(self, url: str) -> Optional[JobPosting]:
        if not self.is_valid_url(url):
            print(f"[ERROR] Invalid URL for {self.SITE_NAME}: {url}")
            return None
            
        try:
            self.driver.get(url)
            time.sleep(2)  
            return self.extract_job_posting(url)
        except Exception as e:
            print(f"[ERROR] Failed to crawl {url}: {e}")
            return None
            
    def wait_for_element(self, by: By, value: str, timeout: int = 10):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None
            
    def safe_find_element(self, by: By, value: str):
        try:
            return self.driver.find_element(by, value)
        except NoSuchElementException:
            return None
            
    def safe_find_elements(self, by: By, value: str):
        try:
            return self.driver.find_elements(by, value)
        except NoSuchElementException:
            return []
            
    def get_text_or_none(self, by: By, value: str) -> Optional[str]:
        element = self.safe_find_element(by, value)
        return element.text.strip() if element else None


def save_job_postings(postings: List[JobPosting], output_path: str):
    if not postings:
        return

    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for posting in postings:
            json_line = json.dumps(posting.to_dict(), ensure_ascii=False)
            f.write(json_line + '\n')
            
    print(f"[INFO] Saved {len(postings)} job postings to {output_path}")


if __name__ == "__main__":
    posting = JobPosting(
        original_url="https://example.com/job/123",
        site_name="test",
        raw_html="<html>...</html>",
        job_title="Backend Developer",
        company_name="Test Company"
    )
    print(posting.to_json())