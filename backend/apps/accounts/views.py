from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.accounts.serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        return Response(self.get_serializer(request.user).data)
