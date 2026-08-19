from django.test import SimpleTestCase

from exams.passing import gve_subject_label, is_gve_exam


class GvePassingTests(SimpleTestCase):
    def test_code_51_is_gve_russian(self):
        self.assertTrue(is_gve_exam(exam_code="51"))
        self.assertTrue(is_gve_exam(exam_code="051"))
        self.assertFalse(is_gve_exam(exam_code="01"))
        self.assertFalse(is_gve_exam(exam_code="1"))

    def test_name_with_gve_marker(self):
        self.assertTrue(is_gve_exam(subject_name="Русский язык ГВЭ"))
        self.assertFalse(is_gve_exam(subject_name="Русский язык"))

    def test_subject_label(self):
        self.assertEqual(gve_subject_label("Русский язык", "51"), "Русский язык (ГВЭ)")
        self.assertEqual(gve_subject_label("Русский язык", "01"), "Русский язык")
