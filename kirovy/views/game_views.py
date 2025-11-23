from django.db.models import QuerySet

from kirovy import permissions, typing as t
from kirovy.models import CncGame
from kirovy.views.base_views import KirovyListCreateView, KirovyDefaultPagination, KirovyRetrieveUpdateView


class GamesListView(KirovyListCreateView):

    permission_classes = [permissions.IsAdmin | permissions.ReadOnly]
    pagination_class: t.Type[KirovyDefaultPagination] | None = KirovyDefaultPagination

    def get_queryset(self) -> QuerySet[CncGame]:
        if self.request.user.is_staff:
            return CncGame.objects.all()

        return CncGame.objects.filter(is_visible=True)


class GameDetailView(KirovyRetrieveUpdateView):

    permission_classes = [permissions.IsAdmin | permissions.ReadOnly]
    pagination_class: t.Type[KirovyDefaultPagination] | None = KirovyDefaultPagination

    def get_queryset(self) -> QuerySet[CncGame]:
        if self.request.user.is_staff:
            return CncGame.objects.all()

        return CncGame.objects.filter(is_visible=True)
