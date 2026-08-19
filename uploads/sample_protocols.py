"""Генерация примеров протоколов ЕГЭ/ОГЭ для скачивания из личного кабинета ОО."""

from io import BytesIO

from openpyxl import Workbook


def _school_code_cell(school_code: str):
    code = (school_code or "").strip()
    if code.isdigit():
        return int(code)
    try:
        return int(float(code.replace(",", ".")))
    except ValueError:
        return code


def build_ege_sample_xlsx(school_code: str) -> bytes:
    code = _school_code_cell(school_code)
    wb = Workbook()
    ws = wb.active
    ws.title = "Протокол ЕГЭ"

    ws.append(["01 - Русский язык 2025.05.30"])
    ws.append(
        [
            "№",
            "Код ППЭ",
            "Код ОО",
            "Класс",
            "Код ООП",
            "Профиль",
            "Фамилия",
            "Имя",
            "Отчество",
            "Вариант",
            "Код участника",
            "№ бланка",
            "Ответы в краткой форме",
            "Ответы в развернутой форме",
            "Первичный балл",
            "Итоговый балл",
        ]
    )
    ws.append(
        [
            1,
            100,
            code,
            "11",
            101,
            102,
            "Иванов",
            "Иван",
            "Иванович",
            1,
            "000001",
            "000001",
            "++---+-------------",
            "1(1)2(3)1(2)",
            15,
            35,
        ]
    )
    ws.append(
        [
            2,
            100,
            code,
            "11",
            101,
            102,
            "Петрова",
            "Мария",
            "Сергеевна",
            1,
            "000002",
            "000002",
            "+-+--+-------------",
            "2(2)1(1)0(3)",
            12,
            28,
        ]
    )

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_oge_sample_xlsx(school_code: str) -> bytes:
    code = _school_code_cell(school_code)
    wb = Workbook()
    ws = wb.active
    ws.title = "Протокол ОГЭ"

    ws.append(["01 - Русский язык 2025.06.09"])
    ws.append(
        [
            "№",
            "Код ОО",
            "Класс",
            "Код ППЭ",
            "Аудитория",
            "Код участника",
            "Фамилия",
            "Имя",
            "Отчество",
            "Серия",
            "Номер",
            "Ответы в краткой форме",
            "Ответы в развернутой форме",
            "Первичный балл",
            "Оценка",
        ]
    )
    ws.append(
        [
            1,
            code,
            "9А",
            100,
            101,
            102,
            "Сидоров",
            "Алексей",
            "Петрович",
            "9623",
            "123456",
            "+++++++++++",
            "2(2)2(2)1(1)",
            22,
            4,
        ]
    )
    ws.append(
        [
            2,
            code,
            "9Б",
            100,
            102,
            103,
            "Козлова",
            "Анна",
            "Игоревна",
            "9624",
            "654321",
            "++++++-+-++",
            "2(2)1(2)0(1)",
            17,
            3,
        ]
    )

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
