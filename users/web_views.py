from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Avg, Count, Max, Min, Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from users.http_utils import attachment_response
from django.views.generic import TemplateView, View
import hashlib
import json
from json import JSONDecodeError
from functools import lru_cache
from pathlib import Path

from analytics.services import exam_overview
from exams.models import EgePassingThreshold, Exam, ExamResult, ExamTaskTopic, TaskResult
from exams.passing import (
    GVE_GRADE_THRESHOLD,
    gve_subject_label,
    is_gve_exam,
    oge_score_passed,
    resolve_ege_passing_threshold,
)
from organizations.models import District, School
from users.export_reports import (
    MO_SUBJECT_GROUPS,
    _build_school_analytic_note_payload,
    _build_school_info_stat_payload,
    _build_school_mo_payload,
    _build_school_subject_note_payload,
    generate_school_analytic_note_docx,
    generate_school_analytic_note_pdf,
    generate_school_mo_report_docx,
    generate_school_mo_report_pdf,
    generate_school_deputy_report_docx,
    generate_school_deputy_report_pdf,
    generate_school_deputy_report_xlsx,
    generate_school_subject_note_docx,
    generate_school_subject_note_pdf,
    _build_school_deputy_report_payload,
    _is_weak_subject_row,
    collect_exam_data_for_export,
    generate_pdf_report,
    generate_presentation,
    generate_school_gia_summary_docx,
    generate_school_info_stat_docx,
    generate_school_info_stat_pdf,
    generate_school_info_stat_xlsx,
    generate_district_gia_summary_pdf,
    generate_district_gia_summary_xlsx,
    generate_word_doc,
    generate_xlsx_report,
)
from users.district_export_reports import (
    _build_district_analytic_note_payload,
    _build_district_gia_summary_core,
    _build_district_info_stat_payload,
    _build_district_management_payload,
    _build_district_mo_payload,
    _build_district_school_comparison_payload,
    _build_district_subject_note_payload,
    generate_district_analytic_note_docx,
    generate_district_gia_summary_docx,
    generate_district_info_stat_docx,
    generate_district_management_docx,
    generate_district_mo_report_docx,
    generate_district_school_comparison_docx,
    generate_district_subject_note_docx,
)
from users.report_ui.school_gia_summary import build_gia_summary_presentation


def _cache_get_or_set(key: str, ttl_seconds: int, builder):
    cached = cache.get(key)
    if cached is not None:
        return cached
    value = builder()
    cache.set(key, value, ttl_seconds)
    return value


def _parse_positive_int(value):
    if value and value.isdigit():
        parsed = int(value)
        if parsed > 0:
            return parsed
    return None


def _normalize_grade_label(value):
    label = (value or "").strip()
    if not label:
        return "Класс не указан"
    # Drop non-class placeholders like exam type labels.
    if not any(ch.isdigit() for ch in label):
        return "Класс не указан"
    return label


def _resolve_school_id_for_user(user):
    if user.school_id:
        return user.school_id
    username = (user.username or "").strip()
    if not username:
        return None
    school = School.objects.filter(code=username).only("id").first()
    return school.id if school else None


def _catalog_source(exam_type="ege"):
    data_dir = Path(__file__).resolve().parents[1] / "data"
    if (exam_type or "ege").lower() == "oge":
        source = data_dir / "oge_json" / "oge_2026_enriched.json"
        if source.exists():
            return source
    source = data_dir / "ege_2026_enriched.json"
    if not source.exists():
        source = data_dir / "ege_2026_full.json"
    return source


@lru_cache(maxsize=16)
def _load_subject_task_catalog_cached(source_path: str, version_token: int):
    source = Path(source_path)
    if not source.exists():
        return {}
    raw = source.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except JSONDecodeError:
        return {}
    result = {}
    for subject in payload.get("subjects", []):
        key = (subject.get("subject") or "").strip().lower()
        if not key:
            continue
        result[key] = {
            item.get("task"): {
                "topic": item.get("topic"),
                "topic_oge": item.get("topic_oge"),
                "grade_range": item.get("grade_range") or [],
                "grade_range_oge": item.get("grade_range_oge") or [],
            }
            for item in subject.get("tasks", [])
            if item.get("task") is not None
        }
    return result


def _load_subject_task_catalog(exam_type="ege"):
    source = _catalog_source(exam_type)
    version_token = source.stat().st_mtime_ns if source.exists() else 0
    return _load_subject_task_catalog_cached(str(source), version_token)


def _subject_key_candidates(subject_name, exam_type="ege"):
    from users.task_topics import subject_key_candidates

    return subject_key_candidates(subject_name, exam_type)


def _topic_for_task(subject_name, task_number, exam_type="ege"):
    from users.task_topics import topic_for_task

    return topic_for_task(subject_name, task_number, exam_type)


def _grades_for_task(subject_name, task_number, exam_type="ege"):
    et = (exam_type or "ege").lower()
    manual_meta = _manual_task_meta(subject_name, task_number, et)
    if manual_meta and manual_meta.get("grade_range"):
        return manual_meta["grade_range"]
    topics_index = _load_subject_task_catalog(et)
    for candidate in _subject_key_candidates(subject_name, et):
        task_meta = topics_index.get(candidate, {}).get(task_number, {})
        if et == "oge":
            grades = task_meta.get("grade_range_oge") or task_meta.get("grade_range") or []
        else:
            grades = task_meta.get("grade_range") or []
        if grades:
            return grades
    return []


def _spec_grade_label(spec_grades):
    normalized = [str(item).strip() for item in spec_grades if str(item).strip()]
    if not normalized:
        return ""
    if len(normalized) == 1:
        return f"{normalized[0]} класс (по спецификации)"
    return f"{'–'.join(normalized)} классы (по спецификации)"


def _ru_parallel_word(n: int) -> str:
    """Согласование для подписи «N класс / класса / классов»."""
    n = abs(int(n)) % 100
    if 11 <= n <= 14:
        return "классов"
    n = n % 10
    if n == 1:
        return "класс"
    if 2 <= n <= 4:
        return "класса"
    return "классов"


def _format_oge_kim_grade_levels(grades) -> str:
    """
    Параллели из спецификации КИМ ОГЭ (поле grade_range в каталоге): где по программе проходит тема.
    """
    nums = []
    for g in grades or []:
        s = str(g).strip()
        if s.isdigit():
            nums.append(int(s))
    nums = sorted(set(nums))
    if not nums:
        return ""
    if len(nums) == 1:
        n = nums[0]
        return f"{n} {_ru_parallel_word(n)}"
    if nums == list(range(nums[0], nums[-1] + 1)):
        return f"{nums[0]}–{nums[-1]} классы"
    if len(nums) == 2:
        a, b = nums[0], nums[1]
        return f"{a} и {b} {_ru_parallel_word(max(a, b))}"
    return ", ".join(str(n) for n in nums) + f" {_ru_parallel_word(nums[-1])}"


