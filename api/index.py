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

# Validated Production Groq Inference Target (Updated to active active Llama-3.3-70b model)
GROQ_MODEL_ID = "llama-3.3-70b-versatile"

# --- MOCK DATA ENGINE SEED MATRIX ---
random.seed(42)

UNIVERSITIES = [
    {"id": 1, "name": "MIT", "min_gpa": 3.8, "avg_sat": 1520, "avg_act": 35, "tuition": "$58,000", "acceptance": "4%", "dna_tags": ["STEM Focus", "Research-Heavy", "Innovation Labs"]},
    {"id": 2, "name": "Stanford University", "min_gpa": 3.85, "avg_sat": 1510, "avg_act": 34, "tuition": "$61,000", "acceptance": "3.9%", "dna_tags": ["Startup Culture", "Venture Fellowship", "AI Pioneers"]},
    {"id": 3, "name": "UC Berkeley", "min_gpa": 3.65, "avg_sat": 1410, "avg_act": 31, "tuition": "$44,000", "acceptance": "11.4%", "dna_tags": ["Public Ivy", "Social Impact", "Open Source Labs"]},
    {"id": 4, "name": "Carnegie Mellon", "min_gpa": 3.75, "avg_sat": 1500, "avg_act": 34, "tuition": "$62,000", "acceptance": "11%", "dna_tags": ["Robotics Hub", "Coding Intensive", "Human-Computer Interaction"]},
    {"id": 5, "name": "Harvard University", "min_gpa": 3.9, "avg_sat": 1540, "avg_act": 35, "tuition": "$56,000", "acceptance": "3.4%", "dna_tags": ["Global Leadership", "Humanities Elite", "Case Study Method"]},
    {"id": 6, "name": "Caltech", "min_gpa": 3.9, "avg_sat": 1560, "avg_act": 36, "tuition": "$60,000", "acceptance": "2.7%", "dna_tags": ["Pure Physics", "Deep Space Research", "Mathematical Rigor"]}
]

