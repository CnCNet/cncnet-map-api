# Map browser API

Endpoints the map browser UI, and CnCNet clients, use to list, sort, filter, download, and moderate maps.

## Listing and searching maps

`GET /maps/search/`

Results are paginated with `limit` and `offset` (default 30, max 200).

### Sorting

Use `?ordering=`. It takes the aliases below, or field names from `MapListView.ordering_fields`.
Prefix a field name with `-` for descending order, and separate several fields with commas.

| Alias      | What it does                                                                          |
|------------|---------------------------------------------------------------------------------------|
| `newest`   | Newest maps first. This is the default when `ordering` isn't set.                     |
| `popular`  | Most downloads of all time first.                                                     |
| `trending` | Most downloads in the last `MAP_TRENDING_WINDOW_DAYS` days (default 7) first.         |
| `updated`  | Maps with the most recently uploaded file version first.                              |

Field names: `map_name`, `created`, `modified`, `download_count`, `trending_download_count`,
`latest_file_created`, `latest_file_width`, `latest_file_height`, `id`.

The API ignores unknown fields instead of returning an error. It always adds `id` as a tie-breaker so that pages
stay stable.

### Filters

| Param                                                  | Example                                     | Notes                                                  |
|--------------------------------------------------------|---------------------------------------------|--------------------------------------------------------|
| `search`                                               | `?search=gold`                              | Map name, or the start of the description.             |
| `game_slug` / `cnc_game`                               | `?game_slug=yr`                             |                                                        |
| `categories` / `category_slug`                         | `?category_slug=standard&category_slug=koth` | Game modes. Matches maps with **any** of them.         |
| `author`                                               | `?author=Kane`                              | CnCNet username, case-insensitive.                     |
| `cnc_user_id`                                          | `?cnc_user_id=<uuid>`                       |                                                        |
| `min_width`, `max_width`, `min_height`, `max_height`   | `?min_width=100`                            | Uses the newest file version. Excludes legacy uploads. |
| `created_after`, `created_before`                      | `?created_after=2026-01-01T00:00:00Z`       | ISO 8601.                                              |
| `is_reviewed`                                          | `?is_reviewed=true`                         | Staff-curated maps.                                    |
| `include_edits`                                        | `?include_edits=true`                       | Include edits of other maps.                           |

Each result includes `download_count` and `cnc_user_name`, alongside the existing map fields.

## Downloading maps

- `GET /maps/<map_id>/download/` downloads the newest version of the map file.
- `GET /maps/<map_id>/download/?version=2` downloads a specific version.
- `GET /<game_slug>/<sha1>.zip` is the MapDB 1.0 compatible download for legacy clients. It's unchanged, except that
  it now returns `404` for banned maps.

Both download routes count the download. Counting updates `CncMap.download_count` (all time, for `popular`) and
`CncMapDownloadStat`, which keeps one row per map per day (for `trending`). Counters are incremented with `F()`
expressions, so concurrent downloads don't overwrite each other, and nothing about the downloader is stored.

## Editing and moderation

`PATCH /maps/<map_id>/` edits a map. Map authors can edit their own maps unless the map is banned.
Staff can edit any map.

- Editable fields are `map_name`, `description`, `category_ids`, `is_published`, and `incomplete_upload`.
- Only staff can set `is_reviewed`, which is used for curated map lists.
- Staff hide a map by setting `is_published` to false, or by banning it with `POST /admin/ban/`.
- When staff edit someone else's map, the map's `moderated_by` and `moderator_notes` are updated.
- Staff delete maps with `DELETE /maps/delete/<map_id>/`.

## Cleaning up temporary lobby uploads

Maps that CnCNet clients share in lobbies are uploaded anonymously and flagged `is_temporary`. To remove the ones
that are no longer used:

```shell
python manage.py purge_temporary_maps --days 90 --dry-run
python manage.py purge_temporary_maps --days 90
```

The command only deletes a map if all of these are true:

- It was uploaded more than `--days` days ago.
- It hasn't been downloaded in that window.
- It isn't banned. Banned maps are kept so their hashes keep blocking re-uploads.
- No other map lists it as its parent.

The command also deletes the map's files from storage. Nothing schedules it, so it only runs when someone runs it.
