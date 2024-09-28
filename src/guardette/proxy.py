import functools
import logging
from secrets import compare_digest

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.datastructures import URL, MutableHeaders

from guardette import config
from guardette.actions import ActionContext, action_registry
from guardette.auth import AuthHandlerRegistry, auth_registry
from guardette.datastructures import ProxyRequest, ProxyResponse
from guardette.exceptions import (
    AuthException,
    ConfigurationException,
    GuardetteException,
    HttpMethodNotSupportedException,
    MatchNotFoundException,
    TransformationException,
)
from guardette.matching import Matcher, SourceMatcherResult
from guardette.policy import load_policy
from guardette.secrets import (
    AwsSecretsManager,
    ConfigSecretsManager,
    SecretManagerType,
    SecretsManager,
)
from guardette.utils import copy_signature
from guardette.version import VERSION

PROXY_HOST_HEADER = "X-Guardette-Host"

PROXY_ERROR_HEADER = "X-Guardette-Error"

STRIP_REQUEST_HEADERS = {
    PROXY_HOST_HEADER.lower(),
    "authorization",
    "host",
    "connection",
    "content-length",
    "transfer-encoding",
}

STRIP_RESPONSE_HEADERS = {
    "connection",
    "content-length",
    "content-encoding",
    "transfer-encoding",
}


logger = logging.getLogger(__name__)


def guardette_route():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException as http_exc:
                # Propagate HTTPExceptions (from proxied source) as-is
                raise http_exc
            except GuardetteException as ge:
                # Handle known internal proxy exceptions
                logger.exception(f"GuardetteException: {ge!s}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": {
                            "message": "Internal Server Error",
                            "source": "proxy",
                            "details": str(ge),
                        },
                    },
                    headers={PROXY_ERROR_HEADER: "proxy"},
                )
            except Exception:
                # Handle unexpected internal errors
                logger.exception("Unexpected error occurred:")
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": {
                            "message": "Internal Server Error",
                            "source": "proxy",
                            "details": "An unexpected error occurred.",
                        },
                    },
                    headers={PROXY_ERROR_HEADER: "proxy"},
                )
        return wrapped
    return wrapper


class Guardette:
    def __init__(self, policy_path=".guardette/policy.yml"):
        self.actions = action_registry
        self.auth = auth_registry
        self.policy = load_policy(policy_path)
        self.config = config.ConfigManager()

        conf_secret_manager = self.config.get(config.SECRET_MANAGER) or "default"
        if conf_secret_manager == SecretManagerType.DEFAULT:
            self.secrets: SecretsManager = ConfigSecretsManager(self.config)
        elif conf_secret_manager == SecretManagerType.AWS_SECRET_MANAGER:
            self.secrets: SecretsManager = AwsSecretsManager(self.config)
        else:
            raise ConfigurationException("Invalid secret manager option: " + conf_secret_manager)

    @property
    def policy(self):
        return self._policy

    @policy.setter
    def policy(self, value):
        self._policy = value
        self._matcher = Matcher(self._policy)

    @property
    def matcher(self):
        return self._matcher

    @guardette_route()
    async def _meta_route(self):
        return {
            "version": VERSION,
        }

    @guardette_route()
    async def _proxy_route(self, path: str, request: Request):
        req_client_secret = request.headers.get("authorization")
        if not req_client_secret:
            raise AuthException("Missing authorization header.")

        client_secret = await self.secrets.get(config.CLIENT_SECRET)

        if not compare_digest(req_client_secret, client_secret):
            raise AuthException("Invalid authorization header.")

        target_host = request.headers.get(PROXY_HOST_HEADER)
        if not target_host:
            raise GuardetteException(f"{PROXY_HOST_HEADER} header is missing.")

        match = self.matcher.match(request, target_host=target_host)
        if match is None:
            raise MatchNotFoundException("Match not found.")

        proxy_transformer = ProxyTransformer(
            auth=self.auth, config=self.config, secrets=self.secrets, match=match,
        )
        try:
            proxy_request = await proxy_transformer.transform_request(request)
        except Exception as e:
            raise TransformationException(f"Error transforming request: {e!s}") from e

        async with httpx.AsyncClient() as client:
            if request.method == "GET":
                response = await client.get(
                    proxy_request.url, headers=proxy_request.headers,
                )
            elif request.method == "POST":
                response = await client.post(
                    proxy_request.url,
                    headers=proxy_request.headers,
                    data=proxy_request.json_data,
                )
            elif request.method == "PUT":
                response = await client.put(
                    proxy_request.url,
                    headers=proxy_request.headers,
                    data=proxy_request.json_data,
                )
            elif request.method == "PATCH":
                response = await client.patch(
                    proxy_request.url,
                    headers=proxy_request.headers,
                    data=proxy_request.json_data,
                )
            elif request.method == "DELETE":
                response = await client.delete(
                    proxy_request.url, headers=proxy_request.headers,
                )
            elif request.method == "HEAD":
                response = await client.head(
                    proxy_request.url, headers=proxy_request.headers,
                )
            elif request.method == "OPTIONS":
                response = await client.options(
                    proxy_request.url, headers=proxy_request.headers,
                )
            else:
                raise HttpMethodNotSupportedException(f"Unexpected http method: {request.method}")

        try:
            proxy_response = await proxy_transformer.transform_response(response)
        except Exception as e:
            raise TransformationException(f"Error transforming response: {e!s}") from e

        return JSONResponse(
            content=proxy_response.json_data,
            status_code=proxy_response.status_code,
            headers=dict(proxy_response.headers),
        )

    @copy_signature(action_registry.register)
    def action(self, *args, **kwargs):
        return self.actions.register(*args, **kwargs)

    @copy_signature(auth_registry.register)
    def auth_handler(self, *args, **kwargs):
        return self.auth.register(*args, **kwargs)

    def to_fastapi(self, app: FastAPI):
        app.api_route("/_guardette/meta", methods=["GET"])(self._meta_route)
        app.api_route(
            "/{path:path}",
            methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"],
        )(self._proxy_route)


