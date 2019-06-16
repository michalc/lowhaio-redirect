# lowhaio-redirect

Wrapper of lowhaio that follows HTTP redirects

> This is a work in-progress. This document serves as a rough design spec.


## Installation

```bash
pip install lowhaio lowhaio_redirect
```


## Usage

The `request` function returned from `lowhaio.Pool` must be wrapped with `lowhaio_redirect.redirectable`, as in the below example.

```python
import os
from lowhaio import Pool
from lowhaio_redirect import redirectable

request, _ = Pool()

redirectable_request = redirectable(request)
code, headers, body = await redirectable_request(b'GET', 'https://example.com/path')

async for chunk in body:
    print(chunk)
```


## Method and body changing

By default, for 301, 302 and 303 redirects, HEAD and GET requests are redirected with unchanged methods and bodies, and other methods are converted into GETs with empty bodies. For 307 and 308 redirects, the method and bodies are always unchanged.

Note however, that an unchanged body is actually _not_ guaranteed by this wrapper. For each request the function passed as the `body` argument is called, and it may return different things on each call. It is up the the developer to handle this case as needed: there is no one-size-fits all approach, since for streaming requests, the body may not be available again. In many cases, a redirect that expects a resubmission of a large upload may be an error; or if an API is never expected to return a redirect, _not_ using this wrapper may be a viable option.


## Customise redirects

It is possible to customise which redirects are followed, and how they affect the method and body. As an example, to recreate the default behaviour explicitly, the below code could be used.

```python
def get(_, _):
    # Asynchronous generator that end immediately, and results in an empty body
    async def empty_body():
        while False:
            yield

    return (b'GET', empty_body)

def unchanged(method, body):
    return (method, body)

redirectable_request = redirectable(request, redirects=(
    # Omit codes to not follow redirect
    (b'301', unchanged if method in (b'GET', b'HEAD') else get),
    (b'302', unchanged if method in (b'GET', b'HEAD') else get),
    (b'303', unchanged if method in (b'GET', b'HEAD') else get),
    (b'307', unchanged),
    (b'308', unchanged),
))
```


## Authorization header

By default, the Authorization header is not passed to if redirected to another domain. This can be customised. As an example, to recreate the default behaviour explicitly, the below code can be used.

```python
def strip_authorization_if_different_host(request_url, request_headers, redirect_url, redirect_headers):
    host_request = urllib.parse.urlsplit(request_url).hostname
    host_redirect = urllib.parse.urlsplit(redirect_url).hostname
    forbidden = \
        (b'authorization',) if host_request != host_redirect else \
        ()
    return tuple(
        (key, value)
        for key, value in request_headers if key.lower() in forbidden
    )

redirectable_request = redirectable(request, headers=strip_authorization_if_different_host)
```
