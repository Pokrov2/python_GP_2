from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import pandas as pd, time, random, re, logging
from urllib.parse import quote
from datetime import datetime, timedelta
from collections import Counter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'scraper_{datetime.now().strftime("%Y%m%d_%H%M")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

def setup_driver():
    logger.info("Запуск браузера Chrome")
    o = Options()
    o.add_argument("--log-level=3")
    o.add_argument("--silent")
    o.add_argument("--disable-logging")
    o.add_argument("--disable-dev-tools")
    o.add_experimental_option('excludeSwitches', ['enable-logging'])
    o.add_argument("--disable-blink-features=AutomationControlled")
    o.add_experimental_option("excludeSwitches", ["enable-automation"])
    o.add_experimental_option('useAutomationExtension', False)
    o.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    o.add_argument("--start-maximized")
    d = webdriver.Chrome(options=o)
    d.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return d

def extract_salary_with_period(t):
    if not t or t == "N/A": return "N/A"
    t = re.sub(r'\s+', ' ', t.strip())
    p = ""
    if re.search(r'year|annual|yr', t, re.I): p = "a year"
    elif re.search(r'hour|hr', t, re.I): p = "an hour"
    s = "N/A"
    for pat in [r'\$\d{1,3}(?:,\d{3})*(?:\s*-\s*\$\d{1,3}(?:,\d{3})*)?', r'\$\d{1,3}(?:,\d{3})*', r'\d{1,3}(?:,\d{3})*\s*[kK]']:
        m = re.findall(pat, t, re.I)
        if m: s = max(m, key=len); break
    if s != "N/A" and not p:
        if re.search(r'\d{3,}|k', s, re.I): p = "a year"
        elif re.search(r'\$\d{1,2}', s): p = "an hour"
    return f"{s} {p}" if s != "N/A" else "N/A"

def extract_location(t):
    if not t or t == "N/A": return "N/A"
    for f in ['Remote', 'Hybrid', 'On-site', 'Work From Home']:
        t = re.sub(r'\b'+f+r'\b','',t,flags=re.I)
    t = re.sub(r'\s+', ' ', t).strip()
    return t if t else "N/A"

def extract_work_format(t):
    if not t or t == "N/A": return "Not specified"
    m = {'Remote':['Remote','WFH'],'Hybrid':['Hybrid'],'On-site':['On-site','Office']}
    for k,v in m.items():
        for x in v:
            if re.search(r'\b'+x+r'\b',t,re.I): return k
    return "Not specified"

def convert_simplyhired_date(t):
    if not t or t == "N/A": 
        return "N/A"
    n = datetime.now()
    t = t.strip().lower()
    if t in ['just posted', 'today', 'now']:
        return n.strftime("%Y-%m-%d")
    m = re.match(r'(\d+)([dhmw])', t)
    if not m:
        return "N/A"
    num, u = int(m.group(1)), m.group(2)
    if u == 'h':
        d = n - timedelta(hours=num)
    elif u == 'd':
        d = n - timedelta(days=num)
    elif u == 'w':
        d = n - timedelta(weeks=num)
    elif u == 'm':
        d = n - timedelta(days=30 * num)
    else:
        return "N/A"
    return d.strftime("%Y-%m-%d")

def extract_posted_date(e):
    for s in ["[data-testid='searchSerpJobDateStamp']","[class*='date']","[class*='posted']"]:
        try:
            t = e.find_element(By.CSS_SELECTOR, s).text.strip()
            if t: return convert_simplyhired_date(t)
        except: continue
    return "N/A"

def extract_job_url(e):
    for s in ["[data-testid='searchSerpJobTitle']","h2 a","a[href*='/job/']"]:
        try:
            u = e.find_element(By.CSS_SELECTOR, s).get_attribute('href')
            if u: return f"https://www.simplyhired.com{u}" if u.startswith('/') else u
        except: continue
    return "N/A"