INSTITUTIONAL_CANDIDATES = [
    {"id": 101, "name": "Alex Vance", "gpa": 3.92, "sat": 1550, "act": 35, "major": "Computer Science", "dna": ["STEM Focus", "AI Pioneers"]},
    {"id": 102, "name": "Elena Rostova", "gpa": 3.78, "sat": 1460, "act": 32, "major": "Biomedical Engineering", "dna": ["Research-Heavy", "Innovation Labs"]},
    {"id": 103, "name": "Marcus Chen", "gpa": 3.85, "sat": 1510, "act": 34, "major": "Applied Mathematics", "dna": ["Startup Culture", "Coding Intensive"]},
    {"id": 104, "name": "Sarah Jenkins", "gpa": 3.62, "sat": 1390, "act": 29, "major": "Economics & Public Policy", "dna": ["Public Ivy", "Social Impact"]}
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/match/colleges', methods=['POST'])
def match_colleges():
    data = request.json or {}
    
    # Validation constraints bound to actual academic ranges to prevent extreme inputs like 99999999
    try:
        gpa = max(0.0, min(4.0, float(data.get('gpa', 3.5))))
        sat = max(400, min(1600, int(data.get('sat', 1400))))
        act = max(1, min(36, int(data.get('act', 30))))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid numerical parameters supplied for academic credentials."}), 400

    user_major = data.get('major', 'General')
    user_dna = data.get('dna_tags', [])

    matches = []
    for u in UNIVERSITIES:
        score = 50
        if gpa >= u["min_gpa"]:
            score += 25
        if sat >= u["avg_sat"] - 50:
            score += 15
        if any(tag in u["dna_tags"] for tag in user_dna):
            score += 10
            
        score = min(99, max(45, score))
        matches.append({
            "name": u["name"],
            "match_score": score,
            "min_gpa": u["min_gpa"],
            "avg_sat": u["avg_sat"],
            "tuition": u["tuition"],
            "acceptance": u["acceptance"],
            "dna_tags": u["dna_tags"]
        })

    matches.sort(key=lambda x: x['match_score'], reverse=True)
    return jsonify({"matches": matches})

@app.route('/api/predict/deep', methods=['POST'])
def predict_deep():
    data = request.json or {}
    try:
        gpa = max(0.0, min(4.0, float(data.get('gpa', 3.7))))
        sat = max(400, min(1600, int(data.get('sat', 1450))))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid profile metrics."}), 400

    target_school = data.get('target_school', 'MIT')

    prompt = (
        f"Context: You are an expert admissions predictor utilizing real institutional benchmark datasets.\n"
        f"Candidate Profile: GPA {gpa}/4.0, SAT Score {sat}/1600.\n"
        f"Target Institution: {target_school}.\n"
        f"Task: Provide an advanced quantitative admission probability estimation, critical profile bottlenecks, "
        f"and 2 optimization action steps. Keep the response precise, highly analytical, and professionally formatted."
    )

    if not groq_client:
        return jsonify({
            "prediction": f"Based on historical metrics for {target_school}, a candidate with GPA {gpa} and SAT {sat} has a strong competitive standing. Recommended focus: amplify differentiated leadership projects."
        })

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL_ID,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        return jsonify({"prediction": completion.choices[0].message.content.strip()})
    except Exception as e:
        return jsonify({"prediction": f"Deep prediction model exception: {str(e)}"}), 500

@app.route('/api/match/institute', methods=['POST'])
def match_institute():
    data = request.json or {}
    try:
        min_gpa = max(0.0, min(4.0, float(data.get('min_gpa', 3.5))))
    except (ValueError, TypeError):
        min_gpa = 3.5

    target_dna = data.get('target_dna', [])
    anonymize = data.get('anonymize', False)

    filtered_candidates = []
    for c in INSTITUTIONAL_CANDIDATES:
        if c['gpa'] >= min_gpa:
            if not target_dna or any(tag in c['dna'] for tag in target_dna):
                cand_copy = c.copy()
                if anonymize:
                    cand_copy['name'] = f"Candidate #{c['id']}"
                filtered_candidates.append(cand_copy)

    # Dataset context injected into the AI training loop
    dataset_context = f"Active Institutional Pool Datapoints: {len(INSTITUTIONAL_CANDIDATES)} candidates indexed across universities including MIT, Stanford, Caltech with GPA range [0.0-4.0] and SAT range [400-1600]."

    prompt = (
        f"Context: You are an expert AI/ML Higher-Education Solutions Architect advising an admissions team.\n"
        f"Dataset Reference Data: {dataset_context}\n"
        f"Task: Create a highly analytical institutional outreach summary based on chosen parameters:\n"
        f"Recruitment Target Criteria: Minimum GPA: {min_gpa}/4.0, DNA Requirements: {', '.join(target_dna) if target_dna else 'All Tracks'}.\n"
        f"Constraints: Outline a data-driven strategy to capture high-yield candidates matching this DNA footprint "
        f"in the competitive US landscape. Keep the response completely objective, professional, and limited to 3 distinct sentences."
    )

    if not groq_client:
        return jsonify({
            "candidates": filtered_candidates,
            "strategy": f"Deploy data-driven recruitment pipelines prioritizing secondary high schools with deep concentrations in {', '.join(target_dna) if target_dna else 'general'} tracks. Emphasize early engagement paradigms, specialized cohort scholarships, and institutional research allowances to shift yield metrics across the matching matrix."
        })

    try:
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL_ID,
            messages=[
                {"role": "system", "content": f"You are trained on verified higher-ed admissions and candidate tracking matrices. {dataset_context}"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=250
        )
        return jsonify({
            "candidates": filtered_candidates,
            "strategy": completion.choices[0].message.content.strip()
        })
    except Exception as e:
        return jsonify({
            "candidates": filtered_candidates,
            "strategy": f"Institutional Outreach Strategy parsing pipeline exception: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
