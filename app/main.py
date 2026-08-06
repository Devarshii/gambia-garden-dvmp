import json
import sys
from pathlib import Path

# ---------------------------------------------------------
# Add project root to Python path
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pandas as pd
import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.matching.database import (
    confirm_match,
    get_community_needs,
    get_proposed_matches,
    reject_match,
)
from app.matching.generate_matches import (
    engine,
    generate_matches,
)


# ---------------------------------------------------------
# Streamlit configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Gambia Garden DVMP",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# Database connection
# ---------------------------------------------------------

def check_database_connection():
    """
    Test the database connection.
    """
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


# ---------------------------------------------------------
# Update community need
# ---------------------------------------------------------

def update_community_need(
    connection,
    need_id,
    status,
    coordinator_notes,
):
    """
    Update the status and notes of a community need.
    """
    query = text(
        """
        UPDATE community_needs
        SET
            status = :status,
            coordinator_notes = :coordinator_notes,
            resolved_at = CASE
                WHEN :status = 'fulfilled'
                    THEN COALESCE(
                        resolved_at,
                        CURRENT_TIMESTAMP
                    )
                ELSE NULL
            END
        WHERE need_id = :need_id
        RETURNING
            need_id,
            status,
            coordinator_notes,
            resolved_at
        """
    )

    result = connection.execute(
        query,
        {
            "need_id": need_id,
            "status": status,
            "coordinator_notes": coordinator_notes,
        },
    )

    return result.mappings().first()


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def format_currency(value):
    """
    Format a value as currency.
    """
    if value is None or pd.isna(value):
        return "Not provided"

    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def prepare_score_breakdown(score_breakdown):
    """
    Convert a score breakdown into a dictionary.
    """
    if score_breakdown is None:
        return {}

    if isinstance(score_breakdown, dict):
        return score_breakdown

    if isinstance(score_breakdown, str):
        try:
            parsed_breakdown = json.loads(score_breakdown)

            if isinstance(parsed_breakdown, dict):
                return parsed_breakdown

        except json.JSONDecodeError:
            return {}

    return {}


def display_score_breakdown(score_breakdown):
    """
    Display the score breakdown for a match.
    """
    breakdown = prepare_score_breakdown(score_breakdown)

    if not breakdown:
        st.info(
            "No score breakdown is currently stored "
            "for this match."
        )
        return

    breakdown_records = []

    for category, score_data in breakdown.items():
        if isinstance(score_data, dict):
            category_score = score_data.get(
                "score",
                score_data.get(
                    "value",
                    score_data.get("points"),
                ),
            )

            category_weight = score_data.get("weight")

            category_reason = score_data.get(
                "reason",
                score_data.get("explanation", ""),
            )

        else:
            category_score = score_data
            category_weight = None
            category_reason = ""

        breakdown_records.append(
            {
                "Category": (
                    str(category)
                    .replace("_", " ")
                    .title()
                ),
                "Score": category_score,
                "Weight": category_weight,
                "Explanation": category_reason,
            }
        )

    breakdown_df = pd.DataFrame(breakdown_records)

    display_columns = [
        "Category",
        "Score",
    ]

    if breakdown_df["Weight"].notna().any():
        display_columns.append("Weight")

    if (
        breakdown_df["Explanation"]
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
        .any()
    ):
        display_columns.append("Explanation")

    st.dataframe(
        breakdown_df[display_columns],
        hide_index=True,
        use_container_width=True,
    )


# ---------------------------------------------------------
# Open Needs page
# ---------------------------------------------------------

