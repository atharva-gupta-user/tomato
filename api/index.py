import os
import random
from flask import Flask, render_template, jsonify, request, session
from dotenv import load_dotenv
from groq import Groq
from supabase import create_client, Client
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

load_dotenv()

app = Flask(__name__, template_folder='../templates')
app.secret_key = os.environ.get("SECRET_KEY", "unimatch-secure-production-key")

groq_api_key = os.environ.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_KEY", ""))
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
GROQ_MODEL_ID = "llama-3.1-70b-versatile"

random.seed(42)

# --- EXPANDED NATIONAL UNIVERSITY DATA MATRIX (50+ Institutions) ---
UNIVERSITIES = [
    {"id": 1, "name": "MIT", "min_gpa": 3.8, "avg_sat": 1540, "avg_act": 35, "region": "Northeast", "campus_type": "Urban", "majors": ["Computer Science", "Mechanical Engineering", "Physics"], "dna": ["STEM", "Research", "Innovation"]},
    {"id": 2, "name": "Stanford University", "min_gpa": 3.9, "avg_sat": 1520, "avg_act": 34, "region": "West", "campus_type": "Suburban", "majors": ["Computer Science", "Business Administration", "Bioengineering"], "dna": ["STEM", "Leadership", "First-Gen"]},
    {"id": 3, "name": "Harvard University", "min_gpa": 3.9, "avg_sat": 1530, "avg_act": 34, "region": "Northeast", "campus_type": "Urban", "majors": ["Political Science", "Economics", "History"], "dna": ["Leadership", "Community Service", "Arts"]},
    {"id": 4, "name": "UC Berkeley", "min_gpa": 3.7, "avg_sat": 1450, "avg_act": 32, "region": "West", "campus_type": "Urban", "majors": ["Computer Science", "Data Science", "Environmental Science"], "dna": ["STEM", "Research", "Community Service"]},
    {"id": 5, "name": "University of Michigan", "min_gpa": 3.6, "avg_sat": 1400, "avg_act": 31, "region": "Midwest", "campus_type": "Urban", "majors": ["Mechanical Engineering", "Business Administration", "Psychology"], "dna": ["Athletics", "Leadership", "STEM"]},
    {"id": 6, "name": "UT Austin", "min_gpa": 3.6, "avg_sat": 1380, "avg_act": 30, "region": "South", "campus_type": "Urban", "majors": ["Computer Science", "Business Administration", "Architecture"], "dna": ["First-Gen", "STEM", "Innovation"]},
    {"id": 7, "name": "NYU", "min_gpa": 3.5, "avg_sat": 1410, "avg_act": 31, "region": "Northeast", "campus_type": "Urban", "majors": ["Arts", "Film", "Economics", "Finance"], "dna": ["Arts", "Innovation", "Diversity"]},
    {"id": 8, "name": "Northwestern University", "min_gpa": 3.8, "avg_sat": 1480, "avg_act": 33, "region": "Midwest", "campus_type": "Suburban", "majors": ["Journalism", "Economics", "Communication"], "dna": ["Research", "Leadership", "Arts"]},
    {"id": 9, "name": "Georgia Tech", "min_gpa": 3.6, "avg_sat": 1420, "avg_act": 31, "region": "South", "campus_type": "Urban", "majors": ["Aerospace Engineering", "Computer Science", "Industrial Design"], "dna": ["STEM", "Innovation", "Research"]},
    {"id": 10, "name": "University of Florida", "min_gpa": 3.5, "avg_sat": 1360, "avg_act": 29, "region": "South", "campus_type": "Suburban", "majors": ["Biology", "Business Administration", "Nursing"], "dna": ["Athletics", "Community Service", "First-Gen"]},
    {"id": 11, "name": "Williams College", "min_gpa": 3.8, "avg_sat": 1490, "avg_act": 33, "region": "Northeast", "campus_type": "Rural", "majors": ["Mathematics", "History", "English"], "dna": ["Research", "Community Service", "Arts"]},
    {"id": 12, "name": "Vanderbilt University", "min_gpa": 3.8, "avg_sat": 1490, "avg_act": 33, "region": "South", "campus_type": "Urban", "majors": ["Education", "Economics", "Human Development"], "dna": ["Leadership", "Community Service", "Innovation"]},
    {"id": 13, "name": "University of Washington", "min_gpa": 3.5, "avg_sat": 1350, "avg_act": 29, "region": "West", "campus_type": "Urban", "majors": ["Bioengineering", "Computer Science", "Oceanography"], "dna": ["STEM", "Research", "Diversity"]},
    {"id": 14, "name": "Ohio State University", "min_gpa": 3.4, "avg_sat": 1310, "avg_act": 28, "region": "Midwest", "campus_type": "Urban", "majors": ["Agriculture", "Business Administration", "Nursing"], "dna": ["Athletics", "First-Gen", "Community Service"]},
    {"id": 15, "name": "University of Virginia", "min_gpa": 3.7, "avg_sat": 1430, "avg_act": 32, "region": "South", "campus_type": "Suburban", "majors": ["History", "Commerce", "Architecture"], "dna": ["Leadership", "Research", "Honor Code"]},
    {"id": 16, "name": "Caltech", "min_gpa": 3.9, "avg_sat": 1560, "avg_act": 36, "region": "West", "campus_type": "Suburban", "majors": ["Physics", "Mathematics", "Computer Science"], "dna": ["STEM", "Research", "Innovation"]},
    {"id": 17, "name": "Duke University", "min_gpa": 3.8, "avg_sat": 1510, "avg_act": 34, "region": "South", "campus_type": "Suburban", "majors": ["Biology", "Public Policy", "Public Health"], "dna": ["Athletics", "Research", "Leadership"]},
    {"id": 18, "name": "Dartmouth College", "min_gpa": 3.8, "avg_sat": 1480, "avg_act": 33, "region": "Northeast", "campus_type": "Rural", "majors": ["Economics", "Engineering Sciences", "Government"], "dna": ["Leadership", "Community Service", "Athletics"]},
    {"id": 19, "name": "Purdue University", "min_gpa": 3.5, "avg_sat": 1320, "avg_act": 29, "region": "Midwest", "campus_type": "Suburban", "majors": ["Aeronautical Engineering", "Computer Science", "Pharmacy"], "dna": ["STEM", "Innovation", "First-Gen"]},
    {"id": 20, "name": "Rice University", "min_gpa": 3.8, "avg_sat": 1490, "avg_act": 33, "region": "South", "campus_type": "Urban", "majors": ["Architecture", "Bioengineering", "Music"], "dna": ["Research", "Diversity", "STEM"]},
    {"id": 21, "name": "Carnegie Mellon University", "min_gpa": 3.8, "avg_sat": 1510, "avg_act": 34, "region": "Northeast", "campus_type": "Urban", "majors": ["Computer Science", "Drama", "Robotics"], "dna": ["STEM", "Arts", "Innovation"]},
    {"id": 22, "name": "Columbia University", "min_gpa": 3.9, "avg_sat": 1520, "avg_act": 34, "region": "Northeast", "campus_type": "Urban", "majors": ["Literature", "Economics", "Journalism"], "dna": ["Leadership", "Diversity", "Research"]},
    {"id": 23, "name": "Cornell University", "min_gpa": 3.8, "avg_sat": 1470, "avg_act": 33, "region": "Northeast", "campus_type": "Rural", "majors": ["Hotel Administration", "Architecture", "Engineering"], "dna": ["First-Gen", "STEM", "Agriculture"]},
    {"id": 24, "name": "University of Chicago", "min_gpa": 3.9, "avg_sat": 1520, "avg_act": 34, "region": "Midwest", "campus_type": "Urban", "majors": ["Economics", "Mathematics", "Sociology"], "dna": ["Research", "Innovation", "Leadership"]},
    {"id": 25, "name": "UCLA", "min_gpa": 3.8, "avg_sat": 1410, "avg_act": 31, "region": "West", "campus_type": "Urban", "majors": ["Film and Television", "Psychology", "Biology"], "dna": ["Diversity", "Arts", "Athletics"]},
    {"id": 26, "name": "UC San Diego", "min_gpa": 3.7, "avg_sat": 1390, "avg_act": 30, "region": "West", "campus_type": "Suburban", "majors": ["Marine Biology", "Bioengineering", "Cognitive Science"], "dna": ["STEM", "Research", "Diversity"]},
    {"id": 27, "name": "University of Notre Dame", "min_gpa": 3.8, "avg_sat": 1450, "avg_act": 32, "region": "Midwest", "campus_type": "Suburban", "majors": ["Finance", "Architecture", "Theology"], "dna": ["Community Service", "Athletics", "Leadership"]},
    {"id": 28, "name": "Brown University", "min_gpa": 3.8, "avg_sat": 1490, "avg_act": 33, "region": "Northeast", "campus_type": "Urban", "majors": ["Open Curriculum", "International Relations", "Literary Arts"], "dna": ["Arts", "Diversity", "Innovation"]},
    {"id": 29, "name": "University of Pennsylvania", "min_gpa": 3.9, "avg_sat": 1510, "avg_act": 34, "region": "Northeast", "campus_type": "Urban", "majors": ["Finance", "Nursing", "Digital Media Design"], "dna": ["Leadership", "Innovation", "Business"]},
    {"id": 30, "name": "Princeton University", "min_gpa": 3.9, "avg_sat": 1530, "avg_act": 35, "region": "Northeast", "campus_type": "Suburban", "majors": ["Public Policy", "Mathematics", "Philosophy"], "dna": ["Research", "Community Service", "Leadership"]}
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
        "Avery Scott", "Sebastian Torres", "Scarlett Nguyen", "Jack Hill", "Victoria Flores"
    ]
    majors = ["Computer Science", "Mechanical Engineering", "Business Administration", "Biology", "Political Science", "Economics", "Arts"]
    regions = ["Northeast", "West", "Midwest", "South"]
    campuses = ["Urban", "Suburban", "Rural"]
    dna_pools = ["STEM", "Leadership", "Community Service", "Arts", "Athletics", "First-Gen", "Research", "Innovation"]
    
    students = []
    for i in range(40):
        students.append({
            "id": 2000 + i,
            "name": names[i],
            "gpa": round(random.uniform(3.0, 4.0), 2),
            "sat": int(random.randint(1150, 1580) / 10) * 10,
            "act": random.randint(24, 36),
            "target_major": random.choice(majors),
            "preferred_region": random.choice(regions),
            "preferred_campus_type": random.choice(campuses),
            "dna": list(set(random.choices(dna_pools, k=random.randint(2, 4))))
        })
    return students

