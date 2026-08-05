import os
import re
import uuid
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, redirect, url_for, request, session, flash, abort
from supabase import Client, create_client
from jinja_markdown2 import MarkdownExtension

try:
    # supabase-py >= 2.x
    from supabase_auth.errors import AuthApiError
except ImportError:
    # supabase-py < 2.x (älteres gotrue-Paket)
    from gotrue.errors import AuthApiError

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY fehlt in der .env-Datei!")

# jinja-markdown2 Extension in Flask registrieren
app.jinja_env.add_extension(MarkdownExtension)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL oder SUPABASE_KEY fehlt in der .env-Datei!")

supabase: Client = create_client(url, key)

supabase: Client = create_client(url, key)

# Fallback 404 Markdown mit Inline-HTML
NOT_FOUND_MARKDOWN = """
<div style="text-align: center; padding: 2rem 0;">
    <h1 style="font-size: 4rem; color: var(--accent-gold); margin-bottom: 0;">404</h1>
    <h2 style="margin-top: 0;">Artikel nicht gefunden</h2>
    <p>Der gesuchte Artikel existiert nicht oder wurde verschoben oder gelöscht.</p>
    <br>
    <a href="/" class="btn btn-primary">
        <i class="fa-solid fa-house"></i> Zurück zur Startseite
    </a>
</div>
"""


# ==========================================================================
# AUTH HELPERS
# ==========================================================================

def current_user():
    """Gibt das aktuell eingeloggte User-Dict aus der Session zurück (oder None)."""
    if "user_id" not in session:
        return None
    print({
        "id": session["user_id"],
        "email": session.get("user_email"),
        "role": session.get("user_role", "user"),
    })
    return {
        "id": session["user_id"],
        "email": session.get("user_email"),
        "role": session.get("user_role", "user"),
    }


@app.context_processor
def inject_user():
    # Macht `current_user` in ALLEN Templates verfügbar (z.B. für die Navbar)
    return {"current_user": current_user()}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Bitte melde dich zuerst an.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Bitte melde dich zuerst an.", "error")
            return redirect(url_for("login", next=request.path))
        if user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or str(uuid.uuid4())[:8]

@app.route('/ping')
def ping():
    return {'WacaWikiWakey': True, 'success': True, 'status': 'success'}

# ==========================================================================
# AUTH ROUTES
# ==========================================================================

