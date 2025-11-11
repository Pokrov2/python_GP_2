import requests
import pandas as pd
import time

output_file = "only_asdasdasaсссссвsd.csv"
flag = False
cities = {
    1: "Москва",
    2: "Санкт-Петербург",
    4: "Новосибирск",
    3: "Екатеринбург",
    88: "Казань",
    54: "Красноярск",
    66: "Нижний Новгород",
    104: "Челябинск",
    99: "Уфа",
    53: "Краснодар"
}

queries = [
    "data scientist",
    "data analyst",
    "data engineer",
    "аналитик данных",
    "инженер данных",
    "machine learning",
    "машинное обучение",
    "ml engineer",
    "AI developer",
    "искусственный интеллект",
    "нейронные сети",
    "computer vision",
    "big data",
    "sql аналитик",
    "bi analyst",
    "product analyst",
    "junior data scientist",
    "middle data scientist",
    "senior data scientist",
    "junior data analyst",
    "middle data analyst",
    "senior data analyst",
    "junior data engineer",
    "middle data engineer",
    "senior data engineer",
    "junior аналитик данных",
    "middle аналитик данных",
    "senior аналитик данных",
    "junior инженер данных",
    "middle инженер данных",
    "senior инженер данных",
    "python developer",
    "разработчик python",
    "python разработчик",
    "developer python",
    "junior python developer",
    "middle python developer",
    "senior python developer",
    "junior разработчик python",
    "middle разработчик python",
    "senior разработчик python",
    "junior python разработчик",
    "middle python разработчик",
    "senior python разработчик",
    "backend developer",
    "разработчик backend",
    "backend разработчик",
    "developer backend",
    "frontend developer",
    "разработчик frontend",
    "frontend разработчик",
    "developer frontend",
    "fullstack developer",
    "разработчик fullstack",
    "fullstack разработчик",
    "developer fullstack",
    "junior backend developer",
    "middle backend developer",
    "senior backend developer",
    "junior разработчик backend",
    "middle разработчик backend",
    "senior разработчик backend",
    "junior frontend developer",
    "middle frontend developer",
    "senior frontend developer",
    "junior разработчик frontend",
    "middle разработчик frontend",
    "senior разработчик frontend",
    "junior fullstack developer",
    "middle fullstack developer",
    "senior fullstack developer",
    "junior разработчик fullstack",
    "middle разработчик fullstack",
    "senior разработчик fullstack",
    "java developer",
    "разработчик java",
    "java разработчик",
    "developer java",
    "junior java developer",
    "middle java developer",
    "senior java developer",
    "junior разработчик java",
    "middle разработчик java",
    "senior разработчик java",
    "c# developer",
    "разработчик c#",
    "c# разработчик",
    "developer c#",
    "junior c# developer",
    "middle c# developer",
    "senior c# developer",
    "junior разработчик c#",
    "middle разработчик c#",
    "senior разработчик c#",
    "c++ developer",
    "разработчик c++",
    "c++ разработчик",
    "developer c++",
    "junior c++ developer",
    "middle c++ developer",
    "senior c++ developer",
    "junior разработчик c++",
    "middle разработчик c++",
    "senior разработчик c++",
    "javascript developer",
    "разработчик javascript",
    "javascript разработчик",
    "developer javascript",
    "junior javascript developer",
    "middle javascript developer",
    "senior javascript developer",
    "junior разработчик javascript",
    "middle разработчик javascript",
    "senior разработчик javascript",
    "go developer",
    "разработчик go",
    "go разработчик",
    "golang developer",
    "разработчик golang",
    "golang разработчик",
    "junior go developer",
    "middle go developer",
    "senior go developer",
    "junior разработчик go",
    "middle разработчик go",
    "senior разработчик go",
    "kotlin developer",
    "разработчик kotlin",
    "kotlin разработчик",
    "developer kotlin",
    "junior kotlin developer",
    "middle kotlin developer",
    "senior kotlin developer",
    "junior разработчик kotlin",
    "middle разработчик kotlin",
    "senior разработчик kotlin",
    "системный администратор",
    "junior системный администратор",
    "middle системный администратор",
    "senior системный администратор",
    "sysadmin",
    "junior sysadmin",
    "senior sysadmin",
    "1С",
    "программист 1С",
    "разработчик 1С",
    "junior 1С",
    "middle 1С",
    "senior 1С",
]


