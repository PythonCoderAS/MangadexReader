from flask import Flask, abort, jsonify, render_template, render_template_string, request

from database_operations import auto_complete, get_all, get_data, refresh_all, refresh_manga_data, update_data, \
    updated_count

from threading import Thread

app = Flask(__name__)


@app.before_request
def determine_valid_ip():
    if request.headers.get("X-Forwarded-For", "127.0.0.1") not in ["24.102.65.225", "127.0.0.1"]:
        return abort(403)


def prep_data(data):
    return [(manga_id, title, cover_url, read, total, completed, user_completed) if len(title) <= 100
            else (manga_id, title[:100] + "...", cover_url, read, total, completed, user_completed)
            for manga_id, title, cover_url, read, total, completed, user_completed in data]


@app.route('/')
def home():
    data = get_all(order="read / cast(total as decimal)", direction="asc")
    data = prep_data(data)
    return render_template("home.html", data=data, home=home)


@app.context_processor
def load_builtins():
    return {key: value for key, value in __builtins__.items() if not key.startswith("_")}


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
        title, cover_url, read_int, total, completed, user_completed = update_data(manga_id, read=read_int)
        return render_template_string("""<div class="progress">
                    <div class="progress-bar" style="width: {{ read/total * 100|int }}%;background-color: {% if
                    completed %}#00AAFF{% else %}#00FF66{% endif %};"
                         aria-valuemin="0"
                         aria-valuemax="{{ total }}" aria-valuenow="{{ read }}">{{ read }} / {{ total }}</div>
                </div>""",
                                      title=title, cover_url=cover_url, read=read_int, total=total, completed=completed,
                                      user_completed=user_completed)


@app.route("/update/one/<int:manga_id>", methods=["POST"])
def add_one(manga_id):
    read, = get_data(manga_id, parameters=["read"])
    read += 1
    title, cover_url, read, total, completed, user_completed = update_data(manga_id, read=read)
    return render_template_string("""<div class="progress">
                        <div class="progress-bar" style="width: {{ read/total * 100|int }}%;background-color: {% if
                        completed %}#00AAFF{% else %}#00FF66{% endif %};"
                             aria-valuemin="0"
                             aria-valuemax="{{ total }}" aria-valuenow="{{ read }}">{{ read }} / {{ total }}</div>
                    </div>""",
                                  title=title, cover_url=cover_url, read=read, total=total, completed=completed,
                                  user_completed=user_completed)


def complete_base(manga_id, user_completed):
    update_data(manga_id, user_completed=user_completed)
    return render_template_string("""<button class="btn btn-outline-primary {% if user_completed %}active{% endif %}"
                            onclick="{% if user_completed %}un{% endif %}complete(this);">Complete{% if
                    user_completed %}d{% endif %}</button>""", user_completed=user_completed)


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
    title, cover_url, read, total, completed, user_completed = update_data(manga_id, read=total)
    return render_template_string("""<div class="progress">
                        <div class="progress-bar" style="width: {{ read/total * 100|int }}%;background-color: {% if
                        completed %}#00AAFF{% else %}#00FF66{% endif %};"
                             aria-valuemin="0"
                             aria-valuemax="{{ total }}" aria-valuenow="{{ read }}">{{ read }} / {{ total }}</div>
                    </div>""",
                                  title=title, cover_url=cover_url, read=read, total=total, completed=completed,
                                  user_completed=user_completed)

if __name__ == '__main__':
    app.run()
