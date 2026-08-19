from rest_framework import serializers


class AnalyticsFilterSerializer(serializers.Serializer):
    year = serializers.IntegerField(required=False)
    district_id = serializers.IntegerField(required=False)
    school_id = serializers.IntegerField(required=False)
