#!/usr/bin/env python3
# -*- encoding: utf8

from flask import Flask, render_template, redirect, abort
from typing import Any, List

app = Flask(__name__)
DEBUG = True


def getServerList() -> List[str]:
    if DEBUG:
        return ["creative2", "minerva", "anarchy", "creative", "patreon"]
    return []


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
    servers = getServerList()
    if len(servers) == 0:
        return "No servers? :("
    return redirect("/" + servers[0])


@app.route("/<server>/")
def server(server: str) -> Any:
    servers = getServerList()
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
                           servers=servers, worlds=worlds, jars=jars)
