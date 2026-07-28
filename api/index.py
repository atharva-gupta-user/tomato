import os
import random
from datetime import datetime

from flask import Flask, render_template, jsonify, request, session
from dotenv import load_dotenv
from groq import Groq

try:
    from supabase import create_client, Client
except ImportError:  # supabase package not installed in this environment
    create_client = None
    Client = None

try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
except ImportError:
    id_token = None
    google_requests = None

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
load_dotenv()

app = Flask(__name__, template_folder='../templates')
app.secret_key = os.environ.get("SECRET_KEY", "unimatch-secret-key-2026")

# --- Groq (LLM) ---
groq_api_key = os.environ.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

# llama-3.3-70b-versatile was deprecated by Groq on 2026-06-17.
# openai/gpt-oss-120b is Groq's recommended replacement.
GROQ_MODEL_ID = os.environ.get("GROQ_MODEL_ID", "openai/gpt-oss-120b")

# --- Supabase (optional persistent auth store) ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_KEY", ""))
supabase_client = None
if create_client and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase_client = None

# --- Google Sign-In (optional) ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

random.seed(42)

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------
UNIVERSITIES = [
    {"id": 1, "name": "MIT", "min_gpa": 3.8, "avg_sat": 1520, "avg_act": 35,
     "tuition": "$58,000", "acceptance": "4%", "region": "Northeast", "campus_type": "Urban",
     "dna_tags": ["STEM", "Research", "Innovation"]},
    {"id": 2, "name": "Stanford University", "min_gpa": 3.85, "avg_sat": 1510, "avg_act": 34,
     "tuition": "$61,000", "acceptance": "3.9%", "region": "West", "campus_type": "Suburban",
     "dna_tags": ["STEM", "Innovation", "Leadership"]},
    {"id": 3, "name": "UC Berkeley", "min_gpa": 3.65, "avg_sat": 1410, "avg_act": 31,
     "tuition": "$44,000", "acceptance": "11.4%", "region": "West", "campus_type": "Urban",
     "dna_tags": ["Community Service", "Research", "STEM"]},
    {"id": 4, "name": "Carnegie Mellon", "min_gpa": 3.75, "avg_sat": 1500, "avg_act": 34,
     "tuition": "$62,000", "acceptance": "11%", "region": "Northeast", "campus_type": "Urban",
     "dna_tags": ["STEM", "Innovation", "Research"]},
    {"id": 5, "name": "Harvard University", "min_gpa": 3.9, "avg_sat": 1540, "avg_act": 35,
     "tuition": "$56,000", "acceptance": "3.4%", "region": "Northeast", "campus_type": "Urban",
     "dna_tags": ["Leadership", "Community Service", "Arts"]},
    {"id": 6, "name": "Caltech", "min_gpa": 3.9, "avg_sat": 1560, "avg_act": 36,
     "tuition": "$60,000", "acceptance": "2.7%", "region": "West", "campus_type": "Suburban",
     "dna_tags": ["STEM", "Research", "Innovation"]},
]

INSTITUTIONAL_CANDIDATES = [
    {"id": 101, "name": "Alex Vance", "gpa": 3.92, "sat": 1550, "act": 35,
     "major": "Computer Science", "dna": ["STEM", "Innovation"]},
    {"id": 102, "name": "Elena Rostova", "gpa": 3.78, "sat": 1460, "act": 32,
     "major": "Biomedical Engineering", "dna": ["Research", "STEM"]},
    {"id": 103, "name": "Marcus Chen", "gpa": 3.85, "sat": 1510, "act": 34,
     "major": "Applied Mathematics", "dna": ["Leadership", "STEM"]},
    {"id": 104, "name": "Sarah Jenkins", "gpa": 3.62, "sat": 1390, "act": 29,
     "major": "Economics & Public Policy", "dna": ["Community Service", "Leadership"]},
]


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def _parse_profile(data):
    gpa = _clamp(float(data.get('gpa', 3.5) or 3.5), 0.0, 4.0)
    sat = int(_clamp(float(data.get('sat', 1400) or 1400), 400, 1600))
    act = int(_clamp(float(data.get('act', 30) or 30), 1, 36))
    return gpa, sat, act


