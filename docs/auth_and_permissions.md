# Authentication and Permissions
---

How permission is determined:

1. UI requests a JWT from the CnCNet ladder API
2. The UI calls Kirovy and includes the JWT token
3. The function `kirovy.authentication.CncNetAuthentication.authenticate` is called, which will create or updates
   the user object in Kirovy, then set `request.user` to that object.
4. The permission classes check their various permissions based on `request.user`


```mermaid
graph LR;
	url[Found in `urls.py`, points to a view]
	view_base[Views have an `authentication_classes` attribute to define an authenticator. It defaults to `kirovy.authentication.CncNetAuthentication`]
```
