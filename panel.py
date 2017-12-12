#!/usr/bin/env python3
# -*- encoding: utf8

from flask import Flask, render_template, redirect, abort
from typing import Any, Dict, List, NamedTuple

app = Flask(__name__)
DEBUG = True


Server = NamedTuple('Server', [("name", str), ("online", bool)])


def getServers() -> Dict[str, Server]:
    if DEBUG:
        return {"creative2": Server("creative2", True),
                "minerva": Server("minerva", True),
                "anarchy": Server("anarchy", False),
                "creative": Server("creative", True),
                "patreon": Server("patreon", False)
                }
    return {}


def getWorldList(server: str) -> List[str]:
    if DEBUG:
        return ["world", "Other", "worlds", "show", "here"]
    return []


def getJarList() -> List[str]:
    if DEBUG:
        return ["minecraft/2017-09-10-01-26-11-minecraft_server.1.12.1.jar",
                "minecraft/2017-09-22-16-53-04-minecraft_server.1.12.2.jar",
                "minerva/minerva.jar",
                "minukkit/craftbukkit-1.12.jar"
                ]
    return []


@app.route("/")
def root() -> Any:
    servers = getServers()
    if len(servers) == 0:
        return "No servers? :("
    return redirect("/" + list(servers)[0])


@app.route("/<server>/")
def server(server: str) -> Any:
    servers = getServers()
    if server not in servers:
        return abort(404)

    worlds = getWorldList(server)
    jars = getJarList()

    serverInfo = {"jar": "minerva/minerva.jar",
                  "world": "world",
                  "name": server,
                  "ram": 3072,
                  "port": 65535,
                  }

    return render_template("server.html", serverInfo=serverInfo,
                           servers=servers.values(), worlds=worlds, jars=jars)
