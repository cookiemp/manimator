# --- 1. Import necessary libraries ---
import os
import uuid
import docker
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

# --- 2. Configuration and Setup ---

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()

PROJECT_ROOT = Path(__file__).parent.resolve()
docker_client = docker.from_env()
DOCKER_IMAGE_NAME = "manim-runner"

class Prompt(BaseModel):
    text: str

# --- 3. Define the API Endpoint ---
@app.post("/api/generate")
async def generate_animation(prompt: Prompt):
    print(f"Received prompt: {prompt.text}")

    try:
        # --- THIS PROMPT CONTAINS THE FINAL FIX ---
        full_prompt = f"""
        You are an expert-level Manim developer. Your primary goal is to write clear, concise, and correct Manim Community v0.19.0 code to create educational animations.

        **Your code generation must strictly adhere to the following rules:**

        1.  **Class Naming:** The main scene class must be named `GeneratedScene`.
        2.  **Self-Contained Script:** The final output must be a single, complete Python script with all necessary `from manim import *` components.
        3.  **Logical Pacing:** Use `self.wait(1)` to create pauses between distinct animations. This is crucial for viewer comprehension.
        4.  **Clarity and Simplicity:** Prefer fundamental animations like `Create`, `FadeIn`, `Transform`, and `MoveTo`.
        5.  **Correct Math Rendering:** Always use `MathTex("r'...'")` for mathematical formulas.
        6.  **Code Only:** You must not include any explanations, comments, or markdown formatting like ```python in your response. The output must be only raw Python code.
        7.  **Keyword Arguments:** When creating Mobjects like `Circle`, `Square`, or `Triangle`, you MUST use keyword arguments for all parameters except for the most obvious one (e.g., `n` for `RegularPolygon`). For example, instead of `Circle(2)`, write `Circle(radius=2)`. This prevents `TypeError`.
        8.  **Positioning:** To center an object, use `.move_to(ORIGIN)`. To place an object next to another, use `.next_to(other_object, DIRECTION)`. Do not invent positioning methods.

        ---
        **EXAMPLE OF EXCELLENT OUTPUT:**

        Here is an example of a perfect response to a user request.

        *User Request:* "A circle turning into a square"

        *Your Output:*
        ```python
        from manim import *

        class GeneratedScene(Scene):
            def construct(self):
                circle = Circle(radius=1.5, color=BLUE, fill_opacity=0.5)
                square = Square(side_length=2.5, color=RED, fill_opacity=0.5)

                self.play(Create(circle))
                self.wait(1)
                self.play(Transform(circle, square))
                self.wait(1)
                self.play(FadeOut(square))
                self.wait(1)
        ```
        ---

        **TASK:**

        Now, following all the rules and mirroring the style of the example, generate a Manim script for the following user request.

        *User's request:* "{prompt.text}"
        """
        # -----------------------------------------------

        model = genai.GenerativeModel("gemini-2.5-flash") # Keeping this model as requested
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        response = model.generate_content(full_prompt, safety_settings=safety_settings)
        generated_code = response.text.strip().replace("```python", "").replace("```", "")
        if not generated_code.strip():
            raise ValueError("AI returned an empty response.")

    except Exception as e:
        print(f"Error generating code from AI: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate code from AI.")

    script_filename = f"temp_scene_{uuid.uuid4()}.py"
    container_output = b""
    try:
        with open(PROJECT_ROOT / script_filename, "w") as f:
            f.write(generated_code)

        print(f"Running Manim in Docker for {script_filename}...")
        try:
            container_output = docker_client.containers.run(
                image=DOCKER_IMAGE_NAME,
                command=f"manim -pqh {script_filename} GeneratedScene",
                volumes={str(PROJECT_ROOT): {'bind': '/app', 'mode': 'rw'}},
                remove=True,
                stderr=True,
                stdout=True
            )
        except docker.errors.ContainerError as e:
            print("Docker container ran but the command inside failed.")
            container_output = e.stderr

    except Exception as e:
        print(f"An unexpected Docker-related error occurred: {e}")
        raise HTTPException(status_code=500, detail="An unexpected server error occurred while running Docker.")
    finally:
        if os.path.exists(PROJECT_ROOT / script_filename):
            os.remove(PROJECT_ROOT / script_filename)

    if b"Traceback (most recent call last)" in container_output:
        error_message = container_output.decode('utf-8', errors='ignore')
        print(f"Manim rendering error:\n{error_message}")
        raise HTTPException(status_code=400, detail="The AI generated invalid Manim code. Please try a different prompt.")

    video_folder_name = script_filename.replace('.py', '')
    expected_video_path = PROJECT_ROOT / "media" / "videos" / video_folder_name / "1080p60" / "GeneratedScene.mp4"

    if not os.path.exists(expected_video_path):
        if "No animations in scene" in container_output.decode('utf-8', errors='ignore'):
            print("CRITICAL ERROR: The script was valid but had no animations.")
            raise HTTPException(status_code=400, detail="The AI generated valid code, but it contained no animations. Try a different prompt.")
        else:
            print("CRITICAL ERROR: Manim reported success, but no video file was found at the expected high-quality path.")
            print("\n--- Full Container Log ---")
            print(container_output.decode('utf-8', errors='ignore'))
            print("--------------------------\n")
            raise HTTPException(status_code=500, detail="Video rendering completed, but the output file is missing. Check logs.")

    video_url = f"/media/videos/{video_folder_name}/1080p60/GeneratedScene.mp4"
    print(f"Successfully generated video. URL: {video_url}")
    return {
        "generated_code": generated_code,
        "video_url": video_url
    }

# --- 4. Mount Static Directories ---
app.mount("/media", StaticFiles(directory=PROJECT_ROOT / "media"), name="media")
app.mount("/", StaticFiles(directory=PROJECT_ROOT / "static", html=True), name="static")