from django.db.models import QuerySet, Sum
from django.http import HttpResponse
from django.utils.html import escape
from django.views import View
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny

from kirovy import logging
from kirovy.models import CncGame, SyncLog
from kirovy.objects.ui_objects import ResultResponseData
from kirovy.request import KirovyRequest
from kirovy.response import KirovyResponse
from kirovy.views.base_views import KirovyApiView

_LOGGER = logging.get_logger(__name__)

_MAX_SYNC_LOG_BYTES = 10 * 1024 * 1024  # 10 MB per file — sync logs are typically 300-3000 KB each
_STORAGE_CAP_BYTES = 500 * 1024 * 1024  # 500 MB total storage cap


class SyncLogUploadView(KirovyApiView):
    """Accept a SYNC*.TXT file from a CnCNet game client after a desync.

    No authentication required — players should not need an account for this.
    One file per player slot per machine per game session is enforced by a unique constraint.
    """

    parser_classes = [MultiPartParser]
    permission_classes = [AllowAny]

    def post(self, request: KirovyRequest, format=None) -> KirovyResponse:
        uploaded_file = request.data.get("file")
        game_hash = request.data.get("game_hash", "").strip()
        player_name = request.data.get("player_name", "").strip()
        sync_file_index = request.data.get("sync_file_index", "0")
        map_sha1 = request.data.get("map_sha1", "").strip()
        map_name = request.data.get("map_name", "").strip()
        game_mode = request.data.get("game_mode", "").strip()
        game_slug = request.data.get("game_slug", "").strip()

        if not uploaded_file:
            return KirovyResponse(
                ResultResponseData(message="No file provided."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not game_hash:
            return KirovyResponse(
                ResultResponseData(message="game_hash is required."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not player_name:
            return KirovyResponse(
                ResultResponseData(message="player_name is required."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sync_file_index = int(sync_file_index)
        except (ValueError, TypeError):
            return KirovyResponse(
                ResultResponseData(message="sync_file_index must be an integer 0–7."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (0 <= sync_file_index <= 7):
            return KirovyResponse(
                ResultResponseData(message="sync_file_index must be 0–7."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        if uploaded_file.size > _MAX_SYNC_LOG_BYTES:
            return KirovyResponse(
                ResultResponseData(message="File too large."),
                status=status.HTTP_400_BAD_REQUEST,
            )

        cnc_game = CncGame.objects.filter(slug__iexact=game_slug).first() if game_slug else None

        ip_address = request.client_ip_address

        # Silently succeed on duplicates — the client may retry on network failure.
        existing = SyncLog.objects.filter(
            game_hash=game_hash,
            sync_file_index=sync_file_index,
            ip_address=ip_address,
        ).first()
        if existing:
            _LOGGER.debug(
                "sync_log.duplicate_upload",
                game_hash=game_hash,
                sync_file_index=sync_file_index,
                ip=ip_address,
            )
            return KirovyResponse(
                ResultResponseData(message="Sync log already uploaded.", result={"id": str(existing.id)}),
                status=status.HTTP_200_OK,
            )

        uploaded_file.name = f"{game_hash}_{sync_file_index}_{ip_address.replace(':', '_')}.txt"
        file_size = uploaded_file.size

        sync_log = SyncLog(
            game_hash=game_hash,
            player_name=player_name[:64],
            sync_file_index=sync_file_index,
            map_sha1=map_sha1[:40],
            map_name=map_name[:255],
            game_mode=game_mode[:128],
            cnc_game=cnc_game,
            file=uploaded_file,
            file_size=file_size,
            ip_address=ip_address,
        )
        sync_log.save()

        _LOGGER.info(
            "sync_log.uploaded",
            game_hash=game_hash,
            player=player_name,
            index=sync_file_index,
            ip=ip_address,
        )

        self._enforce_storage_cap()

        return KirovyResponse(
            ResultResponseData(message="Sync log uploaded.", result={"id": str(sync_log.id)}),
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _enforce_storage_cap() -> None:
        """Delete oldest sync logs until total storage is under :data:`_STORAGE_CAP_BYTES`."""
        total = SyncLog.objects.aggregate(total=Sum("file_size"))["total"] or 0
        if total <= _STORAGE_CAP_BYTES:
            return

        # Order oldest-first; delete until we're under the cap.
        for log in SyncLog.objects.order_by("uploaded_at").iterator():
            if total <= _STORAGE_CAP_BYTES:
                break
            try:
                log.file.delete(save=False)
            except Exception:
                pass
            total -= log.file_size
            log.delete()
            _LOGGER.info("sync_log.evicted_for_cap", id=str(log.id), remaining_bytes=total)


class SyncLogSessionView(KirovyApiView):
    """List all sync logs for a game session, identified by game_hash."""

    permission_classes = [AllowAny]

    def get(self, request: KirovyRequest, game_hash: str, format=None) -> KirovyResponse:
        logs: QuerySet[SyncLog] = (
            SyncLog.objects.filter(game_hash=game_hash)
            .select_related("cnc_game")
            .order_by("sync_file_index", "uploaded_at")
        )

        result = [
            {
                "id": str(log.id),
                "player_name": log.player_name,
                "sync_file_index": log.sync_file_index,
                "map_name": log.map_name,
                "map_sha1": log.map_sha1,
                "game_mode": log.game_mode,
                "game_slug": log.cnc_game.slug if log.cnc_game else "",
                "uploaded_at": log.uploaded_at.isoformat(),
                "file_url": request.build_absolute_uri(log.file.url),
            }
            for log in logs
        ]

        return KirovyResponse(
            ResultResponseData(
                message=f"{len(result)} log(s) for session {game_hash[:8]}…",
                result={"game_hash": game_hash, "logs": result},
            )
        )


class SyncLogCompareView(KirovyApiView):
    """Return the raw text of all sync logs for a game session for side-by-side comparison."""

    permission_classes = [AllowAny]

    def get(self, request: KirovyRequest, game_hash: str, format=None) -> KirovyResponse:
        logs: QuerySet[SyncLog] = SyncLog.objects.filter(game_hash=game_hash).order_by("sync_file_index", "uploaded_at")

        result = {}
        for log in logs:
            key = f"SYNC{log.sync_file_index}_{log.player_name}"
            try:
                with log.file.open("r") as f:
                    result[key] = f.read()
            except Exception as e:
                result[key] = f"[Error reading file: {e}]"

        return KirovyResponse(
            ResultResponseData(
                message=f"Raw sync logs for session {game_hash[:8]}…",
                result={"game_hash": game_hash, "files": result},
            )
        )


# ---------------------------------------------------------------------------
# HTML compare page
# ---------------------------------------------------------------------------

_COMPARE_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sync Logs \u2014 __SHORT_HASH__\u2026</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/diff2html@3.4.47/bundles/css/diff2html.min.css">
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; margin: 0; padding: 1rem 2rem;
           background: #f0f2f5; color: #222; }
    h1 { font-size: 1.1rem; margin: 0 0 1rem; }
    h1 code { background: #dde; padding: 2px 6px; border-radius: 3px; font-size: 1rem; }
    .controls { display: flex; gap: .75rem; align-items: center; flex-wrap: wrap;
                background: #fff; border: 1px solid #ddd; border-radius: 6px;
                padding: .75rem 1rem; margin-bottom: 1rem; }
    .controls label { font-size: .85rem; color: #555; }
    select { padding: .35rem .5rem; border: 1px solid #bbb; border-radius: 4px;
             min-width: 220px; font-size: .9rem; }
    button { padding: .35rem 1.1rem; background: #0066cc; color: #fff; border: none;
             border-radius: 4px; cursor: pointer; font-size: .9rem; }
    button:hover { background: #0055aa; }
    #status { font-size: .85rem; color: #666; }
    #diff-output { background: #fff; border: 1px solid #ddd; border-radius: 6px;
                   overflow-x: auto; }
  </style>
</head>
<body>
  <h1>Sync Log Compare \u2014 <code>__SHORT_HASH__\u2026</code></h1>

  <div class="controls">
    <label for="file-a">File A</label>
    <select id="file-a"><option value="">Loading\u2026</option></select>
    <label for="file-b">File B</label>
    <select id="file-b"><option value="">Loading\u2026</option></select>
    <button onclick="runCompare()">Compare</button>
    <span id="status"></span>
  </div>

  <div id="diff-output"></div>

  <script src="https://cdn.jsdelivr.net/npm/diff@5.2.0/dist/diff.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/diff2html@3.4.47/bundles/js/diff2html-ui.min.js"></script>
  <script>
    var SESSION_URL = "/sync-logs/session/__GAME_HASH__/";
    var logs = [];

    async function init() {
      var status = document.getElementById("status");
      status.textContent = "Loading session\u2026";
      try {
        var res = await fetch(SESSION_URL);
        if (!res.ok) throw new Error("HTTP " + res.status);
        var data = await res.json();
        logs = data.result.logs;
        populateSelects();
        status.textContent = logs.length + " log(s) found.";
      } catch (e) {
        status.textContent = "Error: " + e.message;
      }
    }

    function populateSelects() {
      var selA = document.getElementById("file-a");
      var selB = document.getElementById("file-b");
      selA.innerHTML = '<option value="">— Select file A —</option>';
      selB.innerHTML = '<option value="">— Select file B —</option>';
      logs.forEach(function(log, i) {
        var label = "SYNC" + log.sync_file_index + " \u2014 " + log.player_name;
        [selA, selB].forEach(function(sel) {
          var opt = document.createElement("option");
          opt.value = i;
          opt.textContent = label;
          sel.appendChild(opt);
        });
      });
      if (logs.length >= 1) selA.value = 0;
      if (logs.length >= 2) selB.value = 1;
    }

    async function runCompare() {
      var status = document.getElementById("status");
      var ai = document.getElementById("file-a").value;
      var bi = document.getElementById("file-b").value;
      if (ai === "" || bi === "") {
        status.textContent = "Select both files first.";
        return;
      }
      if (ai === bi) {
        status.textContent = "Select two different files.";
        return;
      }
      var logA = logs[ai];
      var logB = logs[bi];
      status.textContent = "Fetching files\u2026";
      try {
        var [textA, textB] = await Promise.all([
          fetch(logA.file_url).then(function(r) {
            if (!r.ok) throw new Error("HTTP " + r.status + " for file A");
            return r.text();
          }),
          fetch(logB.file_url).then(function(r) {
            if (!r.ok) throw new Error("HTTP " + r.status + " for file B");
            return r.text();
          }),
        ]);
        var nameA = "SYNC" + logA.sync_file_index + "_" + logA.player_name;
        var nameB = "SYNC" + logB.sync_file_index + "_" + logB.player_name;
        var patch = Diff.createTwoFilesPatch(nameA, nameB, textA, textB, "", "", {context: 5});
        var container = document.getElementById("diff-output");
        container.innerHTML = "";
        var ui = new Diff2HtmlUI(container, patch, {
          drawFileList: false,
          matching: "lines",
          outputFormat: "side-by-side",
          highlight: false,
        });
        ui.draw();
        status.textContent = "Done.";
      } catch (e) {
        status.textContent = "Error: " + e.message;
      }
    }

    init();
  </script>
</body>
</html>
"""


class SyncLogComparePageView(View):
    """Serve an HTML page for side-by-side sync log diffing.

    The page fetches the session data via the JSON API, lets the user pick two
    logs from dropdowns, then diffs them client-side using jsdiff + diff2html.
    No authentication required — same access level as the session endpoint.
    """

    def get(self, request, game_hash: str) -> HttpResponse:
        safe_hash = escape(game_hash)
        short_hash = escape(game_hash[:8])
        html = _COMPARE_PAGE.replace("__GAME_HASH__", safe_hash).replace("__SHORT_HASH__", short_hash)
        return HttpResponse(html, content_type="text/html; charset=utf-8")