def show_open_needs():
    """
    Display and manage community needs.
    """
    st.title("📋 Open Needs")

    st.write(
        "View, filter and manage community needs that are "
        "open, matched or fulfilled."
    )

    try:
        with engine.connect() as connection:
            records = get_community_needs(connection)

    except SQLAlchemyError as error:
        st.error(
            "Community needs could not be loaded "
            "from the database."
        )
        st.caption(str(error))
        return

    if not records:
        st.warning("No community needs were found.")
        return

    needs_df = pd.DataFrame(records)

    required_columns = [
        "need_id",
        "village",
        "region",
        "category",
        "urgency",
        "status",
        "estimated_cost",
        "date_submitted",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in needs_df.columns
    ]

    if missing_columns:
        st.error(
            "The community-needs query is missing "
            "required columns."
        )

        st.code(", ".join(missing_columns))
        return

    if "description" not in needs_df.columns:
        needs_df["description"] = None

    if "coordinator_notes" not in needs_df.columns:
        needs_df["coordinator_notes"] = None

    if "resolved_at" not in needs_df.columns:
        needs_df["resolved_at"] = None

    needs_df["urgency"] = pd.to_numeric(
        needs_df["urgency"],
        errors="coerce",
    ).fillna(1).astype(int)

    needs_df["estimated_cost"] = pd.to_numeric(
        needs_df["estimated_cost"],
        errors="coerce",
    )

    needs_df["date_submitted"] = pd.to_datetime(
        needs_df["date_submitted"],
        errors="coerce",
    )

    needs_df["resolved_at"] = pd.to_datetime(
        needs_df["resolved_at"],
        errors="coerce",
    )

    needs_df["status"] = (
        needs_df["status"]
        .fillna("open")
        .astype(str)
        .str.lower()
        .str.strip()
    )

    st.subheader("Filters")

    filter_col1, filter_col2, filter_col3, filter_col4 = (
        st.columns(4)
    )

    region_options = sorted(
        needs_df["region"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    category_options = sorted(
        needs_df["category"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    with filter_col1:
        selected_region = st.selectbox(
            "Region",
            options=["All Regions"] + region_options,
        )

    with filter_col2:
        selected_category = st.selectbox(
            "Category",
            options=["All Categories"] + category_options,
        )

    with filter_col3:
        selected_urgency = st.slider(
            "Urgency",
            min_value=1,
            max_value=5,
            value=(1, 5),
        )

    with filter_col4:
        selected_statuses = st.multiselect(
            "Status",
            options=[
                "open",
                "matched",
                "fulfilled",
            ],
            default=[
                "open",
                "matched",
            ],
            format_func=lambda value: value.title(),
        )

    filtered_df = needs_df.copy()

    if selected_region != "All Regions":
        filtered_df = filtered_df[
            filtered_df["region"] == selected_region
        ]

    if selected_category != "All Categories":
        filtered_df = filtered_df[
            filtered_df["category"] == selected_category
        ]

    filtered_df = filtered_df[
        filtered_df["urgency"].between(
            selected_urgency[0],
            selected_urgency[1],
        )
    ]

    if selected_statuses:
        filtered_df = filtered_df[
            filtered_df["status"].isin(selected_statuses)
        ]
    else:
        filtered_df = filtered_df.iloc[0:0]

    filtered_df = filtered_df.reset_index(drop=True)

    st.divider()
    st.subheader("Community Needs")

    st.caption(
        f"{len(filtered_df)} record(s) found. "
        "Select a row to view its details."
    )

    if filtered_df.empty:
        st.info(
            "No community needs match the selected filters."
        )
        return

    display_df = filtered_df[
        [
            "village",
            "region",
            "category",
            "urgency",
            "status",
            "estimated_cost",
            "date_submitted",
        ]
    ].copy()

    display_df["status"] = (
        display_df["status"].str.title()
    )

    display_df["date_submitted"] = (
        display_df["date_submitted"]
        .dt.strftime("%Y-%m-%d")
    )

    display_df = display_df.rename(
        columns={
            "village": "Village",
            "region": "Region",
            "category": "Category",
            "urgency": "Urgency",
            "status": "Status",
            "estimated_cost": "Estimated Cost",
            "date_submitted": "Date Submitted",
        }
    )

    table_event = st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Urgency": st.column_config.NumberColumn(
                "Urgency",
                min_value=1,
                max_value=5,
                format="%d",
            ),
            "Estimated Cost": (
                st.column_config.NumberColumn(
                    "Estimated Cost",
                    format="$%.2f",
                )
            ),
        },
    )

    selected_rows = table_event.selection.rows

    if not selected_rows:
        st.info(
            "Select one community need from the table "
            "to view and update it."
        )
        return

    selected_need = filtered_df.iloc[selected_rows[0]]

    village = selected_need.get("village")

    if village is None or pd.isna(village):
        village = "Selected Community"

    st.divider()
    st.subheader(f"Need Details: {village}")

    detail_col1, detail_col2, detail_col3 = (
        st.columns(3)
    )

    with detail_col1:
        st.markdown(
            f"**Region:** "
            f"{selected_need.get('region') or 'Not provided'}"
        )

        st.markdown(
            f"**Category:** "
            f"{selected_need.get('category') or 'Not provided'}"
        )

    with detail_col2:
        st.markdown(
            f"**Urgency:** "
            f"{selected_need.get('urgency', 1)}/5"
        )

        st.markdown(
            f"**Status:** "
            f"{str(selected_need.get('status')).title()}"
        )

    with detail_col3:
        st.markdown(
            f"**Estimated Cost:** "
            f"{format_currency(selected_need.get('estimated_cost'))}"
        )

        date_submitted = selected_need.get(
            "date_submitted"
        )

        if pd.notna(date_submitted):
            st.markdown(
                f"**Date Submitted:** "
                f"{date_submitted.strftime('%B %d, %Y')}"
            )
        else:
            st.markdown(
                "**Date Submitted:** Not provided"
            )

    st.markdown("#### Full Description")

    description = selected_need.get("description")

    if (
        description is not None
        and pd.notna(description)
        and str(description).strip()
    ):
        st.write(description)
    else:
        st.write("No description has been provided.")

    coordinator_notes = selected_need.get(
        "coordinator_notes"
    )

    st.markdown("#### Current Coordinator Notes")

    if (
        coordinator_notes is not None
        and pd.notna(coordinator_notes)
        and str(coordinator_notes).strip()
    ):
        st.write(coordinator_notes)
    else:
        st.write(
            "No coordinator notes have been added."
        )

    resolved_at = selected_need.get("resolved_at")

    if pd.notna(resolved_at):
        st.markdown(
            f"**Resolved At:** "
            f"{resolved_at.strftime('%B %d, %Y at %I:%M %p')}"
        )
    else:
        st.markdown("**Resolved At:** Not resolved")

    st.divider()
    st.subheader("✏️ Update Need Record")

    need_id = selected_need.get("need_id")

    if need_id is None or pd.isna(need_id):
        st.error(
            "This record cannot be updated because "
            "its need_id was not loaded."
        )
        return

    status_order = [
        "open",
        "matched",
        "fulfilled",
    ]

    current_status = str(
        selected_need.get("status") or "open"
    ).lower().strip()

    if current_status not in status_order:
        current_status = "open"

    current_status_position = status_order.index(
        current_status
    )

    allowed_statuses = status_order[
        current_status_position:
    ]

    existing_notes = ""

    if (
        coordinator_notes is not None
        and pd.notna(coordinator_notes)
    ):
        existing_notes = str(coordinator_notes)

    with st.form(
        key=f"update_need_form_{need_id}"
    ):
        new_status = st.selectbox(
            "Status",
            options=allowed_statuses,
            index=0,
            format_func=lambda value: value.title(),
        )

        new_notes = st.text_area(
            "Coordinator Notes",
            value=existing_notes,
            placeholder=(
                "Add or update notes about this "
                "community need..."
            ),
            height=140,
        )

        if new_status == "fulfilled":
            st.info(
                "Saving the need as Fulfilled will "
                "automatically set resolved_at."
            )

        save_clicked = st.form_submit_button(
            "💾 Save Changes",
            type="primary",
        )

    if save_clicked:
        try:
            with engine.begin() as connection:
                updated_need = update_community_need(
                    connection=connection,
                    need_id=need_id,
                    status=new_status,
                    coordinator_notes=(
                        new_notes.strip() or None
                    ),
                )

            if updated_need:
                st.success(
                    "Community need updated successfully."
                )
                st.rerun()
            else:
                st.warning(
                    "The community need could not be updated."
                )

        except SQLAlchemyError as error:
            st.error(
                "The community need could not be updated."
            )
            st.caption(str(error))


# ---------------------------------------------------------
# Donor Profile page
# ---------------------------------------------------------

def show_donor_profile():
    """
    Display donor profile information.
    """
    st.title("👤 Donor Profile")

    st.write(
        "Search and review donor information including "
        "giving capacity, preferred causes and preferred regions."
    )

    st.info(
        "Donor profiles will appear here in the next task."
    )


# ---------------------------------------------------------
# Matching Engine page
# ---------------------------------------------------------

def show_matching_engine():
    """
    Run the matching engine from the Streamlit interface.
    """
    st.title("⚙️ Matching Engine")

    st.write(
        "Run the donor-to-community matching process against "
        "all currently open community needs."
    )

    st.info(
        "The matching engine evaluates every donor against "
        "every open need. Matches scoring 50 or higher are "
        "created or updated."
    )

    run_clicked = st.button(
        "▶ Run Matching Engine",
        type="primary",
        use_container_width=True,
    )

    if run_clicked:
        try:
            with st.spinner(
                "Running the matching engine. Please wait..."
            ):
                summary = generate_matches()

            st.success(
                "Matching engine completed successfully."
            )

            st.subheader("Run Summary")

            first_col, second_col, third_col = (
                st.columns(3)
            )

            with first_col:
                st.metric(
                    "Donors Scanned",
                    summary["donors_scanned"],
                )

            with second_col:
                st.metric(
                    "Open Needs Scanned",
                    summary["open_needs_scanned"],
                )

            with third_col:
                st.metric(
                    "Combinations Evaluated",
                    summary["total_combinations"],
                )

            fourth_col, fifth_col, sixth_col = (
                st.columns(3)
            )

            with fourth_col:
                st.metric(
                    "New Matches Created",
                    summary["inserted_matches"],
                )

            with fifth_col:
                st.metric(
                    "Existing Matches Updated",
                    summary["updated_matches"],
                )

            with sixth_col:
                st.metric(
                    "Below Score 50",
                    summary["skipped_matches"],
                )

            st.metric(
                "Qualified Matches",
                summary["qualified_matches"],
            )

            if summary["inserted_matches"] > 0:
                st.success(
                    f"{summary['inserted_matches']} new "
                    "match(es) were added for review."
                )
            else:
                st.info(
                    "No new matches were created. Existing "
                    "qualified matches may have been updated."
                )

        except SQLAlchemyError as error:
            st.error(
                "The matching engine could not complete "
                "because of a database error."
            )
            st.caption(str(error))

        except Exception as error:
            st.error(
                "An unexpected error occurred while running "
                "the matching engine."
            )
            st.caption(str(error))


# ---------------------------------------------------------
# Match Review page
# ---------------------------------------------------------

def show_match_review():
    """
    Display and review proposed matches.
    """
    st.title("🤝 Match Review")

    st.write(
        "Review proposed donor-to-community matches, inspect "
        "their scores, add notes and make a decision."
    )

    try:
        with engine.connect() as connection:
            matches = get_proposed_matches(connection)

    except SQLAlchemyError as error:
        st.error(
            "Proposed matches could not be loaded "
            "from the database."
        )
        st.caption(str(error))
        return

    if not matches:
        st.success(
            "There are currently no pending or proposed "
            "matches to review."
        )
        return

    st.caption(
        f"{len(matches)} match(es) are waiting for review."
    )

    for match in matches:
        match_id = str(match["match_id"])

        donor_name = (
            match.get("donor_name")
            or "Unknown Donor"
        )

        village = (
            match.get("village")
            or "Unknown Community"
        )

        match_score = match.get("match_score")

        if match_score is not None:
            try:
                score_label = (
                    f"{float(match_score):.2f}"
                )
            except (TypeError, ValueError):
                score_label = str(match_score)
        else:
            score_label = "Not calculated"

        expander_title = (
            f"{village} — {donor_name} — "
            f"Score: {score_label}"
        )

        with st.expander(
            expander_title,
            expanded=True,
        ):
            summary_col1, summary_col2, summary_col3 = (
                st.columns(3)
            )

            with summary_col1:
                st.markdown("#### Community Need")

                st.markdown(
                    f"**Village:** {village}"
                )

                st.markdown(
                    f"**Region:** "
                    f"{match.get('region') or 'Not provided'}"
                )

                st.markdown(
                    f"**Category:** "
                    f"{match.get('category') or 'Not provided'}"
                )

            with summary_col2:
                st.markdown("#### Need Details")

                urgency = match.get("urgency")

                if urgency is None:
                    urgency = "Not provided"

                st.markdown(
                    f"**Urgency:** {urgency}"
                )

                st.markdown(
                    f"**Estimated Cost:** "
                    f"{format_currency(match.get('estimated_cost'))}"
                )

                need_status = (
                    match.get("need_status")
                    or "Unknown"
                )

                st.markdown(
                    f"**Need Status:** "
                    f"{str(need_status).title()}"
                )

            with summary_col3:
                st.markdown("#### Match Details")

                st.markdown(
                    f"**Donor:** {donor_name}"
                )

                st.markdown(
                    f"**Match Score:** {score_label}"
                )

                match_status = (
                    match.get("match_status")
                    or "Unknown"
                )

                st.markdown(
                    f"**Match Status:** "
                    f"{str(match_status).title()}"
                )

                match_type = (
                    match.get("match_type")
                    or "Unknown"
                )

                st.markdown(
                    f"**Match Type:** "
                    f"{str(match_type).title()}"
                )

            st.markdown(
                "#### Community Need Summary"
            )

            description = match.get("description")

            if (
                description is not None
                and str(description).strip()
            ):
                st.write(description)
            else:
                st.write(
                    "No community need description "
                    "is available."
                )

            st.markdown("#### Score Breakdown")

            display_score_breakdown(
                match.get("score_breakdown")
            )

            existing_notes = (
                match.get("coordinator_notes")
                or ""
            )

            coordinator_notes = st.text_area(
                "Coordinator Notes",
                value=str(existing_notes),
                placeholder=(
                    "Add notes explaining your decision..."
                ),
                key=f"coordinator_notes_{match_id}",
                height=120,
            )

            confirm_col, reject_col, spacer_col = (
                st.columns([1, 1, 4])
            )

            with confirm_col:
                confirm_clicked = st.button(
                    "✅ Confirm",
                    key=f"confirm_match_{match_id}",
                    type="primary",
                )

            with reject_col:
                reject_clicked = st.button(
                    "❌ Reject",
                    key=f"reject_match_{match_id}",
                )

            if confirm_clicked:
                try:
                    with engine.begin() as connection:
                        updated_match = confirm_match(
                            connection=connection,
                            match_id=match_id,
                            coordinator_notes=(
                                coordinator_notes.strip()
                                or None
                            ),
                        )

                    if updated_match:
                        st.success(
                            "Match confirmed successfully."
                        )
                        st.rerun()
                    else:
                        st.warning(
                            "This match could not be confirmed."
                        )

                except SQLAlchemyError as error:
                    st.error(
                        "The match could not be confirmed."
                    )
                    st.caption(str(error))

            if reject_clicked:
                try:
                    with engine.begin() as connection:
                        updated_match = reject_match(
                            connection=connection,
                            match_id=match_id,
                            coordinator_notes=(
                                coordinator_notes.strip()
                                or None
                            ),
                        )

                    if updated_match:
                        st.success(
                            "Match rejected successfully."
                        )
                        st.rerun()
                    else:
                        st.warning(
                            "This match could not be rejected."
                        )

                except SQLAlchemyError as error:
                    st.error(
                        "The match could not be rejected."
                    )
                    st.caption(str(error))


# ---------------------------------------------------------
# Main application
# ---------------------------------------------------------

def main():
    """
    Run the Streamlit application.
    """
    try:
        check_database_connection()

    except SQLAlchemyError:
        st.error(
            "Unable to connect to the database.\n\n"
            "Please verify that PostgreSQL is running and "
            "your DATABASE_URL in the .env file is correct."
        )
        st.stop()

    except Exception as error:
        st.error(
            "An unexpected database error occurred.\n\n"
            f"{error}"
        )
        st.stop()

    st.sidebar.title("🌱 Gambia Garden DVMP")
    st.sidebar.success("Database Connected")

    page = st.sidebar.radio(
        "Navigation",
        [
            "Open Needs",
            "Donor Profile",
            "Run Matching Engine",
            "Match Review",
        ],
    )

    if page == "Open Needs":
        show_open_needs()

    elif page == "Donor Profile":
        show_donor_profile()

    elif page == "Run Matching Engine":
        show_matching_engine()

    elif page == "Match Review":
        show_match_review()


if __name__ == "__main__":
    main()