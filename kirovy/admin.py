"""Django admin registrations for Kirovy models.

The sync log admin is the primary reason this file exists. It provides a
grouped view of sync logs by game session with a direct link to the
compare endpoint for side-by-side log analysis.
"""

from django.contrib import admin
from django.utils.html import format_html

from kirovy.models.sync_log import SyncLog


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = (
        "player_name",
        "sync_file_index",
        "game_hash_short",
        "map_name",
        "game_mode",
        "game_slug",
        "ip_address",
        "uploaded_at",
        "compare_link",
    )
    list_filter = ("cnc_game__slug", "uploaded_at")
    search_fields = ("game_hash", "player_name", "map_sha1", "map_name")
    readonly_fields = ("id", "uploaded_at", "game_hash", "ip_address", "compare_link")
    ordering = ("-uploaded_at",)

    @admin.display(description="Game", ordering="cnc_game__slug")
    def game_slug(self, obj: SyncLog) -> str:
        return obj.cnc_game.slug if obj.cnc_game else "—"

    @admin.display(description="Game Hash")
    def game_hash_short(self, obj: SyncLog) -> str:
        return obj.game_hash[:12] + "…"

    @admin.display(description="Compare Session")
    def compare_link(self, obj: SyncLog) -> str:
        return format_html(
            '<a href="/sync-logs/compare/{}/view/" target="_blank">Compare logs</a>',
            obj.game_hash,
        )
