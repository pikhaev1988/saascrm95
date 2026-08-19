from django.test import TestCase

from users.task_topics import (
    EGE_GEOGRAPHY_TASK_SKILLS,
    EGE_GEOGRAPHY_TASK_TOPICS,
    is_expanded_answer_task,
    part2_start_task,
    skill_for_task,
    topic_for_task,
)

EXPECTED_BOUNDARY = 22
PART2_TASKS = range(22, 30)


class GeographyEge2026TaskTopicsTests(TestCase):
    def test_all_tasks_1_29_have_static_topics_and_skills(self):
        for number in range(1, 30):
            with self.subTest(task=number):
                self.assertIn(number, EGE_GEOGRAPHY_TASK_TOPICS)
                self.assertIn(number, EGE_GEOGRAPHY_TASK_SKILLS)
                self.assertEqual(
                    topic_for_task("География", number, "ege"),
                    EGE_GEOGRAPHY_TASK_TOPICS[number],
                )
                self.assertEqual(
                    skill_for_task("География", number, "ege"),
                    EGE_GEOGRAPHY_TASK_SKILLS[number],
                )

    def test_kim_part_boundary(self):
        for number in range(1, EXPECTED_BOUNDARY):
            self.assertFalse(is_expanded_answer_task("ege", "geography", number), number)
        for number in PART2_TASKS:
            self.assertTrue(is_expanded_answer_task("ege", "geography", number), number)
        self.assertEqual(part2_start_task("ege", "geography"), EXPECTED_BOUNDARY)

    def test_subject_aliases(self):
        self.assertEqual(
            topic_for_task("география", 5, "ege"),
            EGE_GEOGRAPHY_TASK_TOPICS[5],
        )
        self.assertEqual(
            skill_for_task("География", 29, "ege"),
            EGE_GEOGRAPHY_TASK_SKILLS[29],
        )
