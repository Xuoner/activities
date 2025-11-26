import streamlit as st
import json
import os
from datetime import datetime
import re
import os
from PIL import Image


# -----------------------
# Config
# -----------------------
ACTIVITIES_FILE = "activities.json"
PARTICIPANTS_FILE = "participants.json"
ADMIN_PASSWORD = "admin123"

AVATAR_FOLDER = "avatars"

# -----------------------
# Custom CSS
# -----------------------
st.markdown("""
<style>
.part-badge {
    display: inline-block;
    background-color: #0057b7;
    color: white;
    padding: 5px 10px;
    margin: 3px;
    border-radius: 8px;
    font-size: 0.85rem;
}
.cal-today {
    color: #d10000;
    font-weight: bold;
}
.cal-soon {
    color: #e67e22;
    font-weight: bold;
}
.cal-future {
    color: #2c3e50;
    font-weight: bold;
}
.stButton>button {
    border-radius: 8px !important;
    padding: 8px 14px !important;
    font-size: 1rem !important;
}
</style>
""", unsafe_allow_html=True)


# -----------------------
# Helpers
# -----------------------
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
def get_avatar_html(name):
    """
    If an avatar exists for this participant, returns HTML to display it next to the name.
    Otherwise, returns just the name as text.
    """
    avatar_path = os.path.join(AVATAR_FOLDER, f"{name}.png")
    if os.path.exists(avatar_path):
        return f"<img src='{avatar_path}' style='width:30px;height:30px;border-radius:50%;vertical-align:middle;margin-right:5px;'>{name}"
    else:
        return name

def parse_date(value):
    """Returns (datetime, display_text)"""
    if not value:
        return None, None

    value = value.strip()

    # ISO yyyy-mm-dd
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            display = dt.strftime("%d/%m/%Y")
            return dt, display
        except:
            return None, None

    # DD/MM/YYYY
    if re.match(r"^\d{2}/\d{2}/\d{4}$", value):
        try:
            dt = datetime.strptime(value, "%d/%m/%Y")

            # Case: "01/MM/YYYY" → display month
            if value.startswith("01/"):
                display = dt.strftime("%B %Y").capitalize()
            else:
                display = value

            return dt, display
        except:
            return None, None

    # French month names
    MONTHS_FR = {
        "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "août": 8, "septembre": 9, "octobre": 10,
        "novembre": 11, "décembre": 12
    }

    lower = value.lower()
    if lower in MONTHS_FR:
        month = MONTHS_FR[lower]
        today = datetime.today()

        year = today.year
        if month < today.month:
            year += 1

        dt = datetime(year, month, 1)
        display = f"{value.capitalize()} {year}"
        return dt, display

    return None, None


# -----------------------
# Load Data
# -----------------------
activities = load_json(ACTIVITIES_FILE, [])
participants = load_json(PARTICIPANTS_FILE, [])

# -----------------------
# Sidebar: identity + calendar
# -----------------------
st.sidebar.header("👤 Qui es-tu ?")
user_name = st.sidebar.text_input("Ton prénom")

st.sidebar.markdown("### 📅 Calendrier")
today = datetime.today()

calendar_entries = []
for act in activities:
    dt, display = parse_date(act.get("date", ""))

    if dt and dt >= today:
        calendar_entries.append({
            "dt": dt,
            "display": display,
            "name": act["name"]
        })

# Group entries
grouped_calendar = {}
for item in calendar_entries:
    grouped_calendar.setdefault(item["display"], []).append(item)

if grouped_calendar:
    for display, items in sorted(grouped_calendar.items(), key=lambda x: x[1][0]["dt"]):

        dt = items[0]["dt"]
        delta_days = (dt - today).days

        if delta_days == 0:
            cls = "cal-today"
        elif delta_days <= 7:
            cls = "cal-soon"
        else:
            cls = "cal-future"

        st.sidebar.markdown(
            f"<span class='{cls}'>{display}</span> : {', '.join([i['name'] for i in items])}",
            unsafe_allow_html=True
        )