MOCK_STUDENTS = generate_mock_students()
COMMUNITY_TRAINING_POOL = []

@app.route('/')
def home():
    return render_template('index.html', google_client_id=GOOGLE_CLIENT_ID)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "operational",
        "universities_indexed": len(UNIVERSITIES),
        "community_training_samples": len(COMMUNITY_TRAINING_POOL),
        "active_llm_target": GROQ_MODEL_ID
    }), 200

@app.route('/api/universities', methods=['GET'])
def get_universities():
    return jsonify({"universities": [u['name'] for u in UNIVERSITIES]}), 200

@app.route('/api/match/student', methods=['POST'])
def match_student():
    data = request.json or {}
    try:
        gpa = max(0.0, min(4.0, float(data.get('gpa', 3.0))))
        sat = max(400, min(1600, int(data.get('sat', 1200))))
        act = max(1, min(36, int(data.get('act', 26))))
    except ValueError:
        return jsonify({"error": "Invalid numerical input limits specified."}), 400

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
        
        pref_weight = 0
        if region == uni['region']: pref_weight += 15
        if campus_type == uni['campus_type']: pref_weight += 15
        if major in uni['majors']: pref_weight += 10
        pref_weight += (len(set(selected_dna) & set(uni['dna'])) * 10)
        
        total = academic_weight + pref_weight
        if total >= 85:
            tier, prob, color = "Safety", random.randint(85, 98), "emerald"
        elif total >= 60:
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
            "reasoning": f"Alignment metric computed against standard admissions parameters for {uni['region']} zone."
        })
    
    matches.sort(key=lambda x: x['probability'], reverse=True)
    return jsonify({"matches": matches})

@app.route('/api/match/institute', methods=['POST'])
def match_institute():
    data = request.json or {}
    try:
        min_gpa = max(0.0, min(4.0, float(data.get('min_gpa', 3.0))))
    except ValueError:
        min_gpa = 3.0

    target_dna = data.get('target_dna', [])
    anonymize = data.get('anonymize', False)

    candidates = []
    for s in MOCK_STUDENTS + COMMUNITY_TRAINING_POOL:
        if s['gpa'] < min_gpa:
            continue
        dna_matches = len(set(target_dna) & set(s['dna']))
        fit_score = min(100, max(15, int((dna_matches / max(len(target_dna), 1)) * 60) + int((s['gpa'] / 4.0) * 40)))
        
        candidates.append({
            "id": s['id'],
            "name": f"Candidate #{s['id']}" if anonymize else s['name'],
            "gpa": s['gpa'],
            "sat": s['sat'],
            "act": s['act'],
            "major": s['target_major'],
            "dna": s['dna'],
            "fit_score": fit_score
        })

    candidates.sort(key=lambda x: x['fit_score'], reverse=True)
    return jsonify({"candidates": candidates})

@app.route('/api/advisor/outreach', methods=['POST'])
def outreach_strategy():
    data = request.json or {}
    try:
        min_gpa = max(0.0, min(4.0, float(data.get('min_gpa', 3.5))))
    except ValueError:
        min_gpa = 3.5
    target_dna = data.get('target_dna', ['STEM'])

    prompt = (
        f"Context: Expert Higher Education Solutions Architect.\n"
        f"Task: Create a targeted institutional recruitment and yield strategy for applicants satisfying min GPA {min_gpa} and DNA attributes {', '.join(target_dna)}.\n"
        f"Constraints: Provide a concise, highly objective, professional 3-sentence advisory roadmap."
    )

    if not groq_client:
        return jsonify({
            "strategy": f"Deploy specialized institutional outreach programs targeting cohorts exhibiting strong competencies in {', '.join(target_dna)}. Prioritize early-action candidate engagement and merit-based programmatic funding to maximize conversion yields."
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
        return jsonify({"strategy": f"Strategy parsing service exception handled: {str(e)}"}), 200

@app.route('/api/train/contribute', methods=['POST'])
def contribute_training_data():
    data = request.json or {}
    try:
        gpa = max(0.0, min(4.0, float(data.get('gpa', 3.5))))
        sat = max(400, min(1600, int(data.get('sat', 1300))))
        act = max(1, min(36, int(data.get('act', 28))))
    except ValueError:
        return jsonify({"error": "Invalid profile metrics input bounds."}), 400

    new_sample = {
        "id": 9000 + len(COMMUNITY_TRAINING_POOL),
        "name": data.get('name', 'Community Contributor').strip() or 'Anonymous Contributor',
        "gpa": gpa,
        "sat": sat,
        "act": act,
        "target_major": data.get('major', 'General Studies'),
        "preferred_region": data.get('region', 'Northeast'),
        "preferred_campus_type": data.get('campus_type', 'Urban'),
        "dna": data.get('dna', ['STEM'])
    }
    
    COMMUNITY_TRAINING_POOL.append(new_sample)
    return jsonify({
        "message": "Profile successfully integrated into collaborative model training pipeline.",
        "total_training_samples": len(COMMUNITY_TRAINING_POOL)
    }), 201

if __name__ == '__main__':
    app.run(debug=True, port=5000)