def _score_university(u, gpa, sat, act, dna_tags):
    score = 40
    if gpa >= u['min_gpa']:
        score += 20
    elif gpa >= u['min_gpa'] - 0.15:
        score += 10
    if sat >= u['avg_sat']:
        score += 15
    elif sat >= u['avg_sat'] - 60:
        score += 8
    if act >= u['avg_act']:
        score += 10
    elif act >= u['avg_act'] - 2:
        score += 5
    overlap = len(set(dna_tags) & set(u['dna_tags']))
    score += min(overlap * 5, 15)
    return int(_clamp(score, 20, 98))


def _tier_for_score(score):
    if score >= 78:
        return "Safety", "emerald"
    if score >= 55:
        return "Target", "amber"
    return "Reach", "rose"


def _reasoning_for(u, gpa, sat, act, dna_tags, score):
    gpa_delta = round(gpa - u['min_gpa'], 2)
    sat_delta = sat - u['avg_sat']
    overlap = sorted(set(dna_tags) & set(u['dna_tags']))
    bits = []
    bits.append(f"Your GPA is {'above' if gpa_delta >= 0 else 'below'} {u['name']}'s typical floor by {abs(gpa_delta)}.")
    bits.append(f"SAT is {'at/above' if sat_delta >= 0 else 'below'} their average by {abs(sat_delta)} points.")
    if overlap:
        bits.append(f"Shared strengths: {', '.join(overlap)}.")
    return " ".join(bits)


def _score_candidate(c, min_gpa, target_dna):
    score = 50
    if c['gpa'] >= min_gpa:
        score += 20
    if target_dna:
        overlap = len(set(c['dna']) & set(target_dna))
        score += min(overlap * 12, 24)
    else:
        score += 10
    # small deterministic jitter for variety, seeded so results are stable
    score += random.Random(c['id']).randint(-3, 3)
    return int(_clamp(score, 40, 99))


def current_user_from_session():
    return session.get('user')


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html', google_client_id=GOOGLE_CLIENT_ID)


# ---------------------------------------------------------------------------
# Universities list (used to populate the deep-predictor dropdown)
# ---------------------------------------------------------------------------
@app.route('/api/universities', methods=['GET'])
def list_universities():
    return jsonify({"universities": [u['name'] for u in UNIVERSITIES]})


# ---------------------------------------------------------------------------
# Student matching
# ---------------------------------------------------------------------------
@app.route('/api/match/student', methods=['POST'])
def match_student():
    data = request.json or {}
    try:
        gpa, sat, act = _parse_profile(data)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numerical parameters supplied for academic credentials."}), 400

    dna_tags = data.get('dna', []) or []
    region_pref = data.get('region')
    campus_pref = data.get('campus_type')

    matches = []
    for u in UNIVERSITIES:
        score = _score_university(u, gpa, sat, act, dna_tags)
        # small nudge for matching stated preferences, doesn't gate results
        if region_pref and region_pref == u['region']:
            score = int(_clamp(score + 3, 20, 99))
        if campus_pref and campus_pref == u['campus_type']:
            score = int(_clamp(score + 2, 20, 99))

        tier, color = _tier_for_score(score)
        matches.append({
            "university": u['name'],
            "probability": score,
            "tier": tier,
            "color": color,
            "region": u['region'],
            "campus_type": u['campus_type'],
            "reasoning": _reasoning_for(u, gpa, sat, act, dna_tags, score),
        })

    matches.sort(key=lambda m: m['probability'], reverse=True)
    return jsonify({"matches": matches})


