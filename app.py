from datetime import datetime
from threading import Thread

import psycopg2.errors
from flask import Flask, abort, jsonify, render_template, request
from pytz import timezone

from database_operations import auto_complete, auto_fill_from_mangadex, get_all, get_data, refresh_all, \
    refresh_manga_data, update_data, updated_count

app = Flask(__name__)


@app.before_request
def determine_valid_ip():
    if request.headers.get("X-Forwarded-For", "127.0.0.1") not in ["24.102.65.225", "127.0.0.1"]:
        return abort(403)


def prep_data(data):
    return [(manga_id, title, cover_url, read, total, completed, user_completed, hidden) if len(title) <= 100
            else (manga_id, title[:100] + "...", cover_url, read, total, completed, user_completed, hidden)
            for manga_id, title, cover_url, read, total, completed, user_completed, hidden in data]


@app.route('/')
def home():
    data = get_all(order="read / cast(total as decimal)", direction="asc")
    data = prep_data(data)
    return render_template("home.html", data=data, home=True)


@app.context_processor
def load_builtins():
    return {key: value for key, value in __builtins__.items() if not key.startswith("_")}


@app.route("/format_log_entry", methods=["POST"])
def format_log_entry():
    data = {
        "content": request.form.get("content", None),
        "tr_id": request.form.get("tr_id", None),
        "tr_class": request.form.get("tr_class", "text-primary border-bottom border-primary"),
        "tr_style": request.form.get("tr_style", None),
        "tr_attributes": request.form.get("tr_attributes", None),
        'timestamp': request.form.get("timestamp",
                                      timezone("America/New_York").fromutc(datetime.utcnow()).strftime("%I:%M:%S %p"))
    }
    return render_template("log-entry.html", **data)


@app.route("/update/<int:manga_id>", methods=["POST"])
def update(manga_id):
    refresh_data = request.form.get("refresh_data", None)
    read: str = request.form.get("read", None)
    if read is None and refresh_data is None:
        abort(400)
    if refresh_data is not None:
        refresh_manga_data(manga_id)
    if read is not None:
        if not read.isnumeric():
            abort(400)
        read_int = int(read)
        try:
            title, cover_url, read_int, total, completed, user_completed, hidden = update_data(manga_id, read=read_int)
        except psycopg2.errors.CheckViolation:
            abort(400)
        else:
            return render_template("progress-bar.html", read=read_int, total=total, completed=completed)


@app.route("/update/one/<sign>/<int:manga_id>", methods=["POST"])
def one(sign, manga_id):
    read, = get_data(manga_id, parameters=["read"])
    if sign == "+":
        read += 1
    elif sign == "-":
        read -= 1
    else:
        abort(400)
    try:
        title, cover_url, read, total, completed, user_completed, hidden = update_data(manga_id, read=read)
    except psycopg2.errors.CheckViolation:
        abort(400)
    else:
        return jsonify({"html": render_template("progress-bar.html", read=read, total=total, completed=completed),
                        "read": read})


def complete_base(manga_id, user_completed):
    update_data(manga_id, user_completed=user_completed)
    return render_template("complete-button.html", user_completed=user_completed)


def hide_base(manga_id, hidden):
    update_data(manga_id, hidden=hidden)
    return render_template("hide-button.html", hidden=hidden)


@app.route("/uncomplete/<int:manga_id>")
def uncomplete(manga_id):
    return complete_base(manga_id, False)


@app.route("/complete/<int:manga_id>")
def complete(manga_id):
    return complete_base(manga_id, True)


@app.route("/update_status", methods=["GET"])
def update_status():
    updated, total = updated_count()
    if updated == total:
        return jsonify({"updated": updated, "total": total}), 500
    return jsonify({"updated": updated, "total": total}), 200


@app.route("/update_all")
def update_all():
    Thread(target=refresh_all).start()
    return "", 206


@app.route("/<int:manga_id>")
def single(manga_id: int):
    data = (manga_id, *get_data(manga_id))
    return render_template("home.html", data=data)


@app.route("/incomplete")
def incomplete():
    data = get_all(order="read / cast(total as decimal)", direction="asc", where="USER_COMPLETED = FALSE")
    data = prep_data(data)
    return render_template("home.html", data=data, incomplete=incomplete)


@app.route("/to_read")
def to_read():
    data = get_all(order="read / cast(total as decimal)", direction="asc",
                   where="(read / cast(total as decimal)) < ""1.0")
    data = prep_data(data)
    return render_template("home.html", data=data, to_read=to_read)


@app.route("/auto_complete")
def auto_complete_endpoint():
    auto_complete()
    return "", 206


@app.route("/update/fill/<int:manga_id>", methods=["POST"])
def fill(manga_id):
    total, = get_data(manga_id, parameters=["total"])
    title, cover_url, read, total, completed, user_completed, hidden = update_data(manga_id, read=total)
    return jsonify({"html": render_template("progress-bar.html", read=read, total=total, completed=completed),
                    "read": total})


@app.route("/hidden")
def hidden_data():
    data = get_all(order="read / cast(total as decimal)", direction="asc", hidden=True)
    data = prep_data(data)
    return render_template("home.html", data=data, hidden=True)


@app.route("/hide/<int:manga_id>")
def hide(manga_id):
    return hide_base(manga_id, True)


@app.route("/unhide/<int:manga_id>")
def unhide(manga_id):
    return hide_base(manga_id, False)


@app.route("/all")
def all_items():
    data = get_all(order="read / cast(total as decimal)", direction="asc", hidden=None)
    data = prep_data(data)
    return render_template("home.html", data=data, all_page=True)


@app.route("/update_from_mangadex")
def update_from_mangadex():
    auto_fill_from_mangadex()
    return "", 206


if __name__ == '__main__':
    app.run()