all_data = []


for city_id, city_name in cities.items():
    print(f"\nСбор вакансий в городе: {city_name}")

    for query in queries:
        print(query)

        page = 0
        while page < 20:
            url = "https://api.hh.ru/vacancies"
            params = {"text": query, "area": city_id, "per_page": 100, "page": page}

            response = requests.get(url, params=params)

            if response.status_code == 429:
                time.sleep(10)

            elif response.status_code == 503:
                flag = True
                break
            elif response.status_code != 200:
                print(response.status_code, page)
                break

            data = response.json()
            items = data.get("items", [])

            if not items:
                break

            for item in items:
                vacancy_id = item.get("id")
                name = item.get("name")
                employer = item.get("employer", {}).get("name", "")
                published_at = item.get("published_at")
                url_link = item.get("alternate_url")

                # требования и обязанности
                snippet = item.get("snippet", {})
                requirement = snippet.get("requirement", "") or ""
                responsibility = snippet.get("responsibility", "") or ""
                description = (requirement + " " + responsibility).strip()

                # зп
                salary_info = item.get("salary")
                salary_from = None
                salary_to = None
                currency = None
                avg_salary = None

                if salary_info:
                    salary_from = salary_info.get("from")
                    salary_to = salary_info.get("to")
                    currency = salary_info.get("currency")

                    # Считаем среднюю только для рублей
                    if currency == "RUR":
                        if salary_from and salary_to:
                            avg_salary = (salary_from + salary_to) / 2
                        elif salary_from:
                            avg_salary = salary_from
                        elif salary_to:
                            avg_salary = salary_to

                employment_info = item.get("employment")
                employment = employment_info.get("name") if employment_info else None

                work_format_info = item.get("work_format", [])
                remote_type = "Очная"

                if work_format_info:
                    work_format_id = work_format_info[0].get("id", "")
                    if work_format_id == "REMOTE":
                        remote_type = "Удалённая"
                    elif work_format_id == "HYBRID":
                        remote_type = "Гибрид"
                    elif work_format_id == "ON_SITE":
                        remote_type = "Очная"
                else:

                    employment_name = (item.get("employment") or {}).get("name", "")
                    schedule_name = (item.get("schedule") or {}).get("name", "")

                    if employment_name == "Удалённая работа":
                        remote_type = "Удалённая"
                    elif schedule_name == "Гибрид":
                        remote_type = "Гибрид"
                    elif description:
                        desc_lower = description.lower()
                        if any(
                            w in desc_lower
                            for w in ["гибрид", "гибридный", "офис и удалён"]
                        ):
                            remote_type = "Гибрид"
                        elif any(w in desc_lower for w in ["удалён", "remote"]):
                            remote_type = "Удалённая"

                if description:
                    all_data.append(
                        {
                            "id": vacancy_id,
                            "title": name,
                            "description": description,
                            "avg_salary": avg_salary,
                            "currency": currency,
                            "employer": employer,
                            "city": city_name,
                            "search_query": query,
                            "employment": employment,
                            "remote": remote_type,
                            "published_at": published_at,
                            "url": url_link,
                        }
                    )

            print(f"Страница {page + 1}: получено {len(items)} вакансий")
            page += 1
            time.sleep(0.7)


df = pd.DataFrame(all_data)


df = df.drop_duplicates(subset="id").reset_index(drop=True)


df.to_csv(output_file, index=False, encoding="utf-8-sig")

print(f"\nСобрано {len(df)} уникальных вакансий.")


if flag:
    print("503 выстрелила")
with_salary = df["avg_salary"].notna().sum()
print("Из них с указанием зп:", with_salary)
