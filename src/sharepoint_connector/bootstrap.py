"""Lazy composition root: shared auth, Graph adapter and file service."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import httpx
from m365_auth import Account, AccountBoundTokenSource, AuthenticationRequired, TokenProvider

from sharepoint_connector import config
from sharepoint_connector.remote.graph import Graph
from sharepoint_connector.service.files import Files


@dataclass
class Services:
    account: Account
    files: Files


class AppContext:
    def __init__(
        self,
        *,
        tokens: TokenProvider | None = None,
        http_client: httpx.AsyncClient | None = None,
        output_home: Path | None = None,
    ) -> None:
        self.tokens = tokens or TokenProvider(login_command=f"{config.CLI_NAME} auth")
        self._http_client = http_client
        self._owns_http_client = http_client is None
        self._output_home = output_home
        self._services: Services | None = None
        self._lock = asyncio.Lock()

    async def services(self) -> Services:
        account = self._current_account()
        if self._services is not None and self._services.account.fingerprint == account.fingerprint:
            return self._services
        async with self._lock:
            account = self._current_account()
            if self._services is None or self._services.account.fingerprint != account.fingerprint:
                self._services = self._build(account)
        return self._services

    def _current_account(self) -> Account:
        claims = self.tokens.get_token(config.GRAPH_PROFILE).claims()
        if not claims.get("tid") or not claims.get("oid"):
            raise AuthenticationRequired(
                "The Microsoft Graph token carries no account identity.",
                command=f"{config.CLI_NAME} auth",
            )
        return Account(
            tenant_id=str(claims["tid"]),
            object_id=str(claims["oid"]),
            username=claims.get("upn") or claims.get("preferred_username"),
        )

    def _build(self, account: Account) -> Services:
        account_tokens = AccountBoundTokenSource(self.tokens, account)
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0, connect=15.0), follow_redirects=False
            )
        graph = Graph(
            account_tokens,
            client=self._http_client,
            expected_account_fingerprint=account.fingerprint,
        )
        return Services(
            account=account,
            files=Files(
                graph,
                output_home=self._output_home,
                account_fingerprint=account.fingerprint,
            ),
        )

    async def aclose(self) -> None:
        if self._http_client is not None and self._owns_http_client:
            await self._http_client.aclose()
