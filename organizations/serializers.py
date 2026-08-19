from rest_framework import serializers

from organizations.models import District, Ministry, School


class MinistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ministry
        fields = ("id", "name")


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ("id", "ministry", "code", "name")


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ("id", "district", "code", "name")
