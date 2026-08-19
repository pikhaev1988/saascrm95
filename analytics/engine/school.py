from __future__ import annotations

from django.db.models import Avg, Count, Q

from analytics.engine.exam import AnalyticsEngine
from analytics.engine.result import ExamAnalysisResult
from exams.models import ExamResult


class SchoolAnalyticsEngine(AnalyticsEngine):
    """Аналитика уровня школы: предметы, динамика, рейтинги."""

    def analyze_school_year(
        self,
        school_id: int,
        exam_type: str,
        year: int,
    ) -> dict:
        base_qs = ExamResult.objects.filter(
            student__school_id=school_id,
            exam__exam_type=exam_type,
            exam__year=year,
        )
        subject_rows = list(
            base_qs.values("exam_id", "exam__subject")
            .annotate(
                students=Count("id"),
                avg_score=Avg("score"),
                passed=Count("id", filter=Q(passed=True)),
            )
            .order_by("-avg_score")
        )
        subjects = []
        for row in subject_rows:
            students = int(row["students"] or 0)
            passed = int(row["passed"] or 0)
            avg = round(float(row["avg_score"] or 0), 2)
            pass_rate = round((passed / students) * 100, 1) if students else 0.0
            subjects.append(
                {
                    "exam_id": row["exam_id"],
                    "subject": row["exam__subject"],
                    "students": students,
                    "avg_score": avg,
                    "pass_rate": pass_rate,
                }
            )

        strong_subjects = subjects[:3]
        weak_subjects = list(reversed(subjects))[:3]

        grade_rows = list(
            base_qs.values("student__grade")
            .annotate(students=Count("id"), avg_score=Avg("score"), passed=Count("id", filter=Q(passed=True)))
            .order_by("-avg_score")
        )
        class_ranking = []
        for row in grade_rows:
            students = int(row["students"] or 0)
            passed = int(row["passed"] or 0)
            class_ranking.append(
                {
                    "grade": row["student__grade"] or "Не указан",
                    "students": students,
                    "avg_score": round(float(row["avg_score"] or 0), 2),
                    "pass_rate": round((passed / students) * 100, 1) if students else 0.0,
                }
            )

        exam_analyses: list[ExamAnalysisResult] = []
        weak_topics: list[dict] = []
        weak_skills: list[dict] = []
        for subject in subjects[:20]:
            result = self.analyze_exam(school_id, int(subject["exam_id"]))
            if result.valid:
                exam_analyses.append(result)
                for topic in result.topics[:3]:
                    if topic.success_rate < 50:
                        weak_topics.append(
                            {"subject": result.subject, "topic": topic.topic, "success_rate": topic.success_rate}
                        )
                for skill in result.skills[:3]:
                    if skill.success_rate < 50:
                        weak_skills.append(
                            {"subject": result.subject, "skill": skill.skill_name, "success_rate": skill.success_rate}
                        )

        dynamics = []
        for y in sorted({year - 2, year - 1, year}):
            if y <= 0:
                continue
            row = (
                ExamResult.objects.filter(student__school_id=school_id, exam__exam_type=exam_type, exam__year=y)
                .aggregate(students=Count("id"), avg_score=Avg("score"), passed=Count("id", filter=Q(passed=True)))
            )
            students = int(row["students"] or 0)
            if not students:
                continue
            dynamics.append(
                {
                    "year": y,
                    "students": students,
                    "avg_score": round(float(row["avg_score"] or 0), 2),
                    "pass_rate": round((int(row["passed"] or 0) / students) * 100, 1),
                }
            )

        return {
            "school_id": school_id,
            "exam_type": exam_type,
            "year": year,
            "subjects": subjects,
            "strong_subjects": strong_subjects,
            "weak_subjects": weak_subjects,
            "class_ranking": class_ranking,
            "weak_topics": sorted(weak_topics, key=lambda item: item["success_rate"])[:12],
            "weak_skills": sorted(weak_skills, key=lambda item: item["success_rate"])[:12],
            "dynamics": dynamics,
            "exam_analyses_count": len(exam_analyses),
        }