@app.route("/auth/confirmation")
def auth_confirmation():
    return render_template("auth_email.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        if not email or not password:
            flash("E-Mail und Passwort werden benötigt.", "error")
            return render_template("register.html")

        if password != password_confirm:
            flash("Die Passwörter stimmen nicht überein.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Das Passwort muss mindestens 8 Zeichen lang sein.", "error")
            return render_template("register.html")

        try:
            result = supabase.auth.sign_up({"email": email, "password": password})
        except AuthApiError as e:
            flash(f"Registrierung fehlgeschlagen: {e.message}", "error")
            return render_template("register.html")

        # Falls "Confirm email" in Supabase aktiviert ist, gibt es noch keine Session.
        if result.session is None:
            flash("Registrierung erfolgreich! Bitte bestätige deine E-Mail-Adresse, bevor du dich anmeldest.", "success")
            return redirect(url_for("login"))

        # Confirm-email ist deaktiviert -> direkt eingeloggt
        _start_session(result.user.id, result.user.email)
        flash("Willkommen! Dein Konto wurde erstellt.", "success")
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        next_url = request.form.get("next") or url_for("index")

        try:
            result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        except AuthApiError:
            flash("E-Mail oder Passwort ist falsch.", "error")
            return render_template("login.html", next=next_url)

        _start_session(result.user.id, result.user.email)
        flash("Erfolgreich angemeldet.", "success")
        return redirect(next_url)

    next_url = request.args.get("next") or url_for("index")
    return render_template("login.html", next=next_url)


@app.route("/logout")
def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    session.clear()
    flash("Du wurdest abgemeldet.", "success")
    return redirect(url_for("index"))


def _start_session(user_id: str, email: str):
    """Lädt die Rolle aus profiles und legt die Flask-Session an."""
    role = "user"
    try:
        profile = supabase.table("profiles").select("role").eq("id", user_id).single().execute()
        if profile.data:
            role = profile.data.get("role", "user")
    except Exception as e:
        print(f"Konnte Rolle nicht laden: {e}")

    session["user_id"] = user_id
    session["user_email"] = email
    session["user_role"] = role


# ==========================================================================
# BESTEHENDE ROUTEN
# ==========================================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/wiki/<int:id>")
def wiki_article(id: int):
    try:
        # 1. Metadaten des Artikels aus der Datenbank abrufen
        db_response = supabase.table("WikiArticles").select("file_path, title").eq("id", id).single().execute()

        article_data = db_response.data
        if not article_data:
            return render_template(
                "wiki_article.html",
                content_md=NOT_FOUND_MARKDOWN,
                title="404 - Nicht gefunden"
            ), 404

        file_path = article_data["file_path"]

        # 2. Markdown-Datei aus dem Supabase Bucket herunterladen
        bucket_name = "WikiArticles"
        storage_response = supabase.storage.from_(bucket_name).download(file_path)

        # 3. Inhalt in UTF-8 Text umwandeln
        markdown_content = storage_response.decode("utf-8")

        # 4. An das Template übergeben
        return render_template(
            "wiki_article.html",
            content_md=markdown_content,
            title=article_data.get("title", f"Artikel #{id}"),
            error=None
        )

    except Exception as e:
        print(f"Fehler beim Laden des Wiki-Artikels: {e}")
        return render_template(
            "wiki_article.html",
            content_md=NOT_FOUND_MARKDOWN,
            title="404 - Nicht gefunden",
            error=404
        ), 404



@app.route("/editor", methods=["GET", "POST"])
@admin_required
def editor():
    if request.method == "POST":
        book_id = request.form.get("book_id")
        title = request.form.get("title", "").strip()
        content_md = request.form.get("content_md", "")

        if not book_id:
            flash("Bitte wähle ein Buch aus.", "error")
            return redirect(url_for("editor"))

        if not title or not content_md.strip():
            flash("Titel und Inhalt dürfen nicht leer sein.", "error")
            return redirect(url_for("editor"))

        try:
            book_id_int = int(book_id)
        except ValueError:
            flash("Ungültiges Buch gewählt.", "error")
            return redirect(url_for("editor"))

        slug = slugify(title)
        file_path = f"{slug}-{uuid.uuid4().hex[:8]}.md"
        bucket_name = "WikiArticles"

        try:
            # 1. Markdown-Datei in den Storage-Bucket hochladen
            supabase.storage.from_(bucket_name).upload(
                file_path,
                content_md.encode("utf-8"),
                {"content-type": "text/markdown"},
            )

            # 2. Eintrag in der WikiArticles-Tabelle anlegen mit expliziter ID = book_id
            user = current_user()
            insert_response = supabase.table("WikiArticles").insert({
                "id": book_id_int,  # Dieselbe ID wie das Buch
                "title": title,
                "file_path": file_path,
                "slug": slug,
                "author_id": user["id"],
            }).execute()

            new_id = insert_response.data[0]["id"]
            flash("Artikel wurde veröffentlicht und mit dem Buch verknüpft!", "success")
            return redirect(url_for("wiki_article", id=new_id))

        except Exception as e:
            print(f"Fehler beim Speichern des Artikels: {e}")
            flash(f"Fehler beim Speichern: {e}", "error")
            return redirect(url_for("editor"))

    # GET-Request: Verfügbare Bücher abrufen (Bücher ohne Wiki-Eintrag)
    try:
        # Alle bestehenden Wiki-Artikel-IDs abrufen
        wiki_res = supabase.table("WikiArticles").select("id").execute()
        existing_wiki_ids = [item["id"] for item in (wiki_res.data or [])]

        # Alle Bücher abrufen
        books_res = supabase.table("Books").select("id, title, author").execute()
        all_books = books_res.data or []

        # Nur Bücher filtern, deren ID noch in keiner WikiArticle-Zeile vorhanden ist
        available_books = [
            b for b in all_books if b["id"] not in existing_wiki_ids
        ]
    except Exception as e:
        print(f"Fehler beim Laden der verfügbaren Bücher: {e}")
        available_books = []

    return render_template("md-editor.html", available_books=available_books)

@app.route("/admin/books", methods=["GET", "POST"])
@admin_required
def admin_books():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        thumbnail_url = request.form.get("thumbnail_url", "").strip()

        if not title or not author:
            flash("Titel und Autor sind Pflichtfelder.", "error")
            return render_template("books_admin.html")

        try:
            user = current_user()
            supabase.table("Books").insert({
                "title": title,
                "author": author,
                "thumbnail_url": thumbnail_url or None,
                "created_by": user["id"],
            }).execute()
            flash("Buch wurde hinzugefügt!", "success")
            return redirect(url_for("admin_books"))
        except Exception as e:
            print(f"Fehler beim Hinzufügen des Buchs: {e}")
            flash(f"Fehler: {e}", "error")
            return render_template("books_admin.html")

    return render_template("books_admin.html")


@app.route("/api/books", methods=["GET"])
def api_books():
    try:
        response = supabase.table("Books").select("*").execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.errorhandler(403)
def forbidden(e):
    return render_template(
        "wiki_article.html",
        content_md="<h1>403</h1><p>Du hast keine Berechtigung, diese Seite aufzurufen.</p>",
        title="403 - Kein Zugriff",
        error=403
    ), 403


if __name__ == "__main__":
    app.run(debug=True)