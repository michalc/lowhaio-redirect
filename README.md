# lowhaio-redirect [![CircleCI](https://circleci.com/gh/michalc/lowhaio-redirect.svg?style=svg)](https://circleci.com/gh/michalc/lowhaio-redirect)

Wrapper of lowhaio that follows HTTP redirects


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

The default behavior is as below.

- 301, 302 redirects from a POST are converted to GETs with empty bodies; all other requests do not change methods and bodies.

- 303 redirects, all non HEAD and GET requests are converted to GETs with empty bodies.

- 307 and 308 redirects, the method and bodies are always unchanged.

Note however, that an unchanged body is actually _not_ guaranteed by this wrapper. For each request the function passed as the `body` argument is called, and it may return different things on each call. It is up the the developer to handle this case as needed: there is no one-size-fits all approach, since for streaming requests, the body may not be available again. In many cases, a redirect that expects a resubmission of a large upload may be an error; or if an API is never expected to return a redirect, _not_ using this wrapper at all may be a viable option, and instead a few lines of code that raises an exception if a redirect is returned from the server.


## Customise redirects

It is possible to customise which redirects are followed, and how they affect the method and body. As an example, to recreate the default behaviour explicitly, the below code could be used.

```python
def get(method, body, body_args, body_kwargs, headers):
    # Asynchronous generator that end immediately, and results in an empty body
    async def empty_body():
        while False:
            yield
    next_request_headers = tuple(
        (key, value)
        for key, value in headers if key.lower() not in (b'content-length', b'transfer-encoding')
    )

    return (b'GET', empty_body, (), (), next_request_headers)


def unchanged(method, body, body_args, body_kwargs, headers):
    return (method, body, body_args, body_kwargs, headers)


redirectable_request = redirectable(request, redirects=(
    (b'301', lambda method: unchanged if method != b'POST' else get),
    (b'302', lambda method: unchanged if method != b'POST' else get),
    (b'303', lambda method: unchanged if method in (b'GET', b'HEAD') else get),
    (b'307', lambda method: unchanged),
    (b'308', lambda method: unchanged),
))
```


## Authorization header

By default, the Authorization header is not passed to if redirected to another domain. This can be customised. As an example, to recreate the default behaviour explicitly, the below code can be used.

```python
def strip_authorization_if_different_host(request_headers, request_host, redirect_host):
    forbidden = \
        (b'authorization',) if request_host != redirect_host else \
        ()
    return tuple(
        (key, value)
        for key, value in request_headers if key.lower() not in forbidden
    )

redirectable_request = redirectable(request, transform_headers=strip_authorization_if_different_host)
```
