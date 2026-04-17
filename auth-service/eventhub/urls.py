from django.urls import path
from api.views import CustomLoginView, register_view, validate_token_view

urlpatterns = [
    path('api/auth/login/',          CustomLoginView.as_view()),
    path('api/auth/register/',       register_view),
    path('api/auth/validate-token/', validate_token_view),
]