# ---------------------------------------------------------------------------
# Deep single-university predictor
# ---------------------------------------------------------------------------
@app.route('/api/advisor/predict', methods=['POST'])
def advisor_predict():
    data = request.json or {}
    try:
        gpa, sat, act = _parse_profile(data)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid profile metrics."}), 400

    university_name = data.get('university', 'MIT')
    major = data.get('major', 'General')
    dna_tags = data.get('dna', []) or []

    u = next((x for x in UNIVERSITIES if x['name'].lower() == str(university_name).lower()), None)
    if not u:
        return jsonify({"error": f"Unknown university '{university_name}'."}), 404

    score = _score_university(u, gpa, sat, act, dna_tags)
    tier, _ = _tier_for_score(score)

    strengths = []
    weaknesses = []

    if gpa >= u['min_gpa']:
        strengths.append(f"GPA of {gpa} clears {u['name']}'s typical floor of {u['min_gpa']}")
    else:
        weaknesses.append(f"GPA of {gpa} sits below {u['name']}'s typical floor of {u['min_gpa']}")

    if sat >= u['avg_sat']:
        strengths.append(f"SAT of {sat} is at or above the {u['avg_sat']} average")
    else:
        weaknesses.append(f"SAT of {sat} trails the {u['avg_sat']} average by {u['avg_sat'] - sat} points")

    if act >= u['avg_act']:
        strengths.append(f"ACT of {act} matches or exceeds the {u['avg_act']} average")
    else:
        weaknesses.append(f"ACT of {act} is below the {u['avg_act']} average")

    overlap = sorted(set(dna_tags) & set(u['dna_tags']))
    missing = sorted(set(u['dna_tags']) - set(dna_tags))
    if overlap:
        strengths.append(f"Strong cultural fit via {', '.join(overlap)}")
    if missing:
        weaknesses.append(f"Limited visible alignment with {', '.join(missing)}")

    if not strengths:
        strengths.append("Well-rounded application profile with room to grow into this tier")
    if not weaknesses:
        weaknesses.append("No major gaps identified against published benchmarks")

    prompt = (
        f"Context: You are an expert admissions advisor.\n"
        f"Candidate: GPA {gpa}/4.0, SAT {sat}/1600, ACT {act}/36, target major {major}.\n"
        f"Target Institution: {u['name']} (min GPA {u['min_gpa']}, avg SAT {u['avg_sat']}, avg ACT {u['avg_act']}, "
        f"acceptance rate {u['acceptance']}).\n"
        f"Task: In 2-3 concise sentences, give the single highest-leverage recommendation to improve this "
        f"candidate's admission odds at {u['name']}. Be specific and actionable."
    )

    if not groq_client:
        recommendations = (
            f"Focus your remaining application cycle on deepening evidence for "
            f"{', '.join(overlap) if overlap else 'your strongest DNA trait'}: seek a project, award, or "
            f"leadership role that clearly differentiates you for {u['name']}'s admissions committee."
        )
    else:
        try:
            completion = groq_client.chat.completions.create(
                model=GROQ_MODEL_ID,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=220,
            )
            recommendations = completion.choices[0].message.content.strip()
        except Exception as e:
            recommendations = f"Recommendation engine temporarily unavailable ({e})."

    return jsonify({
        "university": u['name'],
        "match_score": score,
        "tier": tier,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
    })


# ---------------------------------------------------------------------------
# Institution-side candidate search
# ---------------------------------------------------------------------------
@app.route('/api/match/institute', methods=['POST'])
def match_institute():
    data = request.json or {}
    try:
        min_gpa = _clamp(float(data.get('min_gpa', 3.5) or 3.5), 0.0, 4.0)
    except (ValueError, TypeError):
        min_gpa = 3.5

    target_dna = data.get('target_dna', []) or []
    anonymize = bool(data.get('anonymize', False))

    filtered = []
    for c in INSTITUTIONAL_CANDIDATES:
        if c['gpa'] < min_gpa:
            continue
        if target_dna and not any(tag in c['dna'] for tag in target_dna):
            continue
        cand = c.copy()
        cand['fit_score'] = _score_candidate(c, min_gpa, target_dna)
        if anonymize:
            cand['name'] = f"Candidate #{c['id']}"
        filtered.append(cand)

    filtered.sort(key=lambda c: c['fit_score'], reverse=True)
    return jsonify({"candidates": filtered})


# ---------------------------------------------------------------------------
# Institution outreach strategy (AI-generated)
# ---------------------------------------------------------------------------
@app.route('/api/advisor/outreach', methods=['POST'])
def advisor_outreach():
    data = request.json or {}
    try:
        min_gpa = _clamp(float(data.get('min_gpa', 3.5) or 3.5), 0.0, 4.0)
    except (ValueError, TypeError):
        min_gpa = 3.5

    target_dna = data.get('target_dna', []) or []
    dataset_context = (
        f"Active institutional candidate pool: {len(INSTITUTIONAL_CANDIDATES)} tracked applicants "
        f"across partner universities including MIT, Stanford, and Caltech."
    )

    prompt = (
        f"Context: You are a higher-education admissions strategy advisor.\n"
        f"{dataset_context}\n"
        f"Recruitment criteria: minimum GPA {min_gpa}/4.0, target profile traits: "
        f"{', '.join(target_dna) if target_dna else 'all tracks'}.\n"
        f"Task: In exactly 3 objective, professional sentences, outline a data-driven outreach strategy to "
        f"capture high-yield candidates matching this profile."
    )

    if not groq_client:
        strategy = (
            f"Prioritize outreach to secondary schools with strong concentrations in "
            f"{', '.join(target_dna) if target_dna else 'well-rounded'} programs, and lead with early "
            f"engagement touchpoints such as info sessions and mentorship pairings. Layer in "
            f"scholarship and research-placement incentives to lift yield among candidates above the "
            f"{min_gpa} GPA threshold. Track conversion by traits to reallocate spend toward the "
            f"highest-yield recruiting channels each cycle."
        )
    else:
        try:
            completion = groq_client.chat.completions.create(
                model=GROQ_MODEL_ID,
                messages=[
                    {"role": "system", "content": f"You advise university admissions teams. {dataset_context}"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=220,
            )
            strategy = completion.choices[0].message.content.strip()
        except Exception as e:
            strategy = f"Outreach strategy generation is temporarily unavailable ({e})."

    return jsonify({"strategy": strategy})


# ---------------------------------------------------------------------------
# Auth
#
# When SUPABASE_URL / SUPABASE_ANON_KEY are configured, real accounts are
# created and verified through Supabase Auth. Without those env vars the app
# runs in "demo mode": sign in/up simply issues a signed session cookie so
# the UI is fully functional out of the box, with no external dependency.
# ---------------------------------------------------------------------------
@app.route('/api/auth/signup', methods=['POST'])
def auth_signup():
    data = request.json or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not name or not email or len(password) < 6:
        return jsonify({"error": "Name, a valid email, and a 6+ character password are required."}), 400

    if supabase_client:
        try:
            result = supabase_client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"name": name}},
            })
            if not result.user:
                return jsonify({"error": "Sign up failed."}), 400
            user = {"id": result.user.id, "name": name, "email": email}
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        user = {"id": f"demo-{email}", "name": name, "email": email}

    session['user'] = user
    return jsonify({"user": user})


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.json or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    if supabase_client:
        try:
            result = supabase_client.auth.sign_in_with_password({"email": email, "password": password})
            if not result.user:
                return jsonify({"error": "Invalid credentials."}), 401
            name = (result.user.user_metadata or {}).get('name', email.split('@')[0])
            user = {"id": result.user.id, "name": name, "email": email}
        except Exception:
            return jsonify({"error": "Invalid credentials."}), 401
    else:
        user = {"id": f"demo-{email}", "name": email.split('@')[0].title(), "email": email}

    session['user'] = user
    return jsonify({"user": user})


@app.route('/api/auth/google', methods=['POST'])
def auth_google():
    data = request.json or {}
    credential = data.get('credential')

    if credential and GOOGLE_CLIENT_ID and id_token and google_requests:
        try:
            info = id_token.verify_oauth2_token(
                credential, google_requests.Request(), GOOGLE_CLIENT_ID
            )
            user = {
                "id": info.get('sub'),
                "name": info.get('name', info.get('email', 'Google User')),
                "email": info.get('email'),
                "picture": info.get('picture'),
            }
        except Exception as e:
            return jsonify({"error": f"Google sign-in verification failed: {e}"}), 401
    else:
        # No credential / no configured Google client -> demo fallback used
        # by the "Continue with Google" button when the SDK can't load.
        user = {"id": "demo-google-user", "name": "Demo Student", "email": "demo.student@unimatch.dev"}

    session['user'] = user
    return jsonify({"user": user})


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    session.pop('user', None)
    return jsonify({"ok": True})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
