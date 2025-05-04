# server/aadf/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Authentication views
    LoginView, LogoutView, RegisterView, ChangePasswordView, UserProfileView, AdminCreateUserView,
    
    # Main model viewsets
    TenderViewSet, OfferViewSet, TenderDocumentViewSet, OfferDocumentViewSet,
    EvaluationViewSet, EvaluationCriteriaViewSet, VendorCompanyViewSet, VendorUserViewSet,
    ApprovalViewSet, ReportViewSet, NotificationViewSet, AuditLogViewSet,
    
    # Document handling
    DocumentDownloadView,
    
    # Dashboard and management views
    DashboardView, TenderSearchView, UserManagementView
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'tenders', TenderViewSet)
router.register(r'offers', OfferViewSet)
router.register(r'tender-documents', TenderDocumentViewSet)
router.register(r'offer-documents', OfferDocumentViewSet)
router.register(r'evaluations', EvaluationViewSet)
router.register(r'evaluation-criteria', EvaluationCriteriaViewSet)
router.register(r'vendor-companies', VendorCompanyViewSet)
router.register(r'vendor-users', VendorUserViewSet)
router.register(r'approvals', ApprovalViewSet)
router.register(r'reports', ReportViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'audit-logs', AuditLogViewSet)

urlpatterns = [
    # API Endpoints
    path('', include(router.urls)),
    
    # Authentication Endpoints
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('auth/profile/', UserProfileView.as_view(), name='user-profile'),
    path('auth/admin-create-user/', AdminCreateUserView.as_view(), name='admin-create-user'),
    
    # File Download Endpoint
    path('download/<str:document_type>/<int:document_id>/', DocumentDownloadView.as_view(), name='document-download'),
    
    # Custom endpoints
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('tenders/search/', TenderSearchView.as_view(), name='tender-search'),
    
    # User management endpoints
    path('users/', UserManagementView.as_view(), name='user-list'),
    path('users/<int:user_id>/', UserManagementView.as_view(), name='user-detail'),
    path('users/<int:user_id>/reset-password/', UserManagementView.as_view(), name='user-reset-password'),
    path('reports/<int:pk>/secure-download-link/', ReportViewSet.as_view({'get': 'secure_download_link'}), name='report-secure-download-link'),
    # AI-enhanced endpoints
    path('ai/analyze-tender/<int:tender_id>/', TenderViewSet.as_view({'get': 'analyze_tender'}), name='ai-analyze-tender'),
    path('ai/analyze-offer/<int:offer_id>/', OfferViewSet.as_view({'get': 'analyze_offer'}), name='ai-analyze-offer'),
    path('ai/evaluate-suggestions/<int:offer_id>/', EvaluationViewSet.as_view({'get': 'ai_recommend_evaluations'}), name='ai-evaluate-suggestions'),
    path('ai/vendor-analysis/<int:pk>/', VendorCompanyViewSet.as_view({'get': 'ai_performance_analysis'}), name='ai-vendor-analysis'),
    path('ai/evaluation-anomalies/<int:tender_id>/', EvaluationViewSet.as_view({'get': 'detect_evaluation_anomalies'}), name='ai-evaluation-anomalies'),
    path('ai/analytics-report/<int:tender_id>/', ReportViewSet.as_view({'post': 'generate_ai_enhanced_report'}), name='ai-analytics-report'),
    path('ai/vendor-team-analysis/<int:pk>/', VendorCompanyViewSet.as_view({'get': 'team_analysis'}), name='ai-vendor-team-analysis'),
    
    # DRF browsable API authentication
    path('api-auth/', include('rest_framework.urls')),
]