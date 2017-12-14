#!/usr/bin/env python3
# -*- encoding: utf8

from flask import Flask, render_template, redirect, abort, session, request, url_for
import flask
import functools
import hashlib
import os
import re
import subprocess
import sqlite3
from typing import Any, Dict, List, NamedTuple, Optional  # noqa

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
    jardir = getMSMConfig()["JAR_STORAGE_PATH"]
    ret = []
    for (dirpath, dirs, files) in os.walk(jardir):
        if not dirpath.startswith(jardir + "/"):
            continue
        path = dirpath[len(jardir)+1:]
        for fil in files:
            if fil.endswith(".jar"):
                ret.append(path + "/" + fil)
    return ret


def getMSMConfig() -> Dict[str, str]:
    msm = subprocess.run(["msm", "config"], stdout=subprocess.PIPE, check=True)
    output = msm.stdout.decode("utf-8")  # type: str
    ret = {}
    for line in output.splitlines():
        split = line.split("=")
        if len(split) == 2:
            ret[split[0]] = split[1][1:-1]
    return ret


def login_required(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        if "username" not in session or session["username"] is None:
            session["next"] = request.url
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return inner


def get_db() -> sqlite3.Connection:
    db = getattr(flask.g, "database", None)  # type: Optional[sqlite3.Connection]
    if db is None:
        db = sqlite3.connect("panel.db")
        flask.g.database = db
    return db


@app.teardown_appcontext
def close_db(exception) -> None:
    db = getattr(flask.g, "database", None)  # type: Optional[sqlite3.Connection]
    if db is not None:
        db.close()


def with_db(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        db = get_db()
        ret = f(db, *args, **kwargs)
        db.commit()
        return ret
    return inner


@app.route("/")
def root() -> Any:
    servers = getServers()
    if len(servers) == 0:
        return "No servers? :("
    return redirect("/server/" + list(servers)[0])


@app.route("/login/", methods=["GET", "POST"])
@with_db
def login(db: sqlite3.Connection) -> Any:
    if request.method == "POST":
        if valid_credentials(request.form["username"], request.form["password"]):
            session["username"] = request.form["username"]
            if "next" in session and session["next"] is not None:
                next = session["next"]
                del session["next"]
                return redirect(next)
            return redirect("/")
        return redirect("/login")
    elif request.method == "GET":
        return render_template("login.html")


@app.route("/logout")
def logout() -> Any:
    del session["username"]
    return ""


@app.route("/server/<server>/")
@login_required
def server(server: str) -> Any:
    servers = getServers()
    if server not in servers:
        return abort(404)

    worlds = getWorldList(server)
    jars = getJarList()

    serverInfo = {"jar": "-",
                  "world": "-",
                  "name": server,
                  "ram": "-",
                  "port": "-",
                  }

    return render_template("server.html", serverInfo=serverInfo,
                           servers=servers.values(), worlds=worlds, jars=jars)


@app.route("/admins/")
@login_required
@with_db
def admins(db: sqlite3.Connection) -> Any:
    c = db.cursor()
    c.execute("SELECT username FROM user")
    users = [row[0] for row in c.fetchall()]
    return render_template("admins.html", users=users, servers=getServers().values())


@app.route("/admins/<user>/", methods=["GET", "POST"])
@login_required
@with_db
def user(db: sqlite3.Connection, user: str) -> Any:
    if request.method == "GET":
        return render_template("user.html", user=user, servers=getServers().values())
    elif request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        c = db.cursor()
        if username != user:
            c.execute("UPDATE user SET username = ? WHERE username=?", (username, user))
            user = username

        if password != "":
            salt = os.urandom(8)
            hasher = hashlib.sha256()
            hasher.update(salt)
            hasher.update(password.encode("utf-8"))
            hashed = hasher.hexdigest()
            c.execute("UPDATE user SET password = ?, salt = ? WHERE username=?", (hashed, salt, user))
        return redirect(url_for('admins'))
    return abort(400)


@app.route("/admins/<user>/delete")
@with_db
def delete_user(db: sqlite3.Connection, user: str) -> Any:
    c = db.cursor()
    c.execute("DELETE FROM user WHERE username=?", (user,))
    return redirect(url_for("admins"))


@app.route("/newadmin", methods=["GET", "POST"])
@with_db
def new_user(db: sqlite3.Connection):
    if request.method == "GET":
        return render_template("user.html", user="")
    elif request.method == "POST":
        user = request.form["username"]
        password = request.form["password"]

        salt = os.urandom(8)
        hasher = hashlib.sha256()
        hasher.update(salt)
        hasher.update(password.encode("utf-8"))
        hashed = hasher.hexdigest()

        c = db.cursor()
        c.execute("INSERT INTO user (username, password, salt) VALUES (?, ?, ?)", (user, hashed, salt))
        return redirect(url_for("admins"))
    return abort(400)


@with_db
def valid_credentials(db: sqlite3.Connection, username: str, password: str) -> bool:
    c = db.cursor()
    c.execute("SELECT password, salt FROM user WHERE username=?", (username,))
    user = c.fetchone()
    if user is None:
        return False
    hasher = hashlib.sha256()
    hasher.update(user[1])
    hasher.update(password.encode("utf-8"))
    hashed = hasher.hexdigest()
    return user[0] == hashed


# TODO: Run start/restart/stop in the background and give user feedback
@app.route("/server/<server>/stop")
@login_required
def stop(server: str) -> Any:
    subprocess.run(["msm", server, "stop"])
    return redirect("/" + server)


@app.route("/server/<server>/restart")
@login_required
def restart(server: str) -> Any:
    subprocess.run(["msm", server, "restart"])
    return redirect("/" + server)


@app.route("/server/<server>/start")
@login_required
def start(server: str) -> Any:
    subprocess.run(["msm", server, "start"])
    return redirect("/" + server)


@app.before_first_request
@with_db
def init_db(db: sqlite3.Connection) -> None:
    c = db.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS user (username TEXT, password TEXT, salt TEXT)")


class ReverseProxyMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get("HTTP_X_SCRIPT_NAME", "")
        if script_name:
            environ["SCRIPT_NAME"] = script_name
            path_info = environ["PATH_INFO"]
            if path_info.startswith(script_name):
                environ["PATH_INFO"] = path_info[len(script_name):]

        scheme = environ.get("HTTP_X_SCHEME", "")
        if scheme:
            environ["wsgi.url_scheme"] = scheme

        server = environ.get('HTTP_X_FORWARDED_SERVER', '')
        if server:
            environ['HTTP_HOST'] = server
        return self.app(environ, start_response)


app.secret_key = secrets.secret_key

if __name__ == "__main__":
    app.wsgi_app = ReverseProxyMiddleware(app.wsgi_app)
    app.run(port=15000)