def _scope_hash(scope: dict) -> str:
    normalized_scope = json.dumps(scope, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(normalized_scope.encode("utf-8")).hexdigest()


def _is_success_token(token_value) -> bool:
    token = str(token_value or "").strip()
    if not token:
        return False
    if token == "+":
        return True
    if token in {"-", "0"}:
        return False
    if token.isdigit():
        return int(token) > 0
    return False


@lru_cache(maxsize=8192)
def _manual_task_meta(subject_name, task_number, exam_type="ege"):
    from users.task_topics import manual_task_meta

    return manual_task_meta(subject_name, task_number, exam_type)


def _threshold_subject_key(subject_name):
    title = (subject_name or "").strip().lower()
    if "рус" in title:
        return "russian"
    if "СЂСѓСЃ" in title:
        return "russian"
    if "математика" in title and "проф" in title:
        return "math_profile"
    if "математика" in title and "баз" in title:
        return "math_basic"
    if "обществ" in title:
        return "social"
    if "информат" in title:
        return "informatics"
    if "физик" in title:
        return "physics"
    if "хими" in title:
        return "chemistry"
    if "биолог" in title:
        return "biology"
    if "истори" in title:
        return "history"
    if "литератур" in title:
        return "literature"
    if "географ" in title:
        return "geography"
    if any(lang in title for lang in ("англий", "немец", "француз", "испан", "китай", "иностран")):
        return "foreign_language"
    return None


def _pass_stats_by_school(qs, exam_type: str) -> dict[int, tuple[int, int]]:
    """school_id -> (total_results, passed_count)."""
    if exam_type != "ege":
        stats: dict[int, list[int]] = {}
        for row in qs.values("student__school_id", "score", "passed"):
            school_id = int(row["student__school_id"])
            bucket = stats.setdefault(school_id, [0, 0])
            bucket[0] += 1
            if _oge_exam_passed(row.get("score"), row.get("passed")):
                bucket[1] += 1
        return {school_id: (values[0], values[1]) for school_id, values in stats.items()}

    threshold_cache: dict = {}
    stats: dict[int, list[int]] = {}
    for row in qs.values("student__school_id", "exam__subject", "exam__code", "exam__year", "score", "passed"):
        school_id = int(row["student__school_id"])
        bucket = stats.setdefault(school_id, [0, 0])
        bucket[0] += 1
        if _ege_exam_passed(row, threshold_cache):
            bucket[1] += 1
    return {school_id: (values[0], values[1]) for school_id, values in stats.items()}


def _passed_count_by_subject(qs, exam_type: str) -> dict[str, int]:
    if exam_type != "ege":
        passed_by_subject: dict[str, int] = {}
        for row in qs.values("exam__subject", "score", "passed"):
            subject_name = row.get("exam__subject") or "Предмет не указан"
            if _oge_exam_passed(row.get("score"), row.get("passed")):
                passed_by_subject[subject_name] = passed_by_subject.get(subject_name, 0) + 1
        return passed_by_subject

    threshold_cache: dict = {}
    passed_by_subject: dict[str, int] = {}
    for row in qs.values("exam__subject", "exam__code", "exam__year", "score", "passed"):
        subject_name = row.get("exam__subject") or "Предмет не указан"
        if _ege_exam_passed(row, threshold_cache):
            passed_by_subject[subject_name] = passed_by_subject.get(subject_name, 0) + 1
    return passed_by_subject


def _ege_exam_passed(row: dict, threshold_cache: dict) -> bool:
    """
    Сдал ли экзамен по ЕГЭ с учётом EgePassingThreshold (а не только флага passed в строке импорта).
    row: словарь с ключами exam__subject, exam__year, score, passed; опционально exam__code.
    ГВЭ (код 51 и др.) — шкала оценок 2–5, порог ≥ 3.
    """
    from exams.passing import ege_result_passed

    return ege_result_passed(
        subject_name=row.get("exam__subject"),
        year=row.get("exam__year"),
        score=row.get("score"),
        passed_flag=row.get("passed"),
        exam_code=row.get("exam__code"),
        cache=threshold_cache,
    )


def _oge_exam_passed(score, passed_flag) -> bool:
    """ОГЭ / ГВЭ: на пятибалльной шкале порог — оценка 3 и выше."""
    return oge_score_passed(score, passed_flag)


def _exam_result_below_minimum(result, exam_type: str, threshold_cache: dict | None = None) -> bool:
    """
    True, если результат ниже минимального порога сдачи.
    ОГЭ и ГВЭ (в протоколах ЕГЭ) — шкала 2–5, порог ≥ 3.
    """
    et = (exam_type or "ege").strip().lower()
    if et == "oge":
        return not _oge_exam_passed(result.score, result.passed)

    exam = getattr(result, "exam", None)
    cache = threshold_cache if threshold_cache is not None else {}
    row = {
        "exam__subject": exam.subject if exam else "",
        "exam__code": exam.code if exam else "",
        "exam__year": exam.year if exam else 0,
        "score": result.score,
        "passed": result.passed,
    }
    return not _ege_exam_passed(row, cache)


def _subject_group_key(subject_name):
    title = (subject_name or "").strip()
    if not title:
        return "unknown"
    candidates = _subject_key_candidates(title)
    if candidates:
        return candidates[0]
    return title.lower()


COMPARISON_YEARS = (2023, 2024, 2025)


def _derive_comparison_years(exam_type: str, scope: dict, max_years: int = 6) -> tuple[int, ...]:
    """
    Годы для таблицы динамики по фактическим данным в выборке (республика / зона ответственности).
    Берём последние max_years календарных годов, по которым есть результаты.
    """
    qs = ExamResult.objects.filter(exam__exam_type=exam_type, **scope)
    raw_years = qs.values_list("exam__year", flat=True).distinct()
    years = sorted({int(y) for y in raw_years if y is not None})
    if not years:
        return COMPARISON_YEARS
    if len(years) > max_years:
        years = years[-max_years:]
    return tuple(years)


def _build_year_comparison(results_qs, years=COMPARISON_YEARS, max_chart_subjects=8):
    rows = list(
        results_qs.values("exam__year", "exam__subject")
        .annotate(
            students_count=Count("student_id", distinct=True),
            results_count=Count("id"),
            avg_score=Avg("score"),
            passed_count=Count("id", filter=Q(passed=True)),
        )
        .order_by("exam__subject", "exam__year")
    )

    subjects = {}
    for row in rows:
        year = row["exam__year"]
        if year not in years:
            continue
        subject_name = (row["exam__subject"] or "").strip() or "Предмет не указан"
        subject_key = _subject_group_key(subject_name)
        entry = subjects.setdefault(
            subject_key,
            {
                "subject": subject_name,
                "years": {},
                "total_students": 0,
            },
        )
        year_entry = entry["years"].setdefault(
            year, {"students_count": 0, "results_count": 0, "passed_count": 0, "score_weighted_sum": 0.0}
        )
        students_count = row["students_count"] or 0
        results_count = row["results_count"] or 0
        passed_count = row["passed_count"] or 0
        avg_score = float(row["avg_score"] or 0)
        year_entry["students_count"] += students_count
        year_entry["results_count"] += results_count
        year_entry["passed_count"] += passed_count
        # Вес среднего балла — по числу работ, чтобы не искажать при нескольких попытках.
        year_entry["score_weighted_sum"] += avg_score * results_count
        entry["total_students"] += students_count

    comparison_rows = []
    for subject_data in subjects.values():
        years_data = []
        for year in years:
            year_data = subject_data["years"].get(year)
            if not year_data or year_data["students_count"] == 0:
                years_data.append(
                    {
                        "year": year,
                        "students_count": 0,
                        "avg_score": None,
                        "pass_rate": None,
                    }
                )
                continue
            students_count = year_data["students_count"]
            results_count = year_data["results_count"] or students_count
            avg_score = round(year_data["score_weighted_sum"] / results_count, 2) if results_count else None
            pass_rate = round((year_data["passed_count"] / results_count) * 100, 1) if results_count else 0.0
            years_data.append(
                {
                    "year": year,
                    "students_count": students_count,
                    "avg_score": avg_score,
                    "pass_rate": pass_rate,
                }
            )

        first_with_data = next((item for item in years_data if item["avg_score"] is not None), None)
        last_with_data = next((item for item in reversed(years_data) if item["avg_score"] is not None), None)
        trend_delta = None
        if first_with_data and last_with_data and first_with_data["year"] != last_with_data["year"]:
            trend_delta = round(last_with_data["avg_score"] - first_with_data["avg_score"], 2)

        comparison_rows.append(
            {
                "subject": subject_data["subject"],
                "total_students": subject_data["total_students"],
                "years": years_data,
                "trend_delta": trend_delta,
            }
        )

    comparison_rows.sort(key=lambda item: (-item["total_students"], item["subject"]))
    chart_data = {
        "labels": [str(year) for year in years],
        "datasets": [
            {"label": item["subject"], "data": [year_item["avg_score"] for year_item in item["years"]]}
            for item in comparison_rows[:max_chart_subjects]
        ],
    }
    return comparison_rows, chart_data


def _scope_for_user(user):
    if user.role == "school":
        school_id = _resolve_school_id_for_user(user)
        if school_id:
            return {"student__school_id": school_id}
        return {"student__school_id": -1}
    if user.role == "district":
        return {"student__school__district_id": user.district_id}
    if user.role == "ministry":
        # Республика в модели данных: все школы районов, привязанных к министерству пользователя.
        mid = getattr(user, "ministry_id", None)
        if mid:
            return {"student__school__district__ministry_id": mid}
        # Если профиль министерства не заполнен — сохраняем прежнее поведение (вся база).
        return {}
    return {}


class RoleLoginView(LoginView):
    template_name = "users/home_login.html"
    redirect_authenticated_user = True

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return "/cabinet/"


def csrf_failure(request, reason=""):
    return render(
        request,
        "users/csrf_failure.html",
        {"reason": reason},
        status=403,
    )


class RoleRedirectView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        role = request.user.role
        if not role:
            if request.user.is_superuser:
                return redirect("/admin/")
            return redirect("no-role")
        exam_type = (request.GET.get("exam_type") or "").strip().lower()
        if exam_type in {"ege", "oge", "vpr"}:
            if role == "ministry":
                return redirect(f"/cabinet/ministry/?exam_type={exam_type}")
            if role == "district":
                return redirect(f"/cabinet/district/?exam_type={exam_type}")
            if role == "school":
                return redirect(f"/cabinet/school/?exam_type={exam_type}")
            return redirect("no-role")
        return redirect("cabinet-exam-choice")


class ExamTypeChoiceView(LoginRequiredMixin, TemplateView):
    template_name = "users/exam_choice.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not getattr(request.user, "role", None) and not request.user.is_superuser:
            return redirect("no-role")
        return super().dispatch(request, *args, **kwargs)

    def _hub_scope(self):
        return getattr(self, "_scope_override", None) or _scope_for_user(self.request.user)

    def build_hub_context(self, scope: dict, exam_filter: str, stats_year: int, available_years: list[int]) -> dict:
        self._scope_override = scope
        try:
            comparison_cache_key = f"choice:comparison:v2:{_scope_hash(scope)}:{'-'.join(map(str, COMPARISON_YEARS))}"
            comparison_cached = cache.get(comparison_cache_key)
            if comparison_cached:
                comparison_rows, comparison_chart = comparison_cached
            else:
                comparison_rows, comparison_chart = _build_year_comparison(
                    ExamResult.objects.filter(**scope, exam__year__in=COMPARISON_YEARS),
                    years=COMPARISON_YEARS,
                )
                cache.set(comparison_cache_key, (comparison_rows, comparison_chart), 43200)
            comparison_insights = self._comparison_insights(comparison_rows)
            # Участники за последний год сравнения — уникальные дети, не сумма по предметам.
            latest_cmp_year = COMPARISON_YEARS[-1]
            comparison_insights["participants_latest_year"] = (
                ExamResult.objects.filter(**scope, exam__year=latest_cmp_year)
                .values("student_id")
                .distinct()
                .count()
            )
            ege_stats = self._exam_stats("ege", year=stats_year)
            oge_stats = self._exam_stats("oge", year=stats_year)
            vpr_stats = self._exam_stats("vpr", year=stats_year)
            ege_mix = self._subject_mix("ege", year=stats_year)
            oge_mix = self._subject_mix("oge", year=stats_year)
            vpr_mix = self._subject_mix("vpr", year=stats_year)
            ege_risks = self._risk_tasks("ege", year=stats_year)
            oge_risks = self._risk_tasks("oge", year=stats_year)
            vpr_risks = self._risk_tasks("vpr", year=stats_year)
            overview_extra = self._overview_extra(
                scope, ege_stats, oge_stats, ege_risks, oge_risks, comparison_insights
            )
            overview_extra["data_year_label"] = str(stats_year)
            dynamics_years = self._dynamics_years(scope, exam_filter, available_years)
            year_dynamics = self._year_dynamics(scope, dynamics_years, exam_filter=exam_filter)
            if exam_filter == "oge":
                hub_categories = oge_mix
                hub_categories_title = f"Структура ОГЭ по предметам · {stats_year}"
            elif exam_filter == "ege":
                hub_categories = ege_mix
                hub_categories_title = f"Структура ЕГЭ по предметам · {stats_year}"
            elif exam_filter == "vpr":
                hub_categories = vpr_mix
                hub_categories_title = f"Структура ВПР по предметам · {stats_year}"
            else:
                ege_total = sum(i["students"] for i in ege_mix) if ege_mix else 0
                oge_total = sum(i["students"] for i in oge_mix) if oge_mix else 0
                if oge_total >= ege_total:
                    hub_categories = oge_mix
                    hub_categories_title = f"Структура ОГЭ по предметам · {stats_year}"
                else:
                    hub_categories = ege_mix
                    hub_categories_title = f"Структура ЕГЭ по предметам · {stats_year}"
            return {
                "hub_exam_filter": exam_filter,
                "hub_available_years": available_years,
                "hub_selected_year": stats_year,
                "hub_dynamics_years": list(dynamics_years),
                "comparison_years": list(COMPARISON_YEARS),
                "comparison_rows": comparison_rows,
                "comparison_chart": comparison_chart,
                "comparison_insights": comparison_insights,
                "ege_stats": ege_stats,
                "oge_stats": oge_stats,
                "vpr_stats": vpr_stats,
                "ege_mix": ege_mix,
                "oge_mix": oge_mix,
                "vpr_mix": vpr_mix,
                "ege_risks": ege_risks,
                "oge_risks": oge_risks,
                "vpr_risks": vpr_risks,
                "overview_extra": overview_extra,
                "year_dynamics": year_dynamics,
                "hub_categories": hub_categories,
                "hub_categories_title": hub_categories_title,
            }
        finally:
            if hasattr(self, "_scope_override"):
                del self._scope_override

    def _exam_stats(self, exam_type, year: int):
        scope = self._hub_scope()
        cache_key = f"choice:exam_stats:v4:{exam_type}:{year}:{_scope_hash(scope)}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        results = ExamResult.objects.filter(
            exam__exam_type=exam_type,
            exam__year=year,
            **scope,
        )
        aggregates = results.aggregate(
            total_results=Count("id"),
            unique_students=Count("student_id", distinct=True),
            total_exams=Count("exam_id", distinct=True),
            avg_score=Avg("score"),
            passed_count=Count("id", filter=Q(passed=True)),
            failed_count=Count("id", filter=Q(passed=False)),
        )
        total_results = int(aggregates["total_results"] or 0)
        unique_students = int(aggregates["unique_students"] or 0)
        total_exams = int(aggregates["total_exams"] or 0)
        avg_score = aggregates["avg_score"] or 0
        passed_count = int(aggregates["passed_count"] or 0)
        failed_count = int(aggregates["failed_count"] or 0)
        pass_rate = round((passed_count / total_results) * 100, 1) if total_results else 0
        top_subjects = list(
            results.values("exam__subject")
            .annotate(students=Count("id"))
            .order_by("-students", "exam__subject")
            .values_list("exam__subject", flat=True)[:6]
        )
        payload = {
            "year": year,
            "total_results": total_results,
            "unique_students": unique_students,
            "total_exams": total_exams,
            "avg_score": round(avg_score, 2),
            "pass_rate": pass_rate,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "top_subjects": top_subjects,
        }
        cache.set(cache_key, payload, 43200)
        return payload

    def _recent_years(self, exam_type: str, scope: dict, max_years: int = 1) -> tuple[int, ...]:
        cache_key = f"choice:recent_years:{exam_type}:{max_years}:{_scope_hash(scope)}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        years = _derive_comparison_years(exam_type, scope, max_years=max_years)
        cache.set(cache_key, years, 43200)
        return years

    def _chart_dataset(self, year: int | None = None):
        scope = self._hub_scope()
        cache_key = f"choice:chart_dataset:v2:{year or 'auto'}:{_scope_hash(scope)}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        ege_years = (year,) if year else self._recent_years("ege", scope, max_years=1)
        oge_years = (year,) if year else self._recent_years("oge", scope, max_years=1)
        ege = (
            ExamResult.objects.filter(exam__exam_type="ege", exam__year__in=ege_years, **scope)
            .values("exam__subject")
            .annotate(students=Count("student_id", distinct=True))
            .order_by("-students", "exam__subject")[:8]
        )
        oge = (
            ExamResult.objects.filter(exam__exam_type="oge", exam__year__in=oge_years, **scope)
            .values("exam__subject")
            .annotate(students=Count("student_id", distinct=True))
            .order_by("-students", "exam__subject")[:8]
        )
        payload = {
            "ege_labels": [row["exam__subject"] for row in ege],
            "ege_values": [row["students"] for row in ege],
            "oge_labels": [row["exam__subject"] for row in oge],
            "oge_values": [row["students"] for row in oge],
        }
        cache.set(cache_key, payload, 43200)
        return payload

    def _subject_mix(self, exam_type, year: int, limit: int = 8):
        scope = self._hub_scope()
        cache_key = f"choice:subject_mix:v3:{exam_type}:{year}:{limit}:{_scope_hash(scope)}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        base_qs = ExamResult.objects.filter(
            exam__exam_type=exam_type,
            exam__year=year,
            **scope,
        )
        all_rows = list(
            base_qs.values("exam__subject")
            .annotate(students=Count("student_id", distinct=True))
            .order_by("-students", "exam__subject")
        )
        grand_total = sum(int(row["students"] or 0) for row in all_rows) or 1
        rows = all_rows[:limit]
        for row in rows:
            row["share"] = round((row["students"] / grand_total) * 100, 1)
        shown_total = sum(int(row["students"] or 0) for row in rows)
        others = grand_total - shown_total
        if others > 0:
            rows.append(
                {
                    "exam__subject": "Прочие",
                    "students": others,
                    "share": round((others / grand_total) * 100, 1),
                }
            )
        cache.set(cache_key, rows, 43200)
        return rows

    def _dynamics_years(self, scope: dict, exam_filter: str, available_years: list[int]) -> tuple[int, ...]:
        if exam_filter == "oge":
            years = _derive_comparison_years("oge", scope, max_years=4)
        elif exam_filter == "ege":
            years = _derive_comparison_years("ege", scope, max_years=4)
        elif exam_filter == "vpr":
            years = _derive_comparison_years("vpr", scope, max_years=4)
        elif available_years:
            years = tuple(sorted(available_years)[-4:])
        else:
            years = COMPARISON_YEARS
        return years

    def _risk_tasks(self, exam_type, year: int):
        scope = self._hub_scope()
        cache_key = f"choice:risk_tasks:v2:{exam_type}:{year}:{_scope_hash(scope)}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        top_subjects = list(
            ExamResult.objects.filter(exam__exam_type=exam_type, exam__year=year, **scope)
            .values("exam__subject")
            .annotate(students=Count("student_id", distinct=True))
            .order_by("-students", "exam__subject")
            .values_list("exam__subject", flat=True)[:8]
        )
        if not top_subjects:
            cache.set(cache_key, [], 43200)
            return []
        # Critical path for initial page load: do aggregation in DB instead of Python loops.
        # We treat any token other than "-", "0", "" as success (covers "+", "1", "2"...).
        agg_rows = list(
            TaskResult.objects.filter(
                exam__exam_type=exam_type,
                exam__year=year,
                exam__subject__in=top_subjects,
                **scope,
            )
            .values("exam__subject", "task_number")
            .annotate(
                total=Count("id"),
                plus=Count("id", filter=~Q(value__in=["-", "0", ""])),
            )
            .order_by("exam__subject", "task_number")
        )

        risks = []
        for row in agg_rows:
            total = int(row["total"] or 0)
            if total < 5:
                continue
            plus = int(row["plus"] or 0)
            minus = max(total - plus, 0)
            success_rate = round((plus / total) * 100, 1) if total else 0.0
            if success_rate < 50:
                risks.append(
                    {
                        "subject": row["exam__subject"],
                        "task_number": row["task_number"],
                        "success_rate": success_rate,
                        "minus": minus,
                        "total": total,
                    }
                )
        payload = sorted(risks, key=lambda item: (item["success_rate"], -item["minus"]))[:6]
        cache.set(cache_key, payload, 43200)
        return payload

    def _comparison_insights(self, comparison_rows):
        if not comparison_rows:
            return {
                "overall_avg": 0,
                "overall_delta": None,
                "best_subject": None,
                "best_subject_score": None,
                "participants_latest_year": 0,
                "top_growth_subject": None,
                "top_growth_delta": None,
                "top_decline_subject": None,
                "top_decline_delta": None,
                "trend_label": "Недостаточно данных",
            }

        year_totals = {year: {"weighted_sum": 0.0, "students": 0} for year in COMPARISON_YEARS}
        for row in comparison_rows:
            for item in row["years"]:
                if item["avg_score"] is None or not item["students_count"]:
                    continue
                year_totals[item["year"]]["weighted_sum"] += float(item["avg_score"]) * item["students_count"]
                year_totals[item["year"]]["students"] += item["students_count"]

        overall_avg = 0
        latest_year = COMPARISON_YEARS[-1]
        participants_latest_year = year_totals[latest_year]["students"] or 0
        if year_totals[latest_year]["students"]:
            overall_avg = round(year_totals[latest_year]["weighted_sum"] / year_totals[latest_year]["students"], 2)

        earliest_year = COMPARISON_YEARS[0]
        earliest_avg = None
        latest_avg = None
        if year_totals[earliest_year]["students"]:
            earliest_avg = year_totals[earliest_year]["weighted_sum"] / year_totals[earliest_year]["students"]
        if year_totals[latest_year]["students"]:
            latest_avg = year_totals[latest_year]["weighted_sum"] / year_totals[latest_year]["students"]
        overall_delta = None
        if earliest_avg is not None and latest_avg is not None:
            overall_delta = round(latest_avg - earliest_avg, 2)

        best_subject = None
        best_subject_score = None
        top_growth_subject = None
        top_growth_delta = None
        top_decline_subject = None
        top_decline_delta = None
        for row in comparison_rows:
            latest_data = next((item for item in row["years"] if item["year"] == latest_year), None)
            if not latest_data or latest_data["avg_score"] is None:
                continue
            if best_subject_score is None or latest_data["avg_score"] > best_subject_score:
                best_subject_score = latest_data["avg_score"]
                best_subject = row["subject"]
            if row["trend_delta"] is not None:
                if top_growth_delta is None or row["trend_delta"] > top_growth_delta:
                    top_growth_delta = row["trend_delta"]
                    top_growth_subject = row["subject"]
                if top_decline_delta is None or row["trend_delta"] < top_decline_delta:
                    top_decline_delta = row["trend_delta"]
                    top_decline_subject = row["subject"]

        trend_label = "Стабильная динамика"
        if overall_delta is not None:
            if overall_delta > 0.3:
                trend_label = "Рост результатов"
            elif overall_delta < -0.3:
                trend_label = "Снижение результатов"

        return {
            "overall_avg": overall_avg,
            "overall_delta": overall_delta,
            "best_subject": best_subject,
            "best_subject_score": best_subject_score,
            "participants_latest_year": participants_latest_year,
            "top_growth_subject": top_growth_subject,
            "top_growth_delta": top_growth_delta,
            "top_decline_subject": top_decline_subject,
            "top_decline_delta": top_decline_delta,
            "trend_label": trend_label,
        }

    def _available_years(self, scope: dict) -> list[int]:
        cache_key = f"choice:available_years:{_scope_hash(scope)}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        raw = (
            ExamResult.objects.filter(**scope)
            .values_list("exam__year", flat=True)
            .distinct()
        )
        years = sorted({int(y) for y in raw if y is not None}, reverse=True)
        cache.set(cache_key, years, 43200)
        return years

    def _year_dynamics(self, scope: dict, years: tuple[int, ...], exam_filter: str = "all"):
        cache_key = f"choice:year_dyn:v2:{exam_filter}:{'-'.join(map(str, years))}:{_scope_hash(scope)}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        qs = ExamResult.objects.filter(**scope, exam__year__in=years)
        if exam_filter in ("ege", "oge", "vpr"):
            qs = qs.filter(exam__exam_type=exam_filter)
        rows = list(
            qs.values("exam__year")
            .annotate(
                students=Count("student_id", distinct=True),
                results=Count("id"),
                avg_score=Avg("score"),
            )
            .order_by("exam__year")
        )
        passed_by_year = {
            int(r["exam__year"]): int(r["passed"] or 0)
            for r in qs.filter(passed=True)
            .values("exam__year")
            .annotate(passed=Count("id"))
        }
        failed_by_year = {
            int(r["exam__year"]): int(r["failed"] or 0)
            for r in qs.filter(passed=False)
            .values("exam__year")
            .annotate(failed=Count("id"))
        }
        by_year = {int(r["exam__year"]): r for r in rows}
        labels = [str(y) for y in years]
        participants, avg_scores, pass_rates, failed_counts = [], [], [], []
        for year in years:
            row = by_year.get(year)
            if not row:
                participants.append(0)
                avg_scores.append(None)
                pass_rates.append(None)
                failed_counts.append(0)
                continue
            students = int(row["students"] or 0)
            results = int(row["results"] or 0) or students
            passed = passed_by_year.get(year, 0)
            participants.append(students)
            avg_scores.append(round(float(row["avg_score"] or 0), 2) if results else None)
            pass_rates.append(round((passed / results) * 100, 1) if results else None)
            failed_counts.append(failed_by_year.get(year, 0))
        payload = {
            "labels": labels,
            "participants": participants,
            "avg_scores": avg_scores,
            "pass_rates": pass_rates,
            "failed_counts": failed_counts,
        }
        cache.set(cache_key, payload, 43200)
        return payload

    def _overview_extra(self, scope: dict, ege_stats, oge_stats, ege_risks, oge_risks, insights):
        cache_key = f"choice:overview_extra:{_scope_hash(scope)}"
        schools_payload = cache.get(cache_key)
        if schools_payload is None:
            user = self.request.user
            if user.role == "district" and user.district_id:
                schools_total = School.objects.filter(district_id=user.district_id).count()
                schools_with_data = (
                    ExamResult.objects.filter(**scope)
                    .values("student__school_id")
                    .distinct()
                    .count()
                )
            elif user.role == "school":
                schools_total = 1
                schools_with_data = 1 if (ege_stats["total_results"] or oge_stats["total_results"]) else 0
            elif user.role == "ministry":
                schools_total = School.objects.count()
                schools_with_data = (
                    ExamResult.objects.filter(**scope)
                    .values("student__school_id")
                    .distinct()
                    .count()
                )
            else:
                schools_total = 0
                schools_with_data = 0
            schools_payload = {
                "schools_total": schools_total,
                "schools_with_data": schools_with_data,
            }
            cache.set(cache_key, schools_payload, 43200)

        ege_failed = int(ege_stats.get("failed_count") or 0)
        oge_failed = int(oge_stats.get("failed_count") or 0)
        return {
            "schools_total": schools_payload["schools_total"],
            "schools_with_data": schools_payload["schools_with_data"],
            "schools_without_data": max(
                schools_payload["schools_total"] - schools_payload["schools_with_data"], 0
            ),
            "total_participants": int(ege_stats.get("unique_students") or ege_stats["total_results"])
            + int(oge_stats.get("unique_students") or oge_stats["total_results"]),
            "ege_risk_count": len(ege_risks),
            "oge_risk_count": len(oge_risks),
            "risk_total": len(ege_risks) + len(oge_risks),
            "ege_failed": ege_failed,
            "oge_failed": oge_failed,
            "failed_total": ege_failed + oge_failed,
            "subjects_ege": int(ege_stats["total_exams"]),
            "subjects_oge": int(oge_stats["total_exams"]),
            "best_subject": insights.get("best_subject"),
            "best_subject_score": insights.get("best_subject_score"),
            "overall_delta": insights.get("overall_delta"),
            "trend_label": insights.get("trend_label"),
            "data_year_label": str(COMPARISON_YEARS[-1]),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = self.request.user.role
        scope = _scope_for_user(self.request.user)
        role_title = "Организация"
        school_code = ""
        school_name = ""
        scope_label = "Текущая зона"
        if role == "school":
            school_id = _resolve_school_id_for_user(self.request.user)
            school = (
                School.objects.filter(id=school_id).only("name", "code").first() if school_id else None
            )
            school_name = school.name if school else "Школа"
            school_code = (school.code or "").strip() if school else ""
            role_title = school_name
            scope_label = f"Школа · код ОО {school_code}" if school_code else "Школа"
        elif role == "district":
            role_title = self.request.user.district.name if self.request.user.district_id else "Район"
            scope_label = role_title
        elif role == "ministry":
            role_title = self.request.user.ministry.name if self.request.user.ministry_id else "Министерство"
            scope_label = role_title
        context["role_title"] = role_title
        context["user_role"] = role
        context["school_code"] = school_code
        context["school_name"] = school_name
        context["scope_label"] = scope_label

        exam_filter = (self.request.GET.get("exam_type") or "all").strip().lower()
        if exam_filter not in ("all", "ege", "oge", "vpr"):
            exam_filter = "all"
        available_years = self._available_years(scope)
        selected_year = _parse_positive_int(self.request.GET.get("year"))
        if selected_year and available_years and selected_year not in available_years:
            selected_year = available_years[0] if available_years else None
        if not selected_year and available_years:
            selected_year = available_years[0]
        stats_year = selected_year or (available_years[0] if available_years else COMPARISON_YEARS[-1])
        context.update(self.build_hub_context(scope, exam_filter, stats_year, available_years))
        context["chart_data"] = self._chart_dataset(year=stats_year)
        return context


class DistrictSubjectComparisonView(LoginRequiredMixin, TemplateView):
    template_name = "users/district_subject_comparison.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != "district":
            return redirect("cabinet-exam-choice")
        if not request.user.district_id:
            return redirect("cabinet-exam-choice")
        return super().dispatch(request, *args, **kwargs)

    def _subject_variants(self, scope: dict, subject_name: str, exam_filter: str) -> list[str]:
        selected_key = _subject_group_key(subject_name)
        qs = ExamResult.objects.filter(**scope, exam__year__in=COMPARISON_YEARS)
        if exam_filter in {"ege", "oge"}:
            qs = qs.filter(exam__exam_type=exam_filter)
        subjects = [
            (value or "").strip()
            for value in qs.values_list("exam__subject", flat=True).distinct()
            if (value or "").strip()
        ]
        variants = [value for value in subjects if _subject_group_key(value) == selected_key]
        return sorted(set(variants or [subject_name]))

    def _passed_for_row(self, row: dict) -> bool:
        exam_type = (row.get("exam__exam_type") or "ege").strip().lower()
        if exam_type == "oge":
            return _oge_exam_passed(row.get("score"), row.get("passed"))
        return _ege_exam_passed(row, {})

    def _year_rows(self, qs):
        raw = list(
            qs.values(
                "exam__year",
                "exam__exam_type",
                "exam__subject",
                "exam__code",
                "score",
                "passed",
                "student_id",
            )
        )
        buckets = {year: {"students": set(), "scores": [], "passed": 0, "total": 0} for year in COMPARISON_YEARS}
        for row in raw:
            year = row.get("exam__year")
            if year not in buckets:
                continue
            bucket = buckets[year]
            bucket["students"].add(row.get("student_id"))
            bucket["scores"].append(float(row.get("score") or 0))
            bucket["total"] += 1
            if self._passed_for_row(row):
                bucket["passed"] += 1

        rows = []
        for year in COMPARISON_YEARS:
            bucket = buckets[year]
            total = bucket["total"]
            avg_score = round(sum(bucket["scores"]) / total, 2) if total else None
            pass_rate = round((bucket["passed"] / total) * 100, 1) if total else None
            rows.append(
                {
                    "year": year,
                    "students_count": len(bucket["students"]),
                    "results_count": total,
                    "avg_score": avg_score,
                    "pass_rate": pass_rate,
                }
            )
        return rows

    def _school_rows(self, qs, latest_year: int, district_avg: float | None):
        raw = list(
            qs.filter(exam__year=latest_year).values(
                "student__school_id",
                "student__school__name",
                "student__school__code",
                "exam__exam_type",
                "exam__subject",
                "exam__code",
                "exam__year",
                "score",
                "passed",
                "student_id",
            )
        )
        buckets = {}
        for row in raw:
            school_id = row.get("student__school_id")
            bucket = buckets.setdefault(
                school_id,
                {
                    "school_id": school_id,
                    "school_name": row.get("student__school__name") or "ОО не указана",
                    "school_code": row.get("student__school__code") or "",
                    "students": set(),
                    "scores": [],
                    "passed": 0,
                    "total": 0,
                },
            )
            bucket["students"].add(row.get("student_id"))
            bucket["scores"].append(float(row.get("score") or 0))
            bucket["total"] += 1
            if self._passed_for_row(row):
                bucket["passed"] += 1

        rows = []
        for bucket in buckets.values():
            total = bucket["total"]
            avg_score = round(sum(bucket["scores"]) / total, 2) if total else 0
            pass_rate = round((bucket["passed"] / total) * 100, 1) if total else 0
            delta = round(avg_score - district_avg, 2) if district_avg is not None else None
            if delta is None:
                status = "Нет сравнения"
            elif delta >= 5:
                status = "Лидер"
            elif delta <= -5:
                status = "Зона внимания"
            else:
                status = "Около среднего"
            rows.append(
                {
                    "school_id": bucket["school_id"],
                    "school_name": bucket["school_name"],
                    "school_code": bucket["school_code"],
                    "students": len(bucket["students"]),
                    "avg_score": avg_score,
                    "pass_rate": pass_rate,
                    "delta": delta,
                    "status": status,
                }
            )
        return sorted(rows, key=lambda item: (item["avg_score"], item["pass_rate"]), reverse=True)

    def _task_rows(self, scope: dict, subject_variants: list[str], latest_year: int, exam_filter: str):
        qs = TaskResult.objects.filter(
            **scope,
            exam__subject__in=subject_variants,
            exam__year=latest_year,
        )
        if exam_filter in {"ege", "oge"}:
            qs = qs.filter(exam__exam_type=exam_filter)
        rows = list(
            qs.values("task_number")
            .annotate(
                total=Count("id"),
                plus=Count("id", filter=~Q(value__in=["-", "0", ""])),
            )
            .order_by("task_number")
        )
        payload = []
        for row in rows:
            total = int(row["total"] or 0)
            plus = int(row["plus"] or 0)
            minus = max(total - plus, 0)
            success_rate = round((plus / total) * 100, 1) if total else 0
            payload.append(
                {
                    "task_number": row["task_number"],
                    "success_rate": success_rate,
                    "plus": plus,
                    "minus": minus,
                    "total": total,
                    "topic": _topic_for_task(subject_variants[0], row["task_number"], exam_filter if exam_filter in {"ege", "oge"} else "ege"),
                }
            )
        return sorted(payload, key=lambda item: item["success_rate"])

    def _analysis(self, subject_name: str, year_rows: list[dict], school_rows: list[dict], task_rows: list[dict], republic_avg):
        first = next((row for row in year_rows if row["avg_score"] is not None), None)
        latest = next((row for row in reversed(year_rows) if row["avg_score"] is not None), None)
        delta = None
        if first and latest and first["year"] != latest["year"]:
            delta = round(latest["avg_score"] - first["avg_score"], 2)

        insights = []
        if latest:
            insights.append(
                f"В {latest['year']} средний результат по предмету «{subject_name}» составил {latest['avg_score']}; "
                f"участников: {latest['students_count']}, сдаваемость: {latest['pass_rate']}%."
            )
        if delta is not None:
            direction = "рост" if delta > 0 else "снижение" if delta < 0 else "стабильность"
            insights.append(f"Динамика относительно первого года наблюдения: {direction} ({delta:+.2f} балла).")
        if republic_avg is not None and latest and latest["avg_score"] is not None:
            diff = round(latest["avg_score"] - republic_avg, 2)
            insights.append(f"Отклонение от общего среднего по базе за последний год: {diff:+.2f} балла.")
        if school_rows:
            weakest = [row for row in school_rows if row["status"] == "Зона внимания"][:3]
            if weakest:
                insights.append(
                    "Школы зоны внимания: "
                    + ", ".join(f"{row['school_name']} ({row['avg_score']})" for row in weakest)
                    + "."
                )
        if task_rows:
            weak_tasks = [row for row in task_rows if row["success_rate"] < 50][:5]
            if weak_tasks:
                insights.append(
                    "Критические задания: "
                    + ", ".join(f"№{row['task_number']} ({row['success_rate']}%)" for row in weak_tasks)
                    + "."
                )
        recommendations = [
            "Провести предметный разбор школ с отрицательным отклонением от среднего по району.",
            "Сформировать короткий план коррекции по заданиям с успешностью ниже 50%.",
            "Назначить контрольную диагностику через 4-6 недель и повторно сверить динамику.",
        ]
        return {"delta": delta, "insights": insights, "recommendations": recommendations}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject_name = (self.request.GET.get("subject") or "").strip()
        exam_filter = (self.request.GET.get("exam_type") or "all").strip().lower()
        if exam_filter not in {"all", "ege", "oge"}:
            exam_filter = "all"

        scope = _scope_for_user(self.request.user)
        subject_variants = self._subject_variants(scope, subject_name, exam_filter) if subject_name else []
        qs = ExamResult.objects.filter(**scope, exam__year__in=COMPARISON_YEARS)
        if subject_variants:
            qs = qs.filter(exam__subject__in=subject_variants)
        if exam_filter in {"ege", "oge"}:
            qs = qs.filter(exam__exam_type=exam_filter)

        year_rows = self._year_rows(qs)
        latest = next((row for row in reversed(year_rows) if row["avg_score"] is not None), None)
        latest_year = latest["year"] if latest else COMPARISON_YEARS[-1]
        district_avg = latest["avg_score"] if latest else None

        republic_qs = ExamResult.objects.filter(exam__year=latest_year)
        if subject_variants:
            republic_qs = republic_qs.filter(exam__subject__in=subject_variants)
        if exam_filter in {"ege", "oge"}:
            republic_qs = republic_qs.filter(exam__exam_type=exam_filter)
        republic_raw = republic_qs.aggregate(avg=Avg("score"))["avg"]
        republic_avg = round(float(republic_raw), 2) if republic_raw is not None else None

        school_rows = self._school_rows(qs, latest_year, district_avg)
        task_rows = self._task_rows(scope, subject_variants, latest_year, exam_filter) if subject_variants else []
        analysis = self._analysis(subject_name, year_rows, school_rows, task_rows, republic_avg)

        context.update(
            {
                "role_title": self.request.user.district.name if self.request.user.district_id else "Район",
                "subject_name": subject_name,
                "subject_variants": subject_variants,
                "exam_filter": exam_filter,
                "exam_filter_label": {"all": "ЕГЭ и ОГЭ", "ege": "ЕГЭ", "oge": "ОГЭ"}.get(exam_filter, "ЕГЭ и ОГЭ"),
                "comparison_years": list(COMPARISON_YEARS),
                "year_rows": year_rows,
                "latest_year": latest_year,
                "latest_row": latest,
                "district_avg": district_avg,
                "republic_avg": republic_avg,
                "school_rows": school_rows,
                "top_school_rows": school_rows[:5],
                "risk_school_rows": sorted(school_rows, key=lambda item: (item["avg_score"], item["pass_rate"]))[:5],
                "task_rows": task_rows,
                "weak_task_rows": [row for row in task_rows if row["success_rate"] < 50][:8],
                "analysis": analysis,
                "chart_data": {
                    "labels": [str(row["year"]) for row in year_rows],
                    "avg_scores": [row["avg_score"] for row in year_rows],
                    "pass_rates": [row["pass_rate"] for row in year_rows],
                    "participants": [row["students_count"] for row in year_rows],
                },
            }
        )
        return context


class OgePlaceholderView(LoginRequiredMixin, TemplateView):
    template_name = "users/oge_placeholder.html"


class VprPlaceholderView(LoginRequiredMixin, TemplateView):
    template_name = "users/vpr_placeholder.html"

    def get(self, request, *args, **kwargs):
        # Для ОО сразу открываем единый кабинет аналитики ВПР.
        if request.user.is_authenticated and request.user.role == "school":
            return redirect("vpr-school-analytics")
        if request.user.is_authenticated and request.user.role == "district":
            return redirect("/cabinet/district/?exam_type=vpr")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["role_title"] = "ВПР"
        return context


class SchoolUploadVprPlaceholderView(LoginRequiredMixin, TemplateView):
    template_name = "users/vpr_upload_placeholder.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role != "school":
            return redirect("cabinet")
        return super().dispatch(request, *args, **kwargs)


class OrganizationProfileView(LoginRequiredMixin, TemplateView):
    template_name = "users/profile.html"

    def _org_for_user(self):
        user = self.request.user
        if user.role == "ministry":
            return user.ministry
        if user.role == "district":
            return user.district
        if user.role == "school":
            return user.school
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self._org_for_user()
        context["user_role"] = self.request.user.role
        context["organization"] = org
        context["saved"] = self.request.GET.get("saved") == "1"
        context["error"] = self.request.GET.get("error") or ""
        return context

    def post(self, request, *args, **kwargs):
        org = self._org_for_user()
        if not org:
            return redirect("no-role")
        role = request.user.role
        try:
            if role == "ministry":
                org.name = (request.POST.get("name") or "").strip()
                org.save(update_fields=["name"])
            elif role == "district":
                org.name = (request.POST.get("name") or "").strip()
                org.code = (request.POST.get("code") or "").strip()
                org.save(update_fields=["name", "code"])
            elif role == "school":
                org.name = (request.POST.get("name") or "").strip()
                org.code = (request.POST.get("code") or "").strip()
                org.save(update_fields=["name", "code"])
        except IntegrityError:
            return redirect("/cabinet/profile/?error=Код уже используется")
        return redirect("/cabinet/profile/?saved=1")


class ReportsHubView(LoginRequiredMixin, TemplateView):
    template_name = "users/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_role"] = self.request.user.role
        report_doc = (self.request.GET.get("doc") or "").strip().lower()
        context["report_doc"] = report_doc
        report_nav_exam_type = (self.request.GET.get("exam_type") or "").strip().lower()
        if report_nav_exam_type not in {"ege", "oge"}:
            report_nav_exam_type = "ege"
        context["report_nav_exam_type"] = report_nav_exam_type

        if self.request.user.role == "district":
            district_id = self.request.user.district_id
            district = District.objects.filter(id=district_id).only("name", "code").first() if district_id else None
            context["district_name"] = district.name if district else ""
            district_year_options = list(
                Exam.objects.filter(results__student__school__district_id=district_id)
                .values_list("year", flat=True)
                .distinct()
                .order_by("-year")
            ) if district_id else []
            selected_year = (self.request.GET.get("year") or "").strip()
            if not (selected_year.isdigit() and int(selected_year) in district_year_options):
                selected_year = str(district_year_options[0]) if district_year_options else ""
            context["report_district_year_options"] = district_year_options
            context["report_selected_district_year"] = selected_year
            year_int = int(selected_year) if selected_year.isdigit() else None
            context["report_mo_options"] = [
                {"key": key, "title": meta["title"]} for key, meta in MO_SUBJECT_GROUPS.items()
            ]

            if report_doc == "subject-notes" and district_id:
                subject_options = sorted(
                    {
                        s
                        for s in ExamResult.objects.filter(
                            student__school__district_id=district_id,
                            exam__exam_type=report_nav_exam_type,
                        )
                        .values_list("exam__subject", flat=True)
                        if s
                    }
                )
                selected_subject = (self.request.GET.get("subject") or "").strip()
                if selected_subject not in subject_options:
                    selected_subject = subject_options[0] if subject_options else ""
                context["report_district_subject_options"] = subject_options
                context["report_selected_district_subject"] = selected_subject
                context["district_subject_note_payload"] = (
                    _build_district_subject_note_payload(
                        district_id,
                        report_nav_exam_type,
                        selected_subject,
                        year_int,
                        with_ai=False,
                    )
                    if selected_subject
                    else {"has_data": False, "message": "Выберите предмет."}
                )
                from users.report_ui.district_subject_note import (
                    build_district_subject_note_presentation,
                )

                context["district_subject_note_ui"] = build_district_subject_note_presentation(
                    context["district_subject_note_payload"]
                )
                return context

            if report_doc == "mo-report" and district_id:
                selected_mo = (self.request.GET.get("mo") or "").strip()
                if selected_mo not in MO_SUBJECT_GROUPS:
                    selected_mo = next(iter(MO_SUBJECT_GROUPS), "")
                context["report_selected_mo_key"] = selected_mo
                context["district_mo_report_payload"] = (
                    _build_district_mo_payload(
                        district_id, report_nav_exam_type, selected_mo, year_int, with_ai=False
                    )
                    if selected_mo
                    else {"has_data": False, "message": "Выберите профиль МО."}
                )
                return context

            district_doc_builders = {
                # Страницы: только метрики (без GigaChat). AI — при выгрузке DOCX.
                "gia-summary": ("district_summary_payload", _build_district_gia_summary_core),
                "info-stat": ("district_info_stat_payload", _build_district_info_stat_payload),
                "school-comparison": (
                    "district_school_comparison_payload",
                    lambda d, e, y: _build_district_school_comparison_payload(d, e, y, with_ai=False),
                ),
                "management-report": (
                    "district_management_payload",
                    lambda d, e, y: _build_district_management_payload(d, e, y, with_ai=False),
                ),
            }
            if report_doc == "analysis-note" and district_id:
                note_payload = _build_district_analytic_note_payload(
                    district_id, report_nav_exam_type, year_int
                )
                context["district_analysis_note_payload"] = note_payload
                from users.report_ui.district_analytic_note import (
                    build_district_analytic_note_presentation,
                )

                context["district_analysis_note_ui"] = build_district_analytic_note_presentation(
                    note_payload
                )
                return context
            if report_doc in district_doc_builders and district_id:
                ctx_key, builder = district_doc_builders[report_doc]
                context[ctx_key] = builder(district_id, report_nav_exam_type, year_int)
                if report_doc == "info-stat":
                    from users.report_ui.district_info_stat import (
                        build_district_info_stat_presentation,
                    )

                    context["district_info_stat_ui"] = build_district_info_stat_presentation(
                        context[ctx_key]
                    )
                return context

            context["report_total_count"] = 0
            context["report_exams"] = []
            return context

        if self.request.user.role == "school":
            school_id = _resolve_school_id_for_user(self.request.user)
            school = School.objects.filter(id=school_id).only("name").first() if school_id else None
            context["school_name"] = school.name if school else ""
            if report_doc == "gia-summary":
                summary_year_options = list(
                    Exam.objects.filter(results__student__school_id=school_id)
                    .values_list("year", flat=True)
                    .distinct()
                    .order_by("-year")
                )
                selected_summary_year = (self.request.GET.get("year") or "").strip()
                if not (selected_summary_year.isdigit() and int(selected_summary_year) in summary_year_options):
                    selected_summary_year = str(summary_year_options[0]) if summary_year_options else ""
                selected_summary_exam_type = report_nav_exam_type
                selected_class = (self.request.GET.get("class") or "").strip()
                selected_subject = (self.request.GET.get("subject") or "").strip()
                selected_student = (self.request.GET.get("student") or "").strip()

                context["report_selected_exam_type"] = selected_summary_exam_type
                context["report_summary_year_options"] = summary_year_options
                context["report_selected_summary_year"] = selected_summary_year

                if not selected_summary_year:
                    context["summary_has_data"] = False
                    context["summary_empty_message"] = "Недостаточно данных для формирования аналитического свода."
                    return context

                year_int = int(selected_summary_year)
                base_qs = ExamResult.objects.filter(
                    student__school_id=school_id,
                    exam__exam_type=selected_summary_exam_type,
                    exam__year=year_int,
                ).select_related("student", "exam", "student__school")
                if not base_qs.exists():
                    context["summary_has_data"] = False
                    context["summary_empty_message"] = "Недостаточно данных для формирования аналитического свода."
                    return context

                context["summary_has_data"] = True
                max_score = float(base_qs.aggregate(v=Max("score"))["v"] or 100)
                # Hard split: OGE metrics by grades, EGE metrics by points.
                is_oge_summary = selected_summary_exam_type == "oge"
                quality_threshold = 4 if is_oge_summary else 60
                high_threshold = 5 if is_oge_summary else 70
                risk_threshold = 3 if is_oge_summary else 50

                participants = base_qs.values("student_id").distinct().count()
                total_results = base_qs.count()
                avg_score = float(base_qs.aggregate(v=Avg("score"))["v"] or 0)
                ege_summary_cache: dict = {}
                ege_rows = None
                if not is_oge_summary:
                    ege_rows = list(
                        base_qs.values(
                            "exam__subject",
                            "exam__code",
                            "exam__year",
                            "score",
                            "passed",
                            "student_id",
                            "student__grade",
                        )
                    )
                if is_oge_summary:
                    oge_rows = list(base_qs.values("score", "passed", "student_id"))
                    passed = sum(1 for r in oge_rows if _oge_exam_passed(r.get("score"), r.get("passed")))
                    pass_rate = round((passed / total_results) * 100, 1) if total_results else 0.0
                    failed_count = max(total_results - passed, 0)
                    risk_ids = set()
                    for r in oge_rows:
                        score_v = float(r.get("score") or 0)
                        if (not _oge_exam_passed(score_v, r.get("passed"))) or score_v < risk_threshold:
                            sid = r.get("student_id")
                            if sid is not None:
                                risk_ids.add(sid)
                    risk_students = len(risk_ids)
                else:
                    passed = sum(1 for r in ege_rows if _ege_exam_passed(r, ege_summary_cache))
                    pass_rate = round((passed / total_results) * 100, 1) if total_results else 0.0
                    failed_count = max(total_results - passed, 0)
                    risk_ids = set()
                    for r in ege_rows:
                        if not _ege_exam_passed(r, ege_summary_cache) or float(r.get("score") or 0) < risk_threshold:
                            sid = r.get("student_id")
                            if sid is not None:
                                risk_ids.add(sid)
                    risk_students = len(risk_ids)
                quality_count = base_qs.filter(score__gte=quality_threshold).count()
                quality_rate = round((quality_count / total_results) * 100, 1) if total_results else 0.0
                high_count = base_qs.filter(score__gte=high_threshold).count()

                prev_qs = ExamResult.objects.filter(
                    student__school_id=school_id,
                    exam__exam_type=selected_summary_exam_type,
                    exam__year=year_int - 1,
                )
                prev_avg = float(prev_qs.aggregate(v=Avg("score"))["v"] or 0) if prev_qs.exists() else None
                avg_delta = round(avg_score - prev_avg, 2) if prev_avg is not None else None

                school = School.objects.filter(id=school_id).only("district_id").first()
                district_avg = None
                republic_avg = None
                if school and school.district_id:
                    district_qs = ExamResult.objects.filter(
                        student__school__district_id=school.district_id,
                        exam__exam_type=selected_summary_exam_type,
                        exam__year=year_int,
                    )
                    if district_qs.exists():
                        district_avg = round(float(district_qs.aggregate(v=Avg("score"))["v"] or 0), 2)
                republic_qs = ExamResult.objects.filter(exam__exam_type=selected_summary_exam_type, exam__year=year_int)
                if republic_qs.exists():
                    republic_avg = round(float(republic_qs.aggregate(v=Avg("score"))["v"] or 0), 2)

                if is_oge_summary:
                    by_subj_oge: dict[str, dict] = {}
                    for r in base_qs.values("exam__subject", "score", "passed"):
                        sn = r.get("exam__subject") or "Предмет не указан"
                        b = by_subj_oge.setdefault(
                            sn,
                            {
                                "exam__subject": sn,
                                "participants": 0,
                                "sum_score": 0.0,
                                "passed_n": 0,
                                "high_n": 0,
                                "min_v": None,
                                "max_v": None,
                            },
                        )
                        sc = float(r.get("score") or 0)
                        b["participants"] += 1
                        b["sum_score"] += sc
                        if _oge_exam_passed(sc, r.get("passed")):
                            b["passed_n"] += 1
                        if sc >= high_threshold:
                            b["high_n"] += 1
                        b["min_v"] = sc if b["min_v"] is None else min(b["min_v"], sc)
                        b["max_v"] = sc if b["max_v"] is None else max(b["max_v"], sc)
                    subject_rows = sorted(by_subj_oge.values(), key=lambda x: x["exam__subject"])
                    for row in subject_rows:
                        participants_subj = int(row["participants"] or 0)
                        row["avg"] = (row["sum_score"] / participants_subj) if participants_subj else 0.0
                        row["quality_rate"] = (
                            round((int(row["high_n"] or 0) / participants_subj) * 100, 1) if participants_subj else 0.0
                        )
                        row["pass_rate"] = (
                            round((int(row["passed_n"] or 0) / participants_subj) * 100, 1) if participants_subj else 0.0
                        )
                        row["risk_status"] = (
                            "critical" if row["pass_rate"] < 60 else "warning" if row["pass_rate"] < 75 else "ok"
                        )
                        row.pop("sum_score", None)
                        row.pop("passed_n", None)
                        row.pop("high_n", None)
                else:
                    by_subj: dict[str, dict] = {}
                    for r in ege_rows:
                        sn = r.get("exam__subject") or "Предмет не указан"
                        b = by_subj.setdefault(
                            sn,
                            {
                                "exam__subject": sn,
                                "participants": 0,
                                "sum_score": 0.0,
                                "passed_n": 0,
                                "high_n": 0,
                            },
                        )
                        sc = float(r.get("score") or 0)
                        b["participants"] += 1
                        b["sum_score"] += sc
                        if _ege_exam_passed(r, ege_summary_cache):
                            b["passed_n"] += 1
                        if sc >= high_threshold:
                            b["high_n"] += 1
                    subject_rows = sorted(by_subj.values(), key=lambda x: x["exam__subject"])
                    for row in subject_rows:
                        participants_subj = int(row["participants"] or 0)
                        row["avg"] = (row["sum_score"] / participants_subj) if participants_subj else 0.0
                        row["quality_rate"] = round((int(row["high_n"] or 0) / participants_subj) * 100, 1) if participants_subj else 0.0
                        row["pass_rate"] = round((int(row["passed_n"] or 0) / participants_subj) * 100, 1) if participants_subj else 0.0
                        row["risk_status"] = (
                            "critical" if row["pass_rate"] < 60 else "warning" if row["pass_rate"] < 75 else "ok"
                        )
                        row.pop("sum_score", None)
                        row.pop("passed_n", None)
                        row.pop("high_n", None)

                weak_subjects = sorted(
                    [
                        row
                        for row in subject_rows
                        if _is_weak_subject_row(
                            row,
                            exam_type=selected_summary_exam_type,
                            max_score=max_score,
                            pass_rate_threshold=75,
                        )
                    ],
                    key=lambda x: (x["pass_rate"], float(x["avg"] or 0)),
                )

                if is_oge_summary:
                    by_cls_oge: dict[str, dict] = {}
                    for r in base_qs.values("student__grade", "score", "passed"):
                        cn = r.get("student__grade") or "Класс не указан"
                        b = by_cls_oge.setdefault(
                            cn,
                            {
                                "student__grade": cn,
                                "participants": 0,
                                "sum_score": 0.0,
                                "passed_n": 0,
                                "risk_n": 0,
                            },
                        )
                        sc = float(r.get("score") or 0)
                        b["participants"] += 1
                        b["sum_score"] += sc
                        if _oge_exam_passed(sc, r.get("passed")):
                            b["passed_n"] += 1
                        if sc < risk_threshold:
                            b["risk_n"] += 1
                    class_rows = list(by_cls_oge.values())
                    for row in class_rows:
                        participants_cls = int(row["participants"] or 0)
                        row["avg"] = (row["sum_score"] / participants_cls) if participants_cls else 0.0
                        row["pass_rate"] = (
                            round((int(row["passed_n"] or 0) / participants_cls) * 100, 1) if participants_cls else 0.0
                        )
                        row["risk_rate"] = (
                            round((int(row["risk_n"] or 0) / participants_cls) * 100, 1) if participants_cls else 0.0
                        )
                        row.pop("sum_score", None)
                        row.pop("passed_n", None)
                        row.pop("risk_n", None)
                    class_rows.sort(key=lambda x: (-float(x.get("avg") or 0), str(x.get("student__grade") or "")))
                else:
                    by_cls: dict[str, dict] = {}
                    for r in ege_rows:
                        cn = r.get("student__grade") or "Класс не указан"
                        b = by_cls.setdefault(
                            cn,
                            {
                                "student__grade": cn,
                                "participants": 0,
                                "sum_score": 0.0,
                                "passed_n": 0,
                                "risk_n": 0,
                            },
                        )
                        sc = float(r.get("score") or 0)
                        b["participants"] += 1
                        b["sum_score"] += sc
                        if _ege_exam_passed(r, ege_summary_cache):
                            b["passed_n"] += 1
                        if sc < risk_threshold:
                            b["risk_n"] += 1
                    class_rows = list(by_cls.values())
                    for row in class_rows:
                        participants_cls = int(row["participants"] or 0)
                        row["avg"] = (row["sum_score"] / participants_cls) if participants_cls else 0.0
                        row["pass_rate"] = round((int(row["passed_n"] or 0) / participants_cls) * 100, 1) if participants_cls else 0.0
                        row["risk_rate"] = round((int(row["risk_n"] or 0) / participants_cls) * 100, 1) if participants_cls else 0.0
                        row.pop("sum_score", None)
                        row.pop("passed_n", None)
                        row.pop("risk_n", None)
                    class_rows.sort(key=lambda x: (-float(x.get("avg") or 0), str(x.get("student__grade") or "")))

                class_options = sorted({(row["student__grade"] or "").strip() for row in class_rows if (row["student__grade"] or "").strip()})
                subject_options = [row["exam__subject"] for row in subject_rows]
                if selected_class and selected_class not in class_options:
                    selected_class = ""
                if selected_subject and selected_subject not in subject_options:
                    selected_subject = ""

                detail_qs = base_qs
                if selected_class:
                    detail_qs = detail_qs.filter(student__grade=selected_class)
                if selected_subject:
                    detail_qs = detail_qs.filter(exam__subject=selected_subject)

                if is_oge_summary:
                    students_rows = list(
                        detail_qs.values("student_id", "student__full_name", "student_name", "student__grade")
                        .annotate(avg=Avg("score"), results=Count("id"), failed=Count("id", filter=Q(passed=False)))
                        .order_by("-failed", "avg", "student__full_name")
                    )
                else:
                    drows = list(
                        detail_qs.values(
                            "student_id",
                            "student__full_name",
                            "student_name",
                            "student__grade",
                            "exam__subject",
                            "exam__year",
                            "score",
                            "passed",
                        )
                    )
                    by_stu: dict[int, dict] = {}
                    for r in drows:
                        sid = r.get("student_id")
                        if sid is None:
                            continue
                        b = by_stu.setdefault(
                            sid,
                            {
                                "student_id": sid,
                                "student__full_name": r.get("student__full_name"),
                                "student_name": r.get("student_name"),
                                "student__grade": r.get("student__grade"),
                                "sum_score": 0.0,
                                "results": 0,
                                "failed": 0,
                            },
                        )
                        sc = float(r.get("score") or 0)
                        b["sum_score"] += sc
                        b["results"] += 1
                        if not _ege_exam_passed(r, ege_summary_cache):
                            b["failed"] += 1
                    students_rows = []
                    for b in by_stu.values():
                        n = int(b["results"] or 0)
                        students_rows.append(
                            {
                                "student_id": b["student_id"],
                                "student__full_name": b.get("student__full_name"),
                                "student_name": b.get("student_name"),
                                "student__grade": b.get("student__grade"),
                                "avg": (b["sum_score"] / n) if n else 0.0,
                                "results": n,
                                "failed": int(b["failed"] or 0),
                            }
                        )
                    students_rows.sort(
                        key=lambda x: (-int(x.get("failed") or 0), float(x.get("avg") or 0), str(x.get("student__full_name") or ""))
                    )

                risk_students_rows = [row for row in students_rows if int(row["failed"] or 0) > 0 or float(row["avg"] or 0) < risk_threshold][:20]
                if selected_student and not any(str(row["student_id"]) == selected_student for row in students_rows):
                    selected_student = ""
                student_detail_rows = []
                if selected_student.isdigit():
                    student_detail_rows = list(
                        detail_qs.filter(student_id=int(selected_student))
                        .values("exam__subject", "score", "passed", "exam__code", "exam__exam_date")
                        .order_by("exam__subject", "exam__exam_date")
                    )

                task_qs = TaskResult.objects.filter(
                    student__school_id=school_id,
                    exam__exam_type=selected_summary_exam_type,
                    exam__year=year_int,
                )
                if selected_subject:
                    task_qs = task_qs.filter(exam__subject=selected_subject)
                task_rows = list(
                    task_qs.values("exam__subject", "task_number")
                    .annotate(
                        total=Count("id"),
                        plus=Count("id", filter=~Q(value__in=["-", "0", ""])),
                    )
                    .order_by("exam__subject", "task_number")
                )
                for row in task_rows:
                    total_task = int(row["total"] or 0)
                    plus_task = int(row["plus"] or 0)
                    row["success_rate"] = round((plus_task / total_task) * 100, 1) if total_task else 0.0
                    sr = float(row.get("success_rate") or 0)
                    row["risk"] = (
                        "Высокий" if sr < 40 else "Средний" if sr < 60 else "Низкий"
                    )
                    row["analysis"] = (
                        "Критическое задание, требуется приоритетная методическая отработка."
                        if row["success_rate"] < 40
                        else "Зона внимания, требуется дополнительная практика."
                        if row["success_rate"] < 60
                        else "Стабильный результат."
                    )
                weak_tasks = sorted(task_rows, key=lambda x: x["success_rate"])[:12]

                ai_insights = []
                if avg_delta is not None:
                    if avg_delta > 0:
                        ai_insights.append(f"Отмечается рост среднего балла на {avg_delta} п. относительно {year_int - 1} года.")
                    elif avg_delta < 0:
                        ai_insights.append(f"Отмечается снижение среднего балла на {abs(avg_delta)} п. относительно {year_int - 1} года.")
                if weak_subjects:
                    ai_insights.append("Наиболее проблемные предметы: " + ", ".join((r["exam__subject"] or "предмет") for r in weak_subjects[:3]) + ".")
                if weak_tasks:
                    ai_insights.append("Критические задания КИМ: " + ", ".join(f"{row['exam__subject']} №{row['task_number']}" for row in weak_tasks[:5]) + ".")
                if risk_students:
                    ai_insights.append(f"Выявлена группа риска: {risk_students} обучающихся.")

                recommendations = []
                if weak_subjects:
                    recommendations.append(
                        "Адресная подготовка по предметам: "
                        + ", ".join(
                            f"{(r.get('exam__subject') or 'предмет')} (усп. {r.get('pass_rate')}%)"
                            for r in weak_subjects[:4]
                        )
                        + "."
                    )
                if weak_tasks:
                    recommendations.append(
                        "Drill-down по заданиям КИМ: "
                        + ", ".join(
                            f"{row['exam__subject']} №{row['task_number']}"
                            for row in weak_tasks[:5]
                        )
                        + "."
                    )
                if risk_students:
                    recommendations.append(
                        f"Индивидуальные маршруты для группы риска: {risk_students} обучающихся."
                    )
                if avg_delta is not None and avg_delta < 0:
                    recommendations.append(
                        f"Остановить снижение среднего балла относительно {year_int - 1} года ({avg_delta:+})."
                    )
                if not recommendations:
                    recommendations.append(
                        f"Поддерживать текущий уровень: средний {round(avg_score, 2)}, успеваемость {pass_rate}%."
                    )
                # Без GigaChat на странице отчёта: только тексты из фактических метрик БД.

                context["summary_kpis"] = {
                    "participants": participants,
                    "total_results": total_results,
                    "avg_score": round(avg_score, 2),
                    "avg_label": "Средняя оценка" if is_oge_summary else "Средний балл",
                    "quality_rate": quality_rate,
                    "pass_rate": pass_rate,
                    "high_count": high_count,
                    "high_label": "Отличники (оценка 5)" if is_oge_summary else "Высокобалльники (70+)",
                    "failed_count": failed_count,
                    "failed_label": "Оценка 2" if is_oge_summary else "Неудовлетворительные результаты",
                    "risk_students": risk_students,
                    "avg_delta": avg_delta,
                    "district_avg": district_avg,
                    "republic_avg": republic_avg,
                    "model_label": "ОГЭ: модель оценок (2-5)" if is_oge_summary else "ЕГЭ: модель тестовых баллов (0-100)",
                }
                context["summary_subject_rows"] = subject_rows
                context["summary_class_rows"] = class_rows
                context["summary_weak_subjects"] = weak_subjects[:10]
                context["summary_task_rows"] = task_rows
                context["summary_weak_tasks"] = weak_tasks
                context["summary_ai_insights"] = ai_insights
                context["summary_recommendations"] = recommendations
                context["summary_class_options"] = class_options
                context["summary_subject_options"] = subject_options
                context["summary_selected_class"] = selected_class
                context["summary_selected_subject"] = selected_subject
                context["summary_students_rows"] = students_rows[:50]
                context["summary_risk_students_rows"] = risk_students_rows
                context["summary_selected_student"] = selected_student
                context["summary_student_detail_rows"] = student_detail_rows
                context["summary_distribution"] = (
                    [
                        {"label": "2", "value": base_qs.filter(score__lt=3).count()},
                        {"label": "3", "value": base_qs.filter(score__gte=3, score__lt=4).count()},
                        {"label": "4", "value": base_qs.filter(score__gte=4, score__lt=5).count()},
                        {"label": "5", "value": base_qs.filter(score__gte=5).count()},
                    ]
                    if is_oge_summary
                    else [
                        {"label": "0-35", "value": base_qs.filter(score__lte=35).count()},
                        {"label": "36-60", "value": base_qs.filter(score__gt=35, score__lte=60).count()},
                        {"label": "61-80", "value": base_qs.filter(score__gt=60, score__lte=80).count()},
                        {"label": "81-100", "value": base_qs.filter(score__gt=80).count()},
                    ]
                )
                # Динамика: те же правила сдачи, что и KPI свода (ЕГЭ — порог, ОГЭ — оценка ≥ 3).
                dyn_cache: dict = {}
                dyn_out = []
                for y in [year_int - 2, year_int - 1, year_int]:
                    y_qs = ExamResult.objects.filter(
                        student__school_id=school_id,
                        exam__exam_type=selected_summary_exam_type,
                        exam__year=y,
                    )
                    if not y_qs.exists():
                        continue
                    results_d = y_qs.count()
                    students_d = y_qs.values("student_id").distinct().count()
                    avg_d = float(y_qs.aggregate(v=Avg("score"))["v"] or 0)
                    yr_rows = list(
                        y_qs.values("exam__subject", "exam__code", "exam__year", "score", "passed")
                    )
                    if is_oge_summary:
                        passed_d = sum(1 for r in yr_rows if _oge_exam_passed(r.get("score"), r.get("passed")))
                    else:
                        passed_d = sum(1 for r in yr_rows if _ege_exam_passed(r, dyn_cache))
                    dyn_out.append(
                        {
                            "year": int(y),
                            "avg": round(avg_d, 2),
                            "pass_rate": round((passed_d / results_d) * 100, 1) if results_d else 0.0,
                            "participants": students_d,
                            "students": students_d,
                            "results": results_d,
                        }
                    )
                context["summary_dynamics"] = dyn_out
                context["summary_ui"] = build_gia_summary_presentation(
                    exam_type=selected_summary_exam_type,
                    year=selected_summary_year,
                    kpis=context.get("summary_kpis"),
                    distribution=context.get("summary_distribution"),
                    subject_rows=context.get("summary_subject_rows"),
                    dynamics=context.get("summary_dynamics"),
                )
                return context
            if report_doc == "info-stat":
                info_year_options = list(
                    Exam.objects.filter(results__student__school_id=school_id)
                    .values_list("year", flat=True)
                    .distinct()
                    .order_by("-year")
                )
                selected_info_year = (self.request.GET.get("year") or "").strip()
                if not (selected_info_year.isdigit() and int(selected_info_year) in info_year_options):
                    selected_info_year = str(info_year_options[0]) if info_year_options else ""
                selected_info_exam_type = report_nav_exam_type
                context["report_info_year_options"] = info_year_options
                context["report_selected_info_year"] = selected_info_year
                context["report_selected_info_exam_type"] = selected_info_exam_type
                info_payload = _build_school_info_stat_payload(
                    school_id=school_id,
                    exam_type=selected_info_exam_type,
                    year=int(selected_info_year) if selected_info_year.isdigit() else None,
                )
                context["info_stat_payload"] = info_payload
                from users.report_ui.school_info_stat import build_info_stat_presentation

                context["info_stat_ui"] = build_info_stat_presentation(info_payload)
                return context
            if report_doc == "analysis-note":
                note_year_options = list(
                    Exam.objects.filter(
                        results__student__school_id=school_id,
                        exam_type=report_nav_exam_type,
                    )
                    .values_list("year", flat=True)
                    .distinct()
                    .order_by("-year")
                )
                selected_note_year = (self.request.GET.get("year") or "").strip()
                if not (selected_note_year.isdigit() and int(selected_note_year) in note_year_options):
                    selected_note_year = str(note_year_options[0]) if note_year_options else ""
                selected_note_exam_type = report_nav_exam_type
                context["report_note_year_options"] = note_year_options
                context["report_selected_note_year"] = selected_note_year
                context["report_selected_note_exam_type"] = selected_note_exam_type
                note_payload = _build_school_analytic_note_payload(
                    school_id=school_id,
                    exam_type=selected_note_exam_type,
                    year=int(selected_note_year) if selected_note_year.isdigit() else None,
                )
                context["analytic_note_payload"] = note_payload
                from users.report_ui.school_analytic_note import build_analytic_note_presentation

                context["analytic_note_ui"] = build_analytic_note_presentation(note_payload)
                return context
            if report_doc == "subject-notes":
                subject_year_options = list(
                    Exam.objects.filter(results__student__school_id=school_id)
                    .values_list("year", flat=True)
                    .distinct()
                    .order_by("-year")
                )
                selected_exam_type = report_nav_exam_type
                subject_options = list(
                    Exam.objects.filter(
                        results__student__school_id=school_id,
                        exam_type=selected_exam_type,
                    )
                    .values_list("subject", flat=True)
                    .distinct()
                    .order_by("subject")
                )
                selected_year = (self.request.GET.get("year") or "").strip()
                if not (selected_year.isdigit() and int(selected_year) in subject_year_options):
                    selected_year = str(subject_year_options[0]) if subject_year_options else ""
                selected_subject = (self.request.GET.get("subject") or "").strip()
                if selected_subject and selected_subject not in subject_options:
                    selected_subject = ""
                if not selected_subject and subject_options:
                    selected_subject = subject_options[0]
                context["report_subject_year_options"] = subject_year_options
                context["report_subject_options"] = subject_options
                context["report_selected_subject_year"] = selected_year
                context["report_selected_subject_exam_type"] = selected_exam_type
                context["report_selected_subject_name"] = selected_subject
                subject_payload = _build_school_subject_note_payload(
                    school_id=school_id,
                    exam_type=selected_exam_type,
                    subject=selected_subject,
                    year=int(selected_year) if selected_year.isdigit() else None,
                )
                context["subject_note_payload"] = subject_payload
                return context
            if report_doc == "mo-report":
                mo_year_options = list(
                    Exam.objects.filter(results__student__school_id=school_id)
                    .values_list("year", flat=True)
                    .distinct()
                    .order_by("-year")
                )
                selected_year = (self.request.GET.get("year") or "").strip()
                if not (selected_year.isdigit() and int(selected_year) in mo_year_options):
                    selected_year = str(mo_year_options[0]) if mo_year_options else ""
                selected_exam_type = report_nav_exam_type
                selected_mo = (self.request.GET.get("mo") or "").strip().lower()
                if selected_mo not in MO_SUBJECT_GROUPS:
                    selected_mo = "math-mo"
                context["report_mo_year_options"] = mo_year_options
                context["report_selected_mo_year"] = selected_year
                context["report_selected_mo_exam_type"] = selected_exam_type
                context["report_selected_mo_key"] = selected_mo
                context["report_mo_options"] = [{"key": key, "title": meta["title"]} for key, meta in MO_SUBJECT_GROUPS.items()]
                mo_payload = _build_school_mo_payload(
                    school_id=school_id,
                    exam_type=selected_exam_type,
                    mo_key=selected_mo,
                    year=int(selected_year) if selected_year.isdigit() else None,
                )
                context["mo_report_payload"] = mo_payload
                return context
            if report_doc == "deputy-report":
                selected_exam_type = report_nav_exam_type
                deputy_year_options = list(
                    Exam.objects.filter(results__student__school_id=school_id, exam_type=selected_exam_type)
                    .values_list("year", flat=True)
                    .distinct()
                    .order_by("-year")
                )
                selected_year = (self.request.GET.get("year") or "").strip()
                if not (selected_year.isdigit() and int(selected_year) in deputy_year_options):
                    selected_year = str(deputy_year_options[0]) if deputy_year_options else ""
                context["report_deputy_year_options"] = deputy_year_options
                context["report_selected_deputy_year"] = selected_year
                context["report_selected_deputy_exam_type"] = selected_exam_type
                context["deputy_report_payload"] = _build_school_deputy_report_payload(
                    school_id=school_id,
                    exam_type=selected_exam_type,
                    year=int(selected_year) if selected_year.isdigit() else None,
                )
                return context

            exams_qs = (
                Exam.objects.filter(results__student__school_id=school_id)
                .annotate(students=Count("results__id"))
                .order_by("-year", "exam_type", "subject", "-exam_date")
                .distinct()
            )

            selected_year = (self.request.GET.get("year") or "").strip()
            selected_exam_type = report_nav_exam_type
            selected_subject = (self.request.GET.get("subject") or "").strip()
            search = (self.request.GET.get("q") or "").strip()

            if selected_year.isdigit():
                exams_qs = exams_qs.filter(year=int(selected_year))
            else:
                selected_year = ""
            exams_qs = exams_qs.filter(exam_type=selected_exam_type)

            year_options = list(
                Exam.objects.filter(results__student__school_id=school_id)
                .values_list("year", flat=True)
                .distinct()
                .order_by("-year")
            )
            subject_options = list(
                Exam.objects.filter(
                    results__student__school_id=school_id,
                    exam_type=selected_exam_type,
                )
                .values_list("subject", flat=True)
                .distinct()
                .order_by("subject")
            )
            if selected_subject and selected_subject not in subject_options:
                selected_subject = ""
            if selected_subject:
                exams_qs = exams_qs.filter(subject=selected_subject)
            if search:
                exams_qs = exams_qs.filter(subject__icontains=search)

            # Все предметы текущего типа (ЕГЭ/ОГЭ) — без постраничного обрезания
            exams_list = list(exams_qs)
            context["report_exams"] = exams_list
            context["report_page_obj"] = None
            context["report_paginator"] = None
            context["report_total_count"] = len(exams_list)
            context["report_year_options"] = year_options
            context["report_subject_options"] = subject_options
            context["report_selected_year"] = selected_year
            context["report_selected_exam_type"] = selected_exam_type
            context["report_selected_subject"] = selected_subject
            context["report_search"] = search
        else:
            context["report_exams"] = []
        return context


class RoleDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "users/role_dashboard.html"
    required_role = None
    role_title = ""
    include_default_metrics = True

    def dispatch(self, request, *args, **kwargs):
        if not request.user.role and not request.user.is_superuser:
            return redirect("no-role")
        if self.required_role and request.user.role != self.required_role:
            return redirect("cabinet")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exam_type = (self.request.GET.get("exam_type") or "ege").strip().lower()
        if exam_type not in {"ege", "oge", "vpr"}:
            exam_type = "ege"
        scope_filter = _scope_for_user(self.request.user)
        scope_filter = {**scope_filter, "exam__exam_type": exam_type}
        if self.include_default_metrics:
            selected_exam_id = self.request.GET.get("exam")
            if selected_exam_id and selected_exam_id.isdigit():
                scope_filter = {**scope_filter, "exam_id": int(selected_exam_id)}
            context["metrics"] = exam_overview(scope_filter)
        context["role_title"] = self.role_title
        context["user_role"] = self.request.user.role
        context["selected_exam_type"] = exam_type
        context["selected_exam_type_label"] = {
            "ege": "ЕГЭ",
            "oge": "ОГЭ",
            "vpr": "ВПР",
        }.get(exam_type, "ЕГЭ")
        if self.request.user.role == "district" and self.request.user.district_id:
            context["district_schools"] = School.objects.filter(
                district_id=self.request.user.district_id
            ).order_by("name")
        return context


