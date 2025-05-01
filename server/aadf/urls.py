# aadf/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TenderViewSet, OfferViewSet, TenderDocumentViewSet, OfferDocumentViewSet,
    EvaluationViewSet, LoginView, LogoutView, RegisterView, ChangePasswordView,
    DocumentDownloadView
)

router = DefaultRouter()
router.register(r'tenders', TenderViewSet)
router.register(r'offers', OfferViewSet)
router.register(r'tender-documents', TenderDocumentViewSet)
router.register(r'offer-documents', OfferDocumentViewSet)
router.register(r'evaluations', EvaluationViewSet)

urlpatterns = [
    # API Endpoints
    path('', include(router.urls)),

    # Authentication Endpoints
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),

    # File Download Endpoint
    path('download/<str:document_type>/<int:document_id>/', DocumentDownloadView.as_view(), name='document-download'),

    # DRF browsable API authentication
    path('api-auth/', include('rest_framework.urls')),
]