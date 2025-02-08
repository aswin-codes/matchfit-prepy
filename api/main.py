import os
import json
import base64
import re
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

# Load API Key
GEMINI_API_KEY = "AIzaSyDqx4eK_6Ja9Wnpyq0GQGDRi19lSiL00uM"
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY is not set! Please set it in your environment variables.")

# Initialize FastAPI
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Model
genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel("gemini-1.5-flash")

class AiSuggestion(BaseModel):
    ColorName: str
    hexCode: str
    description: str

def extract_json_from_text(text):
    """Extract JSON array from text using regex"""
    # Find anything that looks like a JSON array
    json_match = re.search(r'\[.*\]', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            return None
    return None

def format_color_suggestion(color_data):
    """Format color suggestion to match expected schema"""
    return {
        "ColorName": color_data.get("ColorName", "Unknown Color"),
        "hexCode": color_data.get("hexCode", "#000000"),
        "description": color_data.get("description", "No description available")
    }

@app.post("/analyze-image")
async def analyze_image(image: UploadFile = File(...), image_type: str = Form(...)):
    """
    Upload an image and specify whether it's a 'top' or 'bottom'.
    The API will return color suggestions from Gemini AI.
    """
    try:
        # Validate image content type
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Uploaded file must be an image")

        # Read image bytes
        image_bytes = await image.read()
        
        # Prepare image for Gemini
        image_parts = [{
            "mime_type": image.content_type,
            "data": base64.b64encode(image_bytes).decode()
        }]

        # Prompt for Gemini with strict formatting instructions
        prompt = f"""
        Analyze this image of a {image_type} wear and suggest exactly 5 complementary colors.
        Note top wear is wore on top and bottom wear is wore on bottom. Suggest matching colors.
        If the image is not a clothing image, and some other image, responsd with error message text.
        You must respond with a JSON array containing exactly 5 color suggestions.
        Each suggestion must have these exact fields: "ColorName", "hexCode", "description"
        
        Example format:
        [
            {{
                "ColorName": "Navy Blue",
                "hexCode": "#000080",
                "description": "A deep, professional blue that pairs well with light colors"
            }},
            {{
                "ColorName": "Burgundy",
                "hexCode": "#800020",
                "description": "A rich red wine color that adds sophistication"
            }},
            {{
                "ColorName": "Forest Green",
                "hexCode": "#228B22",
                "description": "A natural green that creates an earthy combination"
            }},
                        {{
                "ColorName": "Forest Green",
                "hexCode": "#228B22",
                "description": "A natural green that creates an earthy combination"
            }},
                        {{
                "ColorName": "Forest Green",
                "hexCode": "#228B22",
                "description": "A natural green that creates an earthy combination"
            }}
        ]

        Respond only with the JSON array, no additional text or explanation.
        """

        # Call Gemini API
        response = gemini.generate_content([prompt, image_parts[0]])
        
        # Get response text
        text_response = response.text.strip()
        
        # Try to parse the response as JSON
        try:
            suggestions = json.loads(text_response)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from text
            suggestions = extract_json_from_text(text_response)
            if not suggestions:
                print("Raw response:", text_response)  # For debugging
                raise HTTPException(
                    status_code=500,
                    detail="Could not parse AI response into valid JSON format"
                )

        # Validate and format suggestions
        if not isinstance(suggestions, list):
            raise HTTPException(
                status_code=500,
                detail="Invalid response format: expected a list"
            )

        # Format each suggestion
        formatted_suggestions = [format_color_suggestion(s) for s in suggestions]
        
        # Ensure we have exactly 3 suggestions
        while len(formatted_suggestions) < 5:
            formatted_suggestions.append({
                "ColorName": "Neutral Gray",
                "hexCode": "#808080",
                "description": "A versatile neutral color"
            })
        
        formatted_suggestions = formatted_suggestions[:5]  # Limit to 3 suggestions

        return {"status": "success", "data": formatted_suggestions}

    except Exception as e:
        print(f"Error: {str(e)}")  # For debugging
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)