else:
    st.sidebar.write("Aucune date renseignée.")

# -----------------------
# Title
# -----------------------
st.markdown("<h1 style='text-align:center;'>🎉 Activités L&D</h1>", unsafe_allow_html=True)


# -----------------------
# Show activities UI
# -----------------------
def show_activity(activity, key_prefix):
    dt, _ = parse_date(activity.get("date", ""))

    with st.expander(f"{activity['name']} ({activity.get('date','N/A')})"):
        st.markdown(f"**Date :** {activity.get('date','N/A')}  |  **Coût :** {activity.get('cost','N/A')}")

        st.write(activity.get("description", ""))

        # Participants
        act_part = [p for p in participants if p["activity"] == activity["name"]]
        current = len(act_part)
        max_p = activity.get("max_participants")

        st.markdown("### Participants")
        if act_part:
            
            badges = " ".join([f"<span class='part-badge'>{p['name']}</span>" for p in act_part])
            st.markdown(badges, unsafe_allow_html=True)
        else:
            st.write("*Aucun participant*")

        # Participant cap
        if max_p:
            st.markdown(f"**{current} / {max_p} participants**")

        # Signup
        if not max_p or current < max_p:
            if st.button(f"Je participe à {activity['name']}", key=f"{key_prefix}_sign"):
                if not user_name:
                    st.error("Indique ton nom dans la barre latérale.")
                elif any(p["name"] == user_name and p["activity"] == activity["name"] for p in participants):
                    st.warning("Déjà inscrit.")
                else:
                    participants.append({"name": user_name, "activity": activity["name"]})
                    save_json(PARTICIPANTS_FILE, participants)

                    # Mark full
                    if max_p and len([p for p in participants if p["activity"] == activity["name"]]) >= max_p:
                        for a in activities:
                            if a["name"] == activity["name"]:
                                a["status"] = "Complet"
                        save_json(ACTIVITIES_FILE, activities)

                    st.success("Inscription confirmée 🎉")
                    st.rerun()
        else:
            st.warning("Nombre maximal de participants atteint !")


# -----------------------
# Upcoming highlight
# -----------------------
st.markdown("## 🔥 Prochaines activités")

upcoming = []
for act in activities:
    dt, display = parse_date(act.get("date", ""))
    # Only include real dates (ignore placeholder first-of-month)
    if dt and dt.day != 1 and dt >= today:
        upcoming.append((dt, act))

upcoming = sorted(upcoming, key=lambda x: x[0])[:5]

for dt, act in upcoming:
    show_activity(act, f"up_{act['name']}")



st.write("---")

# -----------------------
# Group remaining activities
# -----------------------
already_upcoming = [a[1] for a in upcoming]

status_groups = {"Ouvert": [], "Complet": [], "À venir": []}

for act in activities:
    dt, _ = parse_date(act.get("date", ""))
    if act not in already_upcoming and (not dt or dt >= today):
        status_groups.setdefault(act["status"], []).append(act)

for status, acts in status_groups.items():
    if acts:
        st.markdown(f"## {status}")
        for i, act in enumerate(acts):
            show_activity(act, f"{status}_{i}")


# -----------------------
# Add new activity
# -----------------------
with st.expander("➕ Ajouter une nouvelle activité"):
    with st.form("add_activity"):
        name = st.text_input("Nom")
        description = st.text_area("Description")
        date = st.text_input("Date (jj/mm/aaaa, yyyy-mm-dd ou mois)")
        cost = st.text_input("Coût")
        link = st.text_input("Lien")
        max_participants = st.number_input("Maximum de participants (0 = illimité)", min_value=0, step=1)
        status = st.selectbox("Statut", ["Ouvert", "Complet", "À venir"])

        if st.form_submit_button("Créer"):
            activities.append({
                "name": name,
                "description": description,
                "date": date,
                "cost": cost,
                "link": link,
                "status": status,
                "max_participants": max_participants if max_participants > 0 else None
            })
            save_json(ACTIVITIES_FILE, activities)
            st.success("Activité créée 🎉")
            st.rerun()