class MinistryDashboardView(RoleDashboardView):
    required_role = "ministry"
    role_title = "Кабинет Министерства"
    template_name = "users/ministry_dashboard.html"

    def _ministry_district_results(self, exam_type: str, year: int | None = None):
        scope = _scope_for_user(self.request.user)
        cache_key = f"cabinet:ministry:district_results:{exam_type}:{year or 'all'}:{_scope_hash(scope)}"

        def _build():
            qs = ExamResult.objects.filter(exam__exam_type=exam_type, **scope)
            if year:
                qs = qs.filter(exam__year=year)
            rows = (
                qs.values("student__school__district_id", "student__school__district__code", "student__school__district__name")
                .annotate(
                    students=Count("student_id", distinct=True),
                    results=Count("id"),
                    exams=Count("exam_id", distinct=True),
                    avg_score=Avg("score"),
                    passed=Count("id", filter=Q(passed=True)),
                )
                .order_by("student__school__district__name")
            )
            out = []
            for row in rows:
                students = int(row["students"] or 0)
                results = int(row["results"] or 0) or students
                pass_rate = round((int(row["passed"] or 0) / results) * 100, 1) if results else 0.0
                out.append(
                    {
                        "district_id": row["student__school__district_id"],
                        "district_code": row["student__school__district__code"] or "-",
                        "district_name": row["student__school__district__name"] or "Район без названия",
                        "students": students,
                        "exams": int(row["exams"] or 0),
                        "avg_score": round(float(row["avg_score"] or 0), 2),
                        "pass_rate": pass_rate,
                    }
                )
            return out

        return _cache_get_or_set(cache_key, 900, _build)

    def _ministry_district_school_results(self, district_id: int, exam_type: str, year: int | None = None):
        scope = _scope_for_user(self.request.user)
        cache_key = (
            f"cabinet:ministry:district_school_results:{district_id}:{exam_type}:{year or 'all'}:{_scope_hash(scope)}"
        )

        def _build():
            qs = ExamResult.objects.filter(
                exam__exam_type=exam_type,
                student__school__district_id=district_id,
                **scope,
            )
            if year:
                qs = qs.filter(exam__year=year)
            rows = (
                qs.values("student__school_id", "student__school__code", "student__school__name")
                .annotate(
                    students=Count("student_id", distinct=True),
                    results=Count("id"),
                    exams=Count("exam_id", distinct=True),
                    avg_score=Avg("score"),
                    passed=Count("id", filter=Q(passed=True)),
                )
                .order_by("student__school__name")
            )
            out = []
            for row in rows:
                students = int(row["students"] or 0)
                results = int(row["results"] or 0) or students
                pass_rate = round((int(row["passed"] or 0) / results) * 100, 1) if results else 0.0
                out.append(
                    {
                        "school_id": row["student__school_id"],
                        "school_code": row["student__school__code"] or "-",
                        "school_name": row["student__school__name"] or "Школа без названия",
                        "students": students,
                        "exams": int(row["exams"] or 0),
                        "avg_score": round(float(row["avg_score"] or 0), 2),
                        "pass_rate": pass_rate,
                    }
                )
            return out

        return _cache_get_or_set(cache_key, 900, _build)

    def _ministry_school_subject_results(
        self,
        district_id: int,
        school_id: int,
        exam_type: str,
        year: int | None = None,
    ):
        scope = _scope_for_user(self.request.user)
        cache_key = (
            f"cabinet:ministry:school_subject_results:{district_id}:{school_id}:{exam_type}:{year or 'all'}:{_scope_hash(scope)}"
        )

        def _build():
            qs = ExamResult.objects.filter(
                exam__exam_type=exam_type,
                student__school__district_id=district_id,
                student__school_id=school_id,
                **scope,
            )
            if year:
                qs = qs.filter(exam__year=year)
            rows = list(
                qs.values("exam__subject")
                .annotate(
                    students=Count("student_id", distinct=True),
                    results=Count("id"),
                    exams=Count("exam_id", distinct=True),
                    avg_score=Avg("score"),
                )
                .order_by("exam__subject")
            )

            # Prefer using stored `passed` flag; threshold logic can be expensive on large slices.
            passed_by_subject = {}
            results_by_subject = {}
            for row in qs.values("exam__subject").annotate(
                passed=Count("id", filter=Q(passed=True)),
                results=Count("id"),
            ):
                subject_name = row.get("exam__subject") or "Предмет не указан"
                passed_by_subject[subject_name] = int(row.get("passed") or 0)
                results_by_subject[subject_name] = int(row.get("results") or 0)

            out = []
            for row in rows:
                students = int(row["students"] or 0)
                subject_name = row["exam__subject"] or "Предмет не указан"
                results = int(results_by_subject.get(subject_name) or row.get("results") or 0) or students
                passed_count = int(passed_by_subject.get(subject_name, 0))
                pass_rate = round((passed_count / results) * 100, 1) if results else 0.0
                out.append(
                    {
                        "subject": subject_name,
                        "students": students,
                        "exams": int(row["exams"] or 0),
                        "avg_score": round(float(row["avg_score"] or 0), 2),
                        "pass_rate": pass_rate,
                    }
                )
            return out

        return _cache_get_or_set(cache_key, 900, _build)

    def _ministry_subject_students(
        self,
        district_id: int,
        school_id: int,
        exam_type: str,
        subject_name: str,
        year: int | None = None,
    ):
        scope = _scope_for_user(self.request.user)
        qs = (
            ExamResult.objects.filter(
                exam__exam_type=exam_type,
                exam__subject=subject_name,
                student__school__district_id=district_id,
                student__school_id=school_id,
                **scope,
            )
            .select_related("exam", "student")
            .order_by("exam__exam_date", "student_name", "student__full_name")
        )
        if year:
            qs = qs.filter(exam__year=year)

        threshold_cache: dict = {}
        out = []
        for result in qs:
            below_minimum = _exam_result_below_minimum(result, exam_type, threshold_cache)
            out.append(
                {
                    "student_name": result.student_name or result.student.full_name,
                    "short_answer_tasks": result.short_answer_tasks,
                    "long_answer_tasks": result.long_answer_tasks,
                    "primary_score": result.primary_score,
                    "score": result.score,
                    "exam_date": result.exam.exam_date,
                    "exam_code": result.exam.code,
                    "below_minimum": below_minimum,
                }
            )
        return out

    def _ministry_subject_task_rows(
        self,
        district_id: int,
        school_id: int,
        exam_type: str,
        subject_name: str,
        year: int | None = None,
    ):
        scope = _scope_for_user(self.request.user)
        qs = TaskResult.objects.filter(
            exam__exam_type=exam_type,
            exam__subject=subject_name,
            student__school__district_id=district_id,
            student__school_id=school_id,
            **scope,
        )
        if year:
            qs = qs.filter(exam__year=year)

        raw_task_values = list(qs.values("task_number", "value").order_by("task_number"))
        task_agg = {}
        for row in raw_task_values:
            task_num = row["task_number"]
            bucket = task_agg.setdefault(task_num, {"total": 0, "plus": 0, "minus": 0})
            bucket["total"] += 1
            if _is_success_token(row["value"]):
                bucket["plus"] += 1
            else:
                bucket["minus"] += 1

        task_rows = []
        for task_num in sorted(task_agg):
            row = task_agg[task_num]
            total = row["total"]
            plus = row["plus"]
            minus = row["minus"]
            success_rate = round((plus / total) * 100, 1) if total else 0
            task_rows.append(
                {
                    "task_number": task_num,
                    "success_rate": success_rate,
                    "plus": plus,
                    "minus": minus,
                    "total": total,
                }
            )
        return task_rows

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scope = _scope_for_user(self.request.user)
        selected_exam_type = context.get("selected_exam_type", "ege")

        def _exam_stats_payload(exam_type: str):
            results = ExamResult.objects.filter(exam__exam_type=exam_type, **scope)
            total_results = results.count()
            unique_students = results.values("student_id").distinct().count()
            total_exams = results.values("exam_id").distinct().count()
            avg_score = results.aggregate(value=Avg("score"))["value"] or 0
            passed_count = results.filter(passed=True).count()
            pass_rate = round((passed_count / total_results) * 100, 1) if total_results else 0
            return {
                "total_results": total_results,
                "unique_students": unique_students,
                "total_exams": total_exams,
                "avg_score": round(avg_score, 2),
                "pass_rate": pass_rate,
            }

        def _comparison_insights_payload(comparison_rows, years_span: tuple[int, ...]):
            if not comparison_rows or not years_span:
                return {
                    "overall_avg": 0,
                    "overall_delta": None,
                    "best_subject": None,
                    "best_subject_score": None,
                    "participants_latest_year": 0,
                    "top_growth_subject": None,
                    "top_growth_delta": None,
                    "top_decline_subject": None,
                    "top_decline_delta": None,
                    "trend_label": "Недостаточно данных",
                }

            year_totals = {year: {"weighted_sum": 0.0, "students": 0} for year in years_span}
            for row in comparison_rows:
                for item in row["years"]:
                    if item["avg_score"] is None or not item["students_count"]:
                        continue
                    y = item["year"]
                    if y not in year_totals:
                        continue
                    year_totals[y]["weighted_sum"] += float(item["avg_score"]) * item["students_count"]
                    year_totals[y]["students"] += item["students_count"]

            latest_year = years_span[-1]
            earliest_year = years_span[0]
            latest_avg = (
                year_totals[latest_year]["weighted_sum"] / year_totals[latest_year]["students"]
                if year_totals[latest_year]["students"]
                else None
            )
            earliest_avg = (
                year_totals[earliest_year]["weighted_sum"] / year_totals[earliest_year]["students"]
                if year_totals[earliest_year]["students"]
                else None
            )
            overall_avg = round(latest_avg, 2) if latest_avg is not None else 0
            overall_delta = round(latest_avg - earliest_avg, 2) if latest_avg is not None and earliest_avg is not None else None

            best_subject = None
            best_subject_score = None
            top_growth_subject = None
            top_growth_delta = None
            top_decline_subject = None
            top_decline_delta = None
            for row in comparison_rows:
                latest_data = next((item for item in row["years"] if item["year"] == latest_year), None)
                if latest_data and latest_data["avg_score"] is not None:
                    if best_subject_score is None or latest_data["avg_score"] > best_subject_score:
                        best_subject_score = latest_data["avg_score"]
                        best_subject = row["subject"]
                if row["trend_delta"] is not None:
                    if top_growth_delta is None or row["trend_delta"] > top_growth_delta:
                        top_growth_delta = row["trend_delta"]
                        top_growth_subject = row["subject"]
                    if top_decline_delta is None or row["trend_delta"] < top_decline_delta:
                        top_decline_delta = row["trend_delta"]
                        top_decline_subject = row["subject"]

            trend_label = "Стабильная динамика"
            if overall_delta is not None:
                if overall_delta > 0.3:
                    trend_label = "Рост результатов"
                elif overall_delta < -0.3:
                    trend_label = "Снижение результатов"

            return {
                "overall_avg": overall_avg,
                "overall_delta": overall_delta,
                "best_subject": best_subject,
                "best_subject_score": best_subject_score,
                "participants_latest_year": year_totals[latest_year]["students"] or 0,
                "top_growth_subject": top_growth_subject,
                "top_growth_delta": top_growth_delta,
                "top_decline_subject": top_decline_subject,
                "top_decline_delta": top_decline_delta,
                "trend_label": trend_label,
            }

        comparison_years_dyn = _derive_comparison_years(selected_exam_type, scope)
        comparison_rows, comparison_chart = _build_year_comparison(
            ExamResult.objects.filter(
                **scope,
                exam__exam_type=selected_exam_type,
                exam__year__in=comparison_years_dyn,
            ),
            years=comparison_years_dyn,
        )
        context["comparison_years"] = list(comparison_years_dyn)
        context["comparison_rows"] = comparison_rows
        context["comparison_chart"] = comparison_chart
        context["comparison_insights"] = _comparison_insights_payload(comparison_rows, comparison_years_dyn)
        if comparison_years_dyn:
            latest_year = comparison_years_dyn[-1]
            context["comparison_insights"]["participants_latest_year"] = (
                ExamResult.objects.filter(**scope, exam__exam_type=selected_exam_type, exam__year=latest_year)
                .values("student_id")
                .distinct()
                .count()
            )
        et_label = context.get("selected_exam_type_label") or ("ОГЭ" if selected_exam_type == "oge" else "ЕГЭ")
        base_note = (
            "Свод по всем районам и школам, отнесённым к вашему министерству в базе данных."
            if getattr(self.request.user, "ministry_id", None)
            else "Свод по всем районам и школам в базе данных (профиль министерства у пользователя не задан — охват не ограничен)."
        )
        context["ministry_dynamics_note"] = f"{base_note} Тип экзамена: {et_label}."
        context["ege_stats"] = _exam_stats_payload("ege")
        context["oge_stats"] = _exam_stats_payload("oge")
        available_years_qs = (
            ExamResult.objects.filter(exam__exam_type=selected_exam_type, **scope)
            .values_list("exam__year", flat=True)
            .distinct()
            .order_by("-exam__year")
        )
        ministry_available_years = list(available_years_qs)
        selected_year = _parse_positive_int(self.request.GET.get("year"))
        if selected_year not in ministry_available_years:
            selected_year = ministry_available_years[0] if ministry_available_years else None
        context["ministry_available_years"] = ministry_available_years
        context["ministry_selected_year"] = selected_year

        ministry_district_results = self._ministry_district_results(selected_exam_type, selected_year)
        context["ministry_district_results"] = ministry_district_results

        selected_district_id = _parse_positive_int(self.request.GET.get("district"))
        selected_district = None
        if selected_district_id:
            selected_district = District.objects.filter(id=selected_district_id).only("id", "name", "code").first()
        context["selected_district_id"] = selected_district.id if selected_district else None
        context["selected_district"] = selected_district

        selected_district_school_results = (
            self._ministry_district_school_results(selected_district.id, selected_exam_type, selected_year)
            if selected_district
            else []
        )
        context["selected_district_school_results"] = selected_district_school_results

        selected_school_id = _parse_positive_int(self.request.GET.get("school"))
        selected_school = None
        if selected_school_id and selected_district:
            selected_school = School.objects.filter(
                id=selected_school_id,
                district_id=selected_district.id,
            ).only("id", "name", "code").first()
        context["selected_school_id"] = selected_school.id if selected_school else None
        context["selected_school"] = selected_school

        selected_school_subject_results = (
            self._ministry_school_subject_results(
                selected_district.id,
                selected_school.id,
                selected_exam_type,
                selected_year,
            )
            if selected_district and selected_school
            else []
        )
        context["selected_school_subject_results"] = selected_school_subject_results

        selected_subject_name = (self.request.GET.get("subject") or "").strip()
        available_subjects = {item["subject"] for item in selected_school_subject_results}
        if selected_subject_name not in available_subjects:
            selected_subject_name = ""
        context["selected_subject_name"] = selected_subject_name
        context["selected_subject_results"] = (
            self._ministry_subject_students(
                selected_district.id,
                selected_school.id,
                selected_exam_type,
                selected_subject_name,
                selected_year,
            )
            if selected_district and selected_school and selected_subject_name
            else []
        )
        context["selected_subject_task_rows"] = (
            self._ministry_subject_task_rows(
                selected_district.id,
                selected_school.id,
                selected_exam_type,
                selected_subject_name,
                selected_year,
            )
            if selected_district and selected_school and selected_subject_name
            else []
        )

        context["cabinet_kind"] = "ministry"
        return context


