# File uploads

All file uploads should go into the `kirovy.models.file_base.CncNetFileBaseModel` class.

This class uses Django's [upload_to](https://docs.djangoproject.com/en/5.0/ref/models/fields/#django.db.models.FileField.upload_to)
logic to automatically place the files. By default, files will go to:

- `{seetings.MEDIA_ROOT}/{game_slug}/{object.UPLOAD_TYPE}/{object.id}/filename.ext`

An example of a default upload path would be:

- `/uploaded_media/yr/uncategorized_uploads/1234/conscript_sprites.shf`

## Customizing the upload path for a subclass

Controlling where a file is saved can be easily done by changing `UPLOAD_TYPE: str` for the subclass.
The default value is `uncategorized_uploads`.

If you need even more control, then override `kirovy.models.file_base.CncNetFileBaseModel.generate_upload_to` with your
own function. Files will still always be placed in `settings.MEDIA_ROOT`, but `generate_upload_to` can control
everything about the upload path after that application-wide root path.
