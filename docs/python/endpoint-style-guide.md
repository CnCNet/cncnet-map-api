# Views

Before importing from the default Django REST Framework views, check to see if we
have a custom base view in [our base views](/kirovy/views/base_views.py) first.

They often have a lot of boilerplate, type hints, and custom request classes set up for you.

For example, use `KirovyApiView` instead of `rest_framework.views.APIView`.

# API Errors in API class helpers

Returning errors in the helper functions of your API endpoint can be annoying.
To avoid that annoyance, just raise one of the [view exceptions](/kirovy/exceptions/view_exceptions.py)
or write your own that subclasses `KirovyValidationError`.

**Example where you annoy yourself with bubbling returns:**

```python
class MyView(KirovyApiView):
    ...
    def helper(self, request: KirovyRequest) -> MyObject | KirovyResponse:
        object_id = request.data.get("id")
        if not object_id:
            return KirovyResponse(
                status=status.HTTP_400_BAD_REQUEST,
                data=ErrorResponseData(
                    message="Must specify id",
                    code=api_codes.FileUploadApiCodes.MISSING_FOREIGN_ID,
                    additional={"expected_field": "id"}
                )
            )

        object = get_object_or_404(self.file_parent_class.objects, id=object_id)
        self.check_object_permissions(request, object)

        return object

    def post(self, request: KirovyRequest, format=None) -> KirovyResponse:
        object = self.helper(request)
        if isinstance(object, KirovyResponse):
            return object
        ...
```

**Example where you just raise the exception:**

```python
class MyView(KirovyApiView):
    ...
    def helper(self, request: KirovyRequest) -> MyObject:
        object_id = request.data.get("id")
        if not object_id:
            raise KirovyValidationError(
                detail="Must specify id",
                code=api_codes.FileUploadApiCodes.MISSING_FOREIGN_ID,
                additional={"expected_field": "id"}
            )

        object = get_object_or_404(self.file_parent_class.objects, id=object_id)
        self.check_object_permissions(request, object)

        return object

    def post(self, request: KirovyRequest, format=None) -> KirovyResponse:
        object = self.helper(request)
        ...
```