class DistrictDashboardView(RoleDashboardView):
    required_role = "district"
    role_title = "Кабинет Района"
    template_name = "users/district_dashboard.html"

    def _district_school_results(self, exam_type: str, year: int | None = None):
        if not self.request.user.district_id:
            return []
        district_id = int(self.request.user.district_id)
        cache_key = f"cabinet:district:school_results:v2:{district_id}:{exam_type}:{year or 'all'}"

        def _build():
            qs = ExamResult.objects.filter(
                student__school__district_id=district_id,
                exam__exam_type=exam_type,
            )
            if year:
                qs = qs.filter(exam__year=year)
            rows = (
                qs.values("student__school_id", "student__school__code", "student__school__name")
                .annotate(
                    students=Count("student_id", distinct=True),
                    results=Count("id"),
                    exams=Count("exam_id", distinct=True),
                    avg_score=Avg("score"),
                )
                .order_by("student__school__name")
            )
            pass_stats = _pass_stats_by_school(qs, exam_type)
            out = []
            for row in rows:
                students = int(row["students"] or 0)
                results = int(row["results"] or 0) or students
                school_id = int(row["student__school_id"])
                total_results, passed_count = pass_stats.get(school_id, (results, 0))
                denom = total_results or results
                pass_rate = round((passed_count / denom) * 100, 1) if denom else 0.0
                out.append(
                    {
                        "school_id": row["student__school_id"],
                        "school_code": row["student__school__code"] or "-",
                        "school_name": row["student__school__name"] or "Школа без названия",
                        "students": students,
                        "results": results,
                        "exams": int(row["exams"] or 0),
                        "avg_score": round(float(row["avg_score"] or 0), 2),
                        "pass_rate": pass_rate,
                    }
                )
            return out

        return _cache_get_or_set(cache_key, 900, _build)

    def _district_school_subject_results(self, school_id: int, exam_type: str, year: int | None = None):
        if not self.request.user.district_id:
            return []
        district_id = int(self.request.user.district_id)
        cache_key = f"cabinet:district:school_subject_results:{district_id}:{school_id}:{exam_type}:{year or 'all'}"

        def _build():
            qs = ExamResult.objects.filter(
                student__school__district_id=district_id,
                student__school_id=school_id,
                exam__exam_type=exam_type,
            )
            if year:
                qs = qs.filter(exam__year=year)
            rows = list(
                qs.values("exam__subject")
                .annotate(
                    students=Count("student_id", distinct=True),
                    results=Count("id"),
                    exams=Count("exam_id", distinct=True),
                    avg_score=Avg("score"),
                )
                .order_by("exam__subject")
            )

            passed_by_subject = _passed_count_by_subject(qs, exam_type)

            out = []
            for row in rows:
                students = int(row["students"] or 0)
                results = int(row["results"] or 0) or students
                subject_name = row["exam__subject"] or "Предмет не указан"
                passed_count = int(passed_by_subject.get(subject_name, 0))
                pass_rate = round((passed_count / results) * 100, 1) if results else 0.0
                out.append(
                    {
                        "subject": subject_name,
                        "students": students,
                        "exams": int(row["exams"] or 0),
                        "avg_score": round(float(row["avg_score"] or 0), 2),
                        "pass_rate": pass_rate,
                    }
                )
            return out

        return _cache_get_or_set(cache_key, 900, _build)

    def _district_school_subject_students(
        self,
        school_id: int,
        exam_type: str,
        subject_name: str,
        year: int | None = None,
    ):
        if not self.request.user.district_id:
            return []
        qs = (
            ExamResult.objects.filter(
                student__school__district_id=self.request.user.district_id,
                student__school_id=school_id,
                exam__exam_type=exam_type,
                exam__subject=subject_name,
            )
            .select_related("exam", "student")
            .order_by("exam__exam_date", "student_name", "student__full_name")
        )
        if year:
            qs = qs.filter(exam__year=year)

        threshold_cache: dict = {}
        out = []
        for result in qs:
            below_minimum = _exam_result_below_minimum(result, exam_type, threshold_cache)
            out.append(
                {
                    "result_id": result.id,
                    "student_id": result.student_id,
                    "student_name": result.student_name or result.student.full_name,
                    "short_answer_tasks": result.short_answer_tasks,
                    "long_answer_tasks": result.long_answer_tasks,
                    "primary_score": result.primary_score,
                    "score": result.score,
                    "exam_date": result.exam.exam_date,
                    "exam_code": result.exam.code,
                    "below_minimum": below_minimum,
                }
            )
        return out

    def _district_school_subject_task_rows(
        self,
        school_id: int,
        exam_type: str,
        subject_name: str,
        year: int | None = None,
    ):
        if not self.request.user.district_id:
            return []
        qs = TaskResult.objects.filter(
            student__school__district_id=self.request.user.district_id,
            student__school_id=school_id,
            exam__exam_type=exam_type,
            exam__subject=subject_name,
        )
        if year:
            qs = qs.filter(exam__year=year)

        raw_task_values = list(qs.values("task_number", "value").order_by("task_number"))
        task_agg = {}
        for row in raw_task_values:
            task_num = row["task_number"]
            bucket = task_agg.setdefault(task_num, {"total": 0, "plus": 0, "minus": 0})
            bucket["total"] += 1
            if _is_success_token(row["value"]):
                bucket["plus"] += 1
            else:
                bucket["minus"] += 1

        task_rows = []
        for task_num in sorted(task_agg):
            row = task_agg[task_num]
            total = row["total"]
            plus = row["plus"]
            minus = row["minus"]
            success_rate = round((plus / total) * 100, 1) if total else 0
            task_rows.append(
                {
                    "task_number": task_num,
                    "success_rate": success_rate,
                    "plus": plus,
                    "minus": minus,
                    "total": total,
                }
            )
        return task_rows

    def _district_years_context(self, exam_type: str) -> tuple[list[int], int | None]:
        years_qs = (
            ExamResult.objects.filter(
                student__school__district_id=self.request.user.district_id,
                exam__exam_type=exam_type,
            )
            .values_list("exam__year", flat=True)
            .distinct()
            .order_by("-exam__year")
        )
        district_available_years = list(years_qs)
        selected_year = _parse_positive_int(self.request.GET.get("year"))
        if selected_year not in district_available_years:
            selected_year = district_available_years[0] if district_available_years else None
        return district_available_years, selected_year

    def _district_school_detail_context(
        self,
        *,
        school_id: int,
        exam_type: str,
        selected_year: int | None,
    ) -> dict:
        selected_school = School.objects.filter(
            id=school_id,
            district_id=self.request.user.district_id,
        ).only("id", "name", "code").first()
        if not selected_school:
            return {}

        selected_school_subject_results = self._district_school_subject_results(
            selected_school.id, exam_type, selected_year
        )
        selected_subject_name = (self.request.GET.get("subject") or "").strip()
        available_subjects = {item["subject"] for item in selected_school_subject_results}
        if selected_subject_name not in available_subjects:
            selected_subject_name = ""

        selected_school_subject_students = []
        selected_school_subject_task_rows = []
        if selected_subject_name:
            selected_school_subject_students = self._district_school_subject_students(
                school_id=selected_school.id,
                exam_type=exam_type,
                subject_name=selected_subject_name,
                year=selected_year,
            )
            selected_school_subject_task_rows = self._district_school_subject_task_rows(
                school_id=selected_school.id,
                exam_type=exam_type,
                subject_name=selected_subject_name,
                year=selected_year,
            )

        return {
            "selected_school_id": selected_school.id,
            "selected_school": selected_school,
            "selected_school_subject_results": selected_school_subject_results,
            "selected_subject_name": selected_subject_name,
            "selected_school_subject_students": selected_school_subject_students,
            "selected_school_subject_task_rows": selected_school_subject_task_rows,
        }

    def get(self, request, *args, **kwargs):
        school_id = _parse_positive_int(request.GET.get("school"))
        if school_id and request.user.district_id:
            if School.objects.filter(id=school_id, district_id=request.user.district_id).exists():
                exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
                if exam_type not in {"ege", "oge", "vpr"}:
                    exam_type = "ege"
                params = [f"exam_type={exam_type}"]
                year = (request.GET.get("year") or "").strip()
                if year.isdigit():
                    params.append(f"year={year}")
                subject = (request.GET.get("subject") or "").strip()
                if subject:
                    from urllib.parse import quote

                    params.append(f"subject={quote(subject)}")
                from django.urls import reverse

                query = "?" + "&".join(params)
                return redirect(reverse("cabinet-district-school", kwargs={"school_id": school_id}) + query)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cabinet_kind"] = "district"
        district = getattr(self.request.user, "district", None)
        if district:
            context["role_title"] = district.name
        exam_type = context.get("selected_exam_type", "ege")

        # ВПР: автономный модуль (VprProtocol), не ExamResult.
        if exam_type == "vpr":
            return self._vpr_district_dashboard_context(context, district)

        district_available_years, selected_year = self._district_years_context(exam_type)
        context["district_available_years"] = district_available_years
        context["district_selected_year"] = selected_year
        district_school_results = self._district_school_results(exam_type, selected_year)
        context["district_school_results"] = district_school_results
        context["district_export_year"] = selected_year or ""
        context["district_schools_count"] = len(district_school_results)

        if self.request.user.district_id:
            scope = {"student__school__district_id": self.request.user.district_id}
            hub_helper = ExamTypeChoiceView()
            hub_helper.request = self.request
            hub_available = hub_helper._available_years(scope)
            stats_year = selected_year or (hub_available[0] if hub_available else COMPARISON_YEARS[-1])
            context.update(hub_helper.build_hub_context(scope, exam_type, stats_year, hub_available))
            context["hub_selected_year"] = stats_year

        schools_with_data = [row for row in district_school_results if int(row.get("students") or 0) > 0]
        context["district_top_schools"] = sorted(
            schools_with_data,
            key=lambda row: (float(row.get("avg_score") or 0), float(row.get("pass_rate") or 0)),
            reverse=True,
        )[:5]
        context["district_risk_schools"] = sorted(
            schools_with_data,
            key=lambda row: (float(row.get("pass_rate") or 0), float(row.get("avg_score") or 0)),
        )[:5]
        context["district_risk_school_count"] = sum(
            1 for row in schools_with_data if float(row.get("pass_rate") or 0) < 50
        )
        if exam_type == "ege":
            active_risks = context.get("ege_risks")
        elif exam_type == "oge":
            active_risks = context.get("oge_risks")
        else:
            active_risks = context.get("vpr_risks")
        signals = []
        for risk in (active_risks or [])[:4]:
            subject = risk.get("subject") or "Предмет"
            task_number = risk.get("task_number")
            signals.append(
                {
                    "subject": subject,
                    "title": f"{subject}: задание №{task_number}" if task_number else subject,
                    "issue": f"Успешность {risk.get('success_rate', 0)}%",
                    "reason": "Требуется предметный разбор тем и ошибок по протоколам.",
                    "recommendation": "Назначить диагностику, методическую консультацию и контрольную точку через 4-6 недель.",
                }
            )
        if not signals and context.get("district_risk_schools"):
            for school in context["district_risk_schools"][:3]:
                signals.append(
                    {
                        "subject": school.get("school_name"),
                        "title": school.get("school_name"),
                        "issue": f"Сдаваемость {school.get('pass_rate')}%",
                        "reason": "Школа находится в нижней части муниципального рейтинга.",
                        "recommendation": "Разобрать предметы риска и закрепить план сопровождения администрации школы.",
                    }
                )
        context["district_management_signals"] = signals
        return context

    def _vpr_district_dashboard_context(self, context, district):
        """Районная Аналитика ВПР в BI-оболочке (как ЕГЭ/ОГЭ у ОО)."""
        from apps.vpr.access import scoped_protocols_qs
        from users.report_ui.district_vpr_dashboard import build_district_vpr_dashboard_ui

        protocols_qs = scoped_protocols_qs(self.request.user).select_related("school", "upload")
        available_years = list(
            protocols_qs.values_list("academic_year", flat=True).distinct().order_by("-academic_year")
        )
        selected_year = _parse_positive_int(self.request.GET.get("year"))
        if selected_year not in available_years:
            selected_year = available_years[0] if available_years else None

        year_protocols = protocols_qs
        if selected_year:
            year_protocols = protocols_qs.filter(academic_year=selected_year)

        context["district_available_years"] = available_years
        context["district_selected_year"] = selected_year
        context["available_years"] = available_years
        context["selected_year"] = selected_year
        context["selected_exam_type"] = "vpr"
        context["selected_exam_type_label"] = "ВПР"
        context["district_vpr_ui"] = build_district_vpr_dashboard_ui(
            protocols=list(year_protocols.order_by("school__name", "subject", "parallel")),
            selected_year=selected_year,
            district=district,
        )
        return context


