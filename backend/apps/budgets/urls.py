from rest_framework.routers import DefaultRouter

from apps.budgets.views import BudgetLineViewSet

router = DefaultRouter()
router.register("budgets", BudgetLineViewSet, basename="budget")
urlpatterns = router.urls
