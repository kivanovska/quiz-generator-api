from flask import Flask, request, jsonify
import fitz  # PyMuPDF
import os
import openai
from dotenv import load_dotenv
import json
import re

# Load environment variables from .env file
load_dotenv("apikey.env")
print(os.getenv("OPENROUTER_API_KEY"))


app = Flask(__name__)

# Manually set the API key
API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

if not API_KEY:
    raise ValueError("API key is missing. Check your .env file.")

openai.api_key = API_KEY

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text")
    return text

def generate_quiz(text):
    prompt = f"""
    Based on the following text, generate 5 multiple-choice quiz questions with 4 answer choices each.
    Ensure the questions are relevant to the content. **Return ONLY a JSON object with no extra text.**

    **JSON format example**:
    {{
        "questions": [
            {{
                "question": "What is the capital of France?",
                "options": ["A. Berlin", "B. Madrid", "C. Paris", "D. Rome"],
                "answer": "C. Paris"
            }},
            ...
        ]
    }}

    **Do NOT include any explanations or extra text. Return ONLY the JSON object.**
    
    Text: {text[:300]}  # Limiting input to 300 characters
    """

    try:
        client = openai.OpenAI(
            base_url=BASE_URL,
            api_key=API_KEY
        )

        response = client.chat.completions.create(
            model="deepseek/deepseek-r1:free",
            messages=[{"role": "user", "content": prompt}]
        )

        quiz_content = response.choices[0].message.content.strip()

        # Extract JSON from response using regex (handles cases where AI adds text before/after JSON)
        json_match = re.search(r'\{.*\}', quiz_content, re.DOTALL)
        if json_match:
            quiz_json = json.loads(json_match.group())
            return quiz_json
        else:
            return {"error": "AI response did not contain valid JSON."}

    except json.JSONDecodeError:
        return {"error": "Failed to parse AI response as JSON."}
    except Exception as e:
        return {"error": str(e)}

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Quiz API is running with DeepSeek AI!"})

@app.route("/generate_quiz", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    pdf_path = f"temp/{file.filename}"
    os.makedirs("temp", exist_ok=True)
    file.save(pdf_path)

    text = extract_text_from_pdf(pdf_path)
    os.remove(pdf_path)
    quiz = generate_quiz(text)

    return jsonify({"quiz": quiz})

if __name__ == "__main__":
    app.run(debug=True, port=5000)