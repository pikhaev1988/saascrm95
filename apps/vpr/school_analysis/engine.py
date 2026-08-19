"""
Оркестратор комплексной аналитики школы по ВПР.

Не пересчитывает протокольную аналитику: только вызывает
VprComprehensiveAnalysisEngine / get_protocol_analysis и агрегирует.
"""

from __future__ import annotations

from apps.vpr.comprehensive_analysis import get_protocol_analysis
from apps.vpr.comprehensive_analysis.engine import VprComprehensiveAnalysisEngine
from apps.vpr.models import VprProtocol
from apps.vpr.school_analysis.deficits import SchoolDeficitsAggregator
from apps.vpr.school_analysis.dynamics import SchoolDynamicsAnalyzer
from apps.vpr.school_analysis.grades import SchoolGradesAnalyzer
from apps.vpr.school_analysis.overview import SchoolOverviewBuilder
from apps.vpr.school_analysis.recommendations import SchoolRecommendationsBuilder
from apps.vpr.school_analysis.risk import SchoolRiskClassifier
from apps.vpr.school_analysis.schemas import SchoolAnalysisResult, SchoolOverview
from apps.vpr.school_analysis.strengths import SchoolStrengthsAnalyzer
from apps.vpr.school_analysis.subjects import SchoolSubjectsAnalyzer
from apps.vpr.school_analysis.weaknesses import SchoolWeaknessesAnalyzer
from organizations.models import School


class VprSchoolAnalysisEngine:
    """
    Использование::

        analysis = VprSchoolAnalysisEngine().analyze(organization, academic_year)
    """

    def __init__(
        self,
        *,
        protocol_engine: VprComprehensiveAnalysisEngine | None = None,
        use_cache: bool | None = None,
    ) -> None:
        self.protocol_engine = protocol_engine or VprComprehensiveAnalysisEngine()
        self.use_cache = use_cache
        self.overview_builder = SchoolOverviewBuilder()
        self.subjects_analyzer = SchoolSubjectsAnalyzer()
        self.grades_analyzer = SchoolGradesAnalyzer()
        self.strengths_analyzer = SchoolStrengthsAnalyzer()
        self.weaknesses_analyzer = SchoolWeaknessesAnalyzer()
        self.deficits_aggregator = SchoolDeficitsAggregator()
        self.risk_classifier = SchoolRiskClassifier()
        self.recommendations_builder = SchoolRecommendationsBuilder()
        self.dynamics_analyzer = SchoolDynamicsAnalyzer()

    def analyze(
        self,
        organization: School | int,
        academic_year: int | None,
    ) -> SchoolAnalysisResult:
        school = self._resolve_school(organization)
        year_protocols = self._protocols_for_year(school, academic_year)
        year_analyses = [self._analyze_protocol(p) for p in year_protocols]

        overview = self.overview_builder.build(
            year_analyses,
            organization_name=school.name,
            academic_year=academic_year,
            protocols=year_protocols,
        )
        if not year_analyses:
            dynamics = self._build_dynamics(school, focus_year=academic_year)
            return SchoolAnalysisResult(overview=overview, dynamics=dynamics)

        subjects = self.subjects_analyzer.analyze(year_analyses)
        grades = self.grades_analyzer.analyze(year_analyses)
        strengths = self.strengths_analyzer.analyze(
            analyses=year_analyses,
            subjects=subjects,
            grades=grades,
        )
        weaknesses = self.weaknesses_analyzer.analyze(
            analyses=year_analyses,
            subjects=subjects,
            grades=grades,
        )
        deficits = self.deficits_aggregator.analyze(year_analyses)
        risk_profile = self.risk_classifier.classify(
            overview=overview,
            deficits=deficits,
            analyses=year_analyses,
        )
        recommendations = self.recommendations_builder.build(
            year_analyses,
            subjects=subjects,
        )
        dynamics = self._build_dynamics(school, focus_year=academic_year)

        return SchoolAnalysisResult(
            overview=overview,
            subjects=subjects,
            grades=grades,
            strengths=strengths,
            weaknesses=weaknesses,
            deficits=deficits,
            risk_profile=risk_profile,
            recommendations=recommendations,
            dynamics=dynamics,
        )

    def analyze_to_dict(
        self,
        organization: School | int,
        academic_year: int | None,
    ) -> dict:
        return self.analyze(organization, academic_year).to_dict()

    def _analyze_protocol(self, protocol: VprProtocol):
        return get_protocol_analysis(
            protocol,
            engine=self.protocol_engine,
            use_cache=self.use_cache,
        )

    def _build_dynamics(self, school: School, *, focus_year: int | None):
        all_protocols = list(
            VprProtocol.objects.filter(school=school)
            .select_related("upload")
            .order_by("academic_year", "subject", "parallel", "id")
        )
        if not all_protocols:
            return self.dynamics_analyzer.analyze({})

        by_year: dict[int, list] = {}
        for protocol in all_protocols:
            analysis = self._analyze_protocol(protocol)
            by_year.setdefault(int(protocol.academic_year), []).append(analysis)
        return self.dynamics_analyzer.analyze(by_year)

    @staticmethod
    def _resolve_school(organization: School | int) -> School:
        if isinstance(organization, School):
            return organization
        return School.objects.get(pk=int(organization))

    @staticmethod
    def _protocols_for_year(school: School, academic_year: int | None) -> list[VprProtocol]:
        qs = VprProtocol.objects.filter(school=school).select_related("upload").prefetch_related(
            "student_results"
        )
        if academic_year is not None:
            qs = qs.filter(academic_year=int(academic_year))
        return list(qs.order_by("subject", "parallel", "id"))