class ProxyTransformer:
    def __init__(
        self,
        *,
        auth: AuthHandlerRegistry,
        config: config.ConfigManager,
        secrets: SecretsManager,
        match: SourceMatcherResult,
    ):
        self.auth = auth
        self.config = config
        self.secrets = secrets
        self.target = match["target"]
        self.rule = match["rule"]
        self.path_params = match["path_params"]
        self._proxy_request: ProxyRequest | None = None

    async def transform_request(self, in_request: Request) -> ProxyRequest:
        url = str(
            URL(
                scheme="https",
                hostname=self.target.host,  # Your new hostname
                path=in_request.url.path,
                query=in_request.url.query,
                fragment=in_request.url.fragment,
            ),
        )

        headers = MutableHeaders(
            {
                k: v
                for k, v in in_request.headers.items()
                if k.lower() not in STRIP_REQUEST_HEADERS
            },
        )
        body = await in_request.body()
        if body:
            json_data = await in_request.json()
        else:
            json_data = None

        self._proxy_request = ProxyRequest(
            url=url, headers=headers, json_data=json_data,
        )
        if self.target.auth:
            await self.auth(
                self.target.auth,
                request=self._proxy_request,
                secrets=self.secrets,
                config=self.config,
            )

        ctx = ActionContext(
            config=self.config,
            secrets=self.secrets,
            request=self._proxy_request,
            response=ProxyResponse(
                status_code=0, headers=MutableHeaders(), json_data=None,
            ),
        )
        for action in self.rule.actions:
            await action.request(ctx)
        return self._proxy_request

    async def transform_response(self, in_response: httpx.Response) -> ProxyResponse:
        if self._proxy_request is None:
            raise Exception(
                "Cannot call transform_response() without first "
                "calling transform_request()",
            )
        status_code = in_response.status_code
        headers = MutableHeaders(
            {
                k: v
                for k, v in in_response.headers.items()
                if k.lower() not in STRIP_RESPONSE_HEADERS
            },
        )
        json_data = in_response.json()
        ctx = ActionContext(
            config=self.config,
            secrets=self.secrets,
            request=self._proxy_request,
            response=ProxyResponse(
                status_code=status_code, headers=headers, json_data=json_data,
            ),
        )
        for action in self.rule.actions:
            await action.response(ctx)
        return ctx.response