class DistrictSchoolDashboardView(DistrictDashboardView):
    """Отдельная страница: результаты выбранной школы по предметам."""

    template_name = "users/district_school_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        school_id = kwargs.get("school_id")
        if request.user.role == "district" and request.user.district_id and school_id:
            if not School.objects.filter(id=school_id, district_id=request.user.district_id).exists():
                return redirect("cabinet-district")
        return super(DistrictDashboardView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = RoleDashboardView.get_context_data(self, **kwargs)
        context["cabinet_kind"] = "district"
        district = getattr(self.request.user, "district", None)
        if district:
            context["role_title"] = district.name

        school_id = int(self.kwargs["school_id"])
        exam_type = context.get("selected_exam_type", "ege")
        district_available_years, selected_year = self._district_years_context(exam_type)
        context["district_available_years"] = district_available_years
        context["district_selected_year"] = selected_year
        context.update(
            self._district_school_detail_context(
                school_id=school_id,
                exam_type=exam_type,
                selected_year=selected_year,
            )
        )
        if not context.get("selected_school"):
            context["school_not_found"] = True
        else:
            scope = {"student__school_id": school_id}
            hub_helper = ExamTypeChoiceView()
            hub_helper.request = self.request
            hub_available = hub_helper._available_years(scope)
            stats_year = selected_year or (hub_available[0] if hub_available else COMPARISON_YEARS[-1])
            context.update(hub_helper.build_hub_context(scope, exam_type, stats_year, hub_available))
            context["hub_selected_year"] = stats_year
        return context


class DistrictStudentWorkView(LoginRequiredMixin, TemplateView):
    """Отдельная страница: анализ работы конкретного ученика по выбранному экзамену."""

    template_name = "users/district_student_work.html"
    required_role = "district"

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != self.required_role:
            return redirect("cabinet-exam-choice")
        if self.required_role == "district" and not request.user.district_id:
            return redirect("cabinet-exam-choice")
        if self.required_role == "school" and not _resolve_school_id_for_user(request.user):
            return redirect("cabinet-exam-choice")
        return super().dispatch(request, *args, **kwargs)

    def _load_result(self, result_id: int):
        qs = ExamResult.objects.filter(id=result_id).select_related(
            "exam", "student", "student__school"
        )
        if self.required_role == "district":
            qs = qs.filter(student__school__district_id=self.request.user.district_id)
        else:
            school_id = _resolve_school_id_for_user(self.request.user)
            qs = qs.filter(student__school_id=school_id)
        return qs.first()

    def _task_rows_for_result(self, result: ExamResult) -> list[dict]:
        exam_type = (result.exam.exam_type or "ege").lower()
        subject_name = result.exam.subject or ""
        raw = list(
            TaskResult.objects.filter(student_id=result.student_id, exam_id=result.exam_id)
            .values("task_number", "value")
            .order_by("task_number")
        )
        if not raw:
            # Fallback: parse masks from ExamResult if TaskResult rows are missing.
            from users.task_topics import parse_long_answer_mask

            raw = []
            short_mask = (result.short_answer_tasks or "").strip()
            for idx, token in enumerate(short_mask, start=1):
                raw.append({"task_number": idx, "value": token})
            long_mask = (result.long_answer_tasks or "").strip()
            if long_mask:
                part2_start = len(short_mask) + 1 if short_mask else 1
                for task_number, token in parse_long_answer_mask(long_mask, part2_start):
                    raw.append({"task_number": task_number, "value": token})

        rows = []
        for item in raw:
            task_num = int(item["task_number"])
            value = str(item.get("value") or "").strip()
            success = _is_success_token(value)
            blank = value in {"", "-"}
            rows.append(
                {
                    "task_number": task_num,
                    "value": value or "—",
                    "success": success,
                    "blank": blank,
                    "status": "Верно" if success else ("Не выполнено" if blank else "Ошибка"),
                    "topic": _topic_for_task(subject_name, task_num, exam_type) or "Тема не указана",
                    "grades": _grades_for_task(subject_name, task_num, exam_type) or [],
                }
            )
        return rows

    def _build_analysis(self, result: ExamResult, task_rows: list[dict], below_minimum: bool) -> dict:
        total = len(task_rows)
        correct = sum(1 for row in task_rows if row["success"])
        wrong = sum(1 for row in task_rows if not row["success"] and not row["blank"])
        blank = sum(1 for row in task_rows if row["blank"])
        success_rate = round((correct / total) * 100, 1) if total else 0.0
        weak_tasks = [row for row in task_rows if not row["success"]]
        strong_tasks = [row for row in task_rows if row["success"]]

        insights = []
        subject = gve_subject_label(result.exam.subject, result.exam.code)
        insights.append(
            f"Результат по предмету «{subject}»: {result.score} балла "
            f"({'ниже минимума' if below_minimum else 'порог пройден'})."
        )
        if total:
            insights.append(
                f"По протоколу заданий: верно {correct} из {total} ({success_rate}%), "
                f"ошибок {wrong}, не выполнено {blank}."
            )
        if weak_tasks:
            sample = ", ".join(
                f"№{row['task_number']} ({row['topic']})" for row in weak_tasks[:5]
            )
            insights.append(f"Проблемные задания: {sample}.")
        if strong_tasks:
            sample = ", ".join(f"№{row['task_number']}" for row in strong_tasks[:5])
            insights.append(f"Устойчиво выполненные задания: {sample}.")

        recommendations = []
        if below_minimum:
            recommendations.append(
                "Назначить индивидуальную диагностику и план ликвидации пробелов по заданиям ниже порога."
            )
        if weak_tasks:
            topics = []
            for row in weak_tasks[:6]:
                topic = row.get("topic") or ""
                if topic and topic not in topics and topic != "Тема не указана":
                    topics.append(topic)
            if topics:
                recommendations.append(
                    "Сфокусировать подготовку на темах: " + "; ".join(topics[:4]) + "."
                )
            recommendations.append(
                "Провести повторную тренировку по ошибочным заданиям с разбором типичных ошибок."
            )
        else:
            recommendations.append(
                "Результат стабильный: закрепить сильные задания и расширить практику повышенного уровня."
            )
        recommendations.append(
            "Зафиксировать контрольную точку через 2–3 недели и сравнить выполнение тех же типов заданий."
        )

        return {
            "total": total,
            "correct": correct,
            "wrong": wrong,
            "blank": blank,
            "success_rate": success_rate,
            "weak_tasks": weak_tasks,
            "strong_tasks": strong_tasks[:8],
            "insights": insights,
            "recommendations": recommendations,
        }

    def _back_url(self, result: ExamResult, exam_type: str) -> str:
        from urllib.parse import quote

        if self.required_role == "school":
            return (
                f"/cabinet/school/?exam_type={exam_type}"
                f"&year={result.exam.year}&exam={result.exam_id}"
            )
        return (
            f"/cabinet/district/school/{result.student.school_id}/"
            f"?exam_type={exam_type}&year={result.exam.year}"
            f"&subject={quote(result.exam.subject or '')}"
        )

    def _page_meta(self, result: ExamResult | None) -> dict:
        if self.required_role == "school":
            school_id = _resolve_school_id_for_user(self.request.user)
            school = School.objects.filter(id=school_id).only("name").first() if school_id else None
            return {
                "role_title": school.name if school else "Школа",
                "cabinet_kind": "school",
                "page_eyebrow": "Анализ работы ученика · кабинет школы",
                "back_label": "← К предмету",
                "not_found_hint": "Работа ученика недоступна или не относится к вашей школе.",
            }
        district = getattr(self.request.user, "district", None)
        return {
            "role_title": district.name if district else "Район",
            "cabinet_kind": "district",
            "page_eyebrow": "Анализ работы ученика · районный кабинет",
            "back_label": "← К предмету школы",
            "not_found_hint": "Работа ученика недоступна или не относится к вашему району.",
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result_id = int(self.kwargs["result_id"])
        result = self._load_result(result_id)
        context.update(self._page_meta(result))
        context["result_not_found"] = result is None
        if not result:
            return context

        exam_type = (result.exam.exam_type or "ege").lower()
        below_minimum = _exam_result_below_minimum(result, exam_type)
        task_rows = self._task_rows_for_result(result)
        analysis = self._build_analysis(result, task_rows, below_minimum)
        subject_label = gve_subject_label(result.exam.subject, result.exam.code)

        context.update(
            {
                "exam_result": result,
                "exam_type": exam_type,
                "exam_type_label": result.exam.get_exam_type_display(),
                "subject_name": result.exam.subject,
                "subject_label": subject_label,
                "school": result.student.school,
                "student_name": result.student_name or result.student.full_name,
                "student_grade": result.student.grade or "",
                "below_minimum": below_minimum,
                "task_rows": task_rows,
                "analysis": analysis,
                "back_url": self._back_url(result, exam_type),
                "chart_data": {
                    "labels": [f"№{row['task_number']}" for row in task_rows],
                    "values": [1 if row["success"] else 0 for row in task_rows],
                },
            }
        )
        return context


class SchoolStudentWorkView(DistrictStudentWorkView):
    """Анализ работы ученика в кабинете школы."""

    required_role = "school"


class SchoolDashboardView(RoleDashboardView):
    required_role = "school"
    role_title = "Кабинет Школы"
    include_default_metrics = False
    template_name = "users/school_dashboard.html"

    def _build_selected_subject_comparison(self, school_id, subject_name):
        if not school_id:
            return None
        if not subject_name:
            return None
        selected_subject_key = _subject_group_key(subject_name)
        all_rows, _ = _build_year_comparison(
            ExamResult.objects.filter(student__school_id=school_id, exam__year__in=COMPARISON_YEARS),
            years=COMPARISON_YEARS,
            max_chart_subjects=1,
        )
        for row in all_rows:
            if _subject_group_key(row["subject"]) == selected_subject_key:
                return row
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exam_type = context.get("selected_exam_type", "ege")
        school_id = _resolve_school_id_for_user(self.request.user)
        context["selected_subject_comparison"] = None
        context["comparison_years"] = list(COMPARISON_YEARS)
        context["vpr_mode"] = False

        # Автономный модуль ВПР: протоколы живут в apps.vpr, не в Exam/ExamResult.
        if exam_type == "vpr":
            return self._vpr_school_dashboard_context(context, school_id)

        base_school_results = (
            ExamResult.objects.filter(student__school_id=school_id, exam__exam_type=exam_type)
            .select_related("exam", "student")
            .order_by("exam__subject", "student_name", "student__full_name")
        )
        available_years = list(
            base_school_results.values_list("exam__year", flat=True).distinct().order_by("-exam__year")
        )
        selected_year = _parse_positive_int(self.request.GET.get("year"))
        if selected_year not in available_years:
            selected_year = available_years[0] if available_years else None

        school_results = base_school_results
        if selected_year:
            school_results = school_results.filter(exam__year=selected_year)

        subject_exam_rows = list(
            school_results.values("exam_id", "exam__subject", "exam__exam_date", "exam__code")
            .annotate(students_count=Count("student_id", distinct=True))
            .order_by("exam__subject", "-exam__exam_date")
        )
        for row in subject_exam_rows:
            row["is_gve"] = is_gve_exam(exam_code=row.get("exam__code"), subject_name=row.get("exam__subject"))
            row["subject_label"] = gve_subject_label(row.get("exam__subject"), row.get("exam__code"))
        context["school_subjects"] = subject_exam_rows
        context["available_years"] = available_years
        context["selected_year"] = selected_year

        selected_exam_id = self.request.GET.get("exam")
        if not selected_exam_id and subject_exam_rows:
            selected_exam_id = str(subject_exam_rows[0]["exam_id"])
        metrics_scope = {"student__school_id": school_id, "exam__exam_type": exam_type}
        if selected_exam_id and selected_exam_id.isdigit():
            metrics_scope["exam_id"] = int(selected_exam_id)
        context["metrics"] = exam_overview(metrics_scope, year=selected_year)
        context["selected_exam_id"] = selected_exam_id
        context["selected_exam_results"] = []
        context["selected_exam_title"] = ""
        context["selected_exam_analysis"] = None
        context["selected_exam_threshold"] = None
        if selected_exam_id and selected_exam_id.isdigit():
            selected_results = school_results.filter(exam_id=int(selected_exam_id))
            if selected_results.exists():
                first_result = selected_results.first()
                threshold = None
                if exam_type == "ege":
                    if is_gve_exam(
                        exam_code=first_result.exam.code,
                        subject_name=first_result.exam.subject,
                    ):
                        threshold = GVE_GRADE_THRESHOLD
                    else:
                        subject_key = _threshold_subject_key(first_result.exam.subject)
                        threshold_year = selected_year or first_result.exam.year
                        threshold = resolve_ege_passing_threshold(threshold_year, subject_key)
                elif exam_type == "oge":
                    threshold = GVE_GRADE_THRESHOLD
                context["selected_exam_threshold"] = threshold
                context["selected_subject_comparison"] = self._build_selected_subject_comparison(
                    school_id,
                    first_result.exam.subject,
                )
                subject_title = gve_subject_label(first_result.exam.subject, first_result.exam.code)
                context["selected_exam_title"] = (
                    f"{subject_title} ({first_result.exam.code}) {first_result.exam.exam_date:%d.%m.%Y}"
                )
                selected_exam_results = []
                passed_count = 0
                threshold_cache: dict = {}
                for result in selected_results:
                    below_minimum = _exam_result_below_minimum(result, exam_type, threshold_cache)
                    if not below_minimum:
                        passed_count += 1
                    selected_exam_results.append(
                        {
                            "result": result,
                            "below_minimum": below_minimum,
                        }
                    )
                context["selected_exam_results"] = selected_exam_results
                score_stats = selected_results.aggregate(
                    avg_score=Avg("score"),
                    min_score=Min("score"),
                    max_score=Max("score"),
                )
                students_count = selected_results.count()
                # Успеваемость только по порогу (не по флагу passed из импорта).
                pass_rate = round((passed_count / students_count) * 100, 1) if students_count else 0

                from analytics.engine import AnalyticsEngine
                from analytics.engine.adapters import to_dashboard_analysis

                engine_result = AnalyticsEngine().analyze_exam(school_id, int(selected_exam_id))
                dashboard = to_dashboard_analysis(engine_result)
                if dashboard and dashboard.get("valid"):
                    context["selected_exam_analysis"] = {
                        "exam_type": (first_result.exam.exam_type or "ege").lower(),
                        "students_count": dashboard["students_count"],
                        "avg_score": dashboard["avg_score"],
                        "min_score": dashboard["min_score"],
                        "max_score": dashboard["max_score"],
                        "pass_rate": pass_rate,
                        "task_rows": dashboard["task_rows"],
                        "weak_tasks": [
                            row for row in dashboard["task_rows"] if row["classification"] in {"слабое", "критическое"}
                        ][:3],
                        "strong_tasks": [
                            row for row in dashboard["task_rows"] if row["classification"] == "сильное"
                        ][:3],
                        "recommendations": dashboard["recommendations"],
                        "insights": dashboard.get("insights", []),
                        "control_plan": dashboard.get("control_plan", []),
                        "chart": dashboard["chart"],
                        "task_knowledge_cards": dashboard.get("task_knowledge_cards", []),
                        "deficit_paths": dashboard.get("deficit_paths", []),
                        "thematic_blocks": dashboard.get("thematic_blocks", []),
                        "strength_summary": dashboard.get("strength_summary", {}),
                        "part_narrative": dashboard.get("part_narrative", []),
                        "part1_success_rate": dashboard.get("part1_success_rate"),
                        "part2_success_rate": dashboard.get("part2_success_rate"),
                        "part_gap": dashboard.get("part_gap"),
                        "class_analysis": dashboard.get("class_analysis", {}),
                        "risk_clusters": dashboard.get("risk_clusters", []),
                        "unified_recommendations": dashboard.get("unified_recommendations", {}),
                        "teacher_recommendations": dashboard.get("teacher_recommendations", []),
                        "admin_recommendations": dashboard.get("admin_recommendations", []),
                    }
                else:
                    # Базовый срез по протоколу, если движок не построил полный анализ.
                    error_text = (dashboard or {}).get("error") or "Аналитика по заданиям временно недоступна."
                    context["analytics_error"] = error_text
                    context["selected_exam_analysis"] = {
                        "exam_type": (first_result.exam.exam_type or "ege").lower(),
                        "students_count": students_count,
                        "avg_score": round(float(score_stats["avg_score"] or 0), 1),
                        "min_score": round(float(score_stats["min_score"] or 0), 1),
                        "max_score": round(float(score_stats["max_score"] or 0), 1),
                        "pass_rate": pass_rate,
                        "task_rows": [],
                        "weak_tasks": [],
                        "strong_tasks": [],
                        "recommendations": [error_text],
                        "insights": [],
                        "control_plan": [],
                        "chart": {"labels": [], "success_rates": [], "minus_counts": []},
                        "task_knowledge_cards": [],
                        "deficit_paths": [],
                        "teacher_recommendations": [],
                        "admin_recommendations": [],
                    }
        school = None
        if school_id:
            school = (
                School.objects.filter(id=school_id)
                .select_related("district")
                .first()
            )
            if school:
                context["role_title"] = school.name
                context["school_profile"] = {
                    "name": school.name,
                    "code": school.code,
                    "district": school.district.name if school.district_id else "",
                }

        # Presentation shell for EGE / OGE analytics pages (no algorithm changes).
        if exam_type == "ege":
            from users.report_ui.school_ege_dashboard import build_ege_dashboard_ui

            context["ege_ui"] = build_ege_dashboard_ui(
                year_qs=school_results,
                all_years_qs=base_school_results,
                school_subjects=subject_exam_rows,
                selected_year=selected_year,
                analysis=context.get("selected_exam_analysis"),
                comparison=context.get("selected_subject_comparison"),
                selected_results=context.get("selected_exam_results"),
                school=school,
            )
            context["oge_ui"] = None
        elif exam_type == "oge":
            from users.report_ui.school_oge_dashboard import build_oge_dashboard_ui

            context["oge_ui"] = build_oge_dashboard_ui(
                year_qs=school_results,
                all_years_qs=base_school_results,
                school_subjects=subject_exam_rows,
                selected_year=selected_year,
                analysis=context.get("selected_exam_analysis"),
                comparison=context.get("selected_subject_comparison"),
                selected_results=context.get("selected_exam_results"),
                school=school,
            )
            context["ege_ui"] = None
        else:
            context["ege_ui"] = None
            context["oge_ui"] = None
        return context

    def _vpr_school_dashboard_context(self, context, school_id):
        """
        Ветка ВПР для кабинета школы.
        Использует VprProtocol + VprAnalyticsEngine, без Exam/ExamResult и без AnalyticsEngine ЕГЭ/ОГЭ.
        """
        from apps.vpr.access import scoped_protocols_qs
        from apps.vpr.analytics import VprAnalyticsEngine
        from users.report_ui.school_vpr_dashboard import build_vpr_dashboard_ui

        context["vpr_mode"] = True
        context["selected_exam_results"] = []
        context["selected_exam_analysis"] = None
        context["selected_exam_threshold"] = None
        context["selected_exam_title"] = ""
        context["metrics"] = {}
        context["vpr_selected_protocol"] = None
        context["vpr_selected_summary"] = None
        context["ege_ui"] = None
        context["oge_ui"] = None

        protocols_qs = scoped_protocols_qs(self.request.user).order_by(
            "-academic_year", "subject", "parallel", "-exam_date", "-id"
        )
        available_years = list(
            protocols_qs.values_list("academic_year", flat=True).distinct().order_by("-academic_year")
        )
        selected_year = _parse_positive_int(self.request.GET.get("year"))
        if selected_year not in available_years:
            selected_year = available_years[0] if available_years else None

        if selected_year:
            protocols_qs = protocols_qs.filter(academic_year=selected_year)

        protocol_list = list(protocols_qs)
        subject_rows = []
        for protocol in protocol_list:
            subject_rows.append(
                {
                    "exam_id": protocol.id,
                    "exam__subject": protocol.subject,
                    "subject_label": f"{protocol.subject} · {protocol.parallel} кл.",
                    "exam__code": f"{protocol.parallel} кл.",
                    "exam__exam_date": protocol.exam_date,
                    "students_count": protocol.participants_count,
                    "is_gve": False,
                    "is_vpr": True,
                    "parallel": protocol.parallel,
                    "max_primary_score": protocol.max_primary_score,
                }
            )
        context["school_subjects"] = subject_rows
        context["available_years"] = available_years
        context["selected_year"] = selected_year

        selected_exam_id = self.request.GET.get("exam")
        if not selected_exam_id and subject_rows:
            selected_exam_id = str(subject_rows[0]["exam_id"])
        context["selected_exam_id"] = selected_exam_id

        selected_analytics = None
        summary = None
        if selected_exam_id and str(selected_exam_id).isdigit():
            protocol = next((p for p in protocol_list if int(p.id) == int(selected_exam_id)), None)
            if protocol is None:
                protocol = scoped_protocols_qs(self.request.user).filter(pk=int(selected_exam_id)).first()
            if protocol is not None:
                context["vpr_selected_protocol"] = protocol
                context["selected_exam_title"] = (
                    f"{protocol.subject} · {protocol.parallel} класс · {protocol.academic_year}"
                    + (
                        f" · {protocol.exam_date:%d.%m.%Y}"
                        if protocol.exam_date
                        else ""
                    )
                )
                selected_analytics = VprAnalyticsEngine().analyze(protocol)
                summary = selected_analytics.summary
                context["vpr_selected_summary"] = summary
                context["selected_exam_analysis"] = {
                    "exam_type": "vpr",
                    "students_count": summary.participants_count,
                    "avg_score": summary.avg_primary_score,
                    "min_score": summary.min_primary_score,
                    "max_score": summary.max_primary_result,
                    "pass_rate": summary.absolute_achievement_percent,
                    "knowledge_quality_percent": summary.knowledge_quality_percent,
                    "avg_mark_vpr": summary.avg_mark_vpr,
                    "task_rows": [
                        {
                            "task_number": t.task_number or t.task_code,
                            "topic": t.topic or "—",
                            "skill_name": t.checked_skill or "",
                            "section": t.program_section or "",
                            "success_rate": (
                                round(
                                    100.0
                                    * int(getattr(t, "correct_count", None) or t.full_count or 0)
                                    / int(t.answers_count or 1),
                                    1,
                                )
                                if t.answers_count
                                else (
                                    round(float(t.completion_percent), 1)
                                    if t.completion_percent is not None
                                    else None
                                )
                            ),
                            "plus": int(getattr(t, "correct_count", None) or t.full_count or 0),
                            "minus": max(
                                0,
                                int(t.answers_count or 0)
                                - int(getattr(t, "correct_count", None) or t.full_count or 0),
                            ),
                            "partial": int(t.partial_count or 0),
                            "total": int(t.answers_count or 0),
                        }
                        for t in sorted(
                            selected_analytics.tasks or [],
                            key=lambda item: (int(item.position or 0), str(item.task_code or "")),
                        )
                    ],
                    "weak_tasks": [],
                    "strong_tasks": [],
                    "recommendations": [],
                    "insights": [],
                    "control_plan": [],
                    "chart": {"labels": [], "success_rates": [], "minus_counts": []},
                }
                context["selected_exam_results"] = [{"vpr": True}]

        school = None
        if school_id:
            school = (
                School.objects.filter(id=school_id)
                .select_related("district")
                .first()
            )
            if school:
                context["role_title"] = school.name
                context["school_profile"] = {
                    "name": school.name,
                    "code": school.code,
                    "district": school.district.name if school.district_id else "",
                }

        context["vpr_ui"] = build_vpr_dashboard_ui(
            protocols=protocol_list,
            school_subjects=subject_rows,
            selected_year=selected_year,
            selected_summary=summary,
            selected_analytics=selected_analytics,
            school=school,
        )
        return context


class NoRoleView(LoginRequiredMixin, TemplateView):
    template_name = "users/no_role.html"


class DownloadSchoolExamWordView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        exam_id = request.GET.get("exam")
        if not school_id or not exam_id or not exam_id.isdigit():
            return redirect("cabinet-school")
        exam_data = collect_exam_data_for_export(school_id=school_id, exam_id=int(exam_id))
        if not exam_data:
            return redirect("cabinet-school")
        payload = generate_word_doc(exam_data)
        filename = f"analysis_{exam_data.subject}_{exam_data.date}.docx".replace(" ", "_")
        return attachment_response(
            payload.getvalue(),
            filename,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class DownloadSchoolExamPptxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        exam_id = request.GET.get("exam")
        if not school_id or not exam_id or not exam_id.isdigit():
            return redirect("cabinet-school")
        exam_data = collect_exam_data_for_export(school_id=school_id, exam_id=int(exam_id))
        if not exam_data:
            return redirect("cabinet-school")
        payload = generate_presentation(exam_data)
        filename = f"analysis_{exam_data.subject}_{exam_data.date}.pptx".replace(" ", "_")
        return attachment_response(
            payload.getvalue(),
            filename,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )


class DownloadSchoolExamPdfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        exam_id = request.GET.get("exam")
        if not school_id or not exam_id or not exam_id.isdigit():
            return redirect("cabinet-school")
        exam_data = collect_exam_data_for_export(school_id=school_id, exam_id=int(exam_id))
        if not exam_data:
            return redirect("cabinet-school")
        payload = generate_pdf_report(exam_data)
        filename = f"analysis_{exam_data.subject}_{exam_data.date}.pdf".replace(" ", "_")
        return attachment_response(payload.getvalue(), filename, "application/pdf")


class DownloadSchoolExamXlsxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        exam_id = request.GET.get("exam")
        if not school_id or not exam_id or not exam_id.isdigit():
            return redirect("cabinet-school")
        exam_data = collect_exam_data_for_export(school_id=school_id, exam_id=int(exam_id))
        if not exam_data:
            return redirect("cabinet-school")
        payload = generate_xlsx_report(exam_data)
        filename = f"analysis_{exam_data.subject}_{exam_data.date}.xlsx".replace(" ", "_")
        return attachment_response(
            payload.getvalue(),
            filename,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class DownloadSchoolGiaSummaryView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "").strip().lower()
        if exam_type not in {"ege", "oge"}:
            exam_type = "ege"
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_gia_summary_docx(school_id=school_id, exam_type=exam_type, year=year)
        label = "ege" if exam_type == "ege" else "oge"
        year_label = f"_{year}" if year else ""
        response = HttpResponse(
            payload.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="gia_summary_school_{label}{year_label}.docx"'
        return response


class DownloadSchoolInfoStatDocxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_info_stat_docx(school_id=school_id, exam_type=exam_type, year=year)
        response = HttpResponse(
            payload.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        suffix = f"_{year}" if year else ""
        response["Content-Disposition"] = f'attachment; filename="info_stat_{exam_type}{suffix}.docx"'
        return response


class DownloadSchoolInfoStatPdfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_info_stat_pdf(school_id=school_id, exam_type=exam_type, year=year)
        response = HttpResponse(payload.getvalue(), content_type="application/pdf")
        suffix = f"_{year}" if year else ""
        response["Content-Disposition"] = f'attachment; filename="info_stat_{exam_type}{suffix}.pdf"'
        return response


class DownloadSchoolInfoStatXlsxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_info_stat_xlsx(school_id=school_id, exam_type=exam_type, year=year)
        response = HttpResponse(
            payload.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        suffix = f"_{year}" if year else ""
        response["Content-Disposition"] = f'attachment; filename="info_stat_{exam_type}{suffix}.xlsx"'
        return response


class DownloadSchoolAnalyticNoteDocxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_analytic_note_docx(school_id=school_id, exam_type=exam_type, year=year)
        response = HttpResponse(
            payload.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        suffix = f"_{year}" if year else ""
        response["Content-Disposition"] = f'attachment; filename="analytic_note_{exam_type}{suffix}.docx"'
        return response


class DownloadSchoolAnalyticNotePdfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_analytic_note_pdf(school_id=school_id, exam_type=exam_type, year=year)
        response = HttpResponse(payload.getvalue(), content_type="application/pdf")
        suffix = f"_{year}" if year else ""
        response["Content-Disposition"] = f'attachment; filename="analytic_note_{exam_type}{suffix}.pdf"'
        return response


class DownloadSchoolSubjectNoteDocxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        subject = (request.GET.get("subject") or "").strip()
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_subject_note_docx(
            school_id=school_id,
            exam_type=exam_type,
            subject=subject,
            year=year,
        )
        response = HttpResponse(
            payload.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        safe_subject = (subject or "subject").replace(" ", "_")
        suffix = f"_{year}" if year else ""
        response["Content-Disposition"] = (
            f'attachment; filename="analysis_{safe_subject}{suffix}.docx"'
        )
        return response


class DownloadSchoolSubjectNotePdfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        subject = (request.GET.get("subject") or "").strip()
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_subject_note_pdf(
            school_id=school_id,
            exam_type=exam_type,
            subject=subject,
            year=year,
        )
        response = HttpResponse(payload.getvalue(), content_type="application/pdf")
        safe_subject = (subject or "subject").replace(" ", "_")
        suffix = f"_{year}" if year else ""
        response["Content-Disposition"] = f'attachment; filename="subject_note_{safe_subject}_{exam_type}{suffix}.pdf"'
        return response


class DownloadSchoolMoReportDocxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        mo_key = (request.GET.get("mo") or "math-mo").strip().lower()
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_mo_report_docx(
            school_id=school_id,
            exam_type=exam_type,
            mo_key=mo_key,
            year=year,
        )
        response = HttpResponse(
            payload.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        suffix = f"_{year}" if year else ""
        response["Content-Disposition"] = f'attachment; filename="mo_report_{mo_key}_{exam_type}{suffix}.docx"'
        return response


class DownloadSchoolMoReportPdfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        mo_key = (request.GET.get("mo") or "math-mo").strip().lower()
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_mo_report_pdf(
            school_id=school_id,
            exam_type=exam_type,
            mo_key=mo_key,
            year=year,
        )
        response = HttpResponse(payload.getvalue(), content_type="application/pdf")
        suffix = f"_{year}" if year else ""
        response["Content-Disposition"] = f'attachment; filename="mo_report_{mo_key}_{exam_type}{suffix}.pdf"'
        return response


class DownloadSchoolDeputyReportDocxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        if exam_type not in {"ege", "oge"}:
            exam_type = "ege"
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_deputy_report_docx(school_id=school_id, exam_type=exam_type, year=year)
        response = HttpResponse(
            payload.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        suffix = f"_{year}" if year else ""
        response["Content-Disposition"] = f'attachment; filename="deputy_report_{exam_type}{suffix}.docx"'
        return response


class DownloadSchoolDeputyReportPdfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        if exam_type not in {"ege", "oge"}:
            exam_type = "ege"
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_deputy_report_pdf(school_id=school_id, exam_type=exam_type, year=year)
        response = HttpResponse(payload.getvalue(), content_type="application/pdf")
        suffix = f"_{year}" if year else ""
        response["Content-Disposition"] = f'attachment; filename="deputy_report_{exam_type}{suffix}.pdf"'
        return response


class DownloadSchoolDeputyReportXlsxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "school":
            return redirect("cabinet")
        school_id = _resolve_school_id_for_user(request.user)
        if not school_id:
            return redirect("cabinet-school")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        if exam_type not in {"ege", "oge"}:
            exam_type = "ege"
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_school_deputy_report_xlsx(school_id=school_id, exam_type=exam_type, year=year)
        response = HttpResponse(
            payload.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        suffix = f"_{year}" if year else ""
        response["Content-Disposition"] = f'attachment; filename="deputy_report_{exam_type}{suffix}.xlsx"'
        return response


def _district_export_request(request):
    if request.user.role != "district":
        return None
    district_id = request.user.district_id
    if not district_id:
        return None
    exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
    if exam_type not in {"ege", "oge"}:
        exam_type = "ege"
    year_raw = (request.GET.get("year") or "").strip()
    year = int(year_raw) if year_raw.isdigit() else None
    return district_id, exam_type, year


class DownloadDistrictGiaSummaryDocxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        params = _district_export_request(request)
        if not params:
            return redirect("cabinet-district")
        district_id, exam_type, year = params
        payload = generate_district_gia_summary_docx(district_id=district_id, exam_type=exam_type, year=year)
        suffix = f"_{year}" if year else ""
        return attachment_response(
            payload.getvalue(),
            f"district_gia_summary_{exam_type}{suffix}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class DownloadDistrictInfoStatDocxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        params = _district_export_request(request)
        if not params:
            return redirect("cabinet-district")
        district_id, exam_type, year = params
        payload = generate_district_info_stat_docx(district_id, exam_type, year)
        suffix = f"_{year}" if year else ""
        return attachment_response(
            payload.getvalue(),
            f"district_info_stat_{exam_type}{suffix}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class DownloadDistrictAnalyticNoteDocxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        params = _district_export_request(request)
        if not params:
            return redirect("cabinet-district")
        district_id, exam_type, year = params
        payload = generate_district_analytic_note_docx(district_id, exam_type, year)
        suffix = f"_{year}" if year else ""
        return attachment_response(
            payload.getvalue(),
            f"district_analytic_note_{exam_type}{suffix}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class DownloadDistrictSubjectNoteDocxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        params = _district_export_request(request)
        if not params:
            return redirect("cabinet-district")
        district_id, exam_type, year = params
        subject = (request.GET.get("subject") or "").strip()
        payload = generate_district_subject_note_docx(district_id, exam_type, subject, year)
        suffix = f"_{year}" if year else ""
        safe_subject = (subject or "subject").replace(" ", "_")
        return attachment_response(
            payload.getvalue(),
            f"analysis_{safe_subject}_district{suffix}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class DownloadDistrictSchoolComparisonDocxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        params = _district_export_request(request)
        if not params:
            return redirect("cabinet-district")
        district_id, exam_type, year = params
        payload = generate_district_school_comparison_docx(district_id, exam_type, year)
        suffix = f"_{year}" if year else ""
        return attachment_response(
            payload.getvalue(),
            f"district_school_comparison_{exam_type}{suffix}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class DownloadDistrictMoReportDocxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        params = _district_export_request(request)
        if not params:
            return redirect("cabinet-district")
        district_id, exam_type, year = params
        mo_key = (request.GET.get("mo") or "").strip()
        payload = generate_district_mo_report_docx(district_id, exam_type, mo_key, year)
        suffix = f"_{year}" if year else ""
        return attachment_response(
            payload.getvalue(),
            f"district_mo_report_{exam_type}{suffix}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class DownloadDistrictManagementDocxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        params = _district_export_request(request)
        if not params:
            return redirect("cabinet-district")
        district_id, exam_type, year = params
        payload = generate_district_management_docx(district_id, exam_type, year)
        suffix = f"_{year}" if year else ""
        return attachment_response(
            payload.getvalue(),
            f"district_management_{exam_type}{suffix}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


class DownloadDistrictGiaSummaryPdfView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "district":
            return redirect("cabinet")
        district_id = request.user.district_id
        if not district_id:
            return redirect("cabinet-district")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_district_gia_summary_pdf(district_id=district_id, exam_type=exam_type, year=year)
        suffix = f"_{year}" if year else ""
        return attachment_response(
            payload.getvalue(),
            f"district_gia_summary_{exam_type}{suffix}.pdf",
            "application/pdf",
        )


class DownloadDistrictGiaSummaryXlsxView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if request.user.role != "district":
            return redirect("cabinet")
        district_id = request.user.district_id
        if not district_id:
            return redirect("cabinet-district")
        exam_type = (request.GET.get("exam_type") or "ege").strip().lower()
        year_raw = (request.GET.get("year") or "").strip()
        year = int(year_raw) if year_raw.isdigit() else None
        payload = generate_district_gia_summary_xlsx(district_id=district_id, exam_type=exam_type, year=year)
        suffix = f"_{year}" if year else ""
        return attachment_response(
            payload.getvalue(),
            f"district_gia_summary_{exam_type}{suffix}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


