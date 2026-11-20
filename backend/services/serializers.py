from rest_framework import serializers

from .models import Service, ServiceScopeOption, ServiceScopeQuestion


class ServiceScopeOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceScopeOption
        fields = ["id", "value", "label"]
        read_only_fields = fields


class ServiceScopeQuestionSerializer(serializers.ModelSerializer):
    options = ServiceScopeOptionSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = ServiceScopeQuestion
        fields = ["id", "key", "label", "options"]
        read_only_fields = fields


class ServiceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "description",
            "minimum_price",
            "maximum_price",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        minimum_price = data.get(
            "minimum_price",
            getattr(self.instance, "minimum_price", None)
        )

        maximum_price = data.get(
            "maximum_price",
            getattr(self.instance, "maximum_price", None)
        )

        if (
            minimum_price is not None
            and maximum_price is not None
            and minimum_price > maximum_price
        ):
            raise serializers.ValidationError(
                "Minimum price cannot be greater than maximum price."
            )

        return data