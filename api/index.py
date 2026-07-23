import os
import random
from flask import Flask, render_template, jsonify, request, session
from dotenv import load_dotenv
from groq import Groq
from supabase import create_client, Client
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Initialize application environmental constraints
load_dotenv()

app = Flask(__name__, template_folder='../templates')
app.secret_key = os.environ.get("SECRET_KEY", "unimatch-secret-key-2026")

# Initialize Groq client with global API key validation
groq_api_key = os.environ.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

# Initialize Supabase and Google Auth configurations
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_KEY", ""))
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# Validated Production Groq Inference Target
GROQ_MODEL_ID = "llama-3.1-70b-versatile"

# --- MOCK DATA ENGINE SEED MATRIX ---
random.seed(42)

UNIVERSITIES = [
    {"id": 1, "name": "MIT", "min_gpa": 3.8, "avg_sat": 1540, "avg_act": 35, "region": "Northeast", "campus_type": "Urban", "majors": ["Computer Science", "Mechanical Engineering"], "dna": ["STEM", "Research", "Innovation"]},
    {"id": 2, "name": "Stanford University", "min_gpa": 3.9, "avg_sat": 1520, "avg_act": 34, "region": "West", "campus_type": "Suburban", "majors": ["Computer Science", "Business Administration", "Bioengineering"], "dna": ["STEM", "Leadership", "First-Gen"]},
    {"id": 3, "name": "Harvard University", "min_gpa": 3.9, "avg_sat": 1530, "avg_act": 34, "region": "Northeast", "campus_type": "Urban", "majors": ["Political Science", "Economics", "History"], "dna": ["Leadership", "Community Service", "Arts"]},
    {"id": 4, "name": "UC Berkeley", "min_gpa": 3.7, "avg_sat": 1450, "avg_act": 32, "region": "West", "campus_type": "Urban", "majors": ["Computer Science", "Data Science", "Environmental Science"], "dna": ["STEM", "Research", "Community Service"]},
    {"id": 5, "name": "University of Michigan", "min_gpa": 3.6, "avg_sat": 1400, "avg_act": 31, "region": "Midwest", "campus_type": "Urban", "majors": ["Mechanical Engineering", "Business Administration"], "dna": ["Athletics", "Leadership", "STEM"]},
    {"id": 6, "name": "UT Austin", "min_gpa": 3.6, "avg_sat": 1380, "avg_act": 30, "region": "South", "campus_type": "Urban", "majors": ["Computer Science", "Business Administration"], "dna": ["First-Gen", "STEM", "Innovation"]},
    {"id": 7, "name": "NYU", "min_gpa": 3.5, "avg_sat": 1410, "avg_act": 31, "region": "Northeast", "campus_type": "Urban", "majors": ["Arts", "Film", "Economics"], "dna": ["Arts", "Innovation", "Diversity"]},
    {"id": 8, "name": "Northwestern University", "min_gpa": 3.8, "avg_sat": 1480, "avg_act": 33, "region": "Midwest", "campus_type": "Suburban", "majors": ["Journalism", "Economics", "Communication"], "dna": ["Research", "Leadership", "Arts"]},
    {"id": 9, "name": "Georgia Tech", "min_gpa": 3.6, "avg_sat": 1420, "avg_act": 31, "region": "South", "campus_type": "Urban", "majors": ["Aerospace Engineering", "Computer Science"], "dna": ["STEM", "Innovation", "Research"]},
    {"id": 10, "name": "University of Florida", "min_gpa": 3.5, "avg_sat": 1360, "avg_act": 29, "region": "South", "campus_type": "Suburban", "majors": ["Biology", "Business Administration"], "dna": ["Athletics", "Community Service", "First-Gen"]},
    {"id": 11, "name": "Williams College", "min_gpa": 3.8, "avg_sat": 1490, "avg_act": 33, "region": "Northeast", "campus_type": "Rural", "majors": ["Mathematics", "History"], "dna": ["Research", "Community Service", "Arts"]},
    {"id": 12, "name": "Vanderbilt University", "min_gpa": 3.8, "avg_sat": 1490, "avg_act": 33, "region": "South", "campus_type": "Urban", "majors": ["Education", "Economics"], "dna": ["Leadership", "Community Service", "Innovation"]},
    {"id": 13, "name": "University of Washington", "min_gpa": 3.5, "avg_sat": 1350, "avg_act": 29, "region": "West", "campus_type": "Urban", "majors": ["Bioengineering", "Computer Science"], "dna": ["STEM", "Research", "Diversity"]},
    {"id": 14, "name": "Ohio State University", "min_gpa": 3.4, "avg_sat": 1310, "avg_act": 28, "region": "Midwest", "campus_type": "Urban", "majors": ["Agriculture", "Business Administration"], "dna": ["Athletics", "First-Gen", "Community Service"]},
    {"id": 15, "name": "University of Virginia", "min_gpa": 3.7, "avg_sat": 1430, "avg_act": 32, "region": "South", "campus_type": "Suburban", "majors": ["History", "Commerce"], "dna": ["Leadership", "Research", "Honor Code"]},
    {"id": 16, "name": "Caltech", "min_gpa": 3.9, "avg_sat": 1560, "avg_act": 36, "region": "West", "campus_type": "Suburban", "majors": ["Physics", "Mathematics", "Computer Science"], "dna": ["STEM", "Research", "Innovation"]},
    {"id": 17, "name": "Duke University", "min_gpa": 3.8, "avg_sat": 1510, "avg_act": 34, "region": "South", "campus_type": "Suburban", "majors": ["Biology", "Public Policy"], "dna": ["Athletics", "Research", "Leadership"]},
    {"id": 18, "name": "Dartmouth College", "min_gpa": 3.8, "avg_sat": 1480, "avg_act": 33, "region": "Northeast", "campus_type": "Rural", "majors": ["Economics", "Engineering Sciences"], "dna": ["Leadership", "Community Service", "Athletics"]},
    {"id": 19, "name": "Purdue University", "min_gpa": 3.5, "avg_sat": 1320, "avg_act": 29, "region": "Midwest", "campus_type": "Suburban", "majors": ["Aeronautical Engineering", "Computer Science"], "dna": ["STEM", "Innovation", "First-Gen"]},
    {"id": 20, "name": "Rice University", "min_gpa": 3.8, "avg_sat": 1490, "avg_act": 33, "region": "South", "campus_type": "Urban", "majors": ["Architecture", "Bioengineering"], "dna": ["Research", "Diversity", "STEM"]}
]

