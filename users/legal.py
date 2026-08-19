"""Реквизиты правообладателя платформы «Анализ ГИА»."""

from pathlib import Path

OPERATOR_NAME = "Пихаев Амур Адланович"
OPERATOR_INN = "201005220670"
OPERATOR_STATUS = "плательщик налога на профессиональный доход (самозанятый)"
OPERATOR_EMAIL = "Pikhaev1988@yandex.ru"
SITE_URL = "https://analizgia.ru"
PRODUCT_NAME = "Анализ ГИА"
POLICY_DATE = "18.08.2026"
ACCESS_YEARS = 5

SCHOOL_DOCUMENTS_DIR = Path(__file__).resolve().parents[1] / "static" / "docs" / "school"

SCHOOL_DOCUMENTS = [
    {
        "slug": "letter",
        "file": "01_Pismo_shkole.docx",
        "download_name": "Pismo_rukovoditelyu_Analiz_GIA.docx",
        "icon": "✉️",
        "title": "Письмо руководителю",
        "for_whom": "Директору",
        "description": "Кто правообладатель, что покупает школа и почему договор с физлицом (самозанятым) допустим.",
    },
    {
        "slug": "description",
        "file": "02_Opisanie_platformy.docx",
        "download_name": "Opisanie_platformy_Analiz_GIA.docx",
        "icon": "📘",
        "title": "Описание платформы",
        "for_whom": "Директору и завучу",
        "description": "Назначение сервиса, роли доступа, какие данные обрабатываются, что входит в 5 лет.",
    },
    {
        "slug": "security",
        "file": "03_Spravka_IB.docx",
        "download_name": "Spravka_IB_Analiz_GIA.docx",
        "icon": "🛡️",
        "title": "Справка об информационной безопасности",
        "for_whom": "Ответственному за защиту данных",
        "description": "Меры защиты, роли, персональные данные, почему не требуются ФСТЭК и лицензия на образование.",
    },
    {
        "slug": "contract",
        "file": "04_Dogovor_5_let.docx",
        "download_name": "Dogovor_dostupa_5_let_Analiz_GIA.docx",
        "icon": "📝",
        "title": "Договор на 5 лет (безнал)",
        "for_whom": "Бухгалтерии и директору",
        "description": "Договор оказания услуг с физическим лицом и приложение — поручение на обработку персональных данных.",
    },
    {
        "slug": "contract-cash",
        "file": "04_Dogovor_5_let_nalichnye.docx",
        "download_name": "Dogovor_dostupa_5_let_nalichnye_Analiz_GIA.docx",
        "icon": "📝",
        "title": "Договор на 5 лет (наличные)",
        "for_whom": "Бухгалтерии и директору",
        "description": "Вариант договора для оплаты наличными.",
    },
    {
        "slug": "contract-new",
        "file": "04_Dogovor_5_let_new.docx",
        "download_name": "Dogovor_dostupa_5_let_new_Analiz_GIA.docx",
        "icon": "📝",
        "title": "Договор на 5 лет (новая редакция)",
        "for_whom": "Бухгалтерии и директору",
        "description": "Обновлённая редакция договора оказания услуг.",
    },
    {
        "slug": "act",
        "file": "05_Akt.docx",
        "download_name": "Akt_okazannyh_uslug_Analiz_GIA.docx",
        "icon": "📋",
        "title": "Акт оказанных услуг",
        "for_whom": "Бухгалтерии",
        "description": "Подписывается после оплаты и выдачи логина.",
    },
    {
        "slug": "accounting",
        "file": "06_Pamyatka_buhgalterii.docx",
        "download_name": "Pamyatka_buhgalterii_Analiz_GIA.docx",
        "icon": "💼",
        "title": "Памятка для бухгалтерии",
        "for_whom": "Бухгалтерии",
        "description": "Можно ли покупать у физлица, какие налоги, какой комплект закрывает расход.",
    },
]
