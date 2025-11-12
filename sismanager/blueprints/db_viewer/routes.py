"""
Routes for db_viewer blueprint in SISmanager.
"""

from flask import Blueprint, render_template, request
from sismanager.services.inout.central_db_service import CentralDBRepository

db_viewer_bp = Blueprint(
    "db_viewer", __name__, template_folder="../../templates/db_viewer"
)


@db_viewer_bp.route("/db_viewer", methods=["GET", "POST"])
def db_viewer():
    """Render the database viewer page with current data and optional column filtering."""
    repo = CentralDBRepository()
    df = repo.read()

    if df.empty:
        db_preview = "<p>No data found in the database.</p>"
        available_columns = []
        selected_columns = []
    else:
        available_columns = list(df.columns)

        # Handle column filtering from form submission
        if request.method == "POST":
            selected_columns = request.form.getlist("columns")
            if selected_columns:
                # Filter DataFrame to show only selected columns
                df_filtered = df[selected_columns]
            else:
                df_filtered = df
        else:
            # Default: show all columns
            selected_columns = available_columns
            df_filtered = df

        db_preview = df_filtered.to_html(classes="table table-bordered", index=False)

    return render_template(
        "db_viewer/db_viewer.html",
        db_preview=db_preview,
        available_columns=available_columns,
        selected_columns=selected_columns,
    )
