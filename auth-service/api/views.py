from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User, Group
from rest_framework import status


class CustomLoginView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        if user.is_superuser or user.groups.filter(name='admin').exists():
            role = 'admin'
        else:
            role = 'viewer'
        return Response({
            'token': token.key,
            'role': role,
            'username': user.username,
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    username         = request.data.get('username', '').strip()
    email            = request.data.get('email', '').strip()
    password         = request.data.get('password', '')
    password_confirm = request.data.get('password_confirm', '')

    errors = {}

    if not username:
        errors['username'] = "Le nom d'utilisateur est requis."
    elif User.objects.filter(username=username).exists():
        errors['username'] = "Ce nom d'utilisateur est déjà pris."

    if not email:
        errors['email'] = "L'email est requis."
    elif User.objects.filter(email=email).exists():
        errors['email'] = "Un compte avec cet email existe déjà."

    if not password:
        errors['password'] = "Le mot de passe est requis."
    elif len(password) < 8:
        errors['password'] = "Le mot de passe doit contenir au moins 8 caractères."

    if password != password_confirm:
        errors['password_confirm'] = "Les mots de passe ne correspondent pas."

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )

    viewer_group, _ = Group.objects.get_or_create(name='viewer')
    user.groups.add(viewer_group)
    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'role': 'viewer',
        'username': user.username,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_token_view(request):
    token_key = request.data.get('token')
    try:
        token = Token.objects.get(key=token_key)
        user = token.user
        if user.is_superuser or user.groups.filter(name='admin').exists():
            role = 'admin'
        else:
            role = 'viewer'
        return Response({'valid': True, 'role': role, 'username': user.username})
    except Token.DoesNotExist:
        return Response({'valid': False}, status=status.HTTP_401_UNAUTHORIZED)