def generate_mock_students():
    names = [
        "Liam Smith", "Olivia Johnson", "Noah Williams", "Emma Brown", "Oliver Jones",
        "Ava Garcia", "Elijah Miller", "Charlotte Davis", "William Rodriguez", "Sophia Martinez",
        "James Hernandez", "Amelia Lopez", "Benjamin Gonzalez", "Isabella Wilson", "Lucas Anderson",
        "Mia Thomas", "Henry Taylor", "Evelyn Moore", "Alexander Jackson", "Harper Martin",
        "Mason Lee", "Camila Perez", "Michael Thompson", "Gianna White", "Ethan Harris",
        "Abigail Sanchez", "Daniel Clark", "Luna Ramirez", "Jacob Lewis", "Ella Robinson",
        "Logan Walker", "Elizabeth Young", "Jackson Allen", "Sofia King", "Levi Wright",
        "Avery Scott", "Sebastian Torres", "Scarlett Nguyen", "Jack Hill", "Victoria Flores",
        "Aiden Green", "Madison Adams", "Owen Nelson", "Layla Baker", "Samuel Hall",
        "Chloe Rivera", "Matthew Campbell", "Arlo Mitchell", "David Carter", "Carter Roberts"
    ]
    majors = ["Computer Science", "Mechanical Engineering", "Business Administration", "Biology", "Political Science", "Economics", "Arts"]
    regions = ["Northeast", "West", "Midwest", "South"]
    campuses = ["Urban", "Suburban", "Rural"]
    dna_pools = ["STEM", "Leadership", "Community Service", "Arts", "Athletics", "First-Gen", "Research", "Innovation"]
    
    students = []
    for i in range(50):
        gpa = round(random.uniform(3.0, 4.0), 2)
        sat = int(random.randint(1100, 1600) / 10) * 10
        act = random.randint(22, 36)
        student_dna = list(set(random.choices(dna_pools, k=random.randint(2, 4))))
        
        students.append({
            "id": 1482 + i,
            "name": names[i],
            "gpa": gpa,
            "sat": sat,
            "act": act,
            "target_major": random.choice(majors),
            "preferred_region": random.choice(regions),
            "preferred_campus_type": random.choice(campuses),
            "dna": student_dna
        })
    return students

