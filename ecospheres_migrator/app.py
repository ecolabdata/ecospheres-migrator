import io
import os

from datetime import datetime

from flask import Flask, render_template, request, send_file, session, abort

from ecospheres_migrator.queue import get_queue, get_job
from ecospheres_migrator.migrator import Migrator

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "default-secret-key")


@app.route("/")
def select():
    return render_template(
        "select.html.j2", transformations=Migrator.TRANSFORMATIONS, url=session["url"]
    )


@app.route("/select_preview", methods=["POST"])
def select_preview():
    url = request.form.get("url")
    if not url:
        return "Veuillez entrer une URL de catalogue"
    query = request.form.get("query")
    if not query:
        return "Veuillez entrer une requête de recherche"
    migrator = Migrator(url=url)
    results = migrator.select(query=query)
    return render_template("fragments/select_preview.html.j2", results=results)


@app.route("/transform", methods=["POST"])
def transform():
    url = request.form.get("url") or ""
    session["url"] = url
    query = request.form.get("query")
    transformation = request.form.get("transformation") or ""
    transformation = next(t for t in Migrator.TRANSFORMATIONS if t["id"] == transformation)
    migrator = Migrator(url=url)
    selection = migrator.select(query=query)
    job = get_queue().enqueue(migrator.transform, transformation, selection)
    return render_template(
        "transform.html.j2",
        selection=selection,
        transformation=transformation,
        url=url,
        job=job,
    )


@app.route("/transform_job_status/<job_id>")
def transform_job_status(job_id: str):
    return render_template(
        "fragments/transform_job_status.html.j2",
        job=get_job(job_id),
        now=datetime.now().isoformat(timespec="seconds"),
        url=session["url"],
    )


@app.route("/transform_download_result/<job_id>")
def transform_download_result(job_id: str):
    job = get_job(job_id)
    return send_file(
        io.BytesIO(job.result),
        mimetype="application/zip",
        download_name=f"{job_id}.zip",
        as_attachment=True,
    )


@app.route("/migrate/<job_id>", methods=["POST"])
def migrate(job_id: str):
    transform_job = get_job(job_id)
    if not transform_job:
        abort(404)
    username = request.form.get("username")
    password = request.form.get("password")
    migrator = Migrator(url=session["url"], username=username, password=password)
    migrate_job = get_queue().enqueue(migrator.migrate, transform_job.result)
    return render_template("migrate.html.j2", job=migrate_job)


@app.route("/migrate_job_status/<job_id>")
def migrate_job_status(job_id: str):
    return render_template(
        "fragments/migrate_job_status.html.j2",
        job=get_job(job_id),
        now=datetime.now().isoformat(timespec="seconds"),
        url=session["url"],
    )


@app.route("/docs")
def documentation():
    return render_template("documentation.html.j2")


if __name__ == '__main__':
    app.run(debug=True)
