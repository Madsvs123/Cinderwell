from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import Organization, User
from apps.ledger.chart import seed_chart


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    organization_name = serializers.CharField(max_length=160)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data["name"],
        )
        organization = Organization.objects.create(name=validated_data["organization_name"], owner=user)
        seed_chart(organization)
        return user


class UserSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_id = serializers.IntegerField(source="organization.id", read_only=True)
    currency = serializers.CharField(source="organization.base_currency", read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "name", "organization_id", "organization_name", "currency")