MOCK_STUDENTS = generate_mock_students()

@app.route('/')
def home():
    return render_template('index.html', google_client_id=GOOGLE_CLIENT_ID)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "operational",
        "localization": "US Higher-Ed Framework (4.0 Scale / SAT / ACT)",
        "active_llm_target": GROQ_MODEL_ID,
        "api_key_configured": bool(groq_client),
        "supabase_configured": bool(supabase_client),
        "google_auth_configured": bool(GOOGLE_CLIENT_ID)
    }), 200

# --- AUTHENTICATION ROUTE HANDLERS ---

@app.route('/api/auth/signup', methods=['POST'])
def auth_signup():
    """Handles user sign-up using Supabase email/password auth."""
    data = request.json or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    name = data.get('name', '').strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    if not supabase_client:
        return jsonify({
            "message": "Sign up successful (Simulated Mode - configure SUPABASE_URL & SUPABASE_ANON_KEY for live DB).",
            "user": {
                "id": f"usr_{random.randint(1000, 9999)}",
                "email": email,
                "name": name or email.split('@')[0]
            }
        }), 201

    try:
        response = supabase_client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": name
                }
            }
        })
        user = response.user
        session_data = response.session
        return jsonify({
            "message": "Registration successful.",
            "user": {
                "id": user.id if user else None,
                "email": user.email if user else email,
                "name": name or (user.email.split('@')[0] if user else email)
            },
            "access_token": session_data.access_token if session_data else None
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Handles user sign-in using Supabase email/password auth."""
    data = request.json or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    if not supabase_client:
        return jsonify({
            "message": "Login successful (Simulated Mode - configure SUPABASE_URL & SUPABASE_ANON_KEY for live DB).",
            "user": {
                "id": f"usr_{random.randint(1000, 9999)}",
                "email": email,
                "name": email.split('@')[0]
            },
            "access_token": "simulated_access_token_xyz"
        }), 200

    try:
        response = supabase_client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        user = response.user
        session_data = response.session
        return jsonify({
            "message": "Login successful.",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.user_metadata.get("full_name") or user.email.split('@')[0]
            },
            "access_token": session_data.access_token if session_data else None
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route('/api/auth/google', methods=['POST'])
def auth_google():
    """Handles Google OAuth / Google Cloud Console ID token authentication."""
    data = request.json or {}
    token = data.get('token') or data.get('credential')

    if not token:
        return jsonify({"error": "Google ID token or credential is required."}), 400

    if not GOOGLE_CLIENT_ID:
        # Simulated mode for local/testing environments without a configured Google Client ID
        return jsonify({
            "message": "Google authentication successful (Simulated Mode - configure GOOGLE_CLIENT_ID for live auth).",
            "user": {
                "id": f"google_usr_{random.randint(1000, 9999)}",
                "email": "google.user@example.com",
                "name": "Google User",
                "picture": "https://lh3.googleusercontent.com/a/default-user"
            }
        }), 200

    # Validate the ID token against the configured Google Client ID
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
    except Exception as e:
        return jsonify({"error": f"Google token verification failed: {str(e)}"}), 401

    user_info = {
        "id": idinfo.get("sub"),
        "email": idinfo.get("email"),
        "name": idinfo.get("name"),
        "picture": idinfo.get("picture")
    }

    # Sync with Supabase if configured; fall back to the verified Google identity if this fails
    if supabase_client:
        try:
            res = supabase_client.auth.sign_in_with_id_token({
                "provider": "google",
                "token": token
            })
            if res.user:
                user_info = {
                    "id": res.user.id,
                    "email": res.user.email,
                    "name": res.user.user_metadata.get("full_name") or res.user.user_metadata.get("name") or res.user.email.split('@')[0],
                    "picture": res.user.user_metadata.get("avatar_url") or user_info.get("picture")
                }
        except Exception:
            pass

    return jsonify({
        "message": "Google authentication successful.",
        "user": user_info
    }), 200

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Handles user logout."""
    if supabase_client:
        try:
            supabase_client.auth.sign_out()
        except Exception:
            pass
    return jsonify({"message": "Logged out successfully."}), 200

@app.route('/api/auth/user', methods=['GET'])
def get_auth_user():
    """Returns current user details based on session or Authorization token."""
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None

    if token and supabase_client:
        try:
            res = supabase_client.auth.get_user(token)
            if res.user:
                return jsonify({
                    "authenticated": True,
                    "user": {
                        "id": res.user.id,
                        "email": res.user.email,
                        "name": res.user.user_metadata.get("full_name") or res.user.email.split('@')[0]
                    }
                }), 200
        except Exception:
            pass

    return jsonify({"authenticated": False, "user": None}), 200

# --- CORE DOMAIN API ENDPOINTS ---

@app.route('/api/universities', methods=['GET'])
def get_universities():
    """Returns a list of all raw university names."""
    return jsonify({
        "universities": [uni['name'] for uni in UNIVERSITIES]
    }), 200

@app.route('/api/match/student', methods=['POST'])
def match_student():
    data = request.json or {}
    gpa = float(data.get('gpa', 3.0))
    sat = int(data.get('sat', 1200))
    act = int(data.get('act', 26))
    major = data.get('major', '')
    region = data.get('region', '')
    campus_type = data.get('campus_type', '')
    selected_dna = data.get('dna', [])

    matches = []
    for uni in UNIVERSITIES:
        academic_weight = 0
        if gpa >= uni['min_gpa']: academic_weight += 40
        if sat >= uni['avg_sat']: academic_weight += 30
        if act >= uni['avg_act']: academic_weight += 30
        
        preference_weight = 0
        if region == uni['region']: preference_weight += 15
        if campus_type == uni['campus_type']: preference_weight += 15
        if major in uni['majors']: preference_weight += 10
        
        dna_overlap = len(set(selected_dna) & set(uni['dna']))
        preference_weight += (dna_overlap * 10)
        
        total_score = academic_weight + preference_weight
        
        if total_score >= 85:
            tier, prob, color = "Safety", random.randint(85, 98), "emerald"
        elif total_score >= 60:
            tier, prob, color = "Target", random.randint(55, 84), "amber"
        else:
            tier, prob, color = "Reach", random.randint(10, 54), "rose"

        matches.append({
            "university": uni['name'],
            "tier": tier,
            "probability": prob,
            "color": color,
            "region": uni['region'],
            "campus_type": uni['campus_type'],
            "dna_tags": uni['dna'],
            "reasoning": f"Academic thresholds establish profile alignment for the {uni['region']} market framework."
        })
    
    matches.sort(key=lambda x: x['probability'], reverse=True)
    return jsonify({"matches": matches})

@app.route('/api/match/institute', methods=['POST'])
def match_institute():
    data = request.json or {}
    min_gpa = float(data.get('min_gpa', 3.0))
    target_dna = data.get('target_dna', [])
    anonymize = data.get('anonymize', False)

    candidates = []
    for s in MOCK_STUDENTS:
        if s['gpa'] < min_gpa:
            continue
            
        dna_matches = len(set(target_dna) & set(s['dna']))
        fit_score = int((dna_matches / max(len(target_dna), 1)) * 60) + int((s['gpa'] / 4.0) * 40)
        fit_score = min(100, max(15, fit_score))
        
        display_name = f"Applicant #{s['id']}" if anonymize else s['name']
        
        candidates.append({
            "id": s['id'],
            "name": display_name,
            "gpa": s['gpa'],
            "sat": s['sat'],
            "act": s['act'],
            "major": s['target_major'],
            "dna": s['dna'],
            "fit_score": fit_score
        })

    candidates.sort(key=lambda x: x['fit_score'], reverse=True)
    return jsonify({"candidates": candidates})

@app.route('/api/advisor/profile', methods=['POST'])
def profile_optimizer():
    """Generates personalized tactical advice using the active Groq inference engine."""
    data = request.json or {}
    university = data.get('university', 'Target Institution')
    tier = data.get('tier', 'Target')
    gpa = data.get('gpa', 3.5)
    sat = data.get('sat', 1300)
    act = data.get('act', 28)
    dna = data.get('dna', [])
    
    prompt = (
        f"Context: You are the UniMatch AI Higher-Education Profile Optimizer advisor.\n"
        f"Task: Evaluate this student profile applying to {university} (categorized as a {tier} match).\n"
        f"Student Metrics: Unweighted GPA: {gpa}/4.0, SAT: {sat}, ACT: {act}, Profile Archetypes: {', '.join(dna)}.\n"
        f"Constraints: Provide strict, hyper-specific contextual advice tailored to the US university landscape. "
        f"Explicitly quantify how adding leadership or altering strategic targets impacts acceptance chances. "
        f"Keep the output professional, actionable, structured, and limited to a maximum of 3 sentences."
    )

    if not groq_client:
        # High-Fidelity local fallback simulation if no environmental key present
        return jsonify({
            "advice": f"Your current metrics match the baseline, but your profile lacks dedicated alignment with institutional targets at {university}. Adding a regional leadership role or an advanced independent research project could boost your relative target baseline by an estimated 12% to 15%."
        })

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200
        )
        return jsonify({"advice": completion.choices[0].message.content.strip()})
    except Exception as e:
        return jsonify({"advice": f"Inference pipeline execution error: {str(e)}"}), 500

@app.route('/api/advisor/predict', methods=['POST'])
def college_predictor():
    """Evaluates student compatibility directly against a chosen college using continuous proportional evaluation."""
    data = request.json or {}
    uni_name = data.get('university', '')
    gpa = float(data.get('gpa', 3.0))
    sat = int(data.get('sat', 1200))
    act = int(data.get('act', 26))
    major = data.get('major', '')
    selected_dna = data.get('dna', [])

    uni = next((u for u in UNIVERSITIES if u['name'] == uni_name), None)
    if not uni:
        return jsonify({"error": "Selected university parameters are unavailable."}), 404

    strengths = []
    weaknesses = []

    # Calculate proportional dynamic scoring to prevent rigid steps like 50% or 100%
    gpa_ratio = min(1.15, gpa / uni['min_gpa']) if uni['min_gpa'] else 1.0
    gpa_score = min(40.0, gpa_ratio * 40.0)

    sat_ratio = min(1.15, sat / uni['avg_sat']) if uni['avg_sat'] else 1.0
    sat_score = min(30.0, sat_ratio * 30.0)

    act_ratio = min(1.15, act / uni['avg_act']) if uni['avg_act'] else 1.0
    act_score = min(30.0, act_ratio * 30.0)

    # Strengths and Weaknesses Evaluation (Qualitative)
    if gpa >= uni['min_gpa']:
        strengths.append(f"Unweighted GPA of {gpa} fulfills or surpasses the minimum institutional metric requirement ({uni['min_gpa']}).")
    else:
        weaknesses.append(f"Your GPA ({gpa}) lags slightly behind the institutional historical target of {uni['min_gpa']}.")

    if sat >= uni['avg_sat']:
        strengths.append(f"Standardized SAT index of {sat} aligns favorably with the mid-50% student baseline of {uni['avg_sat']}.")
    else:
        weaknesses.append(f"Standardized SAT ({sat}) resides below the historical admitted mid-50% standard of {uni['avg_sat']}.")

    if act >= uni['avg_act']:
        strengths.append(f"Composite ACT assessment score of {act} satisfies the highly selective student baseline criteria ({uni['avg_act']}).")
    else:
        weaknesses.append(f"ACT evaluation ({act}) drops below the institution's historical student cohort average of {uni['avg_act']}.")

    # Pipeline/Major Weighting
    major_score = 10.0 if major in uni['majors'] else (gpa_ratio * 4.0)
    if major in uni['majors']:
        strengths.append(f"Your specialized interest in '{major}' directly overlaps signature pipelines.")
    else:
        weaknesses.append(f"Desired major specialization is not currently highlighted as a core signature major pipeline.")

    # Extracurricular DNA analysis (Up to 15 points)
    dna_overlap = list(set(selected_dna) & set(uni['dna']))
    dna_score = min(15.0, len(dna_overlap) * 5.0)
    
    if dna_overlap:
        strengths.append(f"Strong structural DNA alignment found across shared institutional priorities: {', '.join(dna_overlap)}.")
    else:
        weaknesses.append(f"Extracurricular footprint does not showcase core cultural alignments of {', '.join(uni['dna'])}.")

    # Normalize proportional summation to 0-100% boundary
    raw_score = gpa_score + sat_score + act_score + major_score + dna_score
    total_score = min(99, max(5, int((raw_score / 125.0) * 100)))

    if total_score >= 85:
        tier, likelihood, color = "Safety", "High Likelihood (85-98%)", "emerald"
    elif total_score >= 60:
        tier, likelihood, color = "Target", "Moderate Likelihood (55-84%)", "amber"
    else:
        tier, likelihood, color = "Reach", "Low Likelihood (10-54%)", "rose"

    prompt = (
        f"Context: You are the lead UniMatch AI Higher-Education Admissions Officer.\n"
        f"Task: Generate custom strategic recommendations for an applicant hoping to enter {uni['name']}.\n"
        f"Target University Parameters: Average SAT: {uni['avg_sat']}, Average ACT: {uni['avg_act']}, Core Archetype: {', '.join(uni['dna'])}.\n"
        f"Student Metrics: Unweighted GPA: {gpa}/4.0, SAT: {sat}, ACT: {act}, Major Field: {major}, DNA Strengths: {', '.join(selected_dna)}.\n"
        f"Constraints: Generate exactly two or three hyper-specific, extremely direct bullet points addressing strategic updates to make their application highly competitive. Avoid introductory setups or conversational summaries. Keep under 120 words total."
    )

    if not groq_client:
        # Static analytics recommendations based on parameters (High-Fidelity fallback)
        fallback_recs = [
            f"Target and cultivate additional DNA profile markers to closely map to {uni['name']}'s signature values: {', '.join(uni['dna'])}."
        ]
        if gpa < uni['min_gpa']:
            fallback_recs.append(f"Enhance standard classroom metrics closer to the {uni['min_gpa']} baseline via strong senior-year academic rigor.")
        if sat < uni['avg_sat'] or act < uni['avg_act']:
            fallback_recs.append(f"Incorporate advanced testing mock repetitions to target institutional medians ({uni['avg_sat']} SAT / {uni['avg_act']} ACT).")
        recommendations = "\n".join([f"• {r}" for r in fallback_recs])
    else:
        try:
            completion = groq_client.chat.completions.create(
                model=GROQ_MODEL_ID,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=220
            )
            recommendations = completion.choices[0].message.content.strip()
        except Exception:
            recommendations = f"• Focus on improving quantitative metrics to meet regional criteria.\n• Develop dedicated portfolios centering around core values: {', '.join(uni['dna'])}."

    return jsonify({
        "university": uni['name'],
        "match_score": total_score,
        "tier": tier,
        "likelihood": likelihood,
        "color": color,
        "strengths": strengths if strengths else ["Metrics meet default thresholds; no additional key strengths noted."],
        "weaknesses": weaknesses if weaknesses else ["Profile does not reveal major strategic deficiencies."],
        "recommendations": recommendations
    }), 200

@app.route('/api/advisor/outreach', methods=['POST'])
def outreach_strategy():
    """Builds an algorithmic recruitment summary outlining general strategy insights."""
    data = request.json or {}
    min_gpa = data.get('min_gpa', 3.5)
    target_dna = data.get('target_dna', [])
    
    prompt = (
        f"Context: You are an expert AI/ML Higher-Education Solutions Architect advising an admissions team.\n"
        f"Task: Create a highly analytical institutional outreach summary based on chosen parameters:\n"
        f"Recruitment Target Criteria: Minimum GPA: {min_gpa}/4.0, DNA Requirements: {', '.join(target_dna)}.\n"
        f"Constraints: Outline a data-driven strategy to capture high-yield candidates matching this DNA footprint "
        f"in the competitive US landscape. Keep the response completely objective, professional, and limited to 3 distinct sentences."
    )

    if not groq_client:
        return jsonify({
            "strategy": f"Deploy data-driven recruitment pipelines prioritizing secondary high schools with deep concentrations in {', '.join(target_dna)} tracks. Emphasize early engagement paradigms, specialized cohort scholarships, and institutional research allowances to shift yield metrics across the matching matrix."
        })

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=250
        )
        return jsonify({"strategy": completion.choices[0].message.content.strip()})
    except Exception as e:
        return jsonify({"strategy": f"Strategy parsing pipeline exception: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)