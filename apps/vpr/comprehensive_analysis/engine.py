"""
Оркестратор комплексного аналитического профиля ВПР.

Не изменяет логику существующих движков: только вызывает их и собирает профиль.
"""

from __future__ import annotations

from apps.vpr.analytics import VprAnalyticsEngine
from apps.vpr.analytics.result import VprAnalyticsResult
from apps.vpr.causes import VprCauseAnalysisEngine
from apps.vpr.comprehensive_analysis.achievement import VprAchievementAnalyzer
from apps.vpr.comprehensive_analysis.groups import VprParticipantGroupAnalyzer
from apps.vpr.comprehensive_analysis.objectivity import VprObjectivityAnalyzer
from apps.vpr.comprehensive_analysis.recommendations import VprRecommendationEngine
from apps.vpr.comprehensive_analysis.schemas import (
    VprComprehensiveAnalysisResult,
    VprProtocolBrief,
)
from apps.vpr.comprehensive_analysis.school_profile import VprSchoolProfileClassifier
from apps.vpr.comprehensive_analysis.skills import VprSkillAnalyzer
from apps.vpr.comprehensive_analysis.tasks import VprTaskAnalyzer
from apps.vpr.comprehensive_analysis.topics import VprTopicAnalyzer
from apps.vpr.conclusion import VprConclusionEngine
from apps.vpr.deficits import VprDeficitEngine
from apps.vpr.models import VprProtocol


class VprComprehensiveAnalysisEngine:
    """
    Использование::

        from apps.vpr.comprehensive_analysis import VprComprehensiveAnalysisEngine

        result = VprComprehensiveAnalysisEngine().analyze(protocol)
    """

    def __init__(
        self,
        *,
        analytics_engine: VprAnalyticsEngine | None = None,
        deficit_engine: VprDeficitEngine | None = None,
        cause_engine: VprCauseAnalysisEngine | None = None,
        conclusion_engine: VprConclusionEngine | None = None,
    ) -> None:
        self.analytics_engine = analytics_engine or VprAnalyticsEngine()
        self.deficit_engine = deficit_engine or VprDeficitEngine()
        self.cause_engine = cause_engine or VprCauseAnalysisEngine()
        self.conclusion_engine = conclusion_engine or VprConclusionEngine()
        self.achievement_analyzer = VprAchievementAnalyzer()
        self.task_analyzer = VprTaskAnalyzer()
        self.topic_analyzer = VprTopicAnalyzer()
        self.skill_analyzer = VprSkillAnalyzer()
        self.group_analyzer = VprParticipantGroupAnalyzer()
        self.objectivity_analyzer = VprObjectivityAnalyzer()
        self.school_classifier = VprSchoolProfileClassifier()
        self.recommendation_engine = VprRecommendationEngine()

    def analyze(self, protocol: VprProtocol | int) -> VprComprehensiveAnalysisResult:
        protocol_obj = self._resolve_protocol(protocol)

        analytics = self.analytics_engine.analyze(protocol_obj)
        deficits = self.deficit_engine.analyze(analytics, protocol=protocol_obj)
        causes = self.cause_engine.analyze(analytics, deficits)
        # VprConclusionEngine API без изменений: build(analytics, deficits).
        # Темы/умения/классификация дефицитов уже входят в эти объекты через справочник.
        conclusion = self.conclusion_engine.build(analytics, deficits)

        return self._assemble(protocol_obj, analytics, deficits, causes, conclusion)

    def analyze_from_parts(
        self,
        analytics: VprAnalyticsResult,
        *,
        protocol: VprProtocol | int | None = None,
        deficits=None,
        causes=None,
        conclusion=None,
    ) -> VprComprehensiveAnalysisResult:
        """Сборка профиля из уже рассчитанных частей (для тестов и повторного использования)."""
        protocol_obj = self._resolve_protocol(protocol) if protocol is not None else None
        if deficits is None:
            deficits = self.deficit_engine.analyze(analytics, protocol=protocol_obj)
        if causes is None:
            causes = self.cause_engine.analyze(analytics, deficits)
        if conclusion is None:
            conclusion = self.conclusion_engine.build(analytics, deficits)
        return self._assemble(protocol_obj, analytics, deficits, causes, conclusion)

    def analyze_to_dict(self, protocol: VprProtocol | int) -> dict:
        return self.analyze(protocol).to_dict()

    def _assemble(
        self,
        protocol: VprProtocol | None,
        analytics: VprAnalyticsResult,
        deficits,
        causes,
        conclusion,
    ) -> VprComprehensiveAnalysisResult:
        achievement = self.achievement_analyzer.analyze(analytics)
        task_analysis = self.task_analyzer.analyze(analytics, deficits)
        topic_analysis = self.topic_analyzer.analyze(analytics, deficits)
        skill_analysis = self.skill_analyzer.analyze(analytics, deficits)
        participant_groups = self.group_analyzer.analyze(analytics)
        objectivity = self.objectivity_analyzer.analyze(analytics)
        school_profile = self.school_classifier.classify(
            achievement=achievement,
            groups=participant_groups,
            objectivity=objectivity,
            topics=topic_analysis,
            deficits=deficits,
        )
        recommendations = self.recommendation_engine.build(
            topics=topic_analysis,
            skills=skill_analysis,
            deficits=deficits,
            causes=causes,
        )

        if protocol is not None:
            brief = VprProtocolBrief(
                protocol_id=protocol.pk,
                subject=protocol.subject,
                parallel=int(protocol.parallel),
                academic_year=int(protocol.academic_year),
                organization_name=protocol.organization_name or "",
                participants_count=int(
                    protocol.participants_count or analytics.summary.participants_count or 0
                ),
                max_primary_score=int(
                    protocol.max_primary_score or analytics.summary.max_primary_score or 0
                ),
            )
        else:
            brief = VprProtocolBrief(
                protocol_id=analytics.protocol_id,
                subject=analytics.subject,
                parallel=int(analytics.parallel),
                academic_year=int(analytics.academic_year),
                organization_name=analytics.organization_name or "",
                participants_count=int(analytics.summary.participants_count or 0),
                max_primary_score=int(analytics.summary.max_primary_score or 0),
            )

        return VprComprehensiveAnalysisResult(
            protocol=brief,
            achievement=achievement,
            task_analysis=task_analysis,
            topic_analysis=topic_analysis,
            skill_analysis=skill_analysis,
            participant_groups=participant_groups,
            objectivity=objectivity,
            school_profile=school_profile,
            deficits=deficits,
            causes=causes,
            recommendations=recommendations,
            conclusion=conclusion,
            analytics=analytics,
        )

    @staticmethod
    def _resolve_protocol(protocol: VprProtocol | int) -> VprProtocol:
        if isinstance(protocol, VprProtocol):
            return protocol
        return VprProtocol.objects.get(pk=int(protocol))
