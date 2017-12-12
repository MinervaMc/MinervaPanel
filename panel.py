#!/usr/bin/env python3
# -*- encoding: utf8

from flask import Flask, render_template, redirect, abort
import re
import subprocess
from typing import Any, Dict, List, NamedTuple

import secrets

app = Flask(__name__)
DEBUG = True

Server = NamedTuple('Server', [("name", str), ("online", bool)])

SERVERLIST_REGEX = re.compile(r"\[ (?:IN)?ACTIVE \] \"([^\"]+)\" is (running|stopped).")


def getServers() -> Dict[str, Server]:
    if DEBUG:
        return {"creative2": Server("creative2", True),
                "minerva": Server("minerva", True),
                "anarchy": Server("anarchy", False),
                "creative": Server("creative", True),
                "patreon": Server("patreon", False)
                }
    msm = subprocess.run(["msm", "server", "list"], stdout=subprocess.PIPE, check=True)
    output = msm.stdout.decode("utf-8")  # type: str
    ret = {}
    for line in output.splitlines():
        m = SERVERLIST_REGEX.match(line)
        if m is not None:
            ret[m.group(1)] = Server(m.group(1), m.group(2) == "running")
    return ret


def getWorldList(server: str) -> List[str]:
    if DEBUG:
        return ["world", "Other", "worlds", "show", "here"]
    msm = subprocess.run(["msm", server, "worlds", "list"], stdout=subprocess.PIPE, check=True)
    output = msm.stdout.decode("utf-8")  # type: str
    return output.splitlines()


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


# TODO: Run start/restart/stop in the background and give user feedback
@app.route("/<server>/stop")
def stop(server: str) -> Any:
    subprocess.run(["msm", server, "stop"])
    return redirect("/" + server)


@app.route("/<server>/restart")
def restart(server: str) -> Any:
    subprocess.run(["msm", server, "restart"])
    return redirect("/" + server)


@app.route("/<server>/start")
def start(server: str) -> Any:
    subprocess.run(["msm", server, "start"])
    return redirect("/" + server)


app.secret_key = secrets.secret_key