def is_location_in_top_states(t):
    if not t or t == "N/A": return False
    l = t.lower()
    s = ['california','ca','texas','tx','florida','fl','new york','ny','pennsylvania','pa','illinois','il','ohio','oh','georgia','ga','north carolina','nc','michigan','mi']
    u = ['remote','united states','usa','us','anywhere','work from home','virtual']
    return any(x in l for x in s+u)

def extract_qualifications(e):
    for s in ["[data-testid='searchSerpJobSnippet']","[class*='description']"]:
        try:
            t = e.find_element(By.CSS_SELECTOR, s).text.strip()
            if t: break
        except: continue
    else: return "N/A"
    skills = ['python','java','sql','aws','react','docker','linux','azure','flask','django','ml','ai','devops','git']
    found = [x for x in skills if x in t.lower()]
    p = [r'\d+\+?\s*years?\s*experience',r'bachelor',r'master',r'phd']
    for r_ in p: found += re.findall(r_, t.lower())
    if found:
        f = list(set(found))[:15]
        res = ", ".join(f)
        return res[:297]+"..." if len(res)>300 else res
    return "N/A"

def click_job_and_get_detail_salary(driver):
    try:
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='viewJobBodyContainer'],[data-testid='viewJobButton']"))
        )
    except Exception as e:
        logger.debug(f"Ожидание деталей вакансии превышено: {e}")

    selectors = [
        "[data-testid='viewJobBodyJobCompensation'] [data-testid='detailText']",
        "[data-testid*='viewJobBodyJobDetailsContainer'] [data-testid='detailText']",
    ]
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            txt = el.text.strip()
            if txt and '$' in txt:
                logger.debug(f"Найдена зарплата в деталях: {txt}")
                return txt
        except Exception as e:
            logger.debug(f"Не удалось найти зарплату в {sel}: {e}")

    try:
        el = driver.find_element(By.XPATH, "//*[contains(@data-icon,'dollar-sign')]/ancestor::*[contains(@data-testid,'viewJobBodyJobCompensation')][1]//span[@data-testid='detailText']")
        txt = el.text.strip()
        if txt:
            logger.debug(f"Найдена зарплата через XPath: {txt}")
            return txt
    except Exception as e:
        logger.debug(f"Не удалось найти зарплату через XPath: {e}")
    return "N/A"

def open_job_card(driver, card):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
        card.click()
        logger.debug("Успешный клик по карточке вакансии")
    except Exception as e:
        logger.warning(f"Ошибка клика по карточке: {e}")
        try:
            driver.execute_script("arguments[0].click();", card)
            logger.debug("Клик выполнен через JavaScript")
        except Exception as e:
            logger.error(f"Не удалось кликнуть по карточке: {e}")
    
    time.sleep(random.uniform(0.3, 0.8))

