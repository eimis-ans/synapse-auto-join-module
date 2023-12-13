import base64
import datetime
import json
import logging
from typing import Any, Dict, Optional, Set
from urllib.parse import parse_qs, urlparse

import attr
import requests
from synapse.api.errors import SynapseError
from synapse.logging.context import make_deferred_yieldable
from synapse.module_api import ModuleApi, run_as_background_process
from synapse.util import json_decoder
from twisted.internet import defer
from twisted.internet.defer import inlineCallbacks
from twisted.web import http
from twisted.web.client import readBody
from twisted.web.http import NO_CONTENT, OK
from twisted.web.server import NOT_DONE_YET, Request

logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, frozen=True)
class EimisDirectoryConfig:
    grist_url: Optional[str] = None
    grist_api_key: Optional[str] = None


class EimisProfile:
    nom: str
    prenom: str
    numeroPsc: str
    mxids: Set[str]

    def __init__(self, nom, prenom, numeroPsc, fonction, mxids):
        self.nom = nom
        self.prenom = prenom
        self.numeroPsc = numeroPsc
        self.fonction = fonction
        self.mxids = mxids.split(", ")

    def toJSON(self):
        return {
            "nom": self.nom,
            "prenom": self.prenom,
            "numeroPsc": self.numeroPsc,
            "mxids": self.mxids
        }

    def __str__(self):
        return f'EimisProfile({self.numeroPsc}, {self.nom}, {self.prenom}, {", ".join(self.mxids)})'


class EimisDirectory:
    def __init__(self, config: EimisDirectoryConfig, api: ModuleApi, store=None):
        self._api = api
        self._config = config
        self._directory = []
        api.register_web_resource("/_synapse/client/eimis-directory/req",
                                  EimisDirectoryServerQueryResource(self._directory))

        api.register_web_resource("/_synapse/client/eimis-directory/dump",
                                  EimisDirectoryServerDumpResource(self._directory))

        run_as_background_process(
            "init_directory",
            self._init_directory,
        )

    async def _init_directory(self):
        logging.info("EIMIS EimisDirectory init " + self._config.grist_url)
        response = await self._api.http_client.request("GET", self._config.grist_url)
        if response.code == 200:
            resp_body = await make_deferred_yieldable(readBody(response))
            js_directory = json_decoder.decode(resp_body.decode("utf-8"))

            if not isinstance(js_directory["records"], list):
                raise SynapseError(500, "Eimis user result is not a list")

            for entry in js_directory["records"]:
                fields = entry["fields"]
                profile = EimisProfile(
                    fields["Nom"], fields["Prenom"], fields["NumeroPsc"], fields["fonction"], fields["mxids"])
                self._directory.append(profile)
        else:
            raise SynapseError(500, "Eimis error when calling user direcotry")

        logger.info("EIMIS Data loaded")

    @staticmethod
    def parse_config(config: Dict[str, Any]) -> EimisDirectoryConfig:
        return EimisDirectoryConfig(
            grist_url=config.get("grist_url", None)
        )


class EimisDirectoryServerQueryResource:
    # This flag helps Twisted identify this as a final resource and not look for children.
    isLeaf = True

    def __init__(self, dictionary):
        # Logging for debug purposes
        logger.info(f"EIMIS EimisDirectoryServerQueryResource init")
        self.dictionary = dictionary

    # Handle incoming HTTP requests to the registered endpoint.
    def render(self, request: Request):
        logging.info("EIMIS render directory module")

        request.setHeader(b"content-type", b"application/json; charset=utf-8")
        request.setHeader(b"Access-Control-Allow-Origin", b"*")

        parsed = urlparse(request.uri)

        if not parsed.query:
            request.setResponseCode(http.BAD_REQUEST)
            return b''

        queriesBt = parse_qs(parsed.query)

        if not queriesBt[b"mxid"]:
            request.setResponseCode(http.BAD_REQUEST)
            return b''

        logging.info(queriesBt[b"mxid"])
        if not queriesBt[b"mxid"] and not queriesBt[b"mxid"][0]:
            request.setResponseCode(http.BAD_REQUEST)
            return b''

        mxid = queriesBt[b"mxid"][0].decode("utf-8")

        # TODO check mxid with some synapse validator
        if (not mxid.startswith("@")) or (not ":" in mxid):
            request.setResponseCode(http.BAD_REQUEST)
            return b'nul'

        for profile in self.dictionary:
            if mxid in str(profile.mxids):
                res = profile.mxids.copy()
                res.remove(mxid)
                request.setResponseCode(http.OK)
                return str.encode(json.dumps(res))

        logging.info(f"Didn't find : {mxid}")
        request.setResponseCode(http.OK)

        return str.encode(json.dumps([]))

    @inlineCallbacks
    def on_PUT(self, request):
        return self.method_not_allowed(request)

    def on_GET(self, request):
        logger.info(str(request))
        return self.method_not_allowed(request)

    def on_POST(self, request):
        return self.method_not_allowed(request)

    # General method to respond with "Method Not Allowed" for disallowed or unrecognized HTTP methods.
    def method_not_allowed(self, request):
        logger.warning(
            f"Method Not Allowed: {request.method.decode('ascii')} from {request.getClientIP()}.")
        request.setResponseCode(405)
        return json.dumps({"error": "Method Not Allowed"}).encode("utf-8")


class EimisDirectoryServerDumpResource:
    # This flag helps Twisted identify this as a final resource and not look for children.
    isLeaf = True

    def __init__(self, dictionary):
        # Logging for debug purposes
        logger.info(f"EIMIS EimisDirectoryServerDumpResource init")
        self.dictionary = dictionary

    # Handle incoming HTTP requests to the registered endpoint.
    def render(self, request: Request):
        logging.info("EIMIS render dump directory module")

        request.setHeader(b"content-type", b"application/json; charset=utf-8")
        request.setHeader(b"Access-Control-Allow-Origin", b"*")

        request.setResponseCode(http.OK)

        result = [u.toJSON() for u in self.dictionary]
        return str.encode(f"{json.dumps(result)}")

    @inlineCallbacks
    def on_PUT(self, request):
        return self.method_not_allowed(request)

    def on_GET(self, request):
        logger.info(str(request))
        return self.method_not_allowed(request)

    def on_POST(self, request):
        return self.method_not_allowed(request)

    # General method to respond with "Method Not Allowed" for disallowed or unrecognized HTTP methods.
    def method_not_allowed(self, request):
        logger.warning(
            f"Method Not Allowed: {request.method.decode('ascii')} from {request.getClientIP()}.")
        request.setResponseCode(405)
        return json.dumps({"error": "Method Not Allowed"}).encode("utf-8")
