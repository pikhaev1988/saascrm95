from django.db import models


class Ministry(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Министерство"
        verbose_name_plural = "Министерства"


class District(models.Model):
    ministry = models.ForeignKey(Ministry, on_delete=models.CASCADE, related_name="districts")
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ("ministry", "name")
        ordering = ("name",)
        verbose_name = "Район"
        verbose_name_plural = "Районы"

    def __str__(self):
        return f"{self.code} - {self.name}"


class School(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="schools")
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = ("district", "name")
        ordering = ("name",)
        verbose_name = "Школа"
        verbose_name_plural = "Школы"

    def __str__(self):
        return f"{self.code} - {self.name}"