def parse_single_query(q, num=100):
    d = setup_driver(); data = []; urls=set(); pg=1
    logger.info(f"Начало парсинга запроса: {q}")
    d.get(f"https://www.simplyhired.com/search?q={quote(q)}")
    time.sleep(3)
    while len(data)<num and pg<=300:
        try:
            WebDriverWait(d,10).until(EC.presence_of_element_located((By.CSS_SELECTOR,"[data-testid='searchSerpJob'],.SerpJob,.card")))
            jobs = d.find_elements(By.CSS_SELECTOR,"[data-testid='searchSerpJob'],.SerpJob,.card")
            logger.debug(f"Страница {pg}: найдено {len(jobs)} вакансий")
            
            for j in jobs:
                if len(data)>=num: break
                u=extract_job_url(j)
                if u=="N/A" or u in urls: continue
                urls.add(u)
                try: t=j.find_element(By.CSS_SELECTOR,"h2, h3").text.strip()
                except: t="N/A"
                try: c=j.find_element(By.CSS_SELECTOR,"[data-testid='companyName']").text.strip()
                except: c="N/A"
                try: l=j.find_element(By.CSS_SELECTOR,"[data-testid='searchSerpJobLocation']").text.strip()
                except: l="N/A"
                if not is_location_in_top_states(l): 
                    logger.debug(f"Пропуск вакансии (локация не в топе): {t}")
                    continue

                try:
                    s=j.find_element(By.CSS_SELECTOR,"[data-testid='searchSerpJobSalary']").text.strip()
                except:
                    s="N/A"

                if s=="N/A" or not s:
                    logger.debug(f"Поиск зарплаты в деталях для: {t}")
                    open_job_card(d, j)
                    s = click_job_and_get_detail_salary(d)

                p=extract_posted_date(j)
                qf=extract_qualifications(j)

                data.append({
                    "Title":t,"Company":c,"Location":extract_location(l),"Work_Format":extract_work_format(l),
                    "Salary":extract_salary_with_period(s),"URL":u,"Posted_Date":p,"Qualifications":qf,
                    "Search_Query":q,"Parsing_Date":datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                logger.debug(f"Добавлена вакансия: {t} - {c}")
                
            pg+=1
            nexts=d.find_elements(By.CSS_SELECTOR,"[data-testid^='paginationBlock']")
            for n in nexts:
                id_=n.get_attribute("data-testid")
                m=re.search(r'paginationBlock(\d+)',id_ or "")
                if m and int(m.group(1))==pg:
                    h=n.get_attribute("href")
                    if h: 
                        logger.debug(f"Переход на страницу {pg}")
                        d.get(h); time.sleep(3); break
        except TimeoutException as e:
            logger.warning(f"Таймаут на странице {pg}: {e}")
            break
        except Exception as e:
            logger.error(f"Ошибка на странице {pg}: {e}")
            break
            
    d.quit()
    logger.info(f"Запрос '{q}': собрано {len(data)} вакансий")
    return pd.DataFrame(data)

def parse_multiple_queries(queries, n=100):
    logger.info(f"Запуск парсинга {len(queries)} запросов")
    all_=[]
    for q in queries:
        df=parse_single_query(q,n)
        if len(df)>0: all_.append(df)
        time.sleep(random.uniform(5,10))
    logger.info(f"Всего собрано вакансий: {sum(len(df) for df in all_)}")
    return pd.concat(all_,ignore_index=True) if all_ else pd.DataFrame()

def save_with_statistics(df, f):
    if len(df) == 0:
        logger.warning("Нет данных для сохранения")
        return
    df.to_csv(f, index=False)
    logger.info(f"Данные сохранены в файл: {f}")


SEARCH_QUERIES=['data scientist', 'data analyst', 'data engineer',
    'data analyst', 'data engineer', 'machine learning',
    'machine learning', 'ml engineer', 'AI developer',
    'artificial intelligence', 'neural networks', 'computer vision',
    'big data', 'sql analyst', 'bi analyst', 'product analyst',
    'junior data analyst', 'middle data analyst',
    'senior data analyst', 'junior data engineer',
    'middle data engineer', 'senior data engineer',
    'python developer', 'python developer',
    'junior python developer', 'middle python developer',
    'senior python developer', 'backend developer',
    'frontend developer', 'fullstack developer', 'java developer',
    'c# developer', 'c++ developer', 'javascript developer',
    'go developer', 'golang developer', 'kotlin developer',
    'system administrator', 'CRM', 'CRM programmer',
    'CRM developer', 'junior CRM', 'middle CRM', 'senior CRM',
    'junior data analyst', 'backend developer', 'backend developer',
    'javascript developer', 'javascript developer',
    'middle system administrator', 'c++ developer',
    'middle frontend developer', 'middle c++ developer',
    'kotlin developer', 'senior backend developer',
    'junior system administrator', 'senior system administrator',
    'middle python developer']

if __name__=="__main__":
    start=time.time()
    logger.info("=== ЗАПУСК СКРИПТА ===")
    df=parse_multiple_queries(SEARCH_QUERIES,300)
    if len(df)>0:
        fn=f"vacancies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        save_with_statistics(df,fn)
        logger.info(f"УСПЕШНО: {len(df)} вакансий за {time.time()-start:.1f} сек")
    else: 
        logger.error("ЗАВЕРШЕНО: нет данных")
    logger.info("=== ЗАВЕРШЕНИЕ СКРИПТА